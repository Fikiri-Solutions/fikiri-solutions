"""Read-only product analytics ops health + reconciliation."""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.product_analytics_emit import emit_server_product_event
from core.product_analytics_ops import (
    build_analytics_ops_health,
    build_analytics_ops_report,
    normalize_lookback_days,
    reconcile_recent_outcomes,
)
from core.product_analytics_store import ensure_product_analytics_tables, increment_ops_counter


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    monkeypatch.delenv("PRODUCT_ANALYTICS_TENANT_ALLOWLIST", raising=False)
    ensure_product_analytics_tables()
    yield
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


def test_normalize_lookback_days():
    assert normalize_lookback_days(7) == 7
    assert normalize_lookback_days(30) == 30
    assert normalize_lookback_days(14) == 30
    assert normalize_lookback_days(3) == 7


def test_ops_health_includes_state_and_counters():
    tenant = 9200 + (uuid.uuid4().int % 50)
    increment_ops_counter(tenant, storage_failures=2, rejected_events=3)
    health = build_analytics_ops_health(tenant, lookback_days=7)
    assert health["analytics_enabled"] is True
    assert health["analytics_state"] in {
        "disabled",
        "collecting",
        "available",
        "stale",
        "unavailable",
    }
    assert health["storage_failure_count"] >= 2
    assert health["rejected_event_count"] >= 3
    assert "last_event_at" in health
    assert "last_aggregated_at" in health


def test_disabled_ops_health(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    health = build_analytics_ops_health(42, lookback_days=7)
    assert health["analytics_enabled"] is False
    assert health["analytics_state"] == "disabled"


def test_reconciliation_report_only_no_backfill(monkeypatch):
    tenant = 9300
    monkeypatch.setattr(
        "core.product_analytics_ops._fetch_recent_leads",
        lambda *_a, **_k: [{"id": 101, "created_at": "2026-07-01"}],
    )
    monkeypatch.setattr(
        "core.product_analytics_ops._fetch_recent_completed_syncs",
        lambda *_a, **_k: [{"job_id": "gmail_sync_x", "completed_at": "2026-07-01", "status": "completed"}],
    )
    monkeypatch.setattr(
        "core.product_analytics_ops._outcome_exists",
        lambda *_a, **_k: False,
    )
    report = reconcile_recent_outcomes(tenant, lookback_days=7)
    assert report["backfill"] is False
    assert report["leads"]["missing_count"] == 1
    assert report["gmail_syncs"]["missing_count"] == 1
    assert report["leads"]["missing_ids"] == ["101"]


def test_reconciliation_matched_after_emit():
    tenant = 9400 + (uuid.uuid4().int % 50)
    lead_id = str(uuid.uuid4().int % 100000)
    emit_server_product_event(
        tenant_id=tenant,
        actor_user_id=tenant,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=lead_id,
        properties={
            "feature_key": "crm",
            "workflow_key": "lead_capture",
            "outcome": "lead_captured",
            "completed": True,
            "source_category": "manual",
            "creation_channel": "crm_ui",
        },
        ensure_tables=True,
    )
    from core.product_analytics_ops import _outcome_exists

    assert _outcome_exists(
        tenant,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=lead_id,
    )


def test_full_report_read_only_flags():
    report = build_analytics_ops_report(42, lookback_days=7, include_reconciliation=True)
    assert report["read_only"] is True
    assert report["mutations"] is False
    assert "health" in report
    assert "reconciliation" in report
    assert report["reconciliation"]["backfill"] is False


def test_analytics_ops_route_is_get_only():
    import inspect
    from routes import admin_platform_api as mod

    src = inspect.getsource(mod.get_tenant_analytics_ops)
    assert "build_analytics_ops_report" in src
    assert "POST" not in src
    retry_src = inspect.getsource(mod.retry_tenant_sync_job)
    assert "build_analytics_ops_report" not in retry_src
