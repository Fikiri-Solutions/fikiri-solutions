#!/usr/bin/env python3
"""
Billing Manager Unit Tests
Tests for core/billing_manager.py
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from core.billing_manager import FikiriBillingManager, SubscriptionTier, UsageMetrics


class TestBillingManager(unittest.TestCase):
    def setUp(self):
        self.manager = FikiriBillingManager()

    def test_create_subscription_stripe_unavailable(self):
        with patch("core.billing_manager.STRIPE_AVAILABLE", False):
            result = self.manager.create_subscription("cus_1", "price_1")
        self.assertEqual(result, {})

    def test_check_usage_limits_overages(self):
        usage = UsageMetrics(
            emails_processed=700,
            leads_created=150,
            ai_responses_generated=300,
            month_year="2026-02",
        )
        result = self.manager.check_usage_limits("u1", SubscriptionTier.STARTER, usage)
        self.assertFalse(result["within_limits"])
        self.assertEqual(result["email_overage"], 200)
        self.assertEqual(result["lead_overage"], 50)
        self.assertEqual(result["ai_overage"], 100)
        self.assertGreater(result["total_overage_cost"], 0)

    def test_check_usage_limits_unlimited_tier(self):
        usage = UsageMetrics(
            emails_processed=100000,
            leads_created=100000,
            ai_responses_generated=100000,
            month_year="2026-02",
        )
        result = self.manager.check_usage_limits("u1", SubscriptionTier.ENTERPRISE, usage)
        self.assertTrue(result["within_limits"])
        self.assertEqual(result["total_overage_cost"], 0)

    def test_get_pricing_tiers_structure(self):
        tiers = self.manager.get_pricing_tiers()
        self.assertIn("starter", tiers)
        self.assertIn("growth", tiers)
        self.assertIn("business", tiers)
        self.assertIn("enterprise", tiers)
        self.assertIn("monthly_price", tiers["starter"])
        self.assertIn("limits", tiers["starter"])
        self.assertEqual(
            tiers["starter"]["limits"]["emails"],
            self.manager.tier_limits[SubscriptionTier.STARTER].emails_per_month,
        )

    def test_create_subscription_success(self):
        stripe_mock = MagicMock()
        subscription = MagicMock()
        subscription.id = "sub_1"
        subscription.status = "trialing"
        subscription.trial_end = 123
        subscription.latest_invoice.payment_intent.client_secret = "secret"
        stripe_mock.Subscription.create.return_value = subscription

        with patch("core.billing_manager.STRIPE_AVAILABLE", True):
            with patch("core.billing_manager.stripe", stripe_mock):
                result = self.manager.create_subscription("cus_1", "price_1", trial_days=7)

        self.assertEqual(result["subscription_id"], "sub_1")
        self.assertEqual(result["status"], "trialing")
        stripe_mock.Subscription.create.assert_called_once()

    def test_create_checkout_session_params(self):
        stripe_mock = MagicMock()
        session = MagicMock()
        session.id = "cs_1"
        session.url = "https://checkout"
        stripe_mock.checkout.Session.create.return_value = session

        with patch("core.billing_manager.stripe", stripe_mock):
            result = self.manager.create_checkout_session("price_1", customer_id=None)

        self.assertEqual(result["session_id"], "cs_1")
        args, kwargs = stripe_mock.checkout.Session.create.call_args
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(kwargs["trial_period_days"], 14)
        self.assertEqual(kwargs["customer_creation"], "always")


if __name__ == "__main__":
    unittest.main()
