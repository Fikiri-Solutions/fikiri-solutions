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
    
    # Private helper methods
    def _update_user_subscription(self, subscription_id: str, customer_id: str, status: str):
        """Update user subscription in database"""
        # TODO: Implement database update
        logger.info(f"Updating subscription {subscription_id} for customer {customer_id} to status {status}")
        pass
    
    def _send_welcome_email(self, customer_id: str, subscription_id: str):
        """Send welcome email to new subscriber"""
        # TODO: Implement email sending
        logger.info(f"Sending welcome email to customer {customer_id}")
        pass
    
    def _send_cancellation_email(self, customer_id: str, subscription_id: str):
        """Send cancellation email"""
        # TODO: Implement email sending
        logger.info(f"Sending cancellation email to customer {customer_id}")
        pass
    
    def _send_trial_ending_email(self, customer_id: str, subscription_id: str, trial_end: int):
        """Send trial ending email"""
        # TODO: Implement email sending
        logger.info(f"Sending trial ending email to customer {customer_id}")
        pass
    
    def _send_payment_confirmation_email(self, customer_id: str, invoice_id: str, amount_paid: int):
        """Send payment confirmation email"""
        # TODO: Implement email sending
        logger.info(f"Sending payment confirmation email to customer {customer_id}")
        pass
    
    def _send_payment_failure_email(self, customer_id: str, invoice_id: str, amount_due: int):
        """Send payment failure email"""
        # TODO: Implement email sending
        logger.info(f"Sending payment failure email to customer {customer_id}")
        pass
    
    def _handle_subscription_activated(self, subscription_id: str, customer_id: str):
        """Handle subscription activation"""
        logger.info(f"Subscription activated: {subscription_id}")
        # TODO: Implement activation logic
        pass
    
    def _handle_subscription_past_due(self, subscription_id: str, customer_id: str):
        """Handle subscription past due"""
        logger.info(f"Subscription past due: {subscription_id}")
        # TODO: Implement past due logic
        pass
    
    def _handle_subscription_canceled(self, subscription_id: str, customer_id: str):
        """Handle subscription cancellation"""
        logger.info(f"Subscription canceled: {subscription_id}")
        # TODO: Implement cancellation logic
        pass
    
    def _track_subscription_event(self, event_type: str, subscription_id: str, customer_id: str):
        """Track subscription events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking subscription event: {event_type} for {subscription_id}")
        pass
    
    def _track_payment_event(self, event_type: str, invoice_id: str, customer_id: str, amount: int):
        """Track payment events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking payment event: {event_type} for invoice {invoice_id}")
        pass
    
    def _track_invoice_event(self, event_type: str, invoice_id: str, customer_id: str, amount: int):
        """Track invoice events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking invoice event: {event_type} for invoice {invoice_id}")
        pass
    
    def _track_customer_event(self, event_type: str, customer_id: str, email: str):
        """Track customer events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking customer event: {event_type} for customer {customer_id}")
        pass
    
    def _track_payment_method_event(self, event_type: str, payment_method_id: str, customer_id: str):
        """Track payment method events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking payment method event: {event_type} for {payment_method_id}")
        pass
    
    def _track_checkout_event(self, event_type: str, session_id: str, customer_id: str, subscription_id: str = None):
        """Track checkout events for analytics"""
        # TODO: Implement analytics tracking
        logger.info(f"Tracking checkout event: {event_type} for session {session_id}")
        pass
