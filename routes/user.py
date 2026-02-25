#!/usr/bin/env python3
"""
User Management Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime

# Import user management modules
from core.user_auth import user_auth_manager
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.jwt_auth import jwt_required, get_current_user
from core.automation_safety import automation_safety_manager
from core.database_optimization import db_optimizer
from core.api_key_manager import api_key_manager
from core.activity_logger import log_activity_event

logger = logging.getLogger(__name__)

# Create user blueprint
user_bp = Blueprint("user", __name__, url_prefix="/api")

@user_bp.route('/user/profile', methods=['GET'])
@handle_api_errors
@jwt_required
def get_user_profile():
    """Get user profile information"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']
        
        # Get user profile directly from database
        # Rulepack compliance: specific columns, not SELECT *
        user_data_db = db_optimizer.execute_query(
            "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        )
        
        if not user_data_db:
            return create_error_response("User not found", 404, 'USER_NOT_FOUND')
        
        user = user_data_db[0]
        # Handle SQLite Row objects by converting to dict
        if hasattr(user, 'keys'):
            user_dict = dict(user)
        else:
            user_dict = user
        
        metadata = json.loads(user_dict.get('metadata', '{}'))
        
        out = {
            'id': user_dict.get('id'),
            'email': user_dict.get('email'),
            'name': user_dict.get('name'),
            'role': user_dict.get('role', 'user'),
            'onboarding_completed': user_dict.get('onboarding_completed', False),
            'onboarding_step': user_dict.get('onboarding_step', 0),
            'business_name': user_dict.get('business_name'),
            'business_email': user_dict.get('business_email'),
            'industry': user_dict.get('industry'),
            'team_size': user_dict.get('team_size'),
            'created_at': user_dict.get('created_at'),
            'last_login': user_dict.get('last_login'),
        }
        if isinstance(metadata, dict):
            out['phone'] = metadata.get('phone') or None
            out['sms_consent'] = bool(metadata.get('sms_consent'))
            out['sms_consent_at'] = metadata.get('sms_consent_at')
        
        return create_success_response({
            'user': out
        }, "User profile retrieved")
        
    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        return create_error_response("Failed to get user profile", 500, 'PROFILE_ERROR')

@user_bp.route('/user/profile', methods=['PUT'])
@handle_api_errors
def update_user_profile():
    """Update user profile information"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Validate allowed fields
        allowed_fields = ['name', 'business_name', 'business_email', 'industry', 'team_size', 'phone', 'sms_consent']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        metadata_updates = {}
        if 'phone' in update_data:
            metadata_updates['phone'] = (update_data.pop('phone') or '').strip() or None
        if 'sms_consent' in update_data:
            metadata_updates['sms_consent'] = bool(update_data.get('sms_consent'))
            metadata_updates['sms_consent_at'] = datetime.utcnow().isoformat() + 'Z' if metadata_updates['sms_consent'] else None
            update_data.pop('sms_consent')

        if not update_data and not metadata_updates:
            return create_error_response("No valid fields to update", 400, 'NO_VALID_FIELDS')

        # Update user profile (columns + metadata)
        result = user_auth_manager.update_user_profile(
            user_id,
            metadata_updates=metadata_updates if metadata_updates else None,
            **update_data
        )
        
        if result['success']:
            log_activity_event(
                user_id,
                'profile_updated',
                message="Profile settings updated",
                metadata={'fields': list(update_data.keys()) + (list(metadata_updates.keys()) if metadata_updates else [])},
                request=request
            )
            u = result['user']
            meta = getattr(u, 'metadata', None) or {}
            user_payload = {
                'id': u.id,
                'email': u.email,
                'name': u.name,
                'role': getattr(u, 'role', 'user'),
                'business_name': getattr(u, 'business_name', None),
                'business_email': getattr(u, 'business_email', None),
                'industry': getattr(u, 'industry', None),
                'team_size': getattr(u, 'team_size', None),
                'onboarding_completed': getattr(u, 'onboarding_completed', False),
                'onboarding_step': getattr(u, 'onboarding_step', 0),
                'created_at': u.created_at.isoformat() if hasattr(u.created_at, 'isoformat') else str(u.created_at),
                'last_login': getattr(u, 'last_login', None),
                'phone': meta.get('phone'),
                'sms_consent': bool(meta.get('sms_consent')),
                'sms_consent_at': meta.get('sms_consent_at'),
            }
            return create_success_response(
                {'user': user_payload},
                'Profile updated successfully'
            )
        else:
            return create_error_response(result['error'], 400, result.get('error_code', 'PROFILE_UPDATE_ERROR'))
            
    except Exception as e:
        logger.error(f"Update user profile error: {e}")
        return create_error_response("Failed to update profile", 500, 'PROFILE_UPDATE_ERROR')

@user_bp.route('/user/onboarding-step', methods=['PUT'])
@handle_api_errors
@jwt_required
def update_onboarding_step():
    """Update user onboarding step"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data or 'step' not in data:
            return create_error_response("Step number is required", 400, 'MISSING_STEP')

        step = data['step']
        if not isinstance(step, int) or step < 1 or step > 4:
            return create_error_response("Invalid step number", 400, 'INVALID_STEP')

        # Update onboarding step
        query = """
            UPDATE users 
            SET onboarding_step = ?, onboarding_completed = ?
            WHERE id = ? AND is_active = 1
        """
        
        onboarding_completed = step >= 4
        
        db_optimizer.execute_query(query, (step, onboarding_completed, user_id))
        
        logger.info(f"✅ User {user_id} updated onboarding step to {step}")
        
        return create_success_response({
            'step': step,
            'onboarding_completed': onboarding_completed,
            'next_step': step + 1 if step < 4 else None
        }, 'Onboarding step updated successfully')
        
    except Exception as e:
        logger.error(f"Update onboarding step error: {e}")
        return create_error_response("Failed to update onboarding step", 500, 'ONBOARDING_UPDATE_ERROR')

@user_bp.route('/user/gmail-connect-status', methods=['GET'])
@handle_api_errors  
def get_gmail_connect_status():
    """Get Gmail connection status for user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Check OAuth token status
        from core.oauth_token_manager import oauth_token_manager
        
        result = oauth_token_manager.get_token_status(user_id, 'gmail')
        
        if result['success']:
            return create_success_response({
                'connected': True,
                'status': 'active',
                'last_sync': result.get('last_sync'),
                'expires_at': result.get('expires_at')
            }, 'Gmail connection status retrieved')
        else:
            return create_success_response({
                'connected': False,
                'status': 'not_connected',
                'error': result.get('error', 'No active connection')
            }, 'Gmail connection status retrieved')
            
    except Exception as e:
        logger.error(f"Gmail connect status error: {e}")
        return create_error_response("Failed to get Gmail connection status", 500, 'GMAIL_STATUS_ERROR')

@user_bp.route('/user/automation-status', methods=['GET'])
@handle_api_errors
def get_automation_status():
    """Get automation configuration status for user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Get automation safety status
        safety_status = automation_safety_manager.get_safety_status(user_id)
        
        return create_success_response({
            'automation_enabled': safety_status.get('automation_enabled', True),
            'safety_level': safety_status.get('safety_level', 'normal'),
            'restrictions': safety_status.get('restrictions', []),
            'last_updated': safety_status.get('last_updated')
        }, 'Automation status retrieved successfully')
        
    except Exception as e:
        logger.error(f"Automation status error: {e}")
        return create_error_response("Failed to get automation status", 500, 'AUTOMATION_STATUS_ERROR')

@user_bp.route('/user/api-keys', methods=['GET'])
@handle_api_errors
def list_user_api_keys():
    """List API keys for the current user (metadata only)."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        keys = api_key_manager.list_api_keys(user_id)
        return create_success_response({'keys': keys}, 'API keys retrieved successfully')
    except Exception as e:
        logger.error(f"List API keys error: {e}")
        return create_error_response("Failed to list API keys", 500, 'API_KEYS_ERROR')

@user_bp.route('/user/api-keys', methods=['POST'])
@handle_api_errors
def create_user_api_key():
    """Create a new API key for the current user (returns full key once)."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json(silent=True) or {}
        name = (data.get('name') or 'Install Page Key').strip()
        description = (data.get('description') or 'Generated for SDK install flow').strip()
        scopes = data.get('scopes') or ["chatbot:query", "webhooks:forms", "webhooks:leads", "leads:create"]
        allowed_origins = data.get('allowed_origins')

        # Normalize allowed_origins to list if provided as string
        if isinstance(allowed_origins, str):
            allowed_origins = [allowed_origins]

        result = api_key_manager.generate_api_key(
            user_id=user_id,
            name=name,
            description=description,
            tenant_id=str(user_id),
            scopes=scopes,
            allowed_origins=allowed_origins
        )

        log_activity_event(
            user_id,
            'api_key_created',
            message="API key created",
            metadata={'key_id': (result.get('key_info') or {}).get('id'), 'name': name},
            request=request
        )
        return create_success_response(
            {
                'api_key': result.get('api_key'),
                'key_info': result.get('key_info')
            },
            'API key created successfully'
        )
    except Exception as e:
        logger.error(f"Create API key error: {e}")
        return create_error_response("Failed to create API key", 500, 'API_KEY_CREATE_ERROR')

@user_bp.route('/user/dashboard-data', methods=['GET'])
@handle_api_errors
def get_dashboard_data():
    """Get aggregated dashboard data for user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Get various data for dashboard
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'greeting': f"Welcome back!",
            'quick_stats': {}
        }

        try:
            # Get CRM stats
            from crm.service import enhanced_crm_service
            leads = enhanced_crm_service.get_leads(user_id)
            dashboard_data['quick_stats']['total_leads'] = len(leads or [])
            
        except Exception as e:
            logger.warning(f"Could not fetch CRM stats: {e}")
            dashboard_data['quick_stats']['total_leads'] = 0

        try:
            # Get automation stats
            from core.oauth_token_manager import oauth_token_manager
            gmail_status = oauth_token_manager.get_token_status(user_id, 'gmail')
            dashboard_data['quick_stats']['gmail_connected'] = gmail_status['success']
            
        except Exception as e:
            logger.warning(f"Could not fetch Gmail status: {e}")
            dashboard_data['quick_stats']['gmail_connected'] = False

        # Get user onboarding status
        user_profile = user_auth_manager.get_user_profile(user_id)
        dashboard_data['user_info'] = {
            'name': user_profile.get('name', 'User'),
            'onboarding_completed': user_profile.get('onboarding_completed', False),
            'onboarding_step': user_profile.get('onboarding_step', 1)
        }

        return create_success_response(dashboard_data, 'Dashboard data retrieved successfully')
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return create_error_response("Failed to get dashboard data", 500, 'DASHBOARD_DATA_ERROR')

@user_bp.route('/user/export-data', methods=['POST'])
@handle_api_errors
def export_user_data():
    """Export user's data for GDPR compliance"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Create data export package
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'user_data': {},
            'export_status': 'success'
        }

        try:
            # Get user profile
            user_profile = user_auth_manager.get_user_profile(user_id)
            export_data['user_data']['profile'] = user_profile
            
        except Exception as e:
            logger.warning(f"Could not export user profile: {e}")
            export_data['user_data']['profile'] = None

        try:
            # Get CRM data
            from crm.service import enhanced_crm_service
            leads = enhanced_crm_service.get_leads(user_id)
            export_data['user_data']['leads'] = leads
            
        except Exception as e:
            logger.warning(f"Could not export CRM data: {e}")
            export_data['user_data']['leads'] = []

        export_data['export_status'] = 'completed'
        
        return create_success_response(export_data, 'User data export completed')
        
    except Exception as e:
        logger.error(f"Data export error: {e}")
        return create_error_response("Failed to export user data", 500, 'DATA_EXPORT_ERROR')
