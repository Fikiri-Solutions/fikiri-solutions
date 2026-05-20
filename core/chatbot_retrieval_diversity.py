"""
Lightweight vector-hit deduplication for chatbot retrieval.

Groups chunked vector results by parent document and limits redundant chunks
before LLM context assembly. Deterministic; no ML reranking.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_VECTOR_FETCH_TOP_K = 12
DEFAULT_MAX_CHUNKS_PER_PARENT = 2
DEFAULT_ADJACENT_CHUNK_SCORE_GAP = 0.08
DEFAULT_VECTOR_RESULT_LIMIT = 3


def get_vector_fetch_top_k() -> int:
    raw = (os.getenv("FIKIRI_CHATBOT_VECTOR_FETCH_TOP_K") or str(DEFAULT_VECTOR_FETCH_TOP_K)).strip()
    try:
        return max(3, min(int(raw), 50))
    except ValueError:
        return DEFAULT_VECTOR_FETCH_TOP_K


def get_max_chunks_per_parent() -> int:
    raw = (os.getenv("FIKIRI_CHATBOT_MAX_CHUNKS_PER_PARENT") or str(DEFAULT_MAX_CHUNKS_PER_PARENT)).strip()
    try:
        return max(1, min(int(raw), 5))
    except ValueError:
        return DEFAULT_MAX_CHUNKS_PER_PARENT


def get_adjacent_chunk_score_gap() -> float:
    raw = (os.getenv("FIKIRI_CHATBOT_ADJACENT_CHUNK_SCORE_GAP") or str(DEFAULT_ADJACENT_CHUNK_SCORE_GAP)).strip()
    try:
        return max(0.0, min(float(raw), 0.5))
    except ValueError:
        return DEFAULT_ADJACENT_CHUNK_SCORE_GAP


def _vector_hit_parent_id(item: Dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    parent = metadata.get("parent_doc_id") or metadata.get("document_id")
    if parent is not None:
        return str(parent)
    hit_id = item.get("id")
    if hit_id is not None:
        return str(hit_id)
    return "unknown"


def _vector_hit_score(item: Dict[str, Any]) -> float:
    try:
        return float(item.get("similarity") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _vector_hit_chunk_index(item: Dict[str, Any]) -> Optional[int]:
    metadata = item.get("metadata") or {}
    index = metadata.get("chunk_index")
    if index is None:
        return None
    try:
        return int(index)
    except (TypeError, ValueError):
        return None


def _select_chunks_for_parent(
    group_hits: List[Dict[str, Any]],
    *,
    max_per_parent: int,
    adjacent_score_gap: float,
) -> List[Dict[str, Any]]:
    if not group_hits:
        return []

    ordered = sorted(
        group_hits,
        key=lambda hit: (-_vector_hit_score(hit), _vector_hit_chunk_index(hit) or 0, str(hit.get("id") or "")),
    )
    kept = [ordered[0]]
    if max_per_parent <= 1 or len(ordered) <= 1:
        return kept

    best = ordered[0]
    best_score = _vector_hit_score(best)
    best_index = _vector_hit_chunk_index(best)

    supporting: List[Tuple[float, int, Dict[str, Any]]] = []
    for candidate in ordered[1:]:
        candidate_score = _vector_hit_score(candidate)
        if (best_score - candidate_score) > adjacent_score_gap:
            continue
        candidate_index = _vector_hit_chunk_index(candidate)
        if best_index is not None and candidate_index is not None:
            if abs(best_index - candidate_index) != 1:
                continue
        supporting.append(
            (
                -candidate_score,
                abs((candidate_index or 0) - (best_index or 0)),
                candidate,
            )
        )

    supporting.sort(key=lambda row: (row[0], row[1], str(row[2].get("id") or "")))
    for _, _, candidate in supporting:
        if len(kept) >= max_per_parent:
            break
        kept.append(candidate)

    kept.sort(
        key=lambda hit: (-_vector_hit_score(hit), _vector_hit_chunk_index(hit) or 0, str(hit.get("id") or ""))
    )
    return kept


def diversify_vector_hits(
    hits: List[Dict[str, Any]],
    *,
    max_per_parent: Optional[int] = None,
    adjacent_score_gap: Optional[float] = None,
    max_results: int = DEFAULT_VECTOR_RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Collapse redundant chunk hits from the same parent document.

    Returns hits ordered by parent best-score desc, then parent_doc_id asc.
    """
    if not hits:
        return []

    per_parent = max_per_parent if max_per_parent is not None else get_max_chunks_per_parent()
    score_gap = (
        adjacent_score_gap if adjacent_score_gap is not None else get_adjacent_chunk_score_gap()
    )
    limit = max(1, int(max_results))

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for hit in hits:
        grouped.setdefault(_vector_hit_parent_id(hit), []).append(hit)

    grouped_selections: List[Tuple[float, str, List[Dict[str, Any]]]] = []
    for parent_id, group_hits in grouped.items():
        selected = _select_chunks_for_parent(
            group_hits,
            max_per_parent=per_parent,
            adjacent_score_gap=score_gap,
        )
        if not selected:
            continue
        grouped_selections.append((max(_vector_hit_score(item) for item in selected), parent_id, selected))

    grouped_selections.sort(key=lambda row: (-row[0], row[1]))

    diversified: List[Dict[str, Any]] = []
    for _, _, selected in grouped_selections:
        diversified.extend(selected)
        if len(diversified) >= limit:
            break

    return diversified[:limit]
