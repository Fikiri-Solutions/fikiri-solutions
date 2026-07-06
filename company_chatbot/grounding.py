"""Grounding gate and evidence-first answer composition."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Sequence

from company_chatbot import config
from company_chatbot.retrieval import KBChunk, RetrievalResult, is_standalone_topic_query, retrieve
from company_chatbot.capabilities import (
    NeedsDetectionResult,
    compose_capability_bridge,
    detect_needs,
    should_use_capability_bridge,
)
from company_chatbot.service_families import (
    FAMILY_BOUNDARIES,
    FAMILY_WORKFLOW_AUDIT,
    compose_bridge_response,
    compose_disambiguation,
    families_in_chunks,
    infer_service_families,
)

_SENSITIVE_TOPIC_PATTERNS = {
    "case_study": re.compile(r"\bcase stud(y|ies)\b", re.I),
    "hipaa": re.compile(r"\bhipaa\b", re.I),
    "soc2": re.compile(r"\bsoc\s*2\b", re.I),
    "guarantee": re.compile(r"\bguarantee\b|\bmoney[- ]back\b", re.I),
}

_NO_EVIDENCE_RESPONSE = (
    "I don't have enough verified information on our site to answer that confidently. "
    "You can reach us at info@fikirisolutions.com or visit fikirisolutions.com/contact."
)

_VAGUE_PAIN_RE = re.compile(
    r"\b(i need help|can this help|can you help|not sure|something that)\b",
    re.I,
)


@dataclass
class GroundingResult:
    grounded: bool
    response: str
    confidence: float
    sources: List[Dict] = field(default_factory=list)
    reason: str = ""

    @property
    def success(self) -> bool:
        return self.grounded


@lru_cache(maxsize=1)
def _forbidden_terms() -> tuple:
    profile_path = config.kb_data_dir() / "fikiri_company_profile.json"
    if not profile_path.is_file():
        return tuple()
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    terms = data.get("forbidden_unless_in_kb") or []
    return tuple(str(term).lower() for term in terms)


def clear_grounding_cache_for_tests() -> None:
    _forbidden_terms.cache_clear()


def _sensitive_topics_in_query(query: str) -> List[str]:
    return [name for name, pattern in _SENSITIVE_TOPIC_PATTERNS.items() if pattern.search(query)]


def _evidence_supports_sensitive_topics(query: str, chunks: Sequence[KBChunk]) -> bool:
    topics = _sensitive_topics_in_query(query)
    if not topics:
        return True
    evidence = " ".join(chunk.text.lower() for chunk in chunks)
    for term in _forbidden_terms():
        if term in query.lower() and term not in evidence:
            return False
    return not topics


def _compose_from_chunks(chunks: Sequence[KBChunk]) -> str:
    if not chunks:
        return ""
    primary = chunks[0].text.strip()
    if len(chunks) == 1:
        return primary
    extra = chunks[1].text.strip()
    return f"{primary} {extra}"


def _confidence_from_score(score: float) -> float:
    return round(min(1.0, max(0.0, score)), 4)


def _needs_from_result(query: str, result: RetrievalResult) -> NeedsDetectionResult:
    if result.needs:
        return NeedsDetectionResult(
            query=result.query,
            detected_families=list(result.needs.get("detected_families") or []),
            detected_capabilities=list(result.needs.get("detected_capabilities") or []),
            suggested_bundle=result.needs.get("suggested_bundle"),
            suggested_bundle_label=result.needs.get("suggested_bundle_label"),
            confidence=float(result.needs.get("confidence") or 0.0),
            kb_chunk_ids=list(result.needs.get("kb_chunk_ids") or []),
            disambiguation_question=result.needs.get("disambiguation_question"),
        )
    return detect_needs(query, effective_query=result.query)


def _should_capability_bridge(query: str, result: RetrievalResult) -> bool:
    needs = _needs_from_result(query, result)
    return should_use_capability_bridge(needs) and len(needs.detected_families) >= 2


def _should_bridge(query: str, result: RetrievalResult) -> bool:
    if _should_capability_bridge(query, result):
        return True
    if result.ambiguous_families and len(result.chunks) >= 2:
        return True
    families = families_in_chunks(result.chunks[:3])
    operational = [f for f in families if f not in {FAMILY_BOUNDARIES, FAMILY_WORKFLOW_AUDIT}]
    if len(operational) >= 2 and result.best_score >= config.grounding_min_score():
        inferred = infer_service_families(query.lower())
        if len(inferred) >= 2:
            return True
    return False


def _should_disambiguate(query: str, result: RetrievalResult) -> bool:
    if result.chunks and result.best_score >= config.grounding_min_score():
        return False
    if _VAGUE_PAIN_RE.search(query) and not result.chunks:
        return True
    inferred = infer_service_families(query.lower())
    return len(inferred) >= 3 and result.best_score < config.grounding_min_score()


def apply_grounding(query: str, retrieval: RetrievalResult | None = None) -> GroundingResult:
    result = retrieval or retrieve(query)
    min_score = config.grounding_min_score()

    if _sensitive_topics_in_query(query) and not _evidence_supports_sensitive_topics(query, result.chunks):
        return GroundingResult(
            grounded=False,
            response=_NO_EVIDENCE_RESPONSE,
            confidence=0.0,
            sources=[],
            reason="sensitive_topic_without_evidence",
        )

    if _should_disambiguate(query, result):
        return GroundingResult(
            grounded=True,
            response=compose_disambiguation(),
            confidence=0.35,
            sources=result.source_dicts(),
            reason="disambiguation",
        )

    if result.best_score < min_score:
        return GroundingResult(
            grounded=False,
            response=_NO_EVIDENCE_RESPONSE,
            confidence=_confidence_from_score(result.best_score),
            sources=result.source_dicts(),
            reason="below_grounding_threshold",
        )

    if _should_bridge(query, result):
        needs = _needs_from_result(query, result)
        if _should_capability_bridge(query, result) and not is_standalone_topic_query(query):
            response = compose_capability_bridge(needs, result.chunks[:2])
            reason = "capability_bridge"
        else:
            families = result.service_families or families_in_chunks(result.chunks[:3])
            response = compose_bridge_response(query, result.chunks[:2], families)
            reason = "bridge_multi_family"
        return GroundingResult(
            grounded=True,
            response=response,
            confidence=_confidence_from_score(result.best_score),
            sources=result.source_dicts(),
            reason=reason,
        )

    response = _compose_from_chunks(result.chunks)
    return GroundingResult(
        grounded=True,
        response=response,
        confidence=_confidence_from_score(result.best_score),
        sources=result.source_dicts(),
        reason="evidence_match",
    )
