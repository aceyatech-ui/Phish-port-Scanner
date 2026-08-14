from flask import Flask, request
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis
from rq import Queue

from app.config import Config
from app.models import db
from app.utils.logging import setup_logging, set_request_id, RequestIDMiddleware
from app.services.email import init_mail

migrate = Migrate()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per hour"])

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Request ID middleware
    app.wsgi_app = RequestIDMiddleware(app.wsgi_app)

    # Setup logging
    loggers = setup_logging(app)
    app.loggers = loggers
    app.logger = loggers['app']

    # Setup mail
    init_mail(app)

    @app.before_request
    def before_request():
        set_request_id()

    @app.after_request
    def after_request(response):
        from app.utils.logging import log_access
        log_access(request, response)
        return response

    # Database
    db.init_app(app)
    migrate.init_app(app, db)

    # JWT
    jwt.init_app(app)

    # CORS
    cors.init_app(app, origins="*")

    # Rate limiting
    limiter.init_app(app)

    # Redis / RQ
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = Queue('recon', connection=app.redis)

    # ===== Register Blueprints =====
    from app.routes.auth import auth_bp
    from app.routes.scans import scans_bp
    from app.routes.payment import payment_bp
    from app.routes.contact import contact_bp  

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(scans_bp, url_prefix='/api/scans')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(contact_bp, url_prefix='/api/contact')  

    return app   