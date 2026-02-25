"""
Onboarding endpoint for saving user onboarding information
"""
import logging
from flask import Blueprint, request, jsonify
from core.secure_sessions import get_current_user_id
from core.jwt_auth import jwt_required, get_current_user
from core.database_optimization import db_optimizer
from core.api_validation import create_success_response, create_error_response, handle_api_errors

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("onboarding", __name__)

@bp.route("/api/onboarding", methods=["POST"])
@handle_api_errors
@jwt_required
def save_onboarding():
    """Save user onboarding information"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']

        # Parse request data
        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_BODY')

        name = data.get("name", "").strip()
        company = data.get("company", "").strip()
        industry = data.get("industry", "").strip()

        # Validate required fields
        if not name:
            return create_error_response("Name is required", 400, 'MISSING_NAME')
        if not company:
            return create_error_response("Company name is required", 400, 'MISSING_COMPANY')

        # Use global database optimizer

        # Create onboarding_info table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS onboarding_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            industry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        db_optimizer.execute_query(create_table_sql)

        # Safe serializer for database values
        def safe_to_str(value):
            if isinstance(value, (dict, list)):
                import json
                return json.dumps(value)
            if value is None:
                return ""
            return str(value)
        
        # Sanitize all incoming values
        sanitized_name = safe_to_str(name)
        sanitized_company = safe_to_str(company)
        sanitized_industry = safe_to_str(industry)
        
        # Save or update onboarding info (SQLite compatible)
        upsert_sql = """
        INSERT OR REPLACE INTO onboarding_info (user_id, name, company, industry, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        db_optimizer.execute_query(upsert_sql, (user_id, sanitized_name, sanitized_company, sanitized_industry))

        # Also update user profile with onboarding completion
        update_user_sql = """
        UPDATE users 
        SET onboarding_completed = 1, onboarding_step = 4, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db_optimizer.execute_query(update_user_sql, (user_id,))

        logger.info(f"Onboarding data saved for user {user_id}: {name} at {company}")

        return create_success_response({
            'user_id': user_id,
            'name': name,
            'company': company,
            'industry': industry,
            'completed': True
        }, "Onboarding completed successfully")

    except Exception as e:
        logger.error(f"❌ Failed to save onboarding data: {e}")
        logger.error(f"User ID: {user_id}, Data: {data}")
        return create_error_response("Failed to save onboarding data", 500, 'SAVE_ERROR')

@bp.route("/api/onboarding/status", methods=["GET"])
@handle_api_errors
@jwt_required
def get_onboarding_status():
    """Get current onboarding status for a user"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']

        # Use global database optimizer

        # Get onboarding info
        select_sql = """
        SELECT name, company, industry, created_at, updated_at
        FROM onboarding_info 
        WHERE user_id = ?
        """
        result = db_optimizer.execute_query(select_sql, (user_id,))
        
        # Get user profile
        user_sql = """
        SELECT onboarding_completed, onboarding_step
        FROM users 
        WHERE id = ?
        """
        user_result = db_optimizer.execute_query(user_sql, (user_id,))
        
        if user_result and len(user_result) > 0:
            user_profile = user_result[0]
            # Handle SQLite Row objects by converting to dict
            if hasattr(user_profile, 'keys'):
                user_dict = dict(user_profile)
            else:
                user_dict = user_profile
                
            onboarding_completed = user_dict.get('onboarding_completed', 0)
            
            if result and len(result) > 0:
                onboarding_data = result[0]
                # Handle SQLite Row objects by converting to dict
                if hasattr(onboarding_data, 'keys'):
                    onboarding_dict = dict(onboarding_data)
                else:
                    onboarding_dict = onboarding_data
                return create_success_response({
                    'completed': bool(onboarding_completed),
                    'data': onboarding_dict,
                    'step': user_dict.get('onboarding_step', 0)
                }, "Onboarding status retrieved")
            else:
                return create_success_response({
                    'completed': False,
                    'data': None,
                    'step': user_dict.get('onboarding_step', 0)
                }, "No onboarding data found")
        else:
            return create_error_response("User not found", 404, 'USER_NOT_FOUND')

    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        return create_error_response("Failed to get onboarding status", 500, 'STATUS_ERROR')

@bp.route("/api/onboarding/resume", methods=["GET"])
@handle_api_errors
@jwt_required
def resume_onboarding():
    """Resume onboarding from where user left off"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']

        # Use global database optimizer

        # Get user's current onboarding step
        user_sql = """
        SELECT onboarding_completed, onboarding_step
        FROM users 
        WHERE id = ?
        """
        user_result = db_optimizer.execute_query(user_sql, (user_id,))
        
        if user_result and len(user_result) > 0:
            user_profile = user_result[0]
            # Handle SQLite Row objects by converting to dict
            if hasattr(user_profile, 'keys'):
                user_dict = dict(user_profile)
            else:
                user_dict = user_profile
                
            onboarding_completed = user_dict.get('onboarding_completed', 0)
            
            if onboarding_completed:
                return create_success_response({
                    'completed': True,
                    'redirect_to': '/dashboard'
                }, "Onboarding already completed")
            else:
                step = user_dict.get('onboarding_step', 1)
                return create_success_response({
                    'completed': False,
                    'recommended_step': step,
                    'redirect_to': f'/onboarding?step={step}'
                }, "Resume onboarding")
        else:
            return create_error_response("User not found", 404, 'USER_NOT_FOUND')

    except Exception as e:
        logger.error(f"Error resuming onboarding: {e}")
        return create_error_response("Failed to resume onboarding", 500, 'RESUME_ERROR')
