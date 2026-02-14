#!/usr/bin/env python3
"""
Appointments Service Unit Tests
Tests for core/appointments_service.py
"""

import unittest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from core.appointments_service import (
    AppointmentsService,
    SUGGESTED_SLOTS_COUNT,
)


class _FakeCursor:
    def __init__(self, conflict_rows=None):
        self._conflict_rows = conflict_rows or []
        self._execute_calls = 0
        self.lastrowid = 123

    def execute(self, _query, _params=None):
        self._execute_calls += 1
        return self

    def fetchall(self):
        # first call is conflict check
        return self._conflict_rows


class _FakeConn:
    def __init__(self, conflict_rows=None):
        self._cursor = _FakeCursor(conflict_rows=conflict_rows)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestAppointmentsService(unittest.TestCase):
    def setUp(self):
        self.service = AppointmentsService(user_id=1)

    def test_create_appointment_rejects_past_start(self):
        start = datetime.now() - timedelta(days=1)
        end = start + timedelta(minutes=30)
        with self.assertRaises(ValueError):
            self.service.create_appointment("Title", start, end)

    def test_create_appointment_conflict_raises(self):
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(minutes=30)
        fake_conn = _FakeConn(conflict_rows=[(1,)])
        with patch("core.appointments_service.db_optimizer.get_connection", return_value=fake_conn):
            with self.assertRaises(ValueError):
                self.service.create_appointment("Title", start, end)
        self.assertTrue(fake_conn.rolled_back)

    def test_create_appointment_success(self):
        start = datetime.now() + timedelta(hours=2)
        end = start + timedelta(minutes=30)
        fake_conn = _FakeConn(conflict_rows=[])

        row = {
            "id": 123,
            "user_id": 1,
            "title": "Title",
            "description": None,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "status": "scheduled",
            "contact_id": None,
            "contact_name": None,
            "contact_email": None,
            "contact_phone": None,
            "location": None,
            "notes": None,
            "sync_to_calendar": 0,
        }
        with patch("core.appointments_service.db_optimizer.get_connection", return_value=fake_conn):
            with patch("core.appointments_service.db_optimizer.execute_query", return_value=[row]):
                result = self.service.create_appointment("Title", start, end)

        self.assertEqual(result["id"], 123)
        self.assertEqual(result["status"], "scheduled")
        self.assertTrue(fake_conn.committed)

    def test_update_appointment_invalid_transition(self):
        appointment = {
            "id": 1,
            "user_id": 1,
            "title": "Title",
            "description": None,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "status": "scheduled",
        }
        with patch.object(self.service, "get_appointment", return_value=appointment):
            with self.assertRaises(ValueError):
                self.service.update_appointment(1, {"status": "completed"})

    def test_update_appointment_invalid_field(self):
        appointment = {
            "id": 1,
            "user_id": 1,
            "title": "Title",
            "description": None,
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "status": "scheduled",
        }
        with patch.object(self.service, "get_appointment", return_value=appointment):
            with self.assertRaises(ValueError):
                self.service.update_appointment(1, {"DROP TABLE": "x"})

    def test_calculate_free_slots_with_busy(self):
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=3)
        busy = [{
            "start": (start + timedelta(minutes=30)).isoformat(),
            "end": (start + timedelta(minutes=60)).isoformat(),
        }]
        free_slots = self.service.calculate_free_slots(start, end, busy, slot_duration_minutes=30)
        # Should return at most suggested slots and include slots before/after busy period
        self.assertLessEqual(len(free_slots), SUGGESTED_SLOTS_COUNT)
        self.assertGreater(len(free_slots), 0)

    def test_get_freebusy_excludes_canceled(self):
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)
        with patch.object(self.service, "list_appointments") as list_appointments:
            list_appointments.return_value = [
                {"id": 1, "title": "A", "start_time": start.isoformat(), "end_time": end.isoformat(), "status": "scheduled"},
                {"id": 2, "title": "B", "start_time": start.isoformat(), "end_time": end.isoformat(), "status": "canceled"},
            ]
            result = self.service.get_freebusy(start, end)

        self.assertEqual(len(result["busy"]), 1)
        self.assertEqual(result["busy"][0]["appointment_id"], 1)


if __name__ == "__main__":
    unittest.main()
