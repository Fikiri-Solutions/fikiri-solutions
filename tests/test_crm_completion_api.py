#!/usr/bin/env python3
"""
CRM Completion API Unit Tests
Tests for crm/completion_api.py (follow-ups, reminders)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from crm.completion_api import crm_bp


class TestCRMCompletionAPI(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(crm_bp)
        self.client = self.app.test_client()

    @patch("crm.completion_api.get_follow_up_system")
    def test_create_follow_up_no_data_400(self, mock_get):
        response = self.client.post(
            "/api/crm/follow-ups/create", json={}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    @patch("crm.completion_api.get_follow_up_system")
    def test_create_follow_up_missing_required_field_400(self, mock_get):
        response = self.client.post(
            "/api/crm/follow-ups/create",
            json={"lead_id": 1, "user_id": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("crm.completion_api.get_follow_up_system")
    def test_create_follow_up_success(self, mock_get):
        mock_get.return_value = MagicMock(
            create_follow_up_task=MagicMock(
                return_value={"success": True, "task_id": "t1"}
            )
        )
        response = self.client.post(
            "/api/crm/follow-ups/create",
            json={"lead_id": 1, "user_id": 1, "stage": "qualified"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))

    @patch("crm.completion_api.get_follow_up_system")
    def test_create_follow_up_system_unavailable_500(self, mock_get):
        mock_get.return_value = None
        response = self.client.post(
            "/api/crm/follow-ups/create",
            json={"lead_id": 1, "user_id": 1, "stage": "qualified"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    @patch("crm.completion_api.get_follow_up_system")
    def test_process_follow_ups_success(self, mock_get):
        mock_get.return_value = MagicMock(
            process_pending_follow_ups=MagicMock(
                return_value={"success": True, "processed": 2}
            )
        )
        response = self.client.post(
            "/api/crm/follow-ups/process", json={}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
