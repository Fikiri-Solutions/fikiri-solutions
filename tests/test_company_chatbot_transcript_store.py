"""Unit tests for company site bot transcript persistence."""

import json
import os

import pytest

from company_chatbot import config
from company_chatbot.schemas import HandoffMetadata, LeadAssessmentMetadata, LeadIntentMetadata, MessageResult
from company_chatbot.transcript_store import (
    _message_row,
    _session_detail_row,
    clear_transcript_tables_for_tests,
    ensure_site_chat_transcript_tables,
    get_transcript_session,
    is_persist_enabled,
    persist_message_turn,
    purge_expired_transcripts,
)
from core.database_optimization import db_optimizer

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def _reset_tables(monkeypatch):
    monkeypatch.delenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", raising=False)
    clear_transcript_tables_for_tests()
    yield
    clear_transcript_tables_for_tests()


def _sample_result() -> MessageResult:
    return MessageResult(
        mode="answer",
        response="Fikiri helps automate email and CRM workflows.",
        handoff=HandoffMetadata(
            applicable=True,
            primary="in_widget_form",
            secondary="/contact",
            handoff_type="contact",
        ),
        lead_intent=LeadIntentMetadata(),
        turn_count=1,
        grounded=True,
        confidence=0.82,
        sources=[{"id": "kb-1", "title": "Product overview"}],
        intake={"active": False, "slots": {"industry": "dental"}},
        lead_assessment=LeadAssessmentMetadata(
            score=4,
            tier="warm",
            signals=["product_interest"],
            synopsis="Warm lead interested in product.",
            recommended_handoff="/contact",
        ),
    )


def test_session_detail_and_message_rows_support_tuple_rows():
    session_tuple = (
        "site_tuple",
        "https://fikirisolutions.com/pricing",
        "2026-01-01T00:00:00+00:00",
        "2026-01-02T00:00:00+00:00",
        2,
        "answer",
        "warm",
        4,
        "Interested in product.",
        "/contact",
        "hash_ip",
        "hash_ua",
        "2026-01-01T00:00:00+00:00",
        "2026-01-02T00:00:00+00:00",
    )
    session = _session_detail_row(session_tuple)
    assert session["hashed_ip"] == "hash_ip"
    assert session["hashed_user_agent"] == "hash_ua"
    assert session["created_at"] == "2026-01-01T00:00:00+00:00"

    message_tuple = (
        "assistant",
        "Hello from Fikiri.",
        "answer",
        1,
        0.9,
        '["kb-1"]',
        '{"active": false}',
        '{"handoff_type": "contact"}',
        '{"tier": "warm", "score": 4}',
        "2026-01-01T00:00:01+00:00",
    )
    message = _message_row(message_tuple)
    assert message["role"] == "assistant"
    assert message["content"] == "Hello from Fikiri."
    assert message["grounded"] is True
    assert message["confidence"] == 0.9
    assert message["sources"] == ["kb-1"]
    assert message["handoff"]["handoff_type"] == "contact"
    assert message["lead_assessment"]["tier"] == "warm"


def test_persistence_disabled_means_no_db_write(monkeypatch):
    monkeypatch.delenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", raising=False)
    assert is_persist_enabled() is False

    calls = []

    def _track(query, params=None, fetch=True, **kwargs):
        calls.append(query)
        return []

    monkeypatch.setattr(db_optimizer, "execute_query", _track)
    persist_message_turn(
        session_id="site_disabled",
        user_message="hello",
        result=_sample_result(),
    )
    assert calls == []


def test_enabled_persistence_writes_session_and_messages(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    assert is_persist_enabled() is True

    persist_message_turn(
        session_id="site_enabled_1",
        user_message="What is Fikiri?",
        result=_sample_result(),
        source_page="https://fikirisolutions.com/pricing",
        client_ip="203.0.113.50",
        user_agent="pytest-agent/1.0",
    )

    payload = get_transcript_session("site_enabled_1")
    assert payload is not None
    session = payload["session"]
    assert session["session_id"] == "site_enabled_1"
    assert session["last_mode"] == "answer"
    assert session["latest_lead_tier"] == "warm"
    assert session["latest_lead_score"] == 4
    assert session["hashed_ip"]
    assert session["hashed_ip"] != "203.0.113.50"
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][1]["role"] == "assistant"
    assert payload["messages"][1]["grounded"] is True
    assert payload["messages"][1]["lead_assessment"]["tier"] == "warm"


def test_persistence_failure_does_not_raise(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")

    def _boom(*args, **kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(
        "company_chatbot.transcript_store._persist_message_turn_impl",
        _boom,
    )
    persist_message_turn(
        session_id="site_fail",
        user_message="hello",
        result=_sample_result(),
    )


def test_metadata_snapshots_serialize_safely(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    result = _sample_result()
    persist_message_turn(session_id="site_meta", user_message="pricing?", result=result)

    assistant = get_transcript_session("site_meta")["messages"][1]
    assert assistant["sources"][0]["title"] == "Product overview"
    assert assistant["intake"]["slots"]["industry"] == "dental"
    assert assistant["handoff"]["handoff_type"] == "contact"
    assert assistant["lead_assessment"]["recommended_handoff"] == "/contact"
    json.dumps(assistant)


def test_retention_config_default_is_90_days():
    assert config.transcript_retention_days() == 90


def test_purge_expired_transcripts_respects_retention(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setenv("FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS", "1")
    ensure_site_chat_transcript_tables()

    old_ts = "2020-01-01T00:00:00+00:00"
    db_optimizer.execute_query(
        """
        INSERT INTO site_chat_sessions (
            session_id, first_seen_at, last_seen_at, turn_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("site_old", old_ts, old_ts, 1, old_ts, old_ts),
        fetch=False,
    )
    removed = purge_expired_transcripts()
    assert removed == 1
    assert get_transcript_session("site_old") is None
