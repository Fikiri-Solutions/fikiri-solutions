"""Internal automation ingress HTTP boundary (Windmill CE pilot).

Thin route: parse request, authenticate API key, map status codes.
Domain logic lives in core.automation_event_ingress.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from core.api_key_manager import api_key_manager
from core.automation_event_ingress import (
    MAX_HTTP_BODY_BYTES,
    IngressPrincipal,
    REQUIRED_SCOPE,
    audit_insufficient_scope,
    handle_automation_test_event,
    log_unauthenticated_failure,
    principal_has_ingress_scope,
    validate_event_payload,
)
from core.automation_windmill_trigger import (
    handle_normalize_leads_trigger,
    validate_normalize_trigger_payload,
)

logger = logging.getLogger(__name__)

internal_automation_bp = Blueprint(
    "internal_automation",
    __name__,
    url_prefix="/api/internal/automation",
)


def _authenticate_ingress() -> tuple[IngressPrincipal | None, tuple | None]:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        log_unauthenticated_failure(reason="missing_api_key", ip_address=request.remote_addr)
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "API key required (X-API-Key header)",
                    "error_code": "MISSING_API_KEY",
                }
            ),
            401,
        )

    key_info = api_key_manager.validate_api_key(api_key)
    if not key_info:
        log_unauthenticated_failure(reason="invalid_api_key", ip_address=request.remote_addr)
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid API key",
                    "error_code": "INVALID_API_KEY",
                }
            ),
            401,
        )

    scopes = key_info.get("scopes") or []
    principal = IngressPrincipal(
        user_id=int(key_info["user_id"]),
        api_key_id=int(key_info["api_key_id"]),
        key_prefix=(key_info.get("key_prefix") or "")[:12],
        scopes=list(scopes) if isinstance(scopes, list) else [],
    )

    if not principal_has_ingress_scope(principal.scopes):
        correlation_hint = None
        try:
            body = request.get_json(silent=True) or {}
            if isinstance(body, dict):
                correlation_hint = body.get("correlation_id")
        except Exception:
            correlation_hint = None
        audit_insufficient_scope(
            principal,
            ip_address=request.remote_addr,
            user_agent=(request.headers.get("User-Agent") or "")[:512] or None,
            correlation_id=correlation_hint if isinstance(correlation_hint, str) else None,
        )
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": f"Insufficient permissions. Required scope: {REQUIRED_SCOPE}",
                    "error_code": "INSUFFICIENT_SCOPE",
                }
            ),
            403,
        )

    return principal, None


@internal_automation_bp.route("/events", methods=["POST"])
def post_automation_event():
    raw_len = request.content_length
    if raw_len is not None and raw_len > MAX_HTTP_BODY_BYTES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Request body too large",
                    "error_code": "PAYLOAD_TOO_LARGE",
                }
            ),
            413,
        )

    raw_body = request.get_data(cache=True, as_text=False) or b""
    if len(raw_body) > MAX_HTTP_BODY_BYTES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Request body too large",
                    "error_code": "PAYLOAD_TOO_LARGE",
                }
            ),
            413,
        )

    principal, err = _authenticate_ingress()
    if err is not None:
        return err

    payload_json = request.get_json(silent=True)
    normalized, validation_error = validate_event_payload(payload_json)
    if validation_error is not None:
        return jsonify(validation_error), 400

    assert principal is not None and normalized is not None
    result = handle_automation_test_event(
        normalized,
        principal=principal,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:512] or None,
    )
    return jsonify(result.body), result.http_status


@internal_automation_bp.route("/jobs/normalize-leads", methods=["POST"])
def post_normalize_leads_job():
    """Enqueue (or optionally wait for) Windmill normalize_leads. Opt-in via env."""
    raw_len = request.content_length
    if raw_len is not None and raw_len > MAX_HTTP_BODY_BYTES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Request body too large",
                    "error_code": "PAYLOAD_TOO_LARGE",
                }
            ),
            413,
        )

    raw_body = request.get_data(cache=True, as_text=False) or b""
    if len(raw_body) > MAX_HTTP_BODY_BYTES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Request body too large",
                    "error_code": "PAYLOAD_TOO_LARGE",
                }
            ),
            413,
        )

    principal, err = _authenticate_ingress()
    if err is not None:
        return err

    payload_json = request.get_json(silent=True)
    normalized, validation_error = validate_normalize_trigger_payload(payload_json)
    if validation_error is not None:
        return jsonify(validation_error), 400

    assert principal is not None and normalized is not None
    result = handle_normalize_leads_trigger(
        normalized,
        principal=principal,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:512] or None,
    )
    return jsonify(result.body), result.http_status
