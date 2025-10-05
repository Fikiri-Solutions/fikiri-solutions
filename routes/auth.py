#!/usr/bin/env python3
"""
Authentication Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify, redirect, session
from functools import wraps
import time
import logging
from datetime import datetime

# Import our authentication modules
from core.user_auth import user_auth_manager
from core.jwt_auth import jwt_auth_manager, jwt_required
from core.secure_sessions import secure_session_manager
from core.api_validation import validate_api_request, handle_api_errors, create_success_response, create_error_response
from core.rate_limiter import rate_limit
from core.database_optimization import db_optimizer
from core.enterprise_logging import log_security_event
from core.business_operations import business_analytics
from core.email_jobs import email_job_manager

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route('/login', methods=['POST'])
@handle_api_errors
@rate_limit('login_attempts', lambda *args, **kwargs: request.remote_addr)
def api_login():
    """Enhanced login endpoint with security features"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    if 'email' not in data or 'password' not in data:
        return create_error_response("Email and password are required", 400, 'MISSING_FIELDS')

    try:
        # Authenticate user with enhanced validation
        auth_result = user_auth_manager.authenticate_user(
            email=data['email'],
            password=data['password'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        if not auth_result['success']:
            return create_error_response(auth_result['error'], 401, auth_result['error_code'])

        user_profile = auth_result['user']
        jwt_tokens = auth_result['tokens']

        # Convert UserProfile to dict for session creation
        user_data = {
            'id': user_profile.id,
            'email': user_profile.email,
            'name': user_profile.name,
            'role': user_profile.role
        }

        # Create secure session
        session_id, cookie_data = secure_session_manager.create_session(
            user_profile.id,
            user_data,
            request.remote_addr,
            request.headers.get('User-Agent')
        )

        # Log security event for successful login
        log_security_event(
            event_type="user_login",
            severity="info",
            details={
                "user_id": user_profile.id,
                "email": user_profile.email,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent')
            }
        )

        # Track login analytics
        business_analytics.track_event('user_login', {
            'user_id': user_profile.id,
            'email': user_profile.email,
            'login_method': 'email_password'
        })

        # Create response with secure cookie
        response_data = {
            'user': {
                'id': user_profile.id,
                'email': user_profile.email,
                'name': user_profile.name,
                'role': user_profile.role,
                'onboarding_completed': user_profile.onboarding_completed,
                'onboarding_step': user_profile.onboarding_step,
                'last_login': datetime.now().isoformat()
            },
            'tokens': jwt_tokens, 
            'session_id': session_id
        }

        response, status_code = create_success_response(response_data, "Login successful")
        
        # Set secure session cookie
        response.set_cookie(**cookie_data)
        
        return response, status_code

    except Exception as e:
        logger.error(f"Login error: {e}")
        return create_error_response("Login failed. Please try again.", 500, "LOGIN_ERROR")

@auth_bp.route('/signup', methods=['POST'])
@handle_api_errors
@rate_limit('signup_attempts', lambda *args, **kwargs: request.remote_addr)
def api_signup():
    """Simplified signup endpoint without tenant complexity"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')

    try:
        user_result = user_auth_manager.create_user(
            email=data['email'],
            password=data['password'],
            name=data['name'],
            business_name=data.get('business_name', ''),
            business_email=data.get('business_email', data['email']),
            industry=data.get('industry', ''),
            team_size=data.get('team_size', '')
        )

        if not user_result['success']:
            return create_error_response(user_result['error'], 400, user_result['error_code'])

        user = user_result['user']

        user_data = {
            'email': user.email,
            'name': user.name,
            'role': user.role
        }

        tokens = jwt_auth_manager.generate_tokens(
            user.id,
            user_data,
            device_info=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )

        session_id, cookie_data = secure_session_manager.create_session(
            user.id,
            user_data,
            request.remote_addr,
            request.headers.get('User-Agent')
        )

        try:
            log_security_event(
                event_type="user_registration",
                severity="info",
                details={
                    "user_id": user.id,
                    "email": user.email
                }
            )
        except Exception as e:
            logger.warning(f"Security logging failed: {e}")

        try:
            business_analytics.track_event('user_signup', {
                'user_id': user.id,
                'email': user.email,
                'industry': data.get('industry'),
                'team_size': data.get('team_size')
            })
        except Exception as e:
            logger.warning(f"Analytics tracking failed: {e}")

        try:
            email_job_manager.queue_welcome_email(
                user_id=user.id,
                email=user.email,
                name=user.name,
                company_name=data.get('business_name', 'My Company')
            )
        except Exception as e:
            logger.warning(f"Failed to queue welcome email: {e}")

        response_data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'onboarding_completed': False,
                'onboarding_step': 1
            },
            'tokens': tokens,
            'session_id': session_id
        }

        response = create_success_response(response_data, "Account created successfully")
        
        # Set secure session cookie safely
        try:
            if cookie_data and isinstance(cookie_data, dict):
                cookie_name = cookie_data.pop('name', 'fikiri_session')
                response.set_cookie(cookie_name, **cookie_data)
        except Exception as e:
            logger.warning(f"Failed to set session cookie: {e}")
        
        logger.info(f"✅ User registration successful: {user.email}")
        return response
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        logger.error(f"Signup error details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Signup traceback: {traceback.format_exc()}")
        return create_error_response("Registration failed. Please try again.", 500, "SIGNUP_ERROR")

@auth_bp.route('/forgot-password', methods=['POST'])
@handle_api_errors  
@rate_limit('forgot_password_attempts', lambda *args, **kwargs: request.remote_addr)
def api_forgot_password():
    """Handle forgot password requests"""
    data = request.get_json()
    if not data or 'email' not in data:
        return create_error_response("Email is required", 400, 'MISSING_EMAIL')

    try:
        # Always return success to prevent email enumeration
        result = user_auth_manager.request_password_reset(data['email'])
        
        log_security_event(
            event_type="password_reset_requested",
            severity="info", 
            details={"email": data['email'], "ip": request.remote_addr}
        )
        
        return create_success_response({"message": "If an account exists, a reset link has been sent"}, "Password reset requested")
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return create_error_response("Password reset request failed", 500, "PASSWORD_RESET_ERROR")

@auth_bp.route('/reset-password', methods=['POST'])
@handle_api_errors
@rate_limit('reset_password_attempts', lambda *args, **kwargs: request.remote_addr)
def api_reset_password():
    """Handle password reset with token validation"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
    
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return create_error_response("Token and password are required", 400, 'MISSING_FIELDS')
    
    if len(new_password) < 6:
        return create_error_response("Password must be at least 6 characters", 400, 'WEAK_PASSWORD')
    
    # Find user with this reset token
    user_data = db_optimizer.execute_query(
        "SELECT id, email, metadata FROM users WHERE json_extract(metadata, '$.reset_token') = ? AND is_active = 1",
        (token,)
    )
    
    if not user_data:
        return create_error_response("Invalid or expired reset token", 400, 'INVALID_TOKEN')
    
    try:
        # Update user password
        result = user_auth_manager.reset_user_password(user_data[0]['id'], new_password)
        
        if result['success']:
            log_security_event(
                event_type="password_reset_completed",
                severity="info",
                details={"user_id": user_data[0]['id'], "email": user_data[0]['email']}
            )
            return create_success_response({"message": "Password reset successfully"}, "Password updated")
        else:
            return create_error_response(result['error'], 400, result.get('error_code', 'RESET_ERROR'))
            
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return create_error_response("Password reset failed", 500, "RESET_ERROR")

@auth_bp.route('/refresh', methods=['POST'])
@handle_api_errors
def refresh_token():
    """Refresh JWT access token"""
    try:
        # Get current token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return create_error_response("Authorization header missing or invalid", 401, 'MISSING_AUTH_HEADER')
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        # Verify current token
        from core.jwt_auth import jwt_auth_manager
        payload = jwt_auth_manager.verify_access_token(token)
        
        if not payload:
            return create_error_response("Invalid or expired token", 401, 'INVALID_TOKEN')
        
        # Generate new tokens
        user_id = payload['user_id']
        user_data = payload.get('user_data', {})
        
        new_tokens = jwt_auth_manager.generate_tokens(
            user_id=user_id,
            user_data=user_data,
            device_info=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        
        if new_tokens:
            return create_success_response({
                'tokens': new_tokens,
                'user_id': user_id
            }, "Token refreshed successfully")
        else:
            return create_error_response("Failed to generate new token", 500, 'TOKEN_GENERATION_ERROR')
            
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return create_error_response("Failed to refresh token", 500, 'REFRESH_ERROR')

@auth_bp.route('/reset-rate-limit', methods=['POST'])
def reset_rate_limit():
    """Reset rate limit for development/testing purposes"""
    try:
        from core.rate_limiter import enhanced_rate_limiter
        
        # Get IP address
        ip_address = request.remote_addr
        
        # Reset login attempts rate limit
        enhanced_rate_limiter.reset_rate_limit('login_attempts', ip_address, ip_address)
        
        logger.info(f"Rate limit reset for IP: {ip_address}")
        
        return create_success_response("Rate limit reset successfully", {
            'ip_address': ip_address,
            'reset_time': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Rate limit reset error: {e}")
        return create_error_response("Rate limit reset failed", 500, 'RATE_LIMIT_RESET_ERROR')
