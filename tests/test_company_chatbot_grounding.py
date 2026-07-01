"""Unit tests for site bot retrieval and grounding."""

import os

import pytest

from company_chatbot.grounding import apply_grounding, clear_grounding_cache_for_tests
from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve, score_chunk, tokenize
from company_chatbot.retrieval import KBChunk
from company_chatbot.service_families import compose_bridge_response

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def reset_caches():
    clear_kb_cache_for_tests()
    clear_grounding_cache_for_tests()
    yield
    clear_kb_cache_for_tests()
    clear_grounding_cache_for_tests()


def test_tokenize_lowercase_alnum():
    assert tokenize("Hello, Fikiri 2026!") == {"hello", "fikiri", "2026"}


def test_score_chunk_overlap():
    chunk = KBChunk(
        id="x",
        text="Starter plan is forty-nine dollars",
        topic="pricing",
        source_url="https://example.com",
        keywords=["starter", "49"],
    )
    score = score_chunk(tokenize("starter plan price"), chunk)
    assert score >= 0.25


def test_retrieve_free_trial():
    result = retrieve("free trial credit card")
    assert result.chunks
    assert "trial" in result.chunks[0].text.lower()


def test_grounding_passes_for_pricing():
    outcome = apply_grounding("What is the Starter plan price?")
    assert outcome.success is True
    assert "$49" in outcome.response
    assert outcome.sources


def test_grounding_fails_for_missing_hipaa():
    outcome = apply_grounding("Are you HIPAA certified?")
    assert outcome.success is False
    assert "don't have enough verified" in outcome.response


def test_grounding_fails_for_case_study_without_evidence():
    outcome = apply_grounding("Share your healthcare case study ROI numbers")
    assert outcome.success is False
    assert "case study" not in outcome.response.lower() or "don't have enough" in outcome.response


def test_grounding_passes_for_ai_email_assistant():
    outcome = apply_grounding("Tell me about the AI email assistant")
    assert outcome.success is True
    assert "email" in outcome.response.lower()
    assert outcome.sources


def test_grounding_passes_for_email_assisant_typo():
    outcome = apply_grounding("I need to find out about the email assisant")
    assert outcome.success is True
    assert "email" in outcome.response.lower()
    assert outcome.sources[0]["id"] == "product_ai_email_assistant"


def test_retrieval_starter_pricing_beats_product():
    result = retrieve("How much is Starter?", top_k=3)
    assert result.chunks[0].id == "pricing_starter"


def test_retrieval_gmail_followup_uses_context():
    result = retrieve(
        "What about Gmail?",
        top_k=3,
        previous_query="Tell me about the AI email assistant",
    )
    assert result.chunks[0].id in {"integration_gmail", "product_ai_email_assistant"}


def test_retrieval_help_me():
    result = retrieve("help me", top_k=3)
    assert result.chunks
    assert result.chunks[0].id == "site_chat_widget"


def test_grounding_bridge_for_messy_follow_up_pain():
    from company_chatbot.retrieval import retrieve

    outcome = apply_grounding(
        "I need help following up with customers",
        retrieval=retrieve("I need help following up with customers"),
    )
    assert outcome.success is True
    assert outcome.reason in {"bridge_multi_family", "evidence_match"}
    assert "follow" in outcome.response.lower()


def test_grounding_disambiguation_for_vague_help():
    outcome = apply_grounding("I need help")
    assert outcome.success is True
    assert outcome.reason == "disambiguation"
    assert "email replies" in outcome.response.lower()


def test_kb_chunk_count_at_least_forty():
    from company_chatbot.retrieval import load_kb_chunks

    assert len(load_kb_chunks()) >= 40


def test_compose_bridge_response_empty_families_does_not_raise():
    chunk = KBChunk(
        id="kb-1",
        text="Fikiri automates workflows.",
        topic="overview",
        source_url="https://fikirisolutions.com",
    )
    response = compose_bridge_response("help me", [chunk], [])
    assert "Fikiri automates workflows." in response
