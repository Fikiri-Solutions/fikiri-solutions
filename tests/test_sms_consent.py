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

