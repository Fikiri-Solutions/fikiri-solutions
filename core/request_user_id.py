#!/usr/bin/env python3
"""
Request-scoped user id resolution.

Session/JWT identity is always preferred. Legacy `user_id` request fallback is
disabled by default and only enabled in test mode (or with explicit opt-in).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Request

from core import secure_sessions
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def _is_test_mode() -> bool:
    env = (os.getenv("FLASK_ENV") or "").strip().lower()
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or env == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def allow_request_user_id_fallback() -> bool:
    """Whether request user_id fallback is permitted."""
    if os.getenv("ALLOW_QUERY_USER_ID_FALLBACK") == "1":
        return True
    return _is_test_mode()


def _validate_active_user(user_id: int) -> bool:
    try:
        active = db_optimizer.sql_cast_int_eq_one("is_active")
        rows = db_optimizer.execute_query(
            f"SELECT id FROM users WHERE id = ? AND {active} LIMIT 1",
            (user_id,),
        )
        return bool(rows)
    except Exception as e:
        logger.warning("Failed user validation for fallback user_id=%s: %s", user_id, e)
        return False


def resolve_request_user_id(
    request: Request,
    *,
    current_user_id: Optional[int] = None,
    allow_query: bool = False,
    allow_body: bool = False,
) -> Optional[int]:
    """
    Resolve user id from authenticated context first, then optional request fallback.
    Returns None when unresolved or fallback is disabled/invalid.
    """
    user_id = current_user_id if current_user_id is not None else secure_sessions.get_current_user_id()
    if user_id:
        return int(user_id)

    if not allow_request_user_id_fallback():
        return None

    candidate = None
    if allow_query:
        candidate = request.args.get("user_id", type=int)
    if not candidate and allow_body:
        data = request.get_json(silent=True) or {}
        raw = data.get("user_id")
        try:
            candidate = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            candidate = None

    if not candidate:
        return None

    if not _validate_active_user(candidate):
        return None

    logger.info("Using request fallback user_id=%s (test/explicit mode)", candidate)
    return candidate
