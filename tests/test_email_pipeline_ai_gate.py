"""Unit tests for optional mailbox AI cost gate (``core/email_pipeline_ai_gate.py``)."""

import os
import unittest
from unittest.mock import patch

from core.ai_budget_guardrails import AIBudgetDecision
from core.email_pipeline_ai_gate import (
    EmailPipelineAIGateDecision,
    email_pipeline_ai_gate_enabled,
    evaluate_email_pipeline_ai_gate,
    record_email_pipeline_ai_usage,
)


class TestEmailPipelineAIGate(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("FIKIRI_EMAIL_PIPELINE_AI_GATE", None)

    def test_flag_off_by_default(self):
        os.environ.pop("FIKIRI_EMAIL_PIPELINE_AI_GATE", None)
        self.assertFalse(email_pipeline_ai_gate_enabled())
        d = evaluate_email_pipeline_ai_gate(1)
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason, "flag_off")

    def test_flag_on_truthy(self):
        for v in ("1", "true", "yes", "on", "TRUE"):
            with self.subTest(v=v):
                os.environ["FIKIRI_EMAIL_PIPELINE_AI_GATE"] = v
                self.assertTrue(email_pipeline_ai_gate_enabled())

    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_tier_block(self, mock_tier):
        mock_tier.return_value = (False, "cap", "PLAN_LIMIT_EXCEEDED")
        d = evaluate_email_pipeline_ai_gate(42)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "PLAN_LIMIT_EXCEEDED")

    @patch("core.ai_budget_guardrails.ai_budget_guardrails")
    @patch("core.tier_usage_caps.check_tier_usage_cap")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_budget_block(self, mock_tier, mock_abg):
        mock_tier.return_value = (True, "", "")
        mock_abg.evaluate.return_value = AIBudgetDecision(
            allowed=False,
            reason="monthly_budget_cap_reached",
            tier="free",
            month="2026-01",
            estimated_cost_usd=1.0,
            projected_cost_usd=2.0,
            budget_cap_usd=2.0,
            threshold_ratio=1.0,
        )
        d = evaluate_email_pipeline_ai_gate(7)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "AI_BUDGET_SOFT_STOP")

    @patch("core.ai_budget_guardrails.ai_budget_guardrails")
    def test_record_skipped_when_flag_off(self, mock_abg):
        os.environ.pop("FIKIRI_EMAIL_PIPELINE_AI_GATE", None)
        record_email_pipeline_ai_usage(1)
        mock_abg.record_ai_usage.assert_not_called()

    @patch("core.ai_budget_guardrails.ai_budget_guardrails")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_record_when_flag_on(self, mock_abg):
        record_email_pipeline_ai_usage(99)
        mock_abg.record_ai_usage.assert_called_once_with(99, 1)

    @patch("core.ai_budget_guardrails.ai_budget_guardrails")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_record_forwards_quantity(self, mock_abg):
        record_email_pipeline_ai_usage(2, 2)
        mock_abg.record_ai_usage.assert_called_once_with(2, 2)


class TestPipelineOrchestrateAIGate(unittest.TestCase):
    def setUp(self):
        self._wf_patch = patch(
            "email_automation.pipeline.run_inbound_email_workflow",
            return_value={
                "success": True,
                "correlation_id": "wf-stub",
                "lead_capture": {"success": False},
                "automation": {},
            },
        )
        self._wf_patch.start()

    def tearDown(self):
        self._wf_patch.stop()
        os.environ.pop("FIKIRI_EMAIL_PIPELINE_AI_GATE", None)

    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    def test_gate_blocks_before_analyze(self, mock_gate):
        mock_gate.return_value = EmailPipelineAIGateDecision(False, "PLAN_LIMIT_EXCEEDED")

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = {
            "message_id": "mid",
            "thread_id": "tid",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "body",
        }
        actions = MinimalEmailActions(
            services={"ai_assistant": MinimalAIEmailAssistant()}
        )

        with patch.object(
            actions.services["ai_assistant"],
            "analyze_incoming_email",
        ) as mock_analyze:
            out = orchestrate_incoming(
                parsed, user_id=5, actions=actions, correlation_id="corr-gate"
            )

        mock_analyze.assert_not_called()
        self.assertTrue(out.get("success"))
        self.assertTrue(out.get("mailbox_ai_skipped"))
        self.assertEqual(out.get("mailbox_ai_skip_reason"), "PLAN_LIMIT_EXCEEDED")

    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.automation_safety_manager")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline.record_email_pipeline_ai_usage")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_pipeline_records_usage_after_analyze_when_gate_on(
        self, mock_record_usage, mock_eval, _mock_ev, mock_safety, mock_db
    ):
        mock_eval.return_value = EmailPipelineAIGateDecision(True, "")
        mock_safety.check_rate_limits.return_value = {"allowed": False}
        mock_db.execute_query.return_value = []

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = {
            "message_id": "mid",
            "thread_id": "tid",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "body",
        }
        actions = MinimalEmailActions(
            services={"ai_assistant": MinimalAIEmailAssistant()}
        )

        with patch.object(
            actions.services["ai_assistant"],
            "_load_business_context",
            return_value={"company_name": "Fikiri"},
        ), patch.object(
            actions.services["ai_assistant"],
            "analyze_incoming_email",
            return_value={
                "intent": "lead_inquiry",
                "confidence": 0.9,
                "urgency": "high",
                "business_value": "high",
                "recommended_action": "send_quote",
                "tone": "professional",
                "crm_updates": {
                    "stage": "qualified",
                    "tags": ["lead"],
                    "follow_up_needed": True,
                    "priority": "high",
                },
                "suggested_reply": "Draft reply",
                "should_auto_send": False,
                "needs_human_review": True,
                "reason_for_recommendation": "Manual review required.",
                "summary": "summary",
            },
        ):
            orchestrate_incoming(parsed, user_id=5, actions=actions, correlation_id="corr-rec")

        mock_record_usage.assert_called_once_with(5)

    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.automation_safety_manager")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline.record_email_pipeline_ai_usage")
    @patch.dict(os.environ, {"FIKIRI_EMAIL_PIPELINE_AI_GATE": "1"})
    def test_gate_blocks_before_reply_process_email(
        self, mock_record_usage, mock_eval, _mock_ev, mock_safety, mock_db
    ):
        mock_eval.side_effect = [
            EmailPipelineAIGateDecision(True, ""),
            EmailPipelineAIGateDecision(False, "PLAN_LIMIT_EXCEEDED"),
        ]
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_db.execute_query.return_value = []

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        analysis = {
            "intent": "lead_inquiry",
            "confidence": 0.9,
            "urgency": "low",
            "business_value": "high",
            "recommended_action": "send_quote",
            "tone": "professional",
            "crm_updates": {
                "stage": "qualified",
                "tags": ["lead"],
                "follow_up_needed": True,
                "priority": "high",
            },
            "suggested_reply": "Hi",
            "should_auto_send": True,
            "needs_human_review": False,
            "reason_for_recommendation": "Safe lead.",
            "summary": "summary",
        }
        parsed = {
            "message_id": "mid",
            "thread_id": "tid",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "body",
        }
        actions = MinimalEmailActions(
            services={"ai_assistant": MinimalAIEmailAssistant()}
        )
        with patch.object(
            actions.services["ai_assistant"],
            "_load_business_context",
            return_value={"company_name": "Fikiri"},
        ), patch.object(
            actions.services["ai_assistant"],
            "analyze_incoming_email",
            return_value=analysis,
        ), patch.object(actions, "process_email") as mock_pe:
            out = orchestrate_incoming(
                parsed, user_id=5, actions=actions, correlation_id="corr-g2"
            )

        mock_pe.assert_not_called()
        self.assertTrue(out.get("success"))
        self.assertEqual(out.get("mailbox_ai_reply_skip_reason"), "PLAN_LIMIT_EXCEEDED")
        mock_record_usage.assert_called_once_with(5)
