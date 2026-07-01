"""Unit tests for company site bot session store."""

import os
from datetime import datetime, timezone

import pytest

from company_chatbot import config
from company_chatbot.intake import IntakeSlots
from company_chatbot.orchestrator import SessionState
from company_chatbot.session_store import (
    clear_sessions_for_tests,
    load_session,
    reset_session_store_backend_for_tests,
    save_session,
)

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def _reset_store():
    reset_session_store_backend_for_tests()
    yield
    clear_sessions_for_tests()


def _sample_state(session_id: str = "site_test123") -> SessionState:
    return SessionState(
        session_id=session_id,
        turn_count=2,
        last_mode=config.MODE_ANSWER,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        intake_active=True,
        intake_mode=config.MODE_EXPLORE_FIT,
        intake_slots=IntakeSlots(industry="dental", main_pain="missed leads"),
        response_history=["hello", "welcome back"],
        last_user_message="pricing?",
    )


def test_session_store_save_and_load_roundtrip():
    state = _sample_state()
    save_session(state)
    loaded = load_session(state.session_id)
    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.turn_count == 2
    assert loaded.last_mode == config.MODE_ANSWER
    assert loaded.intake_active is True
    assert loaded.intake_slots.industry == "dental"
    assert loaded.response_history == ["hello", "welcome back"]
    assert loaded.last_user_message == "pricing?"


def test_session_store_unknown_session_returns_none():
    assert load_session("site_missing") is None


def test_session_ttl_default_config():
    assert config.session_ttl_seconds() == 86400


def test_session_ttl_env_override(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_SESSION_TTL_SECONDS", "120")
    assert config.session_ttl_seconds() == 120


def test_in_memory_fallback_in_test_mode(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_TEST_MODE", "1")
    state = _sample_state("site_memory_only")
    save_session(state)
    loaded = load_session("site_memory_only")
    assert loaded is not None
    assert loaded.session_id == "site_memory_only"


def test_clear_sessions_for_tests():
    save_session(_sample_state("site_a"))
    save_session(_sample_state("site_b"))
    clear_sessions_for_tests()
    assert load_session("site_a") is None
    assert load_session("site_b") is None
