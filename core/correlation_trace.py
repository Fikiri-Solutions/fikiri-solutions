"""
Tenant-scoped correlation trace: aggregate matching rows from domain event tables (no universal table).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 50


def _rows(query: str, params: tuple) -> List[Dict[str, Any]]:
    try:
        raw = db_optimizer.execute_query(query, params, fetch=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("correlation_trace query failed: %s", exc)
        return []
    if not raw:
        return []
    out: List[Dict[str, Any]] = []
    for row in raw:
        out.append(dict(row) if not isinstance(row, dict) else row)
    return out


def fetch_correlation_trace(
    user_id: int,
    correlation_id: str,
    *,
    limit: int = _DEFAULT_LIMIT,
) -> Dict[str, Any]:
    """
    Return slices of domain tables where correlation_id matches and user_id scopes access.
    """
    cid = (correlation_id or "").strip()
    if not cid or len(cid) > 128:
        return {"correlation_id": cid, "error": "invalid_correlation_id", "sections": {}}

    lim = max(1, min(int(limit), 100))

    sections: Dict[str, Any] = {
        "crm_events": _rows(
            """
            SELECT id, event_type, entity_type, entity_id, status, source, created_at, payload_truncated
            FROM crm_events
            WHERE user_id = ? AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        ),
        "automation_run_events": _rows(
            """
            SELECT id, created_at, run_id, job_id, event_type, entity_type, entity_id, status, source, payload_truncated
            FROM automation_run_events
            WHERE user_id = ? AND correlation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        ),
        "email_events": _rows(
            """
            SELECT id, created_at, event_type, provider, message_id, thread_id, lead_id, status, source, payload_truncated
            FROM email_events
            WHERE user_id = ? AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        ),
        "ai_events": _rows(
            """
            SELECT id, created_at, event_type, entity_type, entity_id, status, source, payload_truncated
            FROM ai_events
            WHERE user_id = ? AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        ),
        "automation_jobs": [],
        "chatbot_content_events": _rows(
            """
            SELECT id, created_at, event_type, entity_type, entity_id, status, source, payload_truncated
            FROM chatbot_content_events
            WHERE user_id = ? AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        ),
    }

    try:
        cid_expr = db_optimizer.json_field_expr("payload_json", "$.correlation_id")
        job_rows = _rows(
            f"""
            SELECT job_id, payload_type, status, attempt, created_at, started_at, completed_at, error_message
            FROM automation_jobs
            WHERE user_id = ? AND {cid_expr} = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, cid, lim),
        )
        sections["automation_jobs"] = job_rows
    except Exception as exc:  # noqa: BLE001
        logger.debug("automation_jobs correlation trace skipped: %s", exc)
        sections["automation_jobs"] = []

    return {
        "correlation_id": cid,
        "user_id": user_id,
        "limits": {"per_section": lim},
        "sections": sections,
        "notes": [
            "Scoped to authenticated user_id only.",
            "Form intake rows do not store correlation_id in SQLite; use API/idempotency cache for that link.",
        ],
    }
