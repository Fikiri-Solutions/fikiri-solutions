"""
HTTP API for unified service usage analytics (tenant-scoped).
"""

from __future__ import annotations

import logging

from flask import Blueprint, request

from analytics.service_activity_rollups import (
    aggregate_platform_service_activity,
    refresh_tenant_analytics,
)
from analytics.service_health_metrics import get_tenant_health_snapshot
from analytics.service_usage_analytics import (
    get_tenant_service_summary,
    list_active_tenants_by_service,
)
from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

service_usage_bp = Blueprint("service_usage", __name__, url_prefix="/api/analytics/services")


@service_usage_bp.route("", methods=["GET"])
@handle_api_errors
def get_service_analytics_index():
    return create_success_response(
        {
            "routes": {
                "summary": "/api/analytics/services/summary",
                "health": "/api/analytics/services/health",
                "refresh": "/api/analytics/services/refresh",
                "platform": "/api/analytics/services/platform",
            }
        },
        "Service analytics API",
    )


@service_usage_bp.route("/summary", methods=["GET"])
@handle_api_errors
def get_service_summary():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    return create_success_response(
        get_tenant_service_summary(int(user_id)),
        "Service usage summary",
    )


@service_usage_bp.route("/health", methods=["GET"])
@handle_api_errors
def get_service_health():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    return create_success_response(
        get_tenant_health_snapshot(int(user_id)),
        "Service health snapshot",
    )


@service_usage_bp.route("/refresh", methods=["POST"])
@handle_api_errors
def post_refresh_analytics():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    mirror = request.json.get("mirror_billing", True) if request.is_json else True
    counts = refresh_tenant_analytics(int(user_id), mirror_billing=bool(mirror))
    return create_success_response(counts, "Analytics refreshed")


@service_usage_bp.route("/platform", methods=["GET"])
@handle_api_errors
def get_platform_activity():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    days = request.args.get("days", 30, type=int)
    service_id = request.args.get("service_id", type=str)
    if service_id:
        tenants = list_active_tenants_by_service(service_id, days=days)
        return create_success_response(
            {"service_id": service_id, "active_tenants": tenants},
            "Active tenants for service",
        )
    activity = aggregate_platform_service_activity(days=days)
    return create_success_response(
        {"services": activity, "window_days": days},
        "Platform service activity",
    )
