"""
Append-only email / AI assistant event log. Inserts are best-effort.

event_type: prefix with email. (e.g. email.parsed, email.failed). status: use applied | failed for
outcomes; set error_message when status is failed. Always pass correlation_id when the caller has one.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_MAX_PAYLOAD_BYTES = 16 * 1024


def record_email_event(
    user_id: int,
    event_type: str,
    *,
    provider: Optional[str] = None,
    message_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    synced_email_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    supersedes_event_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    source: Optional[str] = None,
) -> None:
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

        db_optimizer.execute_query(
            """
            INSERT INTO email_events (
                created_at, user_id, event_type, provider,
                message_id, thread_id, synced_email_id, lead_id,
                correlation_id, supersedes_event_id, idempotency_key,
                payload_json, payload_truncated,
                status, error_message, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                user_id,
                event_type,
                provider,
                message_id,
                thread_id,
                synced_email_id,
                lead_id,
                correlation_id,
                supersedes_event_id,
                idempotency_key,
                payload_json,
                truncated,
                status,
                error_message,
                source,
            ),
            fetch=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "email_events insert failed (non-fatal): %s",
            exc,
            extra={
                "event": "email_event_insert_failed",
                "service": "email",
                "severity": "WARN",
                "event_type": event_type,
                "user_id": user_id,
            },
        )


__all__ = ["record_email_event"]
