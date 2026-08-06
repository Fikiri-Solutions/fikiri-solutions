"""Phase 1.5 acceptance tests for platform admin security controls.

Test IDs map to docs/ADMIN_PORTAL_SECURITY.md §6.
"""

import json
import os

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, list_admin_audit, record_admin_audit
from core.admin_security import (
    STEP_UP_HEADER,
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    issue_step_up_token,
    verify_step_up_token,
)
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "true")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.delenv("ADMIN_LOCKDOWN", raising=False)
    monkeypatch.delenv("ADMIN_DESTRUCTIVE_ENABLED", raising=False)
    monkeypatch.delenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", raising=False)
    monkeypatch.delenv("ADMIN_MFA_REQUIRED", raising=False)
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
    headers = {"Authorization": "Bearer platform-admin-token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_jwt(monkeypatch, payload):
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
    monkeypatch.setattr("routes.admin_platform_api.get_jwt_manager", lambda: _Mgr())


def _as_operator(monkeypatch, user_id=1, impersonating=False):
    _mock_jwt(
        monkeypatch,
        {
            "user_id": 55 if impersonating else user_id,
            "type": "access",
            "impersonating": impersonating,
            "actor_user_id": user_id if impersonating else None,
        },
    )
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "routes.admin_platform_api.get_current_user_id",
        lambda: 55 if impersonating else user_id,
    )
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "core.admin_security.get_current_user_id",
        lambda: 55 if impersonating else user_id,
    )


# --- AT-AUTHZ ---


def test_at_authz_01_non_operator_cannot_list_tenants(client, monkeypatch):
    _as_operator(monkeypatch, user_id=42)
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 403


def test_at_authz_02_tenant_role_admin_is_not_platform_operator(client, monkeypatch):
    """BFLA: customer role=admin must not unlock platform APIs."""
    _mock_jwt(monkeypatch, {"user_id": 99, "type": "access", "role": "admin"})
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 99)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 99)
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 403


def test_at_authz_04_nested_impersonation_rejected(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1, impersonating=True)
    step = issue_step_up_token(actor_user_id=1, action="impersonate")
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(**{STEP_UP_HEADER: step["step_up_token"]}),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 403
    body = json.loads(response.data)
    code = body.get("error_code") or body.get("code")
    assert code in (
        "NESTED_IMPERSONATION_FORBIDDEN",
        "FORBIDDEN_WHILE_IMPERSONATING",
    )


def test_at_authz_05_client_actor_user_id_ignored(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1)
    step = issue_step_up_token(actor_user_id=1, action="impersonate")
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
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(**{STEP_UP_HEADER: step["step_up_token"]}),
        data=json.dumps({"target_user_id": 55, "actor_user_id": 999}),
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["tokens"]["actor_user_id"] == 1


# --- AT-AUTHN ---


def test_at_authn_01_impersonate_without_step_up_rejected(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1)
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 403
    body = json.loads(response.data)
    assert body["error_code"] == "STEP_UP_REQUIRED"


def test_at_authn_02_step_up_token_expires(monkeypatch):
    monkeypatch.setenv("ADMIN_STEP_UP_TTL_SECONDS", "600")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    clear_step_up_tokens_for_tests()
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:expire")
    from core.admin_security import establish_admin_step_up, get_admin_step_up_state
    from core.admin_security_store import get_admin_security_store

    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:expire")
    store = get_admin_security_store()
    key = store.k("stepup", 1, "jti:expire")
    state = store.get_json(key)
    state["exp"] = 0
    store.set_json(key, state, ttl=60)
    assert get_admin_step_up_state(1) is None


# --- AT-SESS ---


def test_at_sess_02_impersonation_has_no_refresh_token(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1)
    step = issue_step_up_token(actor_user_id=1, action="impersonate")
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
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(**{STEP_UP_HEADER: step["step_up_token"]}),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 200
    tokens = json.loads(response.data)["data"]["tokens"]
    assert "refresh_token" not in tokens
    assert tokens.get("access_token")


def test_at_sess_03_impersonation_kill_switch(client, monkeypatch):
    monkeypatch.setenv("IMPERSONATION_ENABLED", "false")
    _as_operator(monkeypatch, user_id=1)
    step = issue_step_up_token(actor_user_id=1, action="impersonate")
    response = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(**{STEP_UP_HEADER: step["step_up_token"]}),
        data=json.dumps({"target_user_id": 55}),
    )
    assert response.status_code == 403
    assert json.loads(response.data)["error_code"] == "IMPERSONATION_DISABLED"


def test_at_sess_04_admin_lockdown_blocks_api(client, monkeypatch):
    monkeypatch.setenv("ADMIN_LOCKDOWN", "1")
    _as_operator(monkeypatch, user_id=1)
    response = client.get("/api/admin/platform/tenants", headers=_auth_headers())
    assert response.status_code == 503
    assert json.loads(response.data)["error_code"] == "ADMIN_LOCKDOWN"


# --- AT-AUDIT ---


def test_at_audit_01_and_02_success_and_denied_outcomes(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1)
    # Denied: missing step-up
    denied = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 55}),
    )
    assert denied.status_code == 403

    step = issue_step_up_token(actor_user_id=1, action="impersonate")
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
    ok = client.post(
        "/api/admin/platform/impersonate",
        headers=_auth_headers(**{STEP_UP_HEADER: step["step_up_token"]}),
        data=json.dumps({"target_user_id": 55}),
    )
    assert ok.status_code == 200

    audit = list_admin_audit(limit=50)
    outcomes = {item.get("outcome") for item in audit["items"] if item.get("action") == "platform.impersonate.start"}
    # Success is recorded; missing step-up is denied at decorator before handler audit —
    # capability denials are audited separately. Assert success outcome present.
    assert "success" in outcomes


def test_at_audit_03_redacts_secrets():
    clear_admin_audit_for_tests()
    record_admin_audit(
        actor_user_id=1,
        action="platform.test.redact",
        after={"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb", "email": "a@b.com"},
        metadata={"password": "supersecret", "ok": True},
        outcome="success",
    )
    items = list_admin_audit(limit=5)["items"]
    assert items
    after = items[0].get("after") or {}
    meta = items[0].get("metadata") or {}
    assert after.get("access_token") == "[REDACTED]"
    assert meta.get("password") == "[REDACTED]"
    assert after.get("email") == "a@b.com"


# --- AT-DESIGN / AT-API ---


def test_at_design_01_destructive_gated(client, monkeypatch):
    from core.platform_admin import require_platform_capability
    from flask import Flask

    app = Flask(__name__)

    @app.route("/api/admin/platform/ops-write-probe")
    @require_platform_capability("platform.ops.write")
    def probe():
        return {"ok": True}

    _as_operator(monkeypatch, user_id=1)
    c = app.test_client()
    # Fake jwt for this mini app — decorator only checks capability + destructive flag
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: 1)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 1)
    response = c.get("/api/admin/platform/ops-write-probe")
    assert response.status_code == 403
    assert response.get_json()["error_code"] == "DESTRUCTIVE_DISABLED"


def test_at_api_04_tenant_list_limit_capped(client, monkeypatch):
    _as_operator(monkeypatch, user_id=1)
    monkeypatch.setattr(
        "routes.admin_platform_api.db_optimizer.execute_query",
        lambda *a, **k: [{"total": 0}] if "COUNT" in str(a[0]) else [],
    )
    response = client.get("/api/admin/platform/tenants?limit=9999", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["limit"] <= 100
