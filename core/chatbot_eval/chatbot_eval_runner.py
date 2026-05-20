"""Run chatbot eval cases via library pipeline (dev/local; no production routes)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.chatbot_eval.chatbot_eval_cases import ChatbotEvalCase
from core.chatbot_eval.chatbot_eval_metrics import CaseMetrics, score_eval_case

RetrieveFn = Callable[..., Any]
AnswerFn = Callable[..., Any]


@dataclass
class EvalCaseResult:
    case_id: str
    tenant_id: str
    query: str
    notes: str
    answer_preview: str
    passed: bool
    metrics: Dict[str, Any]
    retrieval_debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvalRunReport:
    run_id: str
    generated_at: str
    cases_total: int
    cases_passed: int
    cases_failed: int
    summary_metrics: Dict[str, Any]
    results: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def _default_retrieve(case: ChatbotEvalCase, correlation_id: str) -> Any:
    from core.chatbot_retrieval import retrieve_chatbot_context

    uid = case.resolved_user_id()
    return retrieve_chatbot_context(
        case.query,
        case.tenant_id,
        uid,
        correlation_id=correlation_id,
    )


def _default_answer(
    case: ChatbotEvalCase,
    retrieval: Any,
    *,
    allow_llm: bool,
    correlation_id: str,
) -> Any:
    from core.chatbot_config import load_chatbot_config
    from core.chatbot_response_service import generate_chatbot_answer

    uid = case.resolved_user_id()
    config = load_chatbot_config(uid, tenant_id=case.tenant_id)
    return generate_chatbot_answer(
        case.query,
        retrieval.context_text,
        retrieval.sources,
        tenant_id=case.tenant_id,
        user_id=uid,
        billing_uid=uid,
        fallback_needed=retrieval.fallback_needed,
        allow_llm=allow_llm,
        chatbot_config=config,
        correlation_id=correlation_id,
    )


def run_eval_case(
    case: ChatbotEvalCase,
    *,
    allow_llm: bool = False,
    correlation_id: Optional[str] = None,
    retrieve_fn: Optional[RetrieveFn] = None,
    answer_fn: Optional[AnswerFn] = None,
) -> EvalCaseResult:
    """
    Execute one eval case through retrieve → answer (preview-equivalent library path).

    Default ``allow_llm=False`` for deterministic local runs without billing/LLM calls.
    """
    cid = correlation_id or f"eval-{case.case_id}"
    retrieve = retrieve_fn or _default_retrieve
    answer_builder = answer_fn

    t0 = time.monotonic()
    retrieval = retrieve(case, cid)
    if answer_builder is None:
        answer = _default_answer(case, retrieval, allow_llm=allow_llm, correlation_id=cid)
    else:
        answer = answer_builder(case, retrieval, allow_llm=allow_llm, correlation_id=cid)
    latency_ms = int((time.monotonic() - t0) * 1000)

    metrics = score_eval_case(
        case,
        answer=answer.answer,
        context_text=retrieval.context_text,
        sources=retrieval.sources,
        retrieval_confidence=retrieval.retrieval_confidence,
        fallback_used=answer.fallback_used,
        retrieval_fallback_needed=retrieval.fallback_needed,
        latency_ms=latency_ms,
    )

    preview = (answer.answer or "")[:240]
    return EvalCaseResult(
        case_id=case.case_id,
        tenant_id=case.tenant_id,
        query=case.query,
        notes=case.notes,
        answer_preview=preview,
        passed=metrics.passed,
        metrics=metrics.to_dict(),
        retrieval_debug=dict(retrieval.retrieval_debug or {}),
    )


def _aggregate_summary(results: Sequence[EvalCaseResult]) -> Dict[str, Any]:
    if not results:
        return {
            "avg_keyword_hit_rate": 0.0,
            "avg_retrieval_confidence": 0.0,
            "avg_source_grounding_coverage": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_rate": 0.0,
            "hallucination_case_count": 0,
        }

    n = len(results)
    kw_sum = sum(r.metrics.get("keyword_hit_rate", 0.0) for r in results)
    conf_sum = sum(r.metrics.get("retrieval_confidence", 0.0) for r in results)
    ground_sum = sum(r.metrics.get("source_grounding_coverage", 0.0) for r in results)
    lat_sum = sum(r.metrics.get("latency_ms", 0) for r in results)
    fallback_count = sum(1 for r in results if r.metrics.get("fallback_used"))
    hallucination_count = sum(
        1 for r in results if r.metrics.get("hallucination_indicators")
    )

    return {
        "avg_keyword_hit_rate": round(kw_sum / n, 4),
        "avg_retrieval_confidence": round(conf_sum / n, 4),
        "avg_source_grounding_coverage": round(ground_sum / n, 4),
        "avg_latency_ms": round(lat_sum / n, 2),
        "fallback_rate": round(fallback_count / n, 4),
        "hallucination_case_count": hallucination_count,
    }


def run_eval_suite(
    cases: Sequence[ChatbotEvalCase],
    *,
    allow_llm: bool = False,
    retrieve_fn: Optional[RetrieveFn] = None,
    answer_fn: Optional[AnswerFn] = None,
    preflight_live: bool = False,
    preflight_timeout_sec: float = 45.0,
) -> EvalRunReport:
    """Run all cases and build a JSON-serializable report."""
    if preflight_live and retrieve_fn is None:
        from core.chatbot_eval.live_preflight import (
            live_eval_needs_vector_probe,
            preflight_live_eval_dependencies,
        )

        preflight_live_eval_dependencies(
            timeout_sec=preflight_timeout_sec,
            require_vector=live_eval_needs_vector_probe(),
        )

    results: List[EvalCaseResult] = []
    for case in cases:
        results.append(
            run_eval_case(
                case,
                allow_llm=allow_llm,
                retrieve_fn=retrieve_fn,
                answer_fn=answer_fn,
            )
        )

    results_sorted = sorted(results, key=lambda r: r.case_id)
    passed = sum(1 for r in results_sorted if r.passed)
    total = len(results_sorted)

    return EvalRunReport(
        run_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        cases_total=total,
        cases_passed=passed,
        cases_failed=total - passed,
        summary_metrics=_aggregate_summary(results_sorted),
        results=[r.to_dict() for r in results_sorted],
    )


def write_eval_report(report: EvalRunReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_json(), encoding="utf-8")
    return path
