"""Deterministic golden-case grader (component / retrieval layer)."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set

from company_chatbot.context_dependency import ContextDependency, detect_context_dependency
from company_chatbot.eval_cases import GoldenCase, normalize_golden_case
from company_chatbot.eval_metrics import (
    GradingResult,
    classify_retrieval_failure,
    contamination_rate,
    forbidden_hit_rate,
    hit_at_k,
    id_precision_at_k,
    id_recall_at_k,
    mean_reciprocal_rank,
    noise_rate,
    set_precision,
    set_recall,
)
from company_chatbot.retrieval import load_kb_chunks, retrieve


def _family_for_id(chunk_id: str, family_index: Dict[str, Set[str]]) -> Set[str]:
    return family_index.get(chunk_id, set())


def build_family_index() -> Dict[str, Set[str]]:
    index: Dict[str, Set[str]] = {}
    for chunk in load_kb_chunks():
        families = set(getattr(chunk, "service_families", None) or [])
        if getattr(chunk, "topic", None):
            families.add(str(chunk.topic).lower())
        index[chunk.id] = families
    return index


def _corpus_ids() -> Set[str]:
    return {chunk.id for chunk in load_kb_chunks()}


def grade_retrieval_case(
    case: GoldenCase | dict,
    *,
    top_k: int = 3,
    family_index: Optional[Dict[str, Set[str]]] = None,
    corpus_ids: Optional[Set[str]] = None,
) -> GradingResult:
    golden = case if isinstance(case, GoldenCase) else normalize_golden_case(case)
    family_index = family_index or build_family_index()
    corpus_ids = corpus_ids or _corpus_ids()

    result = retrieve(golden.query, top_k=max(top_k, 5), previous_query=golden.previous_query)
    retrieved_ids = [chunk.id for chunk in result.chunks]
    top_ids = retrieved_ids[:top_k]

    positive = golden.retrieval.positive_ids
    required = golden.retrieval.required or positive
    relevant = set(positive) | set(golden.retrieval.acceptable)

    hit1 = hit_at_k(retrieved_ids, positive, 1)
    hit3 = hit_at_k(retrieved_ids, positive, 3)
    mrr = mean_reciprocal_rank(retrieved_ids, positive)
    id_p = id_precision_at_k(retrieved_ids, positive, top_k)
    id_r = id_recall_at_k(retrieved_ids, required or positive, top_k)

    retrieved_families: Set[str] = set()
    for chunk_id in top_ids:
        retrieved_families |= _family_for_id(chunk_id, family_index)
    family_recall = set_recall(retrieved_families, golden.families.required) if golden.families.required else 1.0
    family_precision = (
        set_precision(retrieved_families, golden.families.required) if golden.families.required else 1.0
    )

    detected_dep = detect_context_dependency(golden.query, golden.previous_query)
    context_ok = True
    if golden.context_dependency:
        context_ok = detected_dep.value == golden.context_dependency.lower()

    # Contamination: previous-topic docs in top-k when current is standalone.
    previous_topic_ids: List[str] = []
    if golden.previous_query:
        # Approximate previous topic from first retrieval under previous query alone.
        prior = retrieve(golden.previous_query, top_k=3, previous_query=None)
        previous_topic_ids = [chunk.id for chunk in prior.chunks]
    contam = contamination_rate(
        retrieved_ids,
        previous_topic_ids=previous_topic_ids,
        current_is_standalone=detected_dep == ContextDependency.STANDALONE,
        k=top_k,
    )
    # Also count explicit forbidden IDs as contamination when tagged.
    forbid_rate = forbidden_hit_rate(retrieved_ids, golden.retrieval.forbidden, k=top_k)

    mode_ok = True  # retrieval suite does not invoke modes unless expected set with fixture
    # Mode contracts are scored when the caller supplies observed_mode via evidence overlay.
    observed_mode = None
    if isinstance(golden.raw.get("observed_mode"), str):
        observed_mode = golden.raw["observed_mode"]
    if golden.mode.expected and observed_mode is not None:
        mode_ok = observed_mode == golden.mode.expected
    if observed_mode and golden.mode.forbidden and observed_mode in golden.mode.forbidden:
        mode_ok = False

    forbidden_family_hit = bool(set(golden.families.forbidden) & retrieved_families)

    # Contamination hard-fails only when the case opts in via tag (shared chunks across
    # related topics are not automatically "bleed").
    contam_opt_in = "turn_contamination" in golden.tags
    contam_signal = contam if contam_opt_in else 0.0
    if forbid_rate > 0 and contam_opt_in:
        contam_signal = max(contam_signal, forbid_rate)

    failures = classify_retrieval_failure(
        retrieved_ids=retrieved_ids,
        required_ids=required,
        forbidden_ids=golden.retrieval.forbidden,
        corpus_ids=corpus_ids,
        contamination=contam_signal,
        mode_ok=mode_ok,
        context_ok=context_ok,
        k=top_k,
    )
    if forbidden_family_hit and "POLICY_FAILURE" not in failures:
        failures.append("POLICY_FAILURE")

    # Hard gate: required IDs must appear in top_k (legacy behavior).
    required_ok = True
    if golden.retrieval.required:
        required_ok = bool(set(golden.retrieval.required) & set(top_ids))
    elif positive:
        required_ok = bool(set(positive) & set(top_ids))
    forbidden_ok = not (set(golden.retrieval.forbidden) & set(top_ids))
    family_ok = True
    if golden.families.required:
        # Legacy expected_families is OR (any match), matching the golden suite.
        family_ok = bool(set(golden.families.required) & retrieved_families)
    if golden.families.forbidden and forbidden_family_hit:
        family_ok = False

    contam_ok = True
    if contam_opt_in and golden.previous_query and contam > 0:
        contam_ok = False
    if golden.retrieval.forbidden and not forbidden_ok:
        contam_ok = False

    passed = required_ok and forbidden_ok and family_ok and context_ok and mode_ok and contam_ok
    if not passed and not failures:
        failures.append("UNKNOWN")

    score_parts = [hit1, hit3, mrr, id_p, id_r, family_recall]
    score = sum(score_parts) / float(len(score_parts))
    if not passed:
        score = min(score, 0.99)

    reason_bits = []
    if not required_ok:
        reason_bits.append("required_ids_miss")
    if not forbidden_ok:
        reason_bits.append("forbidden_ids_hit")
    if not family_ok:
        reason_bits.append(
            f"family_miss expected_any={golden.families.required} got={sorted(retrieved_families)}"
        )
    if not context_ok:
        reason_bits.append(
            f"context_dependency expected={golden.context_dependency} got={detected_dep.value}"
        )
    if contam > 0:
        reason_bits.append(f"contamination={contam:.2f}")
    if not failures and passed:
        reason_bits.append("ok")

    return GradingResult(
        pass_=passed,
        score=round(score, 4),
        failures=failures,
        metrics={
            "hit_at_1": hit1,
            "hit_at_3": hit3,
            "mrr": mrr,
            "id_precision_at_k": id_p,
            "id_recall_at_k": id_r,
            "family_recall": family_recall,
            "family_precision": family_precision,
            "contamination_rate": contam,
            "forbidden_chunk_rate": forbid_rate,
            "noise_rate": noise_rate(retrieved_ids, relevant or positive, k=top_k),
            "context_dependency_correct": 1.0 if context_ok else 0.0,
            "mode_correct": 1.0 if mode_ok else 0.0,
        },
        evidence={
            "name": golden.name,
            "query": golden.query,
            "previous_query": golden.previous_query,
            "expected_ids": positive,
            "required_ids": golden.retrieval.required,
            "forbidden_ids": golden.retrieval.forbidden,
            "retrieved_ids": retrieved_ids[: max(top_k, 5)],
            "context_dependency_expected": golden.context_dependency,
            "context_dependency_actual": detected_dep.value,
            "failures": failures,
        },
        reason="; ".join(reason_bits) or ("pass" if passed else "fail"),
    )


def grade_suite(
    cases: Iterable[GoldenCase | dict],
    *,
    top_k: int = 3,
) -> List[GradingResult]:
    family_index = build_family_index()
    corpus_ids = _corpus_ids()
    return [
        grade_retrieval_case(case, top_k=top_k, family_index=family_index, corpus_ids=corpus_ids)
        for case in cases
    ]
