"""Tests for Flask → Windmill normalize-leads trigger."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, ensure_admin_audit_table, list_admin_audit
from core.automation_event_ingress import (
    apply_automation_event_receipts_migration_for_tests,
    clear_automation_receipts_for_tests,
    receipts_table_ready,
)
from core.windmill_dev_client import WindmillClientError
from routes.internal_automation_api import internal_automation_bp
from tests.admin_test_util import ensure_operator_user_rows


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FIKIRI_WINDMILL_TRIGGER_ENABLED", "1")
    monkeypatch.setenv("WINDMILL_DEV_TOKEN", "test-token-not-real")
    monkeypatch.setenv("WINDMILL_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("WINDMILL_WORKSPACE", "fikiri-dev")
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


def _mock_key(monkeypatch, *, scopes=("automation:ingress",)):
    monkeypatch.setattr(
        "routes.internal_automation_api.api_key_manager.validate_api_key",
        lambda _key: {
            "api_key_id": 42,
            "user_id": 7,
            "key_prefix": "abcd1234",
            "scopes": list(scopes),
            "name": "automation-dev",
        },
    )


def test_trigger_disabled_returns_503(client, monkeypatch):
    monkeypatch.setenv("FIKIRI_WINDMILL_TRIGGER_ENABLED", "0")
    _mock_key(monkeypatch)
    resp = client.post(
        "/api/internal/automation/jobs/normalize-leads",
        data=json.dumps({"records": [{"email": "a@b.com", "name": "A"}], "trigger_id": "trig_off"}),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 503
    assert resp.get_json()["error_code"] == "TRIGGER_DISABLED"


def test_trigger_requires_scope(client, monkeypatch):
    _mock_key(monkeypatch, scopes=["other:scope"])
    resp = client.post(
        "/api/internal/automation/jobs/normalize-leads",
        data=json.dumps({"records": [], "trigger_id": "trig_scope"}),
        content_type="application/json",
        headers={"X-API-Key": "fik_test"},
    )
    assert resp.status_code == 403


def test_trigger_enqueue_success(client, monkeypatch):
    _mock_key(monkeypatch)

    def fake_run(args, *, config=None, wait=False):
        assert args == {"records": [{"email": "a@b.com", "name": "A"}]}
        assert wait is False
        return {
            "workspace": "fikiri-dev",
            "script_path": "f/normalize_leads/normalize_leads",
            "wait": False,
            "http_status": 201,
            "job_id": "019fc52d-aaaa-bbbb-cccc-ddddeeeeffff",
        }

    with patch("core.automation_windmill_trigger.run_script", side_effect=fake_run):
        resp = client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(
                {
                    "records": [{"email": "a@b.com", "name": "A"}],
                    "trigger_id": "trig_ok_1",
                    "correlation_id": "corr_ok_1",
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["success"] is True
    assert body["job_id"] == "019fc52d-aaaa-bbbb-cccc-ddddeeeeffff"
    assert body["trigger_id"] == "trig_ok_1"
    audits = list_admin_audit(limit=20)["items"]
    assert any(a.get("action") == "automation.windmill.trigger" for a in audits)


def test_trigger_idempotent_duplicate(client, monkeypatch):
    _mock_key(monkeypatch)
    payload = {
        "records": [{"email": "a@b.com", "name": "A"}],
        "trigger_id": "trig_dup_1",
        "correlation_id": "corr_dup_1",
    }

    with patch(
        "core.automation_windmill_trigger.run_script",
        return_value={
            "workspace": "fikiri-dev",
            "script_path": "f/normalize_leads/normalize_leads",
            "wait": False,
            "http_status": 201,
            "job_id": "job-1",
        },
    ) as run_mock:
        first = client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
        second = client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert run_mock.call_count == 1


def test_trigger_payload_conflict(client, monkeypatch):
    _mock_key(monkeypatch)
    with patch(
        "core.automation_windmill_trigger.run_script",
        return_value={
            "workspace": "fikiri-dev",
            "script_path": "f/normalize_leads/normalize_leads",
            "wait": False,
            "http_status": 201,
            "job_id": "job-1",
        },
    ):
        client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(
                {
                    "records": [{"email": "a@b.com", "name": "A"}],
                    "trigger_id": "trig_conflict",
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
        resp = client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(
                {
                    "records": [{"email": "b@c.com", "name": "B"}],
                    "trigger_id": "trig_conflict",
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
    assert resp.status_code == 409
    assert resp.get_json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_trigger_windmill_failure(client, monkeypatch):
    _mock_key(monkeypatch)
    with patch(
        "core.automation_windmill_trigger.run_script",
        side_effect=WindmillClientError("down", error_code="WINDMILL_UNREACHABLE"),
    ):
        resp = client.post(
            "/api/internal/automation/jobs/normalize-leads",
            data=json.dumps(
                {
                    "records": [{"email": "a@b.com", "name": "A"}],
                    "trigger_id": "trig_fail",
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "fik_test"},
        )
    assert resp.status_code == 502
    assert resp.get_json()["error_code"] == "WINDMILL_UNREACHABLE"


def test_script_path_url_segment():
    from core.windmill_dev_client import _script_path_url_segment

    assert _script_path_url_segment("f/normalize_leads/normalize_leads") == (
        "f/normalize_leads/normalize_leads"
    )
