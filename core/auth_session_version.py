"""Canonical auth session version for immediate access-token invalidation.

DB column ``users.auth_session_version`` is authoritative.
JWT claim ``asv`` must match the current DB value on every access-token verify.
Redis may cache the version for hot paths but is never trusted alone.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

CLAIM_KEY = "asv"
ACTOR_CLAIM_KEY = "actor_asv"
REDIS_KEY_PREFIX = "fikiri:auth:asv:"
_COLUMN_READY = False


def ensure_auth_session_version_column() -> None:
    """Additive migration: SQLite tests + PostgreSQL. Idempotent."""
    global _COLUMN_READY
    if _COLUMN_READY:
        return
    try:
        cols = {c.lower() for c in (db_optimizer.list_table_columns("users") or [])}
        if "auth_session_version" not in cols:
            db_optimizer.execute_query(
                "ALTER TABLE users ADD COLUMN auth_session_version INTEGER NOT NULL DEFAULT 1",
                fetch=False,
            )
            logger.info("Added users.auth_session_version column")
        _COLUMN_READY = True
    except Exception as exc:
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate column" in msg:
            _COLUMN_READY = True
            return
        logger.warning("ensure_auth_session_version_column failed: %s", exc)


def _redis_client():
    try:
        from core.redis_connection_helper import get_redis_client

        return get_redis_client()
    except Exception:
        try:
            from core.redis_cache import get_redis_cache

            cache = get_redis_cache()
            return getattr(cache, "client", None) or getattr(cache, "redis", None)
        except Exception:
            return None


def _cache_set(user_id: int, version: int) -> None:
    client = _redis_client()
    if not client:
        return
    try:
        client.setex(f"{REDIS_KEY_PREFIX}{int(user_id)}", 300, str(int(version)))
    except Exception:
        pass


def _cache_delete(user_id: int) -> None:
    client = _redis_client()
    if not client:
        return
    try:
        client.delete(f"{REDIS_KEY_PREFIX}{int(user_id)}")
    except Exception:
        pass


def get_auth_session_version(user_id: int, *, prefer_cache: bool = True) -> int:
    """Authoritative version from DB. Redis cache is optional and never used alone for authz."""
    ensure_auth_session_version_column()
    version = _read_db_version(user_id)
    if version is None:
        return 1
    if prefer_cache:
        _cache_set(user_id, version)
    return int(version)


def _read_db_version(user_id: int) -> Optional[int]:
    try:
        rows = db_optimizer.execute_query(
            "SELECT auth_session_version FROM users WHERE id = ? LIMIT 1",
            (int(user_id),),
        )
        if not rows:
            return None
        row = rows[0]
        raw = row.get("auth_session_version") if hasattr(row, "keys") else row[0]
        if raw is None:
            return 1
        return int(raw)
    except Exception as exc:
        # Column may not exist yet on a lagging worker — treat as 1.
        msg = str(exc).lower()
        if "auth_session_version" in msg or "no such column" in msg:
            ensure_auth_session_version_column()
            try:
                rows = db_optimizer.execute_query(
                    "SELECT auth_session_version FROM users WHERE id = ? LIMIT 1",
                    (int(user_id),),
                )
                if rows:
                    row = rows[0]
                    raw = row.get("auth_session_version") if hasattr(row, "keys") else row[0]
                    return int(raw or 1)
            except Exception:
                return 1
        logger.warning("read auth_session_version failed: %s", exc)
        return None


def bump_auth_session_version(user_id: int, *, cursor=None) -> int:
    """
    Increment version and invalidate cache.

    If ``cursor`` is provided (open DB transaction), use it so password update
    + version bump can commit atomically. Caller commits.
    """
    ensure_auth_session_version_column()
    uid = int(user_id)
    if cursor is not None:
        cursor.execute(
            "UPDATE users SET auth_session_version = COALESCE(auth_session_version, 1) + 1, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (uid,),
        )
        cursor.execute(
            "SELECT auth_session_version FROM users WHERE id = ?",
            (uid,),
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("user_not_found_for_asv_bump")
        if hasattr(row, "keys"):
            new_version = int(row["auth_session_version"] if "auth_session_version" in row.keys() else row[0])
        else:
            new_version = int(row[0])
    else:
        db_optimizer.execute_query(
            "UPDATE users SET auth_session_version = COALESCE(auth_session_version, 1) + 1, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (uid,),
            fetch=False,
        )
        new_version = get_auth_session_version(uid, prefer_cache=False)

    _cache_delete(uid)
    _cache_set(uid, new_version)
    return int(new_version)


def token_version_matches(payload: dict, *, user_row_version: Optional[int] = None) -> bool:
    """Return True iff access-token ``asv`` matches authoritative version."""
    if not isinstance(payload, dict):
        return False
    claim = payload.get(CLAIM_KEY)
    if claim is None:
        # Pre-migration tokens: reject so reset/revoke takes effect immediately.
        return False
    try:
        claimed = int(claim)
    except (TypeError, ValueError):
        return False

    uid = payload.get("user_id")
    if uid is None:
        return False

    if user_row_version is not None:
        current = int(user_row_version)
    else:
        current = get_auth_session_version(int(uid), prefer_cache=True)

    if claimed != current:
        return False

    # Impersonation: actor must also match.
    if payload.get("impersonating") and payload.get("actor_user_id") is not None:
        actor_claim = payload.get(ACTOR_CLAIM_KEY)
        if actor_claim is None:
            return False
        try:
            actor_claimed = int(actor_claim)
        except (TypeError, ValueError):
            return False
        actor_current = get_auth_session_version(int(payload["actor_user_id"]), prefer_cache=True)
        if actor_claimed != actor_current:
            return False

    return True
