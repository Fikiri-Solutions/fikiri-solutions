"""Low-risk platform admin sync operations (Phase 1.6 gate hardening).

Retries a failed Gmail sync job for a specific tenant without enabling
ADMIN_DESTRUCTIVE_ENABLED / platform.ops.write.

Step-up model (intentional): sync.retry requires a valid recent step-up but does
NOT consume it. Multiple same-risk retries are allowed within the step-up TTL;
each mutation is audited separately.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ACTION_NAME = "platform.sync.retry"
RETRYABLE_STATUSES = frozenset({"failed", "retrying"})
ACTIVE_STATUSES = frozenset({"pending", "processing"})
IDEMPOTENCY_TTL_SECONDS = 600

# Controlled permanent-failure markers (matched against sanitized lowercase error text).
_PERMANENT_FAILURE_MARKERS = (
    "invalid_grant",
    "token has been expired or revoked",
    "account has been deleted",
    "mailbox not found",
    "insufficient authentication scopes",
    "permanently deleted",
)


def _row_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {}


def _safe_public_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Strip anything that must never appear in cached/idempotent responses."""
    allowed = (
        "retried",
        "original_job_id",
        "new_job_id",
        "tenant_id",
        "enqueued",
        "enqueue_mode",
        "correlation_id",
        "previous_status",
        "resulting_status",
        "idempotency_key_hash",
        "replayed",
    )
    return {k: result[k] for k in allowed if k in result}


def _parse_meta(raw: Any) -> Dict[str, Any]:
    try:
        if isinstance(raw, dict):
            return dict(raw)
        return json.loads(raw or "{}") if raw else {}
    except Exception:
        return {}


def _normalize_payload(tenant_id: int, job_id: str, confirm: str) -> Dict[str, Any]:
    return {
        "action": ACTION_NAME,
        "confirm": str(confirm or "").strip().lower(),
        "tenant_id": int(tenant_id),
        "job_id": str(job_id),
    }


def _payload_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _client_idem_store_key(store, client_key: str) -> str:
    digest = hashlib.sha256(str(client_key).strip().encode("utf-8")).hexdigest()
    return store.k("sync_retry_idem", digest)


def _idem_key_hash(client_key: str) -> str:
    return hashlib.sha256(str(client_key).strip().encode("utf-8")).hexdigest()[:32]


def list_tenant_sync_jobs(tenant_id: int, *, limit: int = 20) -> List[Dict[str, Any]]:
    from core.database_optimization import db_optimizer

    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return []
    limit = max(1, min(int(limit), 50))
    rows = db_optimizer.execute_query(
        """
        SELECT job_id, user_id, status, progress, emails_synced, error_message,
               created_at, started_at, completed_at, metadata
        FROM gmail_sync_jobs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(tenant_id), limit),
    )
    items: List[Dict[str, Any]] = []
    for row in rows or []:
        data = _row_dict(row)
        meta = _parse_meta(data.get("metadata"))
        safe_meta = {
            k: meta.get(k)
            for k in (
                "sync_type",
                "admin_retry_of",
                "admin_retry_job_id",
                "correlation_id",
                "has_more",
            )
            if k in meta
        }
        job_id = str(data.get("job_id") or "")
        eligible, _reason = evaluate_retry_eligibility(
            tenant_id=int(tenant_id),
            job_id=job_id,
            job_row=data,
            check_oauth=True,
            check_tenant_active=True,
        )
        items.append(
            {
                "job_id": job_id,
                "user_id": int(data.get("user_id") or tenant_id),
                "status": data.get("status"),
                "progress": data.get("progress"),
                "emails_synced": data.get("emails_synced"),
                "error_message": (data.get("error_message") or "")[:500] or None,
                "created_at": data.get("created_at"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "retryable": bool(eligible),
                "metadata": safe_meta,
            }
        )
    return items


def list_actionable_sync_jobs(
    *,
    statuses: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Cross-tenant inbox of failed/retrying sync jobs (read-only, bounded)."""
    from core.database_optimization import db_optimizer

    allowed = {"failed", "retrying"}
    requested = [str(s).strip().lower() for s in (statuses or ["failed", "retrying"])]
    status_list = [s for s in requested if s in allowed]
    if not status_list:
        status_list = ["failed", "retrying"]

    limit = max(1, min(int(limit), 50))
    offset = max(0, int(offset))

    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return {
            "available": False,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "statuses": status_list,
            "reason": "SYNC_JOBS_TABLE_UNAVAILABLE",
        }

    placeholders = ", ".join(["?"] * len(status_list))
    params: List[Any] = list(status_list)
    count_rows = db_optimizer.execute_query(
        f"""
        SELECT COUNT(*) AS total
        FROM gmail_sync_jobs
        WHERE status IN ({placeholders})
        """,
        tuple(params),
    )
    total = 0
    if count_rows:
        row = count_rows[0]
        total = int(row.get("total") if hasattr(row, "keys") else row[0])

    # One JOIN for tenant labels — no per-row OAuth eligibility (dossier owns retry).
    has_users = db_optimizer.table_exists("users")
    if has_users:
        rows = db_optimizer.execute_query(
            f"""
            SELECT j.job_id, j.user_id, j.status, j.error_message, j.created_at,
                   j.started_at, j.completed_at, j.metadata,
                   u.email AS tenant_email, u.name AS tenant_name, u.business_name
            FROM gmail_sync_jobs j
            LEFT JOIN users u ON u.id = j.user_id
            WHERE j.status IN ({placeholders})
            ORDER BY j.created_at DESC, j.job_id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
    else:
        rows = db_optimizer.execute_query(
            f"""
            SELECT job_id, user_id, status, error_message, created_at,
                   started_at, completed_at, metadata
            FROM gmail_sync_jobs
            WHERE status IN ({placeholders})
            ORDER BY created_at DESC, job_id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )

    items: List[Dict[str, Any]] = []
    for row in rows or []:
        data = _row_dict(row)
        tenant_id = int(data.get("user_id") or 0)
        job_id = str(data.get("job_id") or "")
        meta = _parse_meta(data.get("metadata"))
        safe_meta = {
            k: meta.get(k)
            for k in ("sync_type", "admin_retry_of", "correlation_id")
            if k in meta
        }
        err = (data.get("error_message") or "")[:240] or None
        items.append(
            {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "tenant_email": (data.get("tenant_email") or None) if has_users else None,
                "tenant_name": (data.get("tenant_name") or None) if has_users else None,
                "business_name": (data.get("business_name") or None) if has_users else None,
                "status": data.get("status"),
                "error_message": err,
                "created_at": data.get("created_at"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "metadata": safe_meta,
                "dossier_path": f"/admin/tenants/{tenant_id}#sync-jobs" if tenant_id else None,
            }
        )

    return {
        "available": True,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "statuses": status_list,
    }


def _load_job(tenant_id: int, job_id: str) -> Optional[Dict[str, Any]]:
    from core.database_optimization import db_optimizer

    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT job_id, user_id, status, metadata, error_message, created_at, completed_at
        FROM gmail_sync_jobs
        WHERE job_id = ? AND user_id = ?
        LIMIT 1
        """,
        (str(job_id), int(tenant_id)),
    )
    if not rows:
        return None
    return _row_dict(rows[0])


def _tenant_is_active(tenant_id: int) -> bool:
    from core.database_optimization import db_optimizer

    active = db_optimizer.sql_cast_int_eq_one("is_active")
    rows = db_optimizer.execute_query(
        f"SELECT id FROM users WHERE id = ? AND {active} LIMIT 1",
        (int(tenant_id),),
    )
    return bool(rows)


def _gmail_oauth_present(tenant_id: int) -> bool:
    from core.database_optimization import db_optimizer

    if db_optimizer.table_exists("gmail_tokens"):
        rows = db_optimizer.execute_query(
            "SELECT id FROM gmail_tokens WHERE user_id = ? LIMIT 1",
            (int(tenant_id),),
        )
        if rows:
            return True
    if db_optimizer.table_exists("oauth_tokens"):
        rows = db_optimizer.execute_query(
            """
            SELECT id FROM oauth_tokens
            WHERE user_id = ? AND LOWER(COALESCE(provider, '')) = 'gmail'
            LIMIT 1
            """,
            (int(tenant_id),),
        )
        return bool(rows)
    return False


def _is_gmail_sync_job(job_id: str, meta: Dict[str, Any]) -> bool:
    """True only when the job is explicitly a Gmail sync (fail closed on ambiguity)."""
    jid = str(job_id or "")
    if jid.startswith("gmail_sync_"):
        return True
    if jid.startswith("outlook_") or jid.startswith("outlook_sync_"):
        return False
    provider = str(meta.get("provider") or meta.get("sync_provider") or "").strip().lower()
    if provider and provider != "gmail":
        return False
    if provider == "gmail":
        return True
    triggered = str(meta.get("triggered_by") or "").lower()
    return "gmail" in triggered


def _is_permanently_non_retryable(error_message: Optional[str]) -> bool:
    text = (error_message or "").lower()
    return any(marker in text for marker in _PERMANENT_FAILURE_MARKERS)


def _newer_successful_sync_exists(tenant_id: int, job_created_at: Any) -> bool:
    from core.database_optimization import db_optimizer

    if not job_created_at:
        return False
    rows = db_optimizer.execute_query(
        """
        SELECT job_id FROM gmail_sync_jobs
        WHERE user_id = ?
          AND status = 'completed'
          AND created_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (int(tenant_id), job_created_at),
    )
    return bool(rows)


def _has_active_sync(tenant_id: int, *, exclude_job_id: Optional[str] = None) -> bool:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        """
        SELECT job_id FROM gmail_sync_jobs
        WHERE user_id = ? AND status IN ('pending', 'processing')
        LIMIT 5
        """,
        (int(tenant_id),),
    )
    for row in rows or []:
        jid = row.get("job_id") if hasattr(row, "keys") else row[0]
        if exclude_job_id and str(jid) == str(exclude_job_id):
            continue
        return True
    return False


def evaluate_retry_eligibility(
    *,
    tenant_id: int,
    job_id: str,
    job_row: Optional[Dict[str, Any]] = None,
    check_oauth: bool = True,
    check_tenant_active: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Server-side retry eligibility (UI must not be the source of truth)."""
    job = job_row or _load_job(tenant_id, job_id)
    if not job:
        return False, "JOB_NOT_FOUND"

    status = str(job.get("status") or "")
    if status in ("superseded_by_retry", "admin_retry_claimed"):
        return False, "JOB_NOT_RETRYABLE"
    if status not in RETRYABLE_STATUSES:
        return False, "JOB_NOT_RETRYABLE"

    meta = _parse_meta(job.get("metadata"))
    if not _is_gmail_sync_job(str(job.get("job_id") or job_id), meta):
        return False, "JOB_NOT_RETRYABLE"

    if check_tenant_active and not _tenant_is_active(tenant_id):
        return False, "JOB_NOT_RETRYABLE"

    if check_oauth and not _gmail_oauth_present(tenant_id):
        return False, "JOB_NOT_RETRYABLE"

    if _is_permanently_non_retryable(job.get("error_message")):
        return False, "JOB_NOT_RETRYABLE"

    if _newer_successful_sync_exists(tenant_id, job.get("created_at")):
        return False, "JOB_NOT_RETRYABLE"

    if _has_active_sync(tenant_id, exclude_job_id=str(job.get("job_id") or job_id)):
        return False, "SYNC_ALREADY_ACTIVE"

    return True, None


def _claim_failed_job(tenant_id: int, job_id: str, actor_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Conditionally claim a failed/retrying job.

    Returns (claimed, error_code, previous_status).
    Uses UPDATE ... WHERE status IN (...) and requires exactly one row updated.
    """
    from core.database_optimization import db_optimizer

    job = _load_job(tenant_id, job_id)
    if not job:
        return False, "JOB_NOT_FOUND", None
    previous_status = str(job.get("status") or "")

    meta = _parse_meta(job.get("metadata"))
    meta["admin_retry_claimed_by"] = int(actor_id)
    meta["admin_retry_claimed_at"] = int(time.time())

    rows_affected = db_optimizer.execute_query(
        """
        UPDATE gmail_sync_jobs
        SET status = 'admin_retry_claimed',
            metadata = ?,
            error_message = COALESCE(error_message, 'Admin retry claimed')
        WHERE job_id = ? AND user_id = ? AND status IN ('failed', 'retrying')
        """,
        (json.dumps(meta), str(job_id), int(tenant_id)),
        fetch=False,
    )
    try:
        updated = int(rows_affected or 0)
    except Exception:
        updated = 0
    if updated != 1:
        # Another worker claimed it, or status changed.
        current = _load_job(tenant_id, job_id)
        if current and str(current.get("status")) == "admin_retry_claimed":
            return False, "ALREADY_CLAIMED", previous_status
        return False, "JOB_NOT_RETRYABLE", previous_status
    return True, None, previous_status


def _enqueue_with_stable_id(manager: Any, new_job_id: str) -> str:
    """
    Enqueue worker task using the Gmail sync job_id as the queue task id when possible.
    Ambiguous enqueue failures after DB insert must not roll back the original claim.
    """
    from email_automation.gmail_sync_jobs import should_process_gmail_sync_inline

    if should_process_gmail_sync_inline():
        return "inline_deferred"

    try:
        from core.redis_queues import get_queue_manager

        qm = get_queue_manager()
        if not qm or not hasattr(qm, "enqueue_job"):
            return "db_pending"
        # Deduplicate: if this queue id already exists, treat as success.
        if hasattr(qm, "get_job_status"):
            existing = qm.get_job_status(new_job_id)
            if existing is not None:
                return "rq_deduped"
        qm.enqueue_job(
            "process_gmail_sync",
            args={"job_id": new_job_id},
            max_retries=3,
            delay=0,
            job_id=new_job_id,
        )
        return "rq"
    except TypeError:
        # Older enqueue_job without job_id kwarg — fall back.
        try:
            from core.redis_queues import get_queue_manager

            qm = get_queue_manager()
            if qm and hasattr(qm, "enqueue_job"):
                qm.enqueue_job("process_gmail_sync", args={"job_id": new_job_id})
                return "rq"
        except Exception as exc:
            logger.warning("Admin sync retry enqueue soft-failed job=%s: %s", new_job_id, exc)
            return "db_pending"
    except Exception as exc:
        logger.warning("Admin sync retry enqueue soft-failed job=%s: %s", new_job_id, exc)
        return "db_pending"


def retry_failed_gmail_sync(
    *,
    actor_id: int,
    tenant_id: int,
    job_id: str,
    idempotency_key: str,
    confirm: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Retry a failed Gmail sync for tenant_id/job_id.

    Returns (result, error_code).
    Step-up is revalidated here; it is not consumed (multi-retry within TTL).
    """
    from core.admin_security import get_admin_step_up_state, step_up_required
    from core.admin_security_store import AdminSecurityStoreUnavailable, get_admin_security_store
    from core.database_optimization import db_optimizer

    if str(confirm or "").strip().lower() != "retry":
        return None, "CONFIRMATION_REQUIRED"

    job_id = str(job_id or "").strip()
    if not job_id or len(job_id) > 128 or "/" in job_id or "\\" in job_id:
        return None, "INVALID_JOB_ID"

    client_key = str(idempotency_key or "").strip()
    if not client_key or len(client_key) > 128:
        return None, "IDEMPOTENCY_REQUIRED"

    # Step-up must still be valid at execution time (not consumed by sync.retry).
    step_state = get_admin_step_up_state(int(actor_id))
    if step_state is None and step_up_required():
        return None, "STEP_UP_EXPIRED"

    try:
        store = get_admin_security_store()
        store.require_available()
    except AdminSecurityStoreUnavailable:
        return None, "STORE_UNAVAILABLE"

    normalized = _normalize_payload(tenant_id, job_id, confirm)
    payload_digest = _payload_hash(normalized)
    binding = {
        "actor_id": int(actor_id),
        "tenant_id": int(tenant_id),
        "job_id": job_id,
        "action": ACTION_NAME,
        "payload_hash": payload_digest,
    }
    idem_store_key = _client_idem_store_key(store, client_key)
    existing = store.get_json(idem_store_key)
    if existing:
        existing_binding = existing.get("binding") or {}
        if existing_binding != binding:
            return None, "IDEMPOTENCY_CONFLICT"
        if existing.get("result"):
            cached = _safe_public_result(existing["result"])
            cached["replayed"] = True
            return cached, None
        if existing.get("pending"):
            return None, "RETRY_IN_PROGRESS"

    reserved = store.set_nx(
        idem_store_key,
        {"pending": True, "binding": binding, "created_at": int(time.time())},
        ttl=IDEMPOTENCY_TTL_SECONDS,
    )
    if not reserved:
        existing = store.get_json(idem_store_key)
        if existing:
            existing_binding = existing.get("binding") or {}
            if existing_binding != binding:
                return None, "IDEMPOTENCY_CONFLICT"
            if existing.get("result"):
                cached = _safe_public_result(existing["result"])
                cached["replayed"] = True
                return cached, None
        return None, "RETRY_IN_PROGRESS"

    eligible, eligibility_err = evaluate_retry_eligibility(
        tenant_id=int(tenant_id),
        job_id=job_id,
    )
    if not eligible:
        store.delete(idem_store_key)
        return None, eligibility_err or "JOB_NOT_RETRYABLE"

    claimed, claim_err, previous_status = _claim_failed_job(tenant_id, job_id, actor_id)
    if not claimed:
        store.delete(idem_store_key)
        return None, claim_err or "ALREADY_CLAIMED"

    try:
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        correlation_id = f"admin-retry-{secrets.token_hex(8)}"
        # Stable new job id derived from original + actor for queue dedup friendliness.
        new_job_id = f"gmail_sync_{int(tenant_id)}_{int(time.time())}_{secrets.token_hex(3)}"

        # Insert pending job with predetermined id (bypass random id in queue_sync_job).
        job_meta = {
            "admin_retry_of": job_id,
            "admin_actor_id": int(actor_id),
            "triggered_by": "platform_admin_retry",
            "provider": "gmail",
            "sync_type": "incremental",
            "correlation_id": correlation_id,
        }
        inserted = db_optimizer.execute_query(
            """
            INSERT INTO gmail_sync_jobs (user_id, job_id, status, metadata)
            VALUES (?, ?, 'pending', ?)
            """,
            (int(tenant_id), new_job_id, json.dumps(job_meta)),
            fetch=False,
        )
        # If insert somehow raced on unique job_id, treat as success path via existing row.
        if inserted == 0:
            existing_new = _load_job(tenant_id, new_job_id)
            if not existing_new:
                raise RuntimeError("queue_insert_failed")

        try:
            db_optimizer.upsert_user_sync_status_merge(
                int(tenant_id), sync_status="pending", syncing=0
            )
        except Exception:
            pass

        # Link claimed original → new job; mark superseded (do not roll this back on enqueue ambiguity).
        claimed_row = _load_job(tenant_id, job_id) or {}
        meta = _parse_meta(claimed_row.get("metadata"))
        meta["admin_retry_job_id"] = new_job_id
        db_optimizer.execute_query(
            """
            UPDATE gmail_sync_jobs
            SET status = 'superseded_by_retry',
                metadata = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE job_id = ? AND user_id = ? AND status = 'admin_retry_claimed'
            """,
            (json.dumps(meta), str(job_id), int(tenant_id)),
            fetch=False,
        )

        enqueue_mode = _enqueue_with_stable_id(manager, new_job_id)

        result = _safe_public_result(
            {
                "retried": True,
                "original_job_id": job_id,
                "new_job_id": new_job_id,
                "tenant_id": int(tenant_id),
                "enqueued": True,
                "enqueue_mode": enqueue_mode,
                "correlation_id": correlation_id,
                "previous_status": previous_status,
                "resulting_status": "superseded_by_retry",
                "idempotency_key_hash": _idem_key_hash(client_key),
                "replayed": False,
            }
        )
        store.set_json(
            idem_store_key,
            {"binding": binding, "result": result, "completed_at": int(time.time())},
            ttl=IDEMPOTENCY_TTL_SECONDS,
        )
        return result, None
    except Exception as exc:
        logger.warning("Admin sync retry failed before replacement job committed: %s", exc)
        # Only restore original if we never created a replacement job.
        try:
            db_optimizer.execute_query(
                """
                UPDATE gmail_sync_jobs
                SET status = 'failed',
                    error_message = ?
                WHERE job_id = ? AND user_id = ? AND status = 'admin_retry_claimed'
                """,
                ("Admin retry failed; restored to failed", str(job_id), int(tenant_id)),
                fetch=False,
            )
        except Exception:
            pass
        try:
            store.delete(idem_store_key)
        except Exception:
            pass
        return None, "QUEUE_UNAVAILABLE"
