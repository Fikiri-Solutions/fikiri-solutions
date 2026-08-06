"""Product analytics ingestion — validate, authorize, persist.

Failures are contained: storage outages do not claim success; invalid events reject.
Never logs property values.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.product_analytics_registry import (
    MEANINGFUL_OUTCOME_EVENTS,
    product_analytics_enabled,
    validate_event_properties,
)
from core.product_analytics_store import (
    ensure_product_analytics_tables,
    increment_ops_counter,
    insert_product_event,
    tables_available,
    upsert_daily_metric_counters,
)

logger = logging.getLogger(__name__)

MAX_EVENTS_PER_REQUEST = 20
MAX_BODY_EVENTS_CHARS = 32_000


def _hash_session(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:48]


def _parse_client_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _increments_for_event(event_name: str) -> Dict[str, int]:
    inc: Dict[str, int] = {"active_users": 1}
    if event_name == "session.started":
        inc["sessions"] = 1
    if event_name in MEANINGFUL_OUTCOME_EVENTS or event_name == "onboarding.step_completed":
        inc["meaningful_actions"] = 1
    if event_name == "workflow.started":
        inc["workflow_started"] = 1
    if event_name == "workflow.failed":
        inc["workflow_failed"] = 1
    if event_name == "error.category":
        inc["error_count"] = 1
    return inc


def ingest_product_events(
    *,
    tenant_id: int,
    actor_user_id: int,
    events: List[Dict[str, Any]],
    impersonating: bool = False,
    platform_admin_surface: bool = False,
    ensure_tables: bool = False,
) -> Dict[str, Any]:
    """Ingest a batch of events for the authenticated tenant.

    Identity must already be derived from the session — never from event payloads.
    """
    if not product_analytics_enabled():
        return {
            "accepted": 0,
            "rejected": 0,
            "analytics_available": False,
            "analytics_enabled": False,
            "rejection_reasons": [],
        }

    if impersonating:
        logger.info(
            "product_analytics impersonation excluded",
            extra={"event": "product_analytics.impersonation_excluded", "tenant_id": tenant_id},
        )
        return {
            "accepted": 0,
            "rejected": 0,
            "analytics_available": True,
            "analytics_enabled": True,
            "excluded": "IMPERSONATION",
            "rejection_reasons": [],
        }

    if platform_admin_surface:
        return {
            "accepted": 0,
            "rejected": 0,
            "analytics_available": True,
            "analytics_enabled": True,
            "excluded": "PLATFORM_ADMIN_SURFACE",
            "rejection_reasons": [],
        }

    if ensure_tables:
        try:
            ensure_product_analytics_tables()
        except Exception:
            pass

    if not tables_available():
        logger.warning(
            "product_analytics storage unavailable",
            extra={"event": "product_analytics.storage_unavailable"},
        )
        try:
            increment_ops_counter(int(tenant_id), storage_failures=1)
        except Exception:
            pass
        return {
            "accepted": 0,
            "rejected": 0,
            "analytics_available": False,
            "analytics_enabled": True,
            "rejection_reasons": [],
        }

    if not isinstance(events, list):
        return {
            "accepted": 0,
            "rejected": 1,
            "analytics_available": True,
            "analytics_enabled": True,
            "rejection_reasons": [{"index": 0, "reason": "INVALID_BATCH"}],
        }

    if len(events) > MAX_EVENTS_PER_REQUEST:
        return {
            "accepted": 0,
            "rejected": len(events),
            "analytics_available": True,
            "analytics_enabled": True,
            "rejection_reasons": [{"index": -1, "reason": "BATCH_TOO_LARGE"}],
        }

    accepted = 0
    rejected = 0
    reasons: List[Dict[str, Any]] = []
    received_at = datetime.now(timezone.utc)

    for idx, raw in enumerate(events):
        if not isinstance(raw, dict):
            rejected += 1
            reasons.append({"index": idx, "reason": "INVALID_EVENT"})
            continue
        event_name = str(raw.get("event_name") or raw.get("name") or "").strip()
        event_source = str(raw.get("event_source") or "client").strip().lower()
        properties = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
        # Ignore any client identity fields even if nested
        properties = {
            k: v
            for k, v in properties.items()
            if k not in {"tenant_id", "user_id", "actor_user_id"}
        }

        ok, reason, sanitized = validate_event_properties(
            event_name, properties, event_source=event_source
        )
        if not ok:
            rejected += 1
            reasons.append({"index": idx, "reason": reason or "REJECTED", "event_name": event_name or None})
            logger.info(
                "product_analytics event rejected",
                extra={
                    "event": "product_analytics.rejected",
                    "reason": reason,
                    "event_name": event_name or None,
                },
            )
            try:
                increment_ops_counter(int(tenant_id), rejected_events=1)
            except Exception:
                pass
            continue

        client_ts = _parse_client_ts(raw.get("client_timestamp") or raw.get("occurred_at"))
        occurred_at = received_at
        # Client timestamp only for latency comparison — do not trust far-future/past widely
        if client_ts is not None:
            delta = abs((client_ts - received_at).total_seconds())
            if delta <= 86400:
                occurred_at = client_ts

        session_hash = sanitized.get("session_id_hash") or _hash_session(raw.get("session_id"))
        if session_hash and "session_id_hash" not in sanitized:
            sanitized = {**sanitized, "session_id_hash": session_hash}

        dedupe = raw.get("outcome_dedupe_key")
        if dedupe is not None:
            dedupe = str(dedupe).strip()[:128] or None
            if event_source == "client":
                # Clients must not set outcome dedupe for authoritative outcomes
                if event_name.startswith("outcome."):
                    rejected += 1
                    reasons.append({"index": idx, "reason": "CLIENT_OUTCOME_FORBIDDEN", "event_name": event_name})
                    continue

        try:
            row_id = insert_product_event(
                tenant_id=int(tenant_id),
                actor_user_id=int(actor_user_id),
                event_name=event_name,
                event_source=event_source,
                properties=sanitized,
                occurred_at=occurred_at,
                session_id_hash=session_hash,
                correlation_id=sanitized.get("correlation_id"),
                outcome_dedupe_key=dedupe if event_source in {"server", "derived"} else None,
            )
        except Exception:
            # Storage failure mid-batch: do not claim remaining as stored
            logger.warning(
                "product_analytics storage failure during ingest",
                extra={"event": "product_analytics.storage_failure"},
            )
            try:
                increment_ops_counter(int(tenant_id), storage_failures=1)
            except Exception:
                pass
            return {
                "accepted": accepted,
                "rejected": rejected,
                "analytics_available": False,
                "analytics_enabled": True,
                "rejection_reasons": reasons,
            }

        if row_id is None and dedupe:
            # Duplicate outcome — not an error, not a new accept
            continue
        if row_id is None:
            # Insert returned None without dedupe — treat as storage gap
            try:
                increment_ops_counter(int(tenant_id), storage_failures=1)
            except Exception:
                pass
            return {
                "accepted": accepted,
                "rejected": rejected,
                "analytics_available": False,
                "analytics_enabled": True,
                "rejection_reasons": reasons,
            }

        accepted += 1
        metric_date = occurred_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        upsert_daily_metric_counters(
            tenant_id=int(tenant_id),
            metric_date=metric_date,
            increments=_increments_for_event(event_name),
            feature_key=sanitized.get("feature_key"),
            last_event_at=occurred_at,
        )

    return {
        "accepted": accepted,
        "rejected": rejected,
        "analytics_available": True,
        "analytics_enabled": True,
        "rejection_reasons": reasons[:20],
    }
