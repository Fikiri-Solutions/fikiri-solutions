"""
Lightweight durable background job tracking (SQLite + Postgres).

Complements domain tables (gmail_sync_jobs, automation_jobs) with unified
idempotency, retry_count, correlation_id, last_error, and dead-letter flags.
No Celery/Kubernetes — callers keep existing enqueue paths.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Job kinds (extend for new background work).
JOB_KIND_GMAIL_SYNC = "gmail_sync"
JOB_KIND_KB_VECTORIZE = "kb_vectorize"
JOB_KIND_KB_CHUNK_CLEANUP = "kb_chunk_cleanup"
JOB_KIND_ANALYTICS_ROLLUP = "analytics_rollup"
JOB_KIND_CHATBOT_EVAL = "chatbot_eval"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_RETRYING = "retrying"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_DEAD = "dead"

ACTIVE_STATUSES = frozenset({STATUS_PENDING, STATUS_RUNNING, STATUS_RETRYING})
TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_FAILED, STATUS_DEAD})

DEFAULT_MAX_RETRIES = 3
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def ensure_background_jobs_table() -> None:
    """Create background_jobs and indexes (idempotent)."""
    try:
        db_optimizer.execute_query(
            """
            CREATE TABLE IF NOT EXISTS background_jobs (
                id BIGSERIAL PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE,
                job_kind TEXT NOT NULL,
                user_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                idempotency_key TEXT UNIQUE,
                correlation_id TEXT,
                payload_json TEXT,
                result_json TEXT,
                last_error TEXT,
                dead_letter INTEGER NOT NULL DEFAULT 0,
                external_ref TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            """,
            fetch=False,
        )
        for idx_sql in (
            "CREATE INDEX IF NOT EXISTS idx_background_jobs_kind_status ON background_jobs (job_kind, status)",
            "CREATE INDEX IF NOT EXISTS idx_background_jobs_user_kind ON background_jobs (user_id, job_kind)",
            "CREATE INDEX IF NOT EXISTS idx_background_jobs_external_ref ON background_jobs (external_ref)",
            "CREATE INDEX IF NOT EXISTS idx_background_jobs_correlation ON background_jobs (correlation_id)",
        ):
            db_optimizer.execute_query(idx_sql, fetch=False)
    except Exception as exc:
        logger.warning("background_jobs table ensure failed: %s", exc)


def build_idempotency_key(*parts: Any) -> str:
    raw = ":".join(str(p) for p in parts if p is not None and str(p) != "")
    if len(raw) <= 220:
        return raw
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_job_id(kind: str) -> str:
    return f"{kind}_{uuid.uuid4().hex[:20]}"


def resolve_correlation_id(explicit: Optional[str] = None) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        from core.trace_context import get_trace_id

        tid = get_trace_id()
        if tid:
            return str(tid)
    except ImportError:
        pass
    return str(uuid.uuid4())


def _log_job_event(
    event: str,
    *,
    job_id: str,
    job_kind: str,
    status: str,
    user_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    retry_count: int = 0,
    last_error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "event": event,
        "service": "background_jobs",
        "severity": "INFO",
        "job_id": job_id,
        "job_kind": job_kind,
        "job_status": status,
        "user_id": user_id,
        "correlation_id": correlation_id,
        "retry_count": retry_count,
    }
    if last_error:
        payload["last_error"] = (last_error or "")[:500]
        payload["severity"] = "WARN"
    if extra:
        payload.update(extra)
    logger.info("background_job %s kind=%s status=%s", event, job_kind, status, extra=payload)


def find_active_job_by_idempotency(
    idempotency_key: str,
    *,
    job_kind: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not idempotency_key or not db_optimizer.table_exists("background_jobs"):
        return None
    ensure_background_jobs_table()
    ttl_pred = db_optimizer.sql_column_newer_than_n_seconds_ago("created_at", IDEMPOTENCY_TTL_SECONDS)
    clauses = ["idempotency_key = ?", f"status IN ('pending', 'running', 'retrying')", ttl_pred]
    params: List[Any] = [idempotency_key]
    if job_kind:
        clauses.append("job_kind = ?")
        params.append(job_kind)
    rows = db_optimizer.execute_query(
        f"""
        SELECT job_id, job_kind, status, external_ref, correlation_id, retry_count
        FROM background_jobs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        LIMIT 1
        """,
        tuple(params),
    )
    return dict(rows[0]) if rows else None


def enqueue_durable_job(
    job_kind: str,
    *,
    user_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    external_ref: Optional[str] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    job_id: Optional[str] = None,
) -> Optional[str]:
    """
    Insert a pending durable job row. Returns job_id, or None if idempotency blocked duplicate.
    """
    if _is_test_mode() and os.getenv("FIKIRI_DURABLE_JOBS_PERSIST_IN_TEST", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return job_id or new_job_id(job_kind)

    ensure_background_jobs_table()
    if idempotency_key:
        existing = find_active_job_by_idempotency(idempotency_key, job_kind=job_kind)
        if existing:
            _log_job_event(
                "job.duplicate_skipped",
                job_id=existing["job_id"],
                job_kind=job_kind,
                status=existing.get("status") or STATUS_PENDING,
                user_id=user_id,
                correlation_id=existing.get("correlation_id"),
            )
            return None

    jid = job_id or new_job_id(job_kind)
    cid = resolve_correlation_id(correlation_id)
    now = _utcnow_iso()
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO background_jobs (
                job_id, job_kind, user_id, status, retry_count, max_retries,
                idempotency_key, correlation_id, payload_json, external_ref,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                jid,
                job_kind,
                user_id,
                STATUS_PENDING,
                max_retries,
                idempotency_key,
                cid,
                json.dumps(payload or {}, default=str),
                external_ref,
                now,
                now,
            ),
            fetch=False,
        )
        _log_job_event(
            "job.enqueued",
            job_id=jid,
            job_kind=job_kind,
            status=STATUS_PENDING,
            user_id=user_id,
            correlation_id=cid,
            extra={"external_ref": external_ref},
        )
        return jid
    except Exception as exc:
        if idempotency_key and "unique" in str(exc).lower():
            return None
        logger.warning("enqueue_durable_job failed: %s", exc)
        return None


def get_durable_job(job_id: str) -> Optional[Dict[str, Any]]:
    if not db_optimizer.table_exists("background_jobs"):
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT job_id, job_kind, user_id, status, retry_count, max_retries,
               idempotency_key, correlation_id, payload_json, result_json,
               last_error, dead_letter, external_ref,
               created_at, started_at, completed_at, updated_at
        FROM background_jobs WHERE job_id = ?
        """,
        (job_id,),
    )
    if not rows:
        return None
    row = dict(rows[0])
    if row.get("payload_json"):
        try:
            row["payload"] = json.loads(row["payload_json"])
        except (TypeError, ValueError):
            row["payload"] = {}
    else:
        row["payload"] = {}
    return row


def mark_job_running(job_id: str) -> None:
    now = _utcnow_iso()
    db_optimizer.execute_query(
        """
        UPDATE background_jobs
        SET status = ?, started_at = COALESCE(started_at, ?), updated_at = ?
        WHERE job_id = ?
        """,
        (STATUS_RUNNING, now, now, job_id),
        fetch=False,
    )
    job = get_durable_job(job_id)
    if job:
        _log_job_event(
            "job.started",
            job_id=job_id,
            job_kind=job["job_kind"],
            status=STATUS_RUNNING,
            user_id=job.get("user_id"),
            correlation_id=job.get("correlation_id"),
            retry_count=int(job.get("retry_count") or 0),
        )


def mark_job_completed(
    job_id: str,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    now = _utcnow_iso()
    db_optimizer.execute_query(
        """
        UPDATE background_jobs
        SET status = ?, completed_at = ?, result_json = ?, last_error = NULL, updated_at = ?
        WHERE job_id = ?
        """,
        (
            STATUS_COMPLETED,
            now,
            json.dumps(result or {}, default=str),
            now,
            job_id,
        ),
        fetch=False,
    )
    job = get_durable_job(job_id)
    if job:
        _log_job_event(
            "job.completed",
            job_id=job_id,
            job_kind=job["job_kind"],
            status=STATUS_COMPLETED,
            user_id=job.get("user_id"),
            correlation_id=job.get("correlation_id"),
            retry_count=int(job.get("retry_count") or 0),
        )


def mark_job_failed(
    job_id: str,
    error: str,
    *,
    allow_retry: bool = True,
) -> Dict[str, Any]:
    """
    Record failure; increment retry_count. Returns {will_retry, status, retry_count}.
    Sets dead_letter when retries exhausted.
    """
    job = get_durable_job(job_id)
    if not job:
        return {"will_retry": False, "status": STATUS_FAILED, "retry_count": 0}

    retry_count = int(job.get("retry_count") or 0) + 1
    max_retries = int(job.get("max_retries") or DEFAULT_MAX_RETRIES)
    err_text = (error or "unknown error")[:2000]
    now = _utcnow_iso()

    will_retry = allow_retry and retry_count < max_retries
    if will_retry:
        new_status = STATUS_RETRYING
        dead_letter = 0
    else:
        new_status = STATUS_DEAD if retry_count >= max_retries else STATUS_FAILED
        dead_letter = 1 if retry_count >= max_retries else 0

    if will_retry:
        db_optimizer.execute_query(
            """
            UPDATE background_jobs
            SET status = ?, retry_count = ?, last_error = ?, dead_letter = 0, updated_at = ?
            WHERE job_id = ?
            """,
            (new_status, retry_count, err_text, now, job_id),
            fetch=False,
        )
    else:
        db_optimizer.execute_query(
            """
            UPDATE background_jobs
            SET status = ?, retry_count = ?, last_error = ?, dead_letter = ?,
                completed_at = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (new_status, retry_count, err_text, dead_letter, now, now, job_id),
            fetch=False,
        )
    _log_job_event(
        "job.failed" if not will_retry else "job.retry_scheduled",
        job_id=job_id,
        job_kind=job["job_kind"],
        status=new_status,
        user_id=job.get("user_id"),
        correlation_id=job.get("correlation_id"),
        retry_count=retry_count,
        last_error=err_text,
        extra={"will_retry": will_retry, "dead_letter": bool(dead_letter)},
    )
    return {
        "will_retry": will_retry,
        "status": new_status,
        "retry_count": retry_count,
        "dead_letter": bool(dead_letter),
    }


def link_external_ref(job_id: str, external_ref: str) -> None:
    db_optimizer.execute_query(
        "UPDATE background_jobs SET external_ref = ?, updated_at = ? WHERE job_id = ?",
        (external_ref, _utcnow_iso(), job_id),
        fetch=False,
    )


def find_durable_job_by_external_ref(
    external_ref: str,
    *,
    job_kind: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not external_ref or not db_optimizer.table_exists("background_jobs"):
        return None
    clauses = ["external_ref = ?"]
    params: List[Any] = [external_ref]
    if job_kind:
        clauses.append("job_kind = ?")
        params.append(job_kind)
    rows = db_optimizer.execute_query(
        f"""
        SELECT job_id FROM background_jobs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC LIMIT 1
        """,
        tuple(params),
    )
    if not rows:
        return None
    return get_durable_job(rows[0]["job_id"])


def run_durable_job(
    job_id: str,
    worker: Callable[[Dict[str, Any]], Dict[str, Any]],
    *,
    requeue_fn: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Execute worker with durable lifecycle: running -> completed | retry | dead.

    worker receives job dict (includes payload). Must return dict with optional 'success' key.
    """
    job = get_durable_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found", "error_code": "JOB_NOT_FOUND"}

    if job.get("status") in TERMINAL_STATUSES:
        return {
            "success": job.get("status") == STATUS_COMPLETED,
            "status": job.get("status"),
            "skipped": True,
        }

    mark_job_running(job_id)
    try:
        result = worker(job) or {}
        if result.get("success") is False:
            fail_info = mark_job_failed(
                job_id,
                str(result.get("error") or "worker returned failure"),
                allow_retry=result.get("allow_retry", True),
            )
            if fail_info.get("will_retry") and requeue_fn:
                try:
                    requeue_fn(job_id, job)
                except Exception as req_exc:
                    logger.warning("durable job requeue failed: %s", req_exc)
            return {**result, **fail_info}
        mark_job_completed(job_id, result)
        return {"success": True, "status": STATUS_COMPLETED, **result}
    except Exception as exc:
        fail_info = mark_job_failed(job_id, str(exc), allow_retry=True)
        if fail_info.get("will_retry") and requeue_fn:
            try:
                requeue_fn(job_id, job)
            except Exception as req_exc:
                logger.warning("durable job requeue failed: %s", req_exc)
        return {"success": False, "error": str(exc), **fail_info}


def ensure_gmail_sync_job_durable_columns() -> None:
    """Optional linkage columns on legacy gmail_sync_jobs (additive, best-effort)."""
    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return
    for col, ddl in (
        ("retry_count", "INTEGER NOT NULL DEFAULT 0"),
        ("correlation_id", "TEXT"),
    ):
        try:
            cols = set(db_optimizer.list_table_columns("gmail_sync_jobs") or [])
            if col not in cols:
                db_optimizer.execute_query(
                    f"ALTER TABLE gmail_sync_jobs ADD COLUMN {col} {ddl}",
                    fetch=False,
                )
        except Exception as exc:
            logger.debug("gmail_sync_jobs column %s migration skipped: %s", col, exc)


def reconcile_stale_background_jobs(stale_minutes: Optional[int] = None) -> int:
    """Mark long-running jobs dead (startup / heartbeat helper)."""
    ensure_background_jobs_table()
    try:
        minutes = stale_minutes or int(os.getenv("BACKGROUND_JOB_STALE_MINUTES", "45"))
    except ValueError:
        minutes = 45
    co_expr = "COALESCE(started_at, created_at)"
    stale_pred = db_optimizer.sql_column_older_than_n_minutes_ago(co_expr, minutes)
    try:
        db_optimizer.execute_query(
            f"""
            UPDATE background_jobs
            SET status = ?, dead_letter = 1, completed_at = ?, last_error = COALESCE(
                last_error, 'Marked dead: stale running job'
            ), updated_at = ?
            WHERE status IN (?, ?) AND {stale_pred}
            """,
            (
                STATUS_DEAD,
                _utcnow_iso(),
                _utcnow_iso(),
                STATUS_RUNNING,
                STATUS_RETRYING,
            ),
            fetch=False,
        )
        return 1
    except Exception as exc:
        logger.warning("stale background job reconciliation failed: %s", exc)
        return 0
