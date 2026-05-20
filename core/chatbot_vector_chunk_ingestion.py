"""
Vector-store ingestion helpers for chunked chatbot knowledge documents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from core.chatbot_knowledge_chunking import TextChunk, chunk_text, chunk_vector_id
from core.chatbot_vector_chunk_cleanup import delete_kb_chunk_vectors

import hashlib

VectorId = Union[str, int]


def build_chunk_metadata(
    base_metadata: Dict[str, Any],
    *,
    parent_doc_id: str,
    chunk: TextChunk,
) -> Dict[str, Any]:
    metadata = dict(base_metadata or {})
    metadata["parent_doc_id"] = str(parent_doc_id)
    metadata.setdefault("document_id", parent_doc_id)
    metadata["chunk_index"] = chunk.chunk_index
    metadata["total_chunks"] = chunk.total_chunks
    if chunk.total_chunks > 1:
        metadata["source_type"] = "kb_document_chunk"
    else:
        metadata.setdefault("source_type", metadata.get("type", "knowledge_base"))
    return metadata


def ingest_kb_text_to_vector_store(
    vector_search: Any,
    *,
    text: str,
    parent_doc_id: str,
    base_metadata: Optional[Dict[str, Any]] = None,
    use_pinecone: bool = False,
    max_chars: int = 1200,
    overlap_chars: int = 150,
    cleanup_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[List[VectorId], Optional[VectorId]]:
    """
    Vectorize KB text as one or more chunks.

    Returns (vector_ids, primary_vector_id). primary_vector_id is stored on KB metadata.
    """
    chunks = chunk_text(text, max_chars=max_chars, overlap_chars=overlap_chars)
    if not chunks:
        return [], None

    if cleanup_metadata is not None:
        delete_kb_chunk_vectors(
            vector_search,
            str(parent_doc_id),
            stored_chunk_ids=cleanup_metadata.get("chunk_vector_ids"),
            previous_chunk_count=cleanup_metadata.get("chunk_count"),
            prior_vector_id=cleanup_metadata.get("vector_id"),
            use_pinecone=use_pinecone,
        )

    vector_ids: List[VectorId] = []
    for chunk in chunks:
        vector_key = chunk_vector_id(parent_doc_id, chunk.chunk_index, chunk.total_chunks)
        metadata = build_chunk_metadata(
            base_metadata or {},
            parent_doc_id=parent_doc_id,
            chunk=chunk,
        )

        if use_pinecone:
            ok = vector_search.upsert_document(vector_key, chunk.text, metadata)
            if ok:
                vector_ids.append(vector_key)
            continue

        if chunk.total_chunks == 1:
            vector_id = vector_search.add_document(content=chunk.text, metadata=metadata)
        else:
            chunk_metadata = dict(metadata)
            chunk_metadata["document_id"] = vector_key
            vector_id = vector_search.add_document(content=chunk.text, metadata=chunk_metadata)

        if vector_id is not None and (not isinstance(vector_id, int) or vector_id >= 0):
            vector_ids.append(vector_id)

    primary = vector_ids[0] if vector_ids else None
    return vector_ids, primary


def _content_fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def ingest_kb_text_to_vector_store_tracked(
    vector_search: Any,
    *,
    text: str,
    parent_doc_id: str,
    user_id: Optional[int] = None,
    base_metadata: Optional[Dict[str, Any]] = None,
    use_pinecone: bool = False,
    max_chars: int = 1200,
    overlap_chars: int = 150,
    cleanup_metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Tuple[List[VectorId], Optional[VectorId]]:
    """
    Same as ingest_kb_text_to_vector_store with durable job lifecycle (inline).
    Idempotent per (doc_id, content fingerprint) for job rows; vector upsert remains safe to repeat.
    """
    from core.durable_jobs import (
        JOB_KIND_KB_VECTORIZE,
        build_idempotency_key,
        enqueue_durable_job,
        find_active_job_by_idempotency,
        mark_job_completed,
        mark_job_failed,
        mark_job_running,
        resolve_correlation_id,
    )

    fingerprint = _content_fingerprint(text)
    idem = build_idempotency_key("kb_vectorize", user_id, parent_doc_id, fingerprint)
    existing = find_active_job_by_idempotency(idem, job_kind=JOB_KIND_KB_VECTORIZE)
    if existing and existing.get("status") == "completed":
        return ingest_kb_text_to_vector_store(
            vector_search,
            text=text,
            parent_doc_id=parent_doc_id,
            base_metadata=base_metadata,
            use_pinecone=use_pinecone,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            cleanup_metadata=cleanup_metadata,
        )

    jid = enqueue_durable_job(
        JOB_KIND_KB_VECTORIZE,
        user_id=user_id,
        payload={"doc_id": str(parent_doc_id), "content_hash": fingerprint},
        idempotency_key=idem,
        correlation_id=resolve_correlation_id(correlation_id),
        external_ref=str(parent_doc_id),
    )
    if jid:
        mark_job_running(jid)
    try:
        vector_ids, primary = ingest_kb_text_to_vector_store(
            vector_search,
            text=text,
            parent_doc_id=parent_doc_id,
            base_metadata=base_metadata,
            use_pinecone=use_pinecone,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            cleanup_metadata=cleanup_metadata,
        )
        if jid:
            mark_job_completed(
                jid,
                {
                    "vector_ids_count": len(vector_ids or []),
                    "content_hash": fingerprint,
                },
            )
        return vector_ids, primary
    except Exception as exc:
        if jid:
            mark_job_failed(jid, str(exc), allow_retry=True)
        raise


def sync_kb_document_vectors(
    vector_search: Any,
    *,
    doc_id: str,
    text: str,
    base_metadata: Optional[Dict[str, Any]] = None,
    prior_metadata: Optional[Dict[str, Any]] = None,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> Tuple[List[VectorId], Optional[VectorId]]:
    """Re-chunk and re-ingest KB document text, cleaning up prior chunk vectors when known."""
    use_pinecone = getattr(vector_search, "use_pinecone", False) is True
    cleanup_metadata = None
    if prior_metadata and (
        prior_metadata.get("vector_id") or prior_metadata.get("chunk_vector_ids")
    ):
        cleanup_metadata = {
            "vector_id": prior_metadata.get("vector_id"),
            "chunk_vector_ids": prior_metadata.get("chunk_vector_ids"),
            "chunk_count": prior_metadata.get("chunk_count"),
        }
    return ingest_kb_text_to_vector_store(
        vector_search,
        text=text,
        parent_doc_id=str(doc_id),
        base_metadata=base_metadata,
        use_pinecone=use_pinecone,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
        cleanup_metadata=cleanup_metadata,
    )
