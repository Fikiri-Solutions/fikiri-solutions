"""Unit tests for core/sms_consent.py."""

import json
import os
import sys

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sms_consent import (
    lead_row_allows_sms,
    lead_sms_destination_matches,
    parse_lead_metadata,
)


def test_parse_lead_metadata_empty():
    assert parse_lead_metadata(None) == {}
    assert parse_lead_metadata("") == {}
    assert parse_lead_metadata("{}") == {}


def test_parse_lead_metadata_dict():
    assert parse_lead_metadata({"a": 1}) == {"a": 1}


def test_lead_row_allows_sms_requires_true():
    assert lead_row_allows_sms({"metadata": "{}"}) == (False, "sms_consent_required")
    assert lead_row_allows_sms({"metadata": json.dumps({"sms_consent": False})}) == (
        False,
        "sms_consent_required",
    )
    assert lead_row_allows_sms({"metadata": json.dumps({"sms_consent": True})}) == (True, "")


def test_lead_sms_destination_matches():
    assert lead_sms_destination_matches("+1 352-575-5716", None) is True
    assert lead_sms_destination_matches("+13525755716", "+1 (352) 575-5716") is True
    assert lead_sms_destination_matches("+15551234567", "+15559876543") is False


def test_lead_row_allows_sms_rejects_truthy_non_bool():
    """Account-holder style strings must not unlock lead SMS."""
    assert lead_row_allows_sms({"metadata": json.dumps({"sms_consent": "true"})}) == (
        False,
        "sms_consent_required",
    )
    assert lead_row_allows_sms({"metadata": json.dumps({"sms_consent": 1})}) == (
        False,
        "sms_consent_required",
    )


def test_sms_action_consent_required_message():
    from unittest.mock import MagicMock, patch
    from services.automation_actions.sms_action import SmsActionHandler
    from core.sms_consent import SMS_CONSENT_BLOCKED_MESSAGE

    handler = SmsActionHandler(MagicMock())
    with patch("services.automation_actions.sms_action.db_optimizer") as mock_db:
        mock_db.execute_query.return_value = [
            {"id": 1, "phone": "+15551234567", "metadata": json.dumps({"sms_consent": False})}
        ]
        out = handler.execute_send_sms({"message": "Hi", "lead_id": 1}, {}, 9)
    assert out.get("success") is False
    assert out.get("skipped") is True
    assert out.get("error_code") == "SMS_CONSENT_REQUIRED"
    assert out.get("message") == SMS_CONSENT_BLOCKED_MESSAGE


def test_apply_lead_sms_consent_merges_metadata():
    from core.sms_consent import apply_lead_sms_consent_to_metadata

    base = {"lead_quality": "C", "score_breakdown": {"x": 1}}
    out = apply_lead_sms_consent_to_metadata(base, True, source="manual_crm")
    assert out["lead_quality"] == "C"
    assert out["score_breakdown"] == {"x": 1}
    assert out["sms_consent"] is True
    assert out["sms_consent_at"]
    assert out["sms_consent_source"] == "manual_crm"
    revoked = apply_lead_sms_consent_to_metadata(out, False)
    assert revoked["lead_quality"] == "C"
    assert revoked["sms_consent"] is False
    assert revoked["sms_consent_at"] is None


def test_sms_action_requires_phone():
    from unittest.mock import MagicMock, patch
    from services.automation_actions.sms_action import SmsActionHandler

    handler = SmsActionHandler(MagicMock())
    with patch("services.automation_actions.sms_action.db_optimizer") as mock_db:
        mock_db.execute_query.return_value = [
            {"id": 1, "phone": "", "metadata": json.dumps({"sms_consent": True})}
        ]
        out = handler.execute_send_sms({"message": "Hi", "lead_id": 1}, {}, 9)
    assert out.get("success") is False
    assert "phone" in (out.get("error") or "").lower()

