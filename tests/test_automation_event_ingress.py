"""Tests for Windmill CE → Flask automation ingress boundary."""

from __future__ import annotations

import json

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, ensure_admin_audit_table, list_admin_audit
from core.automation_event_ingress import (
    STATUS_PROCESSING,
    apply_automation_event_receipts_migration_for_tests,
    clear_automation_receipts_for_tests,
    handle_automation_test_event,
    IngressPrincipal,
    receipts_table_ready,
)
from core.database_optimization import db_optimizer
from routes.internal_automation_api import internal_automation_bp
from tests.admin_test_util import ensure_operator_user_rows


def _base_event(**overrides):
    body = {
        "event_id": "evt_test_001",
        "event_type": "automation.test.received",
        "event_version": 1,
        "source": "windmill-dev",
        "tenant_id": None,
        "correlation_id": "corr_test_001",
        "occurred_at": "2026-08-02T20:00:00Z",
        "data": {"message": "development smoke test"},
    }
    body.update(overrides)
    return body


@pytest.fixture
def client(monkeypatch):
    ensure_operator_user_rows((7, 1))
    ensure_admin_audit_table()
    clear_admin_audit_for_tests()
    apply_automation_event_receipts_migration_for_tests()
    assert receipts_table_ready()
    clear_automation_receipts_for_tests()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(internal_automation_bp)
    yield app.test_client()
    clear_automation_receipts_for_tests()
    clear_admin_audit_for_tests()


def _mock_key(monkeypatch, *, scopes, user_id=7, api_key_id=42):
    def _validate(_key):
        return {
            "api_key_id": api_key_id,
            "user_id": user_id,
            "key_prefix": "abcd1234",
            "scopes": scopes,
            "name": "automation-dev",
        }

    monkeypatch.setattr(
        "routes.internal_automation_api.api_key_manager.validate_api_key",
        _validate,
    )


def test_unauthenticated_rejected(client):
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
    )
    assert resp.status_code == 401
    assert resp.get_json()["error_code"] == "MISSING_API_KEY"
    assert list_admin_audit(limit=10)["items"] == []


def test_invalid_api_key_no_permanent_audit(client, monkeypatch):
    monkeypatch.setattr(
        "routes.internal_automation_api.api_key_manager.validate_api_key",
        lambda _k: None,
    )
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers={"X-API-Key": "fik_invalid"},
    )
    assert resp.status_code == 401
    assert list_admin_audit(limit=10)["items"] == []


def test_insufficient_scope_forbidden(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["chatbot:query"])
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error_code"] == "INSUFFICIENT_SCOPE"
    items = list_admin_audit(limit=20)["items"]
    assert any(i["action"] == "automation.ingress.denied" for i in items)


def test_valid_service_request_accepted(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["duplicate"] is False
    assert body["result_code"] == "automation_test_received"
    assert body["correlation_id"] == "corr_test_001"
    items = list_admin_audit(limit=20)["items"]
    assert any(i["action"] == "automation.ingress.accepted" for i in items)


def test_unsupported_event_type(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event(event_type="automation.other")),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "UNSUPPORTED_EVENT_TYPE"


def test_unsupported_event_version(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event(event_version=99)),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "UNSUPPORTED_EVENT_VERSION"


def test_malformed_tenant_rejected(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event(tenant_id="not-a-number")),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_TENANT"


def test_duplicate_event_idempotent(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    headers = {"X-API-Key": "fik_test"}
    first = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers=headers,
    )
    second = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers=headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert second.get_json()["result_code"] == "automation_test_received"
    accepted = [i for i in list_admin_audit(limit=50)["items"] if i["action"] == "automation.ingress.accepted"]
    assert len(accepted) == 1


def test_payload_hash_conflict(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    headers = {"X-API-Key": "fik_test"}
    client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event()),
        content_type="application/json",
        headers=headers,
    )
    conflict = client.post(
        "/api/internal/automation/events",
        data=json.dumps(_base_event(data={"message": "different"})),
        content_type="application/json",
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.get_json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_oversized_body_rejected(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["automation:ingress"])
    huge = _base_event(data={"message": "x" * 20_000})
    resp = client.post(
        "/api/internal/automation/events",
        data=json.dumps(huge),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code in (400, 413)
    code = resp.get_json().get("error_code")
    assert code in ("DATA_TOO_LARGE", "PAYLOAD_TOO_LARGE")


def test_serialized_first_wins_ownership(monkeypatch):
    """Simulate concurrent claim: second INSERT loses UNIQUE(source, event_id).

    SQLite proves ownership logic; true concurrent PostgreSQL remains a
    production validation item.
    """
    ensure_admin_audit_table()
    apply_automation_event_receipts_migration_for_tests()
    clear_automation_receipts_for_tests()
    clear_admin_audit_for_tests()

    principal = IngressPrincipal(
        user_id=1, api_key_id=9, key_prefix="abcd", scopes=["automation:ingress"]
    )
    payload = _base_event(event_id="evt_race_1", correlation_id="corr_race_1")

    first = handle_automation_test_event(payload, principal=principal)
    assert first.http_status == 200
    assert first.body["duplicate"] is False

    # Leave a processing row and ensure duplicate does not reset it.
    db_optimizer.execute_query(
        """
        UPDATE automation_event_receipts
        SET status = ?, result_code = NULL, completed_at = NULL
        WHERE source = ? AND event_id = ?
        """,
        (STATUS_PROCESSING, "windmill-dev", "evt_race_1"),
        fetch=False,
    )
    second = handle_automation_test_event(payload, principal=principal)
    assert second.http_status == 202
    assert second.body["status"] == STATUS_PROCESSING
    assert second.body["duplicate"] is True

    row = db_optimizer.execute_query(
        "SELECT status FROM automation_event_receipts WHERE event_id = ?",
        ("evt_race_1",),
    )[0]
    assert row["status"] == STATUS_PROCESSING
