"""
Fikiri Solutions - Stripe Webhook Handlers
Handles Stripe webhook events for subscription management
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

# Optional Stripe integration
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

try:
    from core.billing_manager import FikiriBillingManager, SubscriptionStatus
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    FikiriBillingManager = None
    SubscriptionStatus = None

logger = logging.getLogger(__name__)

class StripeWebhookHandler:
    """Handles Stripe webhook events"""
    
    def __init__(self):
        if BILLING_AVAILABLE:
            self.billing_manager = FikiriBillingManager()
        else:
            self.billing_manager = None
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self._billing_from_email = os.getenv('BILLING_FROM_EMAIL', 'billing@fikirisolutions.com')
    
    def _get_customer_email(self, customer_id: str) -> str:
        """Get customer email from Stripe. Returns empty string if unavailable."""
        if not STRIPE_AVAILABLE or not customer_id:
            return ''
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return (customer.email or '') if hasattr(customer, 'email') else (customer.get('email') or '')
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
    
    def handle_event(self, event) -> Dict[str, Any]:
        """Route webhook events to appropriate handlers"""
        if not event:
            return {'status': 'error', 'message': 'No event data'}
            
        event_type = event['type']
        
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
            'payment_intent.succeeded': self.handle_payment_intent_succeeded,
            'payment_intent.payment_failed': self.handle_payment_intent_failed,
            'charge.succeeded': self.handle_charge_succeeded,
            'charge.refunded': self.handle_charge_refunded,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(event['data']['object'])
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            return {'status': 'unhandled', 'event_type': event_type}
    
    def handle_subscription_created(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle new subscription creation"""
        try:
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            status = subscription['status']
            
            logger.info(f"New subscription created: {subscription_id} for customer {customer_id}")
            
            # Update user subscription in database
            self._update_user_subscription(subscription_id, customer_id, status)
            
            # Send welcome email
            self._send_welcome_email(customer_id, subscription_id)
            
            # Track subscription creation
            self._track_subscription_event('created', subscription_id, customer_id)
            
            return {
                'status': 'success',
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'action': 'subscription_created'
            }
            
        except Exception as e:
            logger.error(f"Error handling subscription created: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_subscription_updated(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription updates"""
        try:
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            status = subscription['status']
            
            logger.info(f"Subscription updated: {subscription_id} - Status: {status}")
            
            # Update user subscription in database
            self._update_user_subscription(subscription_id, customer_id, status)
            
            # Handle specific status changes
            if status == 'active':
                self._handle_subscription_activated(subscription_id, customer_id)
            elif status == 'past_due':
                self._handle_subscription_past_due(subscription_id, customer_id)
            elif status == 'canceled':
                self._handle_subscription_canceled(subscription_id, customer_id)
            
            # Track subscription update
            self._track_subscription_event('updated', subscription_id, customer_id)
            
            return {
                'status': 'success',
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'action': 'subscription_updated',
                'new_status': status
            }
            
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_subscription_deleted(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription deletion"""
        try:
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            
            logger.info(f"Subscription deleted: {subscription_id}")
            
            # Update user subscription in database
            self._update_user_subscription(subscription_id, customer_id, 'canceled')
            
            # Send cancellation email
            self._send_cancellation_email(customer_id, subscription_id)
            
            # Track subscription deletion
            self._track_subscription_event('deleted', subscription_id, customer_id)
            
            return {
                'status': 'success',
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'action': 'subscription_deleted'
            }
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_trial_will_end(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle trial ending notification"""
        try:
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            trial_end = subscription['trial_end']
            
            logger.info(f"Trial ending soon for subscription: {subscription_id}")
            
            # Send trial ending email
            self._send_trial_ending_email(customer_id, subscription_id, trial_end)
            
            # Track trial ending event
            self._track_subscription_event('trial_ending', subscription_id, customer_id)
            
            return {
                'status': 'success',
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'action': 'trial_ending',
                'trial_end': trial_end
            }
            
        except Exception as e:
            logger.error(f"Error handling trial will end: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_payment_succeeded(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment"""
        try:
            invoice_id = invoice['id']
            customer_id = invoice['customer']
            subscription_id = invoice['subscription']
            amount_paid = invoice['amount_paid']
            
            logger.info(f"Payment succeeded: Invoice {invoice_id} - Amount: ${amount_paid/100}")
            
            # Update subscription status
            if subscription_id:
                self._update_user_subscription(subscription_id, customer_id, 'active')
            
            # Send payment confirmation email
            self._send_payment_confirmation_email(customer_id, invoice_id, amount_paid)
            
            # Track successful payment
            self._track_payment_event('succeeded', invoice_id, customer_id, amount_paid)
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'action': 'payment_succeeded',
                'amount_paid': amount_paid
            }
            
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_payment_failed(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment"""
        try:
            invoice_id = invoice['id']
            customer_id = invoice['customer']
            subscription_id = invoice['subscription']
            amount_due = invoice['amount_due']
            
            logger.warning(f"Payment failed: Invoice {invoice_id} - Amount: ${amount_due/100}")
            
            # Update subscription status
            if subscription_id:
                self._update_user_subscription(subscription_id, customer_id, 'past_due')
            
            # Send payment failure email
            self._send_payment_failure_email(customer_id, invoice_id, amount_due)
            
            # Track failed payment
            self._track_payment_event('failed', invoice_id, customer_id, amount_due)
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'action': 'payment_failed',
                'amount_due': amount_due
            }
            
        except Exception as e:
            logger.error(f"Error handling payment failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_invoice_created(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoice creation"""
        try:
            invoice_id = invoice['id']
            customer_id = invoice['customer']
            subscription_id = invoice['subscription']
            amount_due = invoice['amount_due']
            
            logger.info(f"Invoice created: {invoice_id} - Amount: ${amount_due/100}")
            
            # Track invoice creation
            self._track_invoice_event('created', invoice_id, customer_id, amount_due)
            
            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'action': 'invoice_created',
                'amount_due': amount_due
            }
            
        except Exception as e:
            logger.error(f"Error handling invoice created: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_customer_created(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer creation"""
        try:
            customer_id = customer['id']
            email = customer['email']
            name = customer['name']
            
            logger.info(f"New customer created: {customer_id} - {email}")
            
            # Track customer creation
            self._track_customer_event('created', customer_id, email)
            
            return {
                'status': 'success',
                'customer_id': customer_id,
                'email': email,
                'name': name,
                'action': 'customer_created'
            }
            
        except Exception as e:
            logger.error(f"Error handling customer created: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_customer_updated(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer updates"""
        try:
            customer_id = customer['id']
            email = customer['email']
            
            logger.info(f"Customer updated: {customer_id} - {email}")
            
            # Track customer update
            self._track_customer_event('updated', customer_id, email)
            
            return {
                'status': 'success',
                'customer_id': customer_id,
                'email': email,
                'action': 'customer_updated'
            }
            
        except Exception as e:
            logger.error(f"Error handling customer updated: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_payment_method_attached(self, payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment method attachment"""
        try:
            payment_method_id = payment_method['id']
            customer_id = payment_method['customer']
            
            logger.info(f"Payment method attached: {payment_method_id} to customer {customer_id}")
            
            # Track payment method attachment
            self._track_payment_method_event('attached', payment_method_id, customer_id)
            
            return {
                'status': 'success',
                'payment_method_id': payment_method_id,
                'customer_id': customer_id,
                'action': 'payment_method_attached'
            }
            
        except Exception as e:
            logger.error(f"Error handling payment method attached: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_checkout_completed(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkout session completion"""
        try:
            session_id = session['id']
            customer_id = session['customer']
            subscription_id = session['subscription']
            
            logger.info(f"Checkout completed: Session {session_id} - Customer {customer_id}")
            
            # Track checkout completion
            self._track_checkout_event('completed', session_id, customer_id, subscription_id)
            
            return {
                'status': 'success',
                'session_id': session_id,
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'action': 'checkout_completed'
            }
            
        except Exception as e:
            logger.error(f"Error handling checkout completed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_checkout_expired(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkout session expiration"""
        try:
            session_id = session['id']
            customer_id = session.get('customer')
            
            logger.info(f"Checkout expired: Session {session_id}")
            
            # Track checkout expiration
            self._track_checkout_event('expired', session_id, customer_id)
            
            return {
                'status': 'success',
                'session_id': session_id,
                'customer_id': customer_id,
                'action': 'checkout_expired'
            }
            
        except Exception as e:
            logger.error(f"Error handling checkout expired: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_payment_intent_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment intent (card verification)"""
        try:
            payment_intent_id = payment_intent['id']
            customer_id = payment_intent.get('customer')
            amount = payment_intent['amount']
            metadata = payment_intent.get('metadata', {})
            
            # Check if this is a verification charge ($1 or less)
            is_verification = metadata.get('verification', 'false') == 'true' or amount <= 100
            
            if is_verification:
                logger.info(f"Card verification succeeded: Payment Intent {payment_intent_id} - Amount: ${amount/100}")
                
                # If it's a $1 verification charge, refund it immediately
                if amount == 100 and STRIPE_AVAILABLE:
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
            
            return {
                'status': 'success',
                'payment_intent_id': payment_intent_id,
                'customer_id': customer_id,
                'action': 'payment_intent_succeeded',
                'is_verification': is_verification,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Error handling payment intent succeeded: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_payment_intent_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment intent (card verification failed)"""
        try:
            payment_intent_id = payment_intent['id']
            customer_id = payment_intent.get('customer')
            last_payment_error = payment_intent.get('last_payment_error', {})
            error_message = last_payment_error.get('message', 'Payment failed')
            
            logger.warning(f"Card verification failed: Payment Intent {payment_intent_id} - {error_message}")
            
            # Track failed verification
            self._track_payment_event('verification_failed', payment_intent_id, customer_id, 0)
            
            return {
                'status': 'success',
                'payment_intent_id': payment_intent_id,
                'customer_id': customer_id,
                'action': 'payment_intent_failed',
                'error_message': error_message
            }
            
        except Exception as e:
            logger.error(f"Error handling payment intent failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_charge_succeeded(self, charge: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful charge (including verification charges)"""
        try:
            charge_id = charge['id']
            customer_id = charge.get('customer')
            amount = charge['amount']
            metadata = charge.get('metadata', {})
            
            is_verification = metadata.get('verification', 'false') == 'true' or amount <= 100
            
            if is_verification:
                logger.info(f"Verification charge succeeded: Charge {charge_id} - Amount: ${amount/100}")
            
            return {
                'status': 'success',
                'charge_id': charge_id,
                'customer_id': customer_id,
                'action': 'charge_succeeded',
                'is_verification': is_verification,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Error handling charge succeeded: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_charge_refunded(self, charge: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refunded charge (verification refund)"""
        try:
            charge_id = charge['id']
            customer_id = charge.get('customer')
            amount_refunded = charge.get('amount_refunded', 0)
            metadata = charge.get('metadata', {})
            
            if metadata.get('reason') == 'card_verification':
                logger.info(f"Verification charge refunded: Charge {charge_id} - Amount: ${amount_refunded/100}")
            
            return {
                'status': 'success',
                'charge_id': charge_id,
                'customer_id': customer_id,
                'action': 'charge_refunded',
                'amount_refunded': amount_refunded
            }
            
        except Exception as e:
            logger.error(f"Error handling charge refunded: {e}")
            return {'status': 'error', 'error': str(e)}
    
    # Private helper methods
    def _update_user_subscription(self, subscription_id: str, customer_id: str, status: str):
        """Update user subscription in database - persists webhook data"""
        from core.database_optimization import DatabaseOptimizer
        db = DatabaseOptimizer()
        
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
                logger.error(f"No email found for customer {customer_id}")
                return
            
            # Find user by email
            user_result = db.execute_query("SELECT id FROM users WHERE email = ?", (user_email,))
            if not user_result or len(user_result) == 0 or not user_result[0]:
                logger.error(f"User not found for email: {user_email}")
                return
            
            user_row = user_result[0]
            user_id = user_row[0] if isinstance(user_row, tuple) else user_row.get('id') if isinstance(user_row, dict) else None
            if not user_id:
                logger.error(f"Invalid user data for email: {user_email}")
                return
            
            # Get tier from product metadata
            tier = 'starter'  # default
            billing_period = 'monthly'  # default
            
            if subscription.items.data and len(subscription.items.data) > 0:
                product_id = subscription.items.data[0].price.product
                try:
                    product = stripe.Product.retrieve(product_id)
                    tier = product.metadata.get('tier', 'starter')
                    
                    # Get billing period from price
                    price = subscription.items.data[0].price
                    if price.recurring:
                        billing_period = price.recurring.interval  # 'month' or 'year'
                        if billing_period == 'year':
                            billing_period = 'annual'
                except Exception as e:
                    logger.warning(f"Failed to get product details: {e}")
            
            # Update or insert subscription in database
            db.execute_query("""
                INSERT OR REPLACE INTO subscriptions 
                (user_id, stripe_customer_id, stripe_subscription_id, status, tier,
                 billing_period, current_period_start, current_period_end, 
                 trial_end, cancel_at_period_end, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id, 
                customer_id, 
                subscription_id, 
                status, 
                tier,
                billing_period,
                subscription.current_period_start,
                subscription.current_period_end,
                subscription.trial_end,
                subscription.cancel_at_period_end or False
            ), fetch=False)
            
            # Update customer_id in users table
            db.execute_query(
                "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                (customer_id, user_id),
                fetch=False
            )
            
            logger.info(f"✅ Updated subscription {subscription_id} in database for user {user_id}")
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error updating subscription: {e}")
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
        body = f"<p>Welcome to Fikiri Solutions! Your subscription is active.</p><p>Subscription ID: {subscription_id}</p>"
        self._send_billing_email(email, "Welcome to Fikiri Solutions", body)
    
    def _send_cancellation_email(self, customer_id: str, subscription_id: str):
        """Send cancellation email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        body = f"<p>Your Fikiri subscription has been canceled. We're sorry to see you go.</p><p>Subscription ID: {subscription_id}</p>"
        self._send_billing_email(email, "Your Fikiri subscription has been canceled", body)
    
    def _send_trial_ending_email(self, customer_id: str, subscription_id: str, trial_end: int):
        """Send trial ending email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        end_str = datetime.utcfromtimestamp(trial_end).strftime('%Y-%m-%d') if trial_end else 'soon'
        body = f"<p>Your Fikiri trial ends on {end_str}. Add a payment method to continue using the service.</p>"
        self._send_billing_email(email, "Your Fikiri trial is ending soon", body)
    
    def _send_payment_confirmation_email(self, customer_id: str, invoice_id: str, amount_paid: int):
        """Send payment confirmation email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        amount_str = f"${amount_paid / 100:.2f}" if amount_paid is not None else "—"
        body = f"<p>Thank you for your payment. We've received {amount_str} for invoice {invoice_id}.</p>"
        self._send_billing_email(email, "Payment received – Fikiri Solutions", body)
    
    def _send_payment_failure_email(self, customer_id: str, invoice_id: str, amount_due: int):
        """Send payment failure email"""
        email = self._get_customer_email(customer_id)
        if not email:
            return
        amount_str = f"${amount_due / 100:.2f}" if amount_due is not None else "—"
        body = f"<p>We couldn't process your payment for invoice {invoice_id}. Amount due: {amount_str}. Please update your payment method.</p>"
        self._send_billing_email(email, "Payment failed – action needed", body)
    
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
