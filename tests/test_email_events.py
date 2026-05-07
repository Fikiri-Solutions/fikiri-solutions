"""Tests for append-only email_events and record_email_event."""

import unittest
from unittest.mock import patch

from email_automation.email_event_log import record_email_event


class TestRecordEmailEvent(unittest.TestCase):
    @patch("email_automation.email_event_log.db_optimizer")
    def test_record_calls_insert(self, mock_db):
        record_email_event(
            1,
            "email.parsed",
            provider="gmail",
            message_id="m1",
            correlation_id="c1",
            payload={"a": 1},
            status="applied",
            source="test",
        )
        mock_db.execute_query.assert_called_once()
        args = mock_db.execute_query.call_args
        self.assertIn("INSERT INTO email_events", args[0][0])
        params = args[0][1]
        self.assertEqual(params[1], 1)
        self.assertEqual(params[2], "email.parsed")
        self.assertEqual(params[3], "gmail")
        self.assertEqual(params[4], "m1")

    @patch("email_automation.email_event_log.db_optimizer")
    def test_record_swallows_db_error(self, mock_db):
        mock_db.execute_query.side_effect = RuntimeError("db down")
        record_email_event(1, "email.failed", status="failed", source="test")


_STUB_INBOUND_WORKFLOW_RETURN = {
    "success": True,
    "correlation_id": "wf-stub",
    "lead_capture": {"success": True, "data": {"lead_id": 777}},
    "automation": {"success": True},
}


class TestPipelineEmailEvents(unittest.TestCase):
    def setUp(self):
        self._wf_patch = patch(
            "email_automation.pipeline.run_inbound_email_workflow",
            return_value=dict(_STUB_INBOUND_WORKFLOW_RETURN),
        )
        self._wf_patch.start()

    def tearDown(self):
        self._wf_patch.stop()

    @patch("email_automation.pipeline.enhanced_crm_service")
    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.automation_safety_manager")
    def test_orchestrate_emits_core_events(
        self, mock_safety, mock_record, mock_db, _crm
    ):
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
                "crm_updates": {"stage": "qualified", "tags": ["lead"], "follow_up_needed": True, "priority": "high"},
                "suggested_reply": "Draft reply",
                "should_auto_send": False,
                "needs_human_review": True,
                "reason_for_recommendation": "Manual review required.",
                "summary": "summary",
            },
        ):
            out = orchestrate_incoming(
                parsed, user_id=5, actions=actions, correlation_id="corr-test"
            )

        self.assertTrue(out.get("success"))
        types = [c[0][1] for c in mock_record.call_args_list]
        self.assertIn("email.parsed", types)
        self.assertIn("email.analyzed", types)
        self.assertIn("email.classified", types)
        self.assertIn("ai.action_recommended", types)
        self.assertIn("ai.action.recommended", types)
        self.assertIn("ai.policy.evaluated", types)
        self.assertIn("email.reply_drafted", types)
        self.assertNotIn("ai.action_cancelled", types)

    @patch("email_automation.pipeline.enhanced_crm_service")
    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.automation_safety_manager")
    def test_orchestrate_classification_failure_emits_failed(
        self, mock_safety, mock_record, mock_db, _crm
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
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
            side_effect=RuntimeError("llm down"),
        ):
            out = orchestrate_incoming(parsed, user_id=5, actions=actions)

        self.assertFalse(out.get("success"))
        self.assertEqual(out.get("error"), "analysis_failed")
        types = [c[0][1] for c in mock_record.call_args_list]
        self.assertIn("email.parsed", types)
        self.assertIn("email.failed", types)
        self.assertNotIn("email.classified", types)

    @patch("email_automation.pipeline.enhanced_crm_service")
    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.automation_safety_manager")
    def test_orchestrate_non_dict_classification_no_crash(
        self, mock_safety, mock_record, mock_db, _crm
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_db.execute_query.return_value = []

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = {
            "message_id": "mid",
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
            return_value={"not": "a dict payload"},
        ), patch.object(actions, "process_email", return_value={"success": True, "action": "mark_read"}):
            out = orchestrate_incoming(parsed, user_id=5, actions=actions)

        self.assertTrue(out.get("success"))
        types = [c[0][1] for c in mock_record.call_args_list]
        self.assertIn("email.classified", types)
        self.assertIn("ai.action_recommended", types)

    @patch("email_automation.pipeline.enhanced_crm_service")
    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.automation_safety_manager")
    def test_orchestrate_process_email_exception_emits_failed(
        self, mock_safety, mock_record, mock_db, _crm
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_db.execute_query.return_value = []

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = {
            "message_id": "mid",
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
                "crm_updates": {"stage": "qualified", "tags": ["lead"], "follow_up_needed": True, "priority": "high"},
                "suggested_reply": "Draft reply",
                "should_auto_send": True,
                "needs_human_review": False,
                "reason_for_recommendation": "Safe to auto send.",
                "summary": "summary",
            },
        ), patch.object(
            actions, "process_email", side_effect=RuntimeError("handler boom")
        ):
            out = orchestrate_incoming(parsed, user_id=5, actions=actions)

        self.assertFalse(out.get("success"))
        self.assertEqual(out.get("error"), "process_email_failed")
        types = [c[0][1] for c in mock_record.call_args_list]
        self.assertIn("email.failed", types)

    @patch("email_automation.pipeline.enhanced_crm_service")
    @patch("email_automation.pipeline.db_optimizer")
    @patch("email_automation.pipeline.record_email_event")
    @patch("email_automation.pipeline.automation_safety_manager")
    def test_orchestrate_non_dict_action_result_emits_failed(
        self, mock_safety, mock_record, mock_db, _crm
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_db.execute_query.return_value = []

        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions
        from email_automation.ai_assistant import MinimalAIEmailAssistant

        parsed = {
            "message_id": "mid",
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
                "crm_updates": {"stage": "qualified", "tags": ["lead"], "follow_up_needed": True, "priority": "high"},
                "suggested_reply": "Draft reply",
                "should_auto_send": True,
                "needs_human_review": False,
                "reason_for_recommendation": "Safe to auto send.",
                "summary": "summary",
            },
        ), patch.object(actions, "process_email", return_value=None):
            out = orchestrate_incoming(parsed, user_id=5, actions=actions)

        self.assertFalse(out.get("success"))
        self.assertEqual(out.get("error"), "invalid_action_result")
        types = [c[0][1] for c in mock_record.call_args_list]
        self.assertIn("email.failed", types)

    @patch("email_automation.pipeline.record_email_event")
    def test_orchestrate_invalid_parsed_no_events(self, mock_record):
        from email_automation.pipeline import orchestrate_incoming
        from email_automation.actions import MinimalEmailActions

        out = orchestrate_incoming(
            None, user_id=5, actions=MinimalEmailActions(services={})
        )
        self.assertFalse(out.get("success"))
        self.assertEqual(out.get("error"), "invalid_parsed_message")
        self.assertIn("correlation_id", out)
        mock_record.assert_not_called()

    def test_parse_message_non_dict_returns_empty_shape(self):
        from email_automation.pipeline import parse_message

        out = parse_message("not-a-dict")
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("message_id"), "")
        self.assertEqual(out.get("headers"), {})


if __name__ == "__main__":
    unittest.main()
