"""
Unit tests for email_automation/jobs.py (EmailJobManager, EmailJob, helpers).
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEmailJobHelpers:
    """Test module-level helpers."""

    def test_is_test_mode_true_in_test_env(self):
        from email_automation.jobs import _is_test_mode
        assert _is_test_mode() is True

    def test_utcnow_naive_returns_naive_datetime(self):
        from email_automation.jobs import _utcnow_naive
        from datetime import datetime
        t = _utcnow_naive()
        assert t.tzinfo is None
        assert isinstance(t, datetime)


class TestEmailJobDataclass:
    """Test EmailJob structure."""

    def test_email_job_fields(self):
        from email_automation.jobs import EmailJob
        j = EmailJob(
            id="j1",
            type="welcome",
            recipient="u@example.com",
            subject="Welcome",
            template="welcome",
            data={"name": "User"},
        )
        assert j.id == "j1"
        assert j.type == "welcome"
        assert j.recipient == "u@example.com"
        assert j.priority == 1
        assert j.attempts == 0
        assert j.max_attempts == 3


class TestEmailJobManager:
    """Test EmailJobManager (queue, generate, status) with mocked DB and Redis."""

    @patch("email_automation.jobs.db_optimizer")
    def test_manager_init_in_test_mode_has_no_redis(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        assert mgr.redis_client is None
        assert mgr.queue_name == "fikiri:email:jobs"

    @patch("email_automation.jobs.db_optimizer")
    def test_queue_welcome_email_returns_job_id(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        job_id = mgr.queue_welcome_email(1, "user@example.com", "Alice", "Acme Inc")
        assert job_id is not None
        assert job_id.startswith("welcome_")
        assert "1_" in job_id
        mock_db.execute_query.assert_called()

    @patch("email_automation.jobs.db_optimizer")
    def test_queue_password_reset_email_returns_job_id(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        job_id = mgr.queue_password_reset_email("u@example.com", "token123", "Bob")
        assert job_id is not None
        assert "reset_" in job_id
        mock_db.execute_query.assert_called()

    @patch("email_automation.jobs.db_optimizer")
    def test_generate_welcome_email_includes_name_and_company(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        content = mgr._generate_welcome_email({
            "name": "Jane",
            "company_name": "TestCo",
            "dashboard_url": "https://example.com",
            "support_email": "support@example.com",
        })
        assert "Jane" in content
        assert "TestCo" in content
        assert "Welcome" in content
        assert "html" in content.lower()

    @patch("email_automation.jobs.db_optimizer")
    def test_generate_email_content_routes_to_welcome(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        content = mgr._generate_email_content("welcome", {"name": "X", "company_name": "Y"})
        assert "Welcome" in content
        assert "X" in content or "there" in content

    @patch("email_automation.jobs.db_optimizer")
    def test_generate_email_content_unknown_template_uses_default(self, mock_db):
        mock_db.execute_query.return_value = None
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        content = mgr._generate_email_content("unknown_type", {"name": "X"})
        assert isinstance(content, str)
        assert len(content) > 0

    @patch("email_automation.jobs.db_optimizer")
    def test_get_job_status_returns_none_for_missing_job(self, mock_db):
        mock_db.execute_query.return_value = []
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        status = mgr.get_job_status("nonexistent_job_id")
        assert status is None

    @patch("email_automation.jobs.db_optimizer")
    def test_get_job_status_returns_dict_when_found(self, mock_db):
        mock_db.execute_query.return_value = [{
            "id": "welcome_1_123",
            "type": "welcome",
            "recipient": "u@example.com",
            "subject": "Welcome",
            "template": "welcome",
            "status": "pending",
            "priority": 1,
            "created_at": "2024-01-01 00:00:00",
            "scheduled_at": "2024-01-01 00:00:00",
            "sent_at": None,
            "attempts": 0,
            "max_attempts": 3,
            "error_message": None,
            "metadata": "{}",
        }]
        from email_automation.jobs import EmailJobManager
        mgr = EmailJobManager()
        status = mgr.get_job_status("welcome_1_123")
        assert status is not None
        assert status.get("id") == "welcome_1_123"
        assert status.get("status") == "pending"


class TestSendEmailFacades:
    """Test top-level send_* functions delegate to manager."""

    @patch("email_automation.jobs.email_job_manager")
    def test_send_welcome_email_calls_manager(self, mock_mgr):
        mock_mgr.queue_welcome_email.return_value = "welcome_1_123"
        from email_automation.jobs import send_welcome_email
        result = send_welcome_email(1, "u@example.com", "Alice", "Acme")
        mock_mgr.queue_welcome_email.assert_called_once_with(1, "u@example.com", "Alice", "Acme")
        assert result == "welcome_1_123"
