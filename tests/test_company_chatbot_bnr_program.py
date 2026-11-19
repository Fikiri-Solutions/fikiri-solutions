"""BNR program tests — preserve golden; report business-need realism metrics."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.bnr_eval import format_bnr_report, run_bnr_suite, summarize_bnr
from company_chatbot.business_needs import detect_business_needs
from company_chatbot.orchestrator import clear_sessions_for_tests
from company_chatbot.retrieval import clear_kb_cache_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

BNR_PATH = Path(__file__).parent / "company_chatbot_bnr_benchmark.yaml"
GOLDEN_PATH = Path(__file__).parent / "company_chatbot_retrieval_eval.yaml"


@pytest.fixture(autouse=True)
def _reset():
    clear_kb_cache_for_tests()
    clear_sessions_for_tests()
    yield
    clear_kb_cache_for_tests()
    clear_sessions_for_tests()


def test_bnr_benchmark_shape_and_holdout_split():
    data = yaml.safe_load(BNR_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) == 150
    dev = [c for c in cases if c["split"] == "dev"]
    hold = [c for c in cases if c["split"] == "holdout"]
    assert len(dev) == 120
    assert len(hold) == 30
    needs = {c["need_id"] for c in cases}
    assert len(needs) == 15


def test_business_need_detector_concept_not_industry():
    # Same need across trucking / barbershop / cleaning wording.
    a = detect_business_needs("I run a trucking company and dispatch is getting out of hand.")
    b = detect_business_needs("My barbershop keeps double booking clients.")
    c = detect_business_needs("cleaning company staff schedules all over the place")
    assert "scheduling_dispatch" in a.need_ids
    assert "scheduling_dispatch" in b.need_ids
    assert "scheduling_dispatch" in c.need_ids


def test_crm_and_reporting_concepts_not_industry_aliases():
    """Restaurant/bakery wording must map to reusable CRM/reporting concepts."""
    orders = detect_business_needs(
        "restaurant regulars — how do I track who ordered what last time"
    )
    payments = detect_business_needs(
        "bakery wholesale accounts — which ones actually pay"
    )
    assert "customer_management" in orders.need_ids
    assert "reporting_analytics" in payments.need_ids


def test_profit_stem_does_not_match_nonprofit():
    nonprofit = detect_business_needs(
        "nonprofit donation interest forms pile up unanswered"
    )
    assert "reporting_analytics" not in nonprofit.need_ids
    assert "lead_intake" in nonprofit.need_ids
    profitable = detect_business_needs(
        "agency retainers vs project work profitability unclear"
    )
    assert "reporting_analytics" in profitable.need_ids


def test_release_candidate_set_is_pristine_and_untuned():
    path = Path(__file__).parent / "company_chatbot_bnr_release_candidate.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data.get("review_status") == "awaiting_independent_labels"
    cases = data.get("cases") or []
    assert len(cases) >= 20
    for case in cases:
        prov = case.get("provenance") or {}
        assert prov.get("used_for_tuning") is False
        assert prov.get("review_status") == "awaiting_independent_labels"


def test_bnr_dev_baseline_and_golden_preserved(capsys):
    golden_n = len(yaml.safe_load(GOLDEN_PATH.read_text())["cases"])
    assert golden_n == 103

    dev_results = run_bnr_suite(BNR_PATH, split="dev")
    # Holdout evaluated once for reporting only — not used to choose fixes in this test.
    hold_results = run_bnr_suite(BNR_PATH, split="holdout")
    dev = summarize_bnr(dev_results)
    hold = summarize_bnr(hold_results)
    print(format_bnr_report(dev, hold))

    # Soft floors after bridge work; labels still draft_unvalidated.
    assert dev["unsupported_claim_rate"] == 0.0
    assert hold["unsupported_claim_rate"] == 0.0
    assert dev["auto_pass_rate"] >= 0.85
    assert hold["auto_pass_rate"] >= 0.85
    assert dev["need_recognition_rate"] >= 0.70
    assert hold["need_recognition_rate"] >= 0.70
