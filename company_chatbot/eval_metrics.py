"""Deterministic retrieval/response metrics — no embeddings, no LLM judges."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set


FAILURE_NORMALIZATION = "NORMALIZATION_FAILURE"
FAILURE_MODE = "MODE_FAILURE"
FAILURE_CONTEXT = "CONTEXT_FAILURE"
FAILURE_RETRIEVAL_MISS = "RETRIEVAL_MISS"
FAILURE_RANKING = "RANKING_FAILURE"
FAILURE_COVERAGE_HOLE = "COVERAGE_HOLE"
FAILURE_COMPOSITION = "COMPOSITION_FAILURE"
FAILURE_POLICY = "POLICY_FAILURE"
FAILURE_FALLBACK = "FALLBACK_FAILURE"
FAILURE_TURN_CONTAMINATION = "TURN_CONTAMINATION"
FAILURE_UNKNOWN = "UNKNOWN"


def hit_at_k(retrieved_ids: Sequence[str], expected_ids: Iterable[str], k: int) -> float:
    expected = set(expected_ids)
    if not expected:
        return 1.0
    top = list(retrieved_ids)[: max(k, 0)]
    return 1.0 if expected & set(top) else 0.0


def mean_reciprocal_rank(retrieved_ids: Sequence[str], expected_ids: Iterable[str]) -> float:
    expected = set(expected_ids)
    if not expected:
        return 1.0
    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            return 1.0 / float(index)
    return 0.0


def id_precision_at_k(retrieved_ids: Sequence[str], expected_ids: Iterable[str], k: int) -> float:
    expected = set(expected_ids)
    top = list(retrieved_ids)[: max(k, 0)]
    if not top:
        return 1.0 if not expected else 0.0
    hits = sum(1 for chunk_id in top if chunk_id in expected)
    return hits / float(len(top))


def id_recall_at_k(retrieved_ids: Sequence[str], expected_ids: Iterable[str], k: int) -> float:
    expected = set(expected_ids)
    if not expected:
        return 1.0
    top = set(list(retrieved_ids)[: max(k, 0)])
    return len(expected & top) / float(len(expected))


def set_precision(actual: Iterable[str], expected: Iterable[str]) -> float:
    actual_set = set(actual)
    expected_set = set(expected)
    if not actual_set:
        return 1.0 if not expected_set else 0.0
    return len(actual_set & expected_set) / float(len(actual_set))


def set_recall(actual: Iterable[str], expected: Iterable[str]) -> float:
    expected_set = set(expected)
    if not expected_set:
        return 1.0
    return len(set(actual) & expected_set) / float(len(expected_set))


def forbidden_hit_rate(retrieved_ids: Sequence[str], forbidden_ids: Iterable[str], k: int = 3) -> float:
    forbidden = set(forbidden_ids)
    if not forbidden:
        return 0.0
    top = list(retrieved_ids)[: max(k, 0)]
    if not top:
        return 0.0
    return sum(1 for chunk_id in top if chunk_id in forbidden) / float(len(top))


def contamination_rate(
    retrieved_ids: Sequence[str],
    *,
    previous_topic_ids: Iterable[str],
    current_is_standalone: bool,
    k: int = 3,
) -> float:
    """Share of top-k that belong to the previous turn's topic when current is standalone."""
    if not current_is_standalone:
        return 0.0
    prior = set(previous_topic_ids)
    if not prior:
        return 0.0
    top = list(retrieved_ids)[: max(k, 0)]
    if not top:
        return 0.0
    return sum(1 for chunk_id in top if chunk_id in prior) / float(len(top))


def noise_rate(retrieved_ids: Sequence[str], relevant_ids: Iterable[str], k: int = 3) -> float:
    relevant = set(relevant_ids)
    top = list(retrieved_ids)[: max(k, 0)]
    if not top:
        return 0.0
    return sum(1 for chunk_id in top if chunk_id not in relevant) / float(len(top))


@dataclass
class GradingResult:
    """Promptfoo-style grading result, simplified for deterministic Fikiri evals."""

    pass_: bool
    score: float
    failures: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, object] = field(default_factory=dict)
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.pass_


def classify_retrieval_failure(
    *,
    retrieved_ids: Sequence[str],
    required_ids: Sequence[str],
    forbidden_ids: Sequence[str] = (),
    corpus_ids: Optional[Set[str]] = None,
    contamination: float = 0.0,
    mode_ok: bool = True,
    context_ok: bool = True,
    k: int = 3,
) -> List[str]:
    """Return ordered failure labels for a single graded turn."""
    failures: List[str] = []
    required = list(required_ids)
    retrieved = list(retrieved_ids)
    top_k = retrieved[:k]
    top_set = set(top_k)

    if not mode_ok:
        failures.append(FAILURE_MODE)
    if not context_ok:
        failures.append(FAILURE_CONTEXT)
    if contamination > 0:
        failures.append(FAILURE_TURN_CONTAMINATION)

    forbidden = set(forbidden_ids)
    if forbidden & top_set:
        failures.append(FAILURE_POLICY)

    if required:
        any_required_in_top = any(chunk_id in top_set for chunk_id in required)
        any_required_anywhere = any(chunk_id in retrieved for chunk_id in required)
        missing_from_corpus = []
        if corpus_ids is not None:
            missing_from_corpus = [chunk_id for chunk_id in required if chunk_id not in corpus_ids]
        if missing_from_corpus and not any_required_anywhere:
            failures.append(FAILURE_COVERAGE_HOLE)
        elif not any_required_anywhere:
            failures.append(FAILURE_RETRIEVAL_MISS)
        elif not any_required_in_top:
            failures.append(FAILURE_RANKING)
        elif required and required[0] not in (retrieved[:1] or [None]):
            # Diagnostic only: primary required id not ranked #1 (still may pass Hit@k).
            pass

    return failures


def aggregate_suite_metrics(results: Sequence[GradingResult]) -> Dict[str, float]:
    if not results:
        return {"cases": 0.0, "pass_rate": 1.0}
    n = float(len(results))
    metric_sums: Dict[str, float] = {}
    metric_counts: Dict[str, int] = {}
    for result in results:
        for key, value in result.metrics.items():
            metric_sums[key] = metric_sums.get(key, 0.0) + float(value)
            metric_counts[key] = metric_counts.get(key, 0) + 1
    summary = {
        "cases": n,
        "pass_rate": sum(1 for result in results if result.passed) / n,
    }
    for key, total in metric_sums.items():
        summary[key] = total / float(metric_counts[key])
    return summary
