"""
Persistence layer for service usage analytics tables.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from analytics.service_usage_constants import normalize_service_id
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def _tables_ready() -> bool:
    return db_optimizer.table_exists("service_usage_events")


def _utc_day(dt: Optional[datetime] = None) -> str:
    when = dt or datetime.now(timezone.utc)
    return when.strftime("%Y-%m-%d")


def _sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    if not metadata:
        return None
    safe: Dict[str, Any] = {}
    for key, value in metadata.items():
        if key in ("body", "email_body", "prompt", "response", "content", "message"):
            continue
        if isinstance(value, str) and len(value) > 500:
            safe[key] = value[:500] + "…"
        else:
            safe[key] = value
    try:
        return json.dumps(safe, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        return None


def insert_usage_event(
    *,
    user_id: int,
    service_id: str,
    event_category: str,
    event_type: str,
    metric_name: Optional[str] = None,
    quantity: float = 1.0,
    status: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> Optional[int]:
    """Insert one event. Returns row id, or None if skipped (duplicate idempotency) or failed."""
    if not user_id or not _tables_ready():
        return None
    sid = normalize_service_id(service_id)
    if not sid or not event_category or not event_type:
        return None

    params: Tuple[Any, ...] = (
        user_id,
        sid,
        event_category,
        event_type,
        metric_name,
        float(quantity or 0),
        status,
        idempotency_key,
        correlation_id,
        resource_type,
        resource_id,
        _sanitize_metadata(metadata),
        source,
    )

    if idempotency_key:
        existing = db_optimizer.execute_query(
            "SELECT id FROM service_usage_events WHERE idempotency_key = ? LIMIT 1",
            (idempotency_key,),
        )
        if existing:
            return None
        if db_optimizer.db_type == "postgresql":
            sql = """
                INSERT INTO service_usage_events (
                    user_id, service_id, event_category, event_type, metric_name,
                    quantity, status, idempotency_key, correlation_id,
                    resource_type, resource_id, metadata_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
            """
            return db_optimizer.execute_insert_returning_id(sql, params)
        sql = """
            INSERT OR IGNORE INTO service_usage_events (  -- noqa: pg-audit (SQLite idempotency branch)
                user_id, service_id, event_category, event_type, metric_name,
                quantity, status, idempotency_key, correlation_id,
                resource_type, resource_id, metadata_json, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return db_optimizer.execute_insert_returning_id(sql, params)

    return db_optimizer.execute_insert_returning_id(
        """
        INSERT INTO service_usage_events (
            user_id, service_id, event_category, event_type, metric_name,
            quantity, status, idempotency_key, correlation_id,
            resource_type, resource_id, metadata_json, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        params,
    )


def upsert_daily_rollup(
    *,
    user_id: int,
    service_id: str,
    day: str,
    metric_name: str,
    event_category: str,
    quantity_delta: float = 0,
    success_delta: int = 0,
    failure_delta: int = 0,
    event_delta: int = 1,
    last_event_at: Optional[str] = None,
) -> None:
    if not user_id or not db_optimizer.table_exists("service_daily_rollups"):
        return
    sid = normalize_service_id(service_id)
    params = (
        user_id,
        sid,
        day,
        metric_name,
        event_category,
        quantity_delta,
        success_delta,
        failure_delta,
        event_delta,
        last_event_at or datetime.now(timezone.utc).isoformat(),
    )
    if db_optimizer.db_type == "postgresql":
        db_optimizer.execute_query(
            """
            INSERT INTO service_daily_rollups (
                user_id, service_id, day, metric_name, event_category,
                total_quantity, success_count, failure_count, event_count,
                last_event_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, service_id, day, metric_name, event_category)
            DO UPDATE SET
                total_quantity = service_daily_rollups.total_quantity + EXCLUDED.total_quantity,
                success_count = service_daily_rollups.success_count + EXCLUDED.success_count,
                failure_count = service_daily_rollups.failure_count + EXCLUDED.failure_count,
                event_count = service_daily_rollups.event_count + EXCLUDED.event_count,
                last_event_at = EXCLUDED.last_event_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            params,
            fetch=False,
        )
        return
    db_optimizer.execute_query(
        """
        INSERT INTO service_daily_rollups (
            user_id, service_id, day, metric_name, event_category,
            total_quantity, success_count, failure_count, event_count,
            last_event_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, service_id, day, metric_name, event_category)
        DO UPDATE SET
            total_quantity = total_quantity + excluded.total_quantity,
            success_count = success_count + excluded.success_count,
            failure_count = failure_count + excluded.failure_count,
            event_count = event_count + excluded.event_count,
            last_event_at = excluded.last_event_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        params,
        fetch=False,
    )


def upsert_tenant_metric(
    *,
    user_id: int,
    service_id: str,
    metric_name: str,
    window_type: str,
    metric_value: float,
    last_activity_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    increment: bool = True,
) -> None:
    if not user_id or not db_optimizer.table_exists("tenant_service_metrics"):
        return
    sid = normalize_service_id(service_id)
    params = (
        user_id,
        sid,
        metric_name,
        window_type,
        metric_value,
        last_activity_at or datetime.now(timezone.utc).isoformat(),
        _sanitize_metadata(metadata),
    )
    value_expr = (
        "tenant_service_metrics.metric_value + EXCLUDED.metric_value"
        if increment
        else "EXCLUDED.metric_value"
    )
    value_expr_sqlite = (
        "metric_value + excluded.metric_value" if increment else "excluded.metric_value"
    )
    if db_optimizer.db_type == "postgresql":
        db_optimizer.execute_query(
            f"""
            INSERT INTO tenant_service_metrics (
                user_id, service_id, metric_name, window_type,
                metric_value, last_activity_at, metadata_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, service_id, metric_name, window_type)
            DO UPDATE SET
                metric_value = {value_expr},
                last_activity_at = EXCLUDED.last_activity_at,
                metadata_json = EXCLUDED.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            params,
            fetch=False,
        )
        return
    db_optimizer.execute_query(
        f"""
        INSERT INTO tenant_service_metrics (
            user_id, service_id, metric_name, window_type,
            metric_value, last_activity_at, metadata_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, service_id, metric_name, window_type)
        DO UPDATE SET
            metric_value = {value_expr_sqlite},
            last_activity_at = excluded.last_activity_at,
            metadata_json = excluded.metadata_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        params,
        fetch=False,
    )


def list_usage_events(
    user_id: int,
    *,
    service_id: Optional[str] = None,
    day: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    if not _tables_ready():
        return []
    clauses = ["user_id = ?"]
    params: List[Any] = [user_id]
    if service_id:
        clauses.append("service_id = ?")
        params.append(normalize_service_id(service_id))
    if day:
        clauses.append("DATE(created_at) = DATE(?)")
        params.append(day)
    params.append(limit)
    rows = db_optimizer.execute_query(
        f"""
        SELECT id, service_id, event_category, event_type, metric_name,
               quantity, status, correlation_id, resource_type, resource_id,
               source, created_at
        FROM service_usage_events
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        tuple(params),
    )
    return [dict(r) for r in (rows or [])]


def replace_daily_rollup(
    *,
    user_id: int,
    service_id: str,
    day: str,
    metric_name: str,
    event_category: str,
    total_quantity: float,
    success_count: int,
    failure_count: int,
    event_count: int,
    last_event_at: Optional[str] = None,
) -> None:
    """Set rollup row to exact aggregates (used by rebuild, not incremental events)."""
    if not user_id or not db_optimizer.table_exists("service_daily_rollups"):
        return
    sid = normalize_service_id(service_id)
    params = (
        user_id,
        sid,
        day,
        metric_name,
        event_category,
        total_quantity,
        success_count,
        failure_count,
        event_count,
        last_event_at or datetime.now(timezone.utc).isoformat(),
    )
    if db_optimizer.db_type == "postgresql":
        db_optimizer.execute_query(
            """
            INSERT INTO service_daily_rollups (
                user_id, service_id, day, metric_name, event_category,
                total_quantity, success_count, failure_count, event_count,
                last_event_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, service_id, day, metric_name, event_category)
            DO UPDATE SET
                total_quantity = EXCLUDED.total_quantity,
                success_count = EXCLUDED.success_count,
                failure_count = EXCLUDED.failure_count,
                event_count = EXCLUDED.event_count,
                last_event_at = EXCLUDED.last_event_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            params,
            fetch=False,
        )
        return
    db_optimizer.execute_query(
        """
        INSERT INTO service_daily_rollups (
            user_id, service_id, day, metric_name, event_category,
            total_quantity, success_count, failure_count, event_count,
            last_event_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, service_id, day, metric_name, event_category)
        DO UPDATE SET
            total_quantity = excluded.total_quantity,
            success_count = excluded.success_count,
            failure_count = excluded.failure_count,
            event_count = excluded.event_count,
            last_event_at = excluded.last_event_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        params,
        fetch=False,
    )


def sum_daily_rollups(
    user_id: int,
    *,
    service_id: Optional[str] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    if not db_optimizer.table_exists("service_daily_rollups"):
        return []
    clauses = ["user_id = ?"]
    params: List[Any] = [user_id]
    if service_id:
        clauses.append("service_id = ?")
        params.append(normalize_service_id(service_id))
    params.append(days)
    rows = db_optimizer.execute_query(
        f"""
        SELECT service_id, day, metric_name, event_category,
               total_quantity, success_count, failure_count, event_count,
               last_event_at
        FROM service_daily_rollups
        WHERE {' AND '.join(clauses)}
          AND day >= date('now', '-' || ? || ' days')
        ORDER BY day DESC, service_id, metric_name
        """,
        tuple(params),
    )
    return [dict(r) for r in (rows or [])]
