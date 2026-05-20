"""
Rebuild daily rollups and tenant metrics from service_usage_events + billing mirror.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from analytics.service_usage_analytics import mirror_billing_usage_to_analytics
from analytics.service_usage_constants import (
    EVENT_CATEGORY_USAGE,
    WINDOW_ALL_TIME,
    WINDOW_CURRENT_MONTH,
    WINDOW_LAST_30D,
    WINDOW_LAST_7D,
)
from analytics.service_usage_store import replace_daily_rollup, upsert_tenant_metric
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def rebuild_daily_rollups_for_user(user_id: int, *, days: int = 30) -> int:
    """
    Aggregate service_usage_events into service_daily_rollups for the last N days.
    Deterministic: replaces rollup totals per (user, service, day, metric, category).
    """
    if not db_optimizer.table_exists("service_usage_events"):
        return 0
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db_optimizer.execute_query(
        """
        SELECT service_id, DATE(created_at) AS day, metric_name, event_category,
               SUM(quantity) AS total_quantity,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
               SUM(CASE WHEN status IN ('failure', 'error') THEN 1 ELSE 0 END) AS failure_count,
               COUNT(*) AS event_count,
               MAX(created_at) AS last_event_at
        FROM service_usage_events
        WHERE user_id = ? AND DATE(created_at) >= DATE(?)
        GROUP BY service_id, DATE(created_at), metric_name, event_category
        """,
        (user_id, since),
    )
    updated = 0
    for row in rows or []:
        replace_daily_rollup(
            user_id=user_id,
            service_id=row.get("service_id") or "",
            day=str(row.get("day") or "")[:10],
            metric_name=row.get("metric_name") or "unknown",
            event_category=row.get("event_category") or EVENT_CATEGORY_USAGE,
            total_quantity=float(row.get("total_quantity") or 0),
            success_count=int(row.get("success_count") or 0),
            failure_count=int(row.get("failure_count") or 0),
            event_count=int(row.get("event_count") or 0),
            last_event_at=str(row.get("last_event_at") or ""),
        )
        updated += 1
    return updated


def rebuild_tenant_metrics_for_user(user_id: int) -> int:
    """Compute windowed totals from service_daily_rollups into tenant_service_metrics."""
    if not db_optimizer.table_exists("service_daily_rollups"):
        return 0
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")
    windows = {
        WINDOW_LAST_7D: (now - timedelta(days=7)).strftime("%Y-%m-%d"),
        WINDOW_LAST_30D: (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        WINDOW_CURRENT_MONTH: f"{month_prefix}-01",
        WINDOW_ALL_TIME: "1970-01-01",
    }
    updated = 0
    for window_type, start_day in windows.items():
        rows = db_optimizer.execute_query(
            """
            SELECT service_id, metric_name, event_category,
                   SUM(total_quantity) AS total,
                   MAX(last_event_at) AS last_activity
            FROM service_daily_rollups
            WHERE user_id = ? AND day >= ?
            GROUP BY service_id, metric_name, event_category
            """,
            (user_id, start_day),
        )
        for row in rows or []:
            upsert_tenant_metric(
                user_id=user_id,
                service_id=row.get("service_id") or "",
                metric_name=row.get("metric_name") or "unknown",
                window_type=window_type,
                metric_value=float(row.get("total") or 0),
                last_activity_at=str(row.get("last_activity") or ""),
                metadata={"event_category": row.get("event_category")},
                increment=False,
            )
            updated += 1
    return updated


def _refresh_tenant_analytics_impl(user_id: int, *, mirror_billing: bool = True) -> Dict[str, int]:
    counts = {"billing_mirrored": 0, "daily_rollups": 0, "tenant_metrics": 0}
    if mirror_billing:
        counts["billing_mirrored"] = mirror_billing_usage_to_analytics(user_id)
    counts["daily_rollups"] = rebuild_daily_rollups_for_user(user_id)
    counts["tenant_metrics"] = rebuild_tenant_metrics_for_user(user_id)
    return counts


def refresh_tenant_analytics(user_id: int, *, mirror_billing: bool = True) -> Dict[str, int]:
    """
    Full refresh: optional billing mirror events, rebuild rollups, rebuild tenant metrics.
    Records a durable job row when persistence is enabled (inline execution).
    """
    try:
        from core.durable_jobs import (
            JOB_KIND_ANALYTICS_ROLLUP,
            build_idempotency_key,
            enqueue_durable_job,
            mark_job_completed,
            mark_job_failed,
            mark_job_running,
        )

        idem = build_idempotency_key("analytics_rollup", user_id, mirror_billing)
        jid = enqueue_durable_job(
            JOB_KIND_ANALYTICS_ROLLUP,
            user_id=user_id,
            payload={"mirror_billing": mirror_billing},
            idempotency_key=idem,
        )
        if jid:
            mark_job_running(jid)
        try:
            counts = _refresh_tenant_analytics_impl(user_id, mirror_billing=mirror_billing)
            if jid:
                mark_job_completed(jid, counts)
            return counts
        except Exception as exc:
            if jid:
                mark_job_failed(jid, str(exc), allow_retry=True)
            raise
    except Exception:
        return _refresh_tenant_analytics_impl(user_id, mirror_billing=mirror_billing)


def aggregate_platform_service_activity(*, days: int = 30) -> List[Dict[str, Any]]:
    """Cross-tenant active services (admin-style); scoped by caller auth in API layer."""
    if not db_optimizer.table_exists("service_usage_events"):
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db_optimizer.execute_query(
        """
        SELECT service_id,
               COUNT(DISTINCT user_id) AS active_tenants,
               COUNT(*) AS event_count,
               SUM(quantity) AS total_quantity
        FROM service_usage_events
        WHERE DATE(created_at) >= DATE(?)
        GROUP BY service_id
        ORDER BY active_tenants DESC
        """,
        (since,),
    )
    return [dict(r) for r in (rows or [])]
