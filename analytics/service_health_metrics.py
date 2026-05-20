"""
Operational health metrics derived from existing tables (no duplicate billing writes).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from analytics.service_usage_constants import normalize_service_id
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def get_automation_health(user_id: int, *, days: int = 30) -> Dict[str, Any]:
    if not db_optimizer.table_exists("automation_executions"):
        return {"total": 0, "success": 0, "failure": 0, "success_rate": 0.0}
    since = _days_ago_iso(days)
    rows = db_optimizer.execute_query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM automation_executions
        WHERE user_id = ? AND executed_at >= ?
        GROUP BY status
        """,
        (user_id, since),
    )
    success = failure = 0
    for row in rows or []:
        status = (row.get("status") or "").lower()
        cnt = int(row.get("cnt") or 0)
        if status == "success":
            success += cnt
        else:
            failure += cnt
    total = success + failure
    rate = (success / total) if total else 0.0
    return {
        "total": total,
        "success": success,
        "failure": failure,
        "success_rate": round(rate, 4),
        "window_days": days,
    }


def get_email_sync_health(user_id: int, *, days: int = 7) -> Dict[str, Any]:
    if not db_optimizer.table_exists("synced_emails"):
        return {"synced_count": 0, "processed_count": 0, "window_days": days}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    total_rows = db_optimizer.execute_query(
        """
        SELECT COUNT(*) AS value FROM synced_emails
        WHERE user_id = ? AND date >= ?
        """,
        (user_id, since),
    )
    processed_rows = db_optimizer.execute_query(
        """
        SELECT COUNT(*) AS value FROM synced_emails
        WHERE user_id = ? AND date >= ? AND processed = TRUE
        """,
        (user_id, since),
    )
    synced = int((total_rows[0].get("value") if total_rows else 0) or 0)
    processed = int((processed_rows[0].get("value") if processed_rows else 0) or 0)
    return {
        "synced_count": synced,
        "processed_count": processed,
        "processed_rate": round(processed / synced, 4) if synced else 0.0,
        "window_days": days,
    }


def get_triage_health(user_id: int, *, days: int = 30) -> Dict[str, Any]:
    if not db_optimizer.table_exists("email_classifications"):
        return {"classified_count": 0, "window_days": days}
    since = _days_ago_iso(days)
    rows = db_optimizer.execute_query(
        """
        SELECT COUNT(*) AS value FROM email_classifications
        WHERE user_id = ? AND updated_at >= ?
        """,
        (user_id, since),
    )
    count = int((rows[0].get("value") if rows else 0) or 0)
    confidence_rows = db_optimizer.execute_query(
        """
        SELECT AVG(confidence) AS avg_confidence
        FROM email_classifications
        WHERE user_id = ? AND updated_at >= ? AND confidence IS NOT NULL
        """,
        (user_id, since),
    )
    avg_conf = None
    if confidence_rows and confidence_rows[0].get("avg_confidence") is not None:
        avg_conf = round(float(confidence_rows[0]["avg_confidence"]), 4)
    return {
        "classified_count": count,
        "avg_confidence": avg_conf,
        "window_days": days,
    }


def get_service_adoption(user_id: int) -> Dict[str, Any]:
    """Feature activation from user_services (config, not usage)."""
    if not db_optimizer.table_exists("user_services"):
        return {"enabled_services": [], "dormant_services": []}
    rows = db_optimizer.execute_query(
        """
        SELECT service_id, enabled, status, updated_at, last_sync_at
        FROM user_services
        WHERE user_id = ?
        """,
        (user_id,),
    )
    enabled: List[str] = []
    dormant: List[str] = []
    for row in rows or []:
        sid = normalize_service_id(row.get("service_id") or "")
        if row.get("enabled"):
            enabled.append(sid)
        else:
            dormant.append(sid)
    return {
        "enabled_services": enabled,
        "dormant_services": dormant,
        "total_configured": len(rows or []),
    }


def get_billing_intelligence(user_id: int) -> Dict[str, Any]:
    """Cost proxy from billing_usage (canonical metering)."""
    if not db_optimizer.table_exists("billing_usage"):
        return {"month": None, "by_type": {}, "ai_responses": 0}
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    rows = db_optimizer.execute_query(
        """
        SELECT usage_type, SUM(quantity) AS total
        FROM billing_usage
        WHERE user_id = ? AND month = ?
        GROUP BY usage_type
        """,
        (user_id, month_key),
    )
    by_type = {(r.get("usage_type") or ""): int(r.get("total") or 0) for r in (rows or [])}
    ai = by_type.get("ai_responses", 0)
    return {
        "month": month_key,
        "by_type": by_type,
        "ai_responses": ai,
        "estimated_tokens": ai * 120,
    }


def get_tenant_health_snapshot(user_id: int) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "automation": get_automation_health(user_id),
        "email_sync": get_email_sync_health(user_id),
        "email_triage": get_triage_health(user_id),
        "adoption": get_service_adoption(user_id),
        "billing": get_billing_intelligence(user_id),
    }
