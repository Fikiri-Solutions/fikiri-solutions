"""Unit tests for site bot intake flow."""

import os

import pytest

from company_chatbot import config
from company_chatbot.intake import (
    IntakeSlots,
    _fill_direct_slot_answer,
    extract_slots_from_message,
    is_intake_complete,
    process_intake_turn,
    should_start_intake,
)
from company_chatbot.modes import detect_mode
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def reset_sessions():
    clear_sessions_for_tests()
    yield
    clear_sessions_for_tests()


def test_should_start_intake_only_for_buying_modes():
    assert should_start_intake(config.MODE_WORKFLOW_AUDIT) is True
    assert should_start_intake(config.MODE_CONSULTING) is True
    assert should_start_intake(config.MODE_EXPLORE_FIT) is True
    assert should_start_intake(config.MODE_ANSWER) is False
    assert should_start_intake(config.MODE_CONTACT) is False


def test_faq_pricing_does_not_start_intake():
    session = start_session()
    result = handle_message(session.session_id, "How much is the Starter plan?")
    assert result.mode == config.MODE_ANSWER
    assert not result.intake.get("active")


def test_workflow_audit_starts_intake_question():
    session = start_session()
    result = handle_message(session.session_id, "I want a workflow audit")
    assert result.mode == config.MODE_WORKFLOW_AUDIT
    assert result.intake.get("active") is True
    assert "industry" in result.response.lower()


def test_slot_extraction_email_industry_pain_timeline():
    slots = IntakeSlots()
    slots = extract_slots_from_message(
        "Landscaping company, missed leads bottleneck, urgent this month, team@acme.com",
        slots,
    )
    assert slots.industry == "landscaping"
    assert slots.main_pain
    assert slots.timeline == "urgent"
    assert slots.contact_email == "team@acme.com"
    assert is_intake_complete(slots)


def test_intake_completes_after_three_core_slots_without_email():
    slots = IntakeSlots()
    slots.industry = "restaurant"
    slots.main_pain = "manual scheduling pain"
    slots.timeline = "this quarter"
    assert is_intake_complete(slots)


def test_refuse_email_counts_toward_completion():
    slots = IntakeSlots()
    slots = extract_slots_from_message("no email, prefer not to share", slots)
    slots.industry = "dental"
    slots.main_pain = "slow follow-up process"
    slots.timeline = "soon"
    assert slots.email_declined is True
    assert is_intake_complete(slots)


def test_intake_one_question_per_turn():
    turn = process_intake_turn("workflow audit", IntakeSlots(), config.MODE_WORKFLOW_AUDIT)
    assert turn.complete is False
    assert turn.next_slot == "industry"
    assert turn.response.count("?") == 1


def test_retail_marketing_followup_intake_does_not_loop():
    """Regression: short bottleneck labels must not repeat the pain question until handoff."""
    session = start_session()
    handle_message(session.session_id, "I'd like a workflow audit")
    r2 = handle_message(session.session_id, "Retail")
    assert r2.intake.get("active") is True
    assert "bottleneck" in r2.response.lower()

    r3 = handle_message(session.session_id, "Marketing")
    assert r3.intake.get("slots", {}).get("main_pain") == "Marketing"
    assert "timeline" in r3.response.lower()
    assert "got stuck" not in r3.response.lower()

    r4 = handle_message(session.session_id, "this quarter")
    assert "got stuck" not in r4.response.lower()
    assert r4.intake.get("slots", {}).get("timeline") == "this quarter"


def test_following_up_with_leads_accepted_as_main_pain():
    session = start_session()
    handle_message(session.session_id, "I'd like a workflow audit")
    handle_message(session.session_id, "Retail")
    r = handle_message(session.session_id, "following up with leads")
    assert r.intake.get("slots", {}).get("main_pain") == "following up with leads"
    assert "got stuck" not in r.response.lower()
    assert "timeline" in r.response.lower()


def test_pain_clarification_on_timeline_question_updates_pain():
    session = start_session()
    handle_message(session.session_id, "I'd like a workflow audit")
    handle_message(session.session_id, "Retail")
    handle_message(session.session_id, "Marketing")
    r = handle_message(session.session_id, "following up with leads")
    assert r.intake.get("slots", {}).get("main_pain") == "following up with leads"
    assert r.intake.get("slots", {}).get("timeline") == ""
    assert "timeline" in r.response.lower()


def test_fill_direct_slot_answer_assigns_extracted_pain_without_prior_extract():
    slots = IntakeSlots(industry="retail")
    updated = _fill_direct_slot_answer("following up with leads", slots, "main_pain")
    assert updated.main_pain == "following up with leads"


def test_multi_detail_message_completes_intake_via_api():
    session = start_session()
    result = handle_message(
        session.session_id,
        "I need help with my business — landscaping, leads fall through cracks, urgent this month, bob@example.com",
    )
    assert result.intake.get("complete") is True
    assert "fikirisolutions.com/intake" in result.response
