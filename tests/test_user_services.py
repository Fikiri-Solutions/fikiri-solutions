"""Tests for per-user service preference helpers."""

from unittest.mock import patch

from core.user_services import (
    get_user_service_row,
    is_crm_inbound_capture_enabled,
    is_service_enabled,
    should_run_mailbox_ai,
)


def test_is_service_enabled_defaults_true_when_no_row():
    with patch("core.user_services.get_user_service_row", return_value=None):
        assert is_service_enabled(1, "crm") is True
        assert should_run_mailbox_ai(1) is True


def test_is_service_enabled_respects_disabled_row():
    with patch(
        "core.user_services.get_user_service_row",
        return_value={"enabled": False, "settings": {}},
    ):
        assert is_service_enabled(1, "crm") is False


def test_crm_auto_lead_creation_setting():
    with patch(
        "core.user_services.get_user_service_row",
        return_value={"enabled": True, "settings": {"autoLeadCreation": False}},
    ):
        assert is_crm_inbound_capture_enabled(1) is False

    with patch(
        "core.user_services.get_user_service_row",
        return_value={"enabled": True, "settings": {"autoLeadCreation": True}},
    ):
        assert is_crm_inbound_capture_enabled(1) is True
