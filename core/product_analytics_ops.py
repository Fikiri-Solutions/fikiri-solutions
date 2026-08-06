"""Read-only product analytics operational checks.

Answers: “Is analytics working, and are these numbers believable?”

- Health snapshot (enabled, last event/aggregate, state)
- Bounded ops counters (storage failures, rejects)
- Manual reconciliation of recent leads/syncs vs emitted outcomes

No silent backfill. No admin mutations. No continuous monitoring engine.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.customer_success_analytics import build_analytics_state
from core.product_analytics_emit import build_outcome_dedupe_key
from core.product_analytics_registry import (
    product_analytics_enabled,
    tenant_in_analytics_allowlist,
)
from core.product_analytics_store import (
    latest_aggregate_timestamp,
    latest_event_timestamp,
    sum_ops_counters,
    tables_available,
)

logger = logging.getLogger(__name__)

ALLOWED_LOOKBACK_DAYS = frozenset({7, 30})
DEFAULT_LOOKBACK_DAYS = 7
MAX_RECONCILE_OBJECTS = 100


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _since_iso(lookback_days: int) -> str:
    return (_utc_now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")


def normalize_lookback_days(raw: Any) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LOOKBACK_DAYS
    if days in ALLOWED_LOOKBACK_DAYS:
        return days
    # Nearest allowed bound without inventing other windows
    return 30 if days > 7 else 7


def build_analytics_ops_health(
    tenant_id: int,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """Small operational health snapshot for one tenant."""
    days = normalize_lookback_days(lookback_days)
    enabled = product_analytics_enabled()
    in_allowlist = tenant_in_analytics_allowlist(int(tenant_id))
    state = build_analytics_state(tenant_id)
    # Prefer explicit ops status vocabulary
    status = state.get("status")
    if status == "partial":
        status = "available"
    counters = sum_ops_counters(int(tenant_id), since_date=_since_iso(days))
    return {
        "tenant_id": int(tenant_id),
        "analytics_enabled": enabled,
        "tenant_in_allowlist": in_allowlist,
        "analytics_available": bool(tables_available()) if enabled else False,
        "analytics_state": status,
        "coverage": state.get("coverage"),
        "last_event_at": state.get("last_event_at") or latest_event_timestamp(tenant_id),
        "last_aggregated_at": state.get("last_aggregated_at")
        or latest_aggregate_timestamp(tenant_id),
        "lookback_days": days,
        "storage_failure_count": int(counters.get("storage_failures") or 0),
        "rejected_event_count": int(counters.get("rejected_events") or 0),
        "unexpected_error_count": int(counters.get("unexpected_errors") or 0),
        "notes": (
            "Counters cover this process's recorded ops since lookback start when "
            "ops daily table is available. Reconciliation is separate and report-only."
        ),
    }


def _fetch_recent_leads(tenant_id: int, *, since: str, limit: int) -> List[Dict[str, Any]]:
    from core.database_optimization import db_optimizer

    if not db_optimizer.table_exists("leads"):
        return []
    # Prefix date compare works for ISO / Postgres timestamps (YYYY-MM-DD…).
    rows = db_optimizer.execute_query(
        """
        SELECT id, created_at
        FROM leads
        WHERE user_id = ? AND created_at >= ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(tenant_id), since, int(limit)),
    )
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        r = dict(row) if hasattr(row, "keys") else {"id": row[0], "created_at": row[1]}
        out.append({"id": r.get("id"), "created_at": r.get("created_at")})
    return out


def _fetch_recent_completed_syncs(
    tenant_id: int, *, since: str, limit: int
) -> List[Dict[str, Any]]:
    from core.database_optimization import db_optimizer

    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return []
    rows = db_optimizer.execute_query(
        """
        SELECT job_id, completed_at, status
        FROM gmail_sync_jobs
        WHERE user_id = ?
          AND LOWER(COALESCE(status, '')) = 'completed'
          AND COALESCE(completed_at, created_at) >= ?
        ORDER BY completed_at DESC
        LIMIT ?
        """,
        (int(tenant_id), since, int(limit)),
    )
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        r = dict(row) if hasattr(row, "keys") else {
            "job_id": row[0],
            "completed_at": row[1],
            "status": row[2],
        }
        out.append(
            {
                "job_id": r.get("job_id"),
                "completed_at": r.get("completed_at"),
                "status": r.get("status"),
            }
        )
    return out


def _outcome_exists(
    tenant_id: int,
    *,
    event_name: str,
    object_type: str,
    object_id: str,
) -> bool:
    from core.database_optimization import db_optimizer

    if not tables_available():
        return False
    dedupe = build_outcome_dedupe_key(
        event_name=event_name, object_type=object_type, object_id=str(object_id)
    )
    rows = db_optimizer.execute_query(
        """
        SELECT id FROM product_events
        WHERE tenant_id = ?
          AND event_name = ?
          AND event_source IN ('server', 'derived')
          AND outcome_dedupe_key = ?
        LIMIT 1
        """,
        (int(tenant_id), event_name, dedupe),
    )
    return bool(rows)


def reconcile_recent_outcomes(
    tenant_id: int,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """Compare recent authoritative leads/syncs to emitted outcomes.

    Read-only. Report-only. Does not backfill or mutate.
    """
    days = normalize_lookback_days(lookback_days)
    since = _since_iso(days)
    leads = _fetch_recent_leads(
        int(tenant_id), since=since, limit=MAX_RECONCILE_OBJECTS
    )
    syncs = _fetch_recent_completed_syncs(
        int(tenant_id), since=since, limit=MAX_RECONCILE_OBJECTS
    )

    lead_matched: List[str] = []
    lead_missing: List[str] = []
    for lead in leads:
        lid = str(lead.get("id"))
        if _outcome_exists(
            int(tenant_id),
            event_name="outcome.lead_captured",
            object_type="lead",
            object_id=lid,
        ):
            lead_matched.append(lid)
        else:
            lead_missing.append(lid)

    sync_matched: List[str] = []
    sync_missing: List[str] = []
    for job in syncs:
        jid = str(job.get("job_id") or "")
        if not jid:
            continue
        if _outcome_exists(
            int(tenant_id),
            event_name="outcome.sync_completed",
            object_type="gmail_sync_job",
            object_id=jid,
        ):
            sync_matched.append(jid)
        else:
            sync_missing.append(jid)

    truncated = (
        len(leads) >= MAX_RECONCILE_OBJECTS or len(syncs) >= MAX_RECONCILE_OBJECTS
    )
    return {
        "tenant_id": int(tenant_id),
        "lookback_days": days,
        "since_date": since,
        "analytics_enabled": product_analytics_enabled(),
        "tables_available": tables_available(),
        "max_objects_per_type": MAX_RECONCILE_OBJECTS,
        "truncated": truncated,
        "leads": {
            "authoritative_count": len(leads),
            "matched_count": len(lead_matched),
            "missing_count": len(lead_missing),
            "missing_ids": lead_missing[:50],
        },
        "gmail_syncs": {
            "authoritative_completed_count": len(syncs),
            "matched_count": len(sync_matched),
            "missing_count": len(sync_missing),
            "missing_job_ids": sync_missing[:50],
        },
        "backfill": False,
        "notes": (
            "Report-only. Missing events may be expected for history before tracking "
            "or post-commit loss. Do not silent-backfill from this report."
        ),
    }


def build_analytics_ops_report(
    tenant_id: int,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    include_reconciliation: bool = True,
) -> Dict[str, Any]:
    """Combined manual ops report for one tenant."""
    days = normalize_lookback_days(lookback_days)
    health = build_analytics_ops_health(tenant_id, lookback_days=days)
    report: Dict[str, Any] = {
        "health": health,
        "generated_at": _utc_now().isoformat(),
        "read_only": True,
        "mutations": False,
    }
    if include_reconciliation:
        report["reconciliation"] = reconcile_recent_outcomes(
            tenant_id, lookback_days=days
        )
    return report
