"""Routing trace — flag, inline capture, and no-replay contract."""

import os
from unittest.mock import patch

import pytest

from company_chatbot import config
from company_chatbot.config import MODE_ANSWER, MODE_FALLBACK
from company_chatbot.modes import detect_mode
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def _reset_sessions():
    clear_sessions_for_tests()
    yield
    clear_sessions_for_tests()


@pytest.fixture
def trace_env(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_ROUTING_TRACE", "1")


@pytest.fixture
def no_trace_env(monkeypatch):
    monkeypatch.delenv("FIKIRI_SITE_BOT_ROUTING_TRACE", raising=False)


def test_routing_trace_flag_off_omits_trace_from_serialized_response(no_trace_env):
    session = start_session()
    result = handle_message(session.session_id, "What is your pricing?")
    payload = result.to_dict("v1")

    assert "routing_trace" not in payload
    assert result.routing_trace is None
    assert result.mode == MODE_ANSWER


def test_routing_trace_flag_on_includes_v1_schema(trace_env):
    session = start_session()
    result = handle_message(session.session_id, "What is your pricing?")
    payload = result.to_dict("v1")

    assert "routing_trace" in payload
    trace = payload["routing_trace"]
    assert trace["schema_version"] == "v1"
    assert trace["path"][0] == "guard"
    assert "mode" in trace["path"]
    assert "outcome" in trace["path"]
    assert trace["guard"]["attempted"] is True
    assert trace["mode"]["attempted"] is True
    assert trace["mode"]["matched_rule"] == "product_pricing_integrations"
    assert trace["outcome"]["mode"] == MODE_ANSWER


def test_routing_trace_fallback_records_null_matched_rule(trace_env):
    session = start_session()
    result = handle_message(session.session_id, "asdfghjkl qwerty")
    trace = result.routing_trace

    assert trace is not None
    assert trace.mode.detected == MODE_FALLBACK
    assert trace.mode.matched_rule is None
    assert result.mode == MODE_FALLBACK


def test_routing_trace_outcome_mode_separate_from_detected_mode_on_rescue(trace_env):
    session = start_session()
    result = handle_message(
        session.session_id,
        "we require a digital presence with automated lead attribution",
    )
    trace = result.routing_trace

    assert trace is not None
    assert trace.mode.detected == MODE_FALLBACK
    assert trace.mode.matched_rule is None
    assert result.mode == MODE_ANSWER
    assert trace.outcome.mode == MODE_ANSWER


def test_routing_trace_does_not_double_call_detect_mode(trace_env):
    calls = []

    def _counting_detect_mode(message, previous_query=None, *, routing_trace=None):
        calls.append((message, previous_query))
        return detect_mode(message, previous_query, routing_trace=routing_trace)

    session = start_session()
    with patch("company_chatbot.orchestrator.detect_mode", side_effect=_counting_detect_mode):
        handle_message(session.session_id, "What is your pricing?")

    assert len(calls) == 1


def test_detect_mode_records_matched_rule_when_trace_passed():
    from company_chatbot.routing_trace import RoutingTrace

    trace = RoutingTrace()
    mode = detect_mode("How much does Fikiri cost?", routing_trace=trace)

    assert mode == MODE_ANSWER
    assert trace.mode.matched_rule == "product_pricing_integrations"
    assert trace.mode.detected == MODE_ANSWER
    assert trace.mode.previous_query_used is False


def test_routing_trace_disabled_does_not_invoke_guard_recording(no_trace_env):
    from company_chatbot.guards import GuardContext, evaluate_guards
    from company_chatbot.routing_trace import RoutingTrace

    trace = RoutingTrace()
    evaluate_guards(GuardContext(turn_count=1, message="hello"), routing_trace=None)

    assert trace.path == []
    assert trace.guard.attempted is False


def test_config_routing_trace_defaults_off(monkeypatch):
    monkeypatch.delenv("FIKIRI_SITE_BOT_ROUTING_TRACE", raising=False)
    assert config.routing_trace_enabled() is False

    monkeypatch.setenv("FIKIRI_SITE_BOT_ROUTING_TRACE", "1")
    assert config.routing_trace_enabled() is True
