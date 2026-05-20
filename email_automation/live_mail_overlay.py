"""Batch local classification/workflow overlay for Live Mail (read-only)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.email_triage_store import ensure_email_classifications_table, fetch_classifications_by_external_ids
from email_automation.email_workflow_state import (
    ensure_email_workflow_state_table,
    fetch_workflow_by_external_ids,
    workflow_status_is_handled,
)

logger = logging.getLogger(__name__)

OVERLAY_FIELD_NAMES = frozenset(
    {
        "classification_category",
        "classification_confidence",
        "lead_score",
        "urgency_score",
        "workflow_status",
        "classification_status",
        "last_action",
        "handled_at",
        "is_locally_archived",
        "is_locally_handled",
    }
)


def _overlay_from_rows(
    classification_row: Optional[Dict[str, Any]],
    workflow_row: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not classification_row and not workflow_row:
        return None

    overlay: Dict[str, Any] = {}
    if classification_row:
        overlay["classification_category"] = classification_row.get("category")
        overlay["classification_confidence"] = classification_row.get("confidence")
        overlay["lead_score"] = classification_row.get("lead_score")
        overlay["urgency_score"] = classification_row.get("urgency_score")

    workflow_status = None
    if workflow_row:
        workflow_status = str(workflow_row.get("workflow_status") or "active")
        overlay["workflow_status"] = workflow_status
        overlay["classification_status"] = workflow_row.get("classification_status")
        overlay["last_action"] = workflow_row.get("last_action")
        overlay["handled_at"] = workflow_row.get("handled_at")
    elif classification_row:
        overlay["classification_status"] = "classified"

    ws = workflow_status or "active"
    overlay["is_locally_archived"] = ws == "archived"
    hidden_cc = int((workflow_row or {}).get("hidden_from_command_center") or 0)
    overlay["is_locally_handled"] = workflow_status_is_handled(ws) or bool(hidden_cc)

    return overlay


def enrich_live_mail_messages(
    user_id: int,
    emails: List[Dict[str, Any]],
    *,
    provider: str = "gmail",
) -> List[Dict[str, Any]]:
    """
    Attach optional local state fields to each message dict (by Gmail message id).
    Best-effort: returns input unchanged on lookup failure.
    """
    if not emails:
        return emails

    external_ids = [
        str(e.get("id") or "").strip()
        for e in emails
        if e.get("id")
    ]
    if not external_ids:
        return emails

    try:
        ensure_email_classifications_table()
        ensure_email_workflow_state_table()
        classifications = fetch_classifications_by_external_ids(
            user_id, external_ids, provider=provider
        )
        workflows = fetch_workflow_by_external_ids(
            user_id, external_ids, provider=provider
        )
    except Exception as exc:
        logger.warning(
            "live_mail_overlay skipped user=%s count=%s: %s",
            user_id,
            len(external_ids),
            exc,
        )
        return emails

    for email in emails:
        eid = str(email.get("id") or "").strip()
        if not eid:
            continue
        overlay = _overlay_from_rows(
            classifications.get(eid),
            workflows.get(eid),
        )
        if overlay:
            email.update(overlay)

    return emails
