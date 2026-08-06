"""Server-side outcome emission tests (lead + Gmail sync)."""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from core.product_analytics_emit import (
    build_outcome_dedupe_key,
    emit_server_product_event,
    map_gmail_sync_type,
    map_lead_source_category,
    processed_count_bucket,
)
from core.product_analytics_store import (
    count_outcome_events,
    ensure_product_analytics_tables,
    sum_daily_metrics,
)


def _uid(prefix: str = "o") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ADMIN_DESTRUCTIVE_ENABLED", "false")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED", "false")
    monkeypatch.delenv("PRODUCT_ANALYTICS_TENANT_ALLOWLIST", raising=False)
    ensure_product_analytics_tables()
    yield
    assert (os.getenv("ADMIN_DESTRUCTIVE_ENABLED") or "false").lower() in {"false", "0", ""}


def test_dedupe_key_format():
    assert build_outcome_dedupe_key(
        event_name="outcome.lead_captured", object_type="lead", object_id="99"
    ) == "lead_captured:lead:99"


def test_emit_lead_once_then_duplicate():
    lead_id = _uid("lead")
    props = {
        "feature_key": "crm",
        "workflow_key": "lead_capture",
        "outcome": "lead_captured",
        "completed": True,
        "source_category": "manual",
        "creation_channel": "crm_ui",
    }
    first = emit_server_product_event(
        tenant_id=7001,
        actor_user_id=7001,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=lead_id,
        properties=props,
        ensure_tables=True,
    )
    second = emit_server_product_event(
        tenant_id=7001,
        actor_user_id=7001,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=lead_id,
        properties=props,
        ensure_tables=True,
    )
    assert first.get("reason") == "OK", first
    assert first["emitted"] is True
    assert second["emitted"] is False
    assert second["duplicate"] is True


def test_disabled_emits_nothing(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    result = emit_server_product_event(
        tenant_id=7002,
        actor_user_id=7002,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=_uid("lead"),
        properties={
            "feature_key": "crm",
            "workflow_key": "lead_capture",
            "outcome": "lead_captured",
            "completed": True,
            "source_category": "manual",
            "creation_channel": "crm_ui",
        },
    )
    assert result["emitted"] is False
    assert result["reason"] == "DISABLED"


def test_allowlist_blocks_other_tenants(monkeypatch):
    monkeypatch.setenv("PRODUCT_ANALYTICS_TENANT_ALLOWLIST", "1,2")
    blocked = emit_server_product_event(
        tenant_id=99,
        actor_user_id=99,
        event_name="outcome.sync_completed",
        object_type="gmail_sync_job",
        object_id=_uid("job"),
        properties={
            "feature_key": "integrations",
            "workflow_key": "email_sync",
            "outcome": "sync_completed",
            "completed": True,
            "provider": "gmail",
            "sync_type": "incremental",
            "result_category": "completed",
            "processed_count_bucket": "1_to_10",
        },
        ensure_tables=True,
    )
    assert blocked["reason"] == "TENANT_NOT_IN_ALLOWLIST"
    assert blocked["emitted"] is False


def test_impersonation_excluded(monkeypatch):
    monkeypatch.setattr(
        "core.product_analytics_emit._is_impersonating_safe",
        lambda: True,
    )
    result = emit_server_product_event(
        tenant_id=7003,
        actor_user_id=1,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=_uid("lead"),
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
    assert result["emitted"] is False
    assert result["reason"] == "IMPERSONATION_EXCLUDED"


def test_prohibited_property_rejects_without_storing(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        result = emit_server_product_event(
            tenant_id=7004,
            actor_user_id=7004,
            event_name="outcome.lead_captured",
            object_type="lead",
            object_id=_uid("lead"),
            correlation_id="corr-prohibit-1",
            properties={
                "feature_key": "crm",
                "workflow_key": "lead_capture",
                "outcome": "lead_captured",
                "completed": True,
                "source_category": "manual",
                "creation_channel": "crm_ui",
                "email": "leak@example.com",
            },
            ensure_tables=True,
        )
    assert result["emitted"] is False
    assert result["reason"] in {"UNKNOWN_PROPERTY", "PROHIBITED_PROPERTY"}
    # Programmer reject is visible; payload values must not appear in logs.
    assert any(
        getattr(r, "msg", "") == "server product analytics programmer reject"
        or "programmer reject" in str(r.message).lower()
        for r in caplog.records
    )
    joined = " ".join(str(r.getMessage()) for r in caplog.records)
    assert "leak@example.com" not in joined
    assert "leak@example.com" not in caplog.text


def test_storage_unavailable_controlled(monkeypatch):
    monkeypatch.setattr(
        "core.product_analytics_emit.tables_available", lambda: False
    )
    result = emit_server_product_event(
        tenant_id=7005,
        actor_user_id=7005,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=_uid("lead"),
        properties={
            "feature_key": "crm",
            "workflow_key": "lead_capture",
            "outcome": "lead_captured",
            "completed": True,
            "source_category": "manual",
            "creation_channel": "crm_ui",
        },
    )
    assert result["emitted"] is False
    assert result["reason"] == "STORAGE_UNAVAILABLE"
    assert result["analytics_available"] is False


def test_unexpected_insert_error_logged_without_payload(monkeypatch, caplog):
    import logging

    class SchemaMismatchError(Exception):
        pass

    monkeypatch.setattr(
        "core.product_analytics_emit.insert_product_event",
        MagicMock(side_effect=SchemaMismatchError("column outcome_dedupe_key missing")),
    )
    with caplog.at_level(logging.ERROR):
        result = emit_server_product_event(
            tenant_id=7006,
            actor_user_id=7006,
            event_name="outcome.lead_captured",
            object_type="lead",
            object_id=_uid("lead"),
            correlation_id="corr-unexpected-1",
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
    assert result["emitted"] is False
    assert result["reason"] == "UNEXPECTED_ERROR"
    assert any("unexpected error" in str(r.message).lower() for r in caplog.records)
    # Never log event property values (extra fields are sanitized identifiers only).
    assert "creation_channel" not in caplog.text
    for record in caplog.records:
        extras = getattr(record, "__dict__", {})
        assert "properties" not in extras
        assert extras.get("event_name") == "outcome.lead_captured"


def test_emit_never_raises_on_inner_blowup(monkeypatch):
    monkeypatch.setattr(
        "core.product_analytics_emit.validate_event_properties",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    result = emit_server_product_event(
        tenant_id=7007,
        actor_user_id=7007,
        event_name="outcome.lead_captured",
        object_type="lead",
        object_id=_uid("lead"),
        properties={
            "feature_key": "crm",
            "workflow_key": "lead_capture",
            "outcome": "lead_captured",
            "completed": True,
            "source_category": "manual",
            "creation_channel": "crm_ui",
        },
    )
    assert result["emitted"] is False
    assert result["reason"] == "UNEXPECTED_ERROR"


def test_sync_emit_and_meaningful_rollup():
    tenant = 8000 + (uuid.uuid4().int % 1000)
    result = emit_server_product_event(
        tenant_id=tenant,
        actor_user_id=tenant,
        event_name="outcome.sync_completed",
        object_type="gmail_sync_job",
        object_id=_uid("job"),
        properties={
            "feature_key": "integrations",
            "workflow_key": "email_sync",
            "outcome": "sync_completed",
            "completed": True,
            "provider": "gmail",
            "sync_type": "lookback",
            "result_category": "completed",
            "processed_count_bucket": processed_count_bucket(25),
        },
        ensure_tables=True,
    )
    assert result.get("reason") == "OK", result
    assert result["emitted"] is True
    metrics = sum_daily_metrics(tenant, since_date="2020-01-01")
    assert metrics["meaningful_actions"] >= 1
    assert metrics["workflow_completed"] >= 1


def test_create_lead_emits_server_outcome(monkeypatch):
    from crm.service import EnhancedCRMService

    service = EnhancedCRMService()
    emit_mock = MagicMock(return_value={"emitted": True, "reason": "OK"})

    def fake_query(sql, params=None, fetch=True):
        sql_l = str(sql).lower()
        if "select id, withdrawn_at" in sql_l:
            return []
        if "insert into leads" in sql_l:
            return None
        if "select id from leads" in sql_l and "order by id desc" in sql_l:
            return [{"id": 555}]
        if "insert into" in sql_l:
            return None
        return []

    monkeypatch.setattr("crm.service.db_optimizer.execute_query", fake_query)
    monkeypatch.setattr("crm.service.record_crm_event", lambda **_k: None)
    monkeypatch.setattr(
        service, "_score_lead_data", lambda *_a, **_k: {"score": 10, "quality": "warm", "breakdown": {}}
    )
    monkeypatch.setattr(service, "_add_lead_activity", lambda *_a, **_k: 1)
    monkeypatch.setattr("core.product_analytics_emit.emit_server_product_event", emit_mock)

    with patch("analytics.service_usage_recorders.record_crm_lead_created", MagicMock()):
        result = service.create_lead(
            42,
            {"email": "new@example.com", "name": "New Lead", "source": "website"},
        )
    assert result["success"] is True
    assert emit_mock.call_count == 1
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["event_name"] == "outcome.lead_captured"
    assert kwargs["object_type"] == "lead"
    assert kwargs["object_id"] == "555"
    assert kwargs["properties"]["source_category"] == "website"
    assert "email" not in kwargs["properties"]
    assert "name" not in kwargs["properties"]


def test_failed_lead_emits_none(monkeypatch):
    from crm.service import EnhancedCRMService

    service = EnhancedCRMService()
    emit_mock = MagicMock()
    monkeypatch.setattr("core.product_analytics_emit.emit_server_product_event", emit_mock)
    result = service.create_lead(42, {"email": "x@example.com"})  # missing name
    assert result["success"] is False
    assert emit_mock.call_count == 0


def test_storage_failure_does_not_break_lead(monkeypatch):
    from crm.service import EnhancedCRMService

    service = EnhancedCRMService()

    def fake_query(sql, params=None, fetch=True):
        sql_l = str(sql).lower()
        if "select id, withdrawn_at" in sql_l:
            return []
        if "insert into leads" in sql_l:
            return None
        if "select id from leads" in sql_l:
            return [{"id": 777}]
        return []

    monkeypatch.setattr("crm.service.db_optimizer.execute_query", fake_query)
    monkeypatch.setattr("crm.service.record_crm_event", lambda **_k: None)
    monkeypatch.setattr(
        service, "_score_lead_data", lambda *_a, **_k: {"score": 1, "quality": "cold", "breakdown": {}}
    )
    monkeypatch.setattr(service, "_add_lead_activity", lambda *_a, **_k: 1)
    monkeypatch.setattr(
        "core.product_analytics_emit.emit_server_product_event",
        MagicMock(side_effect=RuntimeError("analytics down")),
    )
    with patch("analytics.service_usage_recorders.record_crm_lead_created", MagicMock()):
        result = service.create_lead(
            42, {"email": "ok@example.com", "name": "Ok", "source": "manual"}
        )
    assert result["success"] is True


def test_gmail_sync_completion_emits_once_pattern():
    """Mirror post-commit emit contract used by gmail_sync_jobs (dedupe by job id)."""
    job_id = _uid("gmail_sync")
    props = {
        "feature_key": "integrations",
        "workflow_key": "email_sync",
        "outcome": "sync_completed",
        "completed": True,
        "provider": "gmail",
        "sync_type": "retry",
        "result_category": "completed",
        "processed_count_bucket": "1_to_10",
    }
    first = emit_server_product_event(
        tenant_id=9001,
        actor_user_id=9001,
        event_name="outcome.sync_completed",
        object_type="gmail_sync_job",
        object_id=job_id,
        properties=props,
        ensure_tables=True,
    )
    second = emit_server_product_event(
        tenant_id=9001,
        actor_user_id=9001,
        event_name="outcome.sync_completed",
        object_type="gmail_sync_job",
        object_id=job_id,
        properties=props,
        ensure_tables=True,
    )
    assert first["emitted"] is True, first
    assert second["duplicate"] is True
    assert count_outcome_events(9001, event_name="outcome.sync_completed") >= 1


def test_map_helpers():
    assert map_lead_source_category("website") == "website"
    assert processed_count_bucket(0) == "0"
    assert processed_count_bucket(25) == "11_to_50"


def test_map_gmail_sync_type_controlled():
    assert map_gmail_sync_type({"admin_retry_of": "old", "sync_type": "incremental"}) == "retry"
    assert map_gmail_sync_type({"sync_type": "incremental", "lookback_days": 7}) == "incremental"
    assert map_gmail_sync_type({"lookback_preset": "7d", "lookback_days": 7}) == "lookback"
    assert map_gmail_sync_type({"lookback_days": 30}) == "lookback"


def test_concurrent_duplicate_emission_counts_once():
    from concurrent.futures import ThreadPoolExecutor

    lead_id = _uid("lead")
    props = {
        "feature_key": "crm",
        "workflow_key": "lead_capture",
        "outcome": "lead_captured",
        "completed": True,
        "source_category": "manual",
        "creation_channel": "crm_ui",
    }

    def _once():
        return emit_server_product_event(
            tenant_id=7100,
            actor_user_id=7100,
            event_name="outcome.lead_captured",
            object_type="lead",
            object_id=lead_id,
            properties=props,
            ensure_tables=True,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _once(), range(8)))
    assert sum(1 for r in results if r.get("emitted")) == 1
    assert sum(1 for r in results if r.get("duplicate")) >= 1


def test_gmail_source_emits_only_after_completed_update():
    """Static contract: analytics block sits after status='completed' UPDATE."""
    from pathlib import Path

    src = Path("email_automation/gmail_sync_jobs.py").read_text()
    upd = src.find("SET status = 'completed'")
    emit = src.find('event_name="outcome.sync_completed"')
    assert upd != -1 and emit != -1 and upd < emit
    assert "core/admin_sync_ops" not in src
    assert src.count('event_name="outcome.sync_completed"') == 1
