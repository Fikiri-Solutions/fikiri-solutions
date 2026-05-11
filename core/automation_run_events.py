"""
Append-only automation run audit events. Best-effort inserts; failures never break execution.

Uses contextvars for run_id, job_id, correlation_id, attempt, source — set by the job queue
or by engine entrypoints when no queue job exists.

event_type: prefix automation. (e.g. automation.step_started, automation.completed). status: ok |
failed | skipped | cancelled | running as appropriate; use error_message when failed.
"""

from __future__ import annotations

import contextvars
import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_MAX_PAYLOAD_BYTES = 16 * 1024

_ctx_run_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("automation_run_id", default=None)
_ctx_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("automation_job_id", default=None)
_ctx_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "automation_correlation_id", default=None
)
_ctx_attempt: contextvars.ContextVar[int] = contextvars.ContextVar("automation_attempt", default=1)
_ctx_source: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("automation_source", default=None)

_table_ensured = False


def ensure_automation_run_events_table() -> None:
    """Create automation_run_events and indexes if missing (SQLite-safe)."""
    global _table_ensured
    if _table_ensured:
        return
    try:
        db_optimizer.execute_query(
            """
            CREATE TABLE IF NOT EXISTS automation_run_events (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                job_id TEXT,
                correlation_id TEXT,
                event_type TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                supersedes_event_id INTEGER,
                status TEXT,
                error_message TEXT,
                source TEXT,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """,
            fetch=False,
        )
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_automation_run_events_user_run ON automation_run_events (user_id, run_id, id)",
            "CREATE INDEX IF NOT EXISTS idx_automation_run_events_user_created ON automation_run_events (user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_automation_run_events_job ON automation_run_events (job_id)",
        ):
            db_optimizer.execute_query(stmt, fetch=False)
        _table_ensured = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("automation_run_events table init failed: %s", exc)


def get_automation_run_id() -> Optional[str]:
    return _ctx_run_id.get()


@contextmanager
def automation_run_context(
    *,
    run_id: str,
    job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    attempt: int = 1,
    source: Optional[str] = None,
) -> Iterator[None]:
    t_run = _ctx_run_id.set(run_id)
    t_job = _ctx_job_id.set(job_id)
    t_corr = _ctx_correlation_id.set(correlation_id)
    t_attempt = _ctx_attempt.set(attempt)
    t_src = _ctx_source.set(source)
    try:
        yield
    finally:
        _ctx_run_id.reset(t_run)
        _ctx_job_id.reset(t_job)
        _ctx_correlation_id.reset(t_corr)
        _ctx_attempt.reset(t_attempt)
        _ctx_source.reset(t_src)


def new_run_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def enter_automation_run_if_missing(
    trigger_data: Optional[Dict[str, Any]],
    source: str,
) -> Iterator[bool]:
    """
    If no run context is active, start one (new run_id, correlation_id from trigger_data).
    Yields True if this frame created the context, False if a parent already set run_id.
    """
    if get_automation_run_id() is not None:
        yield False
        return
    td = trigger_data or {}
    raw_corr = td.get("correlation_id")
    corr = str(raw_corr) if raw_corr is not None else None
    with automation_run_context(run_id=new_run_id(), correlation_id=corr, attempt=1, source=source):
        yield True


def _context_payload() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    rid = _ctx_run_id.get()
    if rid:
        out["run_id"] = rid
    jid = _ctx_job_id.get()
    if jid:
        out["job_id"] = jid
    corr = _ctx_correlation_id.get()
    if corr:
        out["correlation_id"] = corr
    out["attempt"] = _ctx_attempt.get()
    src = _ctx_source.get()
    if src:
        out["source"] = src
    return out


def record_automation_run_event(
    user_id: int,
    event_type: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    source: Optional[str] = None,
    correlation_id: Optional[str] = None,
    supersedes_event_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert one audit row. No-op if run_id is unset (caller outside any run context)."""
    run_id = _ctx_run_id.get()
    if not run_id:
        return

    ensure_automation_run_events_table()

    merged = {**_context_payload(), **(payload or {})}
    if correlation_id:
        merged["correlation_id"] = correlation_id

    truncated = 0
    payload_json: Optional[str] = None
    if merged:
        raw = json.dumps(merged, default=str, separators=(",", ":"))
        enc = raw.encode("utf-8")
        if len(enc) > _MAX_PAYLOAD_BYTES:
            enc = enc[:_MAX_PAYLOAD_BYTES]
            truncated = 1
            payload_json = enc.decode("utf-8", errors="ignore")
        else:
            payload_json = raw

    created_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    job_id = _ctx_job_id.get()
    eff_source = source if source is not None else _ctx_source.get()
    eff_corr = correlation_id if correlation_id else _ctx_correlation_id.get()

    try:
        db_optimizer.execute_query(
            """
            INSERT INTO automation_run_events (
                created_at, user_id, run_id, job_id, correlation_id,
                event_type, entity_type, entity_id, supersedes_event_id,
                status, error_message, source, payload_json, payload_truncated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                user_id,
                run_id,
                job_id,
                eff_corr,
                event_type,
                entity_type,
                entity_id,
                supersedes_event_id,
                status,
                error_message,
                eff_source,
                payload_json,
                truncated,
            ),
            fetch=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "automation_run_events insert failed (non-fatal): %s",
            exc,
            extra={"event": "automation_run_event_insert_failed", "event_type": event_type, "user_id": user_id},
        )


def record_automation_cancelled(
    user_id: int,
    *,
    run_id: str,
    job_id: Optional[str] = None,
    reason: str,
    lead_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Emit cancellation without requiring an active context (cancel may happen from another request)."""
    ensure_automation_run_events_table()
    payload: Dict[str, Any] = {"reason": reason, "run_id": run_id}
    if job_id:
        payload["job_id"] = job_id
    if lead_id is not None:
        payload["lead_id"] = lead_id
    if correlation_id:
        payload["correlation_id"] = correlation_id

    truncated = 0
    raw = json.dumps(payload, default=str, separators=(",", ":"))
    enc = raw.encode("utf-8")
    if len(enc) > _MAX_PAYLOAD_BYTES:
        enc = enc[:_MAX_PAYLOAD_BYTES]
        truncated = 1
        payload_json = enc.decode("utf-8", errors="ignore")
    else:
        payload_json = raw

    created_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO automation_run_events (
                created_at, user_id, run_id, job_id, correlation_id,
                event_type, entity_type, entity_id, supersedes_event_id,
                status, error_message, source, payload_json, payload_truncated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                user_id,
                run_id,
                job_id,
                correlation_id,
                "automation.cancelled",
                "lead" if lead_id is not None else None,
                str(lead_id) if lead_id is not None else None,
                None,
                "cancelled",
                reason,
                "workflow_cancel",
                payload_json,
                truncated,
            ),
            fetch=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("automation_run_events cancel insert failed (non-fatal): %s", exc)


def _rule_step_payload(rule: Any, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "rule_id": rule.id,
        "rule_name": getattr(rule, "name", None),
        "action_type": rule.action_type.value if hasattr(rule.action_type, "value") else str(rule.action_type),
        "step_key": f"rule:{rule.id}",
    }
    if trigger_data:
        lead_id = trigger_data.get("lead_id")
        if lead_id is not None:
            base["lead_id"] = lead_id
    return base


def record_automation_skipped_rule(user_id: int, rule: Any, trigger_data: Dict[str, Any], reason: str) -> None:
    if not get_automation_run_id():
        return
    p = _rule_step_payload(rule, trigger_data)
    p["skip_reason"] = reason
    record_automation_run_event(
        user_id,
        "automation.skipped",
        entity_type="automation_rule",
        entity_id=str(rule.id),
        status="skipped",
        payload=p,
    )


def record_automation_step_started(user_id: int, rule: Any, trigger_data: Dict[str, Any]) -> None:
    if not get_automation_run_id():
        return
    record_automation_run_event(
        user_id,
        "automation.step_started",
        entity_type="automation_rule",
        entity_id=str(rule.id),
        status="running",
        payload=_rule_step_payload(rule, trigger_data),
    )


def record_automation_step_finished(
    user_id: int, rule: Any, trigger_data: Dict[str, Any], result: Dict[str, Any]
) -> None:
    if not get_automation_run_id():
        return
    p = _rule_step_payload(rule, trigger_data)
    if result.get("success"):
        p["outcome"] = "ok"
        record_automation_run_event(
            user_id,
            "automation.step_executed",
            entity_type="automation_rule",
            entity_id=str(rule.id),
            status="ok",
            payload=p,
        )
    else:
        p["error_code"] = result.get("error_code")
        record_automation_run_event(
            user_id,
            "automation.step_failed",
            entity_type="automation_rule",
            entity_id=str(rule.id),
            status="failed",
            error_message=(result.get("error") or "")[:2000] or None,
            payload=p,
        )


__all__ = [
    "automation_run_context",
    "enter_automation_run_if_missing",
    "ensure_automation_run_events_table",
    "get_automation_run_id",
    "new_run_id",
    "record_automation_cancelled",
    "record_automation_run_event",
    "record_automation_skipped_rule",
    "record_automation_step_finished",
    "record_automation_step_started",
]
