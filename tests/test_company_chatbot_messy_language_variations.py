"""Messy-language variation matrix — routing + sales qualification on every business phrase."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.capabilities import clear_capability_map_cache_for_tests
from company_chatbot.grounding import clear_grounding_cache_for_tests
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.retrieval import clear_kb_cache_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

VARIATIONS_PATH = Path(__file__).parent / "company_chatbot_messy_language_variations.yaml"
_EMPTY_SYNOPSIS = "not provided enough business context"


def _load_cases():
    data = yaml.safe_load(VARIATIONS_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


@pytest.fixture(autouse=True)
def reset_state():
    clear_sessions_for_tests()
    clear_kb_cache_for_tests()
    clear_capability_map_cache_for_tests()
    clear_grounding_cache_for_tests()
    yield
    clear_sessions_for_tests()
    clear_kb_cache_for_tests()
    clear_capability_map_cache_for_tests()
    clear_grounding_cache_for_tests()


def _qualified(synopsis: str, keywords: list[str]) -> bool:
    lowered = (synopsis or "").lower()
    if _EMPTY_SYNOPSIS in lowered:
        return False
    if not keywords:
        return bool(synopsis.strip())
    return any(k.lower() in lowered for k in keywords)


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_messy_language_variation_qualifies(case):
    """Every business-need variation must produce a sales-ready lead synopsis."""
    session = start_session()
    result = handle_message(session.session_id, case["messages"][0])
    synopsis = result.lead_assessment.synopsis

    if case.get("must_qualify", True):
        assert _qualified(synopsis, case.get("qualification_any") or []), (
            f"{case['name']}: weak synopsis: {synopsis!r}"
        )

    if case.get("prefer_answer"):
        assert result.mode == "answer", (
            f"{case['name']}: expected answer got {result.mode}: {result.response[:120]}"
        )


def test_messy_language_variations_baseline_report(capsys):
    cases = _load_cases()
    assert len(cases) == 30, f"expected 30 variations (6 seeds x 5), got {len(cases)}"

    qualify_hits = 0
    answer_hits = 0
    answer_cases = 0
    failures: list[str] = []

    for case in cases:
        clear_sessions_for_tests()
        session = start_session()
        result = handle_message(session.session_id, case["messages"][0])
        synopsis = result.lead_assessment.synopsis

        if case.get("must_qualify", True):
            if _qualified(synopsis, case.get("qualification_any") or []):
                qualify_hits += 1
            else:
                failures.append(f"[qualify] {case['name']}: {synopsis[:100]}")

        if case.get("prefer_answer"):
            answer_cases += 1
            if result.mode == "answer":
                answer_hits += 1
            else:
                failures.append(f"[answer] {case['name']}: mode={result.mode}")

    qualify_rate = qualify_hits / len(cases)
    answer_rate = answer_hits / answer_cases if answer_cases else 1.0
    summary = (
        f"messy-language variations ({len(cases)} cases): "
        f"qualification={qualify_hits}/{len(cases)} ({qualify_rate:.1%}) "
        f"prefer_answer={answer_hits}/{answer_cases} ({answer_rate:.1%})"
    )
    print(summary)
    if failures:
        print("\nTuning: capability map phrase → family relation → KB if factual gap → eval\n")
        print("\n".join(failures))

    assert qualify_rate >= 0.9, summary
