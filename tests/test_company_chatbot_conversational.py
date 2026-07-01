"""Unit tests for conversational greeting/ack replies."""

import os

from company_chatbot.conversational import conversational_reply
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


def test_greeting_reply():
    assert conversational_reply("hello") is not None
    assert "pricing" in conversational_reply("Hi!").lower()


def test_ack_reply_differs_from_greeting():
    assert conversational_reply("wow") != conversational_reply("hello")


def test_why_how_get_distinct_replies():
    assert conversational_reply("why") != conversational_reply("how")
    assert "fit" in conversational_reply("why").lower()
    assert "pricing" in conversational_reply("how").lower()


def test_fit_quick_prompt_starts_intake():
    clear_sessions_for_tests()
    session = start_session()
    result = handle_message(session.session_id, "Is Fikiri a fit for my business?")
    assert result.mode == "explore_fit"
    assert result.intake.get("active") is True
    assert "industry" in result.response.lower()


def test_hello_wow_okay_sequence_no_repeat_handoff():
    clear_sessions_for_tests()
    session = start_session()
    r1 = handle_message(session.session_id, "hello")
    r2 = handle_message(session.session_id, "wow")
    r3 = handle_message(session.session_id, "okay")
    assert "don't want to keep repeating" not in r3.response.lower()
    assert r1.response != r2.response
