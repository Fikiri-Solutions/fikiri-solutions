"""Unit tests for transcript miss review and alias proposals (Phase 6d)."""

from __future__ import annotations

import os

import pytest

from company_chatbot import config
from company_chatbot.miss_review import (
    TranscriptTurn,
    build_alias_proposal,
    detect_miss_signals,
    fetch_session_turns,
    miss_id_for,
)
from company_chatbot.retrieval import clear_kb_cache_for_tests

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def reset_kb():
    clear_kb_cache_for_tests()
    yield
    clear_kb_cache_for_tests()


def _turn(**kwargs) -> TranscriptTurn:
    defaults = {
        "session_id": "site_test",
        "turn_index": 1,
        "user_message": "I'm drowning in emails",
        "assistant_message": "I'm not sure I understood.",
        "mode": config.MODE_FALLBACK,
        "grounded": False,
        "confidence": 0.0,
        "lead_assessment": {"tier": "warm", "score": 7},
    }
    defaults.update(kwargs)
    return TranscriptTurn(**defaults)


def test_detect_miss_signals_warm_lead_ungrounded():
    miss = detect_miss_signals(_turn())
    assert "ungrounded" in miss.signals
    assert "fallback_used" in miss.signals
    assert "warm_lead_ungrounded" in miss.signals
    assert miss.priority in {"critical", "high"}


def test_detect_miss_signals_frustration_followup():
    miss = detect_miss_signals(
        _turn(
            next_user_message="you're stuck in a loop",
            lead_assessment={"tier": "casual", "score": 1},
        )
    )
    assert "user_frustration_followup" in miss.signals


def test_build_alias_proposal_requires_human_approval():
    turn = _turn()
    miss = detect_miss_signals(turn)
    proposal = build_alias_proposal(turn, miss)
    assert proposal.requires_human_approval is True
    assert proposal.status == "proposal"
    assert proposal.suggested_alias
    assert proposal.suggested_chunk_ids
    assert proposal.suggested_eval_case["query"] == turn.user_message
    assert "HUMAN APPROVAL REQUIRED" in proposal.cursor_patch
    assert "tests/company_chatbot_retrieval_eval.yaml" in proposal.cursor_patch


def test_miss_id_roundtrip():
    assert miss_id_for("site_abc", 2) == "site_abc:2"


def test_fetch_session_turns_reads_tuple_rows(monkeypatch):
    rows = [
        (
            "user",
            "I'm drowning in emails",
            None,
            None,
            None,
            None,
            None,
            None,
            "2026-01-01T00:00:00+00:00",
        ),
        (
            "assistant",
            "I can help with inbox automation.",
            config.MODE_FALLBACK,
            0,
            0.2,
            None,
            None,
            '{"tier": "warm", "score": 7}',
            "2026-01-01T00:00:01+00:00",
        ),
    ]

    monkeypatch.setattr(
        "company_chatbot.miss_review.db_optimizer.execute_query",
        lambda *args, **kwargs: rows,
    )
    monkeypatch.setattr(
        "company_chatbot.miss_review.ensure_site_chat_transcript_tables",
        lambda: None,
    )

    turns = fetch_session_turns("site_tuple")
    assert len(turns) == 1
    assert turns[0].user_message == "I'm drowning in emails"
    assert turns[0].assistant_message == "I can help with inbox automation."
    assert turns[0].mode == config.MODE_FALLBACK
    assert turns[0].grounded is False
    assert turns[0].confidence == 0.2
    assert turns[0].lead_assessment == {"tier": "warm", "score": 7}
