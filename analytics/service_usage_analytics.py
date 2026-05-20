"""
Unified service usage analytics — record operational events and query summaries.

Billing metering remains in ``billing_usage``; this layer adds service_id attribution,
health signals, and rollups without duplicating billing writes.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from analytics.service_usage_constants import (
    EVENT_AI_CALL,
    EVENT_AUTOMATION_RUN,
    EVENT_CATEGORY_BILLING_MIRROR,
    EVENT_CATEGORY_USAGE,
    METRIC_AI_RESPONSES,
    METRIC_AUTOMATION_EXECUTIONS,
    METRIC_BILLING_QUANTITY,
    METRIC_CHATBOT_QUERIES,
    WINDOW_CURRENT_MONTH,
    normalize_service_id,
    service_id_for_billing_usage,
)
from analytics.service_usage_store import (
    _utc_day,
    insert_usage_event,
    list_usage_events,
    sum_daily_rollups,
    upsert_daily_rollup,
    upsert_tenant_metric,
)
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def _skip_persist_in_test() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST")) and os.getenv(
        "FIKIRI_SERVICE_USAGE_PERSIST_IN_TEST", ""
    ).lower() not in ("1", "true", "yes")


def build_idempotency_key(*parts: Any) -> str:
    raw = ":".join(str(p) for p in parts if p is not None and str(p) != "")
    if len(raw) <= 200:
        return raw
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_service_usage_event(
    *,
    user_id: int,
    service_id: str,
    event_type: str,
    event_category: str = EVENT_CATEGORY_USAGE,
    metric_name: Optional[str] = None,
    quantity: float = 1.0,
    status: str = "success",
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
    update_rollups: bool = True,
) -> Optional[int]:
    """
    Record one operational usage event with optional idempotency.

    Does not write to ``billing_usage``. Use alongside billing recorders when
    service-level attribution is needed.
    """
    if not user_id or _skip_persist_in_test():
        return None
    row_id = insert_usage_event(
        user_id=user_id,
        service_id=service_id,
        event_category=event_category,
        event_type=event_type,
        metric_name=metric_name or event_type,
        quantity=quantity,
        status=status,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        source=source,
    )
    if row_id and update_rollups:
        _increment_rollups_from_event(
            user_id=user_id,
            service_id=service_id,
            event_category=event_category,
            metric_name=metric_name or event_type,
            quantity=quantity,
            status=status,
        )
    return row_id


def _increment_rollups_from_event(
    *,
    user_id: int,
    service_id: str,
    event_category: str,
    metric_name: str,
    quantity: float,
    status: str,
) -> None:
    day = _utc_day()
    success_delta = 1 if status == "success" else 0
    failure_delta = 1 if status in ("failure", "error") else 0
    upsert_daily_rollup(
        user_id=user_id,
        service_id=service_id,
        day=day,
        metric_name=metric_name,
        event_category=event_category,
        quantity_delta=quantity,
        success_delta=success_delta,
        failure_delta=failure_delta,
    )
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    upsert_tenant_metric(
        user_id=user_id,
        service_id=service_id,
        metric_name=metric_name,
        window_type=WINDOW_CURRENT_MONTH,
        metric_value=quantity,
        metadata={"month": month_key, "last_status": status},
    )


def record_ai_service_usage(
    user_id: int,
    service_id: str,
    *,
    quantity: int = 1,
    correlation_id: Optional[str] = None,
    source: Optional[str] = None,
    operation: Optional[str] = None,
) -> Optional[int]:
    """Attribute AI usage to a product service without touching billing_usage."""
    key = None
    if correlation_id:
        key = build_idempotency_key("ai", user_id, service_id, correlation_id, operation or "")
    return record_service_usage_event(
        user_id=user_id,
        service_id=service_id,
        event_type=EVENT_AI_CALL,
        metric_name=METRIC_AI_RESPONSES,
        quantity=float(quantity),
        idempotency_key=key,
        correlation_id=correlation_id,
        metadata={"operation": operation} if operation else None,
        source=source or "ai",
    )


def record_automation_service_usage(
    user_id: int,
    *,
    rule_id: int,
    status: str,
    correlation_id: Optional[str] = None,
) -> Optional[int]:
    sid = "automations"
    key = build_idempotency_key(
        "automation", user_id, rule_id, correlation_id or datetime.now(timezone.utc).isoformat()
    )
    return record_service_usage_event(
        user_id=user_id,
        service_id=sid,
        event_type=EVENT_AUTOMATION_RUN,
        metric_name=METRIC_AUTOMATION_EXECUTIONS,
        status=status,
        idempotency_key=key,
        resource_type="automation_rule",
        resource_id=str(rule_id),
        source="automation_engine",
    )


def record_chatbot_service_usage(
    user_id: int,
    *,
    metric_name: str,
    quantity: float = 1.0,
    correlation_id: Optional[str] = None,
    llm_success: Optional[bool] = None,
) -> Optional[int]:
    key = None
    if correlation_id:
        key = build_idempotency_key("chatbot", user_id, metric_name, correlation_id)
    return record_service_usage_event(
        user_id=user_id,
        service_id="chatbot",
        event_type=EVENT_AI_CALL if metric_name == METRIC_AI_RESPONSES else "chatbot_query",
        metric_name=metric_name,
        quantity=quantity,
        idempotency_key=key,
        correlation_id=correlation_id,
        metadata={"llm_success": llm_success} if llm_success is not None else None,
        source="chatbot",
    )


def record_email_pipeline_service_usage(
    user_id: int,
    *,
    operation: str,
    correlation_id: Optional[str] = None,
    quantity: int = 1,
) -> Optional[int]:
    key = build_idempotency_key("email_pipeline", user_id, operation, correlation_id or "")
    return record_service_usage_event(
        user_id=user_id,
        service_id="ai-assistant",
        event_type=EVENT_AI_CALL,
        metric_name=METRIC_AI_RESPONSES,
        quantity=float(quantity),
        idempotency_key=key if correlation_id else None,
        correlation_id=correlation_id,
        metadata={"operation": operation},
        source="email_pipeline_ai_gate",
    )


def mirror_billing_usage_to_analytics(user_id: int, month: Optional[str] = None) -> int:
    """
    Read ``billing_usage`` and upsert billing_mirror rollups (no INSERT into billing_usage).

    Uses idempotency keys derived from billing row ids so re-runs do not double-count.
    """
    if not user_id or not db_optimizer.table_exists("billing_usage"):
        return 0
    month_key = month or datetime.now(timezone.utc).strftime("%Y-%m")
    rows = db_optimizer.execute_query(
        """
        SELECT usage_type, SUM(quantity) AS total
        FROM billing_usage
        WHERE user_id = ? AND month = ?
        GROUP BY usage_type
        """,
        (user_id, month_key),
    )
    mirrored = 0
    for row in rows or []:
        usage_type = row.get("usage_type") or ""
        total = float(row.get("total") or 0)
        if total <= 0:
            continue
        service_id = service_id_for_billing_usage(usage_type)
        key = build_idempotency_key("billing_mirror", user_id, month_key, usage_type)
        if insert_usage_event(
            user_id=user_id,
            service_id=service_id,
            event_category=EVENT_CATEGORY_BILLING_MIRROR,
            event_type="billing_aggregate",
            metric_name=METRIC_BILLING_QUANTITY,
            quantity=total,
            status="success",
            idempotency_key=key,
            metadata={"usage_type": usage_type, "month": month_key},
            source="billing_usage_mirror",
        ):
            upsert_daily_rollup(
                user_id=user_id,
                service_id=service_id,
                day=datetime.now(timezone.utc).strftime("%Y-%m-01"),
                metric_name=f"billing_{usage_type}",
                event_category=EVENT_CATEGORY_BILLING_MIRROR,
                quantity_delta=total,
                event_delta=0,
            )
            mirrored += 1
    return mirrored


def get_tenant_service_summary(user_id: int) -> Dict[str, Any]:
    """Operational summary for one tenant (user_id)."""
    services_enabled = db_optimizer.execute_query(
        """
        SELECT service_id, enabled, status, updated_at
        FROM user_services
        WHERE user_id = ?
        """,
        (user_id,),
    )
    metrics_rows = []
    if db_optimizer.table_exists("tenant_service_metrics"):
        metrics_rows = db_optimizer.execute_query(
            """
            SELECT service_id, metric_name, window_type, metric_value, last_activity_at
            FROM tenant_service_metrics
            WHERE user_id = ? AND window_type = ?
            """,
            (user_id, WINDOW_CURRENT_MONTH),
        )
    billing_rows = []
    if db_optimizer.table_exists("billing_usage"):
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        billing_rows = db_optimizer.execute_query(
            """
            SELECT usage_type, SUM(quantity) AS total
            FROM billing_usage
            WHERE user_id = ? AND month = ?
            GROUP BY usage_type
            """,
            (user_id, month_key),
        )
    by_service: Dict[str, Dict[str, Any]] = {}
    for row in metrics_rows or []:
        sid = normalize_service_id(row.get("service_id") or "")
        by_service.setdefault(sid, {"service_id": sid, "metrics": {}})
        by_service[sid]["metrics"][row.get("metric_name")] = {
            "value": float(row.get("metric_value") or 0),
            "last_activity_at": row.get("last_activity_at"),
        }
    billing_map = {
        (r.get("usage_type") or ""): int(r.get("total") or 0) for r in (billing_rows or [])
    }
    return {
        "user_id": user_id,
        "services_configured": [dict(r) for r in (services_enabled or [])],
        "service_metrics": list(by_service.values()),
        "billing_usage_month": billing_map,
        "recent_events": list_usage_events(user_id, limit=20),
        "daily_rollups": sum_daily_rollups(user_id, days=30),
    }


def list_active_tenants_by_service(
    service_id: str,
    *,
    days: int = 30,
    min_events: int = 1,
) -> List[Dict[str, Any]]:
    """Tenants with activity on a service in the last N days."""
    if not db_optimizer.table_exists("service_usage_events"):
        return []
    sid = normalize_service_id(service_id)
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))).isoformat()
    rows = db_optimizer.execute_query(
        """
        SELECT user_id, COUNT(*) AS event_count, MAX(created_at) AS last_activity
        FROM service_usage_events
        WHERE service_id = ?
          AND datetime(created_at) >= datetime(?)
        GROUP BY user_id
        HAVING COUNT(*) >= ?
        ORDER BY last_activity DESC
        """,
        (sid, cutoff, min_events),
    )
    return [dict(r) for r in (rows or [])]
