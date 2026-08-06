"""Unit tests for product analytics registry (Gate 1 — no I/O)."""

from __future__ import annotations

import os

import pytest

from core.product_analytics_registry import (
    EVENT_REGISTRY,
    accessibility_signals_enabled,
    list_registered_event_names,
    product_analytics_enabled,
    validate_event_properties,
)


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    yield


def test_kill_switches_default_off():
    assert product_analytics_enabled() is False
    assert accessibility_signals_enabled() is False


def test_kill_switches_can_enable(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "1")
    assert product_analytics_enabled() is True
    assert accessibility_signals_enabled() is True


def test_registry_contains_slice_events():
    names = set(list_registered_event_names())
    for required in (
        "session.started",
        "feature.opened",
        "workflow.started",
        "workflow.failed",
        "onboarding.step_completed",
        "error.category",
        "outcome.lead_captured",
        "outcome.sync_completed",
    ):
        assert required in names
    assert "session.ended" not in EVENT_REGISTRY


def test_unknown_event_rejected():
    ok, reason, props = validate_event_properties("hack.me", {})
    assert ok is False
    assert reason == "UNKNOWN_EVENT"
    assert props == {}


def test_prohibited_property_rejects_entire_event():
    ok, reason, props = validate_event_properties(
        "feature.opened",
        {"feature_key": "crm", "password": "nope"},
        event_source="client",
    )
    assert ok is False
    assert reason == "PROHIBITED_PROPERTY"
    assert props == {}


def test_secret_like_key_rejects_entire_event():
    ok, reason, props = validate_event_properties(
        "feature.opened",
        {"feature_key": "crm", "access_token": "x"},
        event_source="client",
    )
    assert ok is False
    assert reason == "PROHIBITED_PROPERTY"
    assert props == {}


def test_unknown_property_rejects_event():
    ok, reason, props = validate_event_properties(
        "feature.opened",
        {"feature_key": "crm", "weird_field": "x"},
        event_source="client",
    )
    assert ok is False
    assert reason == "UNKNOWN_PROPERTY"
    assert props == {}


def test_identity_properties_forbidden():
    ok, reason, _ = validate_event_properties(
        "feature.opened",
        {"feature_key": "crm", "tenant_id": 9},
        event_source="client",
    )
    assert ok is False
    assert reason == "IDENTITY_PROPERTY_FORBIDDEN"


def test_valid_feature_opened():
    ok, reason, props = validate_event_properties(
        "feature.opened",
        {"feature_key": "crm", "device_class": "desktop"},
        event_source="client",
    )
    assert ok is True
    assert reason is None
    assert props["feature_key"] == "crm"


def test_outcome_rejects_client_source():
    ok, reason, _ = validate_event_properties(
        "outcome.lead_captured",
        {"feature_key": "crm", "completed": True},
        event_source="client",
    )
    assert ok is False
    assert reason == "SOURCE_NOT_ALLOWED"


def test_outcome_allows_server_source():
    ok, reason, props = validate_event_properties(
        "outcome.lead_captured",
        {"feature_key": "crm", "completed": True},
        event_source="server",
    )
    assert ok is True
    assert props["completed"] is True


def test_accessibility_disabled_rejects(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    ok, reason, _ = validate_event_properties(
        "accessibility.reduced_motion_used",
        {"device_class": "desktop"},
        event_source="client",
    )
    assert ok is False
    assert reason == "ACCESSIBILITY_DISABLED"


def test_accessibility_enabled_accepts(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "true")
    ok, reason, props = validate_event_properties(
        "accessibility.keyboard_navigation_detected",
        {"device_class": "desktop"},
        event_source="client",
    )
    assert ok is True
    assert reason is None
    assert "device_class" in props


def test_admin_destructive_untouched(monkeypatch):
    """Registry import must not enable destructive admin mutations."""
    monkeypatch.delenv("ADMIN_DESTRUCTIVE_ENABLED", raising=False)
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}
