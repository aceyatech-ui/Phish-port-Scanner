from datetime import datetime
from flask import request
from app.models import AnonymousScan, User
from app.config import Config
from app import db

def get_ip_address():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def get_month_key():
    return datetime.utcnow().strftime("%Y-%m")

def can_scan_anonymously(ip):
    month = get_month_key()
    count = AnonymousScan.query.filter_by(ip_address=ip, month=month).count()
    return count < Config.MAX_FREE_SCANS_PER_MONTH

def can_user_scan(user):
    if user.is_paid_user:
        return True, 'paid'

    today = datetime.utcnow()
    if today.month != user.free_scans_last_reset.month:
        user.free_scans_used_this_month = 0
        user.free_scans_last_reset = today
        db.session.commit()

    if user.free_scans_used_this_month < Config.MAX_FREE_SCANS_PER_MONTH:
        return True, 'free'
    return False, 'limit_reached'

def track_anonymous_scan(ip, target, results=None):
    scan = AnonymousScan(
        ip_address=ip,
        target=target,
        month=get_month_key(),
        results=results
    )
    db.session.add(scan)
    db.session.commit()

def track_user_scan(user):
    user.free_scans_used_this_month += 1
    db.session.commit()

def get_anonymous_scan_count(ip):
    month = get_month_key()
    return AnonymousScan.query.filter_by(ip_address=ip, month=month).count()

def get_remaining_free_scans(ip):
    used = get_anonymous_scan_count(ip)
    remaining = Config.MAX_FREE_SCANS_PER_MONTH - used
    return max(0, remaining)

def get_user_remaining_free_scans(user):
    today = datetime.utcnow()
    if today.month != user.free_scans_last_reset.month:
        user.free_scans_used_this_month = 0
        user.free_scans_last_reset = today
        db.session.commit()
    remaining = Config.MAX_FREE_SCANS_PER_MONTH - user.free_scans_used_this_month
    return max(0, remaining)