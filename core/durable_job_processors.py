"""
Dispatch durable background_jobs by job_kind to existing domain handlers.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from core.durable_jobs import (
    JOB_KIND_ANALYTICS_ROLLUP,
    JOB_KIND_CHATBOT_EVAL,
    JOB_KIND_GMAIL_SYNC,
    JOB_KIND_KB_CHUNK_CLEANUP,
    JOB_KIND_KB_VECTORIZE,
    get_durable_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    run_durable_job,
)

logger = logging.getLogger(__name__)


def _payload_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def process_gmail_sync_durable(job: Dict[str, Any]) -> Dict[str, Any]:
    from email_automation.gmail_sync_jobs import gmail_sync_job_manager

    external = job.get("external_ref") or (job.get("payload") or {}).get("gmail_job_id")
    if not external:
        return {"success": False, "error": "missing gmail_job_id", "allow_retry": False}
    trace_id = job.get("correlation_id")
    return gmail_sync_job_manager.process_sync_job(str(external), trace_id=trace_id)


def process_kb_vectorize_durable(job: Dict[str, Any]) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    user_id = job.get("user_id")
    doc_id = str(payload.get("doc_id") or "")
    content = str(payload.get("content") or "")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    prior = payload.get("prior_metadata") if isinstance(payload.get("prior_metadata"), dict) else None
    if not doc_id or not content:
        return {"success": False, "error": "doc_id and content required", "allow_retry": False}

    from core.chatbot_vector_chunk_ingestion import sync_kb_document_vectors
    from core.knowledge_base_system import _get_vector_search

    vs = _get_vector_search()
    if vs is None:
        return {"success": False, "error": "vector search unavailable", "allow_retry": True}

    vector_ids, primary = sync_kb_document_vectors(
        vs,
        doc_id=doc_id,
        text=content,
        base_metadata=metadata,
        prior_metadata=prior,
    )
    return {
        "success": bool(vector_ids),
        "vector_ids_count": len(vector_ids or []),
        "primary_vector_id": str(primary) if primary is not None else None,
        "content_hash": _payload_hash(content),
    }


def process_kb_chunk_cleanup_durable(job: Dict[str, Any]) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    doc_id = str(payload.get("doc_id") or "")
    if not doc_id:
        return {"success": False, "error": "doc_id required", "allow_retry": False}

    from core.chatbot_vector_chunk_cleanup import delete_kb_chunk_vectors
    from core.knowledge_base_system import _get_vector_search

    vs = _get_vector_search()
    if vs is None:
        return {"success": True, "skipped": True, "reason": "no vector search"}

    stats = delete_kb_chunk_vectors(
        vs,
        doc_id,
        stored_chunk_ids=payload.get("chunk_vector_ids"),
        previous_chunk_count=payload.get("chunk_count"),
        prior_vector_id=payload.get("vector_id"),
        use_pinecone=bool(payload.get("use_pinecone")),
    )
    return {"success": True, "cleanup": stats}


def process_analytics_rollup_durable(job: Dict[str, Any]) -> Dict[str, Any]:
    user_id = job.get("user_id")
    if not user_id:
        return {"success": False, "error": "user_id required", "allow_retry": False}
    payload = job.get("payload") or {}
    from analytics.service_activity_rollups import _refresh_tenant_analytics_impl

    counts = _refresh_tenant_analytics_impl(
        int(user_id),
        mirror_billing=bool(payload.get("mirror_billing", True)),
    )
    return {"success": True, "counts": counts}


def process_chatbot_eval_durable(job: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for future eval runs — records completion without external side effects."""
    payload = job.get("payload") or {}
    eval_id = payload.get("eval_id") or job.get("job_id")
    return {"success": True, "eval_id": eval_id, "status": "not_implemented"}


_PROCESSORS = {
    JOB_KIND_GMAIL_SYNC: process_gmail_sync_durable,
    JOB_KIND_KB_VECTORIZE: process_kb_vectorize_durable,
    JOB_KIND_KB_CHUNK_CLEANUP: process_kb_chunk_cleanup_durable,
    JOB_KIND_ANALYTICS_ROLLUP: process_analytics_rollup_durable,
    JOB_KIND_CHATBOT_EVAL: process_chatbot_eval_durable,
}


def process_durable_background_job(job_id: str, **kwargs: Any) -> Dict[str, Any]:
    """Entry point for Redis worker / inline runners."""
    job = get_durable_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}

    kind = job.get("job_kind")
    processor = _PROCESSORS.get(kind)
    if not processor:
        mark_job_failed(job_id, f"unknown job_kind: {kind}", allow_retry=False)
        return {"success": False, "error": f"unknown job_kind: {kind}"}

    return run_durable_job(job_id, processor)


def run_inline_durable_job(
    job_kind: str,
    *,
    user_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enqueue + run immediately in-process (for inline vectorize / rollup / cleanup).
    Returns worker result; duplicate idempotency returns {success: True, duplicate: True}.
    """
    from core.durable_jobs import enqueue_durable_job, find_active_job_by_idempotency

    if idempotency_key:
        existing = find_active_job_by_idempotency(idempotency_key, job_kind=job_kind)
        if existing:
            return {
                "success": True,
                "duplicate": True,
                "job_id": existing.get("job_id"),
                "external_ref": existing.get("external_ref"),
            }

    jid = enqueue_durable_job(
        job_kind,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        external_ref=external_ref,
    )
    if not jid:
        if idempotency_key:
            existing = find_active_job_by_idempotency(idempotency_key, job_kind=job_kind)
            if existing:
                return {"success": True, "duplicate": True, "job_id": existing.get("job_id")}
        return {"success": False, "error": "enqueue failed"}

    processor = _PROCESSORS.get(job_kind)
    if not processor:
        mark_job_failed(jid, f"unknown job_kind: {job_kind}", allow_retry=False)
        return {"success": False, "error": "unknown processor"}

    return run_durable_job(jid, processor)
