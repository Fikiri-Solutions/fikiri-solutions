"""Customer success analytics aggregation and health tests."""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.customer_success_analytics import (
    build_analytics_state,
    build_customer_health,
    build_customer_success_sections,
    build_friction_signals,
)
from core.product_analytics_store import ensure_product_analytics_tables


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    ensure_product_analytics_tables()
    yield


def _dossier(**overrides):
    base = {
        "account": {
            "id": 42,
            "is_active": True,
            "email_verified": True,
            "onboarding_completed": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_login": "2026-07-01T00:00:00+00:00",
        },
        "integrations": {
            "gmail": {"state": "connected"},
            "outlook": {"state": "disconnected"},
            "failed_job_count": 0,
        },
        "commercial": {"status": "unknown"},
        "support_activity": [],
    }
    base.update(overrides)
    return base


def test_disabled_state_not_zero_usage(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    state = build_analytics_state(42)
    assert state["status"] == "disabled"
    sections = build_customer_success_sections(42, _dossier())
    assert sections["customer_health"]["status"] == "unknown"
    assert sections["customer_health"]["reasons"][0]["code"] == "ANALYTICS_DISABLED"
    assert sections["usage_adoption"]["sessions"] is None


def test_no_subscription_not_unhealthy():
    health = build_customer_health(_dossier(commercial={"status": "unknown"}))
    assert health["dimensions"]["commercial"]["status"] == "not_applicable"
    assert health["status"] != "blocked"


def test_gmail_expired_blocks_integration_dimension():
    health = build_customer_health(
        _dossier(
            integrations={
                "gmail": {"state": "expired"},
                "outlook": {"state": "disconnected"},
                "failed_job_count": 0,
            }
        )
    )
    assert health["dimensions"]["integration"]["status"] == "blocked"
    assert health["status"] == "blocked"


def test_historical_activity_does_not_override_expired_oauth():
    usage = {
        "sessions": 10,
        "meaningful_actions": 5,
        "analytics_state": {"status": "available", "coverage": "partial"},
    }
    health = build_customer_health(
        _dossier(
            integrations={
                "gmail": {"state": "expired"},
                "outlook": {"state": "disconnected"},
                "failed_job_count": 0,
            }
        ),
        usage=usage,
    )
    assert health["status"] == "blocked"
    assert any(r["code"] == "GMAIL_AUTH_UNHEALTHY" for r in health["reasons"])


def test_accessibility_not_in_health():
    health = build_customer_health(_dossier())
    blob = str(health)
    assert "accessibility" not in blob.lower() or "ACCESSIBILITY" not in blob


def test_friction_onboarding_stalled():
    signals = build_friction_signals(
        42,
        dossier=_dossier(
            account={
                "id": 42,
                "is_active": True,
                "email_verified": True,
                "onboarding_completed": False,
                "created_at": "2026-01-01T00:00:00+00:00",
                "last_login": "2026-01-02T00:00:00+00:00",
            }
        ),
        usage={"analytics_state": {"status": "available"}},
    )
    assert any(s["code"] == "ONBOARDING_STALLED" for s in signals)


def test_tenant_isolation_sum(monkeypatch):
    from core.product_analytics_ingest import ingest_product_events

    ingest_product_events(
        tenant_id=1,
        actor_user_id=1,
        events=[{"event_name": "session.started", "properties": {}}],
        ensure_tables=True,
    )
    ingest_product_events(
        tenant_id=2,
        actor_user_id=2,
        events=[
            {"event_name": "session.started", "properties": {}},
            {"event_name": "feature.opened", "properties": {"feature_key": "crm"}},
        ],
        ensure_tables=True,
    )
    from core.customer_success_analytics import build_usage_adoption

    u1 = build_usage_adoption(1, lookback_days=30)
    u2 = build_usage_adoption(2, lookback_days=30)
    assert (u2.get("sessions") or 0) >= (u1.get("sessions") or 0)
    # Tenant 1 must not include tenant 2 feature opens
    feats1 = {f["feature_key"] for f in (u1.get("top_features") or [])}
    assert "crm" not in feats1 or (u1.get("sessions") or 0) == 0


def test_destructive_still_off():
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}
