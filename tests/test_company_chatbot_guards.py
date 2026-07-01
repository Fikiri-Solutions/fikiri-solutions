"""Unit tests for site bot conversation guards."""

import os

import pytest

from company_chatbot.guards import (
    GuardContext,
    MAX_TURN_CAP,
    build_guard_handoff_message,
    evaluate_guards,
    would_repeat_too_many_times,
)
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def reset_sessions():
    clear_sessions_for_tests()
    yield
    clear_sessions_for_tests()


def test_turn_cap_guard_triggers():
    result = evaluate_guards(GuardContext(turn_count=MAX_TURN_CAP, message="hello"))
    assert result.suggest_handoff is True
    assert result.reason == "turn_cap"


def test_frustration_guard_triggers():
    result = evaluate_guards(
        GuardContext(turn_count=2, message="I already told you, stop asking")
    )
    assert result.suggest_handoff is True
    assert result.reason == "frustration"


def test_low_information_during_intake_not_handoff():
    result = evaluate_guards(
        GuardContext(turn_count=2, message="?", intake_active=True)
    )
    assert result.triggered is True
    assert result.suggest_handoff is False


def test_repeat_guard_blocks_when_user_repeats_themselves():
    history = ["Same reply."]
    assert would_repeat_too_many_times(
        history,
        "Same reply.",
        last_user_message="hello",
        current_user_message="hello",
    ) is True
    assert would_repeat_too_many_times(
        history,
        "Same reply.",
        last_user_message="hello",
        current_user_message="okay",
    ) is False
    assert would_repeat_too_many_times(["One"], "Two") is False


def test_repeat_guard_blocks_identical_bot_fallback_loop():
    generic = (
        "I'm not sure I understood. You can ask about Fikiri's product, "
        "explore whether we're a fit, request a workflow audit, or ask to contact our team."
    )
    history = [generic, generic]
    assert would_repeat_too_many_times(history, generic) is True


def test_frustration_guard_triggers_on_loop_complaint():
    for message in ("youre stuck in a loop", "you're stuck in a loop", "you already said that"):
        result = evaluate_guards(GuardContext(turn_count=4, message=message))
        assert result.suggest_handoff is True
        assert result.reason == "frustration"


def test_help_me_after_fallback_triggers_handoff():
    generic = "I'm not sure I understood."
    result = evaluate_guards(
        GuardContext(
            turn_count=3,
            message="help me",
            response_history=[generic, generic],
        )
    )
    assert result.suggest_handoff is True
    assert result.reason == "help_after_stuck"

    stuck = "You're right — I got stuck there."
    result = evaluate_guards(
        GuardContext(
            turn_count=5,
            message="help me",
            response_history=["Hi!", "answer", stuck],
        )
    )
    assert result.suggest_handoff is True


def test_frustration_exit_message_acknowledges_stuck_loop():
    session = start_session()
    handle_message(session.session_id, "I need to find out about the email assisant")
    handle_message(session.session_id, "Im asking about one of the producsts, the AI email assistant")
    result = handle_message(session.session_id, "youre stuck in a loop")
    assert result.handoff.applicable is True
    assert "stuck" in result.response.lower()
    assert "workflow audit" in result.response.lower()


def test_frustration_guard_triggers_on_not_helping():
    result = evaluate_guards(GuardContext(turn_count=3, message="this isn't helping"))
    assert result.suggest_handoff is True
    assert result.reason == "frustration"


def test_help_me_standalone_uses_conversational_not_generic_fallback():
    from company_chatbot.conversational import conversational_reply

    reply = conversational_reply("help me")
    assert reply is not None
    assert "email assistant" in reply.lower()
    assert "i'm not sure i understood" not in reply.lower()


def test_frustration_exits_intake_gracefully():
    session = start_session()
    handle_message(session.session_id, "workflow audit")
    handle_message(session.session_id, "landscaping")
    result = handle_message(session.session_id, "I already told you, stop asking")
    assert "fikirisolutions.com/intake" in result.response
    assert result.handoff.applicable is True


def test_guard_handoff_message_includes_intake_path():
    text = build_guard_handoff_message("frustration")
    assert "fikirisolutions.com/intake" in text
    assert "stuck" in text.lower()
