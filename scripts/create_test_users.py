#!/usr/bin/env python3
"""
Create test users for E2E testing
Creates test@example.com, admin@example.com, and other test accounts
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.user_auth import UserAuthManager
from core.database_optimization import db_optimizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    """Create test users for E2E testing"""
    auth_manager = UserAuthManager()
    
    test_users = [
        {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'name': 'Test User',
            'role': 'user'
        },
        {
            'email': 'admin@example.com',
            'password': 'AdminPassword123!',
            'name': 'Admin User',
            'role': 'admin'
        },
        {
            'email': 'demo@example.com',
            'password': 'DemoPassword123!',
            'name': 'Demo User',
            'role': 'user'
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for user_data in test_users:
        email = user_data['email']
        
        # Check if user already exists
        try:
            existing_user = db_optimizer.execute_query(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            )
            if existing_user:
                logger.info(f"⏭️  User {email} already exists, skipping...")
                skipped_count += 1
                continue
        except Exception as e:
            logger.warning(f"Could not check for existing user: {e}")
        
        # Create user
        try:
            result = auth_manager.create_user(
                email=user_data['email'],
                password=user_data['password'],
                name=user_data['name'],
                business_name=None,
                business_email=None,
                industry=None,
                team_size=None
            )
            
            # Update role if needed (admin users)
            if user_data.get('role') == 'admin' and result.get('success'):
                user = result.get('user')
                if user:
                    user_id = user.id if hasattr(user, 'id') else user.get('id')
                    if user_id:
                        db_optimizer.execute_query(
                            "UPDATE users SET role = ? WHERE id = ?",
                            ('admin', user_id),
                            fetch=False
                        )
                        logger.info(f"   Set role to admin for {email}")
            
            if result.get('success'):
                logger.info(f"✅ Created test user: {email}")
                created_count += 1
            else:
                logger.error(f"❌ Failed to create {email}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"❌ Error creating {email}: {e}")
    
    logger.info(f"\n📊 Summary:")
    logger.info(f"   Created: {created_count} users")
    logger.info(f"   Skipped: {skipped_count} users (already exist)")
    logger.info(f"   Total: {len(test_users)} users")
    
    return created_count > 0 or skipped_count > 0

if __name__ == '__main__':
    try:
        success = create_test_users()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
