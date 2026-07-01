"""YAML scenario regression tests for the Fikiri site bot."""

import os
from pathlib import Path

import pytest
import yaml

from company_chatbot.grounding import clear_grounding_cache_for_tests
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.retrieval import clear_kb_cache_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")

SCENARIOS_PATH = Path(__file__).parent / "company_chatbot_scenarios" / "critical.yaml"


def _load_scenarios():
    data = yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return data.get("scenarios") or []


@pytest.fixture(autouse=True)
def reset_state():
    clear_sessions_for_tests()
    clear_kb_cache_for_tests()
    clear_grounding_cache_for_tests()
    yield
    clear_sessions_for_tests()
    clear_kb_cache_for_tests()
    clear_grounding_cache_for_tests()


@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_critical_scenario(scenario):
    session = start_session()
    last = None
    for message in scenario["messages"]:
        last = handle_message(session.session_id, message)

    assert last is not None
    if "expected_mode" in scenario:
        assert last.mode == scenario["expected_mode"]

    response_lower = last.response.lower()
    for phrase in scenario.get("must_include") or []:
        assert phrase.lower() in response_lower, f"missing '{phrase}' in: {last.response}"

    for phrase in scenario.get("must_not_include") or []:
        assert phrase.lower() not in response_lower, f"forbidden '{phrase}' in: {last.response}"

    expected_handoff = scenario.get("expected_handoff")
    if expected_handoff:
        assert last.handoff.applicable is True
        assert last.handoff.handoff_type == expected_handoff

    if scenario.get("intake_active") is True:
        assert last.intake.get("active") is True

    if scenario.get("intake_complete") is True:
        assert last.intake.get("complete") is True


def test_email_assistant_transcript_no_three_identical_fallbacks():
    session = start_session()
    messages = [
        "Hello",
        "I need to find out about the email assisant",
        "Im asking about one of the producsts, the AI email assistant",
        "youre stuck in a loop",
        "help me",
    ]
    generic_snippet = "i'm not sure i understood"
    generic_count = 0
    last = None
    for message in messages:
        last = handle_message(session.session_id, message)
        if generic_snippet in last.response.lower():
            generic_count += 1

    assert generic_count < 3
    assert last is not None
    assert last.handoff.applicable is True
    assert "stuck" in last.response.lower() or "fikirisolutions.com/intake" in last.response.lower()
