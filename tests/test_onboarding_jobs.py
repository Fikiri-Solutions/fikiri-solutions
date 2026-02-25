"""
Unit tests for core/onboarding_jobs.py (OnboardingJobManager, run_first_sync helpers).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.onboarding_jobs import (
    extract_email_from_address,
    extract_name_from_address,
    OnboardingJobManager,
    run_first_sync,
)


class TestExtractAddressHelpers:
    def test_extract_email_from_address_angle_bracket(self):
        assert extract_email_from_address("Jane <jane@example.com>") == "jane@example.com"
        assert extract_email_from_address("Bob <bob@test.co.uk>") == "bob@test.co.uk"

    def test_extract_email_from_address_plain(self):
        assert extract_email_from_address("user@domain.com") == "user@domain.com"

    def test_extract_email_from_address_invalid(self):
        assert extract_email_from_address("no-email-here") is None
        assert extract_email_from_address("") is None

    def test_extract_name_from_address_angle_bracket(self):
        assert extract_name_from_address("Jane Doe <jane@example.com>") == "Jane Doe"
        assert extract_name_from_address('"Smith, John" <john@example.com>') is not None

    def test_extract_name_from_address_plain_email(self):
        assert extract_name_from_address("user@domain.com") is None


class TestOnboardingJobManager:
    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_connection_helper._resolve_redis_url")
    def test_init_no_redis_sets_queue_none(self, mock_url, mock_client):
        mock_url.return_value = None
        mock_client.return_value = None
        mgr = OnboardingJobManager()
        assert mgr.redis_client is None
        assert mgr.queue is None

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_connection_helper._resolve_redis_url")
    def test_get_sync_progress_no_redis_returns_error(self, mock_url, mock_client):
        mock_url.return_value = None
        mock_client.return_value = None
        mgr = OnboardingJobManager()
        result = mgr.get_sync_progress(user_id=1)
        assert result.get("success") is False
        assert "Redis" in result.get("error", "") or "REDIS" in result.get("error_code", "")

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_connection_helper._resolve_redis_url")
    def test_get_sync_progress_redis_returns_progress_structure(self, mock_url, mock_client):
        mock_url.return_value = "redis://localhost"
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {"step": "parsing", "pct": "50", "total": "100", "processed": "50", "status": "running"}
        mock_client.return_value = mock_redis
        mgr = OnboardingJobManager()
        mgr.redis_client = mock_redis
        result = mgr.get_sync_progress(user_id=1)
        assert result.get("success") is True
        assert "progress" in result
        assert result["progress"].get("step") == "parsing"
        assert result["progress"].get("percentage") == 50

    @patch("core.onboarding_jobs.run_first_sync")
    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_connection_helper._resolve_redis_url")
    def test_queue_first_sync_job_no_queue_runs_sync_synchronously(self, mock_url, mock_client, mock_run):
        mock_url.return_value = None
        mock_client.return_value = None
        mgr = OnboardingJobManager()
        mock_run.return_value = {"success": True, "processed": 0, "leads_created": 0, "status": "completed"}
        result = mgr.queue_first_sync_job(user_id=1)
        assert result.get("success") is True
        assert "sync" in result.get("job_id", "").lower() or "message" in result
        mock_run.assert_called_once_with(1)


class TestRunFirstSync:
    def test_run_first_sync_no_gmail_returns_failed(self):
        with patch("core.onboarding_jobs.gmail_client", None):
            result = run_first_sync(user_id=999)
        assert result.get("success") is False
        assert result.get("status") == "failed"
        assert "error" in result
