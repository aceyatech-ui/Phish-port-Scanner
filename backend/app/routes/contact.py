from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from app.services.email import mail
from app.utils.logging import log_app_event, log_error
import re

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('', methods=['POST'])
def send_contact():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not all([name, email, subject, message]):
        return {'msg': 'All fields are required'}, 400

    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return {'msg': 'Invalid email address'}, 400

    try:
        msg = Message(
            subject=f"Contact Form: {subject}",
            recipients=[current_app.config.get('CONTACT_EMAIL', 'aceyathedev@gmail.com')],
            reply_to=email,
            body=f"""
Name: {name}
Email: {email}
Subject: {subject}
Message:
{message}
            """
        )
        mail.send(msg)
        log_app_event(f"Contact message from {email}", extra={'name': name, 'subject': subject})
        return {'msg': 'Message sent successfully'}, 200
    except Exception as e:
        log_error(e, context={'email': email, 'name': name})
        return {'msg': 'Failed to send message'}, 500