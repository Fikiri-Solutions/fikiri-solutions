"""
Domain actions for public form intake update/cancel.
HTTP/auth/rate limits stay in core/webhook_api.py.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer
from core.workflow_followups import cancel_pending_work_for_lead
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)


def find_original_form_intake_row(
    user_id: int, form_id: str, client_submission_id: str
) -> Optional[Dict[str, Any]]:
    rows = db_optimizer.execute_query(
        """
        SELECT id, lead_id, email, name, phone, company, subject, source
        FROM customer_form_intake_submissions
        WHERE user_id = ? AND form_id = ?
          AND client_submission_id IS NOT NULL AND client_submission_id = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (user_id, form_id, client_submission_id),
    )
    if not rows:
        return None
    row = rows[0]
    return dict(row) if hasattr(row, "keys") else row


def _parse_lead_id(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def apply_form_update_to_lead(
    user_id: int,
    lead_id: int,
    *,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    lead_row = db_optimizer.execute_query(
        """
        SELECT id, metadata FROM leads WHERE id = ? AND user_id = ?
        """,
        (lead_id, user_id),
    )
    if not lead_row:
        return {"success": False, "error": "Lead not found", "error_code": "LEAD_NOT_FOUND"}

    row0 = dict(lead_row[0]) if lead_row[0] is not None else {}
    meta: Dict[str, Any] = {}
    try:
        meta = json.loads(row0.get("metadata") or "{}")
    except (json.JSONDecodeError, TypeError, KeyError):
        meta = {}

    if metadata:
        meta = {**meta, **metadata}
    if reason:
        meta["form_update_reason"] = reason
    meta["last_form_update_at"] = datetime.now(timezone.utc).isoformat()

    updates: Dict[str, Any] = {"metadata": meta}
    if name is not None:
        updates["name"] = name
    if phone is not None:
        updates["phone"] = phone
    if company is not None:
        updates["company"] = company
    if source is not None:
        updates["source"] = source
    if correlation_id is not None and str(correlation_id).strip():
        updates["correlation_id"] = str(correlation_id).strip()

    return enhanced_crm_service.update_lead(lead_id, user_id, updates)


def apply_form_cancel_to_lead(
    user_id: int,
    lead_id: int,
    *,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    lead_row = db_optimizer.execute_query(
        """
        SELECT id, tags, metadata FROM leads WHERE id = ? AND user_id = ?
        """,
        (lead_id, user_id),
    )
    if not lead_row:
        return {"success": False, "error": "Lead not found", "error_code": "LEAD_NOT_FOUND"}

    row = dict(lead_row[0])
    try:
        tags = json.loads(row.get("tags") or "[]")
    except (json.JSONDecodeError, TypeError):
        tags = []
    if not isinstance(tags, list):
        tags = []
    if "withdrawn_by_client" not in tags:
        tags.append("withdrawn_by_client")

    try:
        meta = json.loads(row.get("metadata") or "{}")
    except (json.JSONDecodeError, TypeError):
        meta = {}
    meta["withdrawn_by_client"] = True
    if reason:
        meta["form_cancel_reason"] = reason
    if metadata:
        meta = {**meta, **metadata}
    meta["withdrawn_at"] = datetime.now(timezone.utc).isoformat()

    cancel_pending_work_for_lead(user_id, lead_id, reason="withdrawn_by_client")

    upd: Dict[str, Any] = {"stage": "closed", "tags": tags, "metadata": meta}
    if correlation_id is not None and str(correlation_id).strip():
        upd["correlation_id"] = str(correlation_id).strip()

    result = enhanced_crm_service.update_lead(lead_id, user_id, upd)
    return result


def parse_lead_id_from_intake(raw: Any) -> Optional[int]:
    return _parse_lead_id(raw)
