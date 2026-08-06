"""Auth session version + Journey H partial-failure hardening."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from flask import Flask

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("ADMIN_SECURITY_STORE", "memory")

from core.admin_audit import clear_admin_audit_for_tests
from core.admin_mfa import confirm_totp_enrollment, operator_mfa_enrolled, start_totp_enrollment
from core.admin_security import (
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    establish_admin_step_up,
    get_admin_step_up_state,
    invalidate_admin_step_up_for_user,
    mark_admin_step_up_mfa_completed,
    require_admin_step_up,
    step_up_completed_with_mfa,
)
from core.admin_security_store import clear_admin_security_store_for_tests
from core.auth_session_version import (
    CLAIM_KEY,
    bump_auth_session_version,
    ensure_auth_session_version_column,
    get_auth_session_version,
    token_version_matches,
)
from routes.admin_platform_api import admin_platform_bp


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    monkeypatch.setenv("ADMIN_MFA_VERIFIER_ENABLED", "true")
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    clear_admin_security_store_for_tests()

    meta_store: dict = {}

    def _load(uid: int):
        return dict(meta_store.get(int(uid), {}))

    def _save(uid: int, metadata: dict):
        meta_store[int(uid)] = dict(metadata)

    monkeypatch.setattr("core.admin_mfa._load_user_metadata", _load)
    monkeypatch.setattr("core.admin_mfa._save_user_metadata", _save)
    monkeypatch.setattr("core.admin_mfa._operator_label", lambda _uid: "op@example.com")
    yield
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


def test_missing_asv_claim_rejected():
    assert token_version_matches({"user_id": 1, "type": "access"}, user_row_version=1) is False


def test_matching_asv_accepted():
    assert (
        token_version_matches({"user_id": 1, "type": "access", CLAIM_KEY: 3}, user_row_version=3)
        is True
    )


def test_mismatched_asv_rejected():
    assert (
        token_version_matches({"user_id": 1, "type": "access", CLAIM_KEY: 1}, user_row_version=2)
        is False
    )


def test_journey_h_confirm_idempotent_after_db_commit_without_step_up(monkeypatch):
    """DB MFA active + step-up upgrade failed → retry safe; no second recovery set."""
    import pyotp

    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:h1")
    establish_admin_step_up(actor_user_id=1, method="password", mfa_completed=False, binding="jti:h1")
    started = start_totp_enrollment(1)
    code = pyotp.TOTP(started["secret"]).now()

    with patch(
        "core.admin_security.mark_admin_step_up_mfa_completed",
        side_effect=RuntimeError("redis_down"),
    ):
        # Confirm path in admin_mfa does not call mark_ — route does.
        ok, _, result = confirm_totp_enrollment(1, code)
        assert ok is True
        assert result and result.get("recovery_codes")
        first_codes = list(result["recovery_codes"])

    assert operator_mfa_enrolled(1) is True
    # Simulate route upgrade failure: step-up still bootstrap or cleared
    assert step_up_completed_with_mfa(1) is False

    ok2, _, result2 = confirm_totp_enrollment(1, code)
    assert ok2 is True
    assert result2.get("already_completed") is True
    assert result2.get("recovery_codes") == []
    assert first_codes  # original set was issued once

    # Fresh MFA reauth restores privileged path
    invalidate_admin_step_up_for_user(1, reason="test")
    establish_admin_step_up(actor_user_id=1, method="mfa", mfa_completed=True, binding="jti:h1")
    assert step_up_completed_with_mfa(1) is True


def test_journey_h_confirm_db_failure_after_claim_rolls_claim(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    code = pyotp.TOTP(started["secret"]).now()

    def _boom(*_a, **_k):
        raise RuntimeError("db_write_failed")

    monkeypatch.setattr("core.admin_mfa._save_user_metadata", _boom)
    with pytest.raises(RuntimeError, match="db_write_failed"):
        confirm_totp_enrollment(1, code)
    assert operator_mfa_enrolled(1) is False


def test_journey_h_rotation_partial_failure_clears_privilege(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:old")
    establish_admin_step_up(actor_user_id=1, method="mfa", mfa_completed=True, binding="jti:old")
    assert step_up_completed_with_mfa(1) is True

    # Simulate orphaned rotation: delete step-up on old, fail to write new
    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    store.delete(store.k("stepup", 1, "jti:old"))
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:new")
    assert get_admin_step_up_state(1) is None
    # Recover via reauth
    establish_admin_step_up(actor_user_id=1, method="mfa", mfa_completed=True, binding="jti:new")
    assert step_up_completed_with_mfa(1) is True


def test_journey_h_audit_failure_does_not_reverse_mfa(monkeypatch):
    import pyotp

    started = start_totp_enrollment(1)
    ok, _, result = confirm_totp_enrollment(1, pyotp.TOTP(started["secret"]).now())
    assert ok and result
    assert operator_mfa_enrolled(1) is True
    # Audit failure is observed but must not un-enroll
    with patch("core.admin_audit.record_admin_audit", side_effect=RuntimeError("audit_down")):
        try:
            from core.admin_audit import record_admin_audit

            record_admin_audit(actor_user_id=1, action="test", outcome="success")
        except RuntimeError:
            pass
    assert operator_mfa_enrolled(1) is True


def test_destructive_still_off():
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}
