from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.models import db, Scan, User
from app.tasks import perform_scan
from app.services.report import generate_report_html
from app.services.email import send_pdf_report
from app.utils.security import validate_target
from app.utils.limits import (
    get_ip_address, can_scan_anonymously, can_user_scan,
    track_anonymous_scan, track_user_scan,
    get_remaining_free_scans, get_user_remaining_free_scans
)
from app.config import Config
from app.utils.logging import log_audit, log_app_event, log_error
from email_validator import validate_email, EmailNotValidError

scans_bp = Blueprint('scans', __name__)
limiter = Limiter(key_func=get_remote_address)

@scans_bp.route('', methods=['POST'])
@limiter.limit("10 per hour")
def create_scan():
    data = request.get_json()
    target = data.get('target')
    authorized = data.get('authorized', False)

    if not target or not authorized:
        return {'msg': 'Target and authorisation required'}, 400

    try:
        validated_target, host, port = validate_target(target)
    except ValueError as e:
        return {'msg': str(e)}, 400

    auth_header = request.headers.get('Authorization')
    user_id = None
    user = None

    if auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            user_id = decoded['sub']
            user = User.query.get(user_id)
        except:
            pass

    if user:
        allowed, reason = can_user_scan(user)
        if not allowed:
            return {
                'msg': 'Monthly free scan limit reached. Upgrade to continue.',
                'requires_auth': True,
                'remaining': 0,
                'max_free': Config.MAX_FREE_SCANS_PER_MONTH
            }, 429

        scan = Scan(target=validated_target, user_id=user.id, status='queued')
        db.session.add(scan)
        db.session.commit()
        track_user_scan(user)
        current_app.task_queue.enqueue(perform_scan, scan.id)
        remaining = get_user_remaining_free_scans(user)
        log_app_event(f"User scan queued: {validated_target}", extra={'user_id': user.id, 'scan_id': scan.id})
        return {
            'scan_id': scan.id,
            'remaining_free': remaining,
            'max_free': Config.MAX_FREE_SCANS_PER_MONTH,
            'requires_auth': False
        }, 202

    ip = get_ip_address()
    if not can_scan_anonymously(ip):
        return {
            'msg': 'Free scan limit reached. Create an account or subscribe for unlimited scans.',
            'requires_auth': True,
            'remaining': 0,
            'max_free': Config.MAX_FREE_SCANS_PER_MONTH
        }, 429

    scan = Scan(target=validated_target, user_id=None, status='queued')
    db.session.add(scan)
    db.session.commit()
    track_anonymous_scan(ip, validated_target)
    current_app.task_queue.enqueue(perform_scan, scan.id)
    remaining = get_remaining_free_scans(ip)
    log_app_event(f"Anonymous scan queued: {validated_target}", extra={'ip': ip, 'scan_id': scan.id})
    return {
        'scan_id': scan.id,
        'remaining_free': remaining,
        'max_free': Config.MAX_FREE_SCANS_PER_MONTH,
        'requires_auth': False
    }, 202

@scans_bp.route('', methods=['GET'])
@jwt_required()
def list_scans():
    user_id = get_jwt_identity()
    scans = Scan.query.filter_by(user_id=user_id).order_by(Scan.created_at.desc()).all()
    return [s.to_dict() for s in scans], 200

@scans_bp.route('/<scan_id>', methods=['GET'])
@jwt_required()
def get_scan(scan_id):
    user_id = get_jwt_identity()
    scan = Scan.query.filter_by(id=scan_id, user_id=user_id).first()
    if not scan:
        return {'msg': 'Not found'}, 404
    include_results = request.args.get('include_results', 'false').lower() == 'true'
    return scan.to_dict(include_results=include_results), 200

@scans_bp.route('/<scan_id>/report', methods=['GET'])
@jwt_required()
def get_report(scan_id):
    user_id = get_jwt_identity()
    scan = Scan.query.filter_by(id=scan_id, user_id=user_id).first()
    if not scan:
        return {'msg': 'Not found'}, 404
    if scan.status != 'completed':
        return {'msg': 'Scan not completed'},