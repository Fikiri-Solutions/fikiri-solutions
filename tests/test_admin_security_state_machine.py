"""Admin security state-machine journey tests (order / stale / concurrent / revoke).

No new privileged mutations. ADMIN_DESTRUCTIVE_ENABLED stays off.
"""

from __future__ import annotations

import json
import os
import time

import pytest
from cryptography.fernet import Fernet
from flask import Flask

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("ADMIN_SECURITY_STORE", "memory")

from core.admin_audit import clear_admin_audit_for_tests
from core.admin_mfa import (
    confirm_totp_enrollment,
    consume_recovery_code,
    operator_mfa_enrolled,
    regenerate_recovery_codes,
    start_totp_enrollment,
)
from core.admin_security import (
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    establish_admin_step_up,
    get_admin_step_up_state,
    invalidate_admin_step_up_for_user,
    require_admin_step_up,
    step_up_assurance_level,
    step_up_completed_with_mfa,
)
from core.admin_security_store import clear_admin_security_store_for_tests
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "true")
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", raising=False)
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    clear_admin_security_store_for_tests()
    prepare_admin_test_db(monkeypatch)

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
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {
        "false",
        "0",
        "",
    }


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
    headers = {"Authorization": "Bearer sm-token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_operator(monkeypatch, user_id=1, *, binding="jti:sm-a"):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            return {"user_id": user_id, "type": "access", "jti": binding.split(":", 1)[-1]}

        @staticmethod
        def blacklist_token(*_a, **_k):
            return True

        @staticmethod
        def generate_tokens(uid, user_data, **_k):
            return {
                "access_token": f"tok-{uid}",
                "refresh_token": "ref",
                "expires_in": 1800,
            }

        @staticmethod
        def revoke_all_refresh_tokens(uid):
            return True

        @staticmethod
        def revoke_all_user_tokens(uid):
            return True

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.admin_platform_api.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: False)
    monkeypatch.setattr("routes.admin_platform_api.is_platform_admin", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: False)
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("core.admin_security.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: binding)
    monkeypatch.setattr("core.platform_admin.is_platform_admin", lambda *_a, **_k: True)
    monkeypatch.setattr("core.admin_security.operator_account_usable", lambda *_a, **_k: True)
    monkeypatch.setattr("routes.admin_platform_api.verify_operator_password", lambda *_a, **_k: True)
    monkeypatch.setattr(
        "routes.admin_platform_api.rotate_session_after_step_up",
        lambda *_a, **_k: {"rotated": False},
    )


# --- Journey A ---


def test_journey_a_first_time_mfa_enrollment(client, monkeypatch):
    import pyotp

    _mock_operator(monkeypatch)

    reauth = client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    assert reauth.status_code == 200
    assert json.loads(reauth.data)["data"]["mfa_completed"] is False
    assert step_up_assurance_level(1) == "PASSWORD_BOOTSTRAP"

    start = client.post(
        "/api/admin/platform/security/mfa/totp/enroll",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    assert start.status_code == 200
    secret = json.loads(start.data)["data"]["secret"]

    confirm = client.post(
        "/api/admin/platform/security/mfa/totp/confirm",
        headers=_auth_headers(),
        data=json.dumps({"totp_code": pyotp.TOTP(secret).now()}),
    )
    assert confirm.status_code == 200
    body = json.loads(confirm.data)["data"]
    assert body["activated"] is True
    assert body.get("recovery_codes")
    assert operator_mfa_enrolled(1) is True
    assert step_up_completed_with_mfa(1) is True
    assert step_up_assurance_level(1) == "MFA_VERIFIED"

    probe = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert probe.status_code == 200


# --- Journey B ---


def test_journey_b_step_up_expires_before_confirm(client, monkeypatch):
    import pyotp

    _mock_operator(monkeypatch)

    client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    start = client.post(
        "/api/admin/platform/security/mfa/totp/enroll",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    secret = json.loads(start.data)["data"]["secret"]

    # Expire step-up only — do not wipe pending enrollment (unlike full session revoke).
    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    store.delete(store.k("stepup", 1, "jti:sm-a"))
    assert get_admin_step_up_state(1) is None

    denied = client.post(
        "/api/admin/platform/security/mfa/totp/confirm",
        headers=_auth_headers(),
        data=json.dumps({"totp_code": pyotp.TOTP(secret).now()}),
    )
    assert denied.status_code == 403

    # Fresh bootstrap, confirm existing pending secret.
    client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    ok = client.post(
        "/api/admin/platform/security/mfa/totp/confirm",
        headers=_auth_headers(),
        data=json.dumps({"totp_code": pyotp.TOTP(secret).now()}),
    )
    assert ok.status_code == 200
    assert step_up_completed_with_mfa(1) is True
    assert client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers()).status_code == 200


# --- Journey C ---


def test_journey_c_stale_bootstrap_invalidated_after_other_session_enrolls(monkeypatch):
    import pyotp

    # Session A bootstrap
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:session-a")
    establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False, binding="jti:session-a")
    assert get_admin_step_up_state(1) is not None

    # Session B enrolls + confirms
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:session-b")
    started = start_totp_enrollment(1)
    confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    assert operator_mfa_enrolled(1) is True

    # Session A stale password bootstrap must clear / deny privileged
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:session-a")
    assert get_admin_step_up_state(1) is None
    assert step_up_assurance_level(1) == "NONE"


# --- Journey D ---


def test_journey_d_concurrent_enrollment_old_secret_rejected(monkeypatch):
    import pyotp

    first = start_totp_enrollment(1)
    second = start_totp_enrollment(1)
    assert first["secret"] != second["secret"]

    ok_old, err_old, _ = confirm_totp_enrollment(1, pyotp.TOTP(first["secret"]).now())
    assert ok_old is False
    assert err_old in ("MFA_INVALID", "ENROLLMENT_EXPIRED", "ENROLLMENT_INVALID")

    ok_new, err_new, result = confirm_totp_enrollment(1, pyotp.TOTP(second["secret"]).now())
    assert ok_new is True and err_new is None
    assert result and result.get("recovery_codes")
    assert operator_mfa_enrolled(1) is True


# --- Journey E (password reset refresh revoke) ---


def test_journey_e_password_reset_revokes_refresh_alias(monkeypatch):
    from core.jwt_auth import JWTAuthManager

    called = {"n": 0}

    class _Stub(JWTAuthManager):
        def __init__(self):
            pass

        def revoke_all_user_tokens(self, user_id: int) -> bool:
            called["n"] += 1
            called["uid"] = user_id
            return True

    stub = _Stub()
    assert stub.revoke_all_refresh_tokens(9) is True
    assert called["n"] == 1
    assert called["uid"] == 9

    # Step-up invalidated on password reset path
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:e")
    establish_admin_step_up(actor_user_id=1, method="mfa", mfa_completed=True, binding="jti:e")
    invalidate_admin_step_up_for_user(1, reason="password_reset")
    assert get_admin_step_up_state(1) is None


# --- Journey F ---


def test_journey_f_capability_removal_denies_before_mutation(client, monkeypatch):
    import pyotp

    _mock_operator(monkeypatch)
    client.post(
        "/api/admin/platform/security/reauthenticate",
        headers=_auth_headers(),
        data=json.dumps({"password": "x"}),
    )
    start = client.post(
        "/api/admin/platform/security/mfa/totp/enroll",
        headers=_auth_headers(),
        data=json.dumps({}),
    )
    secret = json.loads(start.data)["data"]["secret"]
    client.post(
        "/api/admin/platform/security/mfa/totp/confirm",
        headers=_auth_headers(),
        data=json.dumps({"totp_code": pyotp.TOTP(secret).now()}),
    )
    assert client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers()).status_code == 200

    monkeypatch.setenv("ADMIN_USER_IDS", "999")
    monkeypatch.setattr("core.platform_admin.is_platform_admin", lambda *_a, **_k: False)
    denied = client.post("/api/admin/platform/_step_up_probe", headers=_auth_headers())
    assert denied.status_code == 403
    code = json.loads(denied.data).get("error_code") or json.loads(denied.data).get("code")
    assert code == "FORBIDDEN"


# --- Journey G ---


def test_journey_g_cross_binding_old_denied_new_ok(monkeypatch):
    import pyotp

    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:worker-a")
    establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False, binding="jti:worker-a")
    started = start_totp_enrollment(1)
    confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    # Upgrade on A
    from core.admin_security import mark_admin_step_up_mfa_completed

    mark_admin_step_up_mfa_completed(1, method="mfa")
    assert step_up_completed_with_mfa(1) is True

    # Worker B new binding without step-up
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:worker-b")
    assert get_admin_step_up_state(1) is None

    # Old binding still has state but after enroll, password-only would have been cleared;
    # MFA-upgraded state remains only on A.
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:worker-a")
    assert step_up_completed_with_mfa(1) is True


# --- Additional invariants ---


def test_password_only_cannot_downgrade_mfa_step_up(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:d")
    # Pretend enrolled so password establish is blocked under MFA required
    monkeypatch.setattr("core.admin_security.operator_mfa_enrolled", lambda *_a, **_k: True)
    establish_admin_step_up(actor_user_id=1, method="mfa", mfa_completed=True, binding="jti:d")
    with pytest.raises(PermissionError):
        establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False, binding="jti:d")
    assert step_up_assurance_level(1) == "MFA_VERIFIED"


def test_confirm_idempotent_does_not_mint_second_recovery_set(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    code = pyotp.TOTP(started["secret"]).now()
    ok1, _, r1 = confirm_totp_enrollment(1, code)
    assert ok1 and r1 and len(r1["recovery_codes"]) > 0
    ok2, _, r2 = confirm_totp_enrollment(1, code)
    assert ok2 and r2 and r2.get("already_completed") is True
    assert r2.get("recovery_codes") == []


def test_recovery_code_single_use_with_claim(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    ok, _, result = confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    assert ok
    code = result["recovery_codes"][0]
    assert consume_recovery_code(1, code)[0] is True
    assert consume_recovery_code(1, code)[0] is False


def test_regen_invalidates_old_recovery_code(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    ok, _, result = confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    old = result["recovery_codes"][0]
    ok2, _, new_codes = regenerate_recovery_codes(1)
    assert ok2 and new_codes
    assert consume_recovery_code(1, old)[0] is False
    assert consume_recovery_code(1, new_codes[0])[0] is True


def test_admin_audit_columns_no_pragma_on_postgres(monkeypatch):
    from core import admin_audit

    admin_audit._TABLE_READY = False
    called = {"pragma": 0}

    class _Opt:
        db_type = "postgresql"

        def list_table_columns(self, name):
            return ["id", "actor_user_id", "action", "outcome", "capability", "correlation_id"]

        def execute_query(self, sql, params=None, fetch=True):
            if "PRAGMA" in str(sql).upper():
                called["pragma"] += 1
                raise RuntimeError("PRAGMA not allowed")
            return []

    monkeypatch.setattr(admin_audit, "db_optimizer", _Opt())
    admin_audit._ensure_audit_columns()
    assert called["pragma"] == 0


def test_bearer_binding_preferred_when_cookie_also_present():
    """SPA sends Bearer + cookie; step-up must key off jti (not cookie)."""
    from flask import g

    from core.admin_security import get_admin_session_binding

    app = Flask(__name__)
    with app.test_request_context(
        "/api/admin/platform/security/mfa/totp/enroll",
        method="POST",
        headers={"Authorization": "Bearer unused.token.value"},
    ):
        g.session_id = "cookie-old"
        g.access_token_jti = "jti-active"
        assert get_admin_session_binding() == "jti:jti-active"


def test_rotation_rebinds_step_up_to_cookie_and_jti(monkeypatch):
    """After dual rotation, enroll must find step-up whether next request uses cookie or jti."""
    from flask import g

    from core.admin_security import establish_admin_step_up, rotate_session_after_step_up
    from core.admin_security_store import get_admin_security_store

    establish_admin_step_up(
        actor_user_id=1,
        method="password",
        mfa_completed=False,
        binding="jti:old-jti",
    )
    store = get_admin_security_store()
    assert store.get_json(store.k("stepup", 1, "jti:old-jti")) is not None

    app = Flask(__name__)

    class _Mgr:
        secret_key = "test-secret"
        algorithm = "HS256"

        def blacklist_token(self, *_a, **_k):
            return None

        def generate_tokens(self, user_id, user_data):
            import jwt as pyjwt
            import time as _t

            new_jti = "new-jti"
            access = pyjwt.encode(
                {"user_id": user_id, "jti": new_jti, "exp": int(_t.time()) + 3600},
                self.secret_key,
                algorithm=self.algorithm,
            )
            if isinstance(access, bytes):
                access = access.decode()
            return {
                "access_token": access,
                "refresh_token": "refresh",
                "expires_in": 3600,
            }

        def verify_access_token(self, token):
            import jwt as pyjwt

            return pyjwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr(
        "core.database_optimization.db_optimizer.execute_query",
        lambda *_a, **_k: [{"email": "a@b.c", "name": "A", "role": "admin"}],
    )

    class _Sess:
        def revoke_session(self, *_a, **_k):
            return True

        def create_session(self, user_id, user_data):
            return "new-cookie", {
                "key": "fikiri_session",
                "value": "new-cookie",
                "httponly": True,
                "samesite": "Lax",
            }

    monkeypatch.setattr("core.secure_sessions.secure_session_manager", _Sess())

    import jwt as pyjwt
    import time as _t

    old_access = pyjwt.encode(
        {"user_id": 1, "jti": "old-jti", "exp": int(_t.time()) + 3600},
        "test-secret",
        algorithm="HS256",
    )
    if isinstance(old_access, bytes):
        old_access = old_access.decode()

    with app.test_request_context(
        "/api/admin/platform/security/reauthenticate",
        method="POST",
        headers={"Authorization": f"Bearer {old_access}"},
    ):
        g.session_id = "old-cookie"
        g.access_token_jti = "old-jti"
        rotation = rotate_session_after_step_up(1)

    assert rotation.get("rotated") is True
    assert rotation.get("step_up_orphaned") is not True
    assert "jti:new-jti" in (rotation.get("new_bindings") or [])
    assert "cookie:new-cookie" in (rotation.get("new_bindings") or [])
    assert store.get_json(store.k("stepup", 1, "jti:new-jti")) is not None
    assert store.get_json(store.k("stepup", 1, "cookie:new-cookie")) is not None
    assert store.get_json(store.k("stepup", 1, "jti:old-jti")) is None


def test_destructive_remains_disabled():
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}
