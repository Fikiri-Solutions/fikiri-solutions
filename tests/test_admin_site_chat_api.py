"""API tests for staff-only site chat transcript endpoints."""

import json
import os

import pytest
from flask import Flask

from company_chatbot.orchestrator import clear_sessions_for_tests
from company_chatbot.schemas import HandoffMetadata, LeadAssessmentMetadata, LeadIntentMetadata, MessageResult
from company_chatbot.transcript_store import clear_transcript_tables_for_tests, persist_message_turn
from routes.admin_site_chat_api import admin_site_chat_bp
from routes.site_chatbot_api import site_chatbot_bp

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture
def client():
    clear_sessions_for_tests()
    clear_transcript_tables_for_tests()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(site_chatbot_bp)
    app.register_blueprint(admin_site_chat_bp)
    yield app.test_client()
    clear_sessions_for_tests()
    clear_transcript_tables_for_tests()


def _seed_transcript(session_id: str = "site_admin_demo"):
    result = MessageResult(
        mode="contact",
        response="You can reach us at info@fikirisolutions.com.",
        handoff=HandoffMetadata(applicable=True, secondary="/contact", handoff_type="contact"),
        lead_intent=LeadIntentMetadata(),
        turn_count=1,
        lead_assessment=LeadAssessmentMetadata(
            score=3,
            tier="possible",
            synopsis="Asked to talk with the team.",
            recommended_handoff="/contact",
        ),
    )
    persist_message_turn(
        session_id=session_id,
        user_message="I want to talk to someone",
        result=result,
        source_page="https://fikirisolutions.com/",
        client_ip="203.0.113.77",
        user_agent="pytest",
    )


def test_unauthenticated_admin_transcript_request_rejected(client):
    response = client.get("/api/admin/site-chat/sessions")
    assert response.status_code == 401
    body = json.loads(response.data)
    assert body["code"] == "AUTHENTICATION_REQUIRED"


def test_non_admin_admin_transcript_request_rejected(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 42)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: False)
    monkeypatch.setattr("routes.admin_site_chat_api._get_user_role", lambda _uid: "member")

    response = client.get("/api/admin/site-chat/sessions")
    assert response.status_code == 403
    body = json.loads(response.data)
    assert body["code"] == "FORBIDDEN"


def test_admin_can_list_transcript_sessions(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: True)
    _seed_transcript()

    response = client.get("/api/admin/site-chat/sessions")
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["success"] is True
    sessions = body["data"]["sessions"]
    assert len(sessions) >= 1
    assert sessions[0]["session_id"] == "site_admin_demo"
    assert sessions[0]["latest_lead_tier"] == "possible"


def test_admin_can_read_one_transcript_and_audit(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 7)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: True)
    _seed_transcript("site_read_one")

    response = client.get("/api/admin/site-chat/sessions/site_read_one")
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["session"]["session_id"] == "site_read_one"
    assert len(body["data"]["messages"]) == 2

    from core.database_optimization import db_optimizer

    audits = db_optimizer.execute_query(
        """
        SELECT session_id, reader_user_id, action
        FROM site_chat_transcript_reads
        WHERE session_id = ? AND action = ?
        """,
        ("site_read_one", "read"),
    )
    assert len(audits) == 1


def test_admin_can_export_copy_friendly_transcript(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 9)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: True)
    _seed_transcript("site_export_one")

    response = client.get("/api/admin/site-chat/sessions/site_export_one/export")
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["format"] == "text"
    assert "Fikiri Site Chat Transcript" in body["data"]["content"]
    assert "site_export_one" in body["data"]["content"]

    from core.database_optimization import db_optimizer

    audits = db_optimizer.execute_query(
        """
        SELECT action FROM site_chat_transcript_reads
        WHERE session_id = ? AND action = ?
        """,
        ("site_export_one", "export"),
    )
    assert len(audits) == 1


def test_owner_role_can_read_transcripts(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 3)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: False)
    monkeypatch.setattr("routes.admin_site_chat_api._get_user_role", lambda _uid: "owner")
    _seed_transcript("site_owner_read")

    response = client.get("/api/admin/site-chat/sessions/site_owner_read")
    assert response.status_code == 200


def _seed_miss_transcript(session_id: str = "site_miss_demo"):
    result = MessageResult(
        mode="fallback",
        response="I'm not sure I understood. You can ask about Fikiri's product.",
        handoff=HandoffMetadata(applicable=False),
        lead_intent=LeadIntentMetadata(),
        turn_count=1,
        grounded=False,
        confidence=0.0,
        lead_assessment=LeadAssessmentMetadata(
            score=8,
            tier="warm",
            synopsis="Pain around inbox overload.",
            recommended_handoff="/intake",
        ),
    )
    persist_message_turn(
        session_id=session_id,
        user_message="I'm drowning in emails and nobody follows up",
        result=result,
        source_page="https://fikirisolutions.com/",
    )
    follow = MessageResult(
        mode="fallback",
        response="Handoff message",
        handoff=HandoffMetadata(applicable=True, secondary="/intake", handoff_type="intake"),
        lead_intent=LeadIntentMetadata(),
        turn_count=2,
        grounded=False,
        confidence=0.0,
        lead_assessment=LeadAssessmentMetadata(score=8, tier="warm", synopsis="Frustrated"),
    )
    persist_message_turn(
        session_id=session_id,
        user_message="you're stuck in a loop",
        result=follow,
    )


def test_admin_can_list_misses(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 11)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: True)
    _seed_miss_transcript()

    response = client.get("/api/admin/site-chat/misses")
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["success"] is True
    misses = body["data"]["misses"]
    assert len(misses) >= 1
    assert misses[0]["priority"] in {"critical", "high", "medium", "low"}
    assert "warm_lead_ungrounded" in misses[0]["signals"] or "ungrounded" in misses[0]["signals"]


def test_admin_can_export_miss_cursor_patch(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "1")
    monkeypatch.setattr("routes.admin_site_chat_api.get_current_user_id", lambda: 12)
    monkeypatch.setattr("routes.admin_site_chat_api._is_admin_user", lambda _uid: True)
    _seed_miss_transcript("site_miss_export")

    list_resp = client.get("/api/admin/site-chat/misses")
    miss_id = json.loads(list_resp.data)["data"]["misses"][0]["miss_id"]

    response = client.get(f"/api/admin/site-chat/misses/{miss_id}/export")
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["format"] == "cursor"
    assert "HUMAN APPROVAL REQUIRED" in body["data"]["content"]
    assert "suggested eval case" in body["data"]["content"].lower() or "Suggested eval case" in body["data"]["content"]

    proposal_resp = client.get(f"/api/admin/site-chat/misses/{miss_id}")
    assert proposal_resp.status_code == 200
    proposal = json.loads(proposal_resp.data)["data"]["proposal"]
    assert proposal["requires_human_approval"] is True
    assert proposal["suggested_eval_case"]["query"]
