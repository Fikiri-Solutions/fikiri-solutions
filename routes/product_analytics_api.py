"""Authenticated product analytics event ingestion (non-admin route)."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.jwt_auth import jwt_required
from core.product_analytics_ingest import MAX_EVENTS_PER_REQUEST, ingest_product_events
from core.product_analytics_registry import (
    accessibility_signals_enabled,
    product_analytics_enabled,
)
from core.rate_limiter import enhanced_rate_limiter
from core.secure_sessions import get_actor_user_id, get_current_user_id, is_impersonating

logger = logging.getLogger(__name__)

product_analytics_bp = Blueprint(
    "product_analytics",
    __name__,
    url_prefix="/api/analytics",
)

# ~64KB JSON body ceiling
_MAX_CONTENT_LENGTH = 65_536


@product_analytics_bp.route("/status", methods=["GET"])
@handle_api_errors
@jwt_required
def analytics_status():
    """Safe booleans for the client — never expose raw env beyond these flags."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    return create_success_response(
        {
            "analytics_enabled": product_analytics_enabled(),
            "accessibility_signals_enabled": accessibility_signals_enabled(),
            "impersonating": bool(is_impersonating()),
        },
        "Analytics status",
    )


@product_analytics_bp.route("/events", methods=["POST"])
@handle_api_errors
@jwt_required
def post_analytics_events():
    """Ingest product analytics events for the authenticated user's tenant."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    actor_id = get_actor_user_id() or user_id
    # Tenant ownership currently maps to account user id; keep field separate.
    tenant_id = int(user_id)
    actor_user_id = int(actor_id)

    content_length = request.content_length or 0
    if content_length > _MAX_CONTENT_LENGTH:
        return create_error_response("Payload too large", 413, "PAYLOAD_TOO_LARGE")

    # Rate limit: 120 batches / hour / user
    try:
        rl = enhanced_rate_limiter.check_rate_limit(
            "product_analytics_ingest",
            f"user:{user_id}",
            user_id=user_id,
        )
        if not getattr(rl, "allowed", True):
            return create_error_response("Rate limit exceeded", 429, "RATE_LIMITED")
    except Exception:
        # Rate limiter failure must not block product; continue without hard fail
        logger.warning(
            "product_analytics rate limit check failed",
            extra={"event": "product_analytics.rate_limit_error"},
        )

    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return create_error_response("Invalid payload", 400, "INVALID_PAYLOAD")

    surface = str(body.get("surface") or "").strip().lower()
    platform_admin_surface = surface in {"admin", "platform_admin", "platform-admin"}

    events = body.get("events")
    if events is None and body.get("event_name"):
        events = [body]
    if not isinstance(events, list):
        return create_error_response("events must be a list", 400, "INVALID_PAYLOAD")
    if len(events) > MAX_EVENTS_PER_REQUEST:
        return create_error_response("Too many events", 400, "BATCH_TOO_LARGE")

    # In tests / local SQLite, ensure tables exist when analytics enabled.
    # Production Postgres relies on migration 009 — ensure is a no-op if tables exist.
    from core.product_analytics_registry import product_analytics_enabled as _enabled

    ensure = False
    if _enabled():
        try:
            from core.product_analytics_store import tables_available, ensure_product_analytics_tables

            if not tables_available():
                # Only auto-ensure outside production
                import os

                if (os.getenv("FLASK_ENV") or "").lower() != "production":
                    ensure_product_analytics_tables()
                    ensure = False
        except Exception:
            pass

    result = ingest_product_events(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        events=events,
        impersonating=bool(is_impersonating()),
        platform_admin_surface=platform_admin_surface,
        ensure_tables=ensure,
    )
    return create_success_response(result, "Analytics events processed")
