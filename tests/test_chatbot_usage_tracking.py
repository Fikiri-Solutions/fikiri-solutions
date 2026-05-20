#!/usr/bin/env python3
"""Unit tests for core.chatbot_usage_tracking."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_usage_tracking import (
    check_chatbot_usage_allowed,
    record_chatbot_ai_usage_if_needed,
    record_chatbot_billing_usage,
    record_chatbot_request_usage,
    should_record_chatbot_ai_usage,
)


class TestCheckChatbotUsageAllowed(unittest.TestCase):
    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.check_plan_access")
    def test_plan_block_returns_402(self, mock_plan, mock_log_info):
        mock_plan.return_value = {"plan": "free", "allow_llm": False}

        result = check_chatbot_usage_allowed(
            user_id=5,
            billing_uid=5,
            fallback_needed=False,
            tenant_id="tenant-5",
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.http_status, 402)
        self.assertEqual(result.error_code, "PLAN_LIMIT_EXCEEDED")
        blocked_calls = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.usage.blocked"
        ]
        self.assertEqual(len(blocked_calls), 1)
        self.assertEqual(blocked_calls[0][1]["extra"]["blocked_reason"], "plan_not_allowed")
        self.assertEqual(blocked_calls[0][1]["extra"]["tenant_id"], "tenant-5")

    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.evaluate")
    @patch("core.chatbot_usage_tracking.check_tier_usage_cap")
    @patch("core.chatbot_usage_tracking.check_plan_access")
    def test_tier_cap_block(self, mock_plan, mock_tier, mock_budget, mock_log_info):
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}
        mock_tier.return_value = (False, "Plan limit exceeded for ai_responses.", "PLAN_LIMIT_EXCEEDED")

        result = check_chatbot_usage_allowed(
            user_id=5,
            billing_uid=5,
            fallback_needed=False,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, "PLAN_LIMIT_EXCEEDED")
        mock_budget.evaluate.assert_not_called()
        blocked_calls = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.usage.blocked"
        ]
        self.assertEqual(len(blocked_calls), 1)
        self.assertEqual(blocked_calls[0][1]["extra"]["blocked_reason"], "tier_cap_exceeded")

    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.evaluate")
    @patch("core.chatbot_usage_tracking.check_plan_access")
    def test_budget_block(self, mock_plan, mock_budget):
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}
        mock_budget.return_value = Mock(
            allowed=False,
            reason="monthly_budget_cap_reached",
            tier="enterprise",
            month="2099-01",
            budget_cap_usd=100.0,
            estimated_cost_usd=95.0,
            projected_cost_usd=95.5,
            requires_approval=True,
        )

        result = check_chatbot_usage_allowed(
            user_id=5,
            billing_uid=5,
            fallback_needed=False,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, "AI_BUDGET_SOFT_STOP")

    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.evaluate")
    @patch("core.chatbot_usage_tracking.check_tier_usage_cap")
    @patch("core.chatbot_usage_tracking.check_plan_access")
    def test_fallback_needed_skips_tier_and_budget_checks(
        self, mock_plan, mock_tier, mock_budget
    ):
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}

        result = check_chatbot_usage_allowed(
            user_id=5,
            billing_uid=5,
            fallback_needed=True,
        )

        self.assertTrue(result.allowed)
        mock_tier.assert_not_called()
        mock_budget.evaluate.assert_not_called()


class TestRecordChatbotUsage(unittest.TestCase):
    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.api_key_manager.record_usage")
    def test_record_chatbot_request_usage(self, mock_record, mock_log_info):
        record_chatbot_request_usage(
            api_key_id=9,
            endpoint="public_chatbot.public_chatbot_query",
            ip_address="127.0.0.1",
            user_agent="pytest",
            response_status=200,
            response_time_ms=42,
            user_id=5,
            tenant_id="tenant-9",
        )

        mock_record.assert_called_once_with(
            api_key_id=9,
            endpoint="public_chatbot.public_chatbot_query",
            ip_address="127.0.0.1",
            user_agent="pytest",
            response_status=200,
            response_time_ms=42,
        )
        request_logs = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.usage.request_recorded"
        ]
        self.assertEqual(len(request_logs), 1)
        extra = request_logs[0][1]["extra"]
        self.assertEqual(extra["api_key_id"], 9)
        self.assertEqual(extra["tenant_id"], "tenant-9")

    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.db_optimizer.execute_query")
    @patch("core.chatbot_usage_tracking.db_optimizer.table_exists", return_value=True)
    def test_record_chatbot_billing_usage_logs_event(self, _mock_exists, mock_execute, mock_log_info):
        with patch.dict(os.environ, {"FLASK_ENV": "production", "PYTEST_CURRENT_TEST": ""}, clear=False):
            recorded = record_chatbot_billing_usage(
                5,
                "chatbot_queries",
                1,
                tenant_id="tenant-5",
            )

        self.assertTrue(recorded)
        mock_execute.assert_called_once()
        billing_logs = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.usage.billing_recorded"
        ]
        self.assertEqual(len(billing_logs), 1)
        self.assertTrue(billing_logs[0][1]["extra"]["billing_recorded"])

    @patch("core.chatbot_usage_tracking.db_optimizer.execute_query")
    @patch("core.chatbot_usage_tracking.db_optimizer.table_exists", return_value=True)
    def test_record_chatbot_billing_usage_skipped_in_test_env(self, _mock_exists, mock_execute):
        recorded = record_chatbot_billing_usage(5, "chatbot_queries", 1)
        self.assertFalse(recorded)
        mock_execute.assert_not_called()

    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.record_ai_usage")
    def test_record_chatbot_ai_usage_when_validated(self, mock_record_ai, mock_log_info):
        recorded = record_chatbot_ai_usage_if_needed(
            billing_uid=5,
            llm_attempted=True,
            llm_result_meta={"llm_success": True, "llm_validated": True},
            tenant_id="tenant-5",
        )

        self.assertTrue(recorded)
        mock_record_ai.assert_called_once_with(5, 1)
        ai_logs = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.usage.ai_recorded"
        ]
        self.assertEqual(len(ai_logs), 1)
        extra = ai_logs[0][1]["extra"]
        self.assertTrue(extra["ai_usage_recorded"])
        self.assertTrue(extra["llm_validated"])

    @patch("core.chatbot_usage_tracking.logger.info")
    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.record_ai_usage")
    def test_logs_do_not_include_sensitive_values(self, mock_record_ai, mock_log_info):
        record_chatbot_request_usage(
            api_key_id=9,
            endpoint="public_chatbot.public_chatbot_query",
            ip_address="127.0.0.1",
            user_agent="pytest-agent",
            response_status=200,
            response_time_ms=42,
            user_id=5,
            tenant_id="tenant-9",
        )
        record_chatbot_ai_usage_if_needed(
            billing_uid=5,
            llm_attempted=True,
            llm_result_meta={"llm_success": True, "llm_validated": True},
            tenant_id="tenant-9",
        )

        log_blob = str(mock_log_info.call_args_list)
        self.assertNotIn("secret@example.com", log_blob)
        self.assertNotIn("555-123-4567", log_blob)
        self.assertNotIn("SECRET_QUERY", log_blob)
        self.assertNotIn("fik_", log_blob)
        mock_record_ai.assert_called_once()

    @patch("core.chatbot_usage_tracking.ai_budget_guardrails.record_ai_usage")
    def test_no_ai_usage_when_llm_not_validated(self, mock_record_ai):
        recorded = record_chatbot_ai_usage_if_needed(
            billing_uid=5,
            llm_attempted=True,
            llm_result_meta={"llm_success": True, "llm_validated": False},
        )

        self.assertFalse(recorded)
        mock_record_ai.assert_not_called()

    def test_should_record_chatbot_ai_usage_helper(self):
        self.assertTrue(
            should_record_chatbot_ai_usage(
                billing_uid=1,
                llm_attempted=True,
                llm_result_meta={"llm_success": True, "llm_validated": True},
            )
        )
        self.assertFalse(
            should_record_chatbot_ai_usage(
                billing_uid=1,
                llm_attempted=False,
                llm_result_meta={"llm_success": True, "llm_validated": True},
            )
        )


if __name__ == "__main__":
    unittest.main()
