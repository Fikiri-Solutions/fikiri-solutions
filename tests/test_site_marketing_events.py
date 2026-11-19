"""Anonymous public marketing funnel events."""

from __future__ import annotations

import os
import uuid

import pytest
from cryptography.fernet import Fernet
from flask import Flask

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.database_optimization import db_optimizer
from core.site_marketing_events import (
    build_marketing_funnel_summary,
    ensure_site_marketing_event_tables,
    ingest_site_marketing_events,
)
from routes.site_marketing_events_api import site_marketing_events_bp


def _session_ref(prefix: str = "sess") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SITE_MARKETING_EVENTS_ENABLED", "true")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    ensure_site_marketing_event_tables()
    # Isolate from leftover rows in local/shared SQLite.
    try:
        db_optimizer.execute_query("DELETE FROM site_marketing_events", fetch=False)
    except Exception:
        pass
    yield


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(site_marketing_events_bp)
    return app.test_client()


def test_ingest_approved_events():
    result = ingest_site_marketing_events(
        session_ref=_session_ref("abc"),
        events=[
            {"event_name": "intake_started", "properties": {"source_kind": "organic"}},
            {
                "event_name": "intake_step_viewed",
                "properties": {"step_id": "services"},
                "dedupe_key": "services",
            },
        ],
        ensure_tables=True,
    )
    assert result["accepted"] == 2
    assert result["rejected"] == 0


def test_dedupe_same_session_step():
    ref = _session_ref("dedupe")
    first = ingest_site_marketing_events(
        session_ref=ref,
        events=[
            {
                "event_name": "intake_step_viewed",
                "properties": {"step_id": "contact"},
                "dedupe_key": "contact",
            }
        ],
    )
    second = ingest_site_marketing_events(
        session_ref=ref,
        events=[
            {
                "event_name": "intake_step_viewed",
                "properties": {"step_id": "contact"},
                "dedupe_key": "contact",
            }
        ],
    )
    assert first["accepted"] == 1
    assert second["accepted"] == 0
    assert second["duplicates"] == 1


def test_rejects_prohibited_properties():
    result = ingest_site_marketing_events(
        session_ref=_session_ref("pii"),
        events=[
            {
                "event_name": "intake_started",
                "properties": {"email": "a@b.co"},
            }
        ],
    )
    assert result["accepted"] == 0
    assert result["rejected"] == 1


def test_rejects_unknown_event():
    result = ingest_site_marketing_events(
        session_ref=_session_ref("unknown"),
        events=[{"event_name": "page_view", "properties": {}}],
    )
    assert result["accepted"] == 0
    assert result["rejected"] == 1


def test_disabled_writes_nothing(monkeypatch):
    monkeypatch.setenv("SITE_MARKETING_EVENTS_ENABLED", "false")
    result = ingest_site_marketing_events(
        session_ref=_session_ref("disabled"),
        events=[{"event_name": "chatbot_opened", "properties": {"path_bucket": "/"}}],
    )
    assert result["accepted"] == 0
    assert result["events_enabled"] is False


def test_public_post_endpoint(client):
    response = client.post(
        "/api/site/events",
        json={
            "session_ref": _session_ref("http"),
            "events": [
                {
                    "event_name": "chatbot_opened",
                    "properties": {"path_bucket": "/pricing"},
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["accepted"] == 1


def test_funnel_summary_shape():
    ingest_site_marketing_events(
        session_ref=_session_ref("summary"),
        events=[
            {"event_name": "intake_started", "properties": {"source_kind": "site_chatbot"}},
            {"event_name": "intake_submitted", "properties": {"source_kind": "site_chatbot"}},
            {"event_name": "chatbot_opened", "properties": {"path_bucket": "/"}},
            {"event_name": "chatbot_first_message", "properties": {}},
        ],
    )
    summary = build_marketing_funnel_summary(lookback_days=7)
    assert summary["events_enabled"] is True
    assert summary["intake"]["starts"] >= 1
    assert summary["intake"]["submitted_events"] >= 1
    assert summary["chatbot"]["opened"] >= 1
    assert "notes" in summary
