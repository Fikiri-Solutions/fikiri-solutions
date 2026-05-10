#!/usr/bin/env python3
"""
Prestart initialization for Fikiri Solutions.

This script is a manual convenience for triggering database schema bootstrap
before starting Gunicorn workers. In normal production use (Render via
``gunicorn wsgi:wsgi_app``) this is **not** required: importing
``core.database_optimization.db_optimizer`` runs the same bootstrap path
synchronously during process startup, before the worker accepts requests.

Run it explicitly when:

  * Booting a fresh database (dev, staging, or DR) and you want to fail
    fast on schema problems before serving traffic.
  * An external orchestrator (e.g., Kubernetes init container) needs a
    discrete "schema is ready" signal — a ``data/.db_init_lock`` file is
    written on success.

Behavior:
  * Imports ``db_optimizer``, which auto-runs ``_initialize_database()``.
    That path is Postgres-aware: SQLite DDL in CREATE TABLE statements is
    translated for psycopg2, and ``?`` placeholders are adapted to ``%s``.
    See ``core/postgres_compat.py``.
  * Writes ``data/.db_init_lock`` so subsequent invocations are no-ops.
  * Exits 0 on success, 1 if ``db_optimizer`` reports it isn't ready.

This script intentionally contains no SQL, no ``sqlite3`` import, and no
SQLite-only DDL. Those used to live here and silently created a local
SQLite file that the production Postgres app never read — see
docs/POSTGRES_MIGRATION_AUDIT.md (commit replacing this file).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _lock_path(data_dir: Path) -> Path:
    return data_dir / ".db_init_lock"


def _already_initialized(data_dir: Path) -> bool:
    lock = _lock_path(data_dir)
    if lock.exists():
        print(f"✅ Lock file already present at {lock} — skipping bootstrap.")
        return True
    return False


def _write_lock(data_dir: Path, db_type: str) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    _lock_path(data_dir).write_text(
        f"initialized_at={time.time()}\ndb_type={db_type}\n"
    )


def initialize_database() -> bool:
    """Trigger schema bootstrap via db_optimizer and stamp a lock file."""
    data_dir = PROJECT_ROOT / "data"

    if _already_initialized(data_dir):
        return True

    print("🚀 Initializing database schema via db_optimizer...")

    # Importing db_optimizer triggers _initialize_database() synchronously.
    # On Postgres the PostgresBootstrapCursor translates SQLite-style DDL.
    from core.database_optimization import db_optimizer

    if not getattr(db_optimizer, "_ready", False):
        print("❌ db_optimizer reports not ready after initialization.")
        return False

    _write_lock(data_dir, db_type=db_optimizer.db_type)
    print(f"✅ Database schema initialized ({db_optimizer.db_type}).")
    return True


def main() -> None:
    print("🔧 Fikiri Solutions Prestart Initialization")

    if initialize_database():
        print("✅ Prestart initialization completed successfully")
        sys.exit(0)
    print("❌ Prestart initialization failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
