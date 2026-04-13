"""
Security Configuration for Fikiri Solutions
Production-ready security headers, rate limiting, and CORS
"""

import os
import time
import logging

from config import IS_PRODUCTION
from functools import wraps
from typing import Dict, Any, Optional

# Optional ProxyFix import
try:
    from werkzeug.middleware.proxy_fix import ProxyFix
    PROXY_FIX_AVAILABLE = True
except ImportError:
    PROXY_FIX_AVAILABLE = False
    ProxyFix = None

# Initialize logger
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    from flask import Flask, request, jsonify, g
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not available. Install with: pip install flask flask-cors flask-limiter")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Install with: pip install redis")


def resolve_flask_limiter_storage_uri() -> str:
    """
    Storage URI for Flask-Limiter (shared with limits library).
    Prefer Redis when REDIS_URL resolves and a client can connect; else memory://.

    In development/test, default to memory:// so a bad or unreachable REDIS_URL (DNS/auth)
    cannot 500 every request via Flask-Limiter's before_request. Opt into Redis in dev with
    FLASK_LIMITER_USE_REDIS=1. Force memory in any environment with FIKIRI_LIMITER_MEMORY=1.
    """
    if os.getenv("FIKIRI_LIMITER_MEMORY", "").strip().lower() in ("1", "true", "yes"):
        return "memory://"
    env = os.getenv("FLASK_ENV", "").lower()
    use_redis_explicit = os.getenv("FLASK_LIMITER_USE_REDIS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if env in ("development", "test") and not use_redis_explicit:
        return "memory://"
    try:
        try:
            from core.redis_connection_helper import _resolve_redis_url
            redis_url = _resolve_redis_url() or os.getenv("REDIS_URL", "") or ""
        except Exception:
            redis_url = os.getenv("REDIS_URL", "") or ""
        if redis_url.startswith(("redis://", "rediss://")):
            if redis_url.startswith("rediss://") and "ssl_cert_reqs=" not in redis_url:
                sep = "&" if "?" in redis_url else "?"
                redis_url = f"{redis_url}{sep}ssl_cert_reqs=none"
            try:
                from core.redis_connection_helper import get_redis_client

                client = get_redis_client(decode_responses=True, db=0)
                if client:
                    try:
                        client.ping()
                    except Exception:
                        return "memory://"
                    return redis_url
            except Exception:
                pass
        return "memory://"
    except Exception:
        return "memory://"


def _security_redis_client_for_decorators():
    """Redis client for custom rate_limit_by_* decorators (optional)."""
    try:
        from core.redis_connection_helper import _resolve_redis_url, get_redis_client

        redis_url = _resolve_redis_url() or os.getenv("REDIS_URL", "") or ""
        if redis_url.startswith(("redis://", "rediss://")):
            return get_redis_client(decode_responses=True, db=0)
    except Exception:
        pass
    return None


def init_security(app: Flask):
    """Initialize security middleware and configurations"""
    
    # Trust proxy headers (for rate limiting behind reverse proxy)
    # ProxyFix for production deployments behind reverse proxy
    if PROXY_FIX_AVAILABLE:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        logger.info("✅ ProxyFix middleware enabled")
    else:
        logger.warning("⚠️ ProxyFix not available - install werkzeug for production deployments")
    
    redis_client = _security_redis_client_for_decorators()

    # Flask-Limiter: reuse instance if setup_routes (app.py) already bound one with storage_uri.
    existing_limiter = None
    if getattr(app, "extensions", None):
        existing_limiter = app.extensions.get("limiter")

    storage_uri = resolve_flask_limiter_storage_uri()
    limiter = None
    if FLASK_AVAILABLE:
        try:
            if existing_limiter is not None:
                limiter = existing_limiter
                logger.info("ℹ️ Flask-Limiter already on app (Redis/memory from factory); reusing instance")
            else:
                if storage_uri == "memory://":
                    logger.info("ℹ️ No Redis URL or Redis unreachable, using in-memory rate limiting")
                else:
                    logger.info("✅ Rate limiter will use Redis shared storage")
                limiter = Limiter(
                    key_func=get_remote_address,
                    storage_uri=storage_uri,
                    default_limits=[
                        os.getenv("APP_RATE_LIMIT_PER_HOUR", "1000 per hour"),
                        os.getenv("APP_RATE_LIMIT_PER_MINUTE", "100 per minute"),
                    ],
                )
                limiter.init_app(app)
                if storage_uri == "memory://":
                    logger.info("✅ Rate limiter initialized (in-memory storage - limits reset on restart)")
                else:
                    host_hint = storage_uri.split("@")[-1] if "@" in storage_uri else "localhost"
                    logger.info("✅ Rate limiter initialized with Redis: %s", host_hint)
        except Exception as e:
            logger.error(f"❌ Failed to initialize rate limiter: {e}")
            logger.warning("⚠️ Rate limiting disabled due to initialization error")
            # Try in-memory as last resort
            try:
                limiter = Limiter(
                    key_func=get_remote_address,
                    storage_uri='memory://',
                    default_limits=[
                        os.getenv("APP_RATE_LIMIT_PER_HOUR", "1000 per hour"),
                        os.getenv("APP_RATE_LIMIT_PER_MINUTE", "100 per minute"),
                    ]
                )
                limiter.init_app(app)
                logger.info("✅ Rate limiter initialized (in-memory fallback)")
            except Exception as e2:
                logger.error(f"❌ Failed to initialize in-memory rate limiter: {e2}")
                limiter = None
    else:
        logger.warning("⚠️ Flask-Limiter not available - rate limiting disabled")
    
    # Configure CORS (only if not already configured in app.py)
    # Check if CORS is already configured by checking if app has _cors attribute
    if not hasattr(app, '_cors_configured'):
        _cors_default = (
            "https://fikirisolutions.com,https://www.fikirisolutions.com"
            if IS_PRODUCTION
            else "http://localhost:3000,http://localhost:5173,http://localhost:5174"
        )
        cors_origins = os.getenv("CORS_ORIGINS", _cors_default).split(",")
        # Strip whitespace from origins
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
        CORS(app, 
             origins=cors_origins,
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'x-correlation-id'],
             supports_credentials=True,
             max_age=3600
        )
        logger.info(f"✅ CORS configured with origins: {cors_origins}")
    else:
        logger.info("ℹ️ CORS already configured in app.py, skipping reconfiguration")
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com https://api.openai.com; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp_policy
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (only in production)
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Remove server header
        response.headers.pop('Server', None)
        
        return response
    
    # Rate limiting decorators
    def rate_limit_by_user(limit):
        """Rate limit by authenticated user"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                user_id = getattr(g, 'user_id', None)
                if user_id:
                    key = f"user:{user_id}"
                else:
                    key = get_remote_address()
                
                # Check rate limit
                if not redis_client:
                    return f(*args, **kwargs)
                current = redis_client.get(key)
                if current is None:
                    redis_client.setex(key, 3600, 1)  # 1 hour window
                else:
                    current = int(current)
                    if current >= limit:
                        return jsonify({
                            'status': 'error',
                            'error_code': 'RATE_LIMIT_EXCEEDED',
                            'message': 'Rate limit exceeded',
                            'retry_after': 3600
                        }), 429
                    redis_client.incr(key)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    # IP-based rate limiting
    def rate_limit_by_ip(limit):
        """Rate limit by IP address"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                ip = get_remote_address()
                key = f"ip:{ip}"
                
                if not redis_client:
                    return f(*args, **kwargs)
                current = redis_client.get(key)
                if current is None:
                    redis_client.setex(key, 3600, 1)
                else:
                    current = int(current)
                    if current >= limit:
                        return jsonify({
                            'status': 'error',
                            'error_code': 'RATE_LIMIT_EXCEEDED',
                            'message': 'Rate limit exceeded',
                            'retry_after': 3600
                        }), 429
                    redis_client.incr(key)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    # Store limiter and decorators in app context
    app.limiter = limiter
    app.rate_limit_by_user = rate_limit_by_user
    app.rate_limit_by_ip = rate_limit_by_ip
    
    return app

# Security middleware for specific routes
def require_auth(f):
    """Require authentication for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'status': 'error',
                'error_code': 'AUTHENTICATION_REQUIRED',
                'message': 'Authentication required'
            }), 401
        
        # Validate JWT token here
        token = auth_header.split(' ')[1]
        # Add JWT validation logic
        
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """Require specific role for access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check user role here
            user_role = getattr(g, 'user_role', None)
            if user_role != required_role:
                return jsonify({
                    'status': 'error',
                    'error_code': 'INSUFFICIENT_PERMISSIONS',
                    'message': 'Insufficient permissions'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(schema):
    """Validate request input against schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Validate request data against schema
                data = request.get_json()
                if not schema.validate(data):
                    return jsonify({
                        'status': 'error',
                        'error_code': 'VALIDATION_ERROR',
                        'message': 'Invalid input data',
                        'errors': schema.errors
                    }), 400
                
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Invalid input data'
                }), 400
        return decorated_function
    return decorator

# Security utilities
class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def sanitize_input(data):
        """Sanitize user input"""
        if isinstance(data, str):
            # Remove potentially dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
            for char in dangerous_chars:
                data = data.replace(char, '')
            return data.strip()
        elif isinstance(data, dict):
            return {k: SecurityUtils.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SecurityUtils.sanitize_input(item) for item in data]
        return data
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        return True, "Password is strong"
    
    @staticmethod
    def generate_csrf_token():
        """Generate CSRF token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token, session_token):
        """Verify CSRF token"""
        return token == session_token

# Security monitoring
class SecurityMonitor:
    """Monitor security events and suspicious activity"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def log_failed_login(self, ip, email):
        """Log failed login attempt"""
        key = f"failed_login:{ip}"
        current = self.redis.get(key)
        
        if current is None:
            self.redis.setex(key, 3600, 1)  # 1 hour window
        else:
            count = int(current) + 1
            self.redis.setex(key, 3600, count)
            
            # Alert if too many failed attempts
            if count >= 5:
                self.alert_suspicious_activity(ip, f"Multiple failed login attempts: {count}")
    
    def log_suspicious_request(self, ip, endpoint, reason):
        """Log suspicious request"""
        key = f"suspicious:{ip}"
        self.redis.lpush(key, f"{time.time()}:{endpoint}:{reason}")
        self.redis.ltrim(key, 0, 99)  # Keep last 100 entries
        self.redis.expire(key, 86400)  # 24 hours
    
    def alert_suspicious_activity(self, ip, reason):
        """Alert on suspicious activity"""
        # Log to security log
        import logging
        security_logger = logging.getLogger('security')
        security_logger.warning(f"Suspicious activity from {ip}: {reason}")
        
        # Send alert (implement based on your alerting system)
        # This could be Slack, email, or other notification system
    
    def check_ip_reputation(self, ip):
        """Check IP reputation (placeholder for actual implementation)"""
        # Implement IP reputation checking
        # This could integrate with services like AbuseIPDB, VirusTotal, etc.
        return True  # Placeholder

# Security configuration
SECURITY_CONFIG = {
    'RATE_LIMITS': {
        'login': '5 per minute',
        'register': '3 per hour',
        'api': '1000 per hour',
        'email_send': '10 per minute',
        'password_reset': '3 per hour'
    },
    'CORS_ORIGINS': [
        'http://localhost:3000',
        'https://fikirisolutions.com',
        'https://www.fikirisolutions.com'
    ],
    'CSP_POLICY': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'connect-src': "'self' https://api.stripe.com",
        'frame-src': "'none'",
        'object-src': "'none'"
    },
    'SECURITY_HEADERS': {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
}

def get_security_config():
    """Get security configuration"""
    return SECURITY_CONFIG
