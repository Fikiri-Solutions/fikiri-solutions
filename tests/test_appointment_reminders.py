#!/usr/bin/env python3
"""
Appointment Reminder Job Unit Tests
Tests for core/appointment_reminders.py
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from core import appointment_reminders


class _Idem:
    def __init__(self):
        self.store = {}

    def check_key(self, key):
        return self.store.get(key)

    def store_key(self, key, *_args, **_kwargs):
        self.store[key] = {"status": "pending"}

    def update_key_result(self, key, status, response_data=None):
        self.store[key] = {"status": status, "response_data": response_data}


class TestAppointmentReminders(unittest.TestCase):
    def test_run_reminder_job_sends_and_updates(self):
        appt_24 = {"id": 1, "user_email": "a@example.com", "user_id": 1}
        appt_2 = {"id": 2, "user_email": "b@example.com", "user_id": 1}

        with patch("core.appointment_reminders.db_optimizer") as mock_db, \
             patch("core.appointment_reminders.automation_safety_manager") as mock_safety, \
             patch("core.appointment_reminders.enhanced_crm_service") as mock_crm:
            mock_db.execute_query.side_effect = [
                [appt_24],  # 24h query
                [appt_2],   # 2h query
                None,       # update 24h
                None,       # update 2h
            ]
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            idem = _Idem()
            with patch("core.appointment_reminders.idempotency_manager", idem), \
                 patch("core.appointment_reminders.send_appointment_reminder_email", return_value=True) as send_email:
                result = appointment_reminders.run_reminder_job()

        self.assertTrue(result["success"])
        self.assertEqual(result["reminders_sent"], 2)
        self.assertEqual(send_email.call_count, 2)

    def test_run_reminder_job_handles_send_failure(self):
        appt_24 = {"id": 1, "user_email": "a@example.com", "user_id": 1}

        with patch("core.appointment_reminders.db_optimizer") as mock_db, \
             patch("core.appointment_reminders.automation_safety_manager") as mock_safety, \
             patch("core.appointment_reminders.enhanced_crm_service") as mock_crm:
            mock_db.execute_query.side_effect = [
                [appt_24],  # 24h query
                [],         # 2h query
            ]
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            idem = _Idem()
            with patch("core.appointment_reminders.idempotency_manager", idem), \
                 patch("core.appointment_reminders.send_appointment_reminder_email", side_effect=Exception("send failed")):
                result = appointment_reminders.run_reminder_job()

        self.assertTrue(result["success"])
        self.assertEqual(result["reminders_sent"], 0)

    def test_reminder_job_idempotent(self):
        appt_24 = {"id": 1, "user_email": "a@example.com", "user_id": 1}

        with patch("core.appointment_reminders.db_optimizer") as mock_db, \
             patch("core.appointment_reminders.automation_safety_manager") as mock_safety, \
             patch("core.appointment_reminders.enhanced_crm_service") as mock_crm:
            mock_db.execute_query.side_effect = [
                [appt_24],  # 24h query
                [],         # 2h query
                None,       # update 24h
                [appt_24],  # 24h query (second run)
                [],         # 2h query
            ]
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            idem = _Idem()
            with patch("core.appointment_reminders.idempotency_manager", idem), \
                 patch("core.appointment_reminders.send_appointment_reminder_email", return_value=True) as send_email:
                first = appointment_reminders.run_reminder_job()
                second = appointment_reminders.run_reminder_job()

        self.assertEqual(first["reminders_sent"], 1)
        self.assertEqual(second["reminders_sent"], 0)
        self.assertEqual(send_email.call_count, 1)


if __name__ == "__main__":
    unittest.main()
