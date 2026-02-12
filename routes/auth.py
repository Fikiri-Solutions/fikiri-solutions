#!/usr/bin/env python3
"""
Authentication Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify, redirect, session
from functools import wraps
import time
import logging
import os
from datetime import datetime

# Import our authentication modules
from core.user_auth import user_auth_manager
from core.jwt_auth import jwt_auth_manager, jwt_required
from core.secure_sessions import secure_session_manager
from core.api_validation import validate_api_request, handle_api_errors, create_success_response, create_error_response
from core.rate_limiter import rate_limit
from core.database_optimization import db_optimizer
from core.enterprise_logging import log_security_event
from services.business_operations import business_analytics
from email_automation.jobs import email_job_manager

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

    auth_result = user_auth_manager.authenticate_user(
        email=data['email'],
        password=data['password'],
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    if not auth_result['success']:
        return create_error_response(auth_result['error'], 401, auth_result['error_code'])

    user_obj = auth_result['user']
    jwt_tokens = auth_result.get('tokens')
    user_dict = user_obj.__dict__ if hasattr(user_obj, '__dict__') else user_obj

    user_data = {
        'id': user_dict.get('id'),
        'email': user_dict.get('email'),
        'name': user_dict.get('name'),
        'role': user_dict.get('role', 'user')
    }

    session_id, cookie_data = secure_session_manager.create_session(
        user_data['id'], user_data, request.remote_addr, request.headers.get('User-Agent')
    )

    log_security_event("user_login", "info", {
        "user_id": user_data['id'],
        "email": user_data['email'],
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get('User-Agent')
    })

    business_analytics.track_event('user_login', {
        'user_id': user_data['id'],
        'email': user_data['email'],
        'login_method': 'email_password'
    })

    response_data = {
        'user': {
            'id': user_data['id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'role': user_data['role'],
            'onboarding_completed': user_dict.get('onboarding_completed', False),
            'onboarding_step': user_dict.get('onboarding_step', 1),
            'last_login': datetime.now().isoformat()
        },
        'access_token': jwt_tokens['access_token'] if jwt_tokens else None,
        'expires_in': jwt_tokens['expires_in'] if jwt_tokens else None,
        'token_type': 'Bearer'
    }

    response, status_code = create_success_response(response_data, "Login successful")
    response.set_cookie(**cookie_data)
    return response, status_code

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

        user_obj = user_result['user']
        user_dict = user_obj.__dict__ if hasattr(user_obj, '__dict__') else user_obj

        user_data = {
            'id': user_dict.get('id'),
            'email': user_dict.get('email'),
            'name': user_dict.get('name'),
            'role': user_dict.get('role', 'user')
        }

        tokens = jwt_auth_manager.generate_tokens(
            user_data['id'],
            user_data,
            device_info=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )

        session_id, cookie_data = secure_session_manager.create_session(
            user_data['id'],
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
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data['role'],
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
        
        logger.info(f"✅ User registration successful: {user_data['email']}")
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

@auth_bp.route('/gmail/status', methods=['GET'])
@handle_api_errors
def api_gmail_status():
    """Get Gmail connection status for a user"""
    try:
        # Try to get user_id from session/JWT first
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        
        # Fallback: allow user_id from query parameter for development/testing
        if not user_id:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_error_response("User ID is required", 400, 'MISSING_USER_ID')
        
        # Check Gmail token status - check gmail_tokens table (where tokens are actually stored)
        try:
            # First try to check gmail_tokens table (used by app_oauth.py)
            gmail_token_check = db_optimizer.execute_query("""
                SELECT id, user_id, access_token_enc, refresh_token_enc, 
                       expiry_timestamp, scopes_json, created_at, updated_at
                FROM gmail_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if gmail_token_check and len(gmail_token_check) > 0:
                token_row = gmail_token_check[0]
                
                # Handle both dict and tuple result formats
                if isinstance(token_row, dict):
                    access_token_enc = token_row.get('access_token_enc')
                    access_token = token_row.get('access_token')
                    expiry_timestamp = token_row.get('expiry_timestamp')
                    scopes_json = token_row.get('scopes_json')
                    updated_at = token_row.get('updated_at')
                else:
                    # Tuple format - assume order: id, user_id, access_token_enc, refresh_token_enc, expiry_timestamp, scopes_json, created_at, updated_at
                    access_token_enc = token_row[2] if len(token_row) > 2 else None
                    access_token = token_row[3] if len(token_row) > 3 else None
                    expiry_timestamp = token_row[4] if len(token_row) > 4 else None
                    scopes_json = token_row[5] if len(token_row) > 5 else None
                    updated_at = token_row[7] if len(token_row) > 7 else None
                
                # Check if token exists (even if encrypted)
                has_token = bool(access_token_enc or access_token)
                
                if has_token:
                    # Parse scopes
                    scopes = []
                    if scopes_json:
                        try:
                            import json
                            scopes = json.loads(scopes_json)
                        except:
                            pass
                    
                    # Check if expired
                    is_expired = False
                    if expiry_timestamp:
                        try:
                            expiry_time = int(expiry_timestamp)
                            is_expired = time.time() >= expiry_time
                        except:
                            pass
                    
                    return create_success_response({
                        'connected': True,
                        'status': 'active' if not is_expired else 'expired',
                        'expires_at': expiry_timestamp,
                        'last_refresh_at': updated_at,
                        'scopes': scopes,
                        'is_expired': is_expired
                    }, 'Gmail connection status retrieved')
            
            # If no token in gmail_tokens, check oauth_tokens table as fallback
            from core.oauth_token_manager import oauth_token_manager
            result = oauth_token_manager.get_token_status(user_id, 'gmail')
            
            if result['success']:
                token_data = result.get('data', {})
                return create_success_response({
                    'connected': True,
                    'status': token_data.get('status', 'active'),
                    'expires_at': token_data.get('expires_at'),
                    'last_refresh_at': token_data.get('last_refresh_at'),
                    'scopes': token_data.get('scope', []),
                    'is_expired': token_data.get('is_expired', False)
                }, 'Gmail connection status retrieved')
            else:
                return create_success_response({
                    'connected': False,
                    'status': 'not_connected',
                    'error': result.get('error', 'No active connection')
                }, 'Gmail connection status retrieved')
                
        except Exception as check_error:
            logger.warning(f"Error checking gmail_tokens table: {check_error}")
            # Fallback to oauth_token_manager
            from core.oauth_token_manager import oauth_token_manager
            result = oauth_token_manager.get_token_status(user_id, 'gmail')
            
            if result['success']:
                token_data = result.get('data', {})
                return create_success_response({
                    'connected': True,
                    'status': token_data.get('status', 'active'),
                    'expires_at': token_data.get('expires_at'),
                    'last_refresh_at': token_data.get('last_refresh_at'),
                    'scopes': token_data.get('scope', []),
                    'is_expired': token_data.get('is_expired', False)
                }, 'Gmail connection status retrieved')
            else:
                return create_success_response({
                    'connected': False,
                    'status': 'not_connected',
                    'error': result.get('error', 'No active connection')
                }, 'Gmail connection status retrieved')
            
    except Exception as e:
        logger.error(f"Gmail status error: {e}")
        return create_error_response("Failed to get Gmail status", 500, 'GMAIL_STATUS_ERROR')

@auth_bp.route('/outlook/status', methods=['GET'])
@handle_api_errors  
def api_outlook_status():
    """Get Outlook connection status for a user"""
    try:
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        
        # Fallback: allow user_id from query parameter for development/testing
        if not user_id:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_success_response({
                    'connected': False,
                    'status': 'not_connected',
                    'error': 'User ID required'
                }, 'Outlook connection status retrieved')
        
        # Check outlook_tokens table
        try:
            outlook_token_check = db_optimizer.execute_query("""
                SELECT access_token_enc, access_token, is_active, expiry_timestamp, scopes_json, tenant_id, updated_at
                FROM outlook_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if outlook_token_check and len(outlook_token_check) > 0:
                token_row = outlook_token_check[0]
                
                # Handle both dict and tuple result formats
                if isinstance(token_row, dict):
                    access_token_enc = token_row.get('access_token_enc')
                    access_token = token_row.get('access_token')
                    expiry_timestamp = token_row.get('expiry_timestamp')
                    scopes_json = token_row.get('scopes_json')
                    tenant_id = token_row.get('tenant_id')
                else:
                    access_token_enc = token_row[0] if len(token_row) > 0 else None
                    access_token = token_row[1] if len(token_row) > 1 else None
                    expiry_timestamp = token_row[3] if len(token_row) > 3 else None
                    scopes_json = token_row[4] if len(token_row) > 4 else None
                    tenant_id = token_row[5] if len(token_row) > 5 else None
                
                has_token = bool(access_token_enc or access_token)
                
                if has_token:
                    # Parse scopes
                    scopes = []
                    if scopes_json:
                        try:
                            import json
                            scopes = json.loads(scopes_json) if isinstance(scopes_json, str) else scopes_json
                        except:
                            pass
                    
                    # Check if expired
                    is_expired = False
                    if expiry_timestamp:
                        try:
                            expiry_time = int(expiry_timestamp)
                            is_expired = time.time() >= expiry_time
                        except:
                            pass
                    
                    updated_at = token_row.get('updated_at') if isinstance(token_row, dict) else (token_row[6] if len(token_row) > 6 else None)
                    
                    return create_success_response({
                        'connected': True,
                        'status': 'active' if not is_expired else 'expired',
                        'expires_at': expiry_timestamp,
                        'last_refresh_at': updated_at,
                        'scopes': scopes,
                        'tenant_id': tenant_id,
                        'is_expired': is_expired
                    }, 'Outlook connection status retrieved')
        
        except Exception as check_error:
            logger.warning(f"Error checking outlook_tokens table: {check_error}")
        
        # Not connected
        return create_success_response({
            'connected': False,
            'status': 'not_connected',
            'error': 'No active Outlook connection'
        }, 'Outlook connection status retrieved')
            
    except Exception as e:
        logger.error(f"Outlook status error: {e}")
        import traceback
        logger.error(f"Outlook status traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to get Outlook status: {str(e)}", 500, 'OUTLOOK_STATUS_ERROR')

@auth_bp.route('/gmail/disconnect', methods=['POST'])
@handle_api_errors
def api_gmail_disconnect():
    """Disconnect Gmail account"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        # Try to get user_id from session/JWT if not provided
        if not user_id:
            from core.secure_sessions import get_current_user_id
            user_id = get_current_user_id()
        
        if not user_id:
            return create_error_response("User ID is required", 400, 'MISSING_USER_ID')
        
        # First, try to revoke tokens from gmail_tokens table (where tokens are actually stored)
        try:
            # Get access token for revocation
            gmail_token_check = db_optimizer.execute_query("""
                SELECT access_token, access_token_enc, refresh_token_enc
                FROM gmail_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if gmail_token_check and len(gmail_token_check) > 0:
                token_row = gmail_token_check[0]
                access_token = token_row.get('access_token')
                
                # If we have an access token, try to revoke it with Google
                if access_token:
                    try:
                        import requests
                        revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
                        requests.post(revoke_url, timeout=10)
                        logger.info(f"Revoked Gmail token for user {user_id} with Google")
                    except Exception as revoke_error:
                        logger.warning(f"Failed to revoke token with Google (continuing anyway): {revoke_error}")
                
                # Mark tokens as inactive in gmail_tokens table
                db_optimizer.execute_query("""
                    UPDATE gmail_tokens 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_active = TRUE
                """, (user_id,), fetch=False)
                logger.info(f"Deactivated Gmail tokens for user {user_id} in gmail_tokens table")
        except Exception as gmail_token_error:
            logger.warning(f"Error disconnecting from gmail_tokens table: {gmail_token_error}")
        
        # Also try to revoke from oauth_tokens table (fallback)
        try:
            from core.oauth_token_manager import oauth_token_manager
            oauth_token_manager.revoke_tokens(user_id, 'gmail')
        except Exception as oauth_error:
            logger.warning(f"Error revoking from oauth_tokens table: {oauth_error}")
        
        return create_success_response({
            'disconnected': True,
            'message': 'Gmail account disconnected successfully'
        }, 'Gmail disconnected')
            
    except Exception as e:
        logger.error(f"Gmail disconnect error: {e}")
        import traceback
        logger.error(f"Gmail disconnect traceback: {traceback.format_exc()}")
        return create_error_response("Failed to disconnect Gmail", 500, 'GMAIL_DISCONNECT_ERROR')

@auth_bp.route('/outlook/disconnect', methods=['POST'])
@handle_api_errors
def api_outlook_disconnect():
    """Disconnect Outlook account"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        # Try to get user_id from session/JWT if not provided
        if not user_id:
            from core.secure_sessions import get_current_user_id
            user_id = get_current_user_id()
        
        if not user_id:
            return create_error_response("User ID is required", 400, 'MISSING_USER_ID')
        
        # Get access token for revocation
        try:
            outlook_token_check = db_optimizer.execute_query("""
                SELECT access_token, access_token_enc, refresh_token_enc, tenant_id
                FROM outlook_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if outlook_token_check and len(outlook_token_check) > 0:
                token_row = outlook_token_check[0]
                access_token = token_row.get('access_token')
                tenant_id = token_row.get('tenant_id')
                
                # If we have an access token, try to revoke it with Microsoft
                if access_token:
                    try:
                        import requests
                        # Microsoft Graph API token revocation endpoint
                        revoke_url = f"https://login.microsoftonline.com/{tenant_id or 'common'}/oauth2/v2.0/logout"
                        # Note: Microsoft doesn't have a direct revoke endpoint like Google
                        # The logout endpoint clears the session, but we still need to mark tokens inactive
                        requests.get(revoke_url, timeout=10)
                        logger.info(f"Attempted to revoke Outlook token for user {user_id} with Microsoft")
                    except Exception as revoke_error:
                        logger.warning(f"Failed to revoke token with Microsoft (continuing anyway): {revoke_error}")
                
                # Mark tokens as inactive in outlook_tokens table
                db_optimizer.execute_query("""
                    UPDATE outlook_tokens 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_active = TRUE
                """, (user_id,), fetch=False)
                logger.info(f"Deactivated Outlook tokens for user {user_id} in outlook_tokens table")
        except Exception as outlook_token_error:
            logger.warning(f"Error disconnecting from outlook_tokens table: {outlook_token_error}")
        
        # Also try to revoke from oauth_token_manager (fallback)
        try:
            from core.oauth_token_manager import oauth_token_manager
            oauth_token_manager.revoke_tokens(user_id, 'outlook')
        except Exception as oauth_error:
            logger.warning(f"Error revoking from oauth_token_manager: {oauth_error}")
        
        return create_success_response({
            'disconnected': True,
            'message': 'Outlook account disconnected successfully'
        }, 'Outlook disconnected')
            
    except Exception as e:
        logger.error(f"Outlook disconnect error: {e}")
        import traceback
        logger.error(f"Outlook disconnect traceback: {traceback.format_exc()}")
        return create_error_response("Failed to disconnect Outlook", 500, 'OUTLOOK_DISCONNECT_ERROR')

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
def api_logout():
    """User logout endpoint - clears session and cookies"""
    # Handle CORS preflight - must return 200 OK for preflight to pass
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        origin = request.headers.get('Origin')
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
        else:
            # Allow localhost origins for development
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5174')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response, 200
    
    try:
        # Get session ID from cookie or request
        session_id = session.get('session_id') or request.cookies.get('fikiri_session')
        
        # Revoke session if it exists
        if session_id:
            try:
                secure_session_manager.delete_session(session_id)
            except Exception as e:
                logger.warning(f"Session deletion warning: {e}")
        
        # Clear Flask session
        session.clear()
        
        # Log security event
        try:
            log_security_event(
                event_type="user_logout",
                severity="info",
                details={"session_id": session_id, "ip_address": request.remote_addr}
            )
        except Exception as e:
            logger.warning(f"Security logging failed: {e}")
        
        # Create response
        response_data = {'success': True, 'message': 'Logged out successfully'}
        response, status_code = create_success_response(response_data, "Logout successful")
        
        # Clear cookies by setting them to expire
        response.set_cookie(
            'fikiri_session',
            '',
            expires=0,
            httponly=True,
            secure=os.getenv('FLASK_ENV') == 'production',
            samesite='Lax',
            path='/'
        )
        response.set_cookie(
            'fikiri_refresh_token',
            '',
            expires=0,
            httponly=True,
            secure=os.getenv('FLASK_ENV') == 'production',
            samesite='Lax',
            path='/'
        )
        
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        logger.info(f"✅ User logged out successfully")
        return response, status_code
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        import traceback
        logger.error(f"Logout traceback: {traceback.format_exc()}")
        # Even if there's an error, try to clear cookies
        response = jsonify({'success': False, 'error': str(e)})
        response.set_cookie('fikiri_session', '', expires=0)
        response.set_cookie('fikiri_refresh_token', '', expires=0)
        # Add CORS headers even on error
        origin = request.headers.get('Origin')
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 500

@auth_bp.route('/whoami', methods=['GET'])
@handle_api_errors
def api_whoami():
    """Debug endpoint to check authentication state"""
    try:
        # Check session cookie
        session_id = request.cookies.get('fikiri_session')
        session_data = None
        
        if session_id:
            from core.secure_sessions import secure_session_manager
            session_data = secure_session_manager.get_session(session_id)
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        token_data = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            from core.jwt_auth import get_jwt_manager
            jwt_manager = get_jwt_manager()
            token_data = jwt_manager.verify_access_token(token)
        
        # Get user data if authenticated
        user_data = None
        if session_data:
            user_data = session_data.get('user_data', {})
        elif token_data and 'error' not in token_data:
            # Get user from database
            user_id = token_data.get('user_id')
            if user_id:
                from core.database_optimization import db_optimizer
                users = db_optimizer.execute_query(
                    "SELECT id, email, name, role, onboarding_completed, onboarding_step FROM users WHERE id = ?",
                    (user_id,)
                )
                if users:
                    user_data = users[0]
        
        response_data = {
            'authenticated': bool(user_data),
            'user': user_data,
            'session_exists': bool(session_data),
            'token_valid': bool(token_data and 'error' not in token_data),
            'cookies': {
                'fikiri_session': bool(session_id),
                'fikiri_refresh_token': bool(request.cookies.get('fikiri_refresh_token'))
            },
            'headers': {
                'authorization': bool(auth_header),
                'origin': request.headers.get('Origin'),
                'user_agent': request.headers.get('User-Agent')
            }
        }
        
        return create_success_response(response_data, "Authentication state")
        
    except Exception as e:
        logger.error(f"Whoami error: {e}")
        return create_error_response("Debug check failed", 500, "DEBUG_ERROR")
