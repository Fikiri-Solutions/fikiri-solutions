#!/usr/bin/env python3
"""Explicit site-chat handoffs notify Slack; ordinary answers do not."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from company_chatbot.handoff_notify import (
    is_explicit_human_handoff,
    notify_site_chat_handoff,
)
from company_chatbot.schemas import (
    HandoffMetadata,
    LeadAssessmentMetadata,
    LeadIntentMetadata,
    MessageResult,
)


def _result(**kwargs) -> MessageResult:
    defaults = dict(
        mode="answer",
        response="ok",
        handoff=HandoffMetadata(applicable=False),
        lead_intent=LeadIntentMetadata(),
        turn_count=1,
        lead_assessment=LeadAssessmentMetadata(tier="casual", score=1, synopsis="hi"),
    )
    defaults.update(kwargs)
    return MessageResult(**defaults)


def test_grounded_answer_with_soft_handoff_is_not_explicit():
    result = _result(
        handoff=HandoffMetadata(
            applicable=True,
            secondary="/contact",
            handoff_type=None,
        ),
        lead_intent=LeadIntentMetadata(signals=["product_interest"]),
    )
    assert is_explicit_human_handoff(result) is False


def test_guard_handoff_is_explicit():
    result = _result(
        handoff=HandoffMetadata(applicable=True, handoff_type="intake", secondary="/intake"),
        lead_intent=LeadIntentMetadata(signals=["guard_handoff", "frustration"]),
    )
    assert is_explicit_human_handoff(result) is True


def test_contact_mode_is_explicit():
    result = _result(
        mode="contact",
        handoff=HandoffMetadata(applicable=True, handoff_type="contact", secondary="/contact"),
        lead_intent=LeadIntentMetadata(signals=["contact_request"]),
    )
    assert is_explicit_human_handoff(result) is True


def test_intake_complete_with_email_is_explicit():
    result = _result(
        mode="workflow_audit",
        handoff=HandoffMetadata(applicable=True, handoff_type="intake", secondary="/intake"),
        lead_intent=LeadIntentMetadata(capture_ready=True, signals=["intake"]),
        intake={
            "complete": True,
            "slots": {"contact_email": "lead@example.com", "industry": "landscaping"},
        },
    )
    assert is_explicit_human_handoff(result) is True


@patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
def test_notify_calls_helper_for_contact(mock_send):
    result = _result(
        mode="contact",
        handoff=HandoffMetadata(applicable=True, handoff_type="contact", secondary="/contact"),
        lead_intent=LeadIntentMetadata(signals=["contact_request"]),
        lead_assessment=LeadAssessmentMetadata(
            tier="warm", score=6, synopsis="Wants a human"
        ),
    )
    assert notify_site_chat_handoff(
        session_id="site_abc", result=result, user_message="talk to someone"
    )
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert "Site chat handoff" in kwargs["title"]
    assert kwargs["dedupe_key"]


@patch("core.lead_form_notifications.send_lead_slack_notification")
def test_notify_skips_ordinary_answer(mock_send):
    result = _result(
        handoff=HandoffMetadata(applicable=True, secondary="/contact"),
        lead_intent=LeadIntentMetadata(signals=["product_interest"]),
    )
    assert notify_site_chat_handoff(session_id="site_abc", result=result) is False
    mock_send.assert_not_called()
