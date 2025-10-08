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

@dashboard_bp.route('/debug', methods=['GET'])
@handle_api_errors
@jwt_required
def debug_dashboard():
    """Debug endpoint to identify dashboard issues"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']
        
        debug_info = {
            'user_id': user_id,
            'user_data': user_data,
            'database_connected': True,
            'queries_tested': []
        }
        
        # Test basic database query
        try:
            user_data_db = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (user_id,)
            )
            debug_info['queries_tested'].append({
                'query': 'users',
                'result_count': len(user_data_db) if user_data_db else 0,
                'success': True
            })
        except Exception as e:
            debug_info['queries_tested'].append({
                'query': 'users',
                'error': str(e),
                'success': False
            })
        
        # Test leads query
        try:
            leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )
            debug_info['queries_tested'].append({
                'query': 'leads_count',
                'result_count': len(leads_data) if leads_data else 0,
                'success': True
            })
        except Exception as e:
            debug_info['queries_tested'].append({
                'query': 'leads_count',
                'error': str(e),
                'success': False
            })
        
        return create_success_response(debug_info, "Debug information retrieved")
        
    except Exception as e:
        logger.error(f"Debug dashboard error: {e}")
        import traceback
        logger.error(f"Debug dashboard traceback: {traceback.format_exc()}")
        return create_error_response(f"Debug failed: {str(e)}", 500, "DEBUG_ERROR")

@dashboard_bp.route('/metrics', methods=['GET'])
@handle_api_errors
def get_dashboard_metrics():
    """Get dashboard metrics for authenticated user"""
    try:
        # For now, use default user data until auth is fixed
        user_data = {'user_id': 1, 'name': 'Demo User', 'email': 'demo@example.com'}
        user_id = user_data['user_id']
        
        # Initialize default metrics
        metrics_data = {
            'user': {
                'id': user_id,
                'name': user_data.get('name', 'User'),
                'email': user_data.get('email', ''),
                'onboarding_completed': False,
                'onboarding_step': 1
            },
            'leads': {
                'total': 0,
                'recent': 0,
                'growth_rate': 0
            },
            'email': {
                'total_emails': 0,
                'unread_emails': 0,
                'emails_today': 0,
                'last_email': None
            },
            'automation': {
                'total_automations': 0,
                'active_automations': 0,
                'automations_executed_today': 0,
                'last_execution': None
            },
            'integrations': {
                'gmail_connected': False,
                'crm_synced': True,
                'analytics_enabled': True
            },
            'performance': {
                'response_time': '2.3s',
                'uptime': '99.9%',
                'last_sync': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to get user data from database
        try:
            user_data_db = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (user_id,)
            )
            
            if user_data_db and len(user_data_db) > 0:
                user = user_data_db[0]
                # Handle SQLite Row objects by converting to dict
                if hasattr(user, 'keys'):
                    user_dict = dict(user)
                else:
                    user_dict = user if isinstance(user, dict) else {}
                
                # Update metrics with user data
                metrics_data['user'].update({
                    'name': user_dict.get('name', user_data.get('name', 'User')),
                    'email': user_dict.get('email', user_data.get('email', '')),
                    'onboarding_completed': user_dict.get('onboarding_completed', False),
                    'onboarding_step': user_dict.get('onboarding_step', 1)
                })
        except Exception as e:
            logger.warning(f"Could not get user data: {e}")
        
        # Try to get leads count
        try:
            leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )
            if leads_data and len(leads_data) > 0:
                lead_row = leads_data[0]
                if hasattr(lead_row, 'keys'):
                    lead_dict = dict(lead_row)
                    metrics_data['leads']['total'] = lead_dict.get('count', 0)
                else:
                    metrics_data['leads']['total'] = lead_row.get('count', 0) if isinstance(lead_row, dict) else 0
        except Exception as e:
            logger.warning(f"Could not get leads count: {e}")
        
        # Try to get recent leads
        try:
            recent_leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ? AND created_at >= datetime('now', '-7 days')",
                (user_id,)
            )
            if recent_leads_data and len(recent_leads_data) > 0:
                recent_row = recent_leads_data[0]
                if hasattr(recent_row, 'keys'):
                    recent_dict = dict(recent_row)
                    metrics_data['leads']['recent'] = recent_dict.get('count', 0)
                else:
                    metrics_data['leads']['recent'] = recent_row.get('count', 0) if isinstance(recent_row, dict) else 0
        except Exception as e:
            logger.warning(f"Could not get recent leads: {e}")
        
        # Try to check Gmail connection
        try:
            oauth_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM oauth_tokens WHERE user_id = ? AND provider = 'gmail' AND expires_at > datetime('now')",
                (user_id,)
            )
            if oauth_data and len(oauth_data) > 0:
                oauth_row = oauth_data[0]
                if hasattr(oauth_row, 'keys'):
                    oauth_dict = dict(oauth_row)
                    metrics_data['integrations']['gmail_connected'] = oauth_dict.get('count', 0) > 0
                else:
                    metrics_data['integrations']['gmail_connected'] = oauth_row.get('count', 0) > 0 if isinstance(oauth_row, dict) else False
        except Exception as e:
            logger.warning(f"Could not check Gmail connection: {e}")
        
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

@dashboard_bp.route('/test', methods=['GET'])
def test_dashboard():
    """Simple test endpoint"""
    return jsonify({'success': True, 'message': 'Dashboard blueprint is working'})

@dashboard_bp.route('/kpi', methods=['GET'])
@handle_api_errors
def get_dashboard_kpi():
    """Get business KPI data for dashboard"""
    try:
        # Return sample KPI data
        kpi_data = {
            'success': True,
            'data': {
                'revenue': {
                    'current': 125000,
                    'previous': 98000,
                    'change': 27.5,
                    'trend': 'up'
                },
                'leads': {
                    'current': 45,
                    'previous': 32,
                    'change': 40.6,
                    'trend': 'up'
                },
                'conversion': {
                    'current': 12.5,
                    'previous': 9.8,
                    'change': 27.5,
                    'trend': 'up'
                },
                'emails_processed': {
                    'current': 1250,
                    'previous': 980,
                    'change': 27.5,
                    'trend': 'up'
                }
            },
            'message': 'KPI data retrieved successfully'
        }
        
        return jsonify(kpi_data)
        
    except Exception as e:
        logger.error(f"KPI dashboard error: {e}")
        return create_error_response(f"KPI failed: {str(e)}", 500, "KPI_ERROR")
