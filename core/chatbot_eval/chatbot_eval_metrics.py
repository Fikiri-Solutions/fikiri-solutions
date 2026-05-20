"""Scoring metrics for chatbot eval harness (deterministic, no LLM side effects)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.chatbot_eval.chatbot_eval_cases import ChatbotEvalCase

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)


@dataclass
class CaseMetrics:
    retrieval_source_count: int = 0
    retrieval_confidence: float = 0.0
    fallback_used: bool = False
    retrieval_fallback_needed: bool = False
    source_grounding_coverage: float = 0.0
    keyword_hit_rate: float = 0.0
    hallucination_indicators: List[str] = field(default_factory=list)
    hallucination_risk_score: float = 0.0
    latency_ms: int = 0
    retrieved_source_ids: List[str] = field(default_factory=list)
    expected_source_ids_matched: bool = True
    expected_fallback_matched: bool = True
    forbidden_keyword_hits: List[str] = field(default_factory=list)
    passed: bool = False
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _token_set(text: str) -> set:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def keyword_hit_rate(answer: str, expected_keywords: Sequence[str]) -> float:
    if not expected_keywords:
        return 1.0
    answer_l = _normalize_text(answer)
    hits = sum(1 for kw in expected_keywords if _normalize_text(kw) in answer_l)
    return round(hits / len(expected_keywords), 4)


def forbidden_keyword_hits(answer: str, forbidden_keywords: Sequence[str]) -> List[str]:
    answer_l = _normalize_text(answer)
    return [kw for kw in forbidden_keywords if _normalize_text(kw) in answer_l]


def source_grounding_coverage(answer: str, context_text: str) -> float:
    """Share of answer tokens (len>=4) also present in context (simple overlap)."""
    answer_tokens = _token_set(answer)
    if not answer_tokens:
        return 1.0
    context_tokens = _token_set(context_text)
    if not context_tokens:
        return 0.0
    overlap = answer_tokens & context_tokens
    return round(len(overlap) / len(answer_tokens), 4)


def extract_source_ids(sources: Sequence[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    for src in sources or []:
        sid = src.get("id")
        if sid is not None and str(sid).strip():
            ids.append(str(sid).strip())
    return ids


def detect_hallucination_indicators(
    *,
    answer: str,
    context_text: str,
    fallback_used: bool,
    forbidden_hits: Sequence[str],
) -> Tuple[List[str], float]:
    indicators: List[str] = []
    if forbidden_hits:
        indicators.append("forbidden_keyword_present")

    ctx = (context_text or "").strip()
    ans = (answer or "").strip()
    if not ctx and ans and not fallback_used:
        indicators.append("answer_without_retrieval_context")

    if ctx and ans and not fallback_used:
        coverage = source_grounding_coverage(ans, ctx)
        if coverage < 0.15 and len(_token_set(ans)) >= 3:
            indicators.append("low_context_overlap")

    risk = 0.0
    if "forbidden_keyword_present" in indicators:
        risk += 0.6
    if "answer_without_retrieval_context" in indicators:
        risk += 0.5
    if "low_context_overlap" in indicators:
        risk += 0.35
    return indicators, round(min(1.0, risk), 4)


def score_eval_case(
    case: ChatbotEvalCase,
    *,
    answer: str,
    context_text: str,
    sources: Sequence[Dict[str, Any]],
    retrieval_confidence: float,
    fallback_used: bool,
    retrieval_fallback_needed: bool,
    latency_ms: int,
) -> CaseMetrics:
    retrieved_ids = extract_source_ids(sources)
    kw_rate = keyword_hit_rate(answer, case.expected_keywords)
    forb_hits = forbidden_keyword_hits(answer, case.forbidden_keywords)
    grounding = source_grounding_coverage(answer, context_text)
    hallucination_indicators, hallucination_risk = detect_hallucination_indicators(
        answer=answer,
        context_text=context_text,
        fallback_used=fallback_used,
        forbidden_hits=forb_hits,
    )

    failure_reasons: List[str] = []
    expected_fallback_matched = True
    if case.expected_fallback is not None:
        expected_fallback_matched = fallback_used == case.expected_fallback
        if not expected_fallback_matched:
            failure_reasons.append(
                f"expected_fallback={case.expected_fallback} got fallback_used={fallback_used}"
            )

    if case.expected_keywords and kw_rate < 1.0:
        failure_reasons.append(
            f"keyword_hit_rate={kw_rate} expected all keywords {list(case.expected_keywords)}"
        )

    if forb_hits:
        failure_reasons.append(f"forbidden_keywords matched: {forb_hits}")

    expected_source_ids_matched = True
    if case.expected_source_ids:
        missing = [sid for sid in case.expected_source_ids if sid not in retrieved_ids]
        expected_source_ids_matched = not missing
        if missing:
            failure_reasons.append(f"expected_source_ids missing: {missing}")

    if hallucination_indicators:
        failure_reasons.append(f"hallucination_indicators: {hallucination_indicators}")

    passed = not failure_reasons

    return CaseMetrics(
        retrieval_source_count=len(sources or []),
        retrieval_confidence=round(float(retrieval_confidence or 0.0), 4),
        fallback_used=bool(fallback_used),
        retrieval_fallback_needed=bool(retrieval_fallback_needed),
        source_grounding_coverage=grounding,
        keyword_hit_rate=kw_rate,
        hallucination_indicators=list(hallucination_indicators),
        hallucination_risk_score=hallucination_risk,
        latency_ms=int(latency_ms),
        retrieved_source_ids=retrieved_ids,
        expected_source_ids_matched=expected_source_ids_matched,
        expected_fallback_matched=expected_fallback_matched,
        forbidden_keyword_hits=list(forb_hits),
        passed=passed,
        failure_reasons=failure_reasons,
    )
