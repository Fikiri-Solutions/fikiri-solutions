#!/usr/bin/env python3
"""Revenue-critical mailbox automation tests."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from email_automation import pipeline
from email_automation.actions import MinimalEmailActions


class _Idem:
    def __init__(self):
        self.store = {}

    def check_key(self, key):
        return self.store.get(key)

    def store_key(self, key, *_args, **_kwargs):
        self.store[key] = {"status": "pending"}

    def update_key_result(self, key, status, response_data=None):
        self.store[key] = {"status": status, "response_data": response_data}


def test_mailbox_flow_idempotent_and_logged():
    parsed = {
        "message_id": "m1",
        "headers": {"from": "Lead <lead@example.com>", "subject": "Need help"},
        "body": {"text": "hello", "html": ""},
        "snippet": "hello",
        "labels": []
    }

    ai_assistant = MagicMock()
    ai_assistant.classify_email_intent.return_value = {"intent": "lead_inquiry"}
    ai_assistant.generate_reply.return_value = "Thanks"

    actions = MinimalEmailActions(services={"ai_assistant": ai_assistant})
    actions.db_optimizer = MagicMock()
    actions._auto_reply = MagicMock(return_value={"success": True, "action": "auto_reply"})

    idem = _Idem()

    with patch("email_automation.actions.idempotency_manager", idem), \
         patch("email_automation.pipeline.automation_safety_manager") as mock_safety, \
         patch("email_automation.pipeline.db_optimizer") as mock_db, \
         patch("email_automation.pipeline.enhanced_crm_service") as mock_crm, \
         patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls:
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_parser = MagicMock()
        mock_parser.get_subject.return_value = "Need help"
        mock_parser.get_body_text.return_value = "hello"
        mock_parser.get_sender.return_value = "Lead <lead@example.com>"
        mock_parser_cls.return_value = mock_parser
        mock_db.execute_query.return_value = [{"id": 123}]

        first = pipeline.orchestrate_incoming(parsed, user_id=1, actions=actions)
        second = pipeline.orchestrate_incoming(parsed, user_id=1, actions=actions)

    assert first.get("success") is True
    assert second.get("success") is True
    assert actions._auto_reply.call_count == 1
    mock_crm.add_lead_activity.assert_called_once()
