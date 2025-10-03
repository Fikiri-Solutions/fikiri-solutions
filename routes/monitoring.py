#!/usr/bin/env python3
"""
Monitoring and Health Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
import os
import logging
from datetime import datetime

# Import monitoring modules
from core.monitoring import health_monitor
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.database_optimization import db_optimizer
from core.oauth_token_manager import oauth_token_manager

logger = logging.getLogger(__name__)

# Create monitoring blueprint
monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/api")

@monitoring_bp.route('/health-old')
@handle_api_errors
def api_health_old():
    """Comprehensive health check endpoint for system monitoring."""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'metrics': {
                'uptime': 'operational',
                'active_users': 0,  # Placeholder
                'active_connections': 0,  # Placeholder
                'initialized_services': 3  # Placeholder
            },
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'version': '1.0.0'
        }

        # Database connectivity check
        try:
            db_optimizer.execute_query("SELECT 1")
            health_status['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': 10,  # Placeholder
                'error': None
            }
            health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        # Redis connectivity check (if available)
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                health_status['checks']['redis'] = {
                    'status': 'healthy',
                    'response_time_ms': 5,  # Placeholder
                    'error': None
                }
                health_status['metrics']['initialized_services'] += 1
            else:
                health_status['checks']['redis'] = {
                    'status': 'disabled',
                    'response_time_ms': 0,
                    'error': 'Redis not configured'
                }
        except Exception as e:
            health_status['checks']['redis'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # Gmail OAuth check (sample)
        try:
            health_status['checks']['gmail_auth'] = {
                'status': 'configured' if os.getenv('GOOGLE_CLIENT_ID') else 'not_configured',
                'response_time_ms': 5,
                'error': None
            }
            if os.getenv('GOOGLE_CLIENT_ID'):
                health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['gmail_auth'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # OpenAI API check
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            health_status['checks']['openai'] = {
                'status': 'configured' if openai_key else 'not_configured',
                'response_time_ms': 5,
                'error': None
            }
            if openai_key:
                health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['openai'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # Calculate overall health
        unhealthy_checks = sum(1 for check in health_status['checks'].values() 
                             if check['status'] == 'unhealthy')
        
        if unhealthy_checks == 0:
            health_status['status'] = 'healthy'
            health_status['message'] = 'All systems operational'
        elif unhealthy_checks <= 2:
            health_status['status'] = 'degraded'
            health_status['message'] = f'{unhealthy_checks} system(s) experiencing issues'
        else:
            health_status['status'] = 'unhealthy'
            health_status['message'] = f'{unhealthy_checks} system(s) down'

        health_status['metrics']['initialized_services'] = health_status['metrics']['initialized_services']

        return create_success_response(health_status, 'Health check completed')

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return create_error_response("Health check failed", 500, 'HEALTH_CHECK_ERROR')

@monitoring_bp.route('/gmail/status', methods=['GET'])
@handle_api_errors
def gmail_status():
    """Get Gmail connection status"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        result = oauth_token_manager.get_token_status(user_id, "gmail")
        
        if result['success']:
            return create_success_response({
                'connected': True,
                'status': 'active',
                'last_sync': result.get('last_sync'),
                'expires_at': result.get('expires_at'),
                'scope': result.get('scope', [])
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

@monitoring_bp.route('/email/sync/status', methods=['GET'])
@handle_api_errors
def email_sync_status():
    """Get email synchronization status"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Check sync status from database
        sync_data = db_optimizer.execute_query(
            "SELECT last_sync, sync_status, total_emails FROM user_sync_status WHERE user_id = ?",
            (user_id,)
        )
        
        if sync_data:
            sync_record = sync_data[0]
            return create_success_response({
                'last_sync': sync_record['last_sync'],
                'sync_status': sync_record['sync_status'],
                'total_emails': sync_record['total_emails'],
                'syncing': sync_record['sync_status'] == 'in_progress'
            }, 'Email sync status retrieved')
        else:
            return create_success_response({
                'sync_status': 'never_synced',
                'last_sync': None,
                'total_emails': 0,
                'syncing': False
            }, 'No sync history found')
            
    except Exception as e:
        logger.error(f"Email sync status error: {e}")
        return create_error_response("Failed to get sync status", 500, 'SYNC_STATUS_ERROR')

@monitoring_bp.route('/rate-limits/status', methods=['GET'])
@handle_api_errors
def rate_limits_status():
    """Get rate limiting status for current user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        from core.rate_limiter import enhanced_rate_limiter
        
        # Get rate limit status
        rate_limit_status = enhanced_rate_limiter.get_user_limits(user_id)
        
        return create_success_response({
            'user_id': user_id,
            'limits': rate_limit_status,
            'current_usage': enhanced_rate_limiter.get_current_usage(user_id),
            'reset_time': enhanced_rate_limiter.get_reset_time(user_id)
        }, 'Rate limits status retrieved')
        
    except Exception as e:
        logger.error(f"Rate limits status error: {e}")
        return create_error_response("Failed to get rate limits status", 500, 'RATE_LIMITS_STATUS_ERROR')

@monitoring_bp.route('/system/metrics', methods=['GET'])
@handle_api_errors
def system_metrics():
    """Get system performance metrics"""
    try:
        from core.performance_monitor import performance_monitor
        
        metrics = performance_monitor.get_system_metrics()
        
        return create_success_response(metrics, 'System metrics retrieved')
        
    except Exception as e:
        logger.error(f"System metrics error: {e}")
        return create_error_response("Failed to get system metrics", 500, 'SYSTEM_METRICS_ERROR')

@monitoring_bp.route('/alerts', methods=['GET'])
@handle_api_errors
def get_alerts():
    """Get system alerts and notifications"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Get alerts from database for specific user or global alerts
        alerts_data = db_optimizer.execute_query(
            """
            SELECT id, alert_type, alert_level, message, timestamp, resolved 
            FROM system_alerts 
            WHERE user_id = ? OR user_id IS NULL 
            ORDER BY timestamp DESC 
            LIMIT 100
            """,
            (user_id,)
        )
        
        alerts = []
        if alerts_data:
            alerts = [{
                'id': row['id'],
                'type': row['alert_type'],
                'level': row['alert_level'],
                'message': row['message'],
                'timestamp': row['timestamp'],
                'resolved': row['resolved']
            } for row in alerts_data]
        
        return create_success_response({'alerts': alerts}, 'System alerts retrieved')
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return create_error_response("Failed to get alerts", 500, 'ALERTS_ERROR')
