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

    @patch("analytics.dashboard_api.db_optimizer")
    def test_dashboard_metrics_success(self, mock_db):
        # user, leads total, leads recent, oauth gmail, ai total
        mock_db.execute_query.side_effect = [
            [{"id": 1, "email": "u@t.com", "name": "User", "onboarding_completed": 1, "onboarding_step": 2}],
            [{"count": 5}],
            [{"count": 2}],
            [{"access_token_enc": "enc", "access_token": None, "expiry_timestamp": None}],
            [{"count": 1}],
        ]
        response = self.client.get("/api/dashboard/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        metrics = data.get("data", {})
        self.assertEqual(metrics.get("leads", {}).get("total"), 5)
        self.assertEqual(metrics.get("leads", {}).get("recent"), 2)
        self.assertTrue(metrics.get("integrations", {}).get("gmail_connected"))

    @patch("analytics.dashboard_api.get_current_user_id", return_value=None)
    def test_dashboard_activity_requires_auth(self, mock_user_id):
        response = self.client.get("/api/dashboard/activity")
        self.assertEqual(response.status_code, 401)

    @patch("analytics.dashboard_api.get_current_user_id", return_value=1)
    def test_dashboard_activity_success(self, mock_user_id):
        response = self.client.get("/api/dashboard/activity")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("activities", data.get("data", {}))

    @patch("analytics.dashboard_api.get_current_user_id", return_value=1)
    def test_dashboard_services_success(self, mock_user_id):
        response = self.client.get("/api/dashboard/services")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("services", data.get("data", {}))

    def test_dashboard_kpi_success(self):
        response = self.client.get("/api/dashboard/kpi")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("data", data)

    @patch("analytics.dashboard_api.db_optimizer")
    def test_dashboard_timeseries_success(self, mock_db):
        mock_db.execute_query.side_effect = [
            [{"day": "2026-03-01", "value": 2}],     # leads daily
            [{"day": "2026-03-01", "value": 5}],     # emails daily
            [{"day": "2026-03-01", "value": 3}],     # responses daily
            [{"day": "2026-03-01", "value": 100.0}], # revenue daily
            [{"value": 10}],  # current leads
            [{"value": 5}],   # previous leads
            [{"value": 20}],  # current emails
            [{"value": 10}],  # previous emails
            [{"value": 8}],   # current responses
            [{"value": 4}],   # previous responses
            [{"value": 300}], # current revenue
            [{"value": 200}], # previous revenue
        ]
        response = self.client.get("/api/dashboard/timeseries")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("timeseries", data.get("data", {}))
        self.assertIn("responses", data.get("data", {}).get("summary", {}))

    @patch("analytics.dashboard_api.db_optimizer")
    @patch("analytics.dashboard_api.get_current_user_id", return_value=1)
    def test_dashboard_email_metrics_success(self, mock_user_id, mock_db):
        # total, unread, then per-day results
        day_results = [[{"count": 0}] for _ in range(7)]
        mock_db.execute_query.side_effect = [
            [{"count": 10}],  # total
            [{"count": 3}],   # unread
            *day_results,
        ]
        response = self.client.get("/api/dashboard/emails?period=week")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("total_emails"), 10)
        self.assertEqual(data.get("data", {}).get("unread_emails"), 3)

    @patch("analytics.dashboard_api.db_optimizer")
    @patch("analytics.dashboard_api.get_current_user_id", return_value=1)
    def test_dashboard_ai_metrics_success(self, mock_user_id, mock_db):
        mock_db.execute_query.side_effect = [
            [{"count": 12}],  # total
            [{"count": 5}],   # recent
        ]
        response = self.client.get("/api/dashboard/ai")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("total_responses"), 12)
        self.assertEqual(data.get("data", {}).get("recent_responses"), 5)

    @patch("analytics.dashboard_api.db_optimizer")
    def test_dashboard_metrics_includes_ai_total(self, mock_db):
        """Metrics response includes ai.total for frontend mapping."""
        mock_db.execute_query.side_effect = [
            [{"id": 1, "email": "u@t.com", "name": "User", "onboarding_completed": 0, "onboarding_step": 1}],
            [{"count": 0}],
            [{"count": 0}],
            [{"count": 0}],
            [{"count": 7}],
        ]
        response = self.client.get("/api/dashboard/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        metrics = data.get("data", {})
        self.assertIn("ai", metrics)
        self.assertEqual(metrics["ai"].get("total"), 7)

    @patch("analytics.dashboard_api.db_optimizer")
    def test_dashboard_metrics_handles_db_error_gracefully(self, mock_db):
        """Metrics endpoint still returns 200 with defaults when a query fails."""
        mock_db.execute_query.side_effect = Exception("DB unavailable")
        response = self.client.get("/api/dashboard/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        metrics = data.get("data", {})
        self.assertIn("leads", metrics)
        self.assertIn("timestamp", metrics)

    @patch("analytics.dashboard_api.db_optimizer")
    def test_dashboard_timeseries_accepts_user_id_and_period(self, mock_db):
        mock_db.execute_query.side_effect = [
            [], [], [], [],  # daily rows
            [{"value": 0}], [{"value": 0}], [{"value": 0}], [{"value": 0}],
            [{"value": 0}], [{"value": 0}], [{"value": 0}], [{"value": 0}],
        ]
        """Timeseries accepts user_id and period query params."""
        response = self.client.get("/api/dashboard/timeseries?user_id=2&period=month")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("timeseries", data.get("data", {}))
        self.assertIn("summary", data.get("data", {}))

    def test_dashboard_industry_prompts_success(self):
        response = self.client.get("/api/dashboard/industry/prompts")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("prompts", data.get("data", {}))

    @patch("analytics.dashboard_api.billing_manager")
    def test_dashboard_industry_pricing_success(self, mock_billing):
        mock_billing.get_pricing_tiers.return_value = {
            "starter": {
                "name": "Starter",
                "monthly_price": 49,
                "features": ["basic_ai"],
                "limits": {"ai_responses": 200},
            }
        }
        response = self.client.get("/api/dashboard/industry/pricing")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("pricing_tiers", data.get("data", {}))

    @patch("analytics.dashboard_api.db_optimizer")
    @patch("analytics.dashboard_api.billing_manager")
    @patch("analytics.dashboard_api.get_current_user_id", return_value=1)
    def test_dashboard_industry_usage_success(self, mock_user_id, mock_billing, mock_db):
        mock_billing.get_pricing_tiers.return_value = {
            "growth": {"monthly_price": 99}
        }
        mock_db.execute_query.side_effect = [
            [{"tier": "growth"}],                                # subscription tier
            [{"usage_type": "ai_responses", "total": 12}],       # billing usage
            [{"value": 7}],                                      # automation executions
        ]
        response = self.client.get("/api/dashboard/industry/usage")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        usage = data.get("data", {}).get("usage", {})
        self.assertEqual(usage.get("tier"), "growth")
        self.assertEqual(usage.get("responses"), 12)


if __name__ == "__main__":
    unittest.main()
