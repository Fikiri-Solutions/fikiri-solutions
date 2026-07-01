"""Unit tests for deterministic lead assessment."""

import os

import pytest

from company_chatbot import config
from company_chatbot.intake import IntakeSlots
from company_chatbot.lead_scoring import assess_lead, score_to_tier
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.schemas import HandoffMetadata

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


def _handoff(**kwargs) -> HandoffMetadata:
    return HandoffMetadata(**kwargs)


def test_casual_faq_scores_low():
    result = assess_lead(
        message="hello",
        mode=config.MODE_FALLBACK,
        slots=IntakeSlots(),
        handoff=_handoff(),
    )
    assert result.tier == "casual"
    assert result.score <= 2
    assert "not provided enough business context" in result.synopsis.lower()


def test_pricing_interest_not_hot_alone():
    result = assess_lead(
        message="How much does Fikiri cost?",
        mode=config.MODE_ANSWER,
        slots=IntakeSlots(),
        handoff=_handoff(applicable=True, secondary="/contact", handoff_type="contact"),
    )
    assert "pricing_interest" in result.signals
    assert result.tier in ("casual", "possible")
    assert result.tier != "hot"


def test_workflow_pain_and_industry_scores_possible_or_warm():
    slots = IntakeSlots(industry="landscaping", main_pain="Missed leads and manual follow-up")
    result = assess_lead(
        message="We run a landscaping business and miss too many leads",
        mode=config.MODE_EXPLORE_FIT,
        slots=slots,
        handoff=_handoff(applicable=True, secondary="/intake", handoff_type="intake"),
    )
    assert result.score >= 3
    assert result.tier in ("possible", "warm", "hot")
    assert "business_context" in result.signals
    assert "workflow_pain" in result.signals


def test_email_pain_timeline_scores_hot():
    slots = IntakeSlots(
        industry="landscaping",
        main_pain="Missed leads and slow follow-up",
        timeline="this quarter",
        contact_email="owner@example.com",
    )
    result = assess_lead(
        message="owner@example.com",
        mode=config.MODE_EXPLORE_FIT,
        slots=slots,
        handoff=_handoff(applicable=True, secondary="/intake", handoff_type="intake"),
        intake_complete=True,
    )
    assert result.tier == "hot"
    assert result.score >= 9
    assert "contact_email" in result.signals
    assert "landscaping" in result.synopsis.lower()


def test_synopsis_does_not_invent_missing_fields():
    result = assess_lead(
        message="pricing?",
        mode=config.MODE_ANSWER,
        slots=IntakeSlots(),
        handoff=_handoff(),
    )
    lowered = result.synopsis.lower()
    assert "enterprise" not in lowered
    assert "budget" not in lowered
    assert "employees" not in lowered


def test_recommended_handoff_intake_for_warm_lead():
    slots = IntakeSlots(industry="restaurant", main_pain="Manual scheduling chaos", timeline="urgent")
    result = assess_lead(
        message="restaurant with urgent scheduling pain",
        mode=config.MODE_WORKFLOW_AUDIT,
        slots=slots,
        handoff=_handoff(applicable=False),
    )
    assert result.tier in ("warm", "hot")
    assert result.recommended_handoff == config.HANDOFF_SECONDARY_INTAKE


def test_recommended_handoff_contact_for_contact_mode():
    result = assess_lead(
        message="I want to talk to someone",
        mode=config.MODE_CONTACT,
        slots=IntakeSlots(),
        handoff=_handoff(
            applicable=True,
            secondary=config.HANDOFF_SECONDARY_CONTACT,
            handoff_type="contact",
        ),
    )
    assert result.recommended_handoff == config.HANDOFF_SECONDARY_CONTACT


@pytest.mark.parametrize(
    "score,expected",
    [(0, "casual"), (2, "casual"), (3, "possible"), (5, "possible"), (6, "warm"), (8, "warm"), (9, "hot"), (12, "hot")],
)
def test_score_to_tier_bands(score, expected):
    assert score_to_tier(score) == expected


def test_fallback_business_message_still_qualifies():
    result = assess_lead(
        message="need site track leads",
        mode=config.MODE_FALLBACK,
        slots=IntakeSlots(),
        handoff=_handoff(applicable=True, secondary="/intake", handoff_type="intake"),
    )
    assert "not provided enough" not in result.synopsis.lower()
    assert "quoted" in result.synopsis.lower() or "lead" in result.synopsis.lower()


def test_orchestrator_includes_lead_assessment():
    clear_sessions_for_tests()
    session = start_session()
    reply = handle_message(session.session_id, "Is Fikiri a fit for my business?")
    assert reply.lead_assessment.tier in ("possible", "warm", "hot", "casual")
    assert isinstance(reply.lead_assessment.synopsis, str)
    payload = reply.to_dict("v1")
    assert "lead_assessment" in payload
    assert "score" in payload["lead_assessment"]
