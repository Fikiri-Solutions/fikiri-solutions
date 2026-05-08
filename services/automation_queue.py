"""
Automation Job Queue – reliable execution with Redis queue, job states, retries, idempotency.
When Redis is available, execution is queued and processed by workers; otherwise runs synchronously.
"""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from core.database_optimization import db_optimizer
from core.automation_run_events import (
    automation_run_context,
    ensure_automation_run_events_table,
    record_automation_run_event,
)

logger = logging.getLogger(__name__)

# Avoid circular import: engine is used only inside process function
def _get_engine():
    from services.automation_engine import automation_engine
    return automation_engine


def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


# Job states for persistence and observability
AUTOMATION_JOB_QUEUED = "queued"
AUTOMATION_JOB_RUNNING = "running"
AUTOMATION_JOB_SUCCESS = "success"
AUTOMATION_JOB_FAILED = "failed"
AUTOMATION_JOB_RETRYING = "retrying"
AUTOMATION_JOB_DEAD = "dead"

MAX_ATTEMPTS_DEFAULT = 3
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _generate_idempotency_key(user_id: int, payload_type: str, payload: Dict[str, Any]) -> str:
    """Generate idempotency key for trigger event to prevent duplicate runs."""
    canonical = json.dumps({"user_id": user_id, "type": payload_type, "payload": payload}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class AutomationJobManager:
    """Queue and process automation runs with DB persistence and optional Redis."""

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        try:
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS automation_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    payload_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    result_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            db_optimizer.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_automation_jobs_job_id ON automation_jobs (job_id)",
                fetch=False,
            )
            db_optimizer.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_automation_jobs_idempotency ON automation_jobs (idempotency_key)",
                fetch=False,
            )
            db_optimizer.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_automation_jobs_user_status ON automation_jobs (user_id, status)",
                fetch=False,
            )
            ensure_automation_run_events_table()
            self._reconcile_stale_jobs()
        except Exception as e:
            logger.error("Automation jobs table init failed: %s", e)

    def _reconcile_stale_jobs(self):
        """Mark stale running/retrying jobs dead on startup to avoid stuck-state conflicts."""
        try:
            stale_minutes = int(os.getenv("AUTOMATION_JOB_STALE_MINUTES", "30"))
        except ValueError:
            stale_minutes = 30

        co_expr = "COALESCE(started_at, created_at)"
        stale_pred = db_optimizer.sql_column_older_than_n_minutes_ago(co_expr, stale_minutes)
        try:
            db_optimizer.execute_query(
                f"""
                UPDATE automation_jobs
                SET status = ?, completed_at = ?, error_message = COALESCE(
                    error_message,
                    'Marked dead during startup reconciliation (stale running/retrying job)'
                )
                WHERE status IN (?, ?)
                  AND {stale_pred}
                """,
                (
                    AUTOMATION_JOB_DEAD,
                    _utcnow_iso(),
                    AUTOMATION_JOB_RUNNING,
                    AUTOMATION_JOB_RETRYING,
                ),
                fetch=False,
            )
        except Exception as e:
            logger.warning("Automation stale job reconciliation failed: %s", e)

    def queue_automation_job(
        self,
        user_id: int,
        rule_ids: Optional[List[int]] = None,
        trigger_type: Optional[str] = None,
        trigger_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        max_attempts: int = MAX_ATTEMPTS_DEFAULT,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a job record and return job_id. Caller should then enqueue to Redis if connected.
        If idempotency_key is provided and a recent job with that key is queued, running, or success, returns None (duplicate).

        correlation_id is stored on the job payload so automation_run_events and workers share the same trace as CRM/email/AI.
        """
        if rule_ids is not None:
            payload_type = "rule_ids"
            payload: Dict[str, Any] = {"rule_ids": rule_ids}
        elif trigger_type is not None:
            payload_type = "trigger"
            payload = {"trigger_type": trigger_type, "trigger_data": trigger_data or {}}
        else:
            logger.error("queue_automation_job: need rule_ids or trigger_type")
            return None

        if correlation_id and str(correlation_id).strip():
            cid = str(correlation_id).strip()
            payload["correlation_id"] = cid
            if payload_type == "trigger":
                td = payload.get("trigger_data")
                if not isinstance(td, dict):
                    td = {}
                if td.get("correlation_id") is None:
                    td = {**td, "correlation_id": cid}
                    payload["trigger_data"] = td

        if idempotency_key:
            idem_pred = db_optimizer.sql_column_newer_than_n_seconds_ago("created_at", IDEMPOTENCY_TTL_SECONDS)
            existing = db_optimizer.execute_query(
                f"""SELECT job_id, status FROM automation_jobs
                   WHERE idempotency_key = ? AND status IN (?, ?, ?) AND {idem_pred}
                   ORDER BY created_at DESC LIMIT 1""",
                (idempotency_key, AUTOMATION_JOB_QUEUED, AUTOMATION_JOB_RUNNING, AUTOMATION_JOB_SUCCESS),
            )
            if existing:
                logger.info("Idempotency: skipping duplicate run for key %s (existing status: %s)", idempotency_key[:16], existing[0].get("status"))
                return None

        job_id = f"automation_{uuid.uuid4().hex[:16]}"
        now = _utcnow_iso()
        try:
            db_optimizer.execute_query(
                """INSERT INTO automation_jobs
                   (job_id, user_id, payload_type, payload_json, idempotency_key, status, attempt, max_attempts, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (
                    job_id,
                    user_id,
                    payload_type,
                    json.dumps(payload, default=str),
                    idempotency_key,
                    AUTOMATION_JOB_QUEUED,
                    max_attempts,
                    now,
                ),
                fetch=False,
            )
            return job_id
        except Exception as e:
            logger.error("Failed to create automation job: %s", e)
            return None

    def process_automation_job(self, job_id: str) -> Dict[str, Any]:
        """
        Load job, run automation engine, update state. Used by Redis worker or sync fallback.
        Returns result dict with success, status, execution_results or error.
        """
        engine = _get_engine()
        row = db_optimizer.execute_query(
            """SELECT job_id, user_id, payload_type, payload_json, attempt, max_attempts, status
               FROM automation_jobs WHERE job_id = ?""",
            (job_id,),
        )
        if not row:
            return {"success": False, "error": "Job not found", "status": "failed"}

        job = row[0]
        user_id = job["user_id"]
        payload_type = job["payload_type"]
        payload = json.loads(job["payload_json"])
        attempt = job["attempt"] + 1
        max_attempts = job["max_attempts"]

        corr: Optional[str] = None
        td = payload.get("trigger_data")
        if isinstance(td, dict) and td.get("correlation_id") is not None:
            corr = str(td["correlation_id"])
        if corr is None and payload.get("correlation_id") is not None:
            corr = str(payload["correlation_id"])

        def _audit_completed(status: str, **extra: Any) -> None:
            record_automation_run_event(
                user_id,
                "automation.completed",
                status=status,
                payload={"payload_type": payload_type, "job_id": job_id, "attempt": attempt, **extra},
            )

        with automation_run_context(
            run_id=job_id,
            job_id=job_id,
            correlation_id=corr,
            attempt=attempt,
            source="queue_worker",
        ):
            try:
                db_optimizer.execute_query(
                    """UPDATE automation_jobs SET status = ?, started_at = ?, attempt = ?
                       WHERE job_id = ?""",
                    (AUTOMATION_JOB_RUNNING, _utcnow_iso(), attempt, job_id),
                    fetch=False,
                )
            except Exception as e:
                logger.warning("Update job started_at failed: %s", e)

            triggered_payload: Dict[str, Any] = {
                "payload_type": payload_type,
                "attempt": attempt,
            }
            if payload_type == "rule_ids":
                triggered_payload["rule_ids"] = payload.get("rule_ids")
            elif payload_type == "trigger":
                triggered_payload["trigger_type"] = payload.get("trigger_type")
            record_automation_run_event(
                user_id,
                "automation.triggered",
                payload=triggered_payload,
            )

            try:
                if payload_type == "rule_ids":
                    execution_results = engine.execute_rules(user_id, payload["rule_ids"])
                    not_impl = [r for r in execution_results if r.get("error_code") == "NOT_IMPLEMENTED"]
                    if not_impl:
                        err = not_impl[0].get("error", "Action not implemented")
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=err, result={"execution_results": execution_results})
                        _audit_completed("failed", error=err, execution_results=len(execution_results))
                        return {"success": False, "error": err, "error_code": "NOT_IMPLEMENTED", "status": "failed", "execution_results": execution_results}
                    failed = [r for r in execution_results if not r.get("success")]
                    if failed:
                        err = failed[0].get("error", "One or more rules failed")
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=err, result={"execution_results": execution_results})
                        _audit_completed("partial" if any(r.get("success") for r in execution_results) else "failed", error=err)
                        return {"success": False, "error": err, "status": "failed", "execution_results": execution_results}
                    self._complete_job(job_id, AUTOMATION_JOB_SUCCESS, result={"execution_results": execution_results})
                    _audit_completed("ok", execution_results=len(execution_results))
                    return {"success": True, "status": "success", "execution_results": execution_results}

                if payload_type == "trigger":
                    from services.automation_engine import TriggerType
                    try:
                        trigger_type = TriggerType(payload["trigger_type"])
                    except ValueError:
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message="Invalid trigger_type")
                        _audit_completed("failed", error="Invalid trigger_type")
                        return {"success": False, "error": "Invalid trigger_type", "status": "failed"}
                    trigger_data = payload.get("trigger_data") or {}
                    result = engine.execute_automation_rules(
                        trigger_type, trigger_data, user_id, automation_source="queue_worker"
                    )
                    if not result.get("success"):
                        err = result.get("error", "Execution failed")
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=err, result=result)
                        _audit_completed("failed", error=err)
                        return {"success": False, "error": err, "status": "failed", "data": result.get("data")}
                    failed = result.get("data", {}).get("failed_rules", [])
                    not_impl = next((f for f in failed if f.get("error_code") == "NOT_IMPLEMENTED"), None)
                    if not_impl:
                        err = not_impl.get("error") or "Action not implemented"
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=err, result=result)
                        _audit_completed("failed", error=err)
                        return {"success": False, "error": err, "error_code": "NOT_IMPLEMENTED", "status": "failed"}
                    if failed:
                        err = failed[0].get("error") or "One or more rules failed"
                        self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=err, result=result)
                        _audit_completed("partial")
                        return {"success": False, "error": err, "status": "failed"}
                    self._complete_job(job_id, AUTOMATION_JOB_SUCCESS, result=result.get("data"))
                    _audit_completed("ok", total_executed=result.get("data", {}).get("total_executed"))
                    return {"success": True, "status": "success", "data": result.get("data")}

                self._complete_job(job_id, AUTOMATION_JOB_FAILED, error_message=f"Unknown payload_type: {payload_type}")
                _audit_completed("failed", error=f"Unknown payload_type: {payload_type}")
                return {"success": False, "error": f"Unknown payload_type: {payload_type}", "status": "failed"}

            except Exception as e:
                logger.exception("Automation job %s failed", job_id)
                if attempt >= max_attempts:
                    self._complete_job(job_id, AUTOMATION_JOB_DEAD, error_message=str(e))
                    record_automation_run_event(
                        user_id,
                        "automation.run_failed",
                        status="failed",
                        error_message=str(e)[:2000],
                        payload={"job_id": job_id, "attempt": attempt, "terminal": True},
                    )
                    return {"success": False, "error": str(e), "status": "dead"}
                record_automation_run_event(
                    user_id,
                    "automation.retried",
                    status="retrying",
                    error_message=str(e)[:2000],
                    payload={"job_id": job_id, "attempt": attempt, "max_attempts": max_attempts},
                )
                try:
                    db_optimizer.execute_query(
                        """UPDATE automation_jobs SET status = ?, error_message = ?, attempt = ?
                           WHERE job_id = ?""",
                        (AUTOMATION_JOB_RETRYING, str(e), attempt, job_id),
                        fetch=False,
                    )
                except Exception as upd_err:
                    logger.warning("Update job retrying failed: %s", upd_err)
                try:
                    from core.redis_queues import get_automation_queue
                    aq = get_automation_queue()
                    if aq.is_connected():
                        delay_sec = min(300, max(1, int(0.5 * (2 ** attempt))))
                        aq.enqueue_job("process_automation_run", {"job_id": job_id}, delay=delay_sec)
                        logger.info("Re-enqueued job %s for retry in %ss (attempt %s)", job_id, delay_sec, attempt)
                except Exception as enq_err:
                    logger.warning("Re-enqueue for retry failed: %s", enq_err)
                return {"success": False, "error": str(e), "status": "retrying", "attempt": attempt}

    def _complete_job(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = _utcnow_iso()
        try:
            db_optimizer.execute_query(
                """UPDATE automation_jobs SET status = ?, completed_at = ?, error_message = ?, result_json = ?
                   WHERE job_id = ?""",
                (
                    status,
                    now,
                    error_message,
                    json.dumps(result, default=str) if result else None,
                    job_id,
                ),
                fetch=False,
            )
        except Exception as e:
            logger.warning("Complete job update failed: %s", e)

    def get_job_status(self, job_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Return job status and result for API."""
        query = (
            "SELECT job_id, user_id, payload_type, payload_json, status, attempt, max_attempts, "
            "created_at, started_at, completed_at, error_message, result_json FROM automation_jobs WHERE job_id = ?"
        )
        params = [job_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        row = db_optimizer.execute_query(query, tuple(params))
        if not row:
            return None
        r = row[0]
        out = {
            "job_id": r["job_id"],
            "user_id": r["user_id"],
            "payload_type": r["payload_type"],
            "status": r["status"],
            "attempt": r["attempt"],
            "max_attempts": r["max_attempts"],
            "created_at": r["created_at"],
            "started_at": r["started_at"],
            "completed_at": r["completed_at"],
            "error_message": r["error_message"],
            "correlation_id": None,
        }
        pj = r.get("payload_json")
        if pj:
            try:
                payload = json.loads(pj)
                cid = payload.get("correlation_id")
                if cid is not None and str(cid).strip():
                    out["correlation_id"] = str(cid).strip()
                td = payload.get("trigger_data")
                if out["correlation_id"] is None and isinstance(td, dict) and td.get("correlation_id"):
                    out["correlation_id"] = str(td["correlation_id"]).strip()
            except Exception:
                pass
        if r.get("result_json"):
            try:
                out["result"] = json.loads(r["result_json"])
            except Exception:
                out["result"] = None
        else:
            out["result"] = None
        return out

    def get_queue_depth(self) -> Dict[str, int]:
        """Return counts for queued/running/dead for observability."""
        try:
            depth_pred = db_optimizer.sql_column_newer_than_n_hours_ago("created_at", 24 * 7)
            rows = db_optimizer.execute_query(
                f"""SELECT status, COUNT(*) as cnt FROM automation_jobs
                   WHERE {depth_pred}
                   GROUP BY status"""
            )
            by_status = {r["status"]: r["cnt"] for r in rows} if rows else {}
            return {
                "queued": by_status.get(AUTOMATION_JOB_QUEUED, 0),
                "running": by_status.get(AUTOMATION_JOB_RUNNING, 0),
                "success": by_status.get(AUTOMATION_JOB_SUCCESS, 0),
                "failed": by_status.get(AUTOMATION_JOB_FAILED, 0),
                "retrying": by_status.get(AUTOMATION_JOB_RETRYING, 0),
                "dead": by_status.get(AUTOMATION_JOB_DEAD, 0),
            }
        except Exception as e:
            logger.warning("Queue depth query failed: %s", e)
            return {}

    def get_automation_metrics(self, user_id: Optional[int] = None, hours: int = 24) -> Dict[str, Any]:
        """Return queue depth plus success rate and p95 duration for observability."""
        depth = self.get_queue_depth()
        try:
            where = db_optimizer.sql_column_newer_than_n_hours_ago("created_at", hours)
            params: List[Any] = []
            if user_id is not None:
                where += " AND user_id = ?"
                params.append(user_id)
            rows = db_optimizer.execute_query(
                f"""SELECT status, COUNT(*) as cnt FROM automation_jobs WHERE {where} GROUP BY status""",
                tuple(params),
            )
            by_status = {r["status"]: r["cnt"] for r in rows} if rows else {}
            total_success = by_status.get(AUTOMATION_JOB_SUCCESS, 0)
            total_failed = by_status.get(AUTOMATION_JOB_FAILED, 0)
            total_dead = by_status.get(AUTOMATION_JOB_DEAD, 0)
            total_finished = total_success + total_failed + total_dead
            success_rate_24h = (total_success / total_finished) if total_finished else None

            # P95 duration: completed jobs with started_at and completed_at
            duration_params: List[Any] = [AUTOMATION_JOB_SUCCESS]
            dur_where = db_optimizer.sql_column_newer_than_n_hours_ago("created_at", hours)
            if user_id is not None:
                duration_params.append(user_id)
            user_clause = " AND user_id = ?" if user_id is not None else ""
            duration_rows = db_optimizer.execute_query(
                f"""SELECT started_at, completed_at FROM automation_jobs
                    WHERE status = ? AND started_at IS NOT NULL AND completed_at IS NOT NULL
                    AND {dur_where}{user_clause}""",
                tuple(duration_params),
            )
            durations_sec = []
            for r in duration_rows or []:
                try:
                    from datetime import datetime as dt
                    start = dt.fromisoformat(r["started_at"].replace("Z", "+00:00"))
                    end = dt.fromisoformat(r["completed_at"].replace("Z", "+00:00"))
                    durations_sec.append((end - start).total_seconds())
                except Exception:
                    pass
            p95_duration_seconds = None
            if durations_sec:
                durations_sec.sort()
                idx = max(0, int(len(durations_sec) * 0.95) - 1)
                p95_duration_seconds = round(durations_sec[idx], 2)

            return {
                **depth,
                "success_rate_24h": success_rate_24h,
                "total_success_24h": total_success,
                "total_failed_24h": total_failed,
                "total_dead_24h": total_dead,
                "p95_duration_seconds": p95_duration_seconds,
                "period_hours": hours,
            }
        except Exception as e:
            logger.warning("Automation metrics query failed: %s", e)
            return {**depth, "success_rate_24h": None, "p95_duration_seconds": None, "period_hours": hours}


automation_job_manager = AutomationJobManager()


def process_automation_run(job_id: str, **kwargs) -> Dict[str, Any]:
    """Task entrypoint for Redis worker."""
    return automation_job_manager.process_automation_job(job_id)
