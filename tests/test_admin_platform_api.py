"""Tests for platform admin API (tenant directory, impersonation, audit)."""

import json
import os

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, ensure_admin_audit_table
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "true")
    monkeypatch.setenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", "1")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.delenv("ADMIN_LOCKDOWN", raising=False)
    clear_admin_audit_for_tests()
    prepare_admin_test_db(monkeypatch)
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(admin_platform_bp)
    yield app.test_client()
    clear_admin_audit_for_tests()


def _auth_headers():
    return {"Authorization": "Bearer platform-admin-token"}


def _mock_jwt(monkeypatch, payload):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            return payload

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())


def test_platform_me_requires_auth(client):
    response = client.get("/api/admin/platform/me")
    assert response.status_code == 401


def test_platform_me_non_operator_forbidden_capabilities(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 99, "type": "access"})
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: 99)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 99)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)

    response = client.get("/api/admin/platform/me", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["is_platform_admin"] is False
    assert body["data"]["capabilities"] == []


def test_platform_me_operator(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 1, "type": "access"})
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)

    response = client.get("/api/admin/platform/me", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["is_platform_admin"] is True
    assert "platform.tenants.read" in body["data"]["capabilities"]


def test_list_tenants_forbidden_for_non_operator(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 42, "type": "access"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 42)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 42)

    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 403


def test_impersonation_start_records_audit(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 1, "type": "access"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 1)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 1)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: False)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: 1)
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: 1)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda uid: {
            "id": uid,
            "email": "tenant@example.com",
            "name": "Tenant",
            "role": "user",
            "is_active": 1,
            "email_verified": 1,
            "onboarding_completed": 1,
            "onboarding_step": 0,
            "created_at": "now",
            "last_login": None,
            "business_name": "Acme",
            "industry": "services",
        },
    )
    monkeypatch.setattr(
        "routes.admin_platform_api.get_jwt_manager",
        lambda: type(
            "Mgr",
            (),
            {
                "generate_impersonation_access_token": staticmethod(
                    lambda **kwargs: {
                        "access_token": "impersonation-token",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "impersonating": True,
                        "actor_user_id": kwargs["actor_user_id"],
                        "target_user_id": kwargs["target_user_id"],
                    }
                ),
                "verify_access_token": staticmethod(lambda _token: {"user_id": 1, "type": "access"}),
            },
        )(),
    )

    response = client.post(
        "/api/admin/platform/impersonate",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["tokens"]["access_token"] == "impersonation-token"
    assert body["data"]["target_user"]["email"] == "tenant@example.com"

    ensure_admin_audit_table()
    audit = client.get("/api/admin/platform/audit", headers=_auth_headers())
    audit_body = json.loads(audit.data)
    actions = [item["action"] for item in audit_body["data"]["items"]]
    assert "platform.impersonate.start" in actions


def _as_operator(monkeypatch, user_id=1, *, impersonating=False):
    _mock_jwt(monkeypatch, {"user_id": user_id, "type": "access"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)


def test_audit_forbidden_for_non_operator(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 42, "type": "access"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 42)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 42)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: False)

    response = client.get("/api/admin/platform/audit", headers=_auth_headers())
    assert response.status_code == 403


def test_audit_forbidden_while_impersonating(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1, impersonating=True)

    response = client.get("/api/admin/platform/audit", headers=_auth_headers())
    assert response.status_code == 403


def test_audit_filters_and_pagination(client, monkeypatch):
    from core.admin_audit import record_admin_audit

    _as_operator(monkeypatch)
    clear_admin_audit_for_tests()
    record_admin_audit(
        actor_user_id=1,
        action="platform.capability.denied",
        target_type="user",
        target_id="5",
        outcome="denied",
        capability="platform.ops.write",
        correlation_id="corr_filter_a",
        metadata={"reason": "CAPABILITY_DENIED"},
    )
    record_admin_audit(
        actor_user_id=9,
        action="platform.sync.retry",
        target_type="tenant",
        target_id="2",
        outcome="success",
        correlation_id="corr_filter_b",
    )
    record_admin_audit(
        actor_user_id=1,
        action="admin.session.revoked",
        target_type="user",
        target_id="5",
        outcome="error",
        correlation_id="corr_filter_c",
        metadata={"password": "secret-should-redact"},
    )

    denied = client.get(
        "/api/admin/platform/audit?outcome=denied&actor_user_id=1&target_type=user&target_id=5&limit=10&offset=0",
        headers=_auth_headers(),
    )
    assert denied.status_code == 200
    assert denied.headers.get("Cache-Control", "").lower().find("no-store") >= 0
    body = json.loads(denied.data)["data"]
    assert body["total"] == 1
    assert body["limit"] <= 100
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["outcome"] == "denied"
    assert item["actor_user_id"] == 1
    assert item["target_type"] == "user"
    assert item["target_id"] == "5"
    raw = json.dumps(item, default=str).lower()
    assert "secret-should-redact" not in raw

    malformed = client.get(
        "/api/admin/platform/audit?outcome=not-a-real-outcome&actor_user_id=abc&limit=9999",
        headers=_auth_headers(),
    )
    assert malformed.status_code == 200
    malformed_body = json.loads(malformed.data)["data"]
    assert malformed_body["limit"] <= 100
    assert isinstance(malformed_body["items"], list)

    page = client.get(
        "/api/admin/platform/audit?limit=1&offset=0",
        headers=_auth_headers(),
    )
    page_body = json.loads(page.data)["data"]
    assert page_body["limit"] == 1
    assert len(page_body["items"]) == 1
    assert page_body["total"] == 3


def test_platform_status_read_only_contract(client, monkeypatch):
    from core.admin_audit import record_admin_audit

    _as_operator(monkeypatch)
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    clear_admin_audit_for_tests()
    record_admin_audit(
        actor_user_id=1,
        action="platform.capability.denied",
        outcome="denied",
        metadata={"reason": "CAPABILITY_DENIED"},
    )
    record_admin_audit(
        actor_user_id=1,
        action="platform.sync.retry",
        outcome="success",
    )

    response = client.get("/api/admin/platform/status", headers=_auth_headers())
    assert response.status_code == 200
    assert "no-store" in response.headers.get("Cache-Control", "").lower()
    body = json.loads(response.data)["data"]

    assert body["gates"]["destructive_enabled"] is False
    assert body["gates"]["lockdown"] is False
    assert body["operator"]["actor_user_id"] == 1
    assert "platform.tenants.read" in body["operator"]["capabilities"]
    assert "security" in body["operator"]
    assert body["audit"]["investigate_path"] == "/admin/audit?outcome=denied"
    assert body["audit"]["denied_available"] is True
    assert body["audit"]["denied_count"] >= 1
    assert body["sync_jobs"]["investigate_path"] == "/admin#failed-syncs"
    assert body["analytics"]["state"] in ("disabled", "available", "unavailable", "unknown")
    # No mutation surface in payload
    raw = json.dumps(body).lower()
    assert "access_token" not in raw
    assert "password" not in raw


def test_platform_status_forbidden_for_non_operator(client, monkeypatch):
    _mock_jwt(monkeypatch, {"user_id": 42, "type": "access"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 42)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 42)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: False)

    response = client.get("/api/admin/platform/status", headers=_auth_headers())
    assert response.status_code == 403


def test_platform_sync_jobs_inbox_read_only(client, monkeypatch):
    _as_operator(monkeypatch)

    response = client.get(
        "/api/admin/platform/sync-jobs?status=failed,retrying&limit=20",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert "no-store" in response.headers.get("Cache-Control", "").lower()
    body = json.loads(response.data)["data"]
    assert "items" in body
    assert body["limit"] <= 50
    assert isinstance(body["items"], list)
    for item in body["items"]:
        raw = json.dumps(item).lower()
        assert "access_token" not in raw
        assert "refresh_token" not in raw


def test_audit_export_requires_step_up(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", "0")

    response = client.post(
        "/api/admin/platform/audit/export",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        data=json.dumps({"format": "json", "limit": 10}),
    )
    # Without step-up, decorator should deny.
    assert response.status_code in (401, 403)


def test_tenant_suspend_blocked_when_destructive_disabled(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", "1")

    response = client.post(
        "/api/admin/platform/tenants/2/suspend",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        data=json.dumps({"confirm": "suspend"}),
    )
    assert response.status_code == 403
    body = json.loads(response.data)
    assert body.get("error_code") == "DESTRUCTIVE_DISABLED"
