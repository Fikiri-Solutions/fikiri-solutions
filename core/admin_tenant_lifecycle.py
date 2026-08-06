"""Reversible tenant lifecycle controls for platform operators.

Pause / resume flips users.is_active. Requires platform.ops.write which is
gated by ADMIN_DESTRUCTIVE_ENABLED. No hard delete here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _row_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {}


def get_tenant_active_state(tenant_id: int) -> Optional[Dict[str, Any]]:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        """
        SELECT id, email, name, is_active
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (int(tenant_id),),
    )
    if not rows:
        return None
    row = _row_dict(rows[0])
    active_raw = row.get("is_active")
    if isinstance(active_raw, bool):
        is_active = active_raw
    else:
        try:
            is_active = int(active_raw or 0) == 1
        except (TypeError, ValueError):
            is_active = bool(active_raw)
    return {
        "id": int(row.get("id") or tenant_id),
        "email": row.get("email"),
        "name": row.get("name"),
        "is_active": is_active,
    }


def set_tenant_active(
    tenant_id: int,
    *,
    active: bool,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Set users.is_active.

    Returns (ok, reason_code, before_after_summary).
    """
    from core.database_optimization import db_optimizer

    before = get_tenant_active_state(tenant_id)
    if not before:
        return False, "TENANT_NOT_FOUND", None

    if bool(before["is_active"]) == bool(active):
        return True, "ALREADY_IN_STATE", {
            "before": {"is_active": before["is_active"]},
            "after": {"is_active": before["is_active"]},
            "unchanged": True,
        }

    active_val = 1 if active else 0
    db_optimizer.execute_query(
        """
        UPDATE users
        SET is_active = ?
        WHERE id = ?
        """,
        (active_val, int(tenant_id)),
        fetch=False,
    )
    after = get_tenant_active_state(tenant_id)
    if not after or bool(after["is_active"]) != bool(active):
        return False, "UPDATE_FAILED", {
            "before": {"is_active": before["is_active"]},
            "after": {"is_active": after["is_active"] if after else None},
        }
    return True, "UPDATED", {
        "before": {"is_active": before["is_active"], "email": before.get("email")},
        "after": {"is_active": after["is_active"], "email": after.get("email")},
        "unchanged": False,
    }
