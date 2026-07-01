"""Integration tests for first-party site chat API routes."""

import json
import os

import pytest
from flask import Flask

from company_chatbot.orchestrator import clear_sessions_for_tests
from company_chatbot.rate_limit import clear_rate_limits_for_tests
from company_chatbot.transcript_store import clear_transcript_tables_for_tests, get_transcript_session
from routes.site_chatbot_api import site_chatbot_bp

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture
def client():
    clear_sessions_for_tests()
    clear_rate_limits_for_tests()
    clear_transcript_tables_for_tests()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(site_chatbot_bp)
    yield app.test_client()
    clear_sessions_for_tests()
    clear_rate_limits_for_tests()
    clear_transcript_tables_for_tests()


def _data(response):
    body = json.loads(response.data)
    assert body.get("success") is True
    return body["data"]


def test_session_start_returns_session_and_schema(client):
    response = client.post("/api/site/chat/session/start")
    assert response.status_code == 200
    data = _data(response)
    assert data["schema_version"] == "v1"
    assert data["session_id"].startswith("site_")
    assert data["welcome"]


def test_message_requires_session_and_body(client):
    response = client.post("/api/site/chat/message", json={})
    assert response.status_code == 400

    start = _data(client.post("/api/site/chat/session/start"))
    response = client.post(
        "/api/site/chat/message",
        json={"session_id": start["session_id"], "message": "   "},
    )
    assert response.status_code == 400


def test_message_returns_mode_response_handoff_no_api_key(client):
    start = _data(client.post("/api/site/chat/session/start"))
    response = client.post(
        "/api/site/chat/message",
        json={"session_id": start["session_id"], "message": "I want to talk to someone"},
    )
    assert response.status_code == 200
    data = _data(response)
    assert data["schema_version"] == "v1"
    assert data["session_id"] == start["session_id"]
    assert data["mode"] == "contact"
    assert isinstance(data["response"], str) and data["response"]
    assert data["handoff"]["applicable"] is True
    assert data["handoff"]["handoff_type"] == "contact"
    assert data["handoff"]["secondary"] == "/contact"
    assert "lead_intent" in data
    assert "lead_assessment" in data
    assert data["lead_assessment"]["tier"] in ("casual", "possible", "warm", "hot")
    assert isinstance(data["lead_assessment"]["synopsis"], str)
    assert data["lead_assessment"]["recommended_handoff"] == "/contact"


def test_message_unknown_session_404(client):
    response = client.post(
        "/api/site/chat/message",
        json={"session_id": "site_missing", "message": "hello"},
    )
    assert response.status_code == 404


def test_fit_intake_includes_warm_lead_assessment(client):
    start = _data(client.post("/api/site/chat/session/start"))
    data = _data(
        client.post(
            "/api/site/chat/message",
            json={
                "session_id": start["session_id"],
                "message": "Is Fikiri a fit for my business?",
            },
        )
    )
    assessment = data["lead_assessment"]
    assert assessment["score"] >= 3
    assert assessment["tier"] in ("possible", "warm", "hot")
    assert "business_context" in assessment["signals"]
    assert assessment["recommended_handoff"] == "/intake"


def test_workflow_audit_starts_intake(client):
    start = _data(client.post("/api/site/chat/session/start"))
    data = _data(
        client.post(
            "/api/site/chat/message",
            json={"session_id": start["session_id"], "message": "workflow audit please"},
        )
    )
    assert data["mode"] == "workflow_audit"
    assert data.get("intake", {}).get("active") is True
    assert data["handoff"]["secondary"] == "/intake"
    assert "lead_assessment" in data


def _error_body(response):
    body = json.loads(response.data)
    assert body.get("success") is False
    return body


def test_kill_switch_returns_stable_disabled_response(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_ENABLED", "false")
    response = client.post("/api/site/chat/session/start")
    assert response.status_code == 503
    body = _error_body(response)
    assert body["code"] == "SITE_BOT_DISABLED"
    assert "unavailable" in body["error"].lower()


def test_rate_limit_returns_stable_friendly_response(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_BURST", "1")
    clear_rate_limits_for_tests()

    first = client.post("/api/site/chat/session/start")
    assert first.status_code == 200

    second = client.post("/api/site/chat/session/start")
    assert second.status_code == 429
    body = _error_body(second)
    assert body["code"] == "RATE_LIMIT_EXCEEDED"
    assert "too quickly" in body["error"].lower()
    assert second.headers.get("Retry-After")


def test_site_chat_works_when_transcript_persistence_disabled(client, monkeypatch):
    monkeypatch.delenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", raising=False)
    start = _data(client.post("/api/site/chat/session/start"))
    data = _data(
        client.post(
            "/api/site/chat/message",
            json={"session_id": start["session_id"], "message": "hello"},
        )
    )
    assert data["schema_version"] == "v1"
    assert get_transcript_session(start["session_id"]) is None


def test_site_chat_persists_transcript_when_enabled(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    start = _data(client.post("/api/site/chat/session/start"))
    _data(
        client.post(
            "/api/site/chat/message",
            json={"session_id": start["session_id"], "message": "I want to talk to someone"},
        )
    )
    payload = get_transcript_session(start["session_id"])
    assert payload is not None
    assert len(payload["messages"]) == 2


def test_site_chat_succeeds_when_transcript_write_fails(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")

    def _boom(**kwargs):
        raise RuntimeError("transcript db down")

    monkeypatch.setattr("company_chatbot.transcript_store._persist_message_turn_impl", _boom)

    start = _data(client.post("/api/site/chat/session/start"))
    data = _data(
        client.post(
            "/api/site/chat/message",
            json={"session_id": start["session_id"], "message": "hello"},
        )
    )
    assert data["schema_version"] == "v1"
    assert data["response"]
