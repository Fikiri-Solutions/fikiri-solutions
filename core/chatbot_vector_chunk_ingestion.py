"""
Vector-store ingestion helpers for chunked chatbot knowledge documents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from core.chatbot_knowledge_chunking import TextChunk, chunk_text, chunk_vector_id
from core.chatbot_vector_chunk_cleanup import delete_kb_chunk_vectors

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
