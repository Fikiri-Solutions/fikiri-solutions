"""Hardening tests: impersonation kill switch, nested block, inactive targets, operator isolation."""

import json

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, list_admin_audit
from core.admin_security import (
    STEP_UP_HEADER,
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    issue_step_up_token,
)
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
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    prepare_admin_test_db(monkeypatch)
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(admin_platform_bp)
    yield app.test_client()
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()


def _auth_headers(**extra):
    headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_jwt(monkeypatch, payload, *, with_impersonation_generator=True):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            return payload

        @staticmethod
        def generate_impersonation_access_token(**kwargs):
            return {
                "access_token": "impersonation-token",
                "expires_in": 1800,
                "token_type": "Bearer",
                "impersonating": True,
                "actor_user_id": kwargs["actor_user_id"],
                "target_user_id": kwargs["target_user_id"],
            }

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    if with_impersonation_generator:
        monkeypatch.setattr("routes.admin_platform_api.get_jwt_manager", lambda: _Mgr())


def _as_operator(monkeypatch, *, user_id=1, impersonating=False, effective_id=55):
    payload = {
        "user_id": effective_id if impersonating else user_id,
        "type": "access",
        "impersonating": impersonating,
    }
    if impersonating:
        payload["actor_user_id"] = user_id
    _mock_jwt(monkeypatch, payload)
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "core.platform_admin.get_current_user_id",
        lambda: effective_id if impersonating else user_id,
    )
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "routes.admin_platform_api.get_current_user_id",
        lambda: effective_id if impersonating else user_id,
    )
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "core.admin_security.get_current_user_id",
        lambda: effective_id if impersonating else user_id,
    )


def _active_tenant(uid=55):
    return {
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
    }


def _err_code(body: dict) -> str | None:
    return body.get("error_code") or body.get("code")


def test_impersonation_disabled_blocks_start(client, monkeypatch):
    monkeypatch.delenv("IMPERSONATION_ENABLED", raising=False)
    _as_operator(monkeypatch)
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 403
    body = json.loads(response.data)
    assert _err_code(body) == "IMPERSONATION_DISABLED"
    assert "not available" in body["error"].lower()

    audit = list_admin_audit(limit=20)
    denied = [
        i
        for i in audit["items"]
        if i.get("action") == "platform.impersonate.start" and i.get("outcome") == "denied"
    ]
    assert denied
    assert denied[0]["actor_user_id"] == 1
    raw = json.dumps(denied[0], default=str)
    assert "impersonation-token" not in raw
    assert "Bearer" not in raw


def test_impersonation_stop_available_when_starts_disabled(client, monkeypatch):
    monkeypatch.setenv("IMPERSONATION_ENABLED", "false")
    _as_operator(monkeypatch, impersonating=True)
    response = client.post("/api/admin/platform/impersonate/stop", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["stopped"] is True
    assert body["data"]["actor_user_id"] == 1


def test_impersonated_session_cannot_call_operator_apis(client, monkeypatch):
    _as_operator(monkeypatch, impersonating=True)
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 403
    body = json.loads(response.data)
    assert _err_code(body) == "FORBIDDEN_WHILE_IMPERSONATING"


def test_nested_impersonation_rejected(client, monkeypatch):
    _as_operator(monkeypatch, impersonating=True)
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 77}),
    )
    assert response.status_code == 403
    code = _err_code(json.loads(response.data))
    assert code in ("FORBIDDEN_WHILE_IMPERSONATING", "NESTED_IMPERSONATION_FORBIDDEN")


def test_inactive_target_cannot_be_impersonated(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda uid: {**_active_tenant(uid), "is_active": 0},
    )
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 400
    assert _err_code(json.loads(response.data)) == "USER_INACTIVE"


def test_missing_target_cannot_be_impersonated(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api._fetch_user_row", lambda uid: None)
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 404}),
    )
    assert response.status_code == 404


def test_successful_impersonation_audit_has_actor_target_no_token(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api._fetch_user_row", lambda uid: _active_tenant(uid))
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 200
    tokens = json.loads(response.data)["data"]["tokens"]
    assert tokens["actor_user_id"] == 1
    assert tokens["target_user_id"] == 55
    assert "refresh_token" not in tokens

    audit = list_admin_audit(limit=20)
    success = [
        i
        for i in audit["items"]
        if i.get("action") == "platform.impersonate.start" and i.get("outcome") == "success"
    ]
    assert success
    entry = success[0]
    assert entry["actor_user_id"] == 1
    assert entry["target_id"] == "55"
    assert entry.get("created_at")
    assert "impersonation-token" not in json.dumps(entry, default=str)


def test_non_operator_still_forbidden(client, monkeypatch):
    _as_operator(monkeypatch, user_id=42)
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 403


def test_operator_tenants_still_allowed_when_not_impersonating(client, monkeypatch):
    _as_operator(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api.db_optimizer.execute_query",
        lambda *a, **k: [{"total": 0}] if "COUNT" in str(a[0]) else [],
    )
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 200
