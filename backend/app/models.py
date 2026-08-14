from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid_user = db.Column(db.Boolean, default=False)
    subscription_tier = db.Column(db.String(20), default='free')
    free_scans_used_this_month = db.Column(db.Integer, default=0)
    free_scans_last_reset = db.Column(db.DateTime, default=datetime.utcnow)
    subscribed_to_newsletter = db.Column(db.Boolean, default=False)
    scans = db.relationship('Scan', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_jwt(self):
        return create_access_token(identity=self.id)

class Scan(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='queued')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    results = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    def to_dict(self, include_results=False):
        data = {
            'id': self.id,
            'target': self.target,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_results:
            data['results'] = self.results
            data['error_message'] = self.error_message
        return data

class AnonymousScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    target = db.Column(db.String(255), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    month = db.Column(db.String(7), nullable=False)
    results = db.Column(db.JSON, nullable=True)