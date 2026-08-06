"""PostgreSQL concurrent claim validation for automation_event_receipts.

SQLite tests prove ownership logic but do NOT prove production concurrency.
This module requires a real Postgres URL:

  FIKIRI_PG_CONCURRENCY_TEST_URL=postgresql://user:pass@host:5432/dbname

It is skipped when that env var is unset.
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

REQUIRED_URL_ENV = "FIKIRI_PG_CONCURRENCY_TEST_URL"


def _pg_url() -> str:
    return (os.environ.get(REQUIRED_URL_ENV) or "").strip()


pytestmark = pytest.mark.skipif(
    not _pg_url(),
    reason=f"Set {REQUIRED_URL_ENV} to run genuine PostgreSQL concurrency validation",
)


def _connect():
    import psycopg2

    return psycopg2.connect(_pg_url())


def _apply_schema(conn) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS automation_event_receipts (
        id BIGSERIAL PRIMARY KEY,
        source TEXT NOT NULL,
        event_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_version INTEGER NOT NULL,
        tenant_id TEXT,
        correlation_id TEXT NOT NULL,
        api_key_id INTEGER,
        actor_user_id INTEGER,
        request_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        result_code TEXT,
        error_code TEXT,
        received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        UNIQUE (source, event_id)
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _claim(source: str, event_id: str, request_hash: str, worker_id: int) -> str:
    """Return 'owned' or 'conflict' for one concurrent INSERT attempt."""
    import psycopg2

    conn = _connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO automation_event_receipts (
                        source, event_id, event_type, event_version, tenant_id,
                        correlation_id, api_key_id, actor_user_id, request_hash, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        source,
                        event_id,
                        "automation.test.received",
                        1,
                        None,
                        f"corr_pg_{worker_id}_{uuid.uuid4().hex[:8]}",
                        worker_id,
                        1,
                        request_hash,
                        "processing",
                    ),
                )
                conn.commit()
                return "owned"
            except psycopg2.Error as exc:
                conn.rollback()
                # UniqueViolation
                if getattr(exc, "pgcode", None) == "23505" or "unique" in str(exc).lower():
                    return "conflict"
                raise
    finally:
        conn.close()


def test_postgres_concurrent_claim_single_owner():
    """Two genuine concurrent inserts: exactly one owns processing."""
    conn = _connect()
    try:
        _apply_schema(conn)
    finally:
        conn.close()

    source = "windmill-dev"
    event_id = f"evt_pg_race_{uuid.uuid4().hex}"
    request_hash = "a" * 64
    barrier = threading.Barrier(2)
    results: list[str] = []

    def worker(worker_id: int) -> str:
        barrier.wait(timeout=10)
        return _claim(source, event_id, request_hash, worker_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, i) for i in (1, 2)]
        for fut in as_completed(futures):
            results.append(fut.result())

    assert results.count("owned") == 1, results
    assert results.count("conflict") == 1, results

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), MIN(status), MAX(status) FROM automation_event_receipts WHERE source=%s AND event_id=%s",
                (source, event_id),
            )
            count, min_status, max_status = cur.fetchone()
        assert count == 1
        assert min_status == max_status == "processing"
    finally:
        conn.close()
