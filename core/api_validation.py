"""
Backend API Validation and Error Handling
Comprehensive validation system for Fikiri Solutions API endpoints
"""

from flask import request, jsonify
from functools import wraps
import re
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error class"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)

class APIError(Exception):
    """Custom API error class"""
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's a valid length (7-15 digits)
    return 7 <= len(digits) <= 15

def validate_password(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that all required fields are present"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            field=missing_fields[0] if len(missing_fields) == 1 else None,
            code='MISSING_REQUIRED_FIELDS'
        )

def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> None:
    """Validate field types"""
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                raise ValidationError(
                    f"Field '{field}' must be of type {expected_type.__name__}",
                    field=field,
                    code='INVALID_FIELD_TYPE'
                )

def validate_string_length(data: Dict[str, Any], length_limits: Dict[str, Dict[str, int]]) -> None:
    """Validate string field lengths"""
    for field, limits in length_limits.items():
        if field in data and isinstance(data[field], str):
            min_length = limits.get('min', 0)
            max_length = limits.get('max', float('inf'))
            
            if len(data[field]) < min_length:
                raise ValidationError(
                    f"Field '{field}' must be at least {min_length} characters long",
                    field=field,
                    code='FIELD_TOO_SHORT'
                )
            
            if len(data[field]) > max_length:
                raise ValidationError(
                    f"Field '{field}' must be no more than {max_length} characters long",
                    field=field,
                    code='FIELD_TOO_LONG'
                )

def validate_api_request(required_fields: List[str] = None, 
                       field_types: Dict[str, type] = None,
                       length_limits: Dict[str, Dict[str, int]] = None,
                       custom_validators: Dict[str, callable] = None):
    """Decorator for API request validation"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get JSON data from request
                if not request.is_json:
                    raise APIError("Request must be JSON", 400, 'INVALID_CONTENT_TYPE')
                
                data = request.get_json()
                if not data:
                    raise APIError("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
                
                # Validate required fields
                if required_fields:
                    validate_required_fields(data, required_fields)
                
                # Validate field types
                if field_types:
                    validate_field_types(data, field_types)
                
                # Validate string lengths
                if length_limits:
                    validate_string_length(data, length_limits)
                
                # Custom validators
                if custom_validators:
                    for field, validator in custom_validators.items():
                        if field in data:
                            result = validator(data[field])
                            if isinstance(result, dict) and not result.get('valid', True):
                                raise ValidationError(
                                    f"Field '{field}' validation failed: {', '.join(result.get('errors', []))}",
                                    field=field,
                                    code='CUSTOM_VALIDATION_FAILED'
                                )
                
                # Add validated data to kwargs
                kwargs['validated_data'] = data
                
                # Call the original function
                return f(*args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Validation error: {e.message}")
                return jsonify({
                    'success': False,
                    'error': e.message,
                    'field': e.field,
                    'code': e.code,
                    'timestamp': None
                }), 400
            
            except APIError as e:
                logger.error(f"API error: {e.message}")
                return jsonify({
                    'success': False,
                    'error': e.message,
                    'code': e.error_code,
                    'timestamp': None
                }), e.status_code
            
            except Exception as e:
                logger.error(f"Unexpected error in validation: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Internal server error',
                    'code': 'INTERNAL_ERROR',
                    'timestamp': None
                }), 500
        
        return decorated_function
    return decorator

def handle_api_errors(f):
    """Decorator for consistent API error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'field': e.field,
                'code': e.code
            }), 400
        
        except APIError as e:
            logger.error(f"API error: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'code': e.error_code
            }), e.status_code
        
        except Exception as e:
            import traceback
            logger.error(f"Unhandled API error in {f.__name__}: {e}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'code': 'INTERNAL_ERROR'
            }), 500
    
    return decorated_function

# Common validation schemas
LOGIN_SCHEMA = {
    'required_fields': ['email', 'password'],
    'field_types': {'email': str, 'password': str},
    'length_limits': {
        'email': {'min': 1, 'max': 255},
        'password': {'min': 6, 'max': 128}
    },
    'custom_validators': {
        'email': validate_email
    }
}

LEAD_SCHEMA = {
    'required_fields': ['name', 'email'],
    'field_types': {'name': str, 'email': str, 'phone': str, 'company': str, 'notes': str},
    'length_limits': {
        'name': {'min': 1, 'max': 100},
        'email': {'min': 1, 'max': 255},
        'phone': {'min': 0, 'max': 20},
        'company': {'min': 0, 'max': 100},
        'notes': {'min': 0, 'max': 1000}
    },
    'custom_validators': {
        'email': validate_email,
        'phone': lambda x: True if not x else validate_phone(x)
    }
}

CHAT_SCHEMA = {
    'required_fields': ['message'],
    'field_types': {'message': str, 'context': dict},
    'length_limits': {
        'message': {'min': 1, 'max': 2000}
    }
}

def create_success_response(data: Any = None, message: str = "Success") -> tuple:
    """Create a standardized success response"""
    response = {
        'success': True,
        'message': message,
        'timestamp': None
    }
    
    if data is not None:
        response['data'] = data
    
    return jsonify(response), 200

def create_error_response(message: str, status_code: int = 400, error_code: str = None, field: str = None) -> tuple:
    """Create a standardized error response"""
    response = {
        'success': False,
        'error': message,
        'timestamp': None
    }
    
    if error_code:
        response['code'] = error_code
    
    if field:
        response['field'] = field
    
    return jsonify(response), status_code

