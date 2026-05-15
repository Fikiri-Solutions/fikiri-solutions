"""
Monitoring Dashboard API
REST endpoints for system monitoring and alerts
"""

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from core.billing_api import _is_admin_user
from core.jwt_auth import get_jwt_manager, get_jwt_user_id

# Monitoring dashboard system - disabled as part of cleanup
# from core.monitoring_dashboard_system import monitoring_dashboard_system
monitoring_dashboard_system = None

logger = logging.getLogger(__name__)

# Create blueprint
monitoring_dashboard_bp = Blueprint("monitoring_dashboard", __name__, url_prefix="/api/monitoring")


def _monitoring_unavailable():
    return (
        jsonify(
            {
                "success": False,
                "error": "Monitoring dashboard is not enabled",
                "code": "MONITORING_DISABLED",
            }
        ),
        503,
    )


def _authenticate_monitoring_admin():
    """When the monitoring backend is enabled, require Bearer JWT + platform admin."""
    from flask import request

    if monitoring_dashboard_system is None:
        return None
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Authorization header missing or invalid",
                    "error_code": "MISSING_AUTH_HEADER",
                }
            ),
            401,
        )
    token = auth_header.split(" ", 1)[1].strip()
    payload = get_jwt_manager().verify_access_token(token)
    if not isinstance(payload, dict) or payload.get("error"):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid or expired token",
                    "error_code": "INVALID_TOKEN",
                }
            ),
            401,
        )
    request.current_user = payload
    uid = get_jwt_user_id()
    if not uid or not _is_admin_user(uid):
        return jsonify({"success": False, "error": "Forbidden"}), 403
    return None


@monitoring_dashboard_bp.before_request
def _monitoring_require_admin_when_enabled():
    return _authenticate_monitoring_admin()


@monitoring_dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    """Get complete monitoring dashboard data"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        dashboard_data = monitoring_dashboard_system.get_dashboard_data()
        return jsonify({"success": True, "data": dashboard_data})

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/redis", methods=["GET"])
def get_redis_metrics():
    """Get Redis-specific metrics"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        redis_metrics = monitoring_dashboard_system.get_redis_metrics()
        return jsonify({"success": True, "metrics": redis_metrics})

    except Exception as e:
        logger.error(f"Error getting Redis metrics: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/system", methods=["GET"])
def get_system_metrics():
    """Get system-level metrics"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        system_metrics = monitoring_dashboard_system.get_system_metrics()
        return jsonify({"success": True, "metrics": system_metrics})

    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/application", methods=["GET"])
def get_application_metrics():
    """Get application-specific metrics"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        application_metrics = monitoring_dashboard_system.get_application_metrics()
        return jsonify({"success": True, "metrics": application_metrics})

    except Exception as e:
        logger.error(f"Error getting application metrics: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/alerts", methods=["GET"])
def get_alerts():
    """Get all alerts"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        active_only = request.args.get("active_only", "false").lower() == "true"
        level = request.args.get("level")
        limit = int(request.args.get("limit", 50))

        alerts = monitoring_dashboard_system.alerts

        if active_only:
            alerts = [alert for alert in alerts if not alert.resolved]

        if level:
            alerts = [alert for alert in alerts if alert.level.value == level]

        alerts = alerts[-limit:] if limit > 0 else alerts

        alerts_data = []
        for alert in alerts:
            alerts_data.append(
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                }
            )

        return jsonify({"success": True, "alerts": alerts_data, "total": len(alerts_data)})

    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id: str):
    """Resolve an alert"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        success = monitoring_dashboard_system.resolve_alert(alert_id)

        if success:
            return jsonify({"success": True, "message": "Alert resolved successfully"})
        return (
            jsonify({"success": False, "error": "Alert not found or already resolved"}),
            404,
        )

    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/alerts/statistics", methods=["GET"])
def get_alert_statistics():
    """Get alert statistics"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        stats = monitoring_dashboard_system.get_alert_statistics()
        return jsonify({"success": True, "statistics": stats})

    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    if monitoring_dashboard_system is None:
        return _monitoring_unavailable()
    try:
        dashboard_data = monitoring_dashboard_system.get_dashboard_data()

        if "error" in dashboard_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "status": "unhealthy",
                        "error": dashboard_data["error"],
                    }
                ),
                500,
            )

        overall_health = dashboard_data.get("overall_health", {})
        status = overall_health.get("status", "unknown")

        return jsonify(
            {
                "success": True,
                "status": status,
                "health_score": overall_health.get("score", 0),
                "timestamp": dashboard_data.get("timestamp"),
            }
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/queues", methods=["GET"])
def get_queue_status():
    """Get queue status and metrics"""
    try:
        from core.redis_queues import ai_queue, crm_queue, email_queue, webhook_queue

        queue_names = ["email_processing", "ai_responses", "webhook_processing", "scheduled_tasks"]
        queue_status: Dict[str, Any] = {}

        queue_instances = {
            "email_processing": email_queue,
            "ai_responses": ai_queue,
            "webhook_processing": webhook_queue,
            "scheduled_tasks": crm_queue,
        }

        for queue_name in queue_names:
            try:
                queue_instance = queue_instances.get(queue_name)
                if queue_instance:
                    length = queue_instance.get_queue_length()
                    queue_status[queue_name] = {
                        "length": length,
                        "status": (
                            "healthy"
                            if length < 100
                            else "warning"
                            if length < 500
                            else "critical"
                        ),
                    }
                else:
                    queue_status[queue_name] = {
                        "length": 0,
                        "status": "error",
                        "error": f"Queue {queue_name} not found",
                    }
            except Exception as e:
                queue_status[queue_name] = {"length": 0, "status": "error", "error": str(e)}

        return jsonify({"success": True, "queues": queue_status})

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({"error": str(e)}), 500


@monitoring_dashboard_bp.route("/performance", methods=["GET"])
def get_performance_metrics():
    """Get performance metrics (admin only)."""
    try:
        import time

        import psutil

        process = psutil.Process()

        performance_data = {
            "timestamp": time.time(),
            "process": {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_info": process.memory_info()._asdict(),
                "num_threads": process.num_threads(),
                "create_time": process.create_time(),
            },
            "system": {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": psutil.virtual_memory()._asdict(),
                "disk": psutil.disk_usage("/")._asdict(),
            },
        }

        return jsonify({"success": True, "performance": performance_data})

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({"error": str(e)}), 500
