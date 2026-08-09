"""
Fikiri Solutions - Stripe Webhook Handlers
Handles Stripe webhook events for subscription management.

Dashboard / founder-driven ops (manual invoices, one-off customers, product
edits) are first-class: handlers must tolerate missing optional fields and
must not assume every object is tied to a website subscription or app user.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

# Optional Stripe integration
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from core.email_branding import wrap_html_email_body

logger = logging.getLogger(__name__)


def _stripe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a StripeObject or mapping.

    Stripe Python SDK v15+ no longer subclasses dict, so ``obj.get(key)`` raises
    ``AttributeError('get')`` and breaks webhook handling.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return obj[key]
    except (KeyError, TypeError, StopIteration):
        return default


def _invoice_subscription_id(invoice: Any) -> Optional[str]:
    """Resolve subscription id from legacy or Basil invoice payloads.

    API ``2025-03-31.basil+`` removed top-level ``invoice.subscription`` in favor of
    ``invoice.parent.subscription_details.subscription``. Manual/one-off invoices
    have neither.
    """
    legacy = _stripe_get(invoice, "subscription")
    if legacy:
        return legacy if isinstance(legacy, str) else _stripe_get(legacy, "id")

    parent = _stripe_get(invoice, "parent")
    if not parent:
        return None
    details = _stripe_get(parent, "subscription_details")
    if not details:
        return None
    subscription = _stripe_get(details, "subscription")
    if not subscription:
        return None
    return subscription if isinstance(subscription, str) else _stripe_get(subscription, "id")


def _ack(action: str, **fields: Any) -> Dict[str, Any]:
    """Successful webhook ack (including intentional no-ops for manual/out-of-band events)."""
    payload: Dict[str, Any] = {'status': 'success', 'action': action}
    payload.update(fields)
    return payload


def _soft_error(action: str, error: Exception, **fields: Any) -> Dict[str, Any]:
    """Log and ack with error details without raising (keeps Stripe delivery healthy)."""
    logger.error("Error handling %s: %s", action, error)
    payload: Dict[str, Any] = {'status': 'error', 'action': action, 'error': str(error)}
    payload.update(fields)
    return payload


class StripeWebhookHandler:
    """Handles Stripe webhook events"""
    
    def __init__(self):
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self._billing_from_email = os.getenv('BILLING_FROM_EMAIL', 'info@fikirisolutions.com')
    
    def _get_customer_email(self, customer_id: str) -> str:
        """Get customer email from Stripe. Returns empty string if unavailable."""
        if not STRIPE_AVAILABLE or not customer_id:
            return ''
        try:
            customer = stripe.Customer.retrieve(customer_id)
            if hasattr(customer, 'email') and customer.email:
                return customer.email or ''
            return _stripe_get(customer, 'email') or ''
        except Exception as e:
            logger.warning(f"Could not get customer email for {customer_id}: {e}")
            return ''
    
    def _send_billing_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send transactional billing email via SendGrid, SES, or SMTP. Returns True if sent or attempted."""
        if not to_email or '@' not in to_email:
            logger.warning("No valid recipient for billing email")
            return False
        try:
            sendgrid_key = os.getenv('SENDGRID_API_KEY')
            if sendgrid_key:
                return self._send_billing_via_sendgrid(to_email, subject, body)
            if os.getenv('AWS_ACCESS_KEY_ID'):
                return self._send_billing_via_ses(to_email, subject, body)
            if os.getenv('SMTP_SERVER'):
                return self._send_billing_via_smtp(to_email, subject, body)
            logger.info(f"Billing email (no provider configured): to={to_email} subject={subject!r}")
            return False
        except Exception as e:
            logger.error(f"Failed to send billing email to {to_email}: {e}")
            return False
    
    def _send_billing_via_sendgrid(self, to_email: str, subject: str, body: str) -> bool:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
            mail = Mail(from_email=self._billing_from_email, to_emails=to_email, subject=subject, html_content=body)
            sg.send(mail)
            logger.info(f"Billing email sent via SendGrid to {to_email}")
            return True
        except ImportError:
            logger.warning("SendGrid not available")
            return False
        except Exception as e:
            logger.error(f"SendGrid billing email failed: {e}")
            return False
    
    def _send_billing_via_ses(self, to_email: str, subject: str, body: str) -> bool:
        try:
            import boto3
            ses = boto3.client('ses')
            ses.send_email(
                Source=self._billing_from_email,
                Destination={'ToAddresses': [to_email]},
                Message={'Subject': {'Data': subject}, 'Body': {'Text': {'Data': body}}}
            )
            logger.info(f"Billing email sent via SES to {to_email}")
            return True
        except ImportError:
            logger.warning("boto3 not available")
            return False
        except Exception as e:
            logger.error(f"SES billing email failed: {e}")
            return False
    
    def _send_billing_via_smtp(self, to_email: str, subject: str, body: str) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USERNAME')
            smtp_pass = os.getenv('SMTP_PASSWORD')
            msg = MIMEText(body, 'html')
            msg['Subject'] = subject
            msg['From'] = self._billing_from_email
            msg['To'] = to_email
            with smtplib.SMTP(smtp_server, smtp_port) as s:
                if smtp_user and smtp_pass:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                s.sendmail(self._billing_from_email, [to_email], msg.as_string())
            logger.info(f"Billing email sent via SMTP to {to_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP billing email failed: {e}")
            return False
    
    def verify_webhook_signature(self, payload: bytes, sig_header: str):
        """Verify webhook signature and construct event"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping webhook verification")
            return None
            
        try:
            if STRIPE_AVAILABLE:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, self.webhook_secret
                )
                return event
            else:
                logger.warning("Stripe not available, skipping webhook verification")
                return None
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            raise
    
    def process_verified_event(self, event) -> Dict[str, Any]:
        """Process a signature-verified Stripe event with event.id deduplication."""
        if not event:
            return {'status': 'error', 'message': 'No event data'}

        event_id = _stripe_get(event, 'id')
        if not event_id:
            return {'status': 'error', 'message': 'Missing event id'}

        event_type = _stripe_get(event, 'type') or ''
        claim = self._claim_stripe_webhook_event(event_id, event_type)
        if claim == 'duplicate':
            logger.info("Stripe webhook duplicate ignored: %s", event_id)
            return {
                'status': 'duplicate',
                'event_id': event_id,
                'message': 'Event already processed',
            }
        if claim != 'claimed':
            return {'status': 'error', 'message': 'Failed to record webhook event'}

        result = self.handle_event(event)
        if result.get('status') == 'error':
            self._complete_stripe_webhook_event(event_id, 'failed', result)
        else:
            self._complete_stripe_webhook_event(event_id, 'completed', result)
        return result

    def _claim_stripe_webhook_event(self, event_id: str, event_type: str) -> str:
        """Return 'claimed', 'duplicate', or 'failed'."""
        from core.database_optimization import db_optimizer

        db = db_optimizer
        try:
            inserted = db.execute_query(
                """
                INSERT INTO stripe_webhook_events (stripe_event_id, event_type, status)
                VALUES (?, ?, 'processing')
                ON CONFLICT (stripe_event_id) DO NOTHING
                """,
                (event_id, event_type),
                fetch=False,
            )
            if inserted and inserted > 0:
                return 'claimed'

            rows = db.execute_query(
                "SELECT status FROM stripe_webhook_events WHERE stripe_event_id = ? LIMIT 1",
                (event_id,),
            )
            if not rows:
                return 'failed'

            row = rows[0]
            status = row.get('status') if hasattr(row, 'keys') else row[0]
            if status == 'failed':
                updated = db.execute_query(
                    """
                    UPDATE stripe_webhook_events
                    SET status = 'processing',
                        event_type = ?,
                        processed_at = NULL,
                        result_json = NULL
                    WHERE stripe_event_id = ? AND status = 'failed'
                    """,
                    (event_type, event_id),
                    fetch=False,
                )
                if updated and updated > 0:
                    return 'claimed'
            return 'duplicate'
        except Exception as e:
            logger.error("Stripe webhook claim failed for %s: %s", event_id, e)
            return 'failed'

    def _complete_stripe_webhook_event(
        self,
        event_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        from core.database_optimization import db_optimizer

        db = db_optimizer
        try:
            db.execute_query(
                """
                UPDATE stripe_webhook_events
                SET status = ?,
                    result_json = ?,
                    processed_at = CURRENT_TIMESTAMP
                WHERE stripe_event_id = ?
                """,
                (status, json.dumps(result) if result is not None else None, event_id),
                fetch=False,
            )
        except Exception as e:
            logger.error("Stripe webhook completion update failed for %s: %s", event_id, e)

    def handle_event(self, event) -> Dict[str, Any]:
        """Route webhook events to appropriate handlers"""
        if not event:
            return {'status': 'error', 'message': 'No event data'}

        event_type = _stripe_get(event, 'type') or ''
        data = _stripe_get(event, 'data') or {}
        obj = _stripe_get(data, 'object')

        handlers = {
            'customer.subscription.created': self.handle_subscription_created,
            'customer.subscription.updated': self.handle_subscription_updated,
            'customer.subscription.deleted': self.handle_subscription_deleted,
            'customer.subscription.trial_will_end': self.handle_trial_will_end,
            'invoice.payment_succeeded': self.handle_payment_succeeded,
            'invoice.payment_failed': self.handle_payment_failed,
            'invoice.created': self.handle_invoice_created,
            'customer.created': self.handle_customer_created,
            'customer.updated': self.handle_customer_updated,
            'payment_method.attached': self.handle_payment_method_attached,
            'checkout.session.completed': self.handle_checkout_completed,
            'checkout.session.expired': self.handle_checkout_expired,
            'checkout.session.async_payment_succeeded': self.handle_checkout_async_payment_succeeded,
            'checkout.session.async_payment_failed': self.handle_checkout_async_payment_failed,
            'setup_intent.succeeded': self.handle_setup_intent_succeeded,
            'setup_intent.setup_failed': self.handle_setup_intent_failed,
            'payment_intent.succeeded': self.handle_payment_intent_succeeded,
            'payment_intent.payment_failed': self.handle_payment_intent_failed,
            'charge.succeeded': self.handle_charge_succeeded,
            'charge.refunded': self.handle_charge_refunded,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(obj)
        logger.info("Unhandled Stripe event type (acked): %s", event_type)
        return {'status': 'unhandled', 'event_type': event_type}

    def handle_subscription_created(self, subscription: Any) -> Dict[str, Any]:
        """Handle new subscription creation"""
        try:
            subscription_id = _stripe_get(subscription, 'id')
            customer_id = _stripe_get(subscription, 'customer')
            status = _stripe_get(subscription, 'status') or 'incomplete'

            if not subscription_id or not customer_id:
                logger.info(
                    "Skipping subscription.created side effects: missing id/customer "
                    "(manual or incomplete Dashboard object)"
                )
                return _ack(
                    'subscription_created_skipped',
                    subscription_id=subscription_id,
                    customer_id=customer_id,
                    reason='missing_required_fields',
                )

            logger.info(f"New subscription created: {subscription_id} for customer {customer_id}")
            self._update_user_subscription(subscription_id, customer_id, status)
            self._send_welcome_email(customer_id, subscription_id)
            self._track_subscription_event('created', subscription_id, customer_id)
            return _ack(
                'subscription_created',
                subscription_id=subscription_id,
                customer_id=customer_id,
            )
        except Exception as e:
            return _soft_error('subscription_created', e)

    def handle_subscription_updated(self, subscription: Any) -> Dict[str, Any]:
        """Handle subscription updates"""
        try:
            subscription_id = _stripe_get(subscription, 'id')
            customer_id = _stripe_get(subscription, 'customer')
            status = _stripe_get(subscription, 'status')

            if not subscription_id or not customer_id:
                logger.info("Skipping subscription.updated side effects: missing id/customer")
                return _ack(
                    'subscription_updated_skipped',
                    subscription_id=subscription_id,
                    customer_id=customer_id,
                    reason='missing_required_fields',
                )

            logger.info(f"Subscription updated: {subscription_id} - Status: {status}")
            self._update_user_subscription(subscription_id, customer_id, status or 'incomplete')

            if status == 'active':
                self._handle_subscription_activated(subscription_id, customer_id)
            elif status == 'past_due':
                self._handle_subscription_past_due(subscription_id, customer_id)
            elif status == 'canceled':
                self._handle_subscription_canceled(subscription_id, customer_id)

            self._track_subscription_event('updated', subscription_id, customer_id)
            return _ack(
                'subscription_updated',
                subscription_id=subscription_id,
                customer_id=customer_id,
                new_status=status,
            )
        except Exception as e:
            return _soft_error('subscription_updated', e)

    def handle_subscription_deleted(self, subscription: Any) -> Dict[str, Any]:
        """Handle subscription deletion"""
        try:
            subscription_id = _stripe_get(subscription, 'id')
            customer_id = _stripe_get(subscription, 'customer')

            if not subscription_id or not customer_id:
                logger.info("Skipping subscription.deleted side effects: missing id/customer")
                return _ack(
                    'subscription_deleted_skipped',
                    subscription_id=subscription_id,
                    customer_id=customer_id,
                    reason='missing_required_fields',
                )

            logger.info(f"Subscription deleted: {subscription_id}")
            self._update_user_subscription(subscription_id, customer_id, 'canceled')
            self._send_cancellation_email(customer_id, subscription_id)
            self._track_subscription_event('deleted', subscription_id, customer_id)
            return _ack(
                'subscription_deleted',
                subscription_id=subscription_id,
                customer_id=customer_id,
            )
        except Exception as e:
            return _soft_error('subscription_deleted', e)

    def handle_trial_will_end(self, subscription: Any) -> Dict[str, Any]:
        """Handle trial ending notification"""
        try:
            subscription_id = _stripe_get(subscription, 'id')
            customer_id = _stripe_get(subscription, 'customer')
            trial_end = _stripe_get(subscription, 'trial_end')

            if not subscription_id or not customer_id:
                logger.info("Skipping trial_will_end side effects: missing id/customer")
                return _ack(
                    'trial_ending_skipped',
                    subscription_id=subscription_id,
                    customer_id=customer_id,
                    reason='missing_required_fields',
                )

            logger.info(f"Trial ending soon for subscription: {subscription_id}")
            self._send_trial_ending_email(customer_id, subscription_id, trial_end)
            self._track_subscription_event('trial_ending', subscription_id, customer_id)
            return _ack(
                'trial_ending',
                subscription_id=subscription_id,
                customer_id=customer_id,
                trial_end=trial_end,
            )
        except Exception as e:
            return _soft_error('trial_ending', e)

    def handle_payment_succeeded(self, invoice: Any) -> Dict[str, Any]:
        """Handle successful payment (subscription or manual/one-off invoice)."""
        try:
            invoice_id = _stripe_get(invoice, 'id')
            customer_id = _stripe_get(invoice, 'customer')
            subscription_id = _invoice_subscription_id(invoice)
            amount_paid = _stripe_get(invoice, 'amount_paid') or 0

            logger.info(
                "Payment succeeded: Invoice %s - Amount: $%s (subscription=%s)",
                invoice_id,
                amount_paid / 100,
                subscription_id or 'none',
            )

            if subscription_id and customer_id:
                self._update_user_subscription(subscription_id, customer_id, 'active')

            self._send_payment_confirmation_email(customer_id, invoice_id, amount_paid)
            self._track_payment_event('succeeded', invoice_id, customer_id, amount_paid)
            return _ack(
                'payment_succeeded',
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
                amount_paid=amount_paid,
            )
        except Exception as e:
            return _soft_error('payment_succeeded', e)

    def handle_payment_failed(self, invoice: Any) -> Dict[str, Any]:
        """Handle failed payment (subscription or manual/one-off invoice)."""
        try:
            invoice_id = _stripe_get(invoice, 'id')
            customer_id = _stripe_get(invoice, 'customer')
            subscription_id = _invoice_subscription_id(invoice)
            amount_due = _stripe_get(invoice, 'amount_due') or 0

            logger.warning(
                "Payment failed: Invoice %s - Amount: $%s (subscription=%s)",
                invoice_id,
                amount_due / 100,
                subscription_id or 'none',
            )

            if subscription_id and customer_id:
                self._update_user_subscription(subscription_id, customer_id, 'past_due')

            self._send_payment_failure_email(customer_id, invoice_id, amount_due)
            self._track_payment_event('failed', invoice_id, customer_id, amount_due)
            return _ack(
                'payment_failed',
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
                amount_due=amount_due,
            )
        except Exception as e:
            return _soft_error('payment_failed', e)

    def handle_invoice_created(self, invoice: Any) -> Dict[str, Any]:
        """Handle invoice creation (Dashboard manual invoices included)."""
        try:
            invoice_id = _stripe_get(invoice, 'id')
            customer_id = _stripe_get(invoice, 'customer')
            subscription_id = _invoice_subscription_id(invoice)
            amount_due = _stripe_get(invoice, 'amount_due') or 0

            logger.info(
                "Invoice created: %s - Amount: $%s (subscription=%s)",
                invoice_id,
                amount_due / 100,
                subscription_id or 'none',
            )
            self._track_invoice_event('created', invoice_id, customer_id, amount_due)
            return _ack(
                'invoice_created',
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
                amount_due=amount_due,
            )
        except Exception as e:
            return _soft_error('invoice_created', e)

    def handle_customer_created(self, customer: Any) -> Dict[str, Any]:
        """Handle customer creation (website signup or Dashboard-created)."""
        try:
            customer_id = _stripe_get(customer, 'id')
            email = _stripe_get(customer, 'email')
            name = _stripe_get(customer, 'name')
            logger.info(f"New customer created: {customer_id} - {email}")
            self._track_customer_event('created', customer_id, email)
            return _ack(
                'customer_created',
                customer_id=customer_id,
                email=email,
                name=name,
            )
        except Exception as e:
            return _soft_error('customer_created', e)

    def handle_customer_updated(self, customer: Any) -> Dict[str, Any]:
        """Handle customer updates"""
        try:
            customer_id = _stripe_get(customer, 'id')
            email = _stripe_get(customer, 'email')
            logger.info(f"Customer updated: {customer_id} - {email}")
            self._track_customer_event('updated', customer_id, email)
            return _ack(
                'customer_updated',
                customer_id=customer_id,
                email=email,
            )
        except Exception as e:
            return _soft_error('customer_updated', e)

    def handle_payment_method_attached(self, payment_method: Any) -> Dict[str, Any]:
        """Handle payment method attachment"""
        try:
            payment_method_id = _stripe_get(payment_method, 'id')
            customer_id = _stripe_get(payment_method, 'customer')
            logger.info(f"Payment method attached: {payment_method_id} to customer {customer_id}")
            self._track_payment_method_event('attached', payment_method_id, customer_id)
            return _ack(
                'payment_method_attached',
                payment_method_id=payment_method_id,
                customer_id=customer_id,
            )
        except Exception as e:
            return _soft_error('payment_method_attached', e)

    def handle_checkout_completed(self, session: Any) -> Dict[str, Any]:
        """Handle checkout session completion"""
        try:
            session_id = _stripe_get(session, 'id')
            customer_id = _stripe_get(session, 'customer')
            subscription_id = _stripe_get(session, 'subscription')
            logger.info(f"Checkout completed: Session {session_id} - Customer {customer_id}")
            self._track_checkout_event('completed', session_id, customer_id, subscription_id)
            return _ack(
                'checkout_completed',
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
            )
        except Exception as e:
            return _soft_error('checkout_completed', e)

    def handle_checkout_expired(self, session: Any) -> Dict[str, Any]:
        """Handle checkout session expiration"""
        try:
            session_id = _stripe_get(session, 'id')
            customer_id = _stripe_get(session, 'customer')
            logger.info(f"Checkout expired: Session {session_id}")
            self._track_checkout_event('expired', session_id, customer_id)
            return _ack(
                'checkout_expired',
                session_id=session_id,
                customer_id=customer_id,
            )
        except Exception as e:
            return _soft_error('checkout_expired', e)

    def handle_checkout_async_payment_succeeded(self, session: Any) -> Dict[str, Any]:
        """Handle asynchronous checkout payment success (common with ACH)."""
        try:
            session_id = _stripe_get(session, 'id')
            customer_id = _stripe_get(session, 'customer')
            subscription_id = _stripe_get(session, 'subscription')
            logger.info(f"Checkout async payment succeeded: Session {session_id} - Customer {customer_id}")
            if subscription_id and customer_id:
                self._update_user_subscription(subscription_id, customer_id, 'active')
            self._track_checkout_event('async_payment_succeeded', session_id, customer_id, subscription_id)
            return _ack(
                'checkout_async_payment_succeeded',
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
            )
        except Exception as e:
            return _soft_error('checkout_async_payment_succeeded', e)

    def handle_checkout_async_payment_failed(self, session: Any) -> Dict[str, Any]:
        """Handle asynchronous checkout payment failure (common with ACH)."""
        try:
            session_id = _stripe_get(session, 'id')
            customer_id = _stripe_get(session, 'customer')
            subscription_id = _stripe_get(session, 'subscription')
            logger.warning(f"Checkout async payment failed: Session {session_id} - Customer {customer_id}")
            if subscription_id and customer_id:
                self._update_user_subscription(subscription_id, customer_id, 'past_due')
            self._track_checkout_event('async_payment_failed', session_id, customer_id, subscription_id)
            return _ack(
                'checkout_async_payment_failed',
                session_id=session_id,
                customer_id=customer_id,
                subscription_id=subscription_id,
            )
        except Exception as e:
            return _soft_error('checkout_async_payment_failed', e)

    def handle_setup_intent_succeeded(self, setup_intent: Any) -> Dict[str, Any]:
        """Handle successful setup intent (card or bank account added)."""
        try:
            setup_intent_id = _stripe_get(setup_intent, 'id')
            customer_id = _stripe_get(setup_intent, 'customer')
            payment_method = _stripe_get(setup_intent, 'payment_method')
            logger.info(f"Setup intent succeeded: {setup_intent_id} for customer {customer_id}")
            return _ack(
                'setup_intent_succeeded',
                setup_intent_id=setup_intent_id,
                customer_id=customer_id,
                payment_method_id=payment_method,
            )
        except Exception as e:
            return _soft_error('setup_intent_succeeded', e)

    def handle_setup_intent_failed(self, setup_intent: Any) -> Dict[str, Any]:
        """Handle failed setup intent (card or bank account setup failed)."""
        try:
            setup_intent_id = _stripe_get(setup_intent, 'id')
            customer_id = _stripe_get(setup_intent, 'customer')
            last_setup_error = _stripe_get(setup_intent, 'last_setup_error') or {}
            error_message = _stripe_get(last_setup_error, 'message', 'Setup failed')
            logger.warning(f"Setup intent failed: {setup_intent_id} for customer {customer_id} - {error_message}")
            return _ack(
                'setup_intent_failed',
                setup_intent_id=setup_intent_id,
                customer_id=customer_id,
                error_message=error_message,
            )
        except Exception as e:
            return _soft_error('setup_intent_failed', e)

    def handle_payment_intent_succeeded(self, payment_intent: Any) -> Dict[str, Any]:
        """Handle successful payment intent (card verification)"""
        try:
            payment_intent_id = _stripe_get(payment_intent, 'id')
            customer_id = _stripe_get(payment_intent, 'customer')
            amount = _stripe_get(payment_intent, 'amount') or 0
            metadata = _stripe_get(payment_intent, 'metadata') or {}
            is_verification = _stripe_get(metadata, 'verification', 'false') == 'true' or amount <= 100

            if is_verification:
                logger.info(f"Card verification succeeded: Payment Intent {payment_intent_id} - Amount: ${amount/100}")
                if amount == 100 and STRIPE_AVAILABLE and payment_intent_id:
                    try:
                        refund = stripe.Refund.create(
                            payment_intent=payment_intent_id,
                            amount=100,
                            reason='requested_by_customer',
                            metadata={'reason': 'card_verification', 'original_payment_intent': payment_intent_id}
                        )
                        logger.info(f"Refunded $1 verification charge: Refund {refund.id}")
                    except Exception as e:
                        logger.error(f"Failed to refund verification charge: {e}")

            return _ack(
                'payment_intent_succeeded',
                payment_intent_id=payment_intent_id,
                customer_id=customer_id,
                is_verification=is_verification,
                amount=amount,
            )
        except Exception as e:
            return _soft_error('payment_intent_succeeded', e)

    def handle_payment_intent_failed(self, payment_intent: Any) -> Dict[str, Any]:
        """Handle failed payment intent (card verification failed)"""
        try:
            payment_intent_id = _stripe_get(payment_intent, 'id')
            customer_id = _stripe_get(payment_intent, 'customer')
            last_payment_error = _stripe_get(payment_intent, 'last_payment_error') or {}
            error_message = _stripe_get(last_payment_error, 'message', 'Payment failed')
            logger.warning(f"Card verification failed: Payment Intent {payment_intent_id} - {error_message}")
            self._track_payment_event('verification_failed', payment_intent_id, customer_id, 0)
            return _ack(
                'payment_intent_failed',
                payment_intent_id=payment_intent_id,
                customer_id=customer_id,
                error_message=error_message,
            )
        except Exception as e:
            return _soft_error('payment_intent_failed', e)

    def handle_charge_succeeded(self, charge: Any) -> Dict[str, Any]:
        """Handle successful charge (including verification charges)"""
        try:
            charge_id = _stripe_get(charge, 'id')
            customer_id = _stripe_get(charge, 'customer')
            amount = _stripe_get(charge, 'amount') or 0
            metadata = _stripe_get(charge, 'metadata') or {}
            is_verification = _stripe_get(metadata, 'verification', 'false') == 'true' or amount <= 100
            if is_verification:
                logger.info(f"Verification charge succeeded: Charge {charge_id} - Amount: ${amount/100}")
            return _ack(
                'charge_succeeded',
                charge_id=charge_id,
                customer_id=customer_id,
                is_verification=is_verification,
                amount=amount,
            )
        except Exception as e:
            return _soft_error('charge_succeeded', e)

    def handle_charge_refunded(self, charge: Any) -> Dict[str, Any]:
        """Handle refunded charge (verification refund)"""
        try:
            charge_id = _stripe_get(charge, 'id')
            customer_id = _stripe_get(charge, 'customer')
            amount_refunded = _stripe_get(charge, 'amount_refunded', 0) or 0
            metadata = _stripe_get(charge, 'metadata') or {}
            if _stripe_get(metadata, 'reason') == 'card_verification':
                logger.info(f"Verification charge refunded: Charge {charge_id} - Amount: ${amount_refunded/100}")
            return _ack(
                'charge_refunded',
                charge_id=charge_id,
                customer_id=customer_id,
                amount_refunded=amount_refunded,
            )
        except Exception as e:
            return _soft_error('charge_refunded', e)

    # Private helper methods
    def _update_user_subscription(self, subscription_id: str, customer_id: str, status: str):
        """Update user subscription in database - persists webhook data"""
        from core.database_optimization import db_optimizer
        db = db_optimizer
        
        try:
            # Get subscription details from Stripe
            if not STRIPE_AVAILABLE:
                logger.warning("Stripe not available, cannot update subscription")
                return
            
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get customer details to find user
            customer = stripe.Customer.retrieve(customer_id)
            user_email = customer.email
            
            if not user_email:
                logger.info(
                    "No email on Stripe customer %s — skipping SaaS subscription sync "
                    "(common for Dashboard-only / manual customers)",
                    customer_id,
                )
                return
            
            # Find user by email
            user_result = db.execute_query("SELECT id FROM users WHERE email = ?", (user_email,))
            if not user_result or len(user_result) == 0 or not user_result[0]:
                logger.info(
                    "No Fikiri app user for Stripe customer email %s — skipping SaaS sync "
                    "(manual/Dashboard billing outside website subscriptions)",
                    user_email,
                )
                return
            
            user_row = user_result[0]
            user_id = user_row[0] if isinstance(user_row, tuple) else user_row.get('id') if isinstance(user_row, dict) else None
            if not user_id:
                logger.info("Invalid user row for email %s — skipping SaaS sync", user_email)
                return
            
            # Get tier from product metadata
            tier = 'starter'  # default
            billing_period = 'monthly'  # default
            
            if subscription.items.data and len(subscription.items.data) > 0:
                product_id = subscription.items.data[0].price.product
                try:
                    product = stripe.Product.retrieve(product_id)
                    tier = _stripe_get(product.metadata, 'tier', 'starter')                    
                    # Get billing period from price
                    price = subscription.items.data[0].price
                    if price.recurring:
                        billing_period = price.recurring.interval  # 'month' or 'year'
                        if billing_period == 'year':
                            billing_period = 'annual'
                except Exception as e:
                    logger.warning(f"Failed to get product details: {e}")
            
            # Update or insert subscription in database
            db.upsert_stripe_subscription_row(
                user_id,
                customer_id,
                subscription_id,
                status,
                tier,
                billing_period,
                subscription.current_period_start,
                subscription.current_period_end,
                subscription.trial_end,
                subscription.cancel_at_period_end or False,
            )
            
            # Update customer_id in users table
            db.execute_query(
                "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                (customer_id, user_id),
                fetch=False
            )
            
            logger.info(f"✅ Updated subscription {subscription_id} in database for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update subscription in database: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _send_welcome_email(self, customer_id: str, subscription_id: str):
        """Send welcome email to new subscriber"""
        email = self._get_customer_email(customer_id)
        if not email:
            logger.info(f"Skipping welcome email: no email for customer {customer_id}")
            return
        inner = f"<p>Welcome to Fikiri Solutions! Your subscription is active.</p><p>Subscription ID: {subscription_id}</p>"
        self._send_billing_email(email, "Welcome to Fikiri Solutions", wrap_html_email_body(inner))
    
    def _send_cancellation_email(self, customer_id: str, subscription_id: str):
        """Send cancellation email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        inner = f"<p>Your Fikiri subscription has been canceled. We're sorry to see you go.</p><p>Subscription ID: {subscription_id}</p>"
        self._send_billing_email(email, "Your Fikiri subscription has been canceled", wrap_html_email_body(inner))
    
    def _send_trial_ending_email(self, customer_id: str, subscription_id: str, trial_end: int):
        """Send trial ending email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        end_str = datetime.utcfromtimestamp(trial_end).strftime('%Y-%m-%d') if trial_end else 'soon'
        inner = f"<p>Your Fikiri trial ends on {end_str}. Add a payment method to continue using the service.</p>"
        self._send_billing_email(email, "Your Fikiri trial is ending soon", wrap_html_email_body(inner))
    
    def _send_payment_confirmation_email(self, customer_id: str, invoice_id: str, amount_paid: int):
        """Send payment confirmation email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        amount_str = f"${amount_paid / 100:.2f}" if amount_paid is not None else "—"
        inner = f"<p>Thank you for your payment. We've received {amount_str} for invoice {invoice_id}.</p>"
        self._send_billing_email(email, "Payment received – Fikiri Solutions", wrap_html_email_body(inner))
    
    def _send_payment_failure_email(self, customer_id: str, invoice_id: str, amount_due: int):
        """Send payment failure email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        amount_str = f"${amount_due / 100:.2f}" if amount_due is not None else "—"
        inner = f"<p>We couldn't process your payment for invoice {invoice_id}. Amount due: {amount_str}. Please update your payment method.</p>"
        self._send_billing_email(email, "Payment failed – action needed", wrap_html_email_body(inner))
    
    def _handle_subscription_activated(self, subscription_id: str, customer_id: str):
        """Handle subscription activation (status already persisted by caller)."""
        logger.info(f"Subscription activated: {subscription_id}")
    
    def _handle_subscription_past_due(self, subscription_id: str, customer_id: str):
        """Handle subscription past due (status already persisted by caller)."""
        logger.info(f"Subscription past due: {subscription_id}")
    
    def _handle_subscription_canceled(self, subscription_id: str, customer_id: str):
        """Handle subscription cancellation (status already persisted by caller)."""
        logger.info(f"Subscription canceled: {subscription_id}")
    
    def _track_subscription_event(self, event_type: str, subscription_id: str, customer_id: str):
        """Log subscription events (extend later for analytics)."""
        logger.info(f"Tracking subscription event: {event_type} for {subscription_id}")
    
    def _track_payment_event(self, event_type: str, invoice_id: str, customer_id: str, amount: int):
        """Log payment events (extend later for analytics)."""
        logger.info(f"Tracking payment event: {event_type} for invoice {invoice_id}")
    
    def _track_invoice_event(self, event_type: str, invoice_id: str, customer_id: str, amount: int):
        """Log invoice events (extend later for analytics)."""
        logger.info(f"Tracking invoice event: {event_type} for invoice {invoice_id}")
    
    def _track_customer_event(self, event_type: str, customer_id: str, email: str):
        """Log customer events (extend later for analytics)."""
        logger.info(f"Tracking customer event: {event_type} for customer {customer_id}")
    
    def _track_payment_method_event(self, event_type: str, payment_method_id: str, customer_id: str):
        """Log payment method events (extend later for analytics)."""
        logger.info(f"Tracking payment method event: {event_type} for {payment_method_id}")
    
    def _track_checkout_event(self, event_type: str, session_id: str, customer_id: str, subscription_id: str = None):
        """Log checkout events (extend later for analytics)."""
        logger.info(f"Tracking checkout event: {event_type} for session {session_id}")
