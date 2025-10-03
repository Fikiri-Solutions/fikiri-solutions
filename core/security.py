"""
Security Configuration for Fikiri Solutions
Production-ready security headers, rate limiting, and CORS
"""

import os
import time
from functools import wraps
from typing import Dict, Any, Optional

# Optional imports with fallbacks
try:
    from flask import Flask, request, jsonify, g
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from werkzeug.middleware.proxy_fix import ProxyFix
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Warning: Flask not available. Install with: pip install flask flask-cors flask-limiter")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: Redis not available. Install with: pip install redis")

def init_security(app: Flask):
    """Initialize security middleware and configurations"""
    
    # Trust proxy headers (for rate limiting behind reverse proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Initialize Redis for rate limiting
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    # Initialize rate limiter (fixed - use single initialization style)
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        default_limits=["1000 per hour", "100 per minute"]
    )
    limiter.init_app(app)
    
    # Configure CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, 
         origins=cors_origins,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         supports_credentials=True,
         max_age=3600
    )
    
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
