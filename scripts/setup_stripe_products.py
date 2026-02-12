#!/usr/bin/env python3
"""
Setup Stripe Products and Prices for Fikiri Solutions
Run this script to automatically create all products, features, and prices in Stripe
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.fikiri_stripe_manager import FikiriStripeManager

def main():
    print("🚀 Setting up Stripe billing system for Fikiri Solutions...")
    print("=" * 60)
    
    stripe_manager = FikiriStripeManager()
    
    try:
        result = stripe_manager.setup_complete_billing_system()
        
        if result.get('status') == 'success':
            print("\n✅ Stripe billing system setup complete!")
            print("\nCreated:")
            print(f"  - Features: {len(result.get('features', {}))}")
            print(f"  - Products: {len(result.get('products', {}))}")
            print("\n📋 Product IDs:")
            for tier, product_id in result.get('products', {}).items():
                print(f"  - {tier}: {product_id}")
            print("\n✨ You can now use the checkout flow!")
        else:
            print(f"\n❌ Setup failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

