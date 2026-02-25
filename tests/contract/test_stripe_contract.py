"""Stripe contract tests (sandbox creds required)."""

import hmac
import json
import os
import time
import hashlib

import pytest

try:
    import stripe
except Exception:  # pragma: no cover - optional dependency
    stripe = None

from core.stripe_webhooks import StripeWebhookHandler


def _skip_if_missing_env():
    if not os.getenv("STRIPE_SECRET_KEY"):
        return True
    return False


@pytest.mark.contract
def test_stripe_create_customer():
    if stripe is None or _skip_if_missing_env():
        pytest.skip("Stripe not configured")

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    customer = stripe.Customer.create(email="contract-test@example.com")
    assert customer
    assert customer.get("id")


@pytest.mark.contract
def test_stripe_create_checkout_session():
    if stripe is None or _skip_if_missing_env():
        pytest.skip("Stripe not configured")

    price_id = os.getenv("STRIPE_TEST_PRICE_ID")
    if not price_id:
        pytest.skip("STRIPE_TEST_PRICE_ID not set")

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    assert session
    assert session.get("id")


@pytest.mark.contract
def test_stripe_webhook_signature_verification():
    if stripe is None:
        pytest.skip("Stripe library not available")

    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        pytest.skip("STRIPE_WEBHOOK_SECRET not set")

    payload = json.dumps({"id": "evt_test", "type": "customer.created", "data": {"object": {}}}).encode("utf-8")
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={signature}"

    handler = StripeWebhookHandler()
    event = handler.verify_webhook_signature(payload, sig_header)
    assert event
    assert event.get("type") == "customer.created"
