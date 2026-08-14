import logging
import logging.handlers
import json
from datetime import datetime
from flask import request, has_request_context
import os
import uuid

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

SECURITY_LOG = os.path.join(LOG_DIR, "security.log")
APP_LOG = os.path.join(LOG_DIR, "app.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
ACCESS_LOG = os.path.join(LOG_DIR, "access.log")
AUDIT_LOG = os.path.join(LOG_DIR, "audit.log")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if has_request_context():
            log_data["request_id"] = getattr(request, 'request_id', None)
            log_data["remote_addr"] = request.remote_addr
            log_data["method"] = request.method
            log_data["path"] = request.path
            log_data["user_agent"] = request.headers.get('User-Agent', '')
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
        return json.dumps(log_data)

class ColoredConsoleFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41m',
        'RESET': '\033[0m'
    }
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.levelname = f"{color}{record.levelname}{reset}"
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return f"[{timestamp}] {record.levelname}: {record.getMessage()}"

def setup_logging(app=None):
    loggers = {}

    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    file_handler = logging.handlers.RotatingFileHandler(APP_LOG, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(JsonFormatter())
    app_logger.addHandler(file_handler)
    if app and app.config.get('FLASK_ENV') == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredConsoleFormatter())
        app_logger.addHandler(console_handler)
    loggers['app'] = app_logger

    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    sec_handler = logging.handlers.RotatingFileHandler(SECURITY_LOG, maxBytes=10*1024*1024, backupCount=10)
    sec_handler.setFormatter(JsonFormatter())
    security_logger.addHandler(sec_handler)
    if app and app.config.get('FLASK_ENV') == 'development':
        sec_console = logging.StreamHandler()
        sec_console.setFormatter(ColoredConsoleFormatter())
        security_logger.addHandler(sec_console)
    loggers['security'] = security_logger

    error_logger = logging.getLogger('error')
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False
    err_handler = logging.handlers.RotatingFileHandler(ERROR_LOG, maxBytes=10*1024*1024, backupCount=10)
    err_handler.setFormatter(JsonFormatter())
    error_logger.addHandler(err_handler)
    loggers['error'] = error_logger

    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    access_handler = logging.handlers.RotatingFileHandler(ACCESS_LOG, maxBytes=10*1024*1024, backupCount=5)
    access_handler.setFormatter(JsonFormatter())
    access_logger.addHandler(access_handler)
    loggers['access'] = access_logger

    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    audit_handler = logging.handlers.RotatingFileHandler(AUDIT_LOG, maxBytes=10*1024*1024, backupCount=10)
    audit_handler.setFormatter(JsonFormatter())
    audit_logger.addHandler(audit_handler)
    loggers['audit'] = audit_logger

    return loggers

def get_logger(name):
    return logging.getLogger(name)

def log_security_event(event_type, user_id=None, details=None, severity='info'):
    logger = logging.getLogger('security')
    extra = {'event_type': event_type, 'user_id': user_id, 'severity': severity}
    if details:
        extra['details'] = details
    if has_request_context():
        extra['ip'] = request.remote_addr
        extra['path'] = request.path
        extra['method'] = request.method
    record = logging.LogRecord(
        name='security', level=logging.INFO, pathname='', lineno=0,
        msg=f"Security event: {event_type}", args=(), exc_info=None
    )
    record.extra_data = extra
    logger.handle(record)

def log_audit(action, user_id=None, target=None, details=None):
    logger = logging.getLogger('audit')
    extra = {'action': action, 'user_id': user_id, 'target': target, 'timestamp': datetime.utcnow().isoformat() + 'Z'}
    if details:
        extra['details'] = details
    if has_request_context():
        extra['ip'] = request.remote_addr
    record = logging.LogRecord(
        name='audit', level=logging.INFO, pathname='', lineno=0,
        msg=f"Audit: {action}", args=(), exc_info=None
    )
    record.extra_data = extra
    logger.handle(record)

def log_access(request, response=None, duration_ms=None):
    logger = logging.getLogger('access')
    extra = {
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': response.status_code if response else None,
        'duration_ms': duration_ms,
    }
    if has_request_context():
        from flask_jwt_extended import get_jwt_identity
        try:
            user_id = get_jwt_identity()
            if user_id:
                extra['user_id'] = user_id
        except:
            pass
    record = logging.LogRecord(
        name='access', level=logging.INFO, pathname='', lineno=0,
        msg=f"Access: {request.method} {request.path}", args=(), exc_info=None
    )
    record.extra_data = extra
    logger.handle(record)

def log_error(error, context=None):
    logger = logging.getLogger('error')
    extra = {'error_type': type(error).__name__, 'error_message': str(error), 'context': context}
    if has_request_context():
        extra['path'] = request.path
        extra['method'] = request.method
        extra['ip'] = request.remote_addr
    record = logging.LogRecord(
        name='error', level=logging.ERROR, pathname='', lineno=0,
        msg=f"Error: {str(error)}", args=(), exc_info=error.__traceback__
    )
    record.extra_data = extra
    logger.handle(record)

def log_app_event(message, level='info', extra=None):
    logger = logging.getLogger('app')
    level_map = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING,
                 'error': logging.ERROR, 'critical': logging.CRITICAL}
    log_level = level_map.get(level, logging.INFO)
    record = logging.LogRecord(
        name='app', level=log_level, pathname='', lineno=0,
        msg=message, args=(), exc_info=None
    )
    if extra:
        record.extra_data = extra
    logger.handle(record)

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        request_id = str(uuid.uuid4())[:8]
        environ['REQUEST_ID'] = request_id
        def start_response_with_id(status, headers, exc_info=None):
            headers.append(('X-Request-ID', request_id))
            return start_response(status, headers, exc_info)
        return self.app(environ, start_response_with_id)

def set_request_id():
    if has_request_context():
        request.request_id = request.environ.get('REQUEST_ID', str(uuid.uuid4())[:8])