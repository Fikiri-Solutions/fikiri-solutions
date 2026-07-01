"""Staff-only transcript read API for the Fikiri marketing site bot."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from company_chatbot.transcript_store import (
    build_transcript_export,
    get_transcript_session,
    list_transcript_sessions,
    record_transcript_audit,
)
from company_chatbot.miss_review import (
    export_miss_cursor_patch,
    get_miss_proposal,
    list_likely_misses,
    parse_miss_id,
)
from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.billing_api import _get_user_role, _is_admin_user
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

admin_site_chat_bp = Blueprint("admin_site_chat", __name__, url_prefix="/api/admin/site-chat")

SITE_CHAT_READ_CAPABILITY = "site_chat.read_transcripts"


def _can_read_site_chat_transcripts(user_id) -> bool:
    if not user_id:
        return False
    if _is_admin_user(user_id):
        return True
    role = str(_get_user_role(user_id) or "").strip().lower()
    return role in ("admin", "owner")


def _require_transcript_reader():
    user_id = get_current_user_id()
    if not user_id:
        return None, create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    if not _can_read_site_chat_transcripts(user_id):
        return None, create_error_response("Forbidden", 403, "FORBIDDEN")
    return user_id, None


@admin_site_chat_bp.route("/sessions", methods=["GET"])
@handle_api_errors
def list_site_chat_sessions():
    user_id, err = _require_transcript_reader()
    if err:
        return err

    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0

    result = list_transcript_sessions(
        limit=limit,
        offset=offset,
        tier=(request.args.get("tier") or "").strip() or None,
        mode=(request.args.get("mode") or "").strip() or None,
        date_from=(request.args.get("date_from") or "").strip() or None,
        date_to=(request.args.get("date_to") or "").strip() or None,
    )
    return create_success_response(result, "Site chat sessions retrieved")


@admin_site_chat_bp.route("/sessions/<session_id>", methods=["GET"])
@handle_api_errors
def get_site_chat_session(session_id: str):
    user_id, err = _require_transcript_reader()
    if err:
        return err

    session_id = (session_id or "").strip()
    if not session_id:
        return create_error_response("session_id is required", 400, "MISSING_SESSION_ID")

    payload = get_transcript_session(session_id)
    if not payload:
        return create_error_response("Transcript session not found", 404, "SESSION_NOT_FOUND")

    record_transcript_audit(session_id, str(user_id), "read")
    return create_success_response(payload, "Site chat session retrieved")


@admin_site_chat_bp.route("/sessions/<session_id>/export", methods=["GET"])
@handle_api_errors
def export_site_chat_session(session_id: str):
    user_id, err = _require_transcript_reader()
    if err:
        return err

    session_id = (session_id or "").strip()
    if not session_id:
        return create_error_response("session_id is required", 400, "MISSING_SESSION_ID")

    export_format = (request.args.get("format") or "text").strip().lower()
    if export_format not in ("text", "json"):
        export_format = "text"

    exported = build_transcript_export(session_id, export_format=export_format)
    if not exported:
        return create_error_response("Transcript session not found", 404, "SESSION_NOT_FOUND")

    record_transcript_audit(session_id, str(user_id), "export")
    return create_success_response(exported, "Site chat transcript exported")


@admin_site_chat_bp.route("/misses", methods=["GET"])
@handle_api_errors
def list_site_chat_misses():
    user_id, err = _require_transcript_reader()
    if err:
        return err

    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0

    min_priority = (request.args.get("min_priority") or "").strip() or None
    result = list_likely_misses(limit=limit, offset=offset, min_priority=min_priority)
    record_transcript_audit("miss_review", str(user_id), "list_misses")
    return create_success_response(result, "Site chat likely misses retrieved")


@admin_site_chat_bp.route("/misses/<miss_id>", methods=["GET"])
@handle_api_errors
def get_site_chat_miss_proposal(miss_id: str):
    user_id, err = _require_transcript_reader()
    if err:
        return err

    try:
        session_id, turn_index = parse_miss_id(miss_id)
    except ValueError:
        return create_error_response("Invalid miss_id", 400, "INVALID_MISS_ID")

    payload = get_miss_proposal(session_id, turn_index)
    if not payload:
        return create_error_response("Miss turn not found", 404, "MISS_NOT_FOUND")

    record_transcript_audit(session_id, str(user_id), "miss_proposal")
    return create_success_response(payload, "Site chat miss proposal retrieved")


@admin_site_chat_bp.route("/misses/<miss_id>/export", methods=["GET"])
@handle_api_errors
def export_site_chat_miss_patch(miss_id: str):
    user_id, err = _require_transcript_reader()
    if err:
        return err

    try:
        session_id, turn_index = parse_miss_id(miss_id)
    except ValueError:
        return create_error_response("Invalid miss_id", 400, "INVALID_MISS_ID")

    exported = export_miss_cursor_patch(session_id, turn_index)
    if not exported:
        return create_error_response("Miss turn not found", 404, "MISS_NOT_FOUND")

    record_transcript_audit(session_id, str(user_id), "miss_export")
    return create_success_response(exported, "Site chat miss Cursor patch exported")
