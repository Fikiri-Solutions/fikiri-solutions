"""Immutable audit trail for platform admin actions.

Records successful and denied actions. Never store passwords, tokens, or OAuth secrets.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from flask import request

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_TABLE_READY = False

_SECRET_KEY_RE = re.compile(
    r"(password|passwd|secret|token|refresh|access_token|api_key|authorization|oauth)",
    re.IGNORECASE,
)


def ensure_admin_audit_table() -> None:
    global _TABLE_READY
    if _TABLE_READY:
        return
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id BIGSERIAL PRIMARY KEY,
            actor_user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            before_json TEXT,
            after_json TEXT,
            ip_address TEXT,
            user_agent TEXT,
            metadata_json TEXT,
            outcome TEXT,
            capability TEXT,
            correlation_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (actor_user_id) REFERENCES users (id)
        )
        """,
        fetch=False,
    )
    _ensure_audit_columns()
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_actor_created
        ON admin_audit_log (actor_user_id, created_at DESC)
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_target_created
        ON admin_audit_log (target_type, target_id, created_at DESC)
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_outcome_created
        ON admin_audit_log (outcome, created_at DESC)
        """,
        fetch=False,
    )
    _TABLE_READY = True


def _ensure_audit_columns() -> None:
    """Additive columns for older DBs that created the table before Phase 1.5.

    Uses dialect-aware column listing via list_table_columns (not SQLite catalog SQL).
    """
    try:
        names = {str(c).lower() for c in (db_optimizer.list_table_columns("admin_audit_log") or [])}
    except Exception as exc:
        logger.warning("admin_audit_log column listing failed: %s", exc)
        names = set()

    for col, ddl in (
        ("outcome", "ALTER TABLE admin_audit_log ADD COLUMN outcome TEXT"),
        ("capability", "ALTER TABLE admin_audit_log ADD COLUMN capability TEXT"),
        ("correlation_id", "ALTER TABLE admin_audit_log ADD COLUMN correlation_id TEXT"),
    ):
        if col in names:
            continue
        try:
            db_optimizer.execute_query(ddl, fetch=False)
        except Exception as exc:
            # Column may already exist under concurrent bootstrap; ignore only that case.
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate column" in msg:
                continue
            logger.warning("admin_audit_log add column %s failed: %s", col, exc)

def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                out[key] = "[REDACTED]"
            else:
                out[key] = _redact_secrets(item)
        return out
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    if isinstance(value, str) and len(value) > 32 and value.count(".") >= 2:
        # Likely JWT-shaped; never persist.
        return "[REDACTED]"
    return value


def _json_dump(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(_redact_secrets(value), default=str)
    except Exception:
        return json.dumps({"serialization_error": True})


def record_admin_audit(
    *,
    actor_user_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    before: Any = None,
    after: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    outcome: str = "success",
    capability: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    ensure_admin_audit_table()
    outcome_norm = (outcome or "success").strip().lower()
    if outcome_norm not in ("success", "denied", "error"):
        outcome_norm = "success"
    meta = dict(metadata or {})
    meta.setdefault("outcome", outcome_norm)
    if capability:
        meta.setdefault("capability", capability)
    if correlation_id:
        meta.setdefault("correlation_id", correlation_id)
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO admin_audit_log (
                actor_user_id, action, target_type, target_id,
                before_json, after_json, ip_address, user_agent, metadata_json,
                outcome, capability, correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor_user_id,
                action,
                target_type,
                target_id,
                _json_dump(before),
                _json_dump(after),
                ip_address,
                user_agent,
                _json_dump(meta),
                outcome_norm,
                capability,
                correlation_id,
            ),
            fetch=False,
        )
    except Exception as exc:
        logger.error("Failed to record admin audit action=%s: %s", action, exc)


def record_admin_audit_from_request(
    *,
    actor_user_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    before: Any = None,
    after: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    outcome: str = "success",
    capability: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    ip_address = None
    user_agent = None
    corr = correlation_id
    try:
        if request:
            ip_address = request.remote_addr
            user_agent = (request.headers.get("User-Agent") or "")[:512] or None
            if not corr:
                from core.admin_security import get_request_correlation_id

                corr = get_request_correlation_id()
    except RuntimeError:
        pass
    record_admin_audit(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        outcome=outcome,
        capability=capability,
        correlation_id=corr,
    )


def list_admin_audit(
    *,
    limit: int = 50,
    offset: int = 0,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    outcome: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_admin_audit_table()
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    clauses = ["1=1"]
    params: List[Any] = []
    if actor_user_id is not None:
        clauses.append("actor_user_id = ?")
        params.append(actor_user_id)
    if target_type:
        clauses.append("target_type = ?")
        params.append(target_type)
    if target_id:
        clauses.append("target_id = ?")
        params.append(target_id)
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)

    where_sql = " AND ".join(clauses)
    rows = db_optimizer.execute_query(
        f"""
        SELECT id, actor_user_id, action, target_type, target_id,
               before_json, after_json, ip_address, user_agent, metadata_json,
               outcome, capability, correlation_id, created_at
        FROM admin_audit_log
        WHERE {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, offset]),
    )
    count_rows = db_optimizer.execute_query(
        f"SELECT COUNT(*) AS total FROM admin_audit_log WHERE {where_sql}",
        tuple(params),
    )
    total = 0
    if count_rows:
        row = count_rows[0]
        total = int(row.get("total") if hasattr(row, "keys") else row[0])

    items = []
    for row in rows or []:
        item = dict(row) if hasattr(row, "keys") else {
            "id": row[0],
            "actor_user_id": row[1],
            "action": row[2],
            "target_type": row[3],
            "target_id": row[4],
            "before_json": row[5],
            "after_json": row[6],
            "ip_address": row[7],
            "user_agent": row[8],
            "metadata_json": row[9],
            "outcome": row[10] if len(row) > 10 else None,
            "capability": row[11] if len(row) > 11 else None,
            "correlation_id": row[12] if len(row) > 12 else None,
            "created_at": row[13] if len(row) > 13 else None,
        }
        for key in ("before_json", "after_json", "metadata_json"):
            raw = item.get(key)
            if raw:
                try:
                    item[key.replace("_json", "")] = json.loads(raw)
                except Exception:
                    item[key.replace("_json", "")] = raw
            else:
                item[key.replace("_json", "")] = None
            item.pop(key, None)
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


def clear_admin_audit_for_tests() -> None:
    ensure_admin_audit_table()
    db_optimizer.execute_query("DELETE FROM admin_audit_log", fetch=False)
    # Allow ensure to re-run column checks in subsequent tests if needed.
    global _TABLE_READY
    _TABLE_READY = False
