"""
Append-only CRM event log. Inserts are best-effort: failures must never break CRM mutations.

event_type: use dot-separated verbs aligned with other domains, e.g. lead.created, lead.updated,
contact.created. Pass correlation_id from HTTP/automation/email when mutating so timelines stitch
across crm_events, email_events, and automation_run_events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Keep payloads bounded for SQLite row size and log volume
_MAX_PAYLOAD_BYTES = 16 * 1024

_schema_mode: Optional[str] = None


def _crm_events_schema_mode() -> str:
    """
    Detect legacy local DBs that still require tenant_user_id NOT NULL.

    Canonical schema (Postgres bootstrap / fresh SQLite) uses user_id only.
    """
    global _schema_mode
    if _schema_mode is not None:
        return _schema_mode
    cols = set(db_optimizer.list_table_columns("crm_events") or [])
    if "tenant_user_id" in cols:
        _schema_mode = "legacy"
    else:
        _schema_mode = "canonical"
    return _schema_mode


def record_crm_event(
    user_id: int,
    event_type: str,
    entity_type: str,
    entity_id: int,
    payload: Optional[Dict[str, Any]] = None,
    *,
    correlation_id: Optional[str] = None,
    supersedes_event_id: Optional[int] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    source: Optional[str] = None,
    **_ignored: Any,
) -> None:
    """
    Persist one CRM event. Swallows all errors after logging.
    """
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        truncated = 0
        payload_json: Optional[str] = None
        if payload is not None:
            raw = json.dumps(payload, default=str, separators=(",", ":"))
            enc = raw.encode("utf-8")
            if len(enc) > _MAX_PAYLOAD_BYTES:
                enc = enc[:_MAX_PAYLOAD_BYTES]
                truncated = 1
                payload_json = enc.decode("utf-8", errors="ignore")
            else:
                payload_json = raw

        if _crm_events_schema_mode() == "legacy":
            db_optimizer.execute_query(
                """
                INSERT INTO crm_events (
                    tenant_user_id, user_id, event_type, entity_type, entity_id,
                    correlation_id, supersedes_event_id,
                    payload_json, payload_truncated,
                    status, error_message, source,
                    occurred_at, created_at, actor_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'user')
                """,
                (
                    user_id,
                    user_id,
                    event_type,
                    entity_type,
                    entity_id,
                    correlation_id,
                    supersedes_event_id,
                    payload_json,
                    truncated,
                    status,
                    error_message,
                    source,
                    created_at,
                    created_at,
                ),
                fetch=False,
            )
        else:
            db_optimizer.execute_query(
                """
                INSERT INTO crm_events (
                    user_id, event_type, entity_type, entity_id,
                    correlation_id, supersedes_event_id,
                    payload_json, payload_truncated,
                    status, error_message, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    event_type,
                    entity_type,
                    entity_id,
                    correlation_id,
                    supersedes_event_id,
                    payload_json,
                    truncated,
                    status,
                    error_message,
                    source,
                    created_at,
                ),
                fetch=False,
            )
    except Exception as exc:  # noqa: BLE001 — intentional best-effort sink
        logger.warning(
            "crm_events insert failed (non-fatal): %s",
            exc,
            extra={
                "event": "crm_event_insert_failed",
                "service": "crm",
                "severity": "WARN",
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            },
        )


__all__ = ["record_crm_event"]
