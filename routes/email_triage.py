"""Inbox Command Center API: triage list + user-approved bulk actions."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from core.database_optimization import db_optimizer
from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.request_user_id import resolve_request_user_id
from core.secure_sessions import get_current_user_id
from services.email_triage_service import (
    execute_bulk_action,
    list_triage_inbox,
    triage_and_store_synced_message,
)

logger = logging.getLogger(__name__)

email_triage_bp = Blueprint("email_triage", __name__, url_prefix="/api/email/triage")


@email_triage_bp.route("", methods=["GET"])
@handle_api_errors
def list_triage():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    category = request.args.get("category")
    cleanup_action = request.args.get("cleanup_action")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    data = list_triage_inbox(
        user_id,
        category=category,
        cleanup_action=cleanup_action,
        limit=limit,
        offset=offset,
    )
    return create_success_response(data, "Triage inbox retrieved")


@email_triage_bp.route("/classify", methods=["POST"])
@handle_api_errors
def classify_batch():
    """Classify synced messages by id (rules first; no auto-delete)."""
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=False)
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    body = request.get_json() or {}
    email_ids = body.get("email_ids") or []
    if not isinstance(email_ids, list):
        return create_error_response("email_ids must be a list", 400, "INVALID_PAYLOAD")

    classified = []
    for eid in email_ids[:50]:
        rows = db_optimizer.execute_query(
            """
            SELECT id, subject, sender, body, COALESCE(external_id, gmail_id) AS external_id, provider
            FROM synced_emails
            WHERE user_id = ? AND (external_id = ? OR gmail_id = ?)
            LIMIT 1
            """,
            (user_id, str(eid), str(eid)),
        )
        if not rows:
            continue
        row = rows[0]
        sender = row.get("sender") or ""
        email_addr = sender
        if "<" in sender and ">" in sender:
            email_addr = sender.split("<")[1].split(">")[0].strip()
        triage = triage_and_store_synced_message(
            user_id,
            external_id=str(row.get("external_id") or eid),
            subject=row.get("subject") or "",
            body=row.get("body") or "",
            sender_email=email_addr,
            sender_name=sender.split("<")[0].strip() if "<" in sender else sender,
            provider=row.get("provider") or "gmail",
            synced_email_id=int(row["id"]) if row.get("id") is not None else None,
        )
        classified.append({"email_id": eid, "triage": triage})

    return create_success_response(
        {"classified": classified, "count": len(classified)},
        "Classification complete",
    )


@email_triage_bp.route("/bulk-action", methods=["POST"])
@handle_api_errors
def bulk_action():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=False)
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    body = request.get_json() or {}
    action = body.get("action")
    email_ids = body.get("email_ids") or []
    confirm = bool(body.get("confirm_destructive"))
    label_names = body.get("label_names") or body.get("labels")

    result = execute_bulk_action(
        user_id,
        action=str(action or ""),
        email_ids=[str(x) for x in email_ids],
        confirm_destructive=confirm,
        label_names=label_names if isinstance(label_names, list) else None,
    )
    if result.get("code") == "CONFIRMATION_REQUIRED":
        return create_error_response(result.get("error", "Confirmation required"), 400, "CONFIRMATION_REQUIRED")
    if not result.get("processed") and result.get("errors"):
        return create_error_response("Bulk action failed", 500, "BULK_ACTION_FAILED")
    return create_success_response(result, "Bulk action completed")
