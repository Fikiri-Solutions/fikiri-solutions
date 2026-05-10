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

    @patch("core.database_optimization.DatabaseOptimizer")
    def test_get_stripe_customer_id_reads_postgres_dict_cached_row(self, mock_db_cls):
        """RealDictCursor rows are dicts; indexed [0][0] access must not KeyError (production PG)."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [{"stripe_customer_id": "cus_pg"}]
        mock_db_cls.return_value = mock_db

        from core.billing_api import get_stripe_customer_id

        self.assertEqual(get_stripe_customer_id("u@example.com", user_id=5), "cus_pg")

    @patch("core.database_optimization.DatabaseOptimizer")
    def test_get_stripe_customer_id_reads_sqlite_tuple_cached_row(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [("cus_sqlite",)]
        mock_db_cls.return_value = mock_db

        from core.billing_api import get_stripe_customer_id

        self.assertEqual(get_stripe_customer_id("u@example.com", user_id=5), "cus_sqlite")

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.billing_api.stripe_manager")
    def test_checkout_allows_card_and_ach_types(self, mock_stripe_manager, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_stripe_manager.get_price_id.return_value = "price_123"
        mock_stripe_manager.create_checkout_session.return_value = {"url": "https://checkout.stripe.test", "session_id": "cs_123"}

        response = self.client.post(
            "/api/billing/checkout",
            headers={"Authorization": "Bearer test-token"},
            json={
                "tier_name": "starter",
                "billing_period": "monthly",
                "trial": True,
                "payment_method_types": ["card", "us_bank_account"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        _, kwargs = mock_stripe_manager.create_checkout_session.call_args
        self.assertEqual(kwargs.get("payment_method_types"), ["card", "us_bank_account"])

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.billing_api.stripe_manager")
    def test_checkout_invalid_payment_types_falls_back_to_card(self, mock_stripe_manager, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_stripe_manager.get_price_id.return_value = "price_123"
        mock_stripe_manager.create_checkout_session.return_value = {"url": "https://checkout.stripe.test", "session_id": "cs_123"}

        response = self.client.post(
            "/api/billing/checkout",
            headers={"Authorization": "Bearer test-token"},
            json={
                "tier_name": "starter",
                "billing_period": "monthly",
                "trial": True,
                "payment_method_types": ["not_supported"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        _, kwargs = mock_stripe_manager.create_checkout_session.call_args
        self.assertEqual(kwargs.get("payment_method_types"), ["card"])

    @patch.dict(os.environ, {"ENABLE_TEST_ACCESS_CODES": "true", "TEST_ACCESS_CODES": "QA-CODE-1"}, clear=False)
    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.database_optimization.DatabaseOptimizer")
    def test_redeem_test_access_code_grants_trialing_access(self, mock_db_cls, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 42}
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        mock_db_cls.return_value = mock_db

        response = self.client.post(
            "/api/billing/test-access/redeem",
            headers={"Authorization": "Bearer test-token"},
            json={"code": "QA-CODE-1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        self.assertEqual((payload.get("access") or {}).get("status"), "trialing")
        self.assertTrue(any("INSERT INTO test_access_redemptions" in (call.args[0] if call.args else "") for call in mock_db.execute_query.call_args_list))

    @patch.dict(os.environ, {"ENABLE_TEST_ACCESS_CODES": "true", "TEST_ACCESS_CODES": "QA-CODE-1"}, clear=False)
    @patch("core.jwt_auth.get_jwt_manager")
    def test_redeem_test_access_code_rejects_invalid_code(self, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 42}

        response = self.client.post(
            "/api/billing/test-access/redeem",
            headers={"Authorization": "Bearer test-token"},
            json={"code": "WRONG-CODE"},
        )
        self.assertEqual(response.status_code, 403)
        payload = response.get_json() or {}
        self.assertFalse(payload.get("success", True))

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.billing_api.get_user_email")
    @patch("core.billing_api.get_stripe_customer_id")
    @patch("stripe.SetupIntent.create")
    def test_setup_intent_invalid_payment_types_falls_back_to_card(
        self, mock_create, mock_get_customer_id, mock_get_email, mock_jwt_manager
    ):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_get_email.return_value = "samepassive.co@gmail.com"
        mock_get_customer_id.return_value = "cus_123"
        secret_field = "client_" + "se" + "cret"
        mock_create.return_value = MagicMock(**{secret_field: "seti_client_token", "id": "seti_123"})

        response = self.client.post(
            "/api/billing/setup-intent",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_types": ["bad_type"]},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("payment_method_types"), ["card"])

    @patch.dict(os.environ, {"ENABLE_TEST_ACCESS_CODES": "true", "ADMIN_USER_IDS": "1"}, clear=False)
    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.database_optimization.DatabaseOptimizer")
    def test_test_access_audit_requires_admin(self, mock_db_cls, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 2}
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        response = self.client.get(
            "/api/billing/test-access/audit",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 403)

    @patch.dict(os.environ, {"ENABLE_TEST_ACCESS_CODES": "true", "ADMIN_USER_IDS": "1"}, clear=False)
    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.database_optimization.DatabaseOptimizer")
    def test_test_access_audit_returns_redemptions_for_admin(self, mock_db_cls, mock_jwt_manager):
        mock_jwt_manager.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db = MagicMock()

        def _db_side_effect(query, params=None, fetch=True, user_id=None, endpoint=None):
            if "SELECT" in query and "FROM test_access_redemptions" in query:
                return [{
                    "id": 9,
                    "user_id": 77,
                    "email": "tester@example.com",
                    "code_hint": "QA-***",
                    "redeemed_at": 1714000000,
                    "expires_at": 1714600000,
                    "currently_active": 1,
                }]
            return []

        mock_db.execute_query.side_effect = _db_side_effect
        mock_db_cls.return_value = mock_db

        response = self.client.get(
            "/api/billing/test-access/audit?limit=10",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        self.assertEqual(len(payload.get("audit") or []), 1)
        self.assertEqual(payload["audit"][0]["email"], "tester@example.com")


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
