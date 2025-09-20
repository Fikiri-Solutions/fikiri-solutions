#!/usr/bin/env python3
"""
Fikiri Solutions - Stripe Billing Setup Script
Sets up the complete Stripe billing system with Products, Features, and Entitlements
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.fikiri_stripe_manager import FikiriStripeManager
from core.usage_tracker import UsageTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_stripe_billing():
    """Set up the complete Stripe billing system"""
    try:
        logger.info("🚀 Starting Fikiri Solutions Stripe billing setup...")
        
        # Check for required environment variables
        required_vars = ['STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            logger.error("Please set these in your .env file or environment")
            return False
        
        # Initialize Stripe manager
        stripe_manager = FikiriStripeManager()
        
        # Set up the complete billing system
        logger.info("📦 Creating Stripe products and features...")
        result = stripe_manager.setup_complete_billing_system()
        
        if result['status'] == 'success':
            logger.info("✅ Stripe billing system setup completed successfully!")
            logger.info(f"📊 Created {len(result['features'])} features")
            logger.info(f"📊 Created {len(result['products'])} products")
            
            # Print created features
            logger.info("\n🎯 Created Features:")
            for feature_name, feature_id in result['features'].items():
                logger.info(f"  - {feature_name}: {feature_id}")
            
            # Print created products
            logger.info("\n📦 Created Products:")
            for tier, product_id in result['products'].items():
                logger.info(f"  - {tier}: {product_id}")
            
            return True
        else:
            logger.error(f"❌ Failed to setup billing system: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during billing setup: {e}")
        return False

def setup_usage_tracking():
    """Set up the usage tracking system"""
    try:
        logger.info("📊 Setting up usage tracking system...")
        
        # Initialize usage tracker
        usage_tracker = UsageTracker()
        
        logger.info("✅ Usage tracking system initialized")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up usage tracking: {e}")
        return False

def verify_setup():
    """Verify the billing system setup"""
    try:
        logger.info("🔍 Verifying billing system setup...")
        
        stripe_manager = FikiriStripeManager()
        
        # Get pricing tiers
        pricing_tiers = stripe_manager.get_pricing_tiers()
        
        logger.info("✅ Pricing tiers available:")
        for tier_name, tier_data in pricing_tiers.items():
            logger.info(f"  - {tier_data['name']}: ${tier_data['monthly_price']}/month")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying setup: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("🎯 Fikiri Solutions - Stripe Billing Setup")
    logger.info("=" * 50)
    
    # Step 1: Set up Stripe billing
    if not setup_stripe_billing():
        logger.error("❌ Stripe billing setup failed")
        return False
    
    # Step 2: Set up usage tracking
    if not setup_usage_tracking():
        logger.error("❌ Usage tracking setup failed")
        return False
    
    # Step 3: Verify setup
    if not verify_setup():
        logger.error("❌ Setup verification failed")
        return False
    
    logger.info("\n🎉 Setup completed successfully!")
    logger.info("🚀 Your Fikiri Solutions billing system is ready!")
    
    logger.info("\n📋 Next Steps:")
    logger.info("1. Configure webhook endpoints in Stripe Dashboard")
    logger.info("2. Set up your frontend checkout flow")
    logger.info("3. Test subscription creation and management")
    logger.info("4. Configure usage tracking in your application")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
