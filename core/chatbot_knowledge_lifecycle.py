"""
Canonical chatbot knowledge lifecycle — backend source of truth for ingest/index readiness.

Does not replace retrieval orchestration; records operational state for FAQs, KB documents,
and vector indexing so builder UI and ops can reflect truthful readiness.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    KB_DOCUMENT = "kb_document"
    FAQ = "faq"


class LifecycleState(str, Enum):
    """Ordered progression; not all artifacts traverse every state."""
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    STORED = "stored"
    CHUNKED = "chunked"
    VECTORIZED = "vectorized"
    INDEXED = "indexed"
    RETRIEVAL_READY = "retrieval_ready"
    FAILED = "failed"
    STALE = "stale"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "n/a"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _is_test_skip() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST")) and os.getenv("FIKIRI_CHATBOT_LIFECYCLE_FORCE") != "1"


def lifecycle_table_enabled() -> bool:
    if _is_test_skip():
        return False
    try:
        return bool(db_optimizer.table_exists("chatbot_knowledge_lifecycle"))
    except Exception:
        return False


def _row_to_dict(row: Any) -> Dict[str, Any]:
    return dict(row) if not isinstance(row, dict) else row


def upsert_lifecycle_row(
    *,
    artifact_id: str,
    artifact_type: ArtifactType,
    tenant_id: str,
    user_id: Optional[int] = None,
    lifecycle_state: LifecycleState,
    storage_status: StepStatus = StepStatus.COMPLETED,
    chunk_status: StepStatus = StepStatus.PENDING,
    vectorization_status: StepStatus = StepStatus.PENDING,
    extraction_status: StepStatus = StepStatus.NOT_APPLICABLE,
    retrieval_ready: bool = False,
    vector_chunk_count: int = 0,
    last_error: Optional[str] = None,
    retryable: bool = False,
    content_fingerprint: Optional[str] = None,
    durable_job_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not lifecycle_table_enabled():
        return
    now = _utcnow_iso()
    last_indexed = now if vectorization_status == StepStatus.COMPLETED and vector_chunk_count > 0 else None
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO chatbot_knowledge_lifecycle (
                artifact_id, artifact_type, tenant_id, user_id,
                lifecycle_state, extraction_status, storage_status,
                chunk_status, vectorization_status, retrieval_ready,
                vector_chunk_count, last_indexed_at, last_error,
                retryable, content_fingerprint, durable_job_id, metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id, artifact_type) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                user_id = excluded.user_id,
                lifecycle_state = excluded.lifecycle_state,
                extraction_status = excluded.extraction_status,
                storage_status = excluded.storage_status,
                chunk_status = excluded.chunk_status,
                vectorization_status = excluded.vectorization_status,
                retrieval_ready = excluded.retrieval_ready,
                vector_chunk_count = excluded.vector_chunk_count,
                last_indexed_at = COALESCE(excluded.last_indexed_at, chatbot_knowledge_lifecycle.last_indexed_at),
                last_error = excluded.last_error,
                retryable = excluded.retryable,
                content_fingerprint = COALESCE(
                    excluded.content_fingerprint,
                    chatbot_knowledge_lifecycle.content_fingerprint
                ),
                durable_job_id = COALESCE(excluded.durable_job_id, chatbot_knowledge_lifecycle.durable_job_id),
                metadata_json = COALESCE(excluded.metadata_json, chatbot_knowledge_lifecycle.metadata_json),
                updated_at = excluded.updated_at
            """,
            (
                artifact_id,
                artifact_type.value,
                tenant_id,
                user_id,
                lifecycle_state.value,
                extraction_status.value,
                storage_status.value,
                chunk_status.value,
                vectorization_status.value,
                1 if retrieval_ready else 0,
                int(vector_chunk_count or 0),
                last_indexed,
                last_error,
                1 if retryable else 0,
                content_fingerprint,
                durable_job_id,
                json.dumps(metadata or {}, sort_keys=True),
                now,
                now,
            ),
        )
        logger.info(
            "chatbot knowledge lifecycle updated",
            extra={
                "event": "chatbot.knowledge.lifecycle.updated",
                "service": "chatbot",
                "severity": "INFO",
                "artifact_id": artifact_id,
                "artifact_type": artifact_type.value,
                "tenant_id": tenant_id,
                "lifecycle_state": lifecycle_state.value,
                "retrieval_ready": retrieval_ready,
                "vector_chunk_count": vector_chunk_count,
            },
        )
    except Exception as exc:
        logger.warning("upsert_lifecycle_row failed (non-fatal): %s", exc)


def mark_kb_stored(
    *,
    doc_id: str,
    tenant_id: str,
    user_id: Optional[int],
    content_fingerprint: Optional[str] = None,
) -> None:
    upsert_lifecycle_row(
        artifact_id=doc_id,
        artifact_type=ArtifactType.KB_DOCUMENT,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.STORED,
        storage_status=StepStatus.COMPLETED,
        vectorization_status=StepStatus.PENDING,
        chunk_status=StepStatus.PENDING,
        retrieval_ready=False,
        content_fingerprint=content_fingerprint,
    )


def mark_kb_vectorization_running(
    *,
    doc_id: str,
    tenant_id: str,
    user_id: Optional[int],
    durable_job_id: Optional[str] = None,
) -> None:
    upsert_lifecycle_row(
        artifact_id=doc_id,
        artifact_type=ArtifactType.KB_DOCUMENT,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.CHUNKED,
        storage_status=StepStatus.COMPLETED,
        chunk_status=StepStatus.RUNNING,
        vectorization_status=StepStatus.RUNNING,
        durable_job_id=durable_job_id,
        retrieval_ready=False,
    )


def mark_kb_vectorization_completed(
    *,
    doc_id: str,
    tenant_id: str,
    user_id: Optional[int],
    vector_chunk_count: int,
    content_fingerprint: Optional[str] = None,
    durable_job_id: Optional[str] = None,
) -> None:
    ready = vector_chunk_count > 0
    state = LifecycleState.RETRIEVAL_READY if ready else LifecycleState.INDEXED
    upsert_lifecycle_row(
        artifact_id=doc_id,
        artifact_type=ArtifactType.KB_DOCUMENT,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=state,
        storage_status=StepStatus.COMPLETED,
        chunk_status=StepStatus.COMPLETED,
        vectorization_status=StepStatus.COMPLETED,
        retrieval_ready=ready,
        vector_chunk_count=vector_chunk_count,
        content_fingerprint=content_fingerprint,
        durable_job_id=durable_job_id,
    )


def mark_kb_vectorization_failed(
    *,
    doc_id: str,
    tenant_id: str,
    user_id: Optional[int],
    error: str,
    retryable: bool = True,
    durable_job_id: Optional[str] = None,
) -> None:
    upsert_lifecycle_row(
        artifact_id=doc_id,
        artifact_type=ArtifactType.KB_DOCUMENT,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.FAILED,
        storage_status=StepStatus.COMPLETED,
        chunk_status=StepStatus.FAILED,
        vectorization_status=StepStatus.FAILED,
        retrieval_ready=False,
        last_error=(error or "")[:2000],
        retryable=retryable,
        durable_job_id=durable_job_id,
    )


def mark_faq_stored(
    *,
    faq_id: str,
    tenant_id: str,
    user_id: Optional[int],
) -> None:
    upsert_lifecycle_row(
        artifact_id=str(faq_id),
        artifact_type=ArtifactType.FAQ,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.STORED,
        storage_status=StepStatus.COMPLETED,
        vectorization_status=StepStatus.PENDING,
        retrieval_ready=True,
        metadata={"keyword_search_ready": True},
    )


def mark_faq_vectorization_completed(
    *,
    faq_id: str,
    tenant_id: str,
    user_id: Optional[int],
    vector_key: Optional[str] = None,
) -> None:
    upsert_lifecycle_row(
        artifact_id=str(faq_id),
        artifact_type=ArtifactType.FAQ,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.RETRIEVAL_READY,
        storage_status=StepStatus.COMPLETED,
        vectorization_status=StepStatus.COMPLETED if vector_key else StepStatus.SKIPPED,
        retrieval_ready=True,
        vector_chunk_count=1 if vector_key else 0,
        metadata={"keyword_search_ready": True, "vector_key": vector_key},
    )


def mark_faq_vectorization_failed(
    *,
    faq_id: str,
    tenant_id: str,
    user_id: Optional[int],
    error: str,
) -> None:
    upsert_lifecycle_row(
        artifact_id=str(faq_id),
        artifact_type=ArtifactType.FAQ,
        tenant_id=tenant_id,
        user_id=user_id,
        lifecycle_state=LifecycleState.STORED,
        storage_status=StepStatus.COMPLETED,
        vectorization_status=StepStatus.FAILED,
        retrieval_ready=True,
        last_error=(error or "")[:2000],
        retryable=True,
        metadata={"keyword_search_ready": True},
    )


def _count_seed_faqs() -> int:
    from core.smart_faq_system import get_smart_faq

    faq = get_smart_faq()
    return sum(1 for f in faq.faq_entries.values() if f.user_id is None)


def _tenant_faq_counts(tenant_id: str, user_id: Optional[int]) -> Dict[str, int]:
    from core.smart_faq_system import get_smart_faq

    faq = get_smart_faq()
    total = 0
    tenant_owned = 0
    for entry in faq.faq_entries.values():
        if entry.user_id is None:
            continue
        if user_id is not None and entry.user_id == user_id:
            tenant_owned += 1
        total += 1
    return {"platform_seed_faqs": _count_seed_faqs(), "tenant_faqs": tenant_owned}


def _tenant_kb_from_memory(tenant_id: str) -> List[Dict[str, Any]]:
    from core.knowledge_base_system import get_knowledge_base

    kb = get_knowledge_base()
    out = []
    for doc in kb.list_documents(tenant_id=tenant_id):
        meta = doc.metadata or {}
        chunk_ids = meta.get("chunk_vector_ids") or []
        vector_id = meta.get("vector_id")
        chunk_count = meta.get("chunk_count") or (len(chunk_ids) if chunk_ids else (1 if vector_id else 0))
        semantic_ready = bool(chunk_count and (vector_id or chunk_ids))
        out.append(
            {
                "doc_id": doc.id,
                "title": doc.title,
                "semantic_ready": semantic_ready,
                "chunk_count": int(chunk_count or 0),
            }
        )
    return out


def _lifecycle_rows_for_tenant(tenant_id: str) -> List[Dict[str, Any]]:
    if not lifecycle_table_enabled():
        return []
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT artifact_id, artifact_type, lifecycle_state, storage_status,
                   chunk_status, vectorization_status, retrieval_ready,
                   vector_chunk_count, last_indexed_at, last_error, retryable,
                   updated_at
            FROM chatbot_knowledge_lifecycle
            WHERE tenant_id = ?
            ORDER BY updated_at DESC
            """,
            (tenant_id,),
            fetch=True,
        )
        return [_row_to_dict(r) for r in (rows or [])]
    except Exception as exc:
        logger.warning("lifecycle rows query failed: %s", exc)
        return []


def _failed_vector_jobs(user_id: Optional[int], limit: int = 20) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    try:
        from core.durable_jobs import JOB_KIND_KB_VECTORIZE, STATUS_DEAD, STATUS_FAILED

        rows = db_optimizer.execute_query(
            """
            SELECT job_id, status, last_error, external_ref, updated_at, retry_count, dead_letter
            FROM background_jobs
            WHERE user_id = ? AND job_kind = ?
              AND status IN (?, ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, JOB_KIND_KB_VECTORIZE, STATUS_FAILED, STATUS_DEAD, limit),
            fetch=True,
        )
        return [_row_to_dict(r) for r in (rows or [])]
    except Exception:
        return []


def compute_tenant_retrieval_health(
    tenant_id: str,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Truthful retrieval readiness for a tenant (session user / API key tenant).
    Combines lifecycle table, in-memory KB/FAQ state, vector job failures, and feature flags.
    """
    from core.feature_flags import get_feature_flags

    flags = get_feature_flags()
    vector_search_enabled = flags.is_enabled("vector_search")

    faq_counts = _tenant_faq_counts(tenant_id, user_id)
    kb_docs = _tenant_kb_from_memory(tenant_id)
    lifecycle_rows = _lifecycle_rows_for_tenant(tenant_id)

    retrieval_ready_kb = sum(1 for d in kb_docs if d["semantic_ready"])
    stored_kb = len(kb_docs)
    keyword_ready_kb = stored_kb

    lifecycle_ready = sum(1 for r in lifecycle_rows if r.get("retrieval_ready"))
    pending_vector = sum(
        1
        for r in lifecycle_rows
        if r.get("vectorization_status") in (StepStatus.PENDING.value, StepStatus.RUNNING.value)
    )
    failed_lifecycle = sum(1 for r in lifecycle_rows if r.get("lifecycle_state") == LifecycleState.FAILED.value)
    stale_lifecycle = sum(1 for r in lifecycle_rows if r.get("lifecycle_state") == LifecycleState.STALE.value)

    failed_jobs = _failed_vector_jobs(user_id)

    faq_keyword_ready = faq_counts["platform_seed_faqs"] + faq_counts["tenant_faqs"]

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "vector_search_enabled": vector_search_enabled,
        "summary": {
            "faq_keyword_ready_count": faq_keyword_ready,
            "platform_seed_faq_count": faq_counts["platform_seed_faqs"],
            "tenant_faq_count": faq_counts["tenant_faqs"],
            "kb_stored_count": stored_kb,
            "kb_keyword_ready_count": keyword_ready_kb,
            "kb_semantic_ready_count": retrieval_ready_kb,
            "lifecycle_retrieval_ready_count": lifecycle_ready,
            "pending_vectorization_count": pending_vector,
            "failed_artifact_count": failed_lifecycle,
            "stale_artifact_count": stale_lifecycle,
            "failed_vector_jobs_count": len(failed_jobs),
        },
        "pipelines": {
            "faq": {
                "stored": faq_keyword_ready > 0,
                "keyword_retrieval": True,
                "semantic_retrieval": vector_search_enabled,
            },
            "knowledge_base": {
                "stored_count": stored_kb,
                "requires_vector_for_semantic": vector_search_enabled,
            },
            "document_upload": {
                "extract_only": True,
                "note": "Upload extracts text client-side until saved as KB or vectorized.",
            },
        },
        "preview_live_parity": True,
        "failed_vector_jobs": failed_jobs,
        "lifecycle_artifacts": lifecycle_rows[:50],
        "kb_documents": kb_docs[:50],
    }
