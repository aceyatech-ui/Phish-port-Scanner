import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///recon.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-dev-secret'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    VT_API_KEY = os.environ.get('VT_API_KEY') or ''
    MAX_FREE_SCANS_PER_MONTH = int(os.environ.get('MAX_FREE_SCANS_PER_MONTH', 3))

    # Substack
    SUBSTACK_URL = os.environ.get('SUBSTACK_URL', '')
    SUBSTACK_API_KEY = os.environ.get('SUBSTACK_API_KEY', '')

    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@recon-platform.com')

    # Contact
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'aceyathedev@gmail.com')   # <-- NEW LINE HERE

    # Security
    MAX_REDIRECTS = 5
    REQUEST_TIMEOUT = 10
    DNS_TIMEOUT = 5
    PORT_SCAN_TIMEOUT = 2
    SCAN_TIMEOUT = 60
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024
    ALLOWED_PROTOCOLS = ('http', 'https')
    PRIVATE_IP_RANGES = [
        '127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
        '169.254.0.0/16', '::1', 'fc00::/7', 'fe80::/10'
    ]