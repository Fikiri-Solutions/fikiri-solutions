"""
Fikiri Solutions - Subscription API Endpoints
Flask API endpoints for subscription management and billing
"""

from flask import Blueprint, request, jsonify, current_app
import logging

# Optional JWT integration
try:
    from flask_jwt_extended import jwt_required, get_jwt_identity
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    # Create dummy decorators when JWT is not available
    def jwt_required(fresh=False, optional=False):
        def decorator(func):
            return func
        return decorator
    def get_jwt_identity():
        return None
from core.fikiri_stripe_manager import FikiriStripeManager
from core.stripe_webhooks import StripeWebhookHandler

logger = logging.getLogger(__name__)

# Create Blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

# Initialize managers
stripe_manager = FikiriStripeManager()
webhook_handler = StripeWebhookHandler()

@billing_bp.route('/pricing', methods=['GET'])
def get_pricing_tiers():
    """Get all available pricing tiers"""
    try:
        pricing_tiers = stripe_manager.get_pricing_tiers()
        return jsonify({
            'success': True,
            'pricing_tiers': pricing_tiers
        })
    except Exception as e:
        logger.error(f"Failed to get pricing tiers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/checkout', methods=['POST'])
@jwt_required()
def create_checkout_session():
    """Create Stripe Checkout session for subscription"""
    try:
        data = request.get_json()
        price_id = data.get('price_id')
        billing_period = data.get('billing_period', 'monthly')  # monthly or annual
        
        if not price_id:
            return jsonify({
                'success': False,
                'error': 'Price ID is required'
            }), 400
        
        # Get user info from JWT
        user_id = get_jwt_identity()
        
        # Create checkout session
        session = stripe_manager.create_checkout_session(
            price_id=price_id,
            customer_id=None,  # Will be created during checkout
            success_url=f"{current_app.config.get('FRONTEND_URL')}/dashboard?success=true",
            cancel_url=f"{current_app.config.get('FRONTEND_URL')}/pricing?canceled=true"
        )
        
        return jsonify({
            'success': True,
            'checkout_url': session['url'],
            'session_id': session['session_id']
        })
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/subscription', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create subscription directly (for testing)"""
    try:
        data = request.get_json()
        price_id = data.get('price_id')
        trial_days = data.get('trial_days', 14)
        
        if not price_id:
            return jsonify({
                'success': False,
                'error': 'Price ID is required'
            }), 400
        
        # Get user info from JWT
        user_id = get_jwt_identity()
        
        # Create customer if doesn't exist
        customer = stripe_manager.create_customer(
            email=f"user_{user_id}@fikiri.com",  # TODO: Get real email
            name=f"User {user_id}",
            metadata={'user_id': user_id}
        )
        
        # Create subscription
        subscription = stripe_manager.create_subscription(
            customer_id=customer['id'],
            price_id=price_id,
            trial_days=trial_days
        )
        
        return jsonify({
            'success': True,
            'subscription': subscription
        })
        
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/subscription/<subscription_id>', methods=['GET'])
@jwt_required()
def get_subscription(subscription_id):
    """Get subscription details"""
    try:
        # TODO: Verify user owns this subscription
        subscription = stripe_manager.get_subscription(subscription_id)
        
        return jsonify({
            'success': True,
            'subscription': subscription
        })
        
    except Exception as e:
        logger.error(f"Failed to get subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/subscription/<subscription_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(subscription_id):
    """Cancel subscription"""
    try:
        data = request.get_json()
        at_period_end = data.get('at_period_end', True)
        
        # TODO: Verify user owns this subscription
        result = stripe_manager.cancel_subscription(subscription_id, at_period_end)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/subscription/<subscription_id>/upgrade', methods=['POST'])
@jwt_required()
def upgrade_subscription(subscription_id):
    """Upgrade subscription to higher tier"""
    try:
        data = request.get_json()
        new_price_id = data.get('new_price_id')
        
        if not new_price_id:
            return jsonify({
                'success': False,
                'error': 'New price ID is required'
            }), 400
        
        # TODO: Verify user owns this subscription
        result = stripe_manager.upgrade_subscription(subscription_id, new_price_id)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Failed to upgrade subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/customer/<customer_id>/entitlements', methods=['GET'])
@jwt_required()
def get_customer_entitlements(customer_id):
    """Get customer's active entitlements"""
    try:
        # TODO: Verify user owns this customer
        entitlements = stripe_manager.get_customer_entitlements(customer_id)
        
        return jsonify({
            'success': True,
            'entitlements': entitlements
        })
        
    except Exception as e:
        logger.error(f"Failed to get customer entitlements: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/customer/<customer_id>/limits', methods=['GET'])
@jwt_required()
def get_customer_limits(customer_id):
    """Get customer's usage limits"""
    try:
        # TODO: Verify user owns this customer
        limits = stripe_manager.get_customer_limits(customer_id)
        
        return jsonify({
            'success': True,
            'limits': limits
        })
        
    except Exception as e:
        logger.error(f"Failed to get customer limits: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/check-feature-access', methods=['POST'])
@jwt_required()
def check_feature_access():
    """Check if customer has access to a specific feature"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        feature_name = data.get('feature_name')
        
        if not customer_id or not feature_name:
            return jsonify({
                'success': False,
                'error': 'Customer ID and feature name are required'
            }), 400
        
        # TODO: Verify user owns this customer
        has_access = stripe_manager.check_feature_access(customer_id, feature_name)
        
        return jsonify({
            'success': True,
            'has_access': has_access,
            'feature_name': feature_name
        })
        
    except Exception as e:
        logger.error(f"Failed to check feature access: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/webhook', methods=['POST'])
def handle_stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature
        event = webhook_handler.verify_webhook_signature(payload, sig_header)
        
        # Handle the event
        result = webhook_handler.handle_event(event)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to handle webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@billing_bp.route('/setup', methods=['POST'])
def setup_billing_system():
    """Set up the complete billing system (admin only)"""
    try:
        # TODO: Add admin authentication
        result = stripe_manager.setup_complete_billing_system()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to setup billing system: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Usage tracking endpoints
@billing_bp.route('/usage/track', methods=['POST'])
@jwt_required()
def track_usage():
    """Track usage for overage billing"""
    try:
        data = request.get_json()
        usage_type = data.get('usage_type')  # email_processing, lead_storage, ai_responses
        quantity = data.get('quantity', 1)
        
        if not usage_type:
            return jsonify({
                'success': False,
                'error': 'Usage type is required'
            }), 400
        
        # TODO: Implement usage tracking
        # This would integrate with your usage tracking system
        
        return jsonify({
            'success': True,
            'message': f'Tracked {quantity} {usage_type} usage'
        })
        
    except Exception as e:
        logger.error(f"Failed to track usage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/usage/current', methods=['GET'])
@jwt_required()
def get_current_usage():
    """Get current usage for the month"""
    try:
        # TODO: Implement usage retrieval
        # This would get current usage from your database
        
        return jsonify({
            'success': True,
            'usage': {
                'emails_processed': 0,
                'leads_created': 0,
                'ai_responses_generated': 0,
                'month_year': '2024-01'
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get current usage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
