"""Stripe webhook handler tests (payload handling + DB updates)."""

import unittest
from unittest.mock import patch, MagicMock


class TestStripeWebhookHandler(unittest.TestCase):
    @patch("core.stripe_webhooks.stripe")
    def test_handle_event_routes_known_type(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler

        handler = StripeWebhookHandler()
        with patch.object(handler, "handle_payment_succeeded", return_value={"status": "success"}) as mock_h:
            event = {"type": "invoice.payment_succeeded", "data": {"object": {}}}
            result = handler.handle_event(event)

        self.assertEqual(result.get("status"), "success")
        mock_h.assert_called_once()

    @patch("core.stripe_webhooks.stripe")
    def test_handle_event_unknown_type(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler

        handler = StripeWebhookHandler()
        event = {"type": "unknown.event", "data": {"object": {}}}
        result = handler.handle_event(event)
        self.assertEqual(result.get("status"), "unhandled")

    @patch("core.stripe_webhooks.stripe")
    def test_handle_payment_succeeded_calls_helpers(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler

        handler = StripeWebhookHandler()
        with patch.object(handler, "_update_user_subscription") as mock_update, \
            patch.object(handler, "_send_payment_confirmation_email") as mock_email, \
            patch.object(handler, "_track_payment_event") as mock_track:
            invoice = {
                "id": "in_1",
                "customer": "cus_1",
                "subscription": "sub_1",
                "amount_paid": 5000,
            }
            result = handler.handle_payment_succeeded(invoice)

        self.assertEqual(result.get("status"), "success")
        mock_update.assert_called_once_with("sub_1", "cus_1", "active")
        mock_email.assert_called_once_with("cus_1", "in_1", 5000)
        mock_track.assert_called_once()

    @patch("core.stripe_webhooks.stripe")
    def test_handle_payment_failed_calls_helpers(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler

        handler = StripeWebhookHandler()
        with patch.object(handler, "_update_user_subscription") as mock_update, \
            patch.object(handler, "_send_payment_failure_email") as mock_email, \
            patch.object(handler, "_track_payment_event") as mock_track:
            invoice = {
                "id": "in_2",
                "customer": "cus_2",
                "subscription": "sub_2",
                "amount_due": 2000,
            }
            result = handler.handle_payment_failed(invoice)

        self.assertEqual(result.get("status"), "success")
        mock_update.assert_called_once_with("sub_2", "cus_2", "past_due")
        mock_email.assert_called_once_with("cus_2", "in_2", 2000)
        mock_track.assert_called_once()

    @patch("core.stripe_webhooks.stripe")
    def test_update_user_subscription_happy_path(self, mock_stripe):
        from core import stripe_webhooks as sw
        from core.stripe_webhooks import StripeWebhookHandler

        # Force Stripe available
        sw.STRIPE_AVAILABLE = True

        # Mock Stripe objects
        price = MagicMock()
        price.product = "prod_1"
        price.recurring = MagicMock(interval="year")
        item = MagicMock()
        item.price = price
        subscription = MagicMock(
            items=MagicMock(data=[item]),
            current_period_start=1,
            current_period_end=2,
            trial_end=3,
            cancel_at_period_end=False,
        )
        customer = MagicMock(email="user@example.com")
        product = MagicMock(metadata={"tier": "growth"})

        mock_stripe.Subscription.retrieve.return_value = subscription
        mock_stripe.Customer.retrieve.return_value = customer
        mock_stripe.Product.retrieve.return_value = product

        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [{"id": 7}],  # user lookup
            None,  # insert/update subscriptions
            None,  # update users
        ]

        with patch("core.database_optimization.DatabaseOptimizer", return_value=mock_db):
            handler = StripeWebhookHandler()
            handler._update_user_subscription("sub_1", "cus_1", "active")

        # Ensure subscription insert and user update executed
        calls = [c[0][0] for c in mock_db.execute_query.call_args_list]
        self.assertTrue(any("INSERT OR REPLACE INTO subscriptions" in q for q in calls))
        self.assertTrue(any("UPDATE users SET stripe_customer_id" in q for q in calls))

    def test_handle_event_returns_error_when_event_is_none(self):
        from core.stripe_webhooks import StripeWebhookHandler
        handler = StripeWebhookHandler()
        result = handler.handle_event(None)
        self.assertEqual(result.get("status"), "error")
        self.assertIn("message", result)

    def test_handle_event_returns_error_when_event_empty(self):
        from core.stripe_webhooks import StripeWebhookHandler
        handler = StripeWebhookHandler()
        result = handler.handle_event({})
        self.assertIn(result.get("status"), ("error", "unhandled"))

    @patch("core.stripe_webhooks.stripe")
    def test_handle_subscription_updated_calls_update_and_returns_success(self, mock_stripe):
        from core.stripe_webhooks import StripeWebhookHandler
        handler = StripeWebhookHandler()
        with patch.object(handler, "_update_user_subscription") as mock_update:
            sub = {"id": "sub_1", "customer": "cus_1", "status": "active"}
            result = handler.handle_subscription_updated(sub)
        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("action"), "subscription_updated")
        mock_update.assert_called_once_with("sub_1", "cus_1", "active")

    @patch("core.stripe_webhooks.STRIPE_AVAILABLE", False)
    def test_verify_webhook_signature_returns_none_when_stripe_unavailable(self):
        from core.stripe_webhooks import StripeWebhookHandler
        handler = StripeWebhookHandler()
        result = handler.verify_webhook_signature(b"payload", "Stripe-Signature: x")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
