"""
Cross-source deduplication for chatbot retrieval.

Collapses duplicate KB keyword and vector hits that refer to the same document
while preserving FAQ priority and deterministic ordering.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

DEFAULT_STRONG_VECTOR_SCORE_GAP = 0.15

_SOURCE_TYPE_RANK = {
    "faq": 0,
    "knowledge_base": 1,
    "vector": 2,
}


def get_strong_vector_score_gap() -> float:
    raw = (os.getenv("FIKIRI_CHATBOT_STRONG_VECTOR_SCORE_GAP") or str(DEFAULT_STRONG_VECTOR_SCORE_GAP)).strip()
    try:
        return max(0.0, min(float(raw), 1.0))
    except ValueError:
        return DEFAULT_STRONG_VECTOR_SCORE_GAP


def _normalize_identity_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def _normalize_title_label(title: Any) -> Optional[str]:
    normalized = _normalize_identity_value(title)
    if not normalized:
        return None
    return re.sub(r"[^\w\s-]", "", normalized).strip()


def source_identity_keys(source: Dict[str, Any]) -> List[str]:
    """Stable identity keys for cross-source deduplication."""
    keys: List[str] = []
    source_id = _normalize_identity_value(source.get("id"))
    if source_id:
        keys.append(f"id:{source_id}")

    source_type = source.get("type")
    if source_type == "knowledge_base" and not source_id:
        title_key = _normalize_title_label(source.get("title"))
        if title_key:
            keys.append(f"title:{title_key}")

    return keys


def _source_score(source: Dict[str, Any]) -> float:
    if source.get("type") == "faq":
        raw = source.get("confidence")
    else:
        raw = source.get("relevance")
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _source_type_rank(source: Dict[str, Any]) -> int:
    return _SOURCE_TYPE_RANK.get(str(source.get("type") or ""), 99)


def _prefer_source(
    existing: Dict[str, Any],
    candidate: Dict[str, Any],
    *,
    strong_vector_gap: float,
) -> Dict[str, Any]:
    existing_rank = _source_type_rank(existing)
    candidate_rank = _source_type_rank(candidate)

    if existing_rank < candidate_rank:
        if (
            existing.get("type") == "knowledge_base"
            and candidate.get("type") == "vector"
            and (_source_score(candidate) - _source_score(existing)) >= strong_vector_gap
        ):
            return candidate
        return existing

    if candidate_rank < existing_rank:
        if (
            candidate.get("type") == "knowledge_base"
            and existing.get("type") == "vector"
            and (_source_score(existing) - _source_score(candidate)) >= strong_vector_gap
        ):
            return existing
        return candidate

    return existing


def deduplicate_cross_source_sources(
    sources: List[Dict[str, Any]],
    *,
    strong_vector_gap: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Remove duplicate sources across FAQ, KB keyword, and vector channels.

    Preserves first-seen order for non-colliding sources. On identity collision,
    keeps FAQ over KB over vector unless vector score strongly exceeds KB.
    """
    if not sources:
        return []

    gap = strong_vector_gap if strong_vector_gap is not None else get_strong_vector_score_gap()
    kept: List[Dict[str, Any]] = []
    key_to_index: Dict[str, int] = {}

    for source in sources:
        keys = source_identity_keys(source)
        if not keys:
            kept.append(source)
            continue

        existing_idx: Optional[int] = None
        for key in keys:
            if key in key_to_index:
                existing_idx = key_to_index[key]
                break

        if existing_idx is None:
            idx = len(kept)
            kept.append(source)
            for key in keys:
                key_to_index[key] = idx
            continue

        existing = kept[existing_idx]
        preferred = _prefer_source(existing, source, strong_vector_gap=gap)
        if preferred is source:
            for old_key in source_identity_keys(existing):
                if key_to_index.get(old_key) == existing_idx:
                    del key_to_index[old_key]
            kept[existing_idx] = source
            for key in keys:
                key_to_index[key] = existing_idx

    return kept
