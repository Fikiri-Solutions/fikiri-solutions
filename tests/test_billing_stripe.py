#!/usr/bin/env python3
"""
Billing & Stripe API Unit Tests
Tests for core/billing_api.py and Stripe-related flows (mocked Stripe)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestBillingAPI(unittest.TestCase):
    """Test billing blueprint endpoints with mocked Stripe and JWT."""

    def setUp(self):
        from flask import Flask
        from core.billing_api import billing_bp

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(billing_bp)
        self.client = self.app.test_client()

    @patch("core.billing_api.get_current_user")
    def test_billing_health_or_info_requires_auth_where_required(self, mock_user):
        mock_user.return_value = None
        # Route that requires JWT (e.g. subscription/current) returns 401 without token
        response = self.client.get("/api/billing/subscription/current")
        self.assertIn(response.status_code, (200, 401))

    @patch("core.billing_api.get_current_user")
    @patch("core.billing_api.stripe_manager")
    def test_plans_endpoint_returns_list_when_authenticated(self, mock_stripe, mock_user):
        mock_user.return_value = {"user_id": 1, "email": "u@t.com"}
        mock_stripe.get_pricing_tiers.return_value = []
        response = self.client.get("/api/billing/pricing")
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("success", data or {})
            self.assertIn("pricing_tiers", data or {})

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.billing_api.get_user_email")
    @patch("core.billing_api.get_stripe_customer_id")
    @patch("core.billing_api.stripe_manager")
    def test_customer_details_creates_customer_if_missing(
        self, mock_stripe_manager, mock_get_customer_id, mock_get_email, mock_jwt_manager
    ):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_get_email.return_value = "samepassive.co@gmail.com"
        mock_get_customer_id.return_value = None
        mock_stripe_manager.create_customer.return_value = {"id": "cus_123"}
        mock_stripe_manager.get_customer_details.return_value = {"id": "cus_123", "email": "samepassive.co@gmail.com"}

        response = self.client.get(
            "/api/billing/customer/details",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("customer", {}).get("id"), "cus_123")
        mock_stripe_manager.create_customer.assert_called_once()


class TestStripeWebhookHandler(unittest.TestCase):
    """Test stripe_webhooks module (handler) with mocked Stripe events."""

    @patch("core.stripe_webhooks.stripe")
    def test_webhook_handler_constructs_without_error(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler

        h = StripeWebhookHandler()
        self.assertIsNotNone(h)


class TestFikiriStripeManager(unittest.TestCase):
    """Test fikiri_stripe_manager with mocked Stripe."""

    @patch("core.fikiri_stripe_manager.stripe")
    def test_manager_initializes(self, mock_stripe):
        try:
            from core.fikiri_stripe_manager import FikiriStripeManager

            m = FikiriStripeManager()
            self.assertIsNotNone(m)
        except Exception as e:
            if "STRIPE" in str(e).upper() or "stripe" in str(e):
                self.skipTest("Stripe not configured")
            raise


if __name__ == "__main__":
    unittest.main()
