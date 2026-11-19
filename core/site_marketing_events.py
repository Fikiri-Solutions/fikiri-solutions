"""Anonymous public marketing-site funnel events (intake + chatbot).

First-party collector used because Vercel custom events require Pro/Enterprise.
Never store names, emails, phones, form free text, or chat transcripts.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
MAX_EVENTS_PER_REQUEST = 20
MAX_SESSION_REF_LEN = 64
MAX_DEDUPE_KEY_LEN = 80
MAX_PROP_VALUE_LEN = 64
RAW_RETENTION_DAYS_DEFAULT = 90

APPROVED_EVENTS = frozenset(
    {
        "intake_started",
        "intake_step_viewed",
        "intake_submitted",
        "booking_clicked",
        "chatbot_opened",
        "chatbot_first_message",
        "chatbot_fallback",
        "chatbot_handoff",
    }
)

# Properties allowed per event (all optional except where noted by callers).
ALLOWED_PROPS: Dict[str, frozenset] = {
    "intake_started": frozenset({"source_kind"}),
    "intake_step_viewed": frozenset({"step_id"}),
    "intake_submitted": frozenset({"source_kind", "preferred_next_step", "priority_band"}),
    "booking_clicked": frozenset({"surface"}),
    "chatbot_opened": frozenset({"path_bucket"}),
    "chatbot_first_message": frozenset(),
    "chatbot_fallback": frozenset({"mode"}),
    "chatbot_handoff": frozenset({"handoff_type"}),
}

PROHIBITED_PROP_KEYS = frozenset(
    {
        "email",
        "name",
        "phone",
        "message",
        "notes",
        "body",
        "password",
        "token",
        "authorization",
        "cookie",
        "secret",
        "code",
        "card",
        "clipboard",
        "business_name",
        "contact_name",
        "main_pain",
        "transcript",
        "user_id",
        "tenant_id",
    }
)

_STEP_IDS = frozenset({"services", "detail", "context", "contact", "ready", "next"})
_SOURCE_KINDS = frozenset(
    {
        "consultation_intake_short",
        "consultation_intake",
        "site_chatbot",
        "organic",
        "other",
    }
)
_PRIORITY_BANDS = frozenset({"priority", "warm", "nurture"})
_NEXT_STEPS = frozenset({"book", "email", "not_sure"})
_HANDOFF_TYPES = frozenset({"contact", "intake", "other"})
_PATH_BUCKET_RE = re.compile(r"^/[A-Za-z0-9/_-]{0,62}$")

_TABLES_READY = False


def site_marketing_events_enabled() -> bool:
    raw = (os.getenv("SITE_MARKETING_EVENTS_ENABLED") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def raw_retention_days() -> int:
    try:
        days = int((os.getenv("SITE_MARKETING_EVENTS_RETENTION_DAYS") or str(RAW_RETENTION_DAYS_DEFAULT)).strip())
    except ValueError:
        days = RAW_RETENTION_DAYS_DEFAULT
    return max(7, min(days, 400))


def ensure_site_marketing_event_tables() -> None:
    global _TABLES_READY
    if _TABLES_READY and db_optimizer.table_exists("site_marketing_events"):
        return
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS site_marketing_events (
            id BIGSERIAL PRIMARY KEY,
            event_name TEXT NOT NULL,
            session_ref TEXT NOT NULL,
            dedupe_key TEXT NOT NULL DEFAULT '',
            properties_json TEXT,
            occurred_at TIMESTAMP NOT NULL,
            received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            schema_version INTEGER NOT NULL DEFAULT 1
        )
        """,
        fetch=False,
    )
    for stmt in (
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_site_marketing_events_dedupe
        ON site_marketing_events (event_name, session_ref, dedupe_key)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_site_marketing_events_name_occurred
        ON site_marketing_events (event_name, occurred_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_site_marketing_events_occurred
        ON site_marketing_events (occurred_at)
        """,
    ):
        try:
            db_optimizer.execute_query(stmt, fetch=False)
        except Exception:
            # Index may already exist with engine-specific syntax.
            pass
    _TABLES_READY = True


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_occurred_at(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        text = raw.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utc_now()


def _normalize_session_ref(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or len(value) > MAX_SESSION_REF_LEN:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return None
    return value


def _normalize_dedupe_key(raw: Any) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, (str, int)):
        return ""
    value = str(raw).strip()[:MAX_DEDUPE_KEY_LEN]
    if not value:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        return ""
    return value


def _bounded_enum(value: Any, allowed: frozenset, *, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.strip().lower()[:MAX_PROP_VALUE_LEN]
    if cleaned in allowed:
        return cleaned
    return fallback


def _sanitize_properties(event_name: str, props: Any) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    if props is None:
        props = {}
    if not isinstance(props, dict):
        return None, "INVALID_PROPERTIES"
    allowed = ALLOWED_PROPS.get(event_name, frozenset())
    out: Dict[str, str] = {}
    for key, value in props.items():
        if not isinstance(key, str):
            return None, "INVALID_PROPERTY_KEY"
        key_l = key.strip().lower()
        if key_l in PROHIBITED_PROP_KEYS or any(p in key_l for p in ("email", "phone", "token", "secret", "password")):
            return None, "PROHIBITED_PROPERTY"
        if key_l not in allowed:
            return None, "UNKNOWN_PROPERTY"
        if not isinstance(value, (str, int, bool)) or value is None:
            return None, "INVALID_PROPERTY_VALUE"
        text = str(value).strip()[:MAX_PROP_VALUE_LEN]
        if key_l == "step_id":
            text = _bounded_enum(text, _STEP_IDS)
            if not text:
                return None, "INVALID_STEP_ID"
        elif key_l == "source_kind":
            text = _bounded_enum(text, _SOURCE_KINDS, fallback="other") or "other"
        elif key_l == "priority_band":
            text = _bounded_enum(text, _PRIORITY_BANDS)
            if not text:
                continue
        elif key_l == "preferred_next_step":
            text = _bounded_enum(text, _NEXT_STEPS)
            if not text:
                continue
        elif key_l == "handoff_type":
            text = _bounded_enum(text, _HANDOFF_TYPES, fallback="other") or "other"
        elif key_l == "path_bucket":
            if not isinstance(value, str) or not _PATH_BUCKET_RE.fullmatch(value.strip()[:64]):
                text = "/"
            else:
                text = value.strip()[:64]
        elif key_l == "mode":
            text = re.sub(r"[^a-z0-9_]", "", text.lower())[:32] or "unknown"
        elif key_l == "surface":
            text = re.sub(r"[^a-z0-9_]", "", text.lower())[:32] or "unknown"
        out[key_l] = text
    return out, None


def _default_dedupe(event_name: str, props: Dict[str, str], explicit: str) -> str:
    if explicit:
        return explicit
    if event_name == "intake_step_viewed":
        return props.get("step_id", "")
    if event_name in {
        "intake_started",
        "intake_submitted",
        "chatbot_opened",
        "chatbot_first_message",
    }:
        return "once"
    return ""


def ingest_site_marketing_events(
    *,
    session_ref: str,
    events: List[Dict[str, Any]],
    ensure_tables: bool = True,
) -> Dict[str, Any]:
    if not site_marketing_events_enabled():
        return {
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "events_enabled": False,
        }

    ref = _normalize_session_ref(session_ref)
    if not ref:
        return {
            "accepted": 0,
            "rejected": len(events or []),
            "duplicates": 0,
            "events_enabled": True,
            "reason": "INVALID_SESSION_REF",
        }

    if not isinstance(events, list) or not events:
        return {
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "events_enabled": True,
            "reason": "EMPTY",
        }

    if len(events) > MAX_EVENTS_PER_REQUEST:
        return {
            "accepted": 0,
            "rejected": len(events),
            "duplicates": 0,
            "events_enabled": True,
            "reason": "TOO_MANY_EVENTS",
        }

    if ensure_tables:
        try:
            ensure_site_marketing_event_tables()
        except Exception as exc:
            logger.warning(
                "site_marketing_events table ensure failed",
                extra={
                    "event": "site_marketing_events.storage_unavailable",
                    "exception_class": type(exc).__name__,
                },
            )
            return {
                "accepted": 0,
                "rejected": len(events),
                "duplicates": 0,
                "events_enabled": True,
                "reason": "STORAGE_UNAVAILABLE",
            }

    accepted = 0
    rejected = 0
    duplicates = 0

    for item in events:
        if not isinstance(item, dict):
            rejected += 1
            continue
        event_name = str(item.get("event_name") or "").strip()
        if event_name not in APPROVED_EVENTS:
            rejected += 1
            continue
        props, prop_err = _sanitize_properties(event_name, item.get("properties"))
        if prop_err or props is None:
            rejected += 1
            logger.warning(
                "site_marketing_events reject",
                extra={
                    "event": "site_marketing_events.reject",
                    "reason": prop_err or "INVALID_PROPERTIES",
                    "event_name": event_name,
                },
            )
            continue
        dedupe = _default_dedupe(event_name, props, _normalize_dedupe_key(item.get("dedupe_key")))
        occurred_at = _parse_occurred_at(item.get("client_timestamp"))
        try:
            db_optimizer.execute_query(
                """
                INSERT INTO site_marketing_events (
                    event_name, session_ref, dedupe_key, properties_json,
                    occurred_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_name,
                    ref,
                    dedupe,
                    json.dumps(props, separators=(",", ":")),
                    occurred_at.isoformat(),
                    SCHEMA_VERSION,
                ),
                fetch=False,
            )
            accepted += 1
        except Exception as exc:
            msg = str(exc).lower()
            if "unique" in msg or "duplicate" in msg:
                duplicates += 1
            else:
                rejected += 1
                logger.warning(
                    "site_marketing_events insert failed",
                    extra={
                        "event": "site_marketing_events.insert_error",
                        "exception_class": type(exc).__name__,
                        "event_name": event_name,
                    },
                )

    return {
        "accepted": accepted,
        "rejected": rejected,
        "duplicates": duplicates,
        "events_enabled": True,
    }


def _count_events(event_name: str, since_iso: str) -> int:
    rows = db_optimizer.execute_query(
        """
        SELECT COUNT(*) AS c FROM site_marketing_events
        WHERE event_name = ? AND occurred_at >= ?
        """,
        (event_name, since_iso),
    )
    if not rows:
        return 0
    return int(rows[0].get("c") or rows[0].get("count") or 0)


def _step_view_counts(since_iso: str) -> Dict[str, int]:
    rows = db_optimizer.execute_query(
        """
        SELECT properties_json FROM site_marketing_events
        WHERE event_name = 'intake_step_viewed' AND occurred_at >= ?
        """,
        (since_iso,),
    ) or []
    counts = {step: 0 for step in ("services", "detail", "context", "contact", "ready", "next")}
    for row in rows:
        raw = row.get("properties_json") if isinstance(row, dict) else None
        try:
            props = json.loads(raw) if raw else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            props = {}
        step = str(props.get("step_id") or "")
        if step in counts:
            counts[step] += 1
    return counts


def _crm_intake_snapshot(since_iso: str) -> Dict[str, Any]:
    """Authoritative conversion snapshot from contact submissions (not click events)."""
    by_source: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    total = 0
    try:
        if not db_optimizer.table_exists("customer_contact_submissions"):
            return {"submissions": 0, "by_source": {}, "by_priority": {}, "available": False}
        rows = db_optimizer.execute_query(
            """
            SELECT payload_json, created_at
            FROM customer_contact_submissions
            WHERE form_type = 'consultation_intake' AND created_at >= ?
            """,
            (since_iso,),
        ) or []
        for row in rows:
            total += 1
            raw = row.get("payload_json") if isinstance(row, dict) else None
            try:
                payload = json.loads(raw) if isinstance(raw, str) and raw else (raw or {})
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            source = str(payload.get("source") or "unknown")[:64]
            by_source[source] = by_source.get(source, 0) + 1
            band = str(payload.get("lead_priority_band") or "").strip().lower()
            if band in _PRIORITY_BANDS:
                by_priority[band] = by_priority.get(band, 0) + 1
        return {
            "submissions": total,
            "by_source": by_source,
            "by_priority": by_priority,
            "available": True,
        }
    except Exception as exc:
        logger.warning(
            "site_marketing_events crm snapshot failed",
            extra={"event": "site_marketing_events.crm_snapshot_error", "exception_class": type(exc).__name__},
        )
        return {"submissions": 0, "by_source": {}, "by_priority": {}, "available": False}


def build_marketing_funnel_summary(*, lookback_days: int = 7) -> Dict[str, Any]:
    days = max(1, min(int(lookback_days or 7), 90))
    since = (_utc_now() - timedelta(days=days)).isoformat()
    enabled = site_marketing_events_enabled()
    try:
        ensure_site_marketing_event_tables()
        tables_ok = db_optimizer.table_exists("site_marketing_events")
    except Exception:
        tables_ok = False

    counts = {name: 0 for name in sorted(APPROVED_EVENTS)}
    step_views: Dict[str, int] = {}
    if tables_ok:
        for name in APPROVED_EVENTS:
            counts[name] = _count_events(name, since)
        step_views = _step_view_counts(since)

    starts = counts.get("intake_started", 0)
    submitted_events = counts.get("intake_submitted", 0)
    completion_rate = (submitted_events / starts) if starts else None
    crm = _crm_intake_snapshot(since)

    return {
        "lookback_days": days,
        "since": since,
        "events_enabled": enabled,
        "events_available": bool(tables_ok and enabled),
        "counts": counts,
        "intake": {
            "starts": starts,
            "submitted_events": submitted_events,
            "completion_rate": round(completion_rate, 4) if completion_rate is not None else None,
            "step_views": step_views,
            "crm_submissions": crm.get("submissions", 0),
            "crm_by_source": crm.get("by_source", {}),
            "crm_by_priority": crm.get("by_priority", {}),
            "crm_available": bool(crm.get("available")),
        },
        "chatbot": {
            "opened": counts.get("chatbot_opened", 0),
            "first_message": counts.get("chatbot_first_message", 0),
            "fallback": counts.get("chatbot_fallback", 0),
            "handoff": counts.get("chatbot_handoff", 0),
            "active_rate": (
                round(counts.get("chatbot_first_message", 0) / counts["chatbot_opened"], 4)
                if counts.get("chatbot_opened")
                else None
            ),
        },
        "notes": [
            "Vercel Web Analytics is off (usage-billed on Pro). Speed Insights free tier remains (pauses; no overage).",
            "Abandonment is inferred from intake_started vs intake_submitted over the lookback window.",
            "CRM submissions are authoritative for conversion identity; event counts are funnel telemetry.",
            "This collector is first-party and free (your database only).",
        ],
    }
