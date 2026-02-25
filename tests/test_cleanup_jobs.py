"""
Unit tests for core/integrations/cleanup_jobs.py.
"""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.integrations.cleanup_jobs import (
    cleanup_expired_oauth_states,
    cleanup_stale_refresh_locks,
    cleanup_inactive_event_links,
    run_all_cleanup_jobs,
    OAUTH_STATE_EXPIRY_HOURS,
    STALE_REFRESH_SECONDS,
    INACTIVE_LINKS_MONTHS,
)


class TestCleanupJobs:
    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_expired_oauth_states_success(self, mock_db):
        mock_db.execute_query.return_value = 5
        result = cleanup_expired_oauth_states()
        assert result["success"] is True
        assert "deleted" in result
        mock_db.execute_query.assert_called_once()
        call_args = mock_db.execute_query.call_args[0][0]
        assert "oauth_states" in call_args
        assert "DELETE" in call_args

    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_expired_oauth_states_exception_returns_failure(self, mock_db):
        mock_db.execute_query.side_effect = RuntimeError("db error")
        result = cleanup_expired_oauth_states()
        assert result["success"] is False
        assert "error" in result

    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_stale_refresh_locks_success(self, mock_db):
        mock_db.execute_query.return_value = 1
        result = cleanup_stale_refresh_locks()
        assert result["success"] is True
        assert "cleared" in result
        call_args = mock_db.execute_query.call_args[0][0]
        assert "integration_sync_state" in call_args or "refreshing" in call_args

    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_stale_refresh_locks_exception_returns_failure(self, mock_db):
        mock_db.execute_query.side_effect = RuntimeError("db error")
        result = cleanup_stale_refresh_locks()
        assert result["success"] is False

    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_inactive_event_links_success(self, mock_db):
        mock_db.execute_query.return_value = 0
        result = cleanup_inactive_event_links(months=6)
        assert result["success"] is True
        assert "deleted" in result
        call_args = mock_db.execute_query.call_args[0][0]
        assert "calendar_event_links" in call_args

    @patch("core.integrations.cleanup_jobs.db_optimizer")
    def test_cleanup_inactive_event_links_exception_returns_failure(self, mock_db):
        mock_db.execute_query.side_effect = RuntimeError("db error")
        result = cleanup_inactive_event_links()
        assert result["success"] is False

    @patch("core.integrations.cleanup_jobs.cleanup_inactive_event_links")
    @patch("core.integrations.cleanup_jobs.cleanup_stale_refresh_locks")
    @patch("core.integrations.cleanup_jobs.cleanup_expired_oauth_states")
    def test_run_all_cleanup_jobs_returns_combined_results(self, mock_oauth, mock_stale, mock_links):
        mock_oauth.return_value = {"success": True, "deleted": 2}
        mock_stale.return_value = {"success": True, "cleared": 0}
        mock_links.return_value = {"success": True, "deleted": 1}
        result = run_all_cleanup_jobs()
        assert "oauth_states" in result
        assert "stale_refresh_locks" in result
        assert "inactive_links" in result
        assert result["oauth_states"]["success"] is True
        assert result["oauth_states"]["deleted"] == 2


class TestCleanupConstants:
    def test_constants_defined(self):
        assert OAUTH_STATE_EXPIRY_HOURS == 24
        assert STALE_REFRESH_SECONDS == 60
        assert INACTIVE_LINKS_MONTHS == 6
