"""
Safe cleanup for chunked chatbot knowledge vectors (local + Pinecone).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Union

from core.chatbot_knowledge_chunking import chunk_vector_id

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHUNK_CLEANUP = 64
VectorId = Union[str, int]


def get_max_chunk_cleanup() -> int:
    raw = (os.getenv("FIKIRI_KB_CHUNK_CLEANUP_MAX") or str(DEFAULT_MAX_CHUNK_CLEANUP)).strip()
    try:
        return max(1, min(int(raw), 256))
    except ValueError:
        return DEFAULT_MAX_CHUNK_CLEANUP


def bounded_chunk_vector_ids(parent_doc_id: str, max_chunks: Optional[int] = None) -> List[str]:
    """Fallback chunk ids when stored metadata is missing."""
    parent = str(parent_doc_id)
    limit = max_chunks if max_chunks is not None else get_max_chunk_cleanup()
    ids = [parent]
    for index in range(limit):
        ids.append(chunk_vector_id(parent, index, max(limit, 2)))
    return ids


def collect_chunk_vector_ids(
    parent_doc_id: str,
    *,
    stored_chunk_ids: Optional[Sequence[VectorId]] = None,
    previous_chunk_count: Optional[int] = None,
    prior_vector_id: Optional[VectorId] = None,
    max_chunks: Optional[int] = None,
) -> List[VectorId]:
    """
    Build a deduplicated delete candidate list.

    Prefers stored chunk ids, then prior vector id, parent id, and bounded chunk suffixes.
    """
    limit = max_chunks if max_chunks is not None else get_max_chunk_cleanup()
    seen: set[str] = set()
    ordered: List[VectorId] = []

    def add(value: Optional[VectorId]) -> None:
        if value is None:
            return
        key = str(value)
        if key in seen:
            return
        seen.add(key)
        ordered.append(value)

    if stored_chunk_ids:
        for value in stored_chunk_ids:
            add(value)
        add(prior_vector_id)
        add(parent_doc_id)
        return ordered

    add(prior_vector_id)
    add(parent_doc_id)

    bound = previous_chunk_count if previous_chunk_count and previous_chunk_count > 1 else limit
    bound = min(int(bound), limit)
    for candidate in bounded_chunk_vector_ids(str(parent_doc_id), max_chunks=bound):
        add(candidate)

    return ordered


def _delete_one_vector(vector_search: Any, vector_id: VectorId, *, use_pinecone: bool) -> bool:
    try:
        if use_pinecone:
            return bool(vector_search.delete_document_by_id(str(vector_id)))
        if isinstance(vector_id, int):
            return bool(vector_search.delete_document(vector_id))
        token = str(vector_id)
        if token.isdigit():
            return bool(vector_search.delete_document(int(token)))
        return bool(vector_search.delete_document_by_id(token))
    except Exception as exc:
        logger.warning("Vector delete failed for %s: %s", vector_id, exc)
        return False


def delete_kb_chunk_vectors(
    vector_search: Any,
    parent_doc_id: str,
    *,
    stored_chunk_ids: Optional[Sequence[VectorId]] = None,
    previous_chunk_count: Optional[int] = None,
    prior_vector_id: Optional[VectorId] = None,
    use_pinecone: bool = False,
    max_chunks: Optional[int] = None,
) -> Dict[str, int]:
    """
    Delete parent and chunk vectors for a KB document.

    Never raises; returns counts for observability/tests.
    """
    candidates = collect_chunk_vector_ids(
        str(parent_doc_id),
        stored_chunk_ids=stored_chunk_ids,
        previous_chunk_count=previous_chunk_count,
        prior_vector_id=prior_vector_id,
        max_chunks=max_chunks,
    )

    int_indices: List[int] = []
    other_ids: List[VectorId] = []
    for value in candidates:
        if isinstance(value, int):
            int_indices.append(value)
        elif isinstance(value, str) and value.isdigit():
            int_indices.append(int(value))
        else:
            other_ids.append(value)

    deleted = 0
    errors = 0

    for value in other_ids:
        if _delete_one_vector(vector_search, value, use_pinecone=use_pinecone):
            deleted += 1
        else:
            errors += 1

    for index in sorted(set(int_indices), reverse=True):
        if _delete_one_vector(vector_search, index, use_pinecone=use_pinecone):
            deleted += 1
        else:
            errors += 1

    result = {"deleted": deleted, "errors": errors, "attempted": len(candidates)}
    try:
        from core.durable_jobs import (
            JOB_KIND_KB_CHUNK_CLEANUP,
            build_idempotency_key,
            enqueue_durable_job,
            mark_job_completed,
            mark_job_running,
        )

        idem = build_idempotency_key("kb_cleanup", parent_doc_id, len(candidates))
        jid = enqueue_durable_job(
            JOB_KIND_KB_CHUNK_CLEANUP,
            payload={"doc_id": str(parent_doc_id), "deleted": deleted, "errors": errors},
            idempotency_key=idem,
            external_ref=str(parent_doc_id),
        )
        if jid:
            mark_job_running(jid)
            mark_job_completed(jid, result)
    except Exception:
        pass
    return result


def kb_vector_metadata_fields(vector_ids: Sequence[VectorId], primary_vector_id: Optional[VectorId]) -> Dict[str, Any]:
    """Metadata fields to persist on KB documents after vectorization."""
    ids = list(vector_ids)
    return {
        "vector_id": primary_vector_id,
        "chunk_vector_ids": ids,
        "chunk_count": len(ids),
    }
