"""
Unit tests for core/integrations/calendar/calendar_manager.py (CalendarManager).
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.calendar.calendar_manager import CalendarManager


class TestCalendarManager:
    def test_init_stores_user_id(self):
        mgr = CalendarManager(user_id=42)
        assert mgr.user_id == 42

    @patch("core.integrations.calendar.calendar_manager.integration_manager")
    def test_get_calendar_client_no_integration_returns_none(self, mock_mgr):
        mock_mgr.get_integration.return_value = None
        cm = CalendarManager(user_id=1)
        client = cm.get_calendar_client(provider="google_calendar")
        assert client is None

    @patch("core.integrations.calendar.calendar_manager.integration_manager")
    def test_get_calendar_client_no_token_returns_none(self, mock_mgr):
        mock_mgr.get_integration.return_value = {"id": 1}
        mock_mgr.get_valid_token.return_value = None
        cm = CalendarManager(user_id=1)
        client = cm.get_calendar_client(provider="google_calendar")
        assert client is None

    @patch("core.integrations.calendar.calendar_manager.GoogleCalendarClient")
    @patch("core.integrations.calendar.calendar_manager.integration_manager")
    def test_get_calendar_client_returns_google_client(self, mock_mgr, mock_gcal):
        mock_mgr.get_integration.return_value = {"id": 1}
        mock_mgr.get_valid_token.return_value = "token123"
        mock_gcal.return_value = MagicMock()
        cm = CalendarManager(user_id=1)
        client = cm.get_calendar_client(provider="google_calendar")
        assert client is not None
        mock_gcal.assert_called_once_with("token123")

    @patch("core.integrations.calendar.calendar_manager.integration_manager")
    def test_create_event_no_client_raises(self, mock_mgr):
        mock_mgr.get_integration.return_value = None
        cm = CalendarManager(user_id=1)
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        try:
            cm.create_event("Meeting", start, end, provider="google_calendar")
            assert False
        except ValueError as e:
            assert "not connected" in str(e).lower() or "Calendar" in str(e)

    @patch.object(CalendarManager, "get_freebusy")
    def test_check_conflicts_returns_list(self, mock_fb):
        mock_fb.return_value = {
            "primary": {"busy": [{"start": "2024-01-01T10:00:00Z", "end": "2024-01-01T11:00:00Z"}]}
        }
        cm = CalendarManager(user_id=1)
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        conflicts = cm.check_conflicts(start, end, provider="google_calendar")
        assert isinstance(conflicts, list)
        assert len(conflicts) == 1
        assert "start" in conflicts[0] and "end" in conflicts[0]
