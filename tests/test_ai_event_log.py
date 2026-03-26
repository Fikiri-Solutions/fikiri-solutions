"""Unit tests for core/ai/ai_event_log.py."""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.ai_event_log import (
    coerce_user_id,
    ensure_correlation_in_context,
    record_ai_event,
    sha256_hex,
    text_summary,
    build_router_envelope_base,
)


class TestHelpers:
    def test_coerce_user_id(self):
        assert coerce_user_id(42) == 42
        assert coerce_user_id("7") == 7
        assert coerce_user_id("x") is None
        assert coerce_user_id(None) is None

    def test_text_summary(self):
        assert text_summary("hi", 10) == "hi"
        long = "a" * 50
        out = text_summary(long, 10)
        assert len(out) == 11 and out.endswith("…")

    def test_sha256_hex_stable(self):
        assert len(sha256_hex("abc")) == 64

    def test_ensure_correlation_in_context_mutates(self):
        ctx: dict = {}
        ensure_correlation_in_context(ctx)
        assert "correlation_id" in ctx and len(ctx["correlation_id"]) > 20

    def test_ensure_correlation_preserves_existing(self):
        ctx = {"correlation_id": "fixed"}
        ensure_correlation_in_context(ctx)
        assert ctx["correlation_id"] == "fixed"

    def test_ensure_correlation_replaces_whitespace_only(self):
        ctx = {"correlation_id": "   \t"}
        ensure_correlation_in_context(ctx)
        assert ctx["correlation_id"] != "   \t"
        assert len(ctx["correlation_id"]) > 20

    def test_ensure_correlation_strips_and_keeps_value(self):
        ctx = {"correlation_id": "  abc-123  "}
        ensure_correlation_in_context(ctx)
        assert ctx["correlation_id"] == "abc-123"

    def test_build_router_envelope_base(self):
        env = build_router_envelope_base(
            correlation_id="c1",
            router_trace_id="t1",
            intent="general",
            source="test",
            context={"operation": "unit", "tenant_id": 5},
            preprocessed_prompt="hello",
            model="gpt-3.5-turbo",
            max_tokens=100,
            temperature=0.5,
        )
        assert env["envelope_version"] == 1
        assert env["correlation_id"] == "c1"
        assert env["request"]["intent"] == "general"
        assert env["channel"]["operation"] == "unit"


class TestRecordAiEvent:
    @patch("core.ai.ai_event_log.ai_event_logging_enabled", return_value=False)
    def test_record_skips_when_disabled(self, _mock):
        assert record_ai_event("ai.requested", payload={"x": 1}) is None

    @patch("core.ai.ai_event_log.ai_event_logging_enabled", return_value=True)
    @patch("core.ai.ai_event_log.db_optimizer.execute_insert_returning_id")
    def test_record_calls_insert_when_enabled(self, mock_ins, _mock_en):
        mock_ins.return_value = 99
        rid = record_ai_event(
            "ai.requested",
            user_id=1,
            correlation_id="cid",
            source="test",
            payload={"k": "v"},
        )
        assert rid == 99
        mock_ins.assert_called_once()

    @patch("core.ai.ai_event_log.ai_event_logging_enabled", return_value=True)
    @patch(
        "core.ai.ai_event_log.db_optimizer.execute_insert_returning_id",
        side_effect=RuntimeError("db"),
    )
    def test_record_swallows_db_errors(self, _mock_ins, _mock_en):
        assert record_ai_event("ai.requested", payload={}) is None
