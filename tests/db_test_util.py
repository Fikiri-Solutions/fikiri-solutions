"""Shared helpers for dual-engine (SQLite + PostgreSQL) regression tests."""

from __future__ import annotations

import os
from typing import Optional

from core.postgres_compat import is_postgresql_dsn

# Point at a disposable Postgres DB (local Docker / CI service), never production Supabase.
POSTGRES_TEST_ENV_KEYS = (
    "FIKIRI_TEST_POSTGRES_URL",
    "TEST_DATABASE_URL",
    "DATABASE_URL",
)


def postgres_dsn_for_tests() -> Optional[str]:
    """Return a Postgres DSN when explicitly configured for integration tests."""
    for key in POSTGRES_TEST_ENV_KEYS:
        dsn = (os.getenv(key) or "").strip()
        if dsn and is_postgresql_dsn(dsn):
            if key == "DATABASE_URL" and os.getenv("FIKIRI_TEST_POSTGRES_URL"):
                continue
            if key == "DATABASE_URL" and os.getenv("FLASK_ENV", "").lower() == "production":
                continue
            return dsn
    return None


def skip_unless_postgres(reason: str = "Postgres test DSN not configured"):
    import unittest

    return unittest.skipUnless(postgres_dsn_for_tests(), reason)
