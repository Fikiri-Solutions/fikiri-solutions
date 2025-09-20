"""
Structured Error Handling for Fikiri Solutions
Production-ready error management with consistent API responses
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from flask import Flask, request, jsonify, current_app
from werkzeug.exceptions import HTTPException
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import uuid
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fikiri.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class FikiriError(Exception):
    """Base exception class for Fikiri Solutions"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.utcnow().isoformat()
        self.error_id = str(uuid.uuid4())
        
        super().__init__(self.message)

class ValidationError(FikiriError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            user_message=f"Please check your input: {message}"
        )
        self.field = field

class AuthenticationError(FikiriError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details,
            user_message="Please log in to continue"
        )

class AuthorizationError(FikiriError):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details,
            user_message="You don't have permission to perform this action"
        )

class NotFoundError(FikiriError):
    """Raised when a resource is not found"""
    
    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404,
            details=details,
            user_message=f"{resource} not found"
        )

class RateLimitError(FikiriError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            user_message="Too many requests. Please try again later."
        )

class ExternalServiceError(FikiriError):
    """Raised when external service fails"""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service} service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details,
            user_message="External service temporarily unavailable"
        )

class DatabaseError(FikiriError):
    """Raised when database operation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database error: {message}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details,
            user_message="Database operation failed"
        )

class ConfigurationError(FikiriError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Configuration error: {message}",
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details,
            user_message="System configuration error"
        )

def create_error_response(
    error: Union[FikiriError, Exception],
    include_details: bool = False
) -> Dict[str, Any]:
    """Create a standardized error response"""
    
    if isinstance(error, FikiriError):
        response = {
            "status": "error",
            "error_code": error.error_code,
            "message": error.user_message,
            "timestamp": error.timestamp,
            "error_id": error.error_id
        }
        
        if include_details and error.details:
            response["details"] = error.details
            
    elif isinstance(error, HTTPException):
        response = {
            "status": "error",
            "error_code": "HTTP_ERROR",
            "message": error.description or "HTTP error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "error_id": str(uuid.uuid4())
        }
        
    else:
        # Generic error
        response = {
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "error_id": str(uuid.uuid4())
        }
        
        if include_details:
            response["details"] = {
                "type": type(error).__name__,
                "message": str(error)
            }
    
    return response

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context information"""
    
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "request_id": getattr(request, 'id', None),
        "user_id": getattr(request, 'user_id', None),
        "endpoint": request.endpoint if request else None,
        "method": request.method if request else None,
        "url": request.url if request else None,
        "user_agent": request.headers.get('User-Agent') if request else None,
        "ip_address": request.remote_addr if request else None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if context:
        error_context.update(context)
    
    # Log to application logs
    logger.error(f"Error occurred: {error_context}")
    
    # Log to Sentry if configured
    if os.getenv('SENTRY_DSN'):
        with sentry_sdk.push_scope() as scope:
            for key, value in error_context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)

def handle_error(error: Exception) -> tuple:
    """Handle errors and return appropriate response"""
    
    # Log the error
    log_error(error)
    
    # Determine if we should include details
    include_details = current_app.debug or os.getenv('FLASK_ENV') == 'development'
    
    # Create error response
    response = create_error_response(error, include_details)
    
    # Determine status code
    if isinstance(error, FikiriError):
        status_code = error.status_code
    elif isinstance(error, HTTPException):
        status_code = error.code
    else:
        status_code = 500
    
    return jsonify(response), status_code

def init_error_handlers(app: Flask):
    """Initialize error handlers for Flask app"""
    
    @app.errorhandler(FikiriError)
    def handle_fikiri_error(error: FikiriError):
        return handle_error(error)
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return handle_error(error)
    
    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception):
        return handle_error(error)
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return handle_error(NotFoundError("Endpoint"))
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return handle_error(FikiriError(
            message="Method not allowed",
            error_code="METHOD_NOT_ALLOWED",
            status_code=405,
            user_message="This method is not allowed for this endpoint"
        ))
    
    @app.errorhandler(413)
    def handle_payload_too_large(error):
        return handle_error(FikiriError(
            message="Payload too large",
            error_code="PAYLOAD_TOO_LARGE",
            status_code=413,
            user_message="Request payload is too large"
        ))
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        return handle_error(RateLimitError())

def init_sentry(app: Flask):
    """Initialize Sentry for error tracking"""
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration()
            ],
            environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
            release=os.getenv('SENTRY_RELEASE', '1.0.0'),
            traces_sample_rate=0.1,
            send_default_pii=False
        )
        
        logger.info("Sentry initialized for error tracking")

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present in data"""
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )

def validate_email(email: str) -> None:
    """Validate email format"""
    
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValidationError(
            message="Invalid email format",
            field="email",
            details={"email": email}
        )

def validate_password_strength(password: str) -> None:
    """Validate password strength"""
    
    if len(password) < 8:
        raise ValidationError(
            message="Password must be at least 8 characters long",
            field="password"
        )
    
    if not any(c.isupper() for c in password):
        raise ValidationError(
            message="Password must contain at least one uppercase letter",
            field="password"
        )
    
    if not any(c.islower() for c in password):
        raise ValidationError(
            message="Password must contain at least one lowercase letter",
            field="password"
        )
    
    if not any(c.isdigit() for c in password):
        raise ValidationError(
            message="Password must contain at least one number",
            field="password"
        )

# Context manager for error handling
class ErrorContext:
    """Context manager for handling errors in specific operations"""
    
    def __init__(self, operation: str, context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.context = context or {}
        self.start_time = datetime.utcnow()
    
    def __enter__(self):
        logger.info(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            error_context = {
                "operation": self.operation,
                "duration": duration,
                **self.context
            }
            log_error(exc_val, error_context)
            return False  # Don't suppress the exception
        else:
            logger.info(f"Completed operation: {self.operation} in {duration:.2f}s")

# Decorator for error handling
def handle_errors(operation: str = None):
    """Decorator for handling errors in functions"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            with ErrorContext(op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Success response helper
def create_success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
) -> tuple:
    """Create a standardized success response"""
    
    response = {
        "status": "success",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    
    return jsonify(response), status_code
