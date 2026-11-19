"""Deterministic adversarial / metamorphic mutations — no LLM paraphrasing."""

from __future__ import annotations

import re
from typing import List, Sequence

from company_chatbot.context_dependency import detect_context_dependency
from company_chatbot.eval_cases import GoldenCase, normalize_golden_case
from company_chatbot.eval_metrics import GradingResult, hit_at_k
from company_chatbot.eval_runner import grade_retrieval_case


_TYPO_SWAPS = (
    ("assistant", "assisant"),
    ("automation", "automtion"),
    ("pricing", "pricng"),
    ("gmail", "gamil"),
    ("outlook", "outlok"),
    ("products", "producsts"),
)

_FILLERS = (
    "hey so basically I was wondering: {q}",
    "okay quick question — {q}",
    "um like {q}",
    "please, {q}",
    "actually just {q}",
)

_POLITE = (
    "Could you tell me {q}",
    "Can you explain {q}",
    "I'd like to know {q}",
)


def mutate_query(query: str) -> List[str]:
    """Generate a bounded set of deterministic surface variants for one query."""
    q = (query or "").strip()
    if not q:
        return []
    variants = {
        q,
        q.lower(),
        q.upper(),
        q.rstrip("?.!"),
        q.replace(" ", "-") if " " in q else q,
        re.sub(r"[?.!]+$", "", q) + "?",
    }
    lowered = q.lower()
    for old, new in _TYPO_SWAPS:
        if old in lowered:
            variants.add(re.sub(re.escape(old), new, q, count=1, flags=re.I))
    if lowered.startswith("do you"):
        variants.add(re.sub(r"^do you\b", "do y'all", q, count=1, flags=re.I))
        variants.add(re.sub(r"^do you\b", "do u", q, count=1, flags=re.I))
        variants.add(re.sub(r"^do you\b", "do you guys", q, count=1, flags=re.I))
    for template in _FILLERS:
        variants.add(template.format(q=q))
    bare = q[0].lower() + q[1:] if len(q) > 1 else q.lower()
    for template in _POLITE:
        variants.add(template.format(q=bare))
    ordered = [q] + sorted(v for v in variants if v != q)
    return ordered[:24]


def expand_case_mutations(case: GoldenCase | dict, *, max_variants: int = 12) -> List[GoldenCase]:
    golden = case if isinstance(case, GoldenCase) else normalize_golden_case(case)
    out: List[GoldenCase] = []
    for variant in mutate_query(golden.query)[:max_variants]:
        raw = dict(golden.raw or {})
        raw["name"] = f"{golden.name}__mut_{len(out)}"
        raw["query"] = variant
        if golden.previous_query is not None:
            raw["previous_query"] = golden.previous_query
        # ISR must not weaken assertions — keep retrieval/mode/forbidden contracts.
        # Context-dependency labels are scored separately (polite wrappers break cue anchors).
        raw.pop("context_dependency", None)
        if isinstance(raw.get("expected"), dict):
            expected = dict(raw["expected"])
            expected.pop("context_dependency", None)
            raw["expected"] = expected
        mutated = normalize_golden_case(raw)
        out.append(mutated)
    return out


def _retrieval_intent_ok(graded: GradingResult, golden: GoldenCase, top_k: int) -> bool:
    retrieved = list(graded.evidence.get("retrieved_ids") or [])
    positive = golden.retrieval.positive_ids
    if positive and hit_at_k(retrieved, positive, top_k) < 1.0:
        return False
    forbidden = set(golden.retrieval.forbidden)
    if forbidden & set(retrieved[:top_k]):
        return False
    # Mode contract only when an observed mode was supplied on the base case.
    if graded.metrics.get("mode_correct", 1.0) < 1.0:
        return False
    return True


def intent_stability_rate(
    case: GoldenCase | dict,
    *,
    max_variants: int = 12,
    top_k: int = 3,
) -> GradingResult:
    """Primary ISR = retrieval/mode stability. Context labels reported separately."""
    golden = case if isinstance(case, GoldenCase) else normalize_golden_case(case)
    variants = expand_case_mutations(case, max_variants=max_variants)
    results = [grade_retrieval_case(variant, top_k=top_k) for variant in variants]

    retrieval_flags = [_retrieval_intent_ok(result, golden, top_k) for result in results]
    retrieval_rate = (
        sum(1 for ok in retrieval_flags if ok) / float(len(retrieval_flags)) if retrieval_flags else 1.0
    )

    expected_dep = golden.context_dependency
    label_flags: List[bool] = []
    if expected_dep:
        for variant in variants:
            actual = detect_context_dependency(variant.query, variant.previous_query).value
            label_flags.append(actual == expected_dep.lower())
    label_rate = (
        sum(1 for ok in label_flags if ok) / float(len(label_flags)) if label_flags else 1.0
    )

    return GradingResult(
        pass_=retrieval_rate >= 0.9,
        score=round(retrieval_rate, 4),
        failures=[] if retrieval_rate >= 0.9 else ["MUTATION_INSTABILITY"],
        metrics={
            "intent_stability_rate": retrieval_rate,
            "context_label_stability_rate": label_rate,
            "mutation_count": float(len(results)),
            "hit_at_3": sum(r.metrics.get("hit_at_3", 0.0) for r in results) / max(len(results), 1),
            "forbidden_chunk_rate": sum(
                r.metrics.get("forbidden_chunk_rate", 0.0) for r in results
            )
            / max(len(results), 1),
        },
        evidence={
            "base_name": golden.name,
            "variant_results": [
                {
                    "name": result.evidence.get("name"),
                    "query": result.evidence.get("query"),
                    "retrieval_ok": retrieval_ok,
                    "failures": result.failures,
                    "retrieved_ids": result.evidence.get("retrieved_ids"),
                }
                for result, retrieval_ok in zip(results, retrieval_flags)
            ],
            "context_label_expected": expected_dep,
        },
        reason=(
            f"ISR(retrieval)={retrieval_rate:.3f} "
            f"label_stability={label_rate:.3f} over {len(results)} variants"
        ),
    )


def suite_mutation_stability(
    cases: Sequence[GoldenCase | dict],
    *,
    case_limit: int = 8,
    max_variants: int = 8,
) -> GradingResult:
    """Sample high-signal cases and report aggregate retrieval ISR."""
    sample = list(cases)[:case_limit]
    per_case = [intent_stability_rate(case, max_variants=max_variants) for case in sample]
    if not per_case:
        return GradingResult(pass_=True, score=1.0, reason="no cases")
    avg = sum(r.metrics.get("intent_stability_rate", 0.0) for r in per_case) / float(len(per_case))
    label_avg = sum(
        r.metrics.get("context_label_stability_rate", 1.0) for r in per_case
    ) / float(len(per_case))
    return GradingResult(
        pass_=avg >= 0.9,
        score=round(avg, 4),
        failures=[] if avg >= 0.9 else ["MUTATION_INSTABILITY"],
        metrics={
            "intent_stability_rate": avg,
            "context_label_stability_rate": label_avg,
            "cases_sampled": float(len(per_case)),
        },
        evidence={"per_case": [{"score": r.score, "reason": r.reason} for r in per_case]},
        reason=f"suite ISR(retrieval)={avg:.3f} label_stability={label_avg:.3f}",
    )
