"""Unit tests for Fikiri-native deterministic eval plumbing."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

from company_chatbot.context_dependency import ContextDependency, detect_context_dependency
from company_chatbot.eval_cases import normalize_golden_case
from company_chatbot.eval_metrics import (
    FAILURE_COVERAGE_HOLE,
    FAILURE_RANKING,
    FAILURE_RETRIEVAL_MISS,
    classify_retrieval_failure,
    hit_at_k,
    id_precision_at_k,
    id_recall_at_k,
    mean_reciprocal_rank,
)
from company_chatbot.eval_mutations import intent_stability_rate, mutate_query
from company_chatbot.golden_candidates import (
    advance_candidate_status,
    build_golden_candidate,
    candidate_to_yaml_fragment,
)
from company_chatbot.retrieval import clear_kb_cache_for_tests


@pytest.fixture(autouse=True)
def reset_kb_cache():
    clear_kb_cache_for_tests()
    yield
    clear_kb_cache_for_tests()


def test_id_precision_recall_and_mrr():
    retrieved = ["company_about", "pricing_overview", "pricing_starter"]
    expected = ["pricing_overview", "pricing_starter"]
    assert id_recall_at_k(retrieved, expected, 3) == 1.0
    assert id_precision_at_k(retrieved, expected, 3) == pytest.approx(2 / 3)
    assert mean_reciprocal_rank(retrieved, expected) == pytest.approx(0.5)
    assert hit_at_k(retrieved, expected, 1) == 0.0
    assert hit_at_k(retrieved, expected, 3) == 1.0


def test_failure_taxonomy_miss_vs_ranking_vs_coverage():
    assert FAILURE_RETRIEVAL_MISS in classify_retrieval_failure(
        retrieved_ids=["company_about"],
        required_ids=["pricing_overview"],
        corpus_ids={"company_about", "pricing_overview"},
    )
    assert FAILURE_RANKING in classify_retrieval_failure(
        retrieved_ids=["company_about", "x", "y", "pricing_overview"],
        required_ids=["pricing_overview"],
        corpus_ids={"company_about", "pricing_overview"},
        k=3,
    )
    assert FAILURE_COVERAGE_HOLE in classify_retrieval_failure(
        retrieved_ids=["company_about"],
        required_ids=["missing_chunk_zzz"],
        corpus_ids={"company_about"},
    )


def test_normalize_rich_and_legacy_schema():
    legacy = normalize_golden_case(
        {
            "name": "legacy",
            "query": "What does Fikiri cost?",
            "expected_ids": ["pricing_overview", "pricing_starter"],
            "topic": "pricing",
        }
    )
    assert legacy.retrieval.required == ["pricing_overview", "pricing_starter"]
    assert legacy.expected_ids == ["pricing_overview", "pricing_starter"]

    rich = normalize_golden_case(
        {
            "name": "rich",
            "query": "How do you work with clients?",
            "retrieval": {
                "required": ["engagement_how_we_work"],
                "acceptable": ["engagement_scoped_buildouts"],
                "forbidden": ["contact_intake_path"],
            },
            "forbidden_modes": ["intake"],
            "must_not": {"phrases": ["fill out the intake form"]},
            "context_dependency": "standalone",
        }
    )
    assert rich.retrieval.forbidden == ["contact_intake_path"]
    assert rich.mode.forbidden == ["intake"]
    assert rich.phrases.forbidden == ["fill out the intake form"]
    assert "engagement_scoped_buildouts" in rich.expected_ids


def test_context_dependency_standalone_vs_followup():
    assert (
        detect_context_dependency("What does Fikiri do?", "What does Fikiri cost?")
        == ContextDependency.STANDALONE
    )
    assert (
        detect_context_dependency("What about Gmail?", "Tell me about the AI email assistant")
        == ContextDependency.FOLLOWUP
    )
    assert detect_context_dependency("What does Fikiri cost?", None) == ContextDependency.STANDALONE


def test_live_effective_query_keeps_integration_followup_topic_switch():
    """Regression: detector FOLLOWUP must not force-blend over topic-switch retrieval."""
    from company_chatbot.retrieval import effective_query_for_retrieval, retrieve

    q, prev = "What about Outlook?", "Tell me about the AI email assistant"
    # Live path uses topic-switch (not context_dependency blend).
    assert effective_query_for_retrieval(q, prev) == q
    ids = [c.id for c in retrieve(q, top_k=3, previous_query=prev).chunks]
    assert "integration_outlook" in ids, ids


def test_mutate_query_is_bounded_and_deterministic():
    first = mutate_query("What does Fikiri cost?")
    second = mutate_query("What does Fikiri cost?")
    assert first == second
    assert 2 <= len(first) <= 24
    assert any("y'all" in v.lower() or v.lower() != first[0].lower() for v in first)


def test_intent_stability_on_pricing_query():
    case = {
        "name": "pricing_cost_stability",
        "query": "What does Fikiri cost?",
        "expected_ids": ["pricing_overview", "pricing_starter", "pricing_growth", "pricing_business"],
        "topic": "pricing",
    }
    result = intent_stability_rate(case, max_variants=8)
    assert result.metrics["intent_stability_rate"] >= 0.75, result.evidence
    assert "context_label_stability_rate" in result.metrics


def test_gmail_followup_isr_separates_retrieval_from_context_labels():
    case = {
        "name": "gmail_followup_with_context",
        "query": "What about Gmail?",
        "previous_query": "Tell me about the AI email assistant",
        "context_dependency": "followup",
        "retrieval": {
            "required": ["integration_gmail"],
            "acceptable": ["product_ai_email_assistant"],
        },
    }
    result = intent_stability_rate(case, max_variants=10)
    # Retrieval ISR must stay high even when polite wrappers break ^what about labels.
    assert result.metrics["intent_stability_rate"] >= 0.9, result.reason
    assert result.metrics["context_label_stability_rate"] < result.metrics["intent_stability_rate"]


def test_golden_candidate_lifecycle_no_auto_promote():
    candidate = build_golden_candidate(
        miss_id="chat_miss_3847",
        query="Email me at founder@example.com or +1 (305) 555-0199",
        retrieved_ids=["company_about", "pricing_overview"],
        expected_ids=["pricing_overview"],
        topic="pricing",
        failure_labels=["RANKING_FAILURE"],
    )
    assert candidate["status"] == "OBSERVED"
    assert candidate["provenance"]["auto_promote"] is False
    assert candidate["provenance"]["redacted"] is True
    assert "founder@example.com" not in candidate["query"]
    assert "[REDACTED_EMAIL]" in candidate["query"]
    assert "[REDACTED_PHONE]" in candidate["query"]
    yaml_frag = candidate_to_yaml_fragment(candidate)
    assert "auto_promote=false" in yaml_frag
    assert "redacted=true" in yaml_frag.lower()
    assert "pricing_overview" in yaml_frag
    labeled = advance_candidate_status(candidate, "LABELED")
    assert labeled["status"] == "LABELED"
    with pytest.raises(ValueError):
        advance_candidate_status(labeled, "OBSERVED")
