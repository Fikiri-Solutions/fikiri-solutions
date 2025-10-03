"""
Onboarding endpoint for saving user onboarding information
"""
import logging
from flask import Blueprint, request, jsonify
from core.secure_sessions import get_current_user_id
from core.database_optimization import get_db_optimizer
from core.api_validation import create_success_response, create_error_response, handle_api_errors

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("onboarding", __name__)

@bp.route("/api/onboarding", methods=["POST"])
@handle_api_errors
def save_onboarding():
    """Save user onboarding information"""
    try:
        # Get user ID from session/auth
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

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

        # Initialize database optimizer
        db_optimizer = get_db_optimizer()

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

        # Save or update onboarding info
        upsert_sql = """
        INSERT INTO onboarding_info (user_id, name, company, industry)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (user_id) DO UPDATE SET
            name = excluded.name,
            company = excluded.company,
            industry = excluded.industry,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_optimizer.execute_query(upsert_sql, (user_id, name, company, industry))

        # Also update user profile with onboarding completion
        update_user_sql = """
        UPDATE users 
        SET onboarding_completed = 1, onboarding_step = -1, updated_at = CURRENT_TIMESTAMP
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
        logger.error(f"Error saving onboarding data: {e}")
        return create_error_response("Failed to save onboarding data", 500, 'SAVE_ERROR')

@bp.route("/api/onboarding/status", methods=["GET"])
@handle_api_errors
def get_onboarding_status():
    """Get current onboarding status for a user"""
    try:
        # Get user ID from session/auth
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Initialize database optimizer
        db_optimizer = get_db_optimizer()

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
            onboarding_completed = user_profile.get('onboarding_completed', 0)
            
            if result and len(result) > 0:
                onboarding_data = result[0]
                return create_success_response({
                    'completed': bool(onboarding_completed),
                    'data': onboarding_data,
                    'step': user_profile.get('onboarding_step', 0)
                }, "Onboarding status retrieved")
            else:
                return create_success_response({
                    'completed': False,
                    'data': None,
                    'step': user_profile.get('onboarding_step', 0)
                }, "No onboarding data found")
        else:
            return create_error_response("User not found", 404, 'USER_NOT_FOUND')

    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        return create_error_response("Failed to get onboarding status", 500, 'STATUS_ERROR')

@bp.route("/api/onboarding/resume", methods=["GET"])
@handle_api_errors  
def resume_onboarding():
    """Resume onboarding from where user left off"""
    try:
        # Get user ID from session/auth
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Initialize database optimizer
        db_optimizer = get_db_optimizer()

        # Get user's current onboarding step
        user_sql = """
        SELECT onboarding_completed, onboarding_step
        FROM users 
        WHERE id = ?
        """
        user_result = db_optimizer.execute_query(user_sql, (user_id,))
        
        if user_result and len(user_result) > 0:
            user_profile = user_result[0]
            onboarding_completed = user_profile.get('onboarding_completed', 0)
            
            if onboarding_completed:
                return create_success_response({
                    'completed': True,
                    'redirect_to': '/dashboard'
                }, "Onboarding already completed")
            else:
                step = user_profile.get('onboarding_step', 1)
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