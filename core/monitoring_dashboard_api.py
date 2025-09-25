"""
Monitoring Dashboard API
REST endpoints for system monitoring and alerts
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
from core.monitoring_dashboard_system import monitoring_dashboard_system
# from core.enterprise_logging import log_api_request

logger = logging.getLogger(__name__)

# Create blueprint
monitoring_dashboard_bp = Blueprint('monitoring_dashboard', __name__, url_prefix='/api/monitoring')

@monitoring_dashboard_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get complete monitoring dashboard data"""
    try:
        dashboard_data = monitoring_dashboard_system.get_dashboard_data()
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/redis', methods=['GET'])
def get_redis_metrics():
    """Get Redis-specific metrics"""
    try:
        redis_metrics = monitoring_dashboard_system.get_redis_metrics()
        return jsonify({
            'success': True,
            'metrics': redis_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting Redis metrics: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/system', methods=['GET'])
def get_system_metrics():
    """Get system-level metrics"""
    try:
        system_metrics = monitoring_dashboard_system.get_system_metrics()
        return jsonify({
            'success': True,
            'metrics': system_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/application', methods=['GET'])
def get_application_metrics():
    """Get application-specific metrics"""
    try:
        application_metrics = monitoring_dashboard_system.get_application_metrics()
        return jsonify({
            'success': True,
            'metrics': application_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting application metrics: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    try:
        # Get query parameters
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        level = request.args.get('level')
        limit = int(request.args.get('limit', 50))
        
        alerts = monitoring_dashboard_system.alerts
        
        # Apply filters
        if active_only:
            alerts = [alert for alert in alerts if not alert.resolved]
        
        if level:
            alerts = [alert for alert in alerts if alert.level.value == level]
        
        # Limit results
        alerts = alerts[-limit:] if limit > 0 else alerts
        
        # Convert to dict format
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts_data,
            'total': len(alerts_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id: str):
    """Resolve an alert"""
    try:
        success = monitoring_dashboard_system.resolve_alert(alert_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Alert resolved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found or already resolved'
            }), 404
        
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """Get alert statistics"""
    try:
        stats = monitoring_dashboard_system.get_alert_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        dashboard_data = monitoring_dashboard_system.get_dashboard_data()
        
        if 'error' in dashboard_data:
            return jsonify({
                'success': False,
                'status': 'unhealthy',
                'error': dashboard_data['error']
            }), 500
        
        overall_health = dashboard_data.get('overall_health', {})
        status = overall_health.get('status', 'unknown')
        
        return jsonify({
            'success': True,
            'status': status,
            'health_score': overall_health.get('score', 0),
            'timestamp': dashboard_data.get('timestamp')
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/queues', methods=['GET'])
def get_queue_status():
    """Get queue status and metrics"""
    try:
        from core.redis_queues import email_queue, ai_queue, crm_queue, webhook_queue
        
        queue_names = ['email_processing', 'ai_responses', 'webhook_processing', 'scheduled_tasks']
        queue_status = {}
        
        queue_instances = {
            'email_processing': email_queue,
            'ai_responses': ai_queue,
            'webhook_processing': webhook_queue,
            'scheduled_tasks': crm_queue
        }
        
        for queue_name in queue_names:
            try:
                queue_instance = queue_instances.get(queue_name)
                if queue_instance:
                    length = queue_instance.get_queue_length()
                    queue_status[queue_name] = {
                        'length': length,
                        'status': 'healthy' if length < 100 else 'warning' if length < 500 else 'critical'
                    }
                else:
                    queue_status[queue_name] = {
                        'length': 0,
                        'status': 'error',
                        'error': f'Queue {queue_name} not found'
                    }
            except Exception as e:
                queue_status[queue_name] = {
                    'length': 0,
                    'status': 'error',
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'queues': queue_status
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_dashboard_bp.route('/performance', methods=['GET'])
def get_performance_metrics():
    """Get performance metrics"""
    try:
        import time
        import psutil
        
        # Get current process
        process = psutil.Process()
        
        # Get performance metrics
        performance_data = {
            'timestamp': time.time(),
            'process': {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            },
            'system': {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict()
            }
        }
        
        return jsonify({
            'success': True,
            'performance': performance_data
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': str(e)}), 500
