"""Server-side product analytics emission (no HTTP).

Call only after authoritative business state is committed.

Failure contract (narrow — not “swallow everything”):
- Storage unavailable / timeout / duplicate → controlled result codes
- Registry misuse / prohibited props / invalid construction → reject +
  sanitized programmer-error telemetry (no property values)
- Unexpected exceptions → log exception class + correlation_id only;
  never log event properties; never raise into the business workflow
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.product_analytics_registry import (
    SCHEMA_VERSION,
    product_analytics_enabled,
    tenant_in_analytics_allowlist,
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

_OBJECT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_OBJECT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

# Controlled rejection reasons that indicate call-site / registry misuse.
PROGRAMMER_REJECT_REASONS = frozenset(
    {
        "UNKNOWN_EVENT",
        "INVALID_SOURCE",
        "SOURCE_NOT_ALLOWED",
        "TOO_MANY_PROPERTIES",
        "INVALID_PROPERTY_KEY",
        "PROHIBITED_PROPERTY",
        "IDENTITY_PROPERTY_FORBIDDEN",
        "UNKNOWN_PROPERTY",
        "INVALID_PROPERTY_VALUE",
        "INVALID_FEATURE_KEY",
        "INVALID_WORKFLOW_KEY",
        "INVALID_SOURCE_CATEGORY",
        "INVALID_CREATION_CHANNEL",
        "INVALID_PROVIDER",
        "INVALID_SYNC_TYPE",
        "INVALID_RESULT_CATEGORY",
        "INVALID_PROCESSED_COUNT_BUCKET",
        "INVALID_SCHEMA_VERSION",
        "INVALID_OBJECT_TYPE",
        "INVALID_OBJECT_ID",
        "REJECTED",
    }
)

STORAGE_RESULT_REASONS = frozenset(
    {
        "STORAGE_UNAVAILABLE",
        "STORAGE_TIMEOUT",
        "STORAGE_FAILURE",
        "DISABLED",
    }
)


def build_outcome_dedupe_key(
    *,
    event_name: str,
    object_type: str,
    object_id: str,
) -> str:
    """tenant-scoped uniqueness uses (tenant_id, outcome_dedupe_key)."""
    short_name = (
        event_name.replace("outcome.", "", 1)
        if event_name.startswith("outcome.")
        else event_name
    )
    return f"{short_name}:{object_type}:{object_id}"[:200]


def _is_impersonating_safe() -> bool:
    try:
        from core.secure_sessions import is_impersonating

        return bool(is_impersonating())
    except Exception:
        return False


def _increments_for_server_event(event_name: str) -> Dict[str, int]:
    inc: Dict[str, int] = {"active_users": 1, "meaningful_actions": 1}
    if event_name == "outcome.sync_completed":
        # Count successful sync as a completed workflow signal without inventing starts.
        inc["workflow_completed"] = 1
    return inc


def _bump_ops(
    tenant_id: int,
    *,
    storage_failures: int = 0,
    rejected_events: int = 0,
    unexpected_errors: int = 0,
) -> None:
    try:
        increment_ops_counter(
            int(tenant_id),
            storage_failures=storage_failures,
            rejected_events=rejected_events,
            unexpected_errors=unexpected_errors,
        )
    except Exception:
        pass


def _base_result(*, analytics_enabled: bool) -> Dict[str, Any]:
    return {
        "emitted": False,
        "duplicate": False,
        "analytics_enabled": analytics_enabled,
        "analytics_available": True,
        "reason": None,
    }


def _log_programmer_reject(
    *,
    reason: str,
    event_name: str,
    correlation_id: Optional[str],
    tenant_id: Optional[int] = None,
) -> None:
    """Sanitized programmer-error telemetry — never logs property values."""
    logger.warning(
        "server product analytics programmer reject",
        extra={
            "event": "product_analytics.programmer_reject",
            "severity": "WARN",
            "reason": reason,
            "event_name": event_name,
            "correlation_id": correlation_id,
            "tenant_id": tenant_id,
        },
    )


def _log_storage_issue(
    *,
    reason: str,
    event_name: str,
    correlation_id: Optional[str],
    exception_class: Optional[str] = None,
) -> None:
    logger.warning(
        "server product analytics storage issue",
        extra={
            "event": "product_analytics.server_storage_issue",
            "severity": "WARN",
            "reason": reason,
            "event_name": event_name,
            "correlation_id": correlation_id,
            "exception_class": exception_class,
        },
    )


def _log_unexpected(
    *,
    exception_class: str,
    event_name: str,
    correlation_id: Optional[str],
    phase: str,
) -> None:
    """Unexpected analytics error — class + correlation only; no payloads."""
    logger.error(
        "server product analytics unexpected error",
        extra={
            "event": "product_analytics.server_unexpected",
            "severity": "ERROR",
            "exception_class": exception_class,
            "event_name": event_name,
            "correlation_id": correlation_id,
            "phase": phase,
        },
    )


def _classify_insert_exception(exc: BaseException) -> str:
    """Map DB/driver exceptions to controlled reasons. Unknown → UNEXPECTED_ERROR."""
    name = type(exc).__name__
    name_l = name.lower()
    msg = str(exc).lower()

    if "unique" in msg or "duplicate" in msg:
        return "DUPLICATE"
    if "timeout" in name_l or "timeout" in msg:
        return "STORAGE_TIMEOUT"
    if any(
        token in name_l
        for token in (
            "operational",
            "interface",
            "connection",
            "disconnect",
            "database",
        )
    ):
        return "STORAGE_UNAVAILABLE"
    if "locked" in msg or "busy" in msg or "could not connect" in msg:
        return "STORAGE_UNAVAILABLE"
    # Schema mismatch, programming errors, etc. must remain visible.
    return "UNEXPECTED_ERROR"


def emit_server_product_event(
    *,
    tenant_id: int,
    actor_user_id: int,
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
    object_type: str,
    object_id: str,
    correlation_id: Optional[str] = None,
    ensure_tables: bool = False,
) -> Dict[str, Any]:
    """Emit one server-authoritative product analytics event.

    Never raises into the caller. Returns a controlled result dict.
    Does not log property values on reject or failure.
    """
    enabled = product_analytics_enabled()
    result = _base_result(analytics_enabled=enabled)
    cid = str(correlation_id) if correlation_id else None

    try:
        return _emit_server_product_event_inner(
            result=result,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_name=event_name,
            properties=properties,
            object_type=object_type,
            object_id=object_id,
            correlation_id=cid,
            ensure_tables=ensure_tables,
        )
    except Exception as exc:
        # Last-resort boundary: business workflows must not see this raise.
        _log_unexpected(
            exception_class=type(exc).__name__,
            event_name=event_name or "unknown",
            correlation_id=cid,
            phase="emit_boundary",
        )
        try:
            _bump_ops(int(tenant_id), unexpected_errors=1)
        except Exception:
            pass
        result["analytics_available"] = False
        result["reason"] = "UNEXPECTED_ERROR"
        return result


def _emit_server_product_event_inner(
    *,
    result: Dict[str, Any],
    tenant_id: int,
    actor_user_id: int,
    event_name: str,
    properties: Optional[Dict[str, Any]],
    object_type: str,
    object_id: str,
    correlation_id: Optional[str],
    ensure_tables: bool,
) -> Dict[str, Any]:
    if not result["analytics_enabled"]:
        result["reason"] = "DISABLED"
        result["analytics_available"] = False
        return result

    if not tenant_in_analytics_allowlist(int(tenant_id)):
        result["reason"] = "TENANT_NOT_IN_ALLOWLIST"
        return result

    if _is_impersonating_safe():
        result["reason"] = "IMPERSONATION_EXCLUDED"
        return result

    if not _OBJECT_TYPE_RE.match(str(object_type or "")):
        result["reason"] = "INVALID_OBJECT_TYPE"
        _log_programmer_reject(
            reason="INVALID_OBJECT_TYPE",
            event_name=event_name,
            correlation_id=correlation_id,
            tenant_id=int(tenant_id),
        )
        _bump_ops(int(tenant_id), rejected_events=1)
        return result
    oid = str(object_id or "").strip()
    if not _OBJECT_ID_RE.match(oid):
        result["reason"] = "INVALID_OBJECT_ID"
        _log_programmer_reject(
            reason="INVALID_OBJECT_ID",
            event_name=event_name,
            correlation_id=correlation_id,
            tenant_id=int(tenant_id),
        )
        _bump_ops(int(tenant_id), rejected_events=1)
        return result

    props = dict(properties or {})
    props.setdefault("completed", True)
    props.setdefault("schema_version", SCHEMA_VERSION)

    ok, reason, sanitized = validate_event_properties(
        event_name, props, event_source="server"
    )
    if not ok:
        code = reason or "REJECTED"
        result["reason"] = code
        if code in PROGRAMMER_REJECT_REASONS or code.startswith("INVALID_"):
            _log_programmer_reject(
                reason=code,
                event_name=event_name,
                correlation_id=correlation_id,
                tenant_id=int(tenant_id),
            )
        else:
            logger.info(
                "server product analytics rejected",
                extra={
                    "event": "product_analytics.server_rejected",
                    "reason": code,
                    "event_name": event_name,
                    "correlation_id": correlation_id,
                },
            )
        _bump_ops(int(tenant_id), rejected_events=1)
        return result

    if ensure_tables:
        try:
            ensure_product_analytics_tables()
        except Exception as exc:
            # DDL helper is test/local only; treat as storage availability.
            _log_storage_issue(
                reason="STORAGE_UNAVAILABLE",
                event_name=event_name,
                correlation_id=correlation_id,
                exception_class=type(exc).__name__,
            )
            result["analytics_available"] = False
            result["reason"] = "STORAGE_UNAVAILABLE"
            _bump_ops(int(tenant_id), storage_failures=1)
            return result

    if not tables_available():
        result["analytics_available"] = False
        result["reason"] = "STORAGE_UNAVAILABLE"
        _log_storage_issue(
            reason="STORAGE_UNAVAILABLE",
            event_name=event_name,
            correlation_id=correlation_id,
        )
        _bump_ops(int(tenant_id), storage_failures=1)
        return result

    dedupe = build_outcome_dedupe_key(
        event_name=event_name, object_type=object_type, object_id=oid
    )
    occurred_at = datetime.now(timezone.utc)

    try:
        row_id = insert_product_event(
            tenant_id=int(tenant_id),
            actor_user_id=int(actor_user_id),
            event_name=event_name,
            event_source="server",
            properties=sanitized,
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            outcome_dedupe_key=dedupe,
        )
    except Exception as exc:
        classified = _classify_insert_exception(exc)
        if classified == "DUPLICATE":
            result["duplicate"] = True
            result["reason"] = "DUPLICATE"
            return result
        if classified in STORAGE_RESULT_REASONS or classified in {
            "STORAGE_UNAVAILABLE",
            "STORAGE_TIMEOUT",
            "STORAGE_FAILURE",
        }:
            result["analytics_available"] = False
            result["reason"] = classified
            _log_storage_issue(
                reason=classified,
                event_name=event_name,
                correlation_id=correlation_id,
                exception_class=type(exc).__name__,
            )
            _bump_ops(int(tenant_id), storage_failures=1)
            return result
        result["analytics_available"] = False
        result["reason"] = "UNEXPECTED_ERROR"
        _log_unexpected(
            exception_class=type(exc).__name__,
            event_name=event_name,
            correlation_id=correlation_id,
            phase="insert",
        )
        _bump_ops(int(tenant_id), unexpected_errors=1)
        return result

    if row_id is None:
        # Pre-checked uniqueness or concurrent unique hit — not an error.
        result["duplicate"] = True
        result["reason"] = "DUPLICATE"
        return result

    try:
        metric_date = occurred_at.strftime("%Y-%m-%d")
        upsert_daily_metric_counters(
            tenant_id=int(tenant_id),
            metric_date=metric_date,
            increments=_increments_for_server_event(event_name),
            feature_key=sanitized.get("feature_key"),
            last_event_at=occurred_at,
        )
    except Exception as exc:
        # Event row already durable; aggregate bump is best-effort but visible.
        classified = _classify_insert_exception(exc)
        if classified in {"STORAGE_UNAVAILABLE", "STORAGE_TIMEOUT", "DUPLICATE"}:
            _log_storage_issue(
                reason=classified if classified != "DUPLICATE" else "STORAGE_FAILURE",
                event_name=event_name,
                correlation_id=correlation_id,
                exception_class=type(exc).__name__,
            )
        else:
            _log_unexpected(
                exception_class=type(exc).__name__,
                event_name=event_name,
                correlation_id=correlation_id,
                phase="aggregate_bump",
            )

    result["emitted"] = True
    result["reason"] = "OK"
    return result


def map_lead_source_category(raw_source: Optional[str]) -> str:
    s = (raw_source or "manual").strip().lower()
    if s in {"manual", "crm", "ui"}:
        return "manual"
    if s in {"website", "web", "landing"}:
        return "website"
    if s in {"import", "csv", "migration"}:
        return "import"
    if s in {"email", "gmail", "outlook"}:
        return "email"
    if s in {"automation", "workflow"}:
        return "automation"
    if s in {"api", "webhook"}:
        return "api"
    return "other"


def map_lead_creation_channel(raw_source: Optional[str]) -> str:
    s = (raw_source or "manual").strip().lower()
    if s in {"import", "csv", "migration"}:
        return "import"
    if s in {"automation", "workflow"}:
        return "automation"
    if s in {"webhook"}:
        return "webhook"
    if s in {"api"}:
        return "api"
    return "crm_ui"


def processed_count_bucket(count: int) -> str:
    n = max(0, int(count or 0))
    if n == 0:
        return "0"
    if n <= 10:
        return "1_to_10"
    if n <= 50:
        return "11_to_50"
    if n <= 200:
        return "51_to_200"
    if n <= 1000:
        return "201_to_1000"
    return "over_1000"


def map_gmail_sync_type(completed_meta: Optional[Dict[str, Any]]) -> str:
    """Map job metadata to a controlled sync_type for outcome.sync_completed."""
    meta = completed_meta or {}
    if meta.get("is_retry") or meta.get("retry_of") or meta.get("admin_retry_of"):
        return "retry"
    raw = str(meta.get("sync_type") or "").strip().lower()
    if raw in {"incremental", "initial", "lookback", "retry"}:
        return raw
    if raw in {"full"} or meta.get("lookback_preset"):
        return "lookback"
    # Gmail jobs stamp lookback_days for the date window; default lookback.
    return "lookback"
