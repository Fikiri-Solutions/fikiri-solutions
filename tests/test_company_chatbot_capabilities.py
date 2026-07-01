"""Capability map eval and multi-need detection tests (Phase 6e)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.capabilities import clear_capability_map_cache_for_tests, detect_needs
from company_chatbot.grounding import apply_grounding, clear_grounding_cache_for_tests
from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

EVAL_PATH = Path(__file__).parent / "company_chatbot_capability_eval.yaml"
FAMILY_TARGET = 0.90
BUNDLE_TARGET = 0.75


def _load_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


@pytest.fixture(autouse=True)
def reset_caches():
    clear_kb_cache_for_tests()
    clear_capability_map_cache_for_tests()
    clear_grounding_cache_for_tests()
    yield
    clear_kb_cache_for_tests()
    clear_capability_map_cache_for_tests()
    clear_grounding_cache_for_tests()


def test_capability_map_loads():
    from company_chatbot.capabilities import load_capability_map

    cmap = load_capability_map()
    assert len(cmap.families) >= 9
    assert len(cmap.bundles) >= 4


def test_detect_multi_family_website_quotes():
    needs = detect_needs(
        "I need a website where customers can request quotes, and I want those leads tracked automatically"
    )
    assert "website_and_landing_pages" in needs.detected_families
    assert "forms_and_intake" in needs.detected_families
    assert "crm_and_lead_tracking" in needs.detected_families
    assert needs.suggested_bundle == "lead_intake_system"
    assert needs.confidence >= 0.5


def test_retrieval_includes_needs_payload():
    result = retrieve("People fill out the form but nobody follows up", top_k=3)
    assert result.needs
    assert "forms_and_intake" in result.needs.get("detected_families", [])


def test_capability_bridge_grounding():
    query = (
        "I need a website where customers can request quotes, "
        "and I want those leads tracked automatically"
    )
    outcome = apply_grounding(query, retrieval=retrieve(query))
    assert outcome.success is True
    assert outcome.reason in {"capability_bridge", "bridge_multi_family", "evidence_match"}
    assert "mix" in outcome.response.lower() or "closest" in outcome.response.lower()


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_capability_eval_case(case):
    needs = detect_needs(case["query"])
    detected = set(needs.detected_families)

    expected_families = set(case.get("expected_families") or [])
    if expected_families:
        assert expected_families & detected, (
            f"{case['name']}: expected one of {sorted(expected_families)} got {sorted(detected)}"
        )

    min_families = case.get("min_families")
    if min_families:
        assert len(detected) >= int(min_families)

    expected_capabilities = set(case.get("expected_capabilities") or [])
    if expected_capabilities:
        detected_caps = set(needs.detected_capabilities)
        assert expected_capabilities & detected_caps, (
            f"{case['name']}: expected caps {expected_capabilities} got {detected_caps}"
        )

    expected_bundle = case.get("expected_bundle")
    if expected_bundle:
        assert needs.suggested_bundle == expected_bundle, (
            f"{case['name']}: expected bundle {expected_bundle} got {needs.suggested_bundle}"
        )


def test_capability_eval_aggregate_rates():
    cases = _load_cases()
    assert len(cases) >= 15

    family_hits = 0
    bundle_hits = 0
    bundle_cases = 0
    failures: list[str] = []

    for case in cases:
        needs = detect_needs(case["query"])
        detected = set(needs.detected_families)
        expected_families = set(case.get("expected_families") or [])
        min_families = int(case.get("min_families") or 0)

        if expected_families:
            if expected_families & detected:
                family_hits += 1
            else:
                failures.append(f"{case['name']} families expected {expected_families} got {detected}")
        elif min_families:
            if len(detected) >= min_families:
                family_hits += 1
            else:
                failures.append(f"{case['name']} min_families {min_families} got {len(detected)}")

        if case.get("expected_bundle"):
            bundle_cases += 1
            if needs.suggested_bundle == case["expected_bundle"]:
                bundle_hits += 1
            else:
                failures.append(
                    f"{case['name']} bundle expected {case['expected_bundle']} got {needs.suggested_bundle}"
                )

    family_cases = sum(1 for c in cases if c.get("expected_families") or c.get("min_families"))
    family_rate = family_hits / family_cases if family_cases else 1.0
    bundle_rate = bundle_hits / bundle_cases if bundle_cases else 1.0

    summary = f"capability eval: family={family_hits}/{family_cases} ({family_rate:.1%}) bundle={bundle_hits}/{bundle_cases} ({bundle_rate:.1%})"
    print(summary)
    if failures:
        print("failures:\n" + "\n".join(failures[:20]))

    assert family_rate >= FAMILY_TARGET, summary
    if bundle_cases:
        assert bundle_rate >= BUNDLE_TARGET, summary
