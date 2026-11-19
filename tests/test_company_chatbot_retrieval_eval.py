"""Golden retrieval eval for the Fikiri site bot (Phase 6b + deterministic grader)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.eval_cases import load_golden_cases, normalize_golden_case
from company_chatbot.eval_metrics import aggregate_suite_metrics
from company_chatbot.eval_runner import grade_retrieval_case, grade_suite
from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve
from company_chatbot.service_families import chunk_service_families

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

EVAL_PATH = Path(__file__).parent / "company_chatbot_retrieval_eval.yaml"
HIT1_TARGET = 0.85
HIT3_TARGET = 0.95
FAMILY_TARGET = 0.90


def _load_raw_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


@pytest.fixture(autouse=True)
def reset_kb_cache():
    clear_kb_cache_for_tests()
    yield
    clear_kb_cache_for_tests()


def test_retrieval_eval_hit_rates():
    cases = _load_raw_cases()
    assert 50 <= len(cases) <= 110, f"expected 50-110 eval cases, got {len(cases)}"

    hit1 = 0
    hit3 = 0
    family_hits = 0
    family_cases = 0
    failures: list[str] = []

    for case in cases:
        golden = normalize_golden_case(case)
        result = retrieve(
            golden.query,
            top_k=3,
            previous_query=golden.previous_query,
        )
        actual_ids = [chunk.id for chunk in result.chunks]
        expected = set(golden.expected_ids)

        top1_ok = bool(actual_ids) and actual_ids[0] in expected
        top3_ok = bool(expected & set(actual_ids[:3]))

        if top1_ok:
            hit1 += 1
        if top3_ok:
            hit3 += 1
        else:
            failures.append(
                f"{golden.name}: query={golden.query!r} "
                f"expected_any={sorted(expected)} actual_top3={actual_ids}"
            )
        if not top1_ok and top3_ok:
            failures.append(
                f"{golden.name} hit@3 only: query={golden.query!r} "
                f"expected={sorted(expected)} top1={actual_ids[:1]}"
            )

        expected_families = case.get("expected_families")
        if expected_families:
            family_cases += 1
            actual_families = set(result.service_families)
            for chunk in result.chunks[:3]:
                actual_families.update(chunk_service_families(chunk))
            if set(expected_families) & actual_families:
                family_hits += 1
            else:
                failures.append(
                    f"{golden.name} family miss: query={golden.query!r} "
                    f"expected_families={expected_families} actual={sorted(actual_families)}"
                )

        # Negative contracts (forbidden chunks) when declared.
        forbidden = set(golden.retrieval.forbidden)
        if forbidden & set(actual_ids[:3]):
            failures.append(
                f"{golden.name} forbidden chunk: query={golden.query!r} "
                f"forbidden={sorted(forbidden & set(actual_ids[:3]))} top3={actual_ids}"
            )

    hit1_rate = hit1 / len(cases)
    hit3_rate = hit3 / len(cases)
    family_rate = family_hits / family_cases if family_cases else 1.0

    summary = (
        f"retrieval eval: cases={len(cases)} hit@1={hit1}/{len(cases)} ({hit1_rate:.1%}) "
        f"hit@3={hit3}/{len(cases)} ({hit3_rate:.1%}) "
        f"family={family_hits}/{family_cases} ({family_rate:.1%})"
    )
    print(summary)
    if failures:
        print("failures:\n" + "\n".join(failures[:25]))

    assert hit1_rate >= HIT1_TARGET, summary
    assert hit3_rate >= HIT3_TARGET, summary
    if family_cases:
        assert family_rate >= FAMILY_TARGET, summary
    assert not any("forbidden chunk" in f for f in failures), "\n".join(failures)


def test_deterministic_grader_suite_summary():
    cases = load_golden_cases(_load_raw_cases())
    results = grade_suite(cases, top_k=3)
    summary = aggregate_suite_metrics(results)
    hard_fails = [r for r in results if not r.passed]
    print(
        "grader summary:",
        {k: round(v, 4) if isinstance(v, float) else v for k, v in summary.items()},
    )
    if hard_fails:
        print(
            "grader failures:\n"
            + "\n".join(
                f"{r.evidence.get('name')}: {r.reason} failures={r.failures} "
                f"retrieved={r.evidence.get('retrieved_ids')}"
                for r in hard_fails[:20]
            )
        )
    # Keep gate aligned with Hit@3 target; grader may be slightly stricter on contracts.
    assert summary["pass_rate"] >= HIT3_TARGET, summary
    assert summary.get("hit_at_3", 0.0) >= HIT3_TARGET, summary
    assert summary.get("mrr", 0.0) >= 0.80, summary


def test_company_after_pricing_has_no_pricing_contamination():
    cases = {c["name"]: c for c in _load_raw_cases()}
    graded = grade_retrieval_case(cases["company_after_pricing_followup"], top_k=3)
    assert graded.passed, graded.reason
    assert graded.metrics["forbidden_chunk_rate"] == 0.0
    top3 = (graded.evidence.get("retrieved_ids") or [])[:3]
    assert not any(chunk_id.startswith("pricing_") for chunk_id in top3), top3
