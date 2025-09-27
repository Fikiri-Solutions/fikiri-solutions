"""
Fikiri Solutions - Enhanced Stripe Billing Manager
Implements Stripe's Products, Features, and Entitlements system for proper feature gating
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
class FikiriFeature:
    """Fikiri feature definition"""
    name: str
    display_name: str
    description: str
    feature_type: str  # 'boolean', 'usage', 'limit'

@dataclass
class SubscriptionLimits:
    """Usage limits for each subscription tier"""
    emails_per_month: int
    leads_storage: int
    ai_responses_per_month: int
    users: int
    integrations: List[str]
    features: List[str]

class FikiriStripeManager:
    """Enhanced Stripe manager using Products, Features, and Entitlements"""
    
    def __init__(self):
        # Define Fikiri features
        self.features = {
            'basic_ai': FikiriFeature(
                name='basic_ai',
                display_name='Basic AI Responses',
                description='AI-powered email responses with basic templates',
                feature_type='boolean'
            ),
            'advanced_ai': FikiriFeature(
                name='advanced_ai',
                display_name='Advanced AI Responses',
                description='AI responses with conversation context and learning',
                feature_type='boolean'
            ),
            'custom_ai': FikiriFeature(
                name='custom_ai',
                display_name='Custom AI Training',
                description='Custom AI models trained on your business data',
                feature_type='boolean'
            ),
            'email_parsing': FikiriFeature(
                name='email_parsing',
                display_name='Email Parsing',
                description='Automatic email parsing and categorization',
                feature_type='boolean'
            ),
            'basic_crm': FikiriFeature(
                name='basic_crm',
                display_name='Basic CRM',
                description='Basic lead management and contact storage',
                feature_type='boolean'
            ),
            'advanced_crm': FikiriFeature(
                name='advanced_crm',
                display_name='Advanced CRM',
                description='Advanced lead scoring, analytics, and automation',
                feature_type='boolean'
            ),
            'email_support': FikiriFeature(
                name='email_support',
                display_name='Email Support',
                description='Email-based customer support',
                feature_type='boolean'
            ),
            'priority_support': FikiriFeature(
                name='priority_support',
                display_name='Priority Support',
                description='Priority email support with faster response times',
                feature_type='boolean'
            ),
            'phone_support': FikiriFeature(
                name='phone_support',
                display_name='Phone Support',
                description='Phone-based customer support',
                feature_type='boolean'
            ),
            'dedicated_support': FikiriFeature(
                name='dedicated_support',
                display_name='Dedicated Support',
                description='Dedicated account manager and support team',
                feature_type='boolean'
            ),
            'analytics': FikiriFeature(
                name='analytics',
                display_name='Basic Analytics',
                description='Basic usage analytics and reporting',
                feature_type='boolean'
            ),
            'advanced_analytics': FikiriFeature(
                name='advanced_analytics',
                display_name='Advanced Analytics',
                description='Advanced analytics with custom reports and insights',
                feature_type='boolean'
            ),
            'white_label': FikiriFeature(
                name='white_label',
                display_name='White Label Options',
                description='Remove Fikiri branding and customize appearance',
                feature_type='boolean'
            ),
            'custom_integrations': FikiriFeature(
                name='custom_integrations',
                display_name='Custom Integrations',
                description='Custom integrations with third-party tools',
                feature_type='boolean'
            ),
            'sla': FikiriFeature(
                name='sla',
                display_name='Service Level Agreement',
                description='Guaranteed uptime and performance SLA',
                feature_type='boolean'
            ),
            'custom_branding': FikiriFeature(
                name='custom_branding',
                display_name='Custom Branding',
                description='Fully customized branding and interface',
                feature_type='boolean'
            ),
            'email_limit': FikiriFeature(
                name='email_limit',
                display_name='Email Processing Limit',
                description='Monthly email processing limit',
                feature_type='limit'
            ),
            'lead_limit': FikiriFeature(
                name='lead_limit',
                display_name='Lead Storage Limit',
                description='Maximum number of leads in CRM',
                feature_type='limit'
            ),
            'ai_response_limit': FikiriFeature(
                name='ai_response_limit',
                display_name='AI Response Limit',
                description='Monthly AI response generation limit',
                feature_type='limit'
            ),
            'user_limit': FikiriFeature(
                name='user_limit',
                display_name='User Limit',
                description='Maximum number of users',
                feature_type='limit'
            )
        }
        
        # Define product configurations
        self.products = {
            SubscriptionTier.STARTER: {
                'name': 'Fikiri Starter',
                'description': 'Perfect for solo entrepreneurs and growing small businesses',
                'features': ['basic_ai', 'email_parsing', 'basic_crm', 'email_support'],
                'limits': {
                    'email_limit': 500,
                    'lead_limit': 100,
                    'ai_response_limit': 200,
                    'user_limit': 1
                },
                'integrations': ['gmail'],
                'pricing': {
                    'monthly': 3900,  # $39.00 in cents
                    'annual': 39000   # $390.00 in cents (10% discount)
                }
            },
            SubscriptionTier.GROWTH: {
                'name': 'Fikiri Growth',
                'description': 'Scale your operations with advanced AI and integrations',
                'features': ['basic_ai', 'advanced_ai', 'email_parsing', 'advanced_crm', 'priority_support', 'analytics'],
                'limits': {
                    'email_limit': 2000,
                    'lead_limit': 1000,
                    'ai_response_limit': 800,
                    'user_limit': 3
                },
                'integrations': ['gmail', 'outlook', 'yahoo'],
                'pricing': {
                    'monthly': 7900,  # $79.00 in cents
                    'annual': 79000   # $790.00 in cents (10% discount)
                }
            },
            SubscriptionTier.BUSINESS: {
                'name': 'Fikiri Business',
                'description': 'Complete business automation platform with white-label options',
                'features': ['basic_ai', 'advanced_ai', 'email_parsing', 'advanced_crm', 'phone_support', 'advanced_analytics', 'white_label', 'custom_integrations'],
                'limits': {
                    'email_limit': 10000,
                    'lead_limit': 5000,
                    'ai_response_limit': 4000,
                    'user_limit': -1  # Unlimited
                },
                'integrations': ['gmail', 'outlook', 'yahoo', 'imap'],
                'pricing': {
                    'monthly': 19900,  # $199.00 in cents
                    'annual': 199000   # $1990.00 in cents (10% discount)
                }
            },
            SubscriptionTier.ENTERPRISE: {
                'name': 'Fikiri Enterprise',
                'description': 'Enterprise-grade automation with dedicated support and custom AI',
                'features': ['basic_ai', 'advanced_ai', 'custom_ai', 'email_parsing', 'advanced_crm', 'dedicated_support', 'advanced_analytics', 'white_label', 'custom_integrations', 'sla', 'custom_branding'],
                'limits': {
                    'email_limit': -1,  # Unlimited
                    'lead_limit': -1,   # Unlimited
                    'ai_response_limit': -1,  # Unlimited
                    'user_limit': -1    # Unlimited
                },
                'integrations': ['all'],
                'pricing': {
                    'monthly': 39900,  # $399.00 in cents
                    'annual': 399000   # $3990.00 in cents (10% discount)
                }
            }
        }

    def create_features(self) -> Dict[str, str]:
        """Create all Fikiri features in Stripe"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping feature creation")
            return {}
            
        created_features = {}
        
        for feature_name, feature in self.features.items():
            try:
                stripe_feature = stripe.Feature.create(
                    name=feature_name,
                    display_name=feature.display_name,
                    description=feature.description
                )
                created_features[feature_name] = stripe_feature.id
                logger.info(f"Created feature: {feature_name} ({stripe_feature.id})")
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create feature {feature_name}: {e}")
                
        return created_features

    def create_products(self, feature_ids: Dict[str, str]) -> Dict[str, str]:
        """Create all Fikiri products in Stripe"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping product creation")
            return {}
            
        created_products = {}
        
        for tier, product_config in self.products.items():
            try:
                # Create product
                product = stripe.Product.create(
                    name=product_config['name'],
                    description=product_config['description'],
                    type='service',
                    metadata={
                        'tier': tier.value,
                        'integrations': ','.join(product_config['integrations'])
                    }
                )
                created_products[tier.value] = product.id
                logger.info(f"Created product: {product_config['name']} ({product.id})")
                
                # Create product features
                for feature_name in product_config['features']:
                    if feature_name in feature_ids:
                        try:
                            stripe.ProductFeature.create(
                                product=product.id,
                                feature=feature_ids[feature_name]
                            )
                            logger.info(f"Added feature {feature_name} to product {product.id}")
                        except stripe.error.StripeError as e:
                            logger.error(f"Failed to add feature {feature_name} to product {product.id}: {e}")
                
                # Create prices for the product
                self._create_product_prices(product.id, product_config['pricing'])
                
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create product {product_config['name']}: {e}")
                
        return created_products

    def _create_product_prices(self, product_id: str, pricing: Dict[str, int]):
        """Create monthly and annual prices for a product"""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, skipping price creation")
            return
            
        try:
            # Create monthly price
            monthly_price = stripe.Price.create(
                product=product_id,
                unit_amount=pricing['monthly'],
                currency='usd',
                recurring={'interval': 'month'},
                metadata={'billing_period': 'monthly'}
            )
            logger.info(f"Created monthly price: {monthly_price.id}")
            
            # Create annual price
            annual_price = stripe.Price.create(
                product=product_id,
                unit_amount=pricing['annual'],
                currency='usd',
                recurring={'interval': 'year'},
                metadata={'billing_period': 'annual'}
            )
            logger.info(f"Created annual price: {annual_price.id}")
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create prices for product {product_id}: {e}")

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

    def get_customer_entitlements(self, customer_id: str) -> Dict[str, Any]:
        """Get customer's active entitlements"""
        try:
            entitlements = stripe.Entitlement.list(
                customer=customer_id,
                active=True
            )
            
            entitlements_data = {}
            for entitlement in entitlements.data:
                feature_name = entitlement.feature.name
                entitlements_data[feature_name] = {
                    'id': entitlement.id,
                    'feature_id': entitlement.feature.id,
                    'feature_name': feature_name,
                    'active': entitlement.active,
                    'created': entitlement.created
                }
            
            return entitlements_data
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get entitlements for customer {customer_id}: {e}")
            raise

    def check_feature_access(self, customer_id: str, feature_name: str) -> bool:
        """Check if customer has access to a specific feature"""
        try:
            entitlements = self.get_customer_entitlements(customer_id)
            return feature_name in entitlements and entitlements[feature_name]['active']
            
        except Exception as e:
            logger.error(f"Failed to check feature access for {feature_name}: {e}")
            return False

    def get_customer_limits(self, customer_id: str) -> Dict[str, int]:
        """Get customer's usage limits based on their subscription"""
        try:
            # Get customer's active subscription
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='active'
            )
            
            if not subscriptions.data:
                return {}
            
            subscription = subscriptions.data[0]
            product_id = subscription.items.data[0].price.product
            
            # Get product details
            product = stripe.Product.retrieve(product_id)
            tier = product.metadata.get('tier')
            
            if tier and tier in self.products:
                return self.products[SubscriptionTier(tier)]['limits']
            
            return {}
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get customer limits for {customer_id}: {e}")
            return {}

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

    def create_checkout_session(self, price_id: str, customer_id: str = None, success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """Create Stripe Checkout session"""
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
                'features': self.products[SubscriptionTier.STARTER]['features'],
                'limits': self.products[SubscriptionTier.STARTER]['limits']
            },
            'growth': {
                'name': 'Fikiri Growth',
                'monthly_price': 79.00,
                'annual_price': 790.00,
                'description': 'Scale your operations with advanced AI and integrations',
                'features': self.products[SubscriptionTier.GROWTH]['features'],
                'limits': self.products[SubscriptionTier.GROWTH]['limits']
            },
            'business': {
                'name': 'Fikiri Business',
                'monthly_price': 199.00,
                'annual_price': 1990.00,
                'description': 'Complete business automation platform with white-label options',
                'features': self.products[SubscriptionTier.BUSINESS]['features'],
                'limits': self.products[SubscriptionTier.BUSINESS]['limits']
            },
            'enterprise': {
                'name': 'Fikiri Enterprise',
                'monthly_price': 399.00,
                'annual_price': 3990.00,
                'description': 'Enterprise-grade automation with dedicated support and custom AI',
                'features': self.products[SubscriptionTier.ENTERPRISE]['features'],
                'limits': self.products[SubscriptionTier.ENTERPRISE]['limits']
            }
        }

    def setup_complete_billing_system(self) -> Dict[str, Any]:
        """Set up the complete Fikiri billing system"""
        try:
            logger.info("Setting up complete Fikiri billing system...")
            
            # Step 1: Create all features
            logger.info("Creating features...")
            feature_ids = self.create_features()
            
            # Step 2: Create all products with features
            logger.info("Creating products...")
            product_ids = self.create_products(feature_ids)
            
            logger.info("Fikiri billing system setup complete!")
            return {
                'features': feature_ids,
                'products': product_ids,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to setup billing system: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
