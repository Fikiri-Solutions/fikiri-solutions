"""Product analytics ingestion security tests (Gate 2)."""

from __future__ import annotations

import json
import os

import pytest
from cryptography.fernet import Fernet
from flask import Flask

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.product_analytics_ingest import ingest_product_events
from core.product_analytics_store import (
    cleanup_expired_product_events,
    ensure_product_analytics_tables,
    tables_available,
)
from routes.product_analytics_api import product_analytics_bp


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    ensure_product_analytics_tables()
    yield
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(product_analytics_bp)

    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            return {"user_id": 42, "type": "access", "jti": "pa-jti"}

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.product_analytics_api.get_current_user_id", lambda: 42)
    monkeypatch.setattr("routes.product_analytics_api.get_actor_user_id", lambda: 42)
    monkeypatch.setattr("routes.product_analytics_api.is_impersonating", lambda: False)
    return app.test_client()


def _auth():
    return {"Authorization": "Bearer pa-token", "Content-Type": "application/json"}


def test_disabled_writes_nothing(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[{"event_name": "feature.opened", "properties": {"feature_key": "crm"}}],
        ensure_tables=True,
    )
    assert result["accepted"] == 0
    assert result["analytics_enabled"] is False
    assert result["analytics_available"] is False


def test_ingest_approved_event():
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[
            {
                "event_name": "feature.opened",
                "event_source": "client",
                "properties": {"feature_key": "crm"},
            }
        ],
        ensure_tables=True,
    )
    assert result["analytics_available"] is True
    assert result["accepted"] == 1
    assert result["rejected"] == 0


def test_impersonation_excluded():
    result = ingest_product_events(
        tenant_id=99,
        actor_user_id=1,
        events=[{"event_name": "session.started", "properties": {}}],
        impersonating=True,
        ensure_tables=True,
    )
    assert result["accepted"] == 0
    assert result.get("excluded") == "IMPERSONATION"


def test_platform_admin_surface_excluded():
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[{"event_name": "feature.opened", "properties": {"feature_key": "dashboard"}}],
        platform_admin_surface=True,
        ensure_tables=True,
    )
    assert result["accepted"] == 0
    assert result.get("excluded") == "PLATFORM_ADMIN_SURFACE"


def test_prohibited_property_rejects_whole_event():
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[
            {
                "event_name": "feature.opened",
                "properties": {"feature_key": "crm", "token": "sekrit"},
            }
        ],
        ensure_tables=True,
    )
    assert result["accepted"] == 0
    assert result["rejected"] == 1
    assert result["rejection_reasons"][0]["reason"] == "PROHIBITED_PROPERTY"


def test_client_identity_fields_stripped_then_accepted():
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[
            {
                "event_name": "feature.opened",
                "properties": {"feature_key": "crm", "tenant_id": 999},
            }
        ],
        ensure_tables=True,
    )
    assert result["accepted"] == 1


def test_storage_unavailable_shape(monkeypatch):
    monkeypatch.setattr(
        "core.product_analytics_ingest.tables_available",
        lambda: False,
    )
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[{"event_name": "feature.opened", "properties": {"feature_key": "crm"}}],
    )
    assert result["accepted"] == 0
    assert result["rejected"] == 0
    assert result["analytics_available"] is False


def test_route_authenticated_ingest(client):
    resp = client.post(
        "/api/analytics/events",
        headers=_auth(),
        data=json.dumps(
            {
                "events": [
                    {
                        "event_name": "workflow.started",
                        "properties": {"workflow_key": "lead_capture", "feature_key": "crm"},
                    }
                ]
            }
        ),
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)["data"]
    assert body["accepted"] == 1


def test_route_impersonation_excluded(client, monkeypatch):
    monkeypatch.setattr("routes.product_analytics_api.is_impersonating", lambda: True)
    resp = client.post(
        "/api/analytics/events",
        headers=_auth(),
        data=json.dumps(
            {"events": [{"event_name": "session.started", "properties": {}}]}
        ),
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)["data"]
    assert body["accepted"] == 0
    assert body.get("excluded") == "IMPERSONATION"


def test_cleanup_bounded():
    assert tables_available()
    result = cleanup_expired_product_events(batch_size=10)
    assert result["success"] is True
    assert "deleted" in result


def test_outcome_client_source_rejected():
    result = ingest_product_events(
        tenant_id=42,
        actor_user_id=42,
        events=[
            {
                "event_name": "outcome.lead_captured",
                "event_source": "client",
                "properties": {"feature_key": "crm", "completed": True},
            }
        ],
        ensure_tables=True,
    )
    assert result["accepted"] == 0
    assert result["rejected"] == 1


def test_destructive_still_off():
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}
