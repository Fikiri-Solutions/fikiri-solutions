"""Shared helpers for platform-admin unit tests (xdist-safe)."""

from __future__ import annotations

from typing import Iterable


def stub_operator_account_usable(monkeypatch, *, usable: bool = True) -> None:
    """Bypass users-table lookup used by require_admin_step_up."""

    monkeypatch.setattr(
        "core.admin_security.operator_account_usable",
        lambda *_a, **_k: usable,
    )


def ensure_operator_user_rows(user_ids: Iterable[int] = (1,)) -> None:
    """Insert operator rows so admin_audit_log FK inserts succeed on empty xdist DBs."""

    from core.database_optimization import db_optimizer

    ids = [int(uid) for uid in user_ids]
    is_pg = getattr(db_optimizer, "db_type", None) == "postgresql"

    if not is_pg:
        db_optimizer.execute_query(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT,
                password_hash TEXT,
                name TEXT,
                is_active INTEGER DEFAULT 1
            )
            """,
            fetch=False,
        )

    for uid in ids:
        email = f"operator{uid}@example.com"
        name = f"Operator {uid}"
        if is_pg:
            try:
                db_optimizer.execute_query(
                    """
                    INSERT INTO users (id, email, password_hash, name, is_active)
                    VALUES (?, ?, 'x', ?, TRUE)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (uid, email, name),
                    fetch=False,
                )
            except Exception:
                db_optimizer.execute_query(
                    """
                    INSERT INTO users (id, email, is_active)
                    VALUES (?, ?, TRUE)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (uid, email),
                    fetch=False,
                )
        else:
            db_optimizer.execute_query(
                """
                INSERT OR IGNORE INTO users (id, email, password_hash, name, is_active)
                VALUES (?, ?, 'x', ?, 1)
                """,
                (uid, email, name),
                fetch=False,
            )


def prepare_admin_test_db(
    monkeypatch,
    user_ids: Iterable[int] = (1, 9, 42, 55, 77, 99),
    *,
    usable: bool = True,
) -> None:
    """Common fixture setup for admin API tests under pytest-xdist."""

    stub_operator_account_usable(monkeypatch, usable=usable)
    ensure_operator_user_rows(user_ids)
