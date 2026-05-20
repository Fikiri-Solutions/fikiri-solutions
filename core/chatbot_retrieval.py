"""
Chatbot retrieval orchestration for the public widget path.

FAQ + knowledge-base + optional vector search, source assembly, and context string building.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.domain.schemas import knowledge_snippet, snippets_to_context_string
from core.feature_flags import get_feature_flags
from core.knowledge_base_system import get_knowledge_base
from core.smart_faq_system import get_smart_faq
from core.vector_search import get_vector_search

logger = logging.getLogger(__name__)

faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()


@dataclass
class RetrievalResult:
    sources: List[Dict[str, Any]]
    snippets: List[Dict[str, Any]]
    context_text: str
    retrieval_confidence: float
    fallback_needed: bool
    source_count: int


def _build_sources(faq_results, kb_results, vector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources = []
    if faq_results and getattr(faq_results, "success", False) and getattr(faq_results, "matches", None):
        for match in faq_results.matches[:3]:
            sources.append({
                "type": "faq",
                "id": match.faq_entry.id,
                "question": match.faq_entry.question,
                "answer": match.faq_entry.answer,
                "confidence": match.confidence,
            })
    if kb_results and getattr(kb_results, "success", False) and getattr(kb_results, "results", None):
        for result in kb_results.results[:3]:
            sources.append({
                "type": "knowledge_base",
                "id": result.document.id,
                "title": result.document.title,
                "content": result.document.content[:200] + "..." if len(result.document.content) > 200 else result.document.content,
                "relevance": result.relevance_score,
            })
    for item in vector_results[:3]:
        sources.append({
            "type": "vector",
            "id": item.get("id") or item.get("metadata", {}).get("id") or item.get("metadata", {}).get("doc_id"),
            "content": (item.get("document") or "")[:200],
            "relevance": item.get("similarity"),
        })
    return sources


def retrieval_metadata(sources: List[Dict[str, Any]]) -> tuple:
    """Return (retrieved_doc_ids, retrieval_scores) from sources. Empty arrays if no retrieval."""
    if not sources:
        return [], []
    doc_ids: List[str] = []
    scores: List[float] = []
    for s in sources:
        doc_id = s.get("id") or (s.get("metadata") or {}).get("document_id") or (s.get("metadata") or {}).get("doc_id")
        doc_ids.append(str(doc_id) if doc_id is not None else "")
        sc = s.get("confidence") or s.get("relevance")
        scores.append(round(float(sc), 4) if sc is not None else 0.0)
    return doc_ids, scores


def retrieval_confidence(sources: List[Dict[str, Any]]) -> float:
    """Average top-k similarity from retriever (FAQ confidence, KB relevance, vector similarity). 0 if no sources."""
    _, scores = retrieval_metadata(sources)
    if not scores:
        return 0.0
    normalized = []
    for s in scores:
        if s <= 1.0:
            normalized.append(s)
        else:
            normalized.append(min(1.0, s / 10.0))
    return round(sum(normalized) / len(normalized), 4)


def _sources_to_snippets(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert _build_sources output to canonical KnowledgeSnippet shape."""
    snippets = []
    for s in sources:
        t = s.get("type", "")
        sid = s.get("id")
        source_id = str(sid) if sid is not None else None
        if t == "faq":
            q, a = s.get("question") or "", s.get("answer") or ""
            content = a or q
            snippets.append(knowledge_snippet("faq", content, question=q, answer=a, source_id=source_id, confidence=s.get("confidence")))
        elif t == "knowledge_base":
            content = s.get("content") or ""
            snippets.append(knowledge_snippet("knowledge_base", content, title=s.get("title"), source_id=source_id, relevance=s.get("relevance")))
        elif t == "vector":
            content = s.get("content") or ""
            snippets.append(knowledge_snippet("vector", content, source_id=source_id, relevance=s.get("relevance")))
        else:
            snippets.append(knowledge_snippet(t, s.get("content", ""), source_id=source_id))
    return snippets


def build_context_text(sources: List[Dict[str, Any]], max_context_chars: Optional[int] = None) -> str:
    """Build prompt context string from retrieval sources (canonical KnowledgeSnippet → string)."""
    raw = snippets_to_context_string(_sources_to_snippets(sources))
    if max_context_chars is None:
        try:
            max_len = int((os.getenv("FIKIRI_CHATBOT_CONTEXT_MAX_CHARS") or "6000").strip() or "6000")
        except ValueError:
            max_len = 6000
    else:
        max_len = max_context_chars
    if max_len <= 0:
        max_len = 6000
    if len(raw) <= max_len:
        return raw
    return raw[: max(0, max_len - 25)] + "\n...[context truncated]"


def retrieve_chatbot_context(
    query: str,
    tenant_id: Optional[str],
    user_id: Optional[int],
    *,
    vector_enabled: bool = True,
    max_context_chars: Optional[int] = None,
) -> RetrievalResult:
    """
    Run FAQ, KB, and optional vector retrieval; assemble sources and context for the LLM.
    """
    faq_results = faq_system.search_faqs(query, max_results=3, user_id=user_id)

    kb_filters: Dict[str, Any] = {}
    if tenant_id:
        kb_filters["tenant_id"] = tenant_id
    kb_results = knowledge_base.search(query, filters=kb_filters, limit=3)

    vector_results: List[Dict[str, Any]] = []
    if vector_enabled:
        flags = get_feature_flags()
        if flags.is_enabled("vector_search"):
            try:
                vector_results = get_vector_search().search_similar(
                    query,
                    top_k=3,
                    threshold=0.6,
                    tenant_id=tenant_id,
                )
            except Exception as vector_error:
                logger.warning("Vector search failed: %s", vector_error)

    sources = _build_sources(faq_results, kb_results, vector_results)
    snippets = _sources_to_snippets(sources)
    context_text = build_context_text(sources, max_context_chars=max_context_chars)
    fallback_needed = not bool(context_text.strip())
    ret_conf = retrieval_confidence(sources)

    return RetrievalResult(
        sources=sources,
        snippets=snippets,
        context_text=context_text,
        retrieval_confidence=ret_conf,
        fallback_needed=fallback_needed,
        source_count=len(sources),
    )
