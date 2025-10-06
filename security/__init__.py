# app/security/__init__.py
import re
import hashlib
import secrets
from functools import wraps
from flask import request, abort, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from datetime import datetime, timedelta
import logging


class SecurityManager:
    def __init__(self, app=None):
        self.app = app
        self.rate_limiter = {}
        self.suspicious_activities = {}

    def init_app(self, app):
        """Initialize security with Flask app"""
        self.app = app

        # Security headers middleware
        @app.after_request
        def set_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers[
                'Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            return response

        # Request filtering middleware
        @app.before_request
        def filter_requests():
            self.check_rate_limit()
            self.validate_request()
            self.detect_suspicious_activity()

    def check_rate_limit(self):
        """Rate limiting implementation"""
        client_ip = request.remote_addr
        endpoint = request.endpoint

        key = f"{client_ip}:{endpoint}"
        current_time = datetime.utcnow().timestamp()

        # Clean old entries
        self.rate_limiter = {
            k: v for k, v in self.rate_limiter.items()
            if current_time - v['timestamp'] < 60  # 1 minute window
        }

        if key in self.rate_limiter:
            if self.rate_limiter[key]['count'] >= 100:  # 100 requests per minute
                self.log_security_event('rate_limit_exceeded', client_ip, {
                    'endpoint': endpoint,
                    'count': self.rate_limiter[key]['count']
                })
                abort(429, "Rate limit exceeded")
            self.rate_limiter[key]['count'] += 1
        else:
            self.rate_limiter[key] = {'count': 1, 'timestamp': current_time}

    def validate_request(self):
        """Validate incoming requests for security"""
        # Check content length
        if request.content_length and request.content_length > 50 * 1024 * 1024:  # 50MB
            abort(413, "Request too large")

        # Validate file uploads
        if request.files:
            for file in request.files.values():
                if not self.is_safe_filename(file.filename):
                    self.log_security_event('suspicious_filename', request.remote_addr, {
                        'filename': file.filename
                    })
                    abort(400, "Invalid filename")

        # Validate JSON payloads
        if request.is_json and request.json:
            self.validate_json_payload(request.json)

    def validate_json_payload(self, payload):
        """Validate JSON payload for injection attempts"""
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, str):
                    # Check for potential SQL injection
                    if self.detect_sql_injection(value):
                        self.log_security_event('sql_injection_attempt', request.remote_addr, {
                            'key': key,
                            'value': value[:100]  # Log first 100 chars
                        })
                        abort(400, "Invalid input")

                    # Check for XSS attempts
                    if self.detect_xss(value):
                        self.log_security_event('xss_attempt', request.remote_addr, {
                            'key': key,
                            'value': value[:100]
                        })
                        abort(400, "Invalid input")

    def detect_sql_injection(self, text):
        """Detect SQL injection patterns"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC)\b)",
            r"(\b(OR|AND)\b.*=)",
            r"('(''|[^'])*')",
            r"(\b(WAITFOR|DELAY)\b)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def detect_xss(self, text):
        """Detect XSS attack patterns"""
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe.*?>",
            r"<img.*?src=.*?>"
        ]

        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def is_safe_filename(self, filename):
        """Check if filename is safe"""
        if not filename:
            return False

        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False

        # Check extension
        allowed_extensions = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        return file_ext in allowed_extensions

    def detect_suspicious_activity(self):
        """Detect suspicious activity patterns"""
        client_ip = request.remote_addr

        # Check for rapid successive requests to different endpoints
        current_time = datetime.utcnow()
        if client_ip not in self.suspicious_activities:
            self.suspicious_activities[client_ip] = []

        # Add current request
        self.suspicious_activities[client_ip].append({
            'endpoint': request.endpoint,
            'timestamp': current_time,
            'user_agent': request.headers.get('User-Agent', '')
        })

        # Clean old entries (last 5 minutes)
        self.suspicious_activities[client_ip] = [
            activity for activity in self.suspicious_activities[client_ip]
            if current_time - activity['timestamp'] < timedelta(minutes=5)
        ]

        # Check if suspicious (more than 20 different endpoints in 5 minutes)
        unique_endpoints = len(set(activity['endpoint'] for activity in self.suspicious_activities[client_ip]))
        if unique_endpoints > 20:
            self.log_security_event('suspicious_activity', client_ip, {
                'unique_endpoints': unique_endpoints,
                'total_requests': len(self.suspicious_activities[client_ip])
            })

    def log_security_event(self, event_type, ip_address, details):
        """Log security events"""
        logger = logging.getLogger('security')
        logger.warning(f"Security event: {event_type} from {ip_address} - {details}")


class AuthenticationManager:
    def __init__(self, app=None):
        self.app = app
        self.jwt_secret = None

    def init_app(self, app):
        """Initialize authentication with Flask app"""
        self.app = app
        self.jwt_secret = app.config.get('SECRET_KEY')

        if not self.jwt_secret or self.jwt_secret == 'dev-secret-key-change-in-production':
            raise ValueError("JWT secret key must be set in production")

    def generate_token(self, user_id, expires_in=3600):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }

        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def hash_password(self, password):
        """Hash password using secure method"""
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def verify_password(self, password_hash, password):
        """Verify password against hash"""
        return check_password_hash(password_hash, password)


def require_auth(f):
    """Decorator for requiring authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            abort(401, "Authentication required")

        user_id = AuthenticationManager().verify_token(token)
        if not user_id:
            abort(401, "Invalid or expired token")

        # Add user_id to request context
        request.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function


def require_role(role):
    """Decorator for requiring specific role"""

    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # Implement role-based access control here
            # This would check if the user has the required role
            user_roles = get_user_roles(request.user_id)  # Implement this function
            if role not in user_roles:
                abort(403, "Insufficient permissions")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class InputSanitizer:
    @staticmethod
    def sanitize_string(text):
        """Sanitize string input"""
        if not text:
            return text

        # Remove potentially dangerous characters
        text = re.sub(r'[<>]', '', text)

        # Limit length
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()

    @staticmethod
    def sanitize_url(url):
        """Sanitize URL input"""
        if not url:
            return url

        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return None

        # Remove dangerous characters
        url = re.sub(r'[<>"\']', '', url)

        return url[:2000]  # Limit URL length

    @staticmethod
    def sanitize_email(email):
        """Sanitize email input"""
        if not email:
            return email

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return None

        return email.lower().strip()


class DataEncryption:
    def __init__(self, key=None):
        self.key = key or secrets.token_bytes(32)

    def encrypt_data(self, data):
        """Encrypt sensitive data"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64

        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.key))
        f = Fernet(key)

        encrypted_data = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt + encrypted_data).decode()

    def decrypt_data(self, encrypted_data):
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64

        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            salt = data[:16]
            encrypted = data[16:]

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.key))
            f = Fernet(key)

            return f.decrypt(encrypted).decode()
        except Exception:
            return None# app/security/__init__.py
import re
import hashlib
import secrets
from functools import wraps
from flask import request, abort, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from datetime import datetime, timedelta
import logging

class SecurityManager:
    def __init__(self, app=None):
        self.app = app
        self.rate_limiter = {}
        self.suspicious_activities = {}

    def init_app(self, app):
        """Initialize security with Flask app"""
        self.app = app

        # Security headers middleware
        @app.after_request
        def set_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            return response

        # Request filtering middleware
        @app.before_request
        def filter_requests():
            self.check_rate_limit()
            self.validate_request()
            self.detect_suspicious_activity()

    def check_rate_limit(self):
        """Rate limiting implementation"""
        client_ip = request.remote_addr
        endpoint = request.endpoint

        key = f"{client_ip}:{endpoint}"
        current_time = datetime.utcnow().timestamp()

        # Clean old entries
        self.rate_limiter = {
            k: v for k, v in self.rate_limiter.items()
            if current_time - v['timestamp'] < 60  # 1 minute window
        }

        if key in self.rate_limiter:
            if self.rate_limiter[key]['count'] >= 100:  # 100 requests per minute
                self.log_security_event('rate_limit_exceeded', client_ip, {
                    'endpoint': endpoint,
                    'count': self.rate_limiter[key]['count']
                })
                abort(429, "Rate limit exceeded")
            self.rate_limiter[key]['count'] += 1
        else:
            self.rate_limiter[key] = {'count': 1, 'timestamp': current_time}

    def validate_request(self):
        """Validate incoming requests for security"""
        # Check content length
        if request.content_length and request.content_length > 50 * 1024 * 1024:  # 50MB
            abort(413, "Request too large")

        # Validate file uploads
        if request.files:
            for file in request.files.values():
                if not self.is_safe_filename(file.filename):
                    self.log_security_event('suspicious_filename', request.remote_addr, {
                        'filename': file.filename
                    })
                    abort(400, "Invalid filename")

        # Validate JSON payloads
        if request.is_json and request.json:
            self.validate_json_payload(request.json)

    def validate_json_payload(self, payload):
        """Validate JSON payload for injection attempts"""
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, str):
                    # Check for potential SQL injection
                    if self.detect_sql_injection(value):
                        self.log_security_event('sql_injection_attempt', request.remote_addr, {
                            'key': key,
                            'value': value[:100]  # Log first 100 chars
                        })
                        abort(400, "Invalid input")

                    # Check for XSS attempts
                    if self.detect_xss(value):
                        self.log_security_event('xss_attempt', request.remote_addr, {
                            'key': key,
                            'value': value[:100]
                        })
                        abort(400, "Invalid input")

    def detect_sql_injection(self, text):
        """Detect SQL injection patterns"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC)\b)",
            r"(\b(OR|AND)\b.*=)",
            r"('(''|[^'])*')",
            r"(\b(WAITFOR|DELAY)\b)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def detect_xss(self, text):
        """Detect XSS attack patterns"""
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe.*?>",
            r"<img.*?src=.*?>"
        ]

        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def is_safe_filename(self, filename):
        """Check if filename is safe"""
        if not filename:
            return False

        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False

        # Check extension
        allowed_extensions = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        return file_ext in allowed_extensions

    def detect_suspicious_activity(self):
        """Detect suspicious activity patterns"""
        client_ip = request.remote_addr

        # Check for rapid successive requests to different endpoints
        current_time = datetime.utcnow()
        if client_ip not in self.suspicious_activities:
            self.suspicious_activities[client_ip] = []

        # Add current request
        self.suspicious_activities[client_ip].append({
            'endpoint': request.endpoint,
            'timestamp': current_time,
            'user_agent': request.headers.get('User-Agent', '')
        })

        # Clean old entries (last 5 minutes)
        self.suspicious_activities[client_ip] = [
            activity for activity in self.suspicious_activities[client_ip]
            if current_time - activity['timestamp'] < timedelta(minutes=5)
        ]

        # Check if suspicious (more than 20 different endpoints in 5 minutes)
        unique_endpoints = len(set(activity['endpoint'] for activity in self.suspicious_activities[client_ip]))
        if unique_endpoints > 20:
            self.log_security_event('suspicious_activity', client_ip, {
                'unique_endpoints': unique_endpoints,
                'total_requests': len(self.suspicious_activities[client_ip])
            })

    def log_security_event(self, event_type, ip_address, details):
        """Log security events"""
        logger = logging.getLogger('security')
        logger.warning(f"Security event: {event_type} from {ip_address} - {details}")

class AuthenticationManager:
    def __init__(self, app=None):
        self.app = app
        self.jwt_secret = None

    def init_app(self, app):
        """Initialize authentication with Flask app"""
        self.app = app
        self.jwt_secret = app.config.get('SECRET_KEY')

        if not self.jwt_secret or self.jwt_secret == 'dev-secret-key-change-in-production':
            raise ValueError("JWT secret key must be set in production")

    def generate_token(self, user_id, expires_in=3600):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }

        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def hash_password(self, password):
        """Hash password using secure method"""
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def verify_password(self, password_hash, password):
        """Verify password against hash"""
        return check_password_hash(password_hash, password)

def require_auth(f):
    """Decorator for requiring authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            abort(401, "Authentication required")

        user_id = AuthenticationManager().verify_token(token)
        if not user_id:
            abort(401, "Invalid or expired token")

        # Add user_id to request context
        request.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function

def require_role(role):
    """Decorator for requiring specific role"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # Implement role-based access control here
            # This would check if the user has the required role
            user_roles = get_user_roles(request.user_id)  # Implement this function
            if role not in user_roles:
                abort(403, "Insufficient permissions")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class InputSanitizer:
    @staticmethod
    def sanitize_string(text):
        """Sanitize string input"""
        if not text:
            return text

        # Remove potentially dangerous characters
        text = re.sub(r'[<>]', '', text)

        # Limit length
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()

    @staticmethod
    def sanitize_url(url):
        """Sanitize URL input"""
        if not url:
            return url

        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return None

        # Remove dangerous characters
        url = re.sub(r'[<>"\']', '', url)

        return url[:2000]  # Limit URL length

    @staticmethod
    def sanitize_email(email):
        """Sanitize email input"""
        if not email:
            return email

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return None

        return email.lower().strip()

class DataEncryption:
    def __init__(self, key=None):
        self.key = key or secrets.token_bytes(32)

    def encrypt_data(self, data):
        """Encrypt sensitive data"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64

        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.key))
        f = Fernet(key)

        encrypted_data = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt + encrypted_data).decode()

    def decrypt_data(self, encrypted_data):
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64

        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            salt = data[:16]
            encrypted = data[16:]

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.key))
            f = Fernet(key)

            return f.decrypt(encrypted).decode()
        except Exception:
            return None