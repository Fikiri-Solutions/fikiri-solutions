#!/usr/bin/env python3
"""
Central user feedback router.

Stores normalized feedback events with deterministic routing metadata so
feedback from different endpoints can be audited in one place.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_MAX_DB_RETRIES = 3
_RETRY_BASE_SLEEP_SECONDS = 0.05

# Lower-case substrings we treat as "transient lock/contention" and retry.
# These cover the messages emitted by both sqlite3 (`database is locked`,
# `database is busy`) and psycopg2 (`deadlock detected`, `could not obtain
# lock`, `canceling statement due to lock timeout`). Matching on the message
# instead of the driver-specific exception class keeps this module portable
# across both backends.
_TRANSIENT_DB_ERROR_TOKENS = ("locked", "busy", "deadlock", "lock timeout")


class UserFeedbackRouter:
    """Route and persist normalized feedback events."""

    def record_feedback_event(
        self,
        *,
        source: str,
        user_id: Optional[str],
        tenant_id: Optional[str],
        category: str,
        payload: Dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {"success": False, "error": "payload must be an object", "error_code": "INVALID_PAYLOAD"}

        if not db_optimizer.table_exists("user_feedback_events"):
            return {
                "success": False,
                "error": "user_feedback_events table not available",
                "error_code": "TABLE_NOT_AVAILABLE",
            }

        normalized_category = (category or "general").strip().lower() or "general"
        route = self._determine_route(normalized_category, payload)
        payload_json = json.dumps(payload, default=str)[:50000]
        dedupe_key = self._build_idempotency_key(
            source=source,
            category=normalized_category,
            payload=payload,
            conversation_id=conversation_id,
            message_id=message_id,
            explicit=idempotency_key,
        )

        params = (
            source,
            str(user_id) if user_id is not None else None,
            str(tenant_id) if tenant_id is not None else None,
            normalized_category,
            route,
            conversation_id,
            message_id,
            correlation_id,
            payload_json,
            dedupe_key,
        )
        sql = """
            INSERT INTO user_feedback_events (
                source, user_id, tenant_id, category, route,
                conversation_id, message_id, correlation_id, payload_json, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                correlation_id = COALESCE(excluded.correlation_id, user_feedback_events.correlation_id),
                route = excluded.route,
                category = excluded.category,
                updated_at = CURRENT_TIMESTAMP
        """

        try:
            event_id = self._execute_with_retry(sql, params)
            return {
                "success": True,
                "event_id": event_id,
                "route": route,
                "idempotency_key": dedupe_key,
            }
        except Exception as exc:
            logger.error("Failed to persist feedback event: %s", exc)
            return {"success": False, "error": str(exc), "error_code": "PERSIST_FAILED"}

    def _determine_route(self, category: str, payload: Dict[str, Any]) -> str:
        if category in {"chatbot", "response_quality", "answer_quality"}:
            return "chatbot.quality"
        if category in {"bug", "error_report"}:
            return "product.bug"
        if category in {"feature_request", "feature"}:
            return "product.feature_request"
        if category in {"nps", "csat", "satisfaction"}:
            return "customer.satisfaction"
        if "helpful" in payload:
            return "chatbot.quality"
        return "product.general"

    def _build_idempotency_key(
        self,
        *,
        source: str,
        category: str,
        payload: Dict[str, Any],
        conversation_id: Optional[str],
        message_id: Optional[str],
        explicit: Optional[str],
    ) -> str:
        if explicit and str(explicit).strip():
            return str(explicit).strip()[:120]
        raw = json.dumps(
            {
                "source": source,
                "category": category,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "payload": payload,
            },
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()

    def _execute_with_retry(self, query: str, params: tuple) -> Optional[int]:
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_DB_RETRIES):
            try:
                return db_optimizer.execute_query(query, params, fetch=False)
            except Exception as exc:
                msg = str(exc).lower()
                if not any(token in msg for token in _TRANSIENT_DB_ERROR_TOKENS):
                    raise
                last_error = exc
                if attempt < _MAX_DB_RETRIES - 1:
                    time.sleep(_RETRY_BASE_SLEEP_SECONDS * (2**attempt))
        raise last_error or RuntimeError("feedback insert failed after retries")


_feedback_router: Optional[UserFeedbackRouter] = None


def get_user_feedback_router() -> UserFeedbackRouter:
    global _feedback_router
    if _feedback_router is None:
        _feedback_router = UserFeedbackRouter()
    return _feedback_router
