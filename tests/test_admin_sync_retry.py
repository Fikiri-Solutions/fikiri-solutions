"""Gate review: admin retry of failed Gmail sync (ADMIN_DESTRUCTIVE_ENABLED stays off)."""

from __future__ import annotations

import json

import pytest
from flask import Flask

from core.admin_audit import clear_admin_audit_for_tests, list_admin_audit
from core.admin_security import (
    clear_admin_rate_limits_for_tests,
    clear_step_up_tokens_for_tests,
    establish_admin_step_up,
)
from core.admin_sync_ops import retry_failed_gmail_sync
from routes.admin_platform_api import admin_platform_bp
from tests.admin_test_util import prepare_admin_test_db


def _err_code(body: dict) -> str:
    return body.get("error_code") or body.get("code") or ""


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    monkeypatch.setenv("IMPERSONATION_ENABLED", "false")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "false")
    monkeypatch.delenv("ADMIN_DESTRUCTIVE_ENABLED", raising=False)
    monkeypatch.delenv("ADMIN_STEP_UP_BYPASS_FOR_TESTS", raising=False)
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()
    clear_admin_rate_limits_for_tests()
    prepare_admin_test_db(monkeypatch)
    monkeypatch.setattr("core.jwt_auth.jwt_auth_manager", None)

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.register_blueprint(admin_platform_bp)
    return application


@pytest.fixture
def client(app):
    yield app.test_client()
    clear_admin_audit_for_tests()
    clear_step_up_tokens_for_tests()


def _auth_headers(**extra):
    headers = {"Authorization": "Bearer sync-retry-token", "Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _mock_operator(monkeypatch, user_id=1, *, impersonating=False):
    class _Mgr:
        @staticmethod
        def verify_access_token(_token):
            payload = {"user_id": 55 if impersonating else user_id, "type": "access", "jti": "jti-sync"}
            if impersonating:
                payload["impersonating"] = True
                payload["actor_user_id"] = user_id
            return payload

    monkeypatch.setattr("core.jwt_auth.get_jwt_manager", lambda: _Mgr())
    monkeypatch.setattr("routes.admin_platform_api.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("routes.admin_platform_api.get_actor_user_id", lambda: user_id)
    monkeypatch.setattr("routes.admin_platform_api.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.secure_sessions.is_impersonating", lambda: impersonating)
    monkeypatch.setattr("core.admin_security.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.platform_admin.get_current_user_id", lambda: 55 if impersonating else user_id)
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")


def _seed_step_up(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")


def test_destructive_flag_still_off_for_ops_write(client, monkeypatch):
    """platform.ops.write remains blocked; retry_sync is a separate capability."""
    from core.platform_admin import require_platform_capability

    _mock_operator(monkeypatch)
    app = client.application

    @app.route("/api/admin/platform/_ops_write_probe")
    @require_platform_capability("platform.ops.write")
    def _probe():
        return {"ok": True}

    response = client.get("/api/admin/platform/_ops_write_probe", headers=_auth_headers())
    assert response.status_code == 403
    assert _err_code(json.loads(response.data)) == "DESTRUCTIVE_DISABLED"


def test_retry_requires_step_up(client, monkeypatch):
    _mock_operator(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )
    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/job-1/retry",
        headers=_auth_headers(),
        data=json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "k1"}),
    )
    assert response.status_code == 403
    assert _err_code(json.loads(response.data)) == "STEP_UP_REQUIRED"


def test_retry_rejects_cross_tenant_job(client, monkeypatch):
    _mock_operator(monkeypatch)
    _seed_step_up(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )

    def _fake_retry(**kwargs):
        # Simulate BOLA miss: job belongs to another tenant
        return None, "JOB_NOT_FOUND"

    monkeypatch.setattr("core.admin_sync_ops.retry_failed_gmail_sync", _fake_retry)

    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/other-tenant-job/retry",
        headers=_auth_headers(),
        data=json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "k2"}),
    )
    assert response.status_code == 404
    assert _err_code(json.loads(response.data)) == "JOB_NOT_FOUND"


def test_retry_rejects_tenant_mismatch_body(client, monkeypatch):
    _mock_operator(monkeypatch)
    _seed_step_up(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )
    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/job-1/retry",
        headers=_auth_headers(),
        data=json.dumps({"confirm": "retry", "tenant_id": 99, "idempotency_key": "k3"}),
    )
    assert response.status_code == 400
    assert _err_code(json.loads(response.data)) == "TENANT_MISMATCH"


def test_retry_requires_confirmation(monkeypatch):
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")
    result, err = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="job-1",
        idempotency_key="abc",
        confirm="yes",
    )
    assert result is None
    assert err == "CONFIRMATION_REQUIRED"


def test_retry_success_and_idempotent_replay(client, monkeypatch):
    _mock_operator(monkeypatch)
    _seed_step_up(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )

    calls = {"n": 0}

    def _fake_retry(**kwargs):
        calls["n"] += 1
        return (
            {
                "retried": True,
                "original_job_id": kwargs["job_id"],
                "new_job_id": "gmail_sync_55_1",
                "tenant_id": kwargs["tenant_id"],
                "enqueued": True,
                "enqueue_mode": "db_pending",
                "correlation_id": "c1",
            },
            None,
        )

    monkeypatch.setattr("core.admin_sync_ops.retry_failed_gmail_sync", _fake_retry)

    body = json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "same-key"})
    first = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/failed-job/retry",
        headers=_auth_headers(**{"Idempotency-Key": "same-key"}),
        data=body,
    )
    second = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/failed-job/retry",
        headers=_auth_headers(**{"Idempotency-Key": "same-key"}),
        data=body,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert json.loads(first.data)["data"]["new_job_id"] == "gmail_sync_55_1"
    # Route calls service each time; idempotency is enforced inside service.
    # Here we assert audit recorded success without secrets.
    audit = list_admin_audit(limit=20)
    successes = [i for i in audit["items"] if i.get("action") == "platform.sync.retry" and i.get("outcome") == "success"]
    assert successes
    raw = json.dumps(successes, default=str).lower()
    assert "access_token" not in raw
    assert "refresh_token" not in raw
    assert "bearer " not in raw


def test_retry_blocked_while_impersonating(client, monkeypatch):
    _mock_operator(monkeypatch, impersonating=True)
    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/job-1/retry",
        headers=_auth_headers(),
        data=json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "k"}),
    )
    assert response.status_code == 403


def test_claim_race_and_active_sync(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    clear_step_up_tokens_for_tests()
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")

    monkeypatch.setattr(
        "core.admin_sync_ops.evaluate_retry_eligibility",
        lambda **_k: (False, "SYNC_ALREADY_ACTIVE"),
    )
    result, err = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="job-active",
        idempotency_key="unique-1",
        confirm="retry",
    )
    assert result is None
    assert err == "SYNC_ALREADY_ACTIVE"

    monkeypatch.setattr(
        "core.admin_sync_ops.evaluate_retry_eligibility",
        lambda **_k: (True, None),
    )
    monkeypatch.setattr(
        "core.admin_sync_ops._claim_failed_job",
        lambda *_a, **_k: (False, "ALREADY_CLAIMED", "failed"),
    )
    result2, err2 = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="job-race",
        idempotency_key="unique-2",
        confirm="retry",
    )
    assert result2 is None
    assert err2 == "ALREADY_CLAIMED"


def test_service_idempotency_returns_cached(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    clear_step_up_tokens_for_tests()
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")

    inserts = {"n": 0}

    def _exec(query, params=None, fetch=True, **kwargs):
        q = str(query)
        if "INSERT INTO gmail_sync_jobs" in q:
            inserts["n"] += 1
            return 1
        if "UPDATE gmail_sync_jobs" in q and "admin_retry_claimed" in q and "SET status = 'admin_retry_claimed'" in q:
            return 1
        if "UPDATE gmail_sync_jobs" in q and "superseded_by_retry" in q:
            return 1
        return 1 if not fetch else []

    monkeypatch.setattr(
        "core.admin_sync_ops.evaluate_retry_eligibility",
        lambda **_k: (True, None),
    )
    monkeypatch.setattr("core.admin_sync_ops._claim_failed_job", lambda *_a, **_k: (True, None, "failed"))
    monkeypatch.setattr("core.admin_sync_ops._load_job", lambda *_a, **_k: {"metadata": "{}", "status": "admin_retry_claimed"})
    monkeypatch.setattr("core.admin_sync_ops._enqueue_with_stable_id", lambda *_a, **_k: "db_pending")
    monkeypatch.setattr("core.database_optimization.db_optimizer.execute_query", _exec)
    monkeypatch.setattr(
        "core.database_optimization.db_optimizer.upsert_user_sync_status_merge",
        lambda *_a, **_k: None,
    )

    first, err1 = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="failed-1",
        idempotency_key="idem-fixed",
        confirm="retry",
    )
    second, err2 = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="failed-1",
        idempotency_key="idem-fixed",
        confirm="retry",
    )
    assert err1 is None and err2 is None
    assert first["new_job_id"] == second["new_job_id"]
    assert second.get("replayed") is True
    assert inserts["n"] == 1


def test_idempotency_conflict_on_payload_change(monkeypatch):
    monkeypatch.setenv("ADMIN_SECURITY_STORE", "memory")
    clear_step_up_tokens_for_tests()
    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")

    monkeypatch.setattr("core.admin_sync_ops.evaluate_retry_eligibility", lambda **_k: (True, None))
    monkeypatch.setattr("core.admin_sync_ops._claim_failed_job", lambda *_a, **_k: (True, None, "failed"))
    monkeypatch.setattr("core.admin_sync_ops._load_job", lambda *_a, **_k: {"metadata": "{}"})
    monkeypatch.setattr("core.admin_sync_ops._enqueue_with_stable_id", lambda *_a, **_k: "db_pending")
    monkeypatch.setattr(
        "core.database_optimization.db_optimizer.execute_query",
        lambda *a, **k: 1,
    )
    monkeypatch.setattr(
        "core.database_optimization.db_optimizer.upsert_user_sync_status_merge",
        lambda *_a, **_k: None,
    )

    first, err1 = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="failed-1",
        idempotency_key="shared-key",
        confirm="retry",
    )
    assert err1 is None and first
    # Same client key, different job id → conflict
    second, err2 = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="failed-OTHER",
        idempotency_key="shared-key",
        confirm="retry",
    )
    assert second is None
    assert err2 == "IDEMPOTENCY_CONFLICT"


def test_claim_requires_single_row_update(monkeypatch):
    from core.admin_sync_ops import _claim_failed_job

    monkeypatch.setattr(
        "core.admin_sync_ops._load_job",
        lambda *_a, **_k: {"status": "failed", "metadata": "{}"},
    )
    monkeypatch.setattr(
        "core.database_optimization.db_optimizer.execute_query",
        lambda *a, **k: 0,  # no row updated
    )
    claimed, err, prev = _claim_failed_job(55, "job-1", 1)
    assert claimed is False
    assert err in ("ALREADY_CLAIMED", "JOB_NOT_RETRYABLE")
    assert prev == "failed"


def test_eligibility_rejects_permanent_and_missing_oauth(monkeypatch):
    from core.admin_sync_ops import evaluate_retry_eligibility

    monkeypatch.setattr("core.admin_sync_ops._tenant_is_active", lambda _t: True)
    monkeypatch.setattr("core.admin_sync_ops._gmail_oauth_present", lambda _t: False)
    ok, err = evaluate_retry_eligibility(
        tenant_id=55,
        job_id="gmail_sync_55_1",
        job_row={"job_id": "gmail_sync_55_1", "status": "failed", "metadata": "{}", "error_message": "x"},
        check_oauth=True,
    )
    assert ok is False
    assert err == "JOB_NOT_RETRYABLE"

    monkeypatch.setattr("core.admin_sync_ops._gmail_oauth_present", lambda _t: True)
    ok2, err2 = evaluate_retry_eligibility(
        tenant_id=55,
        job_id="gmail_sync_55_1",
        job_row={
            "job_id": "gmail_sync_55_1",
            "status": "failed",
            "metadata": "{}",
            "error_message": "invalid_grant: token revoked",
            "created_at": "2020-01-01",
        },
        check_oauth=True,
    )
    assert ok2 is False
    assert err2 == "JOB_NOT_RETRYABLE"

    ok3, err3 = evaluate_retry_eligibility(
        tenant_id=55,
        job_id="outlook_sync_55_1",
        job_row={
            "job_id": "outlook_sync_55_1",
            "status": "failed",
            "metadata": "{}",
            "error_message": "timeout",
        },
        check_oauth=True,
    )
    assert ok3 is False
    assert err3 == "JOB_NOT_RETRYABLE"


def test_store_unavailable_preserves_reason_and_does_not_mutate(client, monkeypatch):
    """STORE_UNAVAILABLE must stay distinct from QUEUE_UNAVAILABLE in API + audit."""
    _mock_operator(monkeypatch)
    _seed_step_up(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )

    # Service returns store outage before any claim/insert/enqueue.
    monkeypatch.setattr(
        "core.admin_sync_ops.retry_failed_gmail_sync",
        lambda **_k: (None, "STORE_UNAVAILABLE"),
    )

    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/gmail_sync_55_failed/retry",
        headers=_auth_headers(**{"Idempotency-Key": "store-down-key"}),
        data=json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "store-down-key"}),
    )
    body = json.loads(response.data)
    assert response.status_code == 503
    assert _err_code(body) == "STORE_UNAVAILABLE"
    assert body.get("data") in (None, {}, [])

    raw = json.dumps(body, default=str).lower()
    assert "redis://" not in raw
    assert "127.0.0.1" not in raw
    assert "traceback" not in raw
    assert "access_token" not in raw
    assert "refresh_token" not in raw
    assert "cookie" not in raw
    assert "connection refused" not in raw
    assert "eyj" not in raw

    audit = list_admin_audit(limit=20)
    denied = [
        i
        for i in audit["items"]
        if i.get("action") == "platform.sync.retry" and i.get("outcome") == "denied"
    ]
    assert denied
    reason = (denied[0].get("metadata") or {}).get("reason")
    assert reason == "STORE_UNAVAILABLE"
    assert reason != "QUEUE_UNAVAILABLE"

    audit_raw = json.dumps(denied, default=str).lower()
    assert "redis://" not in audit_raw
    assert "traceback" not in audit_raw
    assert "access_token" not in audit_raw
    assert "refresh_token" not in audit_raw
    assert "connection refused" not in audit_raw


def test_store_unavailable_service_does_not_mutate_or_enqueue(monkeypatch):
    """Shared-store outage fails closed before claim, insert, or queue."""
    from core.admin_security_store import AdminSecurityStoreUnavailable
    from core.admin_sync_ops import retry_failed_gmail_sync

    monkeypatch.setattr("core.admin_security.get_admin_session_binding", lambda: "jti:jti-sync")
    establish_admin_step_up(actor_user_id=1, method="password", binding="jti:jti-sync")
    # Isolate step-up read from the forced store outage so we exercise STORE_UNAVAILABLE.
    monkeypatch.setattr(
        "core.admin_security.get_admin_step_up_state",
        lambda _actor_id: {
            "method": "password",
            "mfa_completed": False,
            "binding": "jti:jti-sync",
            "exp": 10**12,
        },
    )
    monkeypatch.setattr("core.admin_security.step_up_required", lambda: True)

    class _DownStore:
        mode = "redis"
        available = False

        def require_available(self):
            raise AdminSecurityStoreUnavailable("admin security store unavailable")

        def k(self, *parts):
            return "fikiri:admin:" + ":".join(str(p) for p in parts)

    inserts = {"n": 0}
    claims = {"n": 0}
    enqueues = {"n": 0}
    original_status = {"status": "failed"}

    monkeypatch.setattr(
        "core.admin_security_store.get_admin_security_store",
        lambda **_k: _DownStore(),
    )

    def _claim(*_a, **_k):
        claims["n"] += 1
        return True, None, "failed"

    def _enqueue(*_a, **_k):
        enqueues["n"] += 1
        return "rq"

    monkeypatch.setattr("core.admin_sync_ops._claim_failed_job", _claim)
    monkeypatch.setattr("core.admin_sync_ops._enqueue_with_stable_id", _enqueue)


    def _exec(query, params=None, fetch=True, **kwargs):
        q = str(query)
        if "INSERT INTO gmail_sync_jobs" in q:
            inserts["n"] += 1
        return 1 if not fetch else [{"status": original_status["status"]}]

    monkeypatch.setattr("core.database_optimization.db_optimizer.execute_query", _exec)

    result, err = retry_failed_gmail_sync(
        actor_id=1,
        tenant_id=55,
        job_id="gmail_sync_55_failed",
        idempotency_key="store-svc-key",
        confirm="retry",
    )
    assert result is None
    assert err == "STORE_UNAVAILABLE"
    assert claims["n"] == 0
    assert inserts["n"] == 0
    assert enqueues["n"] == 0
    assert original_status["status"] == "failed"


def test_queue_unavailable_remains_distinct(client, monkeypatch):
    """Actual queue/dispatch failure must still report QUEUE_UNAVAILABLE."""
    _mock_operator(monkeypatch)
    _seed_step_up(monkeypatch)
    monkeypatch.setattr(
        "routes.admin_platform_api._fetch_user_row",
        lambda tid: {"id": tid, "email": "t@example.com", "is_active": 1},
    )
    monkeypatch.setattr(
        "core.admin_sync_ops.retry_failed_gmail_sync",
        lambda **_k: (None, "QUEUE_UNAVAILABLE"),
    )

    response = client.post(
        "/api/admin/platform/tenants/55/sync-jobs/gmail_sync_55_failed/retry",
        headers=_auth_headers(**{"Idempotency-Key": "queue-down-key"}),
        data=json.dumps({"confirm": "retry", "tenant_id": 55, "idempotency_key": "queue-down-key"}),
    )
    body = json.loads(response.data)
    assert response.status_code == 503
    assert _err_code(body) == "QUEUE_UNAVAILABLE"

    audit = list_admin_audit(limit=20)
    denied = [
        i
        for i in audit["items"]
        if i.get("action") == "platform.sync.retry"
        and i.get("outcome") == "denied"
        and (i.get("metadata") or {}).get("reason") == "QUEUE_UNAVAILABLE"
    ]
    assert denied
    assert (denied[0].get("metadata") or {}).get("reason") != "STORE_UNAVAILABLE"
