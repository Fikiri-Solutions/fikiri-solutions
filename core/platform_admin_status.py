"""Read-only platform operator status snapshot for /admin Overview.

Assembles existing security, audit, sync, and analytics signals.
No background aggregation, no mutations, no new capability model.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AUDIT_WINDOW_HOURS = 24
SYNC_STATUS_KEYS = ("failed", "retrying", "pending", "processing")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_denied_audit_actions(*, window_hours: int = AUDIT_WINDOW_HOURS) -> Dict[str, Any]:
    """Bounded denied-action count from admin_audit_log (indexed outcome)."""
    from core.admin_audit import ensure_admin_audit_table
    from core.database_optimization import db_optimizer

    hours = max(1, min(int(window_hours), 168))
    since = _utc_now() - timedelta(hours=hours)
    since_iso = _iso_utc(since)
    try:
        ensure_admin_audit_table()
        rows = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS total
            FROM admin_audit_log
            WHERE outcome = ?
              AND created_at >= ?
            """,
            ("denied", since_iso),
        )
        total = 0
        if rows:
            row = rows[0]
            total = int(row.get("total") if hasattr(row, "keys") else row[0])
        return {
            "available": True,
            "count": total,
            "window_hours": hours,
            "since": since_iso,
        }
    except Exception as exc:
        logger.warning("platform status denied-audit count failed: %s", type(exc).__name__)
        return {
            "available": False,
            "count": None,
            "window_hours": hours,
            "since": since_iso,
            "reason": "AUDIT_COUNT_UNAVAILABLE",
        }


def count_active_sync_jobs_by_status() -> Dict[str, Any]:
    """Cross-tenant counts for actionable sync statuses only (bounded GROUP BY)."""
    from core.database_optimization import db_optimizer

    empty = {k: 0 for k in SYNC_STATUS_KEYS}
    try:
        if not db_optimizer.table_exists("gmail_sync_jobs"):
            return {
                "available": False,
                "counts": empty,
                "reason": "SYNC_JOBS_TABLE_UNAVAILABLE",
            }
        placeholders = ", ".join(["?"] * len(SYNC_STATUS_KEYS))
        rows = db_optimizer.execute_query(
            f"""
            SELECT status, COUNT(*) AS total
            FROM gmail_sync_jobs
            WHERE status IN ({placeholders})
            GROUP BY status
            """,
            tuple(SYNC_STATUS_KEYS),
        )
        counts = dict(empty)
        for row in rows or []:
            if hasattr(row, "keys"):
                status = str(row.get("status") or "").strip().lower()
                total = int(row.get("total") or 0)
            else:
                status = str(row[0] or "").strip().lower()
                total = int(row[1] or 0)
            if status in counts:
                counts[status] = total
        return {"available": True, "counts": counts}
    except Exception as exc:
        logger.warning("platform status sync counts failed: %s", type(exc).__name__)
        return {
            "available": False,
            "counts": empty,
            "reason": "SYNC_COUNT_UNAVAILABLE",
        }


def analytics_pipeline_status() -> Dict[str, Any]:
    """Platform-level analytics gate — not per-tenant reconciliation."""
    try:
        from core.product_analytics_registry import product_analytics_enabled
        from core.product_analytics_store import tables_available

        enabled = bool(product_analytics_enabled())
        tables_ok = bool(tables_available()) if enabled else False
        if not enabled:
            state = "disabled"
        elif tables_ok:
            state = "available"
        else:
            state = "unavailable"
        return {
            "available": True,
            "enabled": enabled,
            "tables_available": tables_ok,
            "state": state,
        }
    except Exception as exc:
        logger.warning("platform status analytics snapshot failed: %s", type(exc).__name__)
        return {
            "available": False,
            "enabled": None,
            "tables_available": None,
            "state": "unknown",
            "reason": "ANALYTICS_STATUS_UNAVAILABLE",
        }


def build_platform_status(*, actor_user_id: int, capabilities: List[str]) -> Dict[str, Any]:
    """Assemble Overview contract. Caller enforces authz."""
    from core.admin_security import (
        admin_lockdown_active,
        destructive_admin_enabled,
        get_admin_step_up_state,
        impersonation_disabled,
        mfa_required_for_operators,
        operator_mfa_enrolled,
        step_up_completed_with_mfa,
    )
    from core.secure_sessions import get_current_user_id, is_impersonating

    step_state = get_admin_step_up_state(int(actor_user_id))
    step_expires_at: Optional[str] = None
    if step_state and step_state.get("exp") is not None:
        try:
            step_expires_at = _iso_utc(
                datetime.fromtimestamp(float(step_state["exp"]), tz=timezone.utc)
            )
        except (TypeError, ValueError, OSError):
            step_expires_at = None

    denied = count_denied_audit_actions()
    sync = count_active_sync_jobs_by_status()
    analytics = analytics_pipeline_status()

    sync_counts = sync.get("counts") or {}
    failed = int(sync_counts.get("failed") or 0)
    retrying = int(sync_counts.get("retrying") or 0)

    return {
        "generated_at": _iso_utc(_utc_now()),
        "operator": {
            "actor_user_id": int(actor_user_id),
            "effective_user_id": get_current_user_id(),
            "capabilities": list(capabilities),
            "security": {
                "mfa_required": mfa_required_for_operators(),
                "mfa_enrolled": operator_mfa_enrolled(int(actor_user_id)),
                "step_up_active": bool(step_state),
                "step_up_mfa_completed": step_up_completed_with_mfa(int(actor_user_id)),
                "step_up_expires_at": step_expires_at,
                "impersonating": is_impersonating(),
                "impersonation_disabled": impersonation_disabled(),
            },
        },
        "gates": {
            "lockdown": admin_lockdown_active(),
            "destructive_enabled": destructive_admin_enabled(),
        },
        "audit": {
            "denied_available": bool(denied.get("available")),
            "denied_count": denied.get("count"),
            "window_hours": denied.get("window_hours"),
            "since": denied.get("since"),
            "reason": denied.get("reason"),
            "investigate_path": "/admin/audit?outcome=denied",
        },
        "sync_jobs": {
            "available": bool(sync.get("available")),
            "failed": failed if sync.get("available") else None,
            "retrying": retrying if sync.get("available") else None,
            "pending": int(sync_counts.get("pending") or 0) if sync.get("available") else None,
            "processing": int(sync_counts.get("processing") or 0)
            if sync.get("available")
            else None,
            "actionable": (failed + retrying) if sync.get("available") else None,
            "reason": sync.get("reason"),
            "investigate_path": "/admin#failed-syncs",
        },
        "analytics": {
            "available": bool(analytics.get("available")),
            "enabled": analytics.get("enabled"),
            "tables_available": analytics.get("tables_available"),
            "state": analytics.get("state"),
            "reason": analytics.get("reason"),
        },
    }
