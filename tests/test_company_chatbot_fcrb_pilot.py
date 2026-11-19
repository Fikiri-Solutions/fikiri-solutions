"""FCRB customer-realism pilot — baseline only; does not gate on high auto-pass."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.fcrb_eval import (
    format_fcrb_report,
    load_fcrb_cases,
    run_fcrb_suite,
    summarize_fcrb,
)
from company_chatbot.retrieval import clear_kb_cache_for_tests
from company_chatbot.orchestrator import clear_sessions_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

FCRB_PATH = Path(__file__).parent / "company_chatbot_fcrb_pilot.yaml"
GOLDEN_PATH = Path(__file__).parent / "company_chatbot_retrieval_eval.yaml"


@pytest.fixture(autouse=True)
def _reset():
    clear_kb_cache_for_tests()
    clear_sessions_for_tests()
    yield
    clear_kb_cache_for_tests()
    clear_sessions_for_tests()


def test_fcrb_pilot_suite_shape_independent_of_golden():
    cases = load_fcrb_cases(FCRB_PATH)
    assert len(cases) == 50
    cats = {}
    for case in cases:
        cats[case["category"]] = cats.get(case["category"], 0) + 1
        assert case["provenance"]["independent_of_golden"] is True
        assert case["provenance"]["review_status"] == "draft_unvalidated"
        assert case.get("turns")
    assert cats["standard"] == 10
    assert cats["typo_slang"] == 10
    assert cats["multi_turn"] == 8
    assert cats["non_native_dialect"] == 8
    assert cats["ambiguous"] == 7
    assert cats["safety_handoff"] == 7

    golden_queries = {
        (c.get("query") or "").strip().lower()
        for c in (yaml.safe_load(GOLDEN_PATH.read_text())["cases"] or [])
    }
    # Pilot should not be a copy-paste of golden queries (allow tiny accidental overlap).
    fcrb_final_queries = []
    for case in cases:
        fcrb_final_queries.append((case["turns"][-1]["user"] or "").strip().lower())
    overlap = sum(1 for q in fcrb_final_queries if q in golden_queries)
    assert overlap <= 8, f"too much golden overlap ({overlap}); suite not independent enough"


def test_fcrb_pilot_runs_orchestrator_and_reports_baseline(capsys):
    """Establish baseline metrics; do not require high pass rates (no prod tuning yet)."""
    results = run_fcrb_suite(FCRB_PATH)
    summary = summarize_fcrb(results)
    report = format_fcrb_report(results)
    print(report)

    assert summary["cases"] == 50
    assert summary["all_draft_unvalidated"] is True
    # Structural sanity: at least some standard cases should auto-pass today.
    assert summary["clean_auto_pass_rate"] is not None
    assert summary["clean_auto_pass_rate"] >= 0.4
    # Golden freeze check: golden file still present with >= 100 cases.
    golden_n = len(yaml.safe_load(GOLDEN_PATH.read_text())["cases"])
    assert golden_n >= 100
