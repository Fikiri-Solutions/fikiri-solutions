#!/usr/bin/env python3
"""Tests for POST /api/ai-response (demo vs real LLM contract)."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from app import app  # noqa: E402


class TestAIResponseDirectRoute(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("core.ai.llm_router.LLMRouter")
    @patch("core.secure_sessions.get_current_user_id")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.evaluate")
    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.record_ai_usage")
    def test_llm_success_records_usage_and_flags_llm_used(
        self, mock_record, mock_tier, mock_eval, mock_uid, mock_llm_cls
    ):
        mock_uid.return_value = 1
        mock_tier.return_value = (True, "", "")
        mock_eval.return_value = MagicMock(allowed=True)

        mock_router = MagicMock()
        mock_client = MagicMock()
        mock_client.is_enabled.return_value = True
        mock_router.client = mock_client
        mock_router.process.return_value = {
            "success": True,
            "validated": True,
            "content": "Model says hi",
        }
        mock_llm_cls.return_value = mock_router

        resp = self.client.post("/api/ai-response", json={"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertTrue(data["llm_used"])
        self.assertIsNone(data.get("fallback_reason"))
        self.assertEqual(data["data"].get("response_source"), "llm")
        self.assertEqual(data["data"]["response"], "Model says hi")
        mock_record.assert_called_once_with(1, 1)

    @patch("core.ai.llm_router.LLMRouter")
    @patch("core.secure_sessions.get_current_user_id")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.evaluate")
    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.record_ai_usage")
    def test_llm_disabled_returns_demo_contract(
        self, mock_record, mock_tier, mock_eval, mock_uid, mock_llm_cls
    ):
        mock_uid.return_value = 1
        mock_tier.return_value = (True, "", "")
        mock_eval.return_value = MagicMock(allowed=True)

        mock_router = MagicMock()
        mock_client = MagicMock()
        mock_client.is_enabled.return_value = False
        mock_router.client = mock_client
        mock_llm_cls.return_value = mock_router

        resp = self.client.post("/api/ai-response", json={"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertFalse(data["llm_used"])
        self.assertEqual(data["fallback_reason"], "LLM_DISABLED")
        self.assertEqual(data["data"].get("response_source"), "demo_fallback")
        mock_record.assert_not_called()

    @patch("core.ai.llm_router.LLMRouter")
    @patch("core.secure_sessions.get_current_user_id")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.evaluate")
    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.record_ai_usage")
    def test_llm_schema_invalid_does_not_record_usage(
        self, mock_record, mock_tier, mock_eval, mock_uid, mock_llm_cls
    ):
        mock_uid.return_value = 1
        mock_tier.return_value = (True, "", "")
        mock_eval.return_value = MagicMock(allowed=True)

        mock_router = MagicMock()
        mock_client = MagicMock()
        mock_client.is_enabled.return_value = True
        mock_router.client = mock_client
        mock_router.process.return_value = {
            "success": True,
            "validated": False,
            "content": "{}",
        }
        mock_llm_cls.return_value = mock_router

        resp = self.client.post("/api/ai-response", json={"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["llm_used"])
        self.assertEqual(data["fallback_reason"], "LLM_UNSUCCESSFUL")
        mock_record.assert_not_called()

    @patch("core.ai.llm_router.LLMRouter")
    @patch("core.secure_sessions.get_current_user_id")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.evaluate")
    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch("core.ai_budget_guardrails.ai_budget_guardrails.record_ai_usage")
    def test_llm_exception_returns_llm_error(
        self, mock_record, mock_tier, mock_eval, mock_uid, mock_llm_cls
    ):
        mock_uid.return_value = 1
        mock_tier.return_value = (True, "", "")
        mock_eval.return_value = MagicMock(allowed=True)
        mock_llm_cls.side_effect = RuntimeError("init failed")

        resp = self.client.post("/api/ai-response", json={"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["llm_used"])
        self.assertEqual(data["fallback_reason"], "LLM_ERROR")
        mock_record.assert_not_called()


if __name__ == "__main__":
    unittest.main()
