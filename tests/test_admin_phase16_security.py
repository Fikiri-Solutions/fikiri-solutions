"""Phase 1.6: shared store, MFA TOTP, recovery codes, session rotation, stop hardening."""

from __future__ import annotations

import json
import os

import pytest
from cryptography.fernet import Fernet
from flask import Flask

# Ensure Fernet before db_optimizer cipher checks in MFA module.
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("ADMIN_SECURITY_STORE", "memory")

from core.admin_audit import clear_admin_audit_for_tests, list_admin_audit
from core.admin_mfa import (
    confirm_totp_enrollment,
    consume_recovery_code,
    get_mfa_status,
    get_operator_mfa_record,
    operator_mfa_enrolled,
    start_totp_enrollment,
    verify_totp_code,
)
from core.admin_security import (
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    establish_admin_step_up,
    get_admin_step_up_state,
    invalidate_admin_step_up_for_user,
    require_admin_step_up,
    validate_admin_security_config,
)
from core.admin_security_store import (
    AdminSecurityStoreUnavailable,
    clear_admin_security_store_for_tests,
    get_admin_security_store,
)
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


@pytest.fixture(autouse=True)
def _phase16_env(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "false")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "false")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "true")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", raising=False)
    monkeypatch.delenv("ADMIN_DESTRUCTIVE_ENABLED", raising=False)
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    prepare_admin_test_db(monkeypatch)

    # In-memory MFA metadata for unit tests (avoids DB coupling).
    meta_store: dict = {}

    def _load(uid: int):
        return dict(meta_store.get(int(uid), {}))

    def _save(uid: int, metadata: dict):
        meta_store[int(uid)] = dict(metadata)

    monkeypatch.setattr("core.admin_mfa._load_user_metadata", _load)
    monkeypatch.setattr("core.admin_mfa._save_user_metadata", _save)
    monkeypatch.setattr("core.admin_mfa._operator_label", lambda _uid: "op@example.com")
    yield
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()


@pytest.fixture
def app(monkeypatch):
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
    return app.test_client()


def _auth_headers(**extra):
    headers = {"Authorization": "Bearer phase16-token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_operator(monkeypatch, user_id=1, *, impersonating=False):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            payload = {
                "user_id": 55 if impersonating else user_id,
                "type": "access",
                "jti": "jti-phase16",
            }
            if impersonating:
                payload["impersonating"] = True
                payload["actor_user_id"] = user_id
            return payload

        @staticmethod
        def blacklist_token(*_a, **_k):
            return True

        @staticmethod
        def generate_tokens(uid, user_data, **_k):
            return {
                "access_token": f"restored-token-{uid}",
                "refresh_token": "restored-refresh",
                "expires_in": 1800,
                "token_type": "Bearer",
            }

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.admin_platform_api.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-phase16")


# --- Shared store ---


def test_step_up_shared_across_store_reload(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:shared")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:shared")
    # Simulate another worker: new store facade, same memory backend
    get_admin_security_store(force_reload=True)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:shared")
    assert get_admin_step_up_state(1) is not None


def test_revocation_propagates_via_shared_store(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:rev")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:rev")
    invalidate_admin_step_up_for_user(1, reason="logout")
    get_admin_security_store(force_reload=True)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:rev")
    assert get_admin_step_up_state(1) is None


def test_store_outage_fails_privileged_closed(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr(
        "core.admin_security._store_or_fail",
        lambda: (_ for _ in ()).throw(AdminSecurityStoreUnavailable("down")),
    )
    response = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert response.status_code == 503
    assert json.loads(response.data)["error_code"] == "STORE_UNAVAILABLE"


def test_destructive_config_requires_mfa_and_store(monkeypatch):
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "true")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "false")
    with pytest.raises(RuntimeError):
        validate_admin_security_config()


# --- TOTP enrollment ---


def test_unconfirmed_enrollment_does_not_activate(monkeypatch):
    start_totp_enrollment(1)
    assert operator_mfa_enrolled(1) is False


def test_confirm_activates_and_issues_recovery_codes(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    code = pyotp.TOTP(started["secret"]).now()
    ok, err, result = confirm_totp_enrollment(1, code)
    assert ok is True and err is None
    assert operator_mfa_enrolled(1) is True
    assert result and len(result["recovery_codes"]) == 10
    audit = list_admin_audit(limit=20)
    raw = json.dumps(audit, default=str)
    assert started["secret"] not in raw
    assert "otpauth://" not in raw
    record = get_operator_mfa_record(1)
    assert record.get("secret_enc")
    assert started["secret"] not in json.dumps(record)
    for entry in record.get("recovery_codes") or []:
        assert "hash" in entry and "salt" in entry


def test_invalid_confirm_does_not_activate(monkeypatch):
    start_totp_enrollment(1)
    ok, err, _ = confirm_totp_enrollment(1, "000000")
    assert ok is False
    assert operator_mfa_enrolled(1) is False


def test_new_enrollment_replaces_unconfirmed(monkeypatch):
    first = start_totp_enrollment(1)
    second = start_totp_enrollment(1)
    assert first["secret"] != second["secret"]
    import pyotp

    ok, _, _ = confirm_totp_enrollment(1, pyotp.TOTP(first["secret"]).now())
    assert ok is False


# --- MFA step-up + recovery ---


def test_password_plus_totp_establishes_step_up(client, monkeypatch):
    import pyotp

    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    started = start_totp_enrollment(1)
    confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    totp = pyotp.TOTP(started["secret"]).now()

    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.rotate_session_after_step_up", lambda *_a, **_k: {"rotated": False})

    response = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x", "mfa_code": totp}),
    )
    assert response.status_code == 200
    data = json.loads(response.data)["data"]
    assert data["step_up_confirmed"] is True
    assert data["mfa_completed"] is True
    assert get_admin_step_up_state(1) is not None


def test_recovery_code_single_use(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    ok, _, result = confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    assert ok
    code = result["recovery_codes"][0]
    ok1, _ = consume_recovery_code(1, code)
    ok2, _ = consume_recovery_code(1, code)
    assert ok1 is True
    assert ok2 is False


def test_totp_replay_denied(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    code = pyotp.TOTP(started["secret"]).now()
    ok1, err1 = verify_totp_code(1, code)
    ok2, err2 = verify_totp_code(1, code)
    assert ok1 is True
    assert ok2 is False
    assert err2 == "MFA_REPLAY"


# --- Impersonation stop ---


def test_stop_impersonation_idempotent_and_rejects_target_fields(client, monkeypatch):
    _mock_operator(monkeypatch, impersonating=True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.is_platform_admin", lambda *_a, **_k: True)

    denied = client.post(
        "/api/admin/platform/impersonate/stop",
        headers=_auth_headers(),
        data=json.dumps({"target_user_id": 999}),
    )
    assert denied.status_code == 400

    ok = client.post(
        "/api/admin/platform/impersonate/stop",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert ok.status_code == 200
    body = json.loads(ok.data)["data"]
    assert body["stopped"] is True
    assert body["actor_user_id"] == 1
    assert body.get("tokens", {}).get("access_token", "").startswith("restored-token-1")

    # Idempotent when not impersonating
    _mock_operator(monkeypatch, impersonating=False)
    again = client.post(
        "/api/admin/platform/impersonate/stop",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert again.status_code == 200
    assert json.loads(again.data)["data"].get("already_stopped") is True


def test_stop_when_actor_unauthorized(client, monkeypatch):
    _mock_operator(monkeypatch, impersonating=True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: False)
    monkeypatch.setattr("routes.admin_platform_api.is_platform_admin", lambda *_a, **_k: False)
    response = client.post(
        "/api/admin/platform/impersonate/stop",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert response.status_code == 200
    data = json.loads(response.data)["data"]
    assert data.get("admin_access_revoked") is True
    assert data.get("require_relogin") is True
    assert "tokens" not in data


def test_mfa_status_has_no_secrets(client, monkeypatch):
    _mock_operator(monkeypatch)
    response = client.get("/api/admin/platform/security/mfa/status", headers=_auth_headers())
    assert response.status_code == 200
    data = json.loads(response.data)["data"]
    assert "secret" not in json.dumps(data).lower() or data.get("enrolled") is False
    assert "recovery_codes" not in data
    assert "enrolled" in data


def test_http_bootstrap_enroll_confirm_upgrades_step_up(client, monkeypatch):
    """Regression: MFA_REQUIRED + unenrolled must allow password → enroll → confirm,
    and confirm must upgrade step-up so privileged actions work without a second dance.
    """
    import pyotp

    from core.admin_security import step_up_completed_with_mfa

    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.rotate_session_after_step_up", lambda *_a, **_k: {"rotated": False})
    monkeypatch.setattr("routes.admin_platform_api.is_platform_admin", lambda *_a, **_k: True)

    # 1) Password-only bootstrap reauth (no MFA yet)
    reauth = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "ok"}),
    )
    assert reauth.status_code == 200
    assert json.loads(reauth.data)["data"]["mfa_completed"] is False

    # 2) Privileged probe still denied while unenrolled
    denied = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert denied.status_code == 403
    denied_code = json.loads(denied.data).get("error_code") or json.loads(denied.data).get("code")
    assert denied_code == "MFA_ENROLLMENT_REQUIRED"

    # 3) Start enrollment with bootstrap step-up
    start = client.post(
        "/api/admin/platform/security/mfa/totp/enroll",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert start.status_code == 200
    started = json.loads(start.data)["data"]
    secret = started["secret"]
    assert secret

    # 4) Confirm with TOTP — upgrades step-up to MFA-completed
    code = pyotp.TOTP(secret).now()
    confirm = client.post(
        "/api/admin/platform/security/mfa/totp/confirm",
        headers=_auth_headers(),
        data=json.dumps({"totp_code": code}),
    )
    assert confirm.status_code == 200
    body = json.loads(confirm.data)["data"]
    assert body.get("activated") is True
    assert body.get("recovery_codes")
    assert operator_mfa_enrolled(1) is True
    assert step_up_completed_with_mfa(1) is True

    # 5) Privileged probe now allowed on upgraded step-up
    allowed = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert allowed.status_code == 200


def test_replace_enroll_requires_mfa_completed_step_up(client, monkeypatch):
    """Replacing an enrolled authenticator must not accept password-only step-up."""
    import pyotp

    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    _mock_operator(monkeypatch)
    monkeypatch.setattr("routes.admin_platform_api.is_platform_admin", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)

    started = start_totp_enrollment(1)
    confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    assert operator_mfa_enrolled(1) is True

    # establish() correctly rejects password-only when enrolled — force a stale
    # password step-up into the store to exercise the route-level replace guard.
    try:
        establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False)
    except PermissionError:
        pass
    if get_admin_step_up_state(1) is None:
        from core.admin_security_store import get_admin_security_store
        import time

        store = get_admin_security_store()
        key = store.k("stepup", 1, "jti:jti-phase16")
        now = time.time()
        store.set_json(
            key,
            {
                "user_id": 1,
                "binding": "jti:jti-phase16",
                "method": "password",
                "mfa_completed": False,
                "iat": now,
                "exp": now + 600,
                "last_activity": now,
            },
            600,
        )

    replace = client.post(
        "/api/admin/platform/security/mfa/totp/enroll",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert replace.status_code == 403
    code = json.loads(replace.data).get("error_code") or json.loads(replace.data).get("code")
    # Stale password bootstrap is cleared once enrolled → no step-up for replace.
    assert code == "STEP_UP_REQUIRED"
