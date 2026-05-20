#!/usr/bin/env python3
"""Mailbox sync passes v2 analysis into auto-reply generation."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from email_automation import pipeline
from email_automation.actions import MinimalEmailActions


def _parsed_message():
    return {
        "message_id": "msg-1",
        "thread_id": "th-1",
        "headers": {"from": "Buyer <buyer@example.com>", "subject": "Partnership inquiry"},
        "body": {"text": "We want to explore a partnership.", "html": ""},
        "snippet": "We want to explore a partnership.",
        "labels": [],
    }


def _analysis_v2(**overrides):
    base = {
        "schema_version": "2026-05-email-analysis-v2",
        "intent": "partnership_request",
        "legacy_intent": "lead_inquiry",
        "confidence_score": 0.91,
        "confidence": 0.91,
        "urgency": "medium",
        "business_value": "high",
        "lead_score": 72,
        "urgency_score": 55,
        "business_value_score": 70,
        "suggested_reply": "Thank you for reaching out about a partnership. We would be glad to discuss.",
        "should_auto_send": True,
        "needs_human_review": False,
        "recommended_action": "draft_reply",
        "tone": "professional_warm",
        "crm_updates": {
            "stage": "contacted",
            "tags": ["partnership_request"],
            "follow_up_needed": True,
            "priority": "medium",
        },
        "reply_guidance": {"tone": "professional_warm"},
        "extracted_details": {"requested_service": "partnership"},
        "recommended_action_detail": {"next_best_action": "schedule_call", "workflow": "partnership_review"},
        "classification_source": "mailbox_sync",
    }
    base.update(overrides)
    return base


class TestMailboxReplyUsesAnalysis(unittest.TestCase):
    def test_auto_reply_action_details_include_policy_fields(self):
        parsed = _parsed_message()
        parsed["_analysis"] = _analysis_v2()
        parsed["_mailbox_user_id"] = 7

        assistant = MagicMock()
        assistant.generate_reply_with_metadata.return_value = (
            parsed["_analysis"]["suggested_reply"],
            "reused_suggested_reply",
        )

        actions = MinimalEmailActions(services={"ai_assistant": assistant})
        actions.gmail_service = None
        result = actions._auto_reply(parsed, user_id=7)

        details = result["details"]
        self.assertEqual(details["reply_generation_mode"], "reused_suggested_reply")
        self.assertTrue(details["analysis_reused"])
        self.assertEqual(details["intent"], "partnership_request")
        self.assertEqual(details["urgency"], "medium")
        self.assertEqual(details["lead_score"], 72)
        self.assertEqual(details["tone"], "professional_warm")

    def test_process_email_receives_analysis_on_parsed(self):
        parsed = _parsed_message()
        analysis = _analysis_v2()
        parsed["_analysis"] = analysis

        captured = {}

        def _capture_auto_reply(pe, user_id=None):
            captured["analysis"] = pe.get("_analysis")
            return {"success": True, "action": "auto_reply", "details": {"reply_generation_mode": "reused_suggested_reply"}}

        actions = MinimalEmailActions()
        actions._auto_reply = _capture_auto_reply
        actions.process_email(parsed, action_type="auto_reply", user_id=7)
        self.assertEqual(captured["analysis"]["intent"], "partnership_request")

    @patch("email_automation.pipeline.record_email_pipeline_ai_usage")
    @patch("email_automation.pipeline.email_pipeline_ai_gate_enabled", return_value=True)
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    @patch("services.email_triage_service.triage_and_store_synced_message")
    @patch("email_automation.pipeline.evaluate_email_action_policy")
    def test_orchestrate_skips_second_ai_usage_when_reusing_suggested_reply(
        self,
        mock_policy,
        _mock_triage,
        _mock_should_ai,
        mock_eval_gate,
        _gate_on,
        mock_record_usage,
    ):
        from core.email_pipeline_ai_gate import EmailPipelineAIGateDecision

        mock_eval_gate.return_value = EmailPipelineAIGateDecision(True, None)
        mock_policy.return_value = {
            "recommended_action_type": "auto_reply",
            "should_auto_send": True,
            "requires_human_review": False,
            "execution_mode": "auto_send",
            "reason": "test",
        }
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = _parsed_message()
        assistant = MagicMock(spec=MinimalAIEmailAssistant)
        assistant.is_enabled.return_value = True
        assistant._load_business_context.return_value = {"company_name": "Acme"}
        assistant.analyze_incoming_email.return_value = _analysis_v2()
        assistant.generate_reply_with_metadata.return_value = (
            "Thank you for reaching out about a partnership. We would be glad to discuss.",
            "reused_suggested_reply",
        )

        actions = MinimalEmailActions(services={"ai_assistant": assistant, "gmail": None})
        actions.gmail_service = None
        actions.db_optimizer = MagicMock()

        wf = {
            "success": True,
            "correlation_id": "c1",
            "lead_capture": {"success": True, "data": {"lead_id": 1}},
            "automation": {"success": True},
        }

        with patch("email_automation.pipeline.run_inbound_email_workflow", return_value=wf), \
             patch("email_automation.pipeline.automation_safety_manager") as mock_safety, \
             patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls, \
             patch("email_automation.pipeline.db_optimizer") as mock_db, \
             patch("email_automation.pipeline.enhanced_crm_service"), \
             patch("email_automation.actions.idempotency_manager") as mock_idem:
            mock_idem.check_key.return_value = None
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            mock_parser = MagicMock()
            mock_parser.get_subject.return_value = parsed["headers"]["subject"]
            mock_parser.get_body_text.return_value = parsed["body"]["text"]
            mock_parser.get_sender.return_value = parsed["headers"]["from"]
            mock_parser_cls.return_value = mock_parser
            mock_db.execute_query.return_value = [{"id": 1}]

            result = pipeline.orchestrate_incoming(
                parsed, user_id=1, actions=actions, run_mailbox_ai=True
            )

        self.assertTrue(result.get("success"))
        assistant.classify_email_intent.assert_not_called()
        assistant.generate_reply_with_metadata.assert_called_once()
        call_kwargs = assistant.generate_reply_with_metadata.call_args.kwargs
        self.assertEqual(call_kwargs["analysis"]["intent"], "partnership_request")
        self.assertEqual(
            result["action"]["details"]["reply_generation_mode"],
            "reused_suggested_reply",
        )
        # analyze recorded once at start; no second increment for reused reply
        self.assertEqual(len(mock_record_usage.call_args_list), 1)

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_suggested_reply_skips_llm_router(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = True
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)
        analysis = _analysis_v2()
        text, mode = assistant.generate_reply_with_metadata(
            sender_name="Buyer",
            subject="Partnership",
            email_body="We want a partnership.",
            analysis=analysis,
        )
        self.assertEqual(mode, "reused_suggested_reply")
        self.assertEqual(text, analysis["suggested_reply"])
        mock_router.process.assert_not_called()

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_missing_analysis_still_generates_via_llm(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = True
        mock_router.process.return_value = {"success": True, "content": "LLM draft reply"}
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)
        text, mode = assistant.generate_reply_with_metadata(
            sender_name="Pat",
            subject="Hello",
            email_body="General question",
            analysis=None,
        )
        self.assertEqual(mode, "llm_no_analysis")
        self.assertEqual(text, "LLM draft reply")
        mock_router.process.assert_called_once()


if __name__ == "__main__":
    unittest.main()
