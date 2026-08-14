from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User
from app.utils.logging import log_security_event, log_audit, log_app_event, log_error
from app.config import Config
import requests

auth_bp = Blueprint('auth', __name__)

SUBSTACK_URL = Config.SUBSTACK_URL
SUBSTACK_API_KEY = Config.SUBSTACK_API_KEY

def subscribe_to_substack(email, name=None):
    if not SUBSTACK_URL:
        current_app.logger.warning("SUBSTACK_URL not configured")
        return False
    try:
        url = f"{SUBSTACK_URL}/api/v1/subscribe"
        payload = {"email": email, "name": name or "", "source": "recon-platform"}
        headers = {"Content-Type": "application/json"}
        if SUBSTACK_API_KEY:
            headers["Authorization"] = f"Bearer {SUBSTACK_API_KEY}"
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            current_app.logger.info(f"Subscribed {email} to Substack")
            return True
        else:
            current_app.logger.warning(f"Substack subscription failed: {response.status_code}")
            return False
    except Exception as e:
        current_app.logger.error(f"Substack error: {str(e)}")
        return False

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    subscribe_newsletter = data.get('subscribe_newsletter', False)

    if not username or not email or not password:
        return {'msg': 'Missing fields'}, 400

    if User.query.filter_by(username=username).first():
        return {'msg': 'Username taken'}, 409
    if User.query.filter_by(email=email).first():
        return {'msg': 'Email registered'}, 409

    user = User(
        username=username,
        email=email,
        subscribed_to_newsletter=subscribe_newsletter
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    log_audit('register', user_id=user.id, target=username)
    log_security_event('registration_success', user_id=user.id, details={'username': username, 'email': email})

    if subscribe_newsletter:
        try:
            subscribe_to_substack(email, username)
        except Exception as e:
            log_error(e, context={'email': email, 'action': 'substack_subscription'})

    return {'access_token': user.get_jwt()}, 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        log_security_event('login_success', user_id=user.id, details={'username': user.username})
        return {'access_token': user.get_jwt()}, 200
    log_security_event('login_failure', details={'username': data.get('username'), 'ip': request.remote_addr})
    return {'msg': 'Invalid credentials'}, 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_paid_user': user.is_paid_user,
        'subscription_tier': user.subscription_tier,
        'subscribed_to_newsletter': user.subscribed_to_newsletter
    }, 200

@auth_bp.route('/admin/newsletter-export', methods=['GET'])
@jwt_required()
def export_newsletter():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.username != 'admin':
        return {'msg': 'Unauthorized'}, 403
    subscribers = User.query.filter_by(subscribed_to_newsletter=True).all()
    emails = [{'email': u.email, 'username': u.username, 'created': u.created_at.isoformat()} for u in subscribers]
    return {'subscribers': emails}, 200