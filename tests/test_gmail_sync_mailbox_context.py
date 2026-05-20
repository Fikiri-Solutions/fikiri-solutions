#!/usr/bin/env python3
"""Regression: Gmail sync reuses mailbox automation context once per job."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOrchestrateMailboxContextLazyInit(unittest.TestCase):
    def setUp(self):
        self.parsed = {
            "message_id": "mid-1",
            "thread_id": "tid-1",
            "headers": {"from": "lead@example.com", "subject": "Hello"},
            "snippet": "body",
        }
        self.wf_return = {
            "success": True,
            "correlation_id": "wf-corr",
            "lead_capture": {"success": True, "data": {"lead_id": 9}},
            "automation": {"success": True},
        }

    @patch("email_automation.pipeline.run_inbound_email_workflow", return_value=None)
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    def test_orchestrate_skips_actions_init_when_run_mailbox_ai_false(
        self, _mock_should_ai, mock_wf
    ):
        mock_wf.return_value = self.wf_return

        with patch("email_automation.pipeline.MinimalEmailActions") as mock_actions_cls, patch(
            "email_automation.pipeline.MinimalAIEmailAssistant"
        ) as mock_ai_cls:
            from email_automation.pipeline import orchestrate_incoming

            out = orchestrate_incoming(
                self.parsed,
                user_id=5,
                actions=None,
                run_mailbox_ai=False,
                correlation_id="corr-skip",
            )

        mock_actions_cls.assert_not_called()
        mock_ai_cls.assert_not_called()
        self.assertTrue(out.get("success"))
        self.assertTrue(out.get("mailbox_ai_skipped"))

    @patch("email_automation.pipeline.run_inbound_email_workflow")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    def test_orchestrate_skips_actions_init_when_ai_gate_blocks(
        self, mock_gate, _mock_should_ai, mock_wf
    ):
        from core.email_pipeline_ai_gate import EmailPipelineAIGateDecision

        mock_wf.return_value = self.wf_return
        mock_gate.return_value = EmailPipelineAIGateDecision(False, "PLAN_LIMIT_EXCEEDED")

        with patch("email_automation.pipeline.MinimalEmailActions") as mock_actions_cls, patch(
            "email_automation.pipeline.MinimalAIEmailAssistant"
        ) as mock_ai_cls:
            from email_automation.pipeline import orchestrate_incoming

            out = orchestrate_incoming(
                self.parsed,
                user_id=5,
                actions=None,
                correlation_id="corr-gate-skip",
            )

        mock_actions_cls.assert_not_called()
        mock_ai_cls.assert_not_called()
        self.assertTrue(out.get("mailbox_ai_skipped"))
        self.assertEqual(out.get("mailbox_ai_skip_reason"), "PLAN_LIMIT_EXCEEDED")

    @patch("email_automation.pipeline.run_inbound_email_workflow")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline._build_mailbox_actions")
    def test_orchestrate_reuses_runtime_context_stack(
        self, mock_build, mock_gate, _mock_should_ai, mock_wf
    ):
        from core.email_pipeline_ai_gate import EmailPipelineAIGateDecision
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        mock_wf.return_value = self.wf_return
        mock_gate.return_value = EmailPipelineAIGateDecision(True, None)
        mock_actions = MagicMock()
        mock_actions.services = {"ai_assistant": MagicMock()}
        mock_parser = MagicMock()
        mock_parser.get_subject.return_value = "Subj"
        mock_parser.get_body_text.return_value = "body"
        mock_parser.get_sender.return_value = "a@b.com"
        mock_build.return_value = mock_actions

        ctx = EmailAutomationRuntimeContext(
            job_id="job-ctx",
            user_id=5,
            actions=mock_actions,
            parser=mock_parser,
        )
        ctx._initialized = True

        with patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls, patch(
            "email_automation.pipeline.MinimalEmailActions"
        ) as mock_actions_cls, patch(
            "email_automation.pipeline.MinimalAIEmailAssistant"
        ) as mock_ai_cls:
            from email_automation.pipeline import orchestrate_incoming

            orchestrate_incoming(
                self.parsed,
                user_id=5,
                runtime_context=ctx,
                correlation_id="corr-ctx",
            )

        mock_parser_cls.assert_not_called()
        mock_actions_cls.assert_not_called()
        mock_ai_cls.assert_not_called()
        mock_build.assert_called_once()
        self.assertIs(mock_build.call_args[0][0], mock_actions)
        mock_wf.assert_called_once()
        self.assertIs(mock_wf.call_args.kwargs.get("runtime_context"), ctx)


class TestEmailAutomationRuntimeContext(unittest.TestCase):
    def test_initialize_logs_once(self):
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        with patch(
            "email_automation.actions.MinimalEmailActions"
        ) as mock_actions_cls, patch(
            "email_automation.ai_assistant.MinimalAIEmailAssistant"
        ) as mock_ai_cls, patch(
            "email_automation.parser.MinimalEmailParser"
        ) as mock_parser_cls:
            mock_actions_cls.return_value = MagicMock()
            mock_parser_cls.return_value = MagicMock()

            ctx = EmailAutomationRuntimeContext(job_id="j1", user_id=3)
            self.assertTrue(ctx.initialize_mailbox_stack())
            self.assertTrue(ctx.initialize_mailbox_stack())

        mock_actions_cls.assert_called_once()
        mock_ai_cls.assert_called_once()
        mock_parser_cls.assert_called_once()

    def test_different_users_get_different_contexts(self):
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        a = EmailAutomationRuntimeContext(job_id="j-a", user_id=1)
        b = EmailAutomationRuntimeContext(job_id="j-b", user_id=2)
        self.assertNotEqual(a.user_id, b.user_id)
        self.assertNotEqual(a.job_id, b.job_id)


class TestGmailSyncMailboxContextReuse(unittest.TestCase):
    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_sync_initializes_mailbox_stack_once_per_job(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        messages = [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t2"}]

        mock_ctx = MagicMock()
        mock_ctx.mailbox_stack_ready = True
        mock_ctx.actions = MagicMock()
        mock_ctx.parser = MagicMock()
        mock_ctx.parser.parse_message.return_value = {"message_id": "m1", "headers": {}}

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": messages}
        ), patch.object(manager, "_store_email", return_value=101), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime",
            return_value=mock_ctx,
        ) as mock_create, patch(
            "email_automation.pipeline.orchestrate_incoming"
        ) as mock_orch, patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            manager._sync_emails(MagicMock(), user_id=7, job_id="job-reuse-1", job_meta={})

        mock_create.assert_called_once()
        self.assertEqual(mock_orch.call_count, 2)
        for call in mock_orch.call_args_list:
            self.assertIs(call.kwargs.get("runtime_context"), mock_ctx)
        mock_ctx.log_job_summary.assert_called_once()

    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_one_message_failure_does_not_stop_next(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        messages = [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t2"}]

        mock_ctx = MagicMock()
        mock_ctx.mailbox_stack_ready = True
        mock_ctx.actions = MagicMock()
        mock_ctx.parser = MagicMock()
        mock_ctx.parser.parse_message.return_value = {"message_id": "m1", "headers": {}}

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": messages}
        ), patch.object(manager, "_store_email", return_value=101), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime",
            return_value=mock_ctx,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming",
            side_effect=[Exception("boom"), {"success": True}],
        ), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            result = manager._sync_emails(
                MagicMock(), user_id=7, job_id="job-fail-iso", job_meta={}
            )

        self.assertEqual(result.get("emails_synced"), 2)
        self.assertEqual(mock_ctx.record_message_failed.call_count, 1)
        self.assertEqual(mock_ctx.record_message_processed.call_count, 1)

    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_runtime_init_failure_falls_back_without_breaking_sync(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        messages = [{"id": "m1", "threadId": "t1"}]

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": messages}
        ), patch.object(manager, "_store_email", return_value=101), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime",
            return_value=None,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming"
        ) as mock_orch, patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            result = manager._sync_emails(
                MagicMock(), user_id=7, job_id="job-no-ctx", job_meta={}
            )

        self.assertEqual(result.get("emails_synced"), 1)
        mock_orch.assert_called_once()
        self.assertFalse(mock_orch.call_args.kwargs.get("run_mailbox_ai"))

    @patch("email_automation.pipeline.run_inbound_email_workflow")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=False)
    def test_fallback_without_runtime_context_still_works(self, _mock_ai, mock_wf):
        from email_automation.pipeline import orchestrate_incoming

        mock_wf.return_value = {"success": True, "correlation_id": "c1"}
        parsed = {
            "message_id": "x",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "text",
        }
        out = orchestrate_incoming(parsed, user_id=1, actions=None, runtime_context=None)
        self.assertTrue(out.get("success"))
        mock_wf.assert_called_once()


class TestAutomationEngineRuntimeContext(unittest.TestCase):
    def test_email_received_injects_sync_job_id_from_runtime_context(self):
        from services.automation_engine import AutomationEngine, TriggerType

        engine = AutomationEngine()
        ctx = MagicMock()
        ctx.job_id = "gmail_sync_99_1"
        ctx.user_id = 42

        rule_row = {
            "id": 1,
            "user_id": 42,
            "name": "r",
            "description": "",
            "trigger_type": "email_received",
            "trigger_conditions": "{}",
            "action_type": "send_email",
            "action_parameters": "{}",
            "status": "active",
            "created_at": "2020-01-01T00:00:00",
            "updated_at": "2020-01-01T00:00:00",
            "last_executed": None,
            "execution_count": 0,
            "success_count": 0,
            "error_count": 0,
        }
        handler_triggers = []

        def fake_send(params, trigger_data, uid):
            handler_triggers.append(dict(trigger_data))
            return {"success": True, "data": {"sent": True}}

        from services.automation_engine import ActionType

        with patch(
            "services.automation_engine.db_optimizer.execute_query",
            return_value=[rule_row],
        ), patch.dict(
            engine.action_handlers,
            {ActionType.SEND_EMAIL: fake_send},
        ), patch.object(engine, "_check_trigger_conditions", return_value=True), patch.object(
            engine, "_update_rule_stats"
        ), patch.object(engine, "_log_execution"), patch(
            "services.automation_engine.enter_automation_run_if_missing"
        ) as mock_enter:
            mock_enter.return_value.__enter__ = lambda s: False
            mock_enter.return_value.__exit__ = lambda s, *a: None
            engine.execute_automation_rules(
                TriggerType.EMAIL_RECEIVED,
                {"sender_email": "a@example.com"},
                42,
                runtime_context=ctx,
            )

        self.assertEqual(len(handler_triggers), 1)
        self.assertEqual(handler_triggers[0]["sync_job_id"], "gmail_sync_99_1")

    def test_runtime_context_user_mismatch_not_applied(self):
        from services.automation_engine import AutomationEngine, TriggerType

        engine = AutomationEngine()
        ctx = MagicMock()
        ctx.job_id = "job-x"
        ctx.user_id = 1

        rule_row = {
            "id": 2,
            "user_id": 99,
            "name": "r",
            "description": "",
            "trigger_type": "email_received",
            "trigger_conditions": "{}",
            "action_type": "send_email",
            "action_parameters": "{}",
            "status": "active",
            "created_at": "2020-01-01T00:00:00",
            "updated_at": "2020-01-01T00:00:00",
            "last_executed": None,
            "execution_count": 0,
            "success_count": 0,
            "error_count": 0,
        }
        handler_triggers = []

        def fake_send(params, trigger_data, uid):
            handler_triggers.append(dict(trigger_data))
            return {"success": True, "data": {}}

        from services.automation_engine import ActionType

        with patch(
            "services.automation_engine.db_optimizer.execute_query",
            return_value=[rule_row],
        ), patch.dict(
            engine.action_handlers,
            {ActionType.SEND_EMAIL: fake_send},
        ), patch.object(engine, "_check_trigger_conditions", return_value=True), patch.object(
            engine, "_update_rule_stats"
        ), patch.object(engine, "_log_execution"), patch(
            "services.automation_engine.enter_automation_run_if_missing"
        ) as mock_enter:
            mock_enter.return_value.__enter__ = lambda s: False
            mock_enter.return_value.__exit__ = lambda s, *a: None
            engine.execute_automation_rules(
                TriggerType.EMAIL_RECEIVED,
                {"sender_email": "a@example.com"},
                99,
                runtime_context=ctx,
            )

        self.assertEqual(len(handler_triggers), 1)
        self.assertNotIn("sync_job_id", handler_triggers[0])


class TestEmailActionHandlerNoHeavyInit(unittest.TestCase):
    def test_send_email_path_does_not_construct_mailbox_stack(self):
        import inspect
        from services.automation_actions import email_action as mod

        source = inspect.getsource(mod.EmailActionHandler.execute_send_email)
        self.assertNotIn("MinimalEmailActions", source)
        self.assertNotIn("MinimalAIEmailAssistant", source)


class TestRuntimeContextNEmailInstances(unittest.TestCase):
    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_n_messages_do_not_create_n_assistant_instances(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        n = 5
        messages = [{"id": f"m{i}", "threadId": f"t{i}"} for i in range(n)]

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": messages}
        ), patch.object(manager, "_store_email", return_value=101), patch(
            "email_automation.actions.MinimalEmailActions"
        ) as mock_actions_cls, patch(
            "email_automation.ai_assistant.MinimalAIEmailAssistant"
        ) as mock_ai_cls, patch(
            "email_automation.parser.MinimalEmailParser"
        ) as mock_parser_cls, patch(
            "email_automation.pipeline.orchestrate_incoming"
        ), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_actions_cls.return_value = MagicMock()
            mock_parser_cls.return_value = MagicMock()
            mock_db.execute_query.return_value = []
            manager._sync_emails(MagicMock(), user_id=9, job_id="job-n", job_meta={})

        mock_actions_cls.assert_called_once()
        mock_ai_cls.assert_called_once()
        mock_parser_cls.assert_called_once()

    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_same_assistant_and_actions_instances_across_messages(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        manager = GmailSyncJobManager()
        messages = [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t2"}]
        shared_actions = MagicMock()
        shared_ai = MagicMock()
        shared_actions.services = {"ai_assistant": shared_ai}
        shared_parser = MagicMock()
        shared_parser.parse_message.return_value = {
            "message_id": "m1",
            "headers": {"from": "x@y.com", "subject": "S"},
        }

        ctx = EmailAutomationRuntimeContext(
            job_id="job-same-inst",
            user_id=7,
            actions=shared_actions,
            parser=shared_parser,
        )
        ctx._initialized = True

        orch_actions_ids = []

        def capture_orch(*_a, **kw):
            act = kw.get("actions")
            if act is not None:
                orch_actions_ids.append(id(act))
            rt = kw.get("runtime_context")
            if rt is not None:
                orch_actions_ids.append(id(rt.ai_assistant))
            return {"success": True, "inbound_workflow": {}}

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": messages}
        ), patch.object(manager, "_store_email", return_value=101), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime",
            return_value=ctx,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming",
            side_effect=capture_orch,
        ), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            manager._sync_emails(MagicMock(), user_id=7, job_id="job-same-inst", job_meta={})

        self.assertEqual(len(orch_actions_ids), 4)
        self.assertEqual(len(set(orch_actions_ids)), 2)

    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "false"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_mailbox_automation_disabled_creates_no_context(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": [{"id": "m1"}]}
        ), patch.object(manager, "_store_email", return_value=1), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime"
        ) as mock_create, patch(
            "email_automation.pipeline.orchestrate_incoming"
        ), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            manager._sync_emails(MagicMock(), user_id=1, job_id="job-off", job_meta={})

        mock_create.assert_not_called()

    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "true"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_durable_retry_gets_fresh_context_per_job(self, mock_db):
        from email_automation.gmail_sync_jobs import GmailSyncJobManager

        manager = GmailSyncJobManager()
        created_job_ids = []

        def make_ctx(job_id, user_id, **kwargs):
            ctx = MagicMock()
            ctx.job_id = job_id
            ctx.user_id = user_id
            ctx.mailbox_stack_ready = True
            ctx.actions = MagicMock()
            ctx.parser = MagicMock()
            ctx.parser.parse_message.return_value = {"message_id": "m", "headers": {}}
            created_job_ids.append(job_id)
            return ctx

        with patch.object(
            manager, "_get_gmail_messages", return_value={"messages": [{"id": "m1"}]}
        ), patch.object(manager, "_store_email", return_value=1), patch(
            "email_automation.runtime_context.try_create_gmail_sync_runtime",
            side_effect=make_ctx,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming"
        ), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ):
            mock_db.execute_query.return_value = []
            manager._sync_emails(MagicMock(), user_id=5, job_id="job-retry-a", job_meta={})
            manager._sync_emails(MagicMock(), user_id=5, job_id="job-retry-b", job_meta={})

        self.assertEqual(created_job_ids, ["job-retry-a", "job-retry-b"])
        self.assertNotEqual(created_job_ids[0], created_job_ids[1])


class TestOrchestrateFallbackInit(unittest.TestCase):
    @patch("email_automation.pipeline.run_inbound_email_workflow")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline._build_mailbox_actions")
    def test_no_runtime_context_still_builds_mailbox_stack(
        self, mock_build, mock_gate, _mock_ai, mock_wf
    ):
        from core.email_pipeline_ai_gate import EmailPipelineAIGateDecision
        from email_automation.pipeline import orchestrate_incoming

        mock_wf.return_value = {"success": True, "correlation_id": "c"}
        mock_gate.return_value = EmailPipelineAIGateDecision(True, None)
        mock_build.return_value = MagicMock(services={"ai_assistant": MagicMock()})

        parsed = {
            "message_id": "x",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "t",
        }
        with patch("email_automation.pipeline.record_email_event"), patch(
            "email_automation.pipeline.MinimalEmailParser"
        ):
            orchestrate_incoming(parsed, user_id=3, runtime_context=None)

        mock_build.assert_called_once()

    @patch("email_automation.pipeline.run_inbound_email_workflow")
    @patch("email_automation.pipeline.should_run_mailbox_ai", return_value=True)
    @patch("email_automation.pipeline.evaluate_email_pipeline_ai_gate")
    @patch("email_automation.pipeline._build_mailbox_actions")
    def test_process_email_uses_runtime_context_actions(
        self, mock_build, mock_gate, _mock_ai, mock_wf
    ):
        from core.email_pipeline_ai_gate import EmailPipelineAIGateDecision
        from email_automation.pipeline import orchestrate_incoming
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        mock_wf.return_value = {
            "success": True,
            "correlation_id": "c",
            "lead_capture": {"success": True, "data": {}},
        }
        mock_gate.return_value = EmailPipelineAIGateDecision(True, None)

        mock_actions = MagicMock()
        mock_ai = MagicMock()
        mock_ai.is_enabled.return_value = False
        mock_ai.analyze_incoming_email.return_value = {
            "intent": "general_info",
            "confidence": 0.9,
            "suggested_reply": "hi",
        }
        mock_actions.services = {"ai_assistant": mock_ai}
        mock_build.return_value = mock_actions

        ctx = EmailAutomationRuntimeContext(
            job_id="job-pe",
            user_id=3,
            actions=mock_actions,
            parser=MagicMock(
                get_subject=MagicMock(return_value="S"),
                get_body_text=MagicMock(return_value="body"),
                get_sender=MagicMock(return_value="a@b.com"),
            ),
        )
        ctx._initialized = True

        parsed = {
            "message_id": "x",
            "headers": {"from": "a@b.com", "subject": "Hi"},
            "snippet": "t",
        }
        with patch("email_automation.pipeline.record_email_event"), patch(
            "email_automation.pipeline.evaluate_email_action_policy",
            return_value={
                "recommended_action_type": "mark_read",
                "should_auto_send": True,
                "requires_human_review": False,
            },
        ), patch(
            "email_automation.pipeline.automation_safety_manager.check_rate_limits",
            return_value={"allowed": True},
        ):
            orchestrate_incoming(parsed, user_id=3, runtime_context=ctx)

        mock_actions.process_email.assert_called_once()
        self.assertIs(mock_build.call_args[0][0], mock_actions)


class TestRuntimeContextLogging(unittest.TestCase):
    def test_initialized_log_has_safe_fields_only(self):
        from email_automation.runtime_context import EmailAutomationRuntimeContext

        with patch(
            "email_automation.actions.MinimalEmailActions", return_value=MagicMock()
        ), patch(
            "email_automation.ai_assistant.MinimalAIEmailAssistant", return_value=MagicMock()
        ), patch(
            "email_automation.parser.MinimalEmailParser", return_value=MagicMock()
        ), patch("email_automation.runtime_context.logger") as mock_logger:
            EmailAutomationRuntimeContext.for_gmail_sync("job-log", 12, gmail_service=None)

        mock_logger.info.assert_called()
        call_kwargs = mock_logger.info.call_args
        extra = call_kwargs.kwargs.get("extra")
        if extra is None and len(call_kwargs.args) > 1:
            extra = call_kwargs.args[1]
        self.assertIsNotNone(extra)
        self.assertEqual(extra["event"], "email.sync.runtime_context.initialized")
        self.assertEqual(extra["job_id"], "job-log")
        self.assertEqual(extra["user_id"], 12)
        self.assertEqual(extra["provider"], "gmail")
        self.assertTrue(extra["context_reused"])
        forbidden = ("body", "subject", "sender", "token", "password", "credential")
        extra_str = str(extra).lower()
        for key in forbidden:
            self.assertNotIn(key, extra_str)


if __name__ == "__main__":
    unittest.main()
