"""
Fikiri Solutions - Stripe Billing Manager
Handles subscription management, usage tracking, and billing operations
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Optional Stripe integration
try:
    import stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    """Fikiri subscription tiers"""
    STARTER = "starter"
    GROWTH = "growth"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(Enum):
    """Subscription status states"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"

@dataclass
class SubscriptionLimits:
    """Usage limits for each subscription tier"""
    emails_per_month: int
    leads_storage: int
    ai_responses_per_month: int
    users: int
    integrations: List[str]
    features: List[str]

@dataclass
class UsageMetrics:
    """Current usage metrics for a user"""
    emails_processed: int
    leads_created: int
    ai_responses_generated: int
    month_year: str

class FikiriBillingManager:
    """Main billing manager for Fikiri Solutions"""
    
    def __init__(self):
        self.tier_limits = {
            SubscriptionTier.STARTER: SubscriptionLimits(
                emails_per_month=500,
                leads_storage=100,
                ai_responses_per_month=200,
                users=1,
                integrations=["gmail"],
                features=["basic_ai", "email_parsing", "basic_crm", "email_support"]
            ),
            SubscriptionTier.GROWTH: SubscriptionLimits(
                emails_per_month=2000,
                leads_storage=1000,
                ai_responses_per_month=800,
                users=3,
                integrations=["gmail", "outlook", "yahoo"],
                features=["advanced_ai", "email_parsing", "advanced_crm", "priority_support", "analytics"]
            ),
            SubscriptionTier.BUSINESS: SubscriptionLimits(
                emails_per_month=10000,
                leads_storage=5000,
                ai_responses_per_month=4000,
                users=-1,  # Unlimited
                integrations=["gmail", "outlook", "yahoo", "imap"],
                features=["advanced_ai", "email_parsing", "advanced_crm", "phone_support", "advanced_analytics", "white_label", "custom_integrations"]
            ),
            SubscriptionTier.ENTERPRISE: SubscriptionLimits(
                emails_per_month=-1,  # Unlimited
                leads_storage=-1,  # Unlimited
                ai_responses_per_month=-1,  # Unlimited
                users=-1,  # Unlimited
                integrations=["all"],
                features=["custom_ai", "email_parsing", "advanced_crm", "dedicated_support", "advanced_analytics", "white_label", "custom_integrations", "sla", "custom_branding"]
            )
        }
        
        self.overage_pricing = {
            "email_processing": 0.02,  # $0.02 per email
            "lead_storage": 0.10,    # $0.10 per lead
            "ai_responses": 0.05     # $0.05 per AI response
        }

    def create_subscription(self, customer_id: str, price_id: str, trial_days: int = 14) -> Dict[str, Any]:
        """Create a new subscription with free trial"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping subscription creation")
            return {}
            
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_days,
                payment_behavior='default_incomplete',
                payment_settings={
                    'save_default_payment_method': 'on_subscription'
                },
                expand=['latest_invoice.payment_intent']
            )
            
            logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'trial_end': subscription.trial_end,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'trial_end': subscription.trial_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'items': subscription.items.data
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription {subscription_id}: {e}")
            raise

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel subscription"""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled subscription {subscription_id}")
            return {
                'id': subscription.id,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            raise

    def upgrade_subscription(self, subscription_id: str, new_price_id: str) -> Dict[str, Any]:
        """Upgrade subscription to higher tier"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Update subscription item
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription.items.data[0].id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations'
            )
            
            logger.info(f"Upgraded subscription {subscription_id} to price {new_price_id}")
            return {'success': True, 'subscription_id': subscription_id}
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to upgrade subscription {subscription_id}: {e}")
            raise

    def get_tier_limits(self, tier: SubscriptionTier) -> SubscriptionLimits:
        """Get usage limits for a subscription tier"""
        return self.tier_limits.get(tier)

    def check_usage_limits(self, user_id: str, tier: SubscriptionTier, current_usage: UsageMetrics) -> Dict[str, Any]:
        """Check if user has exceeded usage limits"""
        limits = self.get_tier_limits(tier)
        
        # Check each usage type
        email_overage = max(0, current_usage.emails_processed - limits.emails_per_month) if limits.emails_per_month > 0 else 0
        lead_overage = max(0, current_usage.leads_created - limits.leads_storage) if limits.leads_storage > 0 else 0
        ai_overage = max(0, current_usage.ai_responses_generated - limits.ai_responses_per_month) if limits.ai_responses_per_month > 0 else 0
        
        total_overage_cost = (
            email_overage * self.overage_pricing["email_processing"] +
            lead_overage * self.overage_pricing["lead_storage"] +
            ai_overage * self.overage_pricing["ai_responses"]
        )
        
        return {
            'within_limits': total_overage_cost == 0,
            'email_overage': email_overage,
            'lead_overage': lead_overage,
            'ai_overage': ai_overage,
            'total_overage_cost': total_overage_cost,
            'limits': {
                'emails': limits.emails_per_month,
                'leads': limits.leads_storage,
                'ai_responses': limits.ai_responses_per_month
            }
        }

    def create_usage_record(self, subscription_item_id: str, usage_type: str, quantity: int) -> Dict[str, Any]:
        """Create usage record for overage billing"""
        try:
            usage_record = stripe.UsageRecord.create(
                subscription_item=subscription_item_id,
                quantity=quantity,
                timestamp=int(datetime.now().timestamp()),
                action='increment'
            )
            
            logger.info(f"Created usage record for {usage_type}: {quantity}")
            return {
                'id': usage_record.id,
                'quantity': usage_record.quantity,
                'timestamp': usage_record.timestamp
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create usage record: {e}")
            raise

    def get_customer_subscriptions(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a customer"""
        try:
            subscriptions = stripe.Subscription.list(customer=customer_id)
            return [
                {
                    'id': sub.id,
                    'status': sub.status,
                    'current_period_start': sub.current_period_start,
                    'current_period_end': sub.current_period_end,
                    'trial_end': sub.trial_end,
                    'items': sub.items.data
                }
                for sub in subscriptions.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscriptions for customer {customer_id}: {e}")
            raise

    def create_customer(self, email: str, name: str, metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a new Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            logger.info(f"Created customer {customer.id} for {email}")
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            raise

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer details"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'created': customer.created,
                'metadata': customer.metadata
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve customer {customer_id}: {e}")
            raise

    def create_checkout_session(self, price_id: str, customer_id: str = None, success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """Create Stripe Checkout session"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping checkout session creation")
            return {}
        try:
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'subscription',
                'success_url': success_url or f"{os.getenv('FRONTEND_URL')}/dashboard?success=true",
                'cancel_url': cancel_url or f"{os.getenv('FRONTEND_URL')}/pricing?canceled=true",
                'trial_period_days': 14,
                'allow_promotion_codes': True,
                'billing_address_collection': 'required',
                'customer_creation': 'always' if not customer_id else None,
                'customer': customer_id if customer_id else None,
                'subscription_data': {
                    'trial_period_days': 14,
                    'metadata': {
                        'source': 'fikiri_checkout'
                    }
                }
            }
            
            session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"Created checkout session {session.id}")
            return {
                'session_id': session.id,
                'url': session.url
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    def get_pricing_tiers(self) -> Dict[str, Dict[str, Any]]:
        """Get all pricing tiers with their details"""
        return {
            'starter': {
                'name': 'Fikiri Starter',
                'monthly_price': 39.00,
                'annual_price': 390.00,
                'description': 'Perfect for solo entrepreneurs and growing small businesses',
                'features': self.tier_limits[SubscriptionTier.STARTER].features,
                'limits': {
                    'emails': self.tier_limits[SubscriptionTier.STARTER].emails_per_month,
                    'leads': self.tier_limits[SubscriptionTier.STARTER].leads_storage,
                    'ai_responses': self.tier_limits[SubscriptionTier.STARTER].ai_responses_per_month,
                    'users': self.tier_limits[SubscriptionTier.STARTER].users
                }
            },
            'growth': {
                'name': 'Fikiri Growth',
                'monthly_price': 79.00,
                'annual_price': 790.00,
                'description': 'Scale your operations with advanced AI and integrations',
                'features': self.tier_limits[SubscriptionTier.GROWTH].features,
                'limits': {
                    'emails': self.tier_limits[SubscriptionTier.GROWTH].emails_per_month,
                    'leads': self.tier_limits[SubscriptionTier.GROWTH].leads_storage,
                    'ai_responses': self.tier_limits[SubscriptionTier.GROWTH].ai_responses_per_month,
                    'users': self.tier_limits[SubscriptionTier.GROWTH].users
                }
            },
            'business': {
                'name': 'Fikiri Business',
                'monthly_price': 199.00,
                'annual_price': 1990.00,
                'description': 'Complete business automation platform with white-label options',
                'features': self.tier_limits[SubscriptionTier.BUSINESS].features,
                'limits': {
                    'emails': self.tier_limits[SubscriptionTier.BUSINESS].emails_per_month,
                    'leads': self.tier_limits[SubscriptionTier.BUSINESS].leads_storage,
                    'ai_responses': self.tier_limits[SubscriptionTier.BUSINESS].ai_responses_per_month,
                    'users': self.tier_limits[SubscriptionTier.BUSINESS].users
                }
            },
            'enterprise': {
                'name': 'Fikiri Enterprise',
                'monthly_price': 399.00,
                'annual_price': 3990.00,
                'description': 'Enterprise-grade automation with dedicated support and custom AI',
                'features': self.tier_limits[SubscriptionTier.ENTERPRISE].features,
                'limits': {
                    'emails': self.tier_limits[SubscriptionTier.ENTERPRISE].emails_per_month,
                    'leads': self.tier_limits[SubscriptionTier.ENTERPRISE].leads_storage,
                    'ai_responses': self.tier_limits[SubscriptionTier.ENTERPRISE].ai_responses_per_month,
                    'users': self.tier_limits[SubscriptionTier.ENTERPRISE].users
                }
            }
        }
