"""Golden retrieval eval for the Fikiri site bot (Phase 6b)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve
from company_chatbot.service_families import chunk_service_families

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

EVAL_PATH = Path(__file__).parent / "company_chatbot_retrieval_eval.yaml"
HIT1_TARGET = 0.85
HIT3_TARGET = 0.95
FAMILY_TARGET = 0.90


def _load_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


@pytest.fixture(autouse=True)
def reset_kb_cache():
    clear_kb_cache_for_tests()
    yield
    clear_kb_cache_for_tests()


def test_retrieval_eval_hit_rates():
    cases = _load_cases()
    assert 50 <= len(cases) <= 95, f"expected 50-95 eval cases, got {len(cases)}"

    hit1 = 0
    hit3 = 0
    family_hits = 0
    family_cases = 0
    failures: list[str] = []

    for case in cases:
        result = retrieve(
            case["query"],
            top_k=3,
            previous_query=case.get("previous_query"),
        )
        actual_ids = [chunk.id for chunk in result.chunks]
        expected = set(case["expected_ids"])

        top1_ok = bool(actual_ids) and actual_ids[0] in expected
        top3_ok = bool(expected & set(actual_ids[:3]))

        if top1_ok:
            hit1 += 1
        if top3_ok:
            hit3 += 1
        else:
            failures.append(
                f"{case['name']}: query={case['query']!r} "
                f"expected_any={sorted(expected)} actual_top3={actual_ids}"
            )
        if not top1_ok and top3_ok:
            failures.append(
                f"{case['name']} hit@3 only: query={case['query']!r} "
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
                    f"{case['name']} family miss: query={case['query']!r} "
                    f"expected_families={expected_families} actual={sorted(actual_families)}"
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
