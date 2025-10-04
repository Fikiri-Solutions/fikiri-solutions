"""
Dashboard Metrics API for Fikiri Solutions
Provides /api/dashboard/metrics endpoint for frontend dashboard data
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.database_optimization import db_optimizer
from core.jwt_auth import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/metrics', methods=['GET'])
@handle_api_errors
@jwt_required
def get_dashboard_metrics():
    """Get dashboard metrics for authenticated user"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']
        
        # Get user data
        user_data_db = db_optimizer.execute_query(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        )
        
        if not user_data_db:
            return create_error_response("User not found", 404, 'USER_NOT_FOUND')
        
        user = user_data_db[0]
        # Handle SQLite Row objects by converting to dict
        if hasattr(user, 'keys'):
            user_dict = dict(user)
        else:
            user_dict = user if isinstance(user, dict) else {}
        
        # Get leads count
        leads_data = db_optimizer.execute_query(
            "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
            (user_id,)
        )
        leads_count = 0
        if leads_data and len(leads_data) > 0:
            lead_row = leads_data[0]
            # Handle SQLite Row objects by converting to dict
            if hasattr(lead_row, 'keys'):
                lead_dict = dict(lead_row)
                leads_count = lead_dict.get('count', 0)
            else:
                leads_count = lead_row.get('count', 0) if isinstance(lead_row, dict) else 0
        
        # Get recent leads (last 7 days)
        recent_leads_data = db_optimizer.execute_query(
            "SELECT COUNT(*) as count FROM leads WHERE user_id = ? AND created_at >= datetime('now', '-7 days')",
            (user_id,)
        )
        recent_leads = 0
        if recent_leads_data and len(recent_leads_data) > 0:
            recent_row = recent_leads_data[0]
            # Handle SQLite Row objects by converting to dict
            if hasattr(recent_row, 'keys'):
                recent_dict = dict(recent_row)
                recent_leads = recent_dict.get('count', 0)
            else:
                recent_leads = recent_row.get('count', 0) if isinstance(recent_row, dict) else 0
        
        # Get email activity (mock data for now)
        email_activity = {
            'total_emails': 0,
            'unread_emails': 0,
            'emails_today': 0,
            'last_email': None
        }
        
        # Get automation stats (mock data for now)
        automation_stats = {
            'total_automations': 0,
            'active_automations': 0,
            'automations_executed_today': 0,
            'last_execution': None
        }
        
        # Get Gmail connection status
        gmail_connected = False
        try:
            # Check if user has OAuth tokens
            oauth_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM oauth_tokens WHERE user_id = ? AND provider = 'gmail' AND expires_at > datetime('now')",
                (user_id,)
            )
            if oauth_data and len(oauth_data) > 0:
                oauth_row = oauth_data[0]
                # Handle SQLite Row objects by converting to dict
                if hasattr(oauth_row, 'keys'):
                    oauth_dict = dict(oauth_row)
                    gmail_connected = oauth_dict.get('count', 0) > 0
                else:
                    gmail_connected = oauth_row.get('count', 0) > 0 if isinstance(oauth_row, dict) else False
        except Exception as e:
            logger.warning(f"Could not check Gmail connection: {e}")
            gmail_connected = False
        
        # Compile metrics
        metrics_data = {
            'user': {
                'id': user_dict.get('id'),
                'name': user_dict.get('name'),
                'email': user_dict.get('email'),
                'onboarding_completed': user_dict.get('onboarding_completed', False),
                'onboarding_step': user_dict.get('onboarding_step', 1)
            },
            'leads': {
                'total': leads_count,
                'recent': recent_leads,
                'growth_rate': 0  # Calculate if we have historical data
            },
            'email': email_activity,
            'automation': automation_stats,
            'integrations': {
                'gmail_connected': gmail_connected,
                'crm_synced': True,  # Mock
                'analytics_enabled': True  # Mock
            },
            'performance': {
                'response_time': '2.3s',  # Mock
                'uptime': '99.9%',  # Mock
                'last_sync': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return create_success_response(metrics_data, "Dashboard metrics retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard metrics error: {e}")
        import traceback
        logger.error(f"Dashboard metrics traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to get dashboard metrics: {str(e)}", 500, "DASHBOARD_ERROR")

@dashboard_bp.route('/activity', methods=['GET'])
@handle_api_errors
def get_dashboard_activity():
    """Get recent activity for dashboard"""
    try:
        # Get user ID from session
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Mock activity data for now
        activity_data = [
            {
                'id': 1,
                'type': 'lead_created',
                'message': 'New lead added: John Doe',
                'timestamp': datetime.now().isoformat(),
                'icon': 'user-plus',
                'color': 'green'
            },
            {
                'id': 2,
                'type': 'email_received',
                'message': 'Email from jane@example.com',
                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
                'icon': 'mail',
                'color': 'blue'
            },
            {
                'id': 3,
                'type': 'automation_triggered',
                'message': 'Welcome email sent to new lead',
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                'icon': 'zap',
                'color': 'purple'
            }
        ]
        
        return create_success_response({'activities': activity_data}, "Activity data retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard activity error: {e}")
        return create_error_response("Failed to get activity data", 500, "ACTIVITY_ERROR")

@dashboard_bp.route('/services', methods=['GET'])
@handle_api_errors
def get_dashboard_services():
    """Get service status for dashboard"""
    try:
        # Get user ID from session
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Mock service status data
        services_data = [
            {
                'name': 'Email Parser',
                'status': 'active',
                'uptime': '99.9%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'CRM Integration',
                'status': 'active',
                'uptime': '100%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'AI Assistant',
                'status': 'active',
                'uptime': '99.8%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'Automation Engine',
                'status': 'active',
                'uptime': '99.9%',
                'last_check': datetime.now().isoformat()
            }
        ]
        
        return create_success_response({'services': services_data}, "Service status retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard services error: {e}")
        return create_error_response("Failed to get service status", 500, "SERVICES_ERROR")
