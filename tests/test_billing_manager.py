"""Billing manager tests (usage limits + Stripe flows)."""

import unittest
from unittest.mock import patch, MagicMock

from core.billing_manager import FikiriBillingManager, SubscriptionTier, UsageMetrics


class TestBillingManager(unittest.TestCase):
    def test_check_usage_limits_overages(self):
        mgr = FikiriBillingManager()
        usage = UsageMetrics(
            emails_processed=600,
            leads_created=150,
            ai_responses_generated=250,
            month_year="2026-02",
        )
        result = mgr.check_usage_limits("1", SubscriptionTier.STARTER, usage)
        self.assertFalse(result["within_limits"])
        self.assertGreater(result["total_overage_cost"], 0)
        self.assertEqual(result["email_overage"], 100)
        self.assertEqual(result["lead_overage"], 50)
        self.assertEqual(result["ai_overage"], 50)

    @patch("core.billing_manager.stripe")
    def test_create_checkout_session_uses_stripe(self, mock_stripe):
        mgr = FikiriBillingManager()
        session = MagicMock(id="cs_1", url="http://checkout")
        mock_stripe.checkout.Session.create.return_value = session

        result = mgr.create_checkout_session("price_123", customer_id=None, success_url="http://ok", cancel_url="http://cancel")
        self.assertEqual(result["session_id"], "cs_1")
        self.assertEqual(result["url"], "http://checkout")
        mock_stripe.checkout.Session.create.assert_called_once()

    @patch("core.billing_manager.stripe")
    def test_create_subscription_returns_client_secret(self, mock_stripe):
        import core.billing_manager as bm
        bm.STRIPE_AVAILABLE = True
        mgr = FikiriBillingManager()
        invoice = MagicMock(payment_intent=MagicMock(client_secret="secret"))
        subscription = MagicMock(id="sub_1", status="trialing", trial_end=123, latest_invoice=invoice)
        mock_stripe.Subscription.create.return_value = subscription

        result = mgr.create_subscription("cus_1", "price_1", trial_days=7)
        self.assertEqual(result["subscription_id"], "sub_1")
        self.assertEqual(result["client_secret"], "secret")

    def test_check_usage_limits_within_limits_at_boundary(self):
        """At exact tier limit, within_limits is True (no overage)."""
        mgr = FikiriBillingManager()
        usage = UsageMetrics(
            emails_processed=500,
            leads_created=100,
            ai_responses_generated=200,
            month_year="2026-02",
        )
        result = mgr.check_usage_limits("1", SubscriptionTier.STARTER, usage)
        self.assertTrue(result["within_limits"])
        self.assertEqual(result["email_overage"], 0)
        self.assertEqual(result["lead_overage"], 0)
        self.assertEqual(result["ai_overage"], 0)
        self.assertEqual(result["total_overage_cost"], 0)

    def test_get_tier_limits_returns_limits_for_each_tier(self):
        """get_tier_limits returns SubscriptionLimits for known tiers."""
        mgr = FikiriBillingManager()
        for tier in SubscriptionTier:
            limits = mgr.get_tier_limits(tier)
            self.assertIsNotNone(limits)
            self.assertGreaterEqual(limits.emails_per_month, -1)
            self.assertGreaterEqual(limits.leads_storage, -1)
            self.assertGreaterEqual(limits.ai_responses_per_month, -1)

    @patch("core.billing_manager.STRIPE_AVAILABLE", False)
    def test_create_checkout_session_returns_empty_when_stripe_unavailable(self):
        """When Stripe is not available, create_checkout_session returns empty dict."""
        mgr = FikiriBillingManager()
        result = mgr.create_checkout_session(
            "price_123", customer_id=None,
            success_url="http://ok", cancel_url="http://cancel"
        )
        self.assertEqual(result, {})

    @patch("core.billing_manager.stripe")
    def test_cancel_subscription_at_period_end(self, mock_stripe):
        """cancel_subscription with at_period_end=True modifies subscription."""
        import core.billing_manager as bm
        bm.STRIPE_AVAILABLE = True
        mgr = FikiriBillingManager()
        sub = MagicMock(id="sub_1", status="active", cancel_at_period_end=True)
        mock_stripe.Subscription.modify.return_value = sub
        result = mgr.cancel_subscription("sub_1", at_period_end=True)
        self.assertEqual(result["id"], "sub_1")
        self.assertTrue(result["cancel_at_period_end"])
        mock_stripe.Subscription.modify.assert_called_once_with("sub_1", cancel_at_period_end=True)


if __name__ == "__main__":
    unittest.main()
