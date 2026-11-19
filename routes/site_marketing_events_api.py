"""Public ingest + (admin summary lives on admin_platform_api)."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.rate_limiter import enhanced_rate_limiter
from core.site_marketing_events import (
    MAX_EVENTS_PER_REQUEST,
    ingest_site_marketing_events,
    site_marketing_events_enabled,
)

logger = logging.getLogger(__name__)

site_marketing_events_bp = Blueprint(
    "site_marketing_events",
    __name__,
    url_prefix="/api/site/events",
)

_MAX_CONTENT_LENGTH = 16_384


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.remote_addr or "unknown").strip()


@site_marketing_events_bp.route("", methods=["POST", "OPTIONS"])
@site_marketing_events_bp.route("/", methods=["POST", "OPTIONS"])
@handle_api_errors
def post_site_marketing_events():
    if request.method == "OPTIONS":
        return "", 204

    if not site_marketing_events_enabled():
        return create_success_response(
            {"accepted": 0, "rejected": 0, "duplicates": 0, "events_enabled": False},
            "Site marketing events disabled",
        )

    content_length = request.content_length or 0
    if content_length > _MAX_CONTENT_LENGTH:
        return create_error_response("Payload too large", 413, "PAYLOAD_TOO_LARGE")

    try:
        rl = enhanced_rate_limiter.check_rate_limit(
            "site_marketing_events",
            f"ip:{_client_ip()}",
        )
        if not getattr(rl, "allowed", True):
            return create_error_response("Rate limit exceeded", 429, "RATE_LIMITED")
    except Exception:
        logger.warning(
            "site_marketing_events rate limit check failed",
            extra={"event": "site_marketing_events.rate_limit_error"},
        )

    body = request.get_json(silent=True) or {}
    session_ref = body.get("session_ref")
    events = body.get("events")
    if not isinstance(events, list):
        return create_error_response("events must be a list", 400, "INVALID_PAYLOAD")
    if len(events) > MAX_EVENTS_PER_REQUEST:
        return create_error_response("Too many events", 400, "TOO_MANY_EVENTS")

    result = ingest_site_marketing_events(
        session_ref=str(session_ref or ""),
        events=events,
        ensure_tables=True,
    )
    reason = result.get("reason")
    if reason == "INVALID_SESSION_REF":
        return create_error_response("Invalid session_ref", 400, "INVALID_SESSION_REF")
    if reason == "STORAGE_UNAVAILABLE":
        # Fail open for UX — client should ignore; report soft success
        return create_success_response(result, "Events not stored")
    return create_success_response(result, "Events ingested")
