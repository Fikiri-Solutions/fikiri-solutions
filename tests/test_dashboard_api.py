#!/usr/bin/env python3
"""
Dashboard API Unit Tests
Tests for analytics/dashboard_api.py (metrics, debug)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from analytics.dashboard_api import dashboard_bp


class TestDashboardAPI(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(dashboard_bp)
        self.client = self.app.test_client()

    @patch("analytics.dashboard_api.get_current_user")
    def test_debug_dashboard_requires_auth(self, mock_user):
        mock_user.return_value = None
        response = self.client.get("/api/dashboard/debug")
        self.assertEqual(response.status_code, 401)

    @patch("analytics.dashboard_api.db_optimizer")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_debug_dashboard_returns_debug_info(self, mock_get_jwt, mock_db):
        mock_get_jwt.return_value.verify_access_token.return_value = {
            "user_id": 1, "email": "u@t.com"
        }
        mock_db.execute_query.return_value = [{"id": 1, "email": "u@t.com"}]
        response = self.client.get(
            "/api/dashboard/debug",
            headers={"Authorization": "Bearer fake-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("data", data)
        self.assertIn("user_id", data["data"])
        self.assertIn("queries_tested", data["data"])


if __name__ == "__main__":
    unittest.main()
