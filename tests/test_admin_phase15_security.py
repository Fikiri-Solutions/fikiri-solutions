"""Phase 1.5 admin security: step-up, reauth, MFA boundary, CSRF, rate limits."""

from __future__ import annotations

import hashlib
import json

import pytest
from flask import Flask, g

from core.admin_audit import clear_admin_audit_for_tests, list_admin_audit
from core.admin_security import (
    CSRF_HEADER,
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    establish_admin_step_up,
    get_admin_step_up_state,
    invalidate_admin_step_up_for_user,
    issue_admin_csrf_token,
    require_admin_step_up,
    step_up_completed_with_mfa,
    verify_admin_csrf_token,
)
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "true")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "false")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.delenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", raising=False)
    monkeypatch.delenv("ADMIN_LOCKDOWN", raising=False)
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    prepare_admin_test_db(monkeypatch)
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.register_blueprint(admin_platform_bp)

    @application.route("/api/admin/platform/_step_up_probe", methods=["POST"])
    @require_admin_step_up("destructive")
    def _probe():
        return {"ok": True}

    return application


@pytest.fixture
def client(app):
    yield app.test_client()
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()


def _auth_headers(**extra):
    headers = {"Authorization": "Bearer phase15-token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_operator(monkeypatch, user_id=1, *, impersonating=False):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            payload = {"user_id": 55 if impersonating else user_id, "type": "access", "jti": "jti-phase15"}
            if impersonating:
                payload["impersonating"] = True
                payload["actor_user_id"] = user_id
            return payload

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr(
        "core.admin_security.get_admin_session_binding",
        lambda: f"jti:jti-phase15",
    )


def test_protected_route_rejects_without_step_up(client, monkeypatch):
    _mock_operator(monkeypatch)
    response = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert response.status_code == 403
    body = json.loads(response.data)
    assert (body.get("error_code") or body.get("code")) == "STEP_UP_REQUIRED"


def test_correct_password_creates_step_up(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_mfa", lambda *_a, **_k: (True, None))

    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "CorrectHorseBattery"}),
    )
    assert response.status_code == 200
    data = json.loads(response.data)["data"]
    assert data["step_up_confirmed"] is True
    assert 300 <= int(data["expires_in"]) <= 900
    assert "password" not in json.dumps(data).lower() or data.get("method") == "password"

    audit = list_admin_audit(limit=20)
    assert any(i.get("action") == "admin.step_up.succeeded" for i in audit["items"])
    raw = json.dumps(audit["items"], default=str)
    assert "CorrectHorseBattery" not in raw


def test_incorrect_password_does_not_create_step_up(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: False)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)

    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "wrong"}),
    )
    assert response.status_code == 403
    assert (json.loads(response.data).get("error_code") or json.loads(response.data).get("code")) == "REAUTH_FAILED"
    assert get_admin_step_up_state(1) is None


def test_reauth_rate_limited(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: False)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)

    codes = []
    for _ in range(6):
        response = client.post(
            "/api/admin/platform/security/reauthenticate",
            headers=_auth_headers(),
            data=json.dumps({"password": "x"}),
        )
        codes.append(response.status_code)
    assert 429 in codes


def test_impersonated_session_cannot_reauthenticate(client, monkeypatch):
    _mock_operator(monkeypatch, impersonating=True)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    assert response.status_code == 403


def test_step_up_expires(monkeypatch):
    clear_step_up_tokens_for_tests()
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:expire-test")
    bundle = establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False)
    assert bundle["step_up_confirmed"] is True
    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    key = store.k("stepup", 1, "jti:expire-test")
    state = store.get_json(key)
    assert state
    state["exp"] = 0
    store.set_json(key, state, ttl=60)
    assert get_admin_step_up_state(1) is None
    audit = list_admin_audit(limit=10)
    assert any(i.get("action") == "admin.step_up.expired" for i in audit["items"])


def test_step_up_invalidated_after_password_change_hook(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:revoke-test")
    establish_admin_step_up(actor_user_id=1, method="password")
    assert get_admin_step_up_state(1) is not None
    invalidate_admin_step_up_for_user(1, reason="password_change")
    assert get_admin_step_up_state(1) is None
    audit = list_admin_audit(limit=10)
    assert any(i.get("action") == "admin.session.revoked" for i in audit["items"])


def test_mfa_required_rejects_password_only(client, monkeypatch):
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr(
        "routes.admin_platform_api.verify_operator_mfa",
        lambda *_a, **_k: (False, "MFA_REQUIRED"),
    )
    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "ok"}),
    )
    assert response.status_code == 403
    code = json.loads(response.data).get("error_code") or json.loads(response.data).get("code")
    assert code == "REAUTH_FAILED"
    assert get_admin_step_up_state(1) is None


def test_mfa_required_allows_password_bootstrap_when_unenrolled(client, monkeypatch):
    """Unenrolled operators must be able to step up with password to enroll MFA."""
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr(
        "routes.admin_platform_api.verify_operator_mfa",
        lambda *_a, **_k: (False, "MFA_ENROLLMENT_REQUIRED"),
    )
    monkeypatch.setattr("core.admin_security.operator_mfa_enrolled", lambda *_a, **_k: False)
    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "ok"}),
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    data = body.get("data") or body
    assert data.get("step_up_confirmed") is True
    assert data.get("mfa_completed") is False
    assert get_admin_step_up_state(1) is not None
    assert step_up_completed_with_mfa(1) is False


def test_bootstrap_step_up_does_not_unlock_privileged_actions(client, monkeypatch):
    """Password-only enrollment bootstrap must not satisfy require_admin_step_up."""
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("core.admin_security.operator_mfa_enrolled", lambda *_a, **_k: False)
    establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False)
    response = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert response.status_code == 403
    code = json.loads(response.data).get("error_code") or json.loads(response.data).get("code")
    assert code == "MFA_ENROLLMENT_REQUIRED"


def test_enrolled_password_only_reauth_still_rejected(client, monkeypatch):
    """Once enrolled, MFA-required operators cannot password-only step up."""
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr(
        "routes.admin_platform_api.verify_operator_mfa",
        lambda *_a, **_k: (False, "MFA_REQUIRED"),
    )
    monkeypatch.setattr("core.admin_security.operator_mfa_enrolled", lambda *_a, **_k: True)
    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "ok"}),
    )
    assert response.status_code == 403
    code = json.loads(response.data).get("error_code") or json.loads(response.data).get("code")
    assert code == "REAUTH_FAILED"
    assert get_admin_step_up_state(1) is None


def test_cookie_auth_csrf_enforced(client, monkeypatch):
    """State-changing cookie-authenticated admin requests require a valid CSRF token."""
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_mfa", lambda *_a, **_k: (True, None))
    monkeypatch.setattr("core.admin_security.admin_request_uses_cookie_auth", lambda: True)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "cookie:sess-1")
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: 1)

    denied = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    assert denied.status_code == 403
    body = json.loads(denied.data)
    assert (body.get("error_code") or body.get("code")) == "CSRF_FAILED"

    csrf = issue_admin_csrf_token(1)
    allowed = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(**{CSRF_HEADER: csrf}),
        data=json.dumps({"password": "x"}),
    )
    assert allowed.status_code == 200
    assert verify_admin_csrf_token(1, "bad") is False


def test_admin_api_sets_no_store_cache_header(client, monkeypatch):
    _mock_operator(monkeypatch)
    response = client.get("/api/admin/platform/me", headers=_auth_headers())
    assert response.status_code == 200
    assert "no-store" in (response.headers.get("Cache-Control") or "")


def test_security_headers_present_on_admin_api(client, monkeypatch):
    """AT-CONFIG-01: baseline headers via core.security when configured on app."""
    from core.security import init_security

    _mock_operator(monkeypatch)
    application = client.application
    init_security(application)
    response = client.get("/api/admin/platform/me", headers=_auth_headers())
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "frame-ancestors 'none'" in (response.headers.get("Content-Security-Policy") or "")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in (response.headers.get("Permissions-Policy") or "")


def test_step_up_probe_succeeds_after_establish(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-phase15")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-phase15")
    response = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert response.status_code == 200


def test_deactivate_invalidates_step_up(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:deact")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:deact")
    assert get_admin_step_up_state(1) is not None
    invalidate_admin_step_up_for_user(1, reason="account_deactivated")
    assert get_admin_step_up_state(1) is None
    audit = list_admin_audit(limit=10)
    assert any(
        i.get("action") == "admin.session.revoked"
        and (i.get("metadata") or {}).get("reason") == "account_deactivated"
        for i in audit["items"]
    )
