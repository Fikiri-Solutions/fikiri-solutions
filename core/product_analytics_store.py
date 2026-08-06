"""Persistence for product analytics tables.

Production schema: scripts/migrations/009_product_analytics.sql
Tests / local SQLite: ensure_product_analytics_tables() applies compatible DDL once.
Never call ensure from request handlers in production paths — ingest checks table_exists.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database_optimization import db_optimizer
from core.product_analytics_registry import SCHEMA_VERSION, aggregate_retention_days, raw_retention_days

logger = logging.getLogger(__name__)

_TABLES_READY = False


def ensure_product_analytics_tables() -> None:
    """Idempotent DDL for tests and local SQLite. Not for request-time Postgres prod."""
    global _TABLES_READY
    if _TABLES_READY and db_optimizer.table_exists("product_events"):
        return
    # Prefer BIGSERIAL; db_optimizer translates to SQLite INTEGER PRIMARY KEY on local.
    # Production Postgres schema: scripts/migrations/009_product_analytics.sql
    pk = "BIGSERIAL PRIMARY KEY"
    db_optimizer.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS product_events (
            id {pk},
            tenant_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            event_source TEXT NOT NULL,
            feature_key TEXT,
            workflow_key TEXT,
            properties_json TEXT,
            occurred_at TIMESTAMP NOT NULL,
            received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            session_id_hash TEXT,
            correlation_id TEXT,
            schema_version INTEGER NOT NULL DEFAULT 1,
            outcome_dedupe_key TEXT
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS tenant_daily_metrics (
            id {pk},
            tenant_id INTEGER NOT NULL,
            metric_date TEXT NOT NULL,
            active_users INTEGER NOT NULL DEFAULT 0,
            sessions INTEGER NOT NULL DEFAULT 0,
            meaningful_actions INTEGER NOT NULL DEFAULT 0,
            workflow_started INTEGER NOT NULL DEFAULT 0,
            workflow_completed INTEGER NOT NULL DEFAULT 0,
            workflow_failed INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            feature_usage_json TEXT,
            accessibility_signal_counts_json TEXT,
            last_event_at TIMESTAMP,
            aggregated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tenant_id, metric_date)
        )
        """,
        fetch=False,
    )
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_product_events_tenant_occurred ON product_events (tenant_id, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_product_events_tenant_name_occurred ON product_events (tenant_id, event_name, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_product_events_feature ON product_events (tenant_id, feature_key, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_product_events_workflow ON product_events (tenant_id, workflow_key, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_product_events_received ON product_events (received_at)",
        "CREATE INDEX IF NOT EXISTS idx_tenant_daily_metrics_date ON tenant_daily_metrics (metric_date)",
        "CREATE INDEX IF NOT EXISTS idx_tenant_daily_metrics_updated ON tenant_daily_metrics (updated_at)",
    ):
        try:
            db_optimizer.execute_query(sql, fetch=False)
        except Exception as exc:
            logger.debug("product analytics index ensure skipped: %s", type(exc).__name__)
    # Unique dedupe: allow multiple NULLs (partial unique index)
    try:
        db_optimizer.execute_query(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_product_events_outcome_dedupe
            ON product_events (tenant_id, outcome_dedupe_key)
            WHERE outcome_dedupe_key IS NOT NULL
            """,
            fetch=False,
        )
    except Exception as exc:
        logger.debug("product analytics dedupe index ensure skipped: %s", type(exc).__name__)
    # Ops counters (rollout observability — additive, tiny)
    try:
        db_optimizer.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS product_analytics_ops_daily (
                id {pk},
                tenant_id INTEGER NOT NULL,
                metric_date TEXT NOT NULL,
                storage_failures INTEGER NOT NULL DEFAULT 0,
                rejected_events INTEGER NOT NULL DEFAULT 0,
                unexpected_errors INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, metric_date)
            )
            """,
            fetch=False,
        )
    except Exception as exc:
        logger.debug("product analytics ops table ensure skipped: %s", type(exc).__name__)
    _TABLES_READY = True


def ops_tables_available() -> bool:
    try:
        return bool(db_optimizer.table_exists("product_analytics_ops_daily"))
    except Exception:
        return False


def increment_ops_counter(
    tenant_id: int,
    *,
    storage_failures: int = 0,
    rejected_events: int = 0,
    unexpected_errors: int = 0,
) -> bool:
    """Best-effort daily ops counter bump. Never raises to callers."""
    try:
        if not ops_tables_available():
            return False
        if storage_failures == 0 and rejected_events == 0 and unexpected_errors == 0:
            return True
        metric_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tid = int(tenant_id)
        rows = db_optimizer.execute_query(
            """
            SELECT id, storage_failures, rejected_events, unexpected_errors
            FROM product_analytics_ops_daily
            WHERE tenant_id = ? AND metric_date = ?
            LIMIT 1
            """,
            (tid, metric_date),
        )
        now = datetime.now(timezone.utc).isoformat()
        if rows:
            row = dict(rows[0]) if hasattr(rows[0], "keys") else {}
            db_optimizer.execute_query(
                """
                UPDATE product_analytics_ops_daily
                SET storage_failures = ?,
                    rejected_events = ?,
                    unexpected_errors = ?,
                    updated_at = ?
                WHERE tenant_id = ? AND metric_date = ?
                """,
                (
                    int(row.get("storage_failures") or 0) + int(storage_failures),
                    int(row.get("rejected_events") or 0) + int(rejected_events),
                    int(row.get("unexpected_errors") or 0) + int(unexpected_errors),
                    now,
                    tid,
                    metric_date,
                ),
                fetch=False,
            )
        else:
            db_optimizer.execute_query(
                """
                INSERT INTO product_analytics_ops_daily (
                    tenant_id, metric_date, storage_failures, rejected_events,
                    unexpected_errors, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    metric_date,
                    int(storage_failures),
                    int(rejected_events),
                    int(unexpected_errors),
                    now,
                ),
                fetch=False,
            )
        return True
    except Exception as exc:
        logger.warning(
            "product analytics ops counter bump failed",
            extra={
                "event": "product_analytics.ops_counter_failed",
                "exception_class": type(exc).__name__,
            },
        )
        return False


def sum_ops_counters(tenant_id: int, *, since_date: str) -> Dict[str, int]:
    empty = {
        "storage_failures": 0,
        "rejected_events": 0,
        "unexpected_errors": 0,
    }
    try:
        if not ops_tables_available():
            return empty
        rows = db_optimizer.execute_query(
            """
            SELECT storage_failures, rejected_events, unexpected_errors
            FROM product_analytics_ops_daily
            WHERE tenant_id = ? AND metric_date >= ?
            LIMIT 400
            """,
            (int(tenant_id), since_date),
        )
        out = dict(empty)
        for row in rows or []:
            r = dict(row) if hasattr(row, "keys") else {}
            out["storage_failures"] += int(r.get("storage_failures") or 0)
            out["rejected_events"] += int(r.get("rejected_events") or 0)
            out["unexpected_errors"] += int(r.get("unexpected_errors") or 0)
        return out
    except Exception:
        return empty


def tables_available() -> bool:
    try:
        return bool(db_optimizer.table_exists("product_events"))
    except Exception:
        return False


def insert_product_event(
    *,
    tenant_id: int,
    actor_user_id: int,
    event_name: str,
    event_source: str,
    properties: Dict[str, Any],
    occurred_at: datetime,
    session_id_hash: Optional[str] = None,
    correlation_id: Optional[str] = None,
    outcome_dedupe_key: Optional[str] = None,
) -> Optional[int]:
    """Insert one event. Returns id, or None on duplicate dedupe / failure."""
    if not tables_available():
        return None
    feature_key = properties.get("feature_key")
    workflow_key = properties.get("workflow_key")
    props_json = json.dumps(properties, separators=(",", ":"), default=str) if properties else None
    params = (
        int(tenant_id),
        int(actor_user_id),
        event_name,
        event_source,
        feature_key,
        workflow_key,
        props_json,
        occurred_at.isoformat() if isinstance(occurred_at, datetime) else str(occurred_at),
        session_id_hash or properties.get("session_id_hash"),
        correlation_id or properties.get("correlation_id"),
        SCHEMA_VERSION,
        outcome_dedupe_key,
    )
    sql = """
        INSERT INTO product_events (
            tenant_id, actor_user_id, event_name, event_source,
            feature_key, workflow_key, properties_json, occurred_at,
            session_id_hash, correlation_id, schema_version, outcome_dedupe_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        if outcome_dedupe_key:
            existing = db_optimizer.execute_query(
                """
                SELECT id FROM product_events
                WHERE tenant_id = ? AND outcome_dedupe_key = ?
                LIMIT 1
                """,
                (int(tenant_id), outcome_dedupe_key),
            )
            if existing:
                return None
        return db_optimizer.execute_insert_returning_id(sql, params)
    except Exception as exc:
        # Unique violation on dedupe → treat as duplicate (not stored again)
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            return None
        logger.warning(
            "product_analytics insert failed",
            extra={"event": "product_analytics.insert_failed", "error_type": type(exc).__name__},
        )
        raise


def upsert_daily_metric_counters(
    *,
    tenant_id: int,
    metric_date: str,
    increments: Dict[str, int],
    feature_key: Optional[str] = None,
    last_event_at: Optional[datetime] = None,
) -> bool:
    """Idempotent-ish daily counter bump. Returns False on storage failure."""
    if not tables_available() or not db_optimizer.table_exists("tenant_daily_metrics"):
        return False
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT id, sessions, meaningful_actions, workflow_started, workflow_completed,
                   workflow_failed, error_count, feature_usage_json, active_users
            FROM tenant_daily_metrics
            WHERE tenant_id = ? AND metric_date = ?
            LIMIT 1
            """,
            (int(tenant_id), metric_date),
        )
        now = datetime.now(timezone.utc).isoformat()
        feature_usage: Dict[str, int] = {}
        if rows:
            row = dict(rows[0]) if hasattr(rows[0], "keys") else {}
            raw_fu = row.get("feature_usage_json")
            if raw_fu:
                try:
                    feature_usage = json.loads(raw_fu) if isinstance(raw_fu, str) else {}
                except Exception:
                    feature_usage = {}
            if feature_key:
                feature_usage[feature_key] = int(feature_usage.get(feature_key) or 0) + 1
            sessions = int(row.get("sessions") or 0) + int(increments.get("sessions") or 0)
            meaningful = int(row.get("meaningful_actions") or 0) + int(increments.get("meaningful_actions") or 0)
            w_started = int(row.get("workflow_started") or 0) + int(increments.get("workflow_started") or 0)
            w_completed = int(row.get("workflow_completed") or 0) + int(increments.get("workflow_completed") or 0)
            w_failed = int(row.get("workflow_failed") or 0) + int(increments.get("workflow_failed") or 0)
            errors = int(row.get("error_count") or 0) + int(increments.get("error_count") or 0)
            active_users = max(int(row.get("active_users") or 0), int(increments.get("active_users") or 0), 1)
            db_optimizer.execute_query(
                """
                UPDATE tenant_daily_metrics SET
                    active_users = ?, sessions = ?, meaningful_actions = ?,
                    workflow_started = ?, workflow_completed = ?, workflow_failed = ?,
                    error_count = ?, feature_usage_json = ?,
                    last_event_at = COALESCE(?, last_event_at),
                    aggregated_at = ?, updated_at = ?
                WHERE tenant_id = ? AND metric_date = ?
                """,
                (
                    active_users,
                    sessions,
                    meaningful,
                    w_started,
                    w_completed,
                    w_failed,
                    errors,
                    json.dumps(feature_usage, separators=(",", ":")),
                    last_event_at.isoformat() if last_event_at else None,
                    now,
                    now,
                    int(tenant_id),
                    metric_date,
                ),
                fetch=False,
            )
        else:
            if feature_key:
                feature_usage[feature_key] = 1
            db_optimizer.execute_query(
                """
                INSERT INTO tenant_daily_metrics (
                    tenant_id, metric_date, active_users, sessions, meaningful_actions,
                    workflow_started, workflow_completed, workflow_failed, error_count,
                    feature_usage_json, last_event_at, aggregated_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(tenant_id),
                    metric_date,
                    max(int(increments.get("active_users") or 0), 1),
                    int(increments.get("sessions") or 0),
                    int(increments.get("meaningful_actions") or 0),
                    int(increments.get("workflow_started") or 0),
                    int(increments.get("workflow_completed") or 0),
                    int(increments.get("workflow_failed") or 0),
                    int(increments.get("error_count") or 0),
                    json.dumps(feature_usage, separators=(",", ":")) if feature_usage else None,
                    last_event_at.isoformat() if last_event_at else None,
                    now,
                    now,
                ),
                fetch=False,
            )
        return True
    except Exception as exc:
        logger.warning(
            "product_analytics daily upsert failed",
            extra={"event": "product_analytics.aggregate_failed", "error_type": type(exc).__name__},
        )
        return False


def cleanup_expired_product_events(*, batch_size: int = 500) -> Dict[str, Any]:
    """Dialect-safe bounded cleanup: select IDs then delete by ID."""
    if not tables_available():
        return {"success": True, "deleted": 0, "skipped": True}
    batch_size = max(1, min(int(batch_size), 2000))
    cutoff = datetime.now(timezone.utc) - timedelta(days=raw_retention_days())
    cutoff_s = cutoff.isoformat()
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT id FROM product_events
            WHERE occurred_at < ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (cutoff_s, batch_size),
        )
        ids: List[int] = []
        for row in rows or []:
            if hasattr(row, "keys"):
                ids.append(int(row["id"]))
            else:
                ids.append(int(row[0]))
        if not ids:
            return {"success": True, "deleted": 0}
        placeholders = ",".join(["?"] * len(ids))
        db_optimizer.execute_query(
            f"DELETE FROM product_events WHERE id IN ({placeholders})",
            tuple(ids),
            fetch=False,
        )
        return {"success": True, "deleted": len(ids)}
    except Exception as exc:
        logger.warning(
            "product_analytics cleanup failed",
            extra={"event": "product_analytics.cleanup_failed", "error_type": type(exc).__name__},
        )
        return {"success": False, "deleted": 0, "error_type": type(exc).__name__}


def cleanup_expired_daily_metrics(*, batch_size: int = 500) -> Dict[str, Any]:
    if not tables_available() or not db_optimizer.table_exists("tenant_daily_metrics"):
        return {"success": True, "deleted": 0, "skipped": True}
    batch_size = max(1, min(int(batch_size), 2000))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=aggregate_retention_days())).strftime("%Y-%m-%d")
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT id FROM tenant_daily_metrics
            WHERE metric_date < ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (cutoff, batch_size),
        )
        ids = []
        for row in rows or []:
            ids.append(int(row["id"] if hasattr(row, "keys") else row[0]))
        if not ids:
            return {"success": True, "deleted": 0}
        placeholders = ",".join(["?"] * len(ids))
        db_optimizer.execute_query(
            f"DELETE FROM tenant_daily_metrics WHERE id IN ({placeholders})",
            tuple(ids),
            fetch=False,
        )
        return {"success": True, "deleted": len(ids)}
    except Exception as exc:
        return {"success": False, "deleted": 0, "error_type": type(exc).__name__}


def delete_tenant_analytics(tenant_id: int) -> Dict[str, Any]:
    """Remove analytics for a tenant (account deletion helper)."""
    if not tables_available():
        return {"success": True, "events_deleted": 0, "metrics_deleted": 0, "skipped": True}
    try:
        db_optimizer.execute_query(
            "DELETE FROM product_events WHERE tenant_id = ?",
            (int(tenant_id),),
            fetch=False,
        )
        db_optimizer.execute_query(
            "DELETE FROM tenant_daily_metrics WHERE tenant_id = ?",
            (int(tenant_id),),
            fetch=False,
        )
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error_type": type(exc).__name__}


def latest_aggregate_timestamp(tenant_id: int) -> Optional[str]:
    if not tables_available() or not db_optimizer.table_exists("tenant_daily_metrics"):
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT updated_at FROM tenant_daily_metrics
        WHERE tenant_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (int(tenant_id),),
    )
    if not rows:
        return None
    row = rows[0]
    val = row["updated_at"] if hasattr(row, "keys") else row[0]
    return str(val) if val is not None else None


def latest_event_timestamp(tenant_id: int) -> Optional[str]:
    if not tables_available():
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT occurred_at FROM product_events
        WHERE tenant_id = ?
        ORDER BY occurred_at DESC
        LIMIT 1
        """,
        (int(tenant_id),),
    )
    if not rows:
        return None
    row = rows[0]
    val = row["occurred_at"] if hasattr(row, "keys") else row[0]
    return str(val) if val is not None else None


def earliest_meaningful_outcome_at(tenant_id: int) -> Optional[str]:
    """Earliest server outcome event for TT FV. No raw dump — single indexed lookup."""
    if not tables_available():
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT occurred_at FROM product_events
        WHERE tenant_id = ?
          AND event_name IN ('outcome.lead_captured', 'outcome.sync_completed',
                             'outcome.integration_connected', 'outcome.onboarding_completed')
          AND event_source IN ('server', 'derived')
        ORDER BY occurred_at ASC
        LIMIT 1
        """,
        (int(tenant_id),),
    )
    if not rows:
        return None
    row = rows[0]
    val = row["occurred_at"] if hasattr(row, "keys") else row[0]
    return str(val) if val is not None else None


def count_outcome_events(
    tenant_id: int,
    *,
    event_name: str,
    since_date: Optional[str] = None,
) -> int:
    if not tables_available():
        return 0
    clauses = ["tenant_id = ?", "event_name = ?", "event_source IN ('server', 'derived')"]
    params: list = [int(tenant_id), event_name]
    if since_date:
        clauses.append("occurred_at >= ?")
        params.append(since_date)
    rows = db_optimizer.execute_query(
        f"SELECT COUNT(*) AS c FROM product_events WHERE {' AND '.join(clauses)}",
        tuple(params),
    )
    if not rows:
        return 0
    return int(rows[0]["c"] if hasattr(rows[0], "keys") else rows[0][0])


def sum_daily_metrics(tenant_id: int, *, since_date: str) -> Dict[str, Any]:
    """Bounded aggregate read for dossier — no raw event scan."""
    empty = {
        "sessions": 0,
        "meaningful_actions": 0,
        "workflow_started": 0,
        "workflow_completed": 0,
        "workflow_failed": 0,
        "error_count": 0,
        "active_days": 0,
        "feature_usage": {},
        "rows": 0,
    }
    if not tables_available() or not db_optimizer.table_exists("tenant_daily_metrics"):
        return empty
    rows = db_optimizer.execute_query(
        """
        SELECT sessions, meaningful_actions, workflow_started, workflow_completed,
               workflow_failed, error_count, feature_usage_json, metric_date
        FROM tenant_daily_metrics
        WHERE tenant_id = ? AND metric_date >= ?
        ORDER BY metric_date DESC
        LIMIT 400
        """,
        (int(tenant_id), since_date),
    )
    out = dict(empty)
    feature_usage: Dict[str, int] = {}
    for row in rows or []:
        r = dict(row) if hasattr(row, "keys") else {}
        out["sessions"] += int(r.get("sessions") or 0)
        out["meaningful_actions"] += int(r.get("meaningful_actions") or 0)
        out["workflow_started"] += int(r.get("workflow_started") or 0)
        out["workflow_completed"] += int(r.get("workflow_completed") or 0)
        out["workflow_failed"] += int(r.get("workflow_failed") or 0)
        out["error_count"] += int(r.get("error_count") or 0)
        if int(r.get("sessions") or 0) > 0 or int(r.get("meaningful_actions") or 0) > 0:
            out["active_days"] += 1
        raw_fu = r.get("feature_usage_json")
        if raw_fu:
            try:
                fu = json.loads(raw_fu) if isinstance(raw_fu, str) else raw_fu
                if isinstance(fu, dict):
                    for k, v in fu.items():
                        feature_usage[str(k)] = feature_usage.get(str(k), 0) + int(v or 0)
            except Exception:
                pass
        out["rows"] += 1
    out["feature_usage"] = feature_usage
    return out
