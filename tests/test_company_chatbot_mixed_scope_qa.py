"""Mixed-scope QA conversations — full bot path + capability needs (tune via 6d/6e)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.capabilities import clear_capability_map_cache_for_tests, detect_needs
from company_chatbot.grounding import clear_grounding_cache_for_tests
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.retrieval import clear_kb_cache_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

QA_PATH = Path(__file__).parent / "company_chatbot_mixed_scope_qa.yaml"


def _load_cases():
    data = yaml.safe_load(QA_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


def _user_examples():
    return [c for c in _load_cases() if c.get("user_example")]


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


def _run_conversation(messages: list[str]):
    session = start_session()
    last = None
    for message in messages:
        last = handle_message(session.session_id, message)
    return last


def _needs_for_case(case: dict):
    messages = case["messages"]
    last = messages[-1]
    previous = messages[-2] if len(messages) >= 2 else None
    return detect_needs(last, previous_query=previous)


def _assert_case(case: dict, *, strict_families: bool = True):
    needs = _needs_for_case(case)
    detected = set(needs.detected_families)

    expected_families = set(case.get("expected_families") or [])
    if strict_families and expected_families:
        assert expected_families & detected, (
            f"{case['name']}: expected one of {sorted(expected_families)} got {sorted(detected)}"
        )

    min_families = case.get("min_families")
    if strict_families and min_families:
        assert len(detected) >= int(min_families), (
            f"{case['name']}: expected >={min_families} families got {sorted(detected)}"
        )

    expected_bundle = case.get("expected_bundle")
    if strict_families and expected_bundle:
        assert needs.suggested_bundle == expected_bundle, (
            f"{case['name']}: expected bundle {expected_bundle} got {needs.suggested_bundle}"
        )

    result = _run_conversation(case["messages"])
    assert result is not None

    if case.get("expected_mode"):
        assert result.mode == case["expected_mode"], (
            f"{case['name']}: mode expected {case['expected_mode']} got {result.mode}"
        )

    response_lower = result.response.lower()
    for phrase in case.get("must_include") or []:
        assert phrase.lower() in response_lower, f"missing '{phrase}' in: {result.response}"

    for phrase in case.get("must_not_include") or []:
        assert phrase.lower() not in response_lower, f"forbidden '{phrase}' in: {result.response}"

    if case.get("expected_grounded", True):
        assert result.grounded is True, f"{case['name']} not grounded: {result.response[:160]}"


@pytest.mark.parametrize("case", _user_examples(), ids=lambda c: c["name"])
def test_mixed_scope_user_examples(case):
    """Seven canonical mixed-scope phrases from sales QA — must pass before deploy tuning."""
    _assert_case(case, strict_families=True)


def test_mixed_scope_qa_baseline_report(capsys):
    """Full QA set (25–40 convos): report pass rates and tuning candidates for 6d → 6e."""
    cases = _load_cases()
    assert 25 <= len(cases) <= 40, f"expected 25-40 QA cases, got {len(cases)}"

    family_hits = 0
    bundle_hits = 0
    bundle_cases = 0
    grounded_hits = 0
    mode_hits = 0
    mode_cases = 0
    failures: list[str] = []

    for case in cases:
        needs = _needs_for_case(case)
        detected = set(needs.detected_families)
        expected_families = set(case.get("expected_families") or [])

        if expected_families:
            if expected_families & detected:
                family_hits += 1
            else:
                failures.append(
                    f"[family] {case['name']}: expected {sorted(expected_families)} got {sorted(detected)}"
                )
        elif case.get("min_families"):
            if len(detected) >= int(case["min_families"]):
                family_hits += 1
            else:
                failures.append(
                    f"[family] {case['name']}: need >={case['min_families']} got {sorted(detected)}"
                )

        if case.get("expected_bundle"):
            bundle_cases += 1
            if needs.suggested_bundle == case["expected_bundle"]:
                bundle_hits += 1
            else:
                failures.append(
                    f"[bundle] {case['name']}: expected {case['expected_bundle']} got {needs.suggested_bundle}"
                )

        result = _run_conversation(case["messages"])
        if case.get("expected_grounded", True) and result.grounded:
            grounded_hits += 1
        elif case.get("expected_grounded", True):
            failures.append(f"[grounded] {case['name']}: {result.response[:100]}")

        if case.get("expected_mode"):
            mode_cases += 1
            if result.mode == case["expected_mode"]:
                mode_hits += 1
            else:
                failures.append(
                    f"[mode] {case['name']}: expected {case['expected_mode']} got {result.mode}"
                )

    family_cases = sum(
        1 for c in cases if c.get("expected_families") or c.get("min_families")
    )
    family_rate = family_hits / family_cases if family_cases else 1.0
    bundle_rate = bundle_hits / bundle_cases if bundle_cases else 1.0
    grounded_rate = grounded_hits / len(cases)
    mode_rate = mode_hits / mode_cases if mode_cases else 1.0

    summary = (
        f"mixed-scope QA baseline ({len(cases)} cases): "
        f"family={family_hits}/{family_cases} ({family_rate:.1%}) "
        f"bundle={bundle_hits}/{bundle_cases} ({bundle_rate:.1%}) "
        f"grounded={grounded_hits}/{len(cases)} ({grounded_rate:.1%}) "
        f"mode={mode_hits}/{mode_cases} ({mode_rate:.1%})"
    )
    print(summary)
    if failures:
        print("\nTuning order: capability map phrase → family relation → KB if factual gap → eval → tests\n")
        print("\n".join(failures))

    # Informational baseline for 6d → 6e tuning; strict gate is test_mixed_scope_user_examples.
    assert len(cases) >= 25
