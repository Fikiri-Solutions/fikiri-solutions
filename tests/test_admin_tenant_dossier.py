"""Read-only admin tenant support dossier tests."""

from __future__ import annotations

import json
import os

import pytest
from cryptography.fernet import Fernet
from flask import Flask

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.admin_audit import clear_admin_audit_for_tests, record_admin_audit
from core.admin_tenant_dossier import (
    build_impersonation_eligibility,
    build_support_checklist,
    build_tenant_dossier,
    _sanitize_message,
)
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db

_CANONICAL_STATUSES = frozenset(
    {"healthy", "attention", "blocked", "unknown", "not_applicable"}
)


def _checklist_by_id(items):
    return {i["id"]: i for i in items}


def _stub_dossier_deps(monkeypatch, *, gmail_state="disconnected", outlook_state="disconnected", jobs=None):
    jobs = jobs or {
        "job_counts": {
            "pending": 0,
            "processing": 0,
            "failed": 0,
            "completed": 0,
            "retrying": 0,
            "other": 0,
        },
        "latest_sanitized_error": None,
        "last_successful_sync_at": None,
        "last_failed_sync_at": None,
        "has_retryable_failed_job": False,
    }

    def _oauth(_uid, provider, _table):
        state = gmail_state if provider == "gmail" else outlook_state
        return {
            "provider": provider,
            "connected": state == "connected",
            "state": state,
            "expires_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr("core.admin_tenant_dossier._oauth_provider_state", _oauth)
    monkeypatch.setattr(
        "core.admin_tenant_dossier._access_summary",
        lambda *_a, **_k: {
            "active_session_count": 0,
            "last_login_ip": None,
            "last_login_user_agent": None,
        },
    )
    monkeypatch.setattr("core.admin_tenant_dossier._job_counts", lambda *_a, **_k: jobs)
    monkeypatch.setattr("core.admin_tenant_dossier._support_activity", lambda *_a, **_k: [])


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("ADMIN_LOCKDOWN", raising=False)
    prepare_admin_test_db(monkeypatch)
    clear_admin_audit_for_tests()
    yield
    clear_admin_audit_for_tests()
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(admin_platform_bp)
    return app.test_client()


def _auth_headers():
    return {"Authorization": "Bearer dossier-token"}


def _mock_operator(monkeypatch, user_id=1, *, impersonating=False):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            return {"user_id": user_id, "type": "access", "jti": "dossier-jti"}

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: user_id)
    monkeypatch.setattr("core.platform_admin.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.platform_admin.is_platform_admin", lambda uid: str(uid) in {"1"})
    monkeypatch.setattr(
        "core.platform_admin.get_platform_capabilities",
        lambda uid: set(__import__("core.platform_admin", fromlist=["PLATFORM_CAPABILITIES"]).PLATFORM_CAPABILITIES)
        if str(uid) == "1"
        else set(),
    )


def _sample_user(uid=9):
    return {
        "id": uid,
        "email": f"tenant{uid}@example.com",
        "name": "Tenant User",
        "role": "owner",
        "business_name": "Acme",
        "industry": "services",
        "is_active": True,
        "email_verified": True,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-02T00:00:00",
        "last_login": "2026-01-03T00:00:00",
        "onboarding_completed": False,
        "onboarding_step": 2,
        "metadata": {},
    }


def test_sanitize_message_strips_paths_and_secrets():
    raw = "failed /Users/mac/secret/file Bearer sk-abc eyJhbGciOiJIUzI1NiJ9.aaa.bbb"
    cleaned = _sanitize_message(raw)
    assert cleaned is not None
    assert "/Users/" not in cleaned
    assert "sk-abc" not in cleaned
    assert "eyJ" not in cleaned


def test_build_dossier_sections_and_unknown_oauth(monkeypatch):
    monkeypatch.setattr(
        "core.admin_tenant_dossier._oauth_provider_state",
        lambda *_a, **_k: {
            "provider": "gmail",
            "connected": False,
            "state": "unknown",
            "expires_at": None,
            "updated_at": None,
        },
    )
    monkeypatch.setattr(
        "core.admin_tenant_dossier._access_summary",
        lambda *_a, **_k: {
            "active_session_count": None,
            "last_login_ip": None,
            "last_login_user_agent": None,
        },
    )
    monkeypatch.setattr(
        "core.admin_tenant_dossier._job_counts",
        lambda *_a, **_k: {
            "job_counts": {"pending": 0, "processing": 0, "failed": 0, "completed": 0, "retrying": 0, "other": 0},
            "latest_sanitized_error": None,
            "last_successful_sync_at": None,
            "last_failed_sync_at": None,
            "has_retryable_failed_job": False,
        },
    )
    monkeypatch.setattr("core.admin_tenant_dossier._support_activity", lambda *_a, **_k: [])
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": False,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": {"tier": "starter", "status": "active", "current_period_end": None},
            "pending_gmail_jobs": 0,
        },
    )
    assert set(dossier.keys()) == {
        "account",
        "access",
        "integrations",
        "product_health",
        "commercial",
        "support_activity",
        "support_checklist",
        "impersonation_eligibility",
        "analytics_state",
        "customer_health",
        "usage_adoption",
        "friction_experience",
        "customer_outcomes",
    }
    assert dossier["integrations"]["gmail"]["state"] == "unknown"
    assert dossier["commercial"]["status"] == "active"
    assert isinstance(dossier["support_checklist"], list)
    assert len(dossier["support_checklist"]) >= 5
    assert "stripe" not in json.dumps(dossier["commercial"]).lower()
    blob = json.dumps(dossier)
    assert "access_token" not in blob
    assert "refresh_token" not in blob


def test_ai_budget_snapshot_does_not_emit_alerts(monkeypatch):
    from core.ai_budget_guardrails import AIBudgetGuardrails

    calls = {"emit": 0}
    guard = AIBudgetGuardrails()
    monkeypatch.setattr(guard, "_subscription_tier", lambda _uid: "starter")
    monkeypatch.setattr(guard, "_budget_cap_usd", lambda _tier: 10.0)
    monkeypatch.setattr(guard, "_estimated_cost_per_response", lambda: 0.001)
    monkeypatch.setattr(guard, "_monthly_usage_count", lambda _uid, _m: 0)

    def _boom(*_a, **_k):
        calls["emit"] += 1
        raise AssertionError("alerts must not emit on snapshot")

    monkeypatch.setattr(guard, "_emit_alerts", _boom)
    decision = guard.snapshot(9)
    assert decision.allowed is True
    assert calls["emit"] == 0
    # Default evaluate still emits (side effect path for live AI gates)
    monkeypatch.setattr(guard, "_emit_alerts", lambda *_a, **_k: calls.__setitem__("emit", calls["emit"] + 1))
    guard.evaluate(9, projected_increment=0)
    assert calls["emit"] == 1

def test_support_activity_tenant_bound_and_sanitized(monkeypatch):
    from core.admin_audit import ensure_admin_audit_table
    from core.admin_tenant_dossier import _support_activity

    ensure_admin_audit_table()
    record_admin_audit(
        actor_user_id=1,
        action="platform.impersonate.start",
        outcome="success",
        target_type="user",
        target_id="9",
        metadata={"reason": "support"},
        correlation_id="corr-abcdefghijklmnop",
    )
    record_admin_audit(
        actor_user_id=1,
        action="platform.impersonate.start",
        outcome="success",
        target_type="user",
        target_id="99",
        metadata={"token": "should-not-leak"},
    )
    items = _support_activity(9, limit=20)
    assert items
    assert all(str(i.get("target_id")) == "9" for i in items)
    assert all("token" not in json.dumps(i) for i in items)
    assert all(i.get("correlation_id") is None or len(i["correlation_id"]) <= 12 for i in items)


def test_get_tenant_dossier_operator_ok(client, monkeypatch):
    _mock_operator(monkeypatch, 1)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: _sample_user(tid) if tid == 9 else None,
    )
    monkeypatch.setattr(
        "routes.admin_platform_api._integration_summary",
        lambda _tid: {
            "gmail_connected": True,
            "outlook_connected": False,
            "sync_status": {"sync_status": "idle", "last_sync": "2026-01-01"},
            "subscription": {"tier": "growth", "status": "active", "current_period_end": "2026-02-01"},
            "pending_gmail_jobs": 1,
        },
    )
    monkeypatch.setattr(
        "core.admin_tenant_dossier.build_tenant_dossier",
        lambda user_row, infrastructure, **_k: {
            "account": {"id": user_row["id"], "email": user_row["email"], "is_active": True, "email_verified": True, "onboarding_completed": False},
            "access": {"is_active": True, "email_verified": True, "active_session_count": 0},
            "integrations": {
                "gmail": {"provider": "gmail", "connected": True, "state": "connected"},
                "outlook": {"provider": "outlook", "connected": False, "state": "disconnected"},
                "pending_job_count": 1,
                "processing_job_count": 0,
                "failed_job_count": 0,
                "job_counts": {},
            },
            "product_health": {
                "onboarding_complete": False,
                "onboarding_blockers": ["onboarding_incomplete_step_2"],
                "entitlements_enabled": [],
                "entitlements_disabled": [],
                "ai_budget": {"status": "unknown"},
                "background_jobs": {},
            },
            "commercial": {"tier": "growth", "status": "active", "past_due": False},
            "support_activity": [],
        },
    )
    response = client.get("/api/admin/platform/tenants/9", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)["data"]
    assert body["tenant"]["id"] == 9
    assert body["infrastructure"]["gmail_connected"] is True
    assert body["account"]["id"] == 9
    assert body["integrations"]["gmail"]["state"] == "connected"
    assert "access_token" not in json.dumps(body)


def test_get_tenant_forbidden_non_operator(client, monkeypatch):
    _mock_operator(monkeypatch, 42)
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    response = client.get("/api/admin/platform/tenants/9", headers=_auth_headers())
    assert response.status_code == 403


def test_get_tenant_forbidden_while_impersonating(client, monkeypatch):
    _mock_operator(monkeypatch, 1, impersonating=True)
    response = client.get("/api/admin/platform/tenants/9", headers=_auth_headers())
    assert response.status_code == 403


def test_get_tenant_missing(client, monkeypatch):
    _mock_operator(monkeypatch, 1)
    monkeypatch.setattr("routes.admin_platform_api._fetch_user_row", lambda _tid: None)
    response = client.get("/api/admin/platform/tenants/404", headers=_auth_headers())
    assert response.status_code == 404
    body = json.loads(response.data)
    assert (body.get("error_code") or body.get("code")) == "TENANT_NOT_FOUND"


def test_get_tenant_no_cross_tenant_leak(client, monkeypatch):
    _mock_operator(monkeypatch, 1)

    def _fetch(tid):
        return _sample_user(tid)

    monkeypatch.setattr("routes.admin_platform_api._fetch_user_row", _fetch)
    monkeypatch.setattr(
        "routes.admin_platform_api._integration_summary",
        lambda tid: {"gmail_connected": False, "outlook_connected": False, "sync_status": None, "subscription": None, "pending_gmail_jobs": 0},
    )

    def _dossier(user_row, infrastructure, **_k):
        return {
            "account": {"id": user_row["id"], "email": user_row["email"], "is_active": True, "email_verified": True, "onboarding_completed": True},
            "access": {"is_active": True, "email_verified": True},
            "integrations": {
                "gmail": {"provider": "gmail", "connected": False, "state": "disconnected"},
                "outlook": {"provider": "outlook", "connected": False, "state": "disconnected"},
                "pending_job_count": 0,
                "processing_job_count": 0,
                "failed_job_count": 0,
                "job_counts": {},
            },
            "product_health": {
                "onboarding_complete": True,
                "onboarding_blockers": [],
                "entitlements_enabled": [],
                "entitlements_disabled": [],
                "ai_budget": {"status": "unknown"},
                "background_jobs": {},
            },
            "commercial": {"status": "unknown"},
            "support_activity": [{"target_id": str(user_row["id"]), "action": "platform.x", "outcome": "success"}],
        }

    monkeypatch.setattr("core.admin_tenant_dossier.build_tenant_dossier", _dossier)
    a = json.loads(client.get("/api/admin/platform/tenants/9", headers=_auth_headers()).data)["data"]
    b = json.loads(client.get("/api/admin/platform/tenants/11", headers=_auth_headers()).data)["data"]
    assert a["account"]["id"] == 9
    assert b["account"]["id"] == 11
    assert a["support_activity"][0]["target_id"] == "9"
    assert b["support_activity"][0]["target_id"] == "11"


def test_destructive_still_off():
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


def test_checklist_zero_failed_jobs_never_claims_retryable(monkeypatch):
    _stub_dossier_deps(
        monkeypatch,
        gmail_state="connected",
        jobs={
            "job_counts": {
                "pending": 0,
                "processing": 0,
                "failed": 0,
                "completed": 1,
                "retrying": 0,
                "other": 0,
            },
            "latest_sanitized_error": None,
            "last_successful_sync_at": "2026-01-01T00:00:00",
            "last_failed_sync_at": None,
            "has_retryable_failed_job": False,
        },
    )
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": True,
            "outlook_connected": False,
            "sync_status": {"sync_status": "idle"},
            "subscription": {"tier": "starter", "status": "active"},
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    retry = by_id["no_retryable_failed_jobs"]
    recent = by_id["no_recent_failures"]
    assert retry["status"] in {"healthy", "not_applicable"}
    assert "present" not in retry["label"].lower()
    assert retry["label"] == "No retryable failed jobs"
    assert "No retryable failed jobs" in (retry.get("explanation") or "")
    assert recent["status"] == "healthy"
    assert recent["label"] == "No recent failures"
    assert all(i["status"] in _CANONICAL_STATUSES for i in dossier["support_checklist"])
    assert "pass" not in json.dumps(dossier["support_checklist"])
    assert "fail" not in {i["status"] for i in dossier["support_checklist"]}


def test_checklist_retryable_jobs_attention_not_healthy(monkeypatch):
    _stub_dossier_deps(
        monkeypatch,
        gmail_state="connected",
        jobs={
            "job_counts": {
                "pending": 0,
                "processing": 0,
                "failed": 2,
                "completed": 0,
                "retrying": 0,
                "other": 0,
            },
            "latest_sanitized_error": "timeout",
            "last_successful_sync_at": None,
            "last_failed_sync_at": "2026-01-02T00:00:00",
            "has_retryable_failed_job": True,
        },
    )
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": True,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": None,
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    assert by_id["no_retryable_failed_jobs"]["status"] == "attention"
    assert by_id["no_recent_failures"]["status"] in {"attention", "blocked"}
    assert by_id["no_recent_failures"]["status"] != "healthy"


def test_checklist_gmail_expired_outlook_disconnected_blocked(monkeypatch):
    _stub_dossier_deps(
        monkeypatch,
        gmail_state="expired",
        outlook_state="disconnected",
        jobs={
            "job_counts": {
                "pending": 0,
                "processing": 0,
                "failed": 0,
                "completed": 1,
                "retrying": 0,
                "other": 0,
            },
            "latest_sanitized_error": None,
            "last_successful_sync_at": "2026-01-01T00:00:00",
            "last_failed_sync_at": None,
            "has_retryable_failed_job": False,
        },
    )
    dossier = build_tenant_dossier(
        {**_sample_user(), "is_active": False, "email_verified": False, "onboarding_completed": True},
        infrastructure={
            "gmail_connected": False,
            "outlook_connected": False,
            "sync_status": {"sync_status": "partial"},
            "subscription": None,
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    integration = by_id["email_integration_usable"]
    assert integration["status"] == "blocked"
    assert integration["status"] != "unknown"
    assert "expired" in (integration.get("explanation") or "").lower()
    # Historical successful sync must not override expired OAuth.
    assert by_id["sync_job_health"]["status"] == "blocked"
    assert "authorize" in (by_id["sync_job_health"].get("explanation") or "").lower()
    account = by_id["account_usable"]
    assert account["status"] == "blocked"
    assert "inactive" in (account.get("explanation") or "").lower()
    assert "unverified" in (account.get("explanation") or "").lower()


def test_checklist_healthy_plus_unhealthy_secondary_is_attention(monkeypatch):
    _stub_dossier_deps(
        monkeypatch,
        gmail_state="expired",
        outlook_state="connected",
    )
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": False,
            "outlook_connected": True,
            "sync_status": None,
            "subscription": {"status": "active"},
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    assert by_id["email_integration_usable"]["status"] == "attention"


def test_checklist_missing_integration_unknown(monkeypatch):
    _stub_dossier_deps(monkeypatch, gmail_state="unknown", outlook_state="unknown")
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": False,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": None,
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    assert by_id["email_integration_usable"]["status"] == "unknown"


def test_checklist_disconnected_both_not_applicable(monkeypatch):
    _stub_dossier_deps(monkeypatch, gmail_state="disconnected", outlook_state="disconnected")
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": False,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": None,
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    assert by_id["email_integration_usable"]["status"] == "not_applicable"


def test_impersonation_eligibility_inactive_sanitized():
    eligibility = build_impersonation_eligibility({"is_active": False, "email_verified": False})
    assert eligibility["eligible"] is False
    assert eligibility["reason_code"] == "USER_INACTIVE"
    assert eligibility["reason_label"] == "Account inactive"
    assert "password" not in json.dumps(eligibility).lower()
    assert "token" not in json.dumps(eligibility).lower()


def test_impersonation_eligibility_active():
    eligibility = build_impersonation_eligibility({"is_active": True})
    assert eligibility["eligible"] is True
    assert eligibility["reason_code"] == "AVAILABLE"


def test_checklist_agrees_with_dossier_source_fields(monkeypatch):
    _stub_dossier_deps(
        monkeypatch,
        gmail_state="connected",
        jobs={
            "job_counts": {
                "pending": 0,
                "processing": 0,
                "failed": 0,
                "completed": 0,
                "retrying": 0,
                "other": 0,
            },
            "latest_sanitized_error": None,
            "last_successful_sync_at": None,
            "last_failed_sync_at": None,
            "has_retryable_failed_job": False,
        },
    )
    dossier = build_tenant_dossier(
        _sample_user(),
        infrastructure={
            "gmail_connected": True,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": {"status": "trialing"},
            "pending_gmail_jobs": 0,
        },
    )
    by_id = _checklist_by_id(dossier["support_checklist"])
    assert dossier["integrations"]["failed_job_count"] == 0
    assert dossier["integrations"]["has_retryable_failed_job"] is False
    assert by_id["no_retryable_failed_jobs"]["status"] in {"healthy", "not_applicable"}
    assert by_id["no_recent_failures"]["status"] == "healthy"
    assert dossier["impersonation_eligibility"]["eligible"] is True
    # Re-derive from sections alone must match attached checklist.
    rebuilt = build_support_checklist(dossier)
    assert _checklist_by_id(rebuilt)["email_integration_usable"]["status"] == by_id[
        "email_integration_usable"
    ]["status"]


def test_get_tenant_includes_impersonation_eligibility(client, monkeypatch):
    _mock_operator(monkeypatch, 1)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {**_sample_user(tid), "is_active": False} if tid == 9 else None,
    )
    monkeypatch.setattr(
        "routes.admin_platform_api._integration_summary",
        lambda _tid: {
            "gmail_connected": False,
            "outlook_connected": False,
            "sync_status": None,
            "subscription": None,
            "pending_gmail_jobs": 0,
        },
    )
    _stub_dossier_deps(monkeypatch, gmail_state="expired", outlook_state="disconnected")
    # Use real build_tenant_dossier (do not stub).
    response = client.get("/api/admin/platform/tenants/9", headers=_auth_headers())
    assert response.status_code == 200
    body = json.loads(response.data)["data"]
    assert body["impersonation_eligibility"]["eligible"] is False
    assert body["impersonation_eligibility"]["reason_code"] == "USER_INACTIVE"
    by_id = _checklist_by_id(body["support_checklist"])
    assert by_id["impersonation_available"]["status"] == "blocked"
    assert "inactive" in (by_id["impersonation_available"].get("explanation") or "").lower()
    assert "step-up" not in (by_id["impersonation_available"].get("explanation") or "").lower()
    blob = json.dumps(body)
    assert "access_token" not in blob
    assert "refresh_token" not in blob
