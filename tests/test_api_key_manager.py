#!/usr/bin/env python3
"""
API Key Manager Unit Tests
Tests for API key generation, validation, rate limiting, and tenant isolation
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Set test environment
os.environ['FLASK_ENV'] = 'test'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_key_manager import APIKeyManager


class TestAPIKeyManager(unittest.TestCase):
    """Test API key manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = APIKeyManager()
        self.test_user_id = 999
        self._ensure_test_user()

    def _ensure_test_user(self):
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            INSERT OR IGNORE INTO users (id, email, password_hash, name)
            VALUES (?, ?, ?, ?)
        """, (
            self.test_user_id,
            f"test_user_{self.test_user_id}@example.com",
            "test_hash",
            "Test User"
        ), fetch=False)
    
    def tearDown(self):
        """Clean up test data"""
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query(
            "DELETE FROM api_key_usage WHERE api_key_id IN (SELECT id FROM api_keys WHERE user_id = ?)",
            (self.test_user_id,),
            fetch=False
        )
        db_optimizer.execute_query(
            "DELETE FROM api_keys WHERE user_id = ?",
            (self.test_user_id,),
            fetch=False
        )
        db_optimizer.execute_query(
            "DELETE FROM users WHERE id = ?",
            (self.test_user_id,),
            fetch=False
        )
    
    def test_1_generate_api_key_creates_valid_key(self):
        """Test API key generation creates valid key with correct format"""
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test API Key",
            description="Test key for unit tests"
        )
        
        # Check response structure
        self.assertIn('api_key', result)
        self.assertIn('key_info', result)
        
        # Check key format
        api_key = result['api_key']
        self.assertTrue(api_key.startswith('fik_'))
        self.assertGreater(len(api_key), 40)  # Should be substantial length
        
        # Check key info
        key_info = result['key_info']
        self.assertEqual(key_info['name'], "Test API Key")
        self.assertIn('chatbot:query', key_info['scopes'])
        self.assertEqual(key_info['rate_limit_per_minute'], 60)
        self.assertEqual(key_info['rate_limit_per_hour'], 1000)
    
    def test_2_validate_api_key_accepts_valid_key(self):
        """Test API key validation accepts correctly formatted keys"""
        # Generate a key
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Validation Test Key"
        )
        api_key = result['api_key']
        
        # Validate it
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIsNotNone(key_info)
        self.assertEqual(key_info['user_id'], self.test_user_id)
        self.assertEqual(key_info['name'], "Validation Test Key")
        self.assertIn('chatbot:query', key_info['scopes'])
    
    def test_3_validate_api_key_rejects_invalid_key(self):
        """Test API key validation rejects invalid keys"""
        # Test with invalid format
        result = self.manager.validate_api_key("invalid_key")
        self.assertIsNone(result)
        
        # Test with wrong prefix
        result = self.manager.validate_api_key("wrong_prefix_abc123")
        self.assertIsNone(result)
        
        # Test with non-existent key
        result = self.manager.validate_api_key("fik_nonexistentkey123456789012345678901234567890")
        self.assertIsNone(result)
    
    def test_4_validate_api_key_rejects_expired_key(self):
        """Test API key validation rejects expired keys"""
        # Generate key with expiration in the past
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Expired Key",
            expires_days=-1  # Expired yesterday
        )
        api_key = result['api_key']
        
        # Manually set expiration in database
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            UPDATE api_keys
            SET expires_at = ?
            WHERE user_id = ? AND key_prefix = ?
        """, (
            (datetime.utcnow() - timedelta(days=1)).isoformat(),
            self.test_user_id,
            result['key_info']['key_prefix']
        ), fetch=False)
        
        # Should reject expired key
        key_info = self.manager.validate_api_key(api_key)
        self.assertIsNone(key_info)
    
    def test_5_tenant_isolation_works(self):
        """Test tenant isolation in API keys"""
        # Generate keys for different tenants
        result1 = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Tenant 1 Key",
            tenant_id="tenant_1"
        )
        
        result2 = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Tenant 2 Key",
            tenant_id="tenant_2"
        )
        
        # Validate both keys
        key_info1 = self.manager.validate_api_key(result1['api_key'])
        key_info2 = self.manager.validate_api_key(result2['api_key'])
        
        self.assertEqual(key_info1['tenant_id'], "tenant_1")
        self.assertEqual(key_info2['tenant_id'], "tenant_2")
        self.assertNotEqual(key_info1['tenant_id'], key_info2['tenant_id'])
    
    def test_6_rate_limit_tracking(self):
        """Test rate limit checking and usage recording"""
        # Generate key
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Rate Limit Test Key",
            rate_limit_per_minute=5,
            rate_limit_per_hour=100
        )
        api_key = result['api_key']
        
        # Get key info
        key_info = self.manager.validate_api_key(api_key)
        api_key_id = key_info['api_key_id']
        
        # Check initial rate limit (should allow)
        rate_limit = self.manager.check_rate_limit(api_key_id, 'minute')
        self.assertTrue(rate_limit['allowed'])
        self.assertEqual(rate_limit['limit'], 5)
        self.assertGreaterEqual(rate_limit['remaining'], 4)
        
        # Record some usage
        for i in range(3):
            self.manager.record_usage(
                api_key_id=api_key_id,
                endpoint="/api/public/chatbot/query",
                ip_address="127.0.0.1",
                response_status=200,
                response_time_ms=100
            )
        
        # Check rate limit again (should still allow, but less remaining)
        rate_limit = self.manager.check_rate_limit(api_key_id, 'minute')
        self.assertTrue(rate_limit['allowed'])
        self.assertLessEqual(rate_limit['remaining'], 2)
    
    def test_7_revoke_api_key(self):
        """Test API key revocation"""
        # Generate key
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Revocation Test Key"
        )
        api_key = result['api_key']
        
        # Validate it works
        key_info = self.manager.validate_api_key(api_key)
        self.assertIsNotNone(key_info)
        api_key_id = key_info['api_key_id']
        
        # Revoke it
        revoked = self.manager.revoke_api_key(api_key_id, self.test_user_id)
        self.assertTrue(revoked)
        
        # Should no longer validate
        key_info = self.manager.validate_api_key(api_key)
        self.assertIsNone(key_info)
    
    def test_8_list_api_keys(self):
        """Test listing API keys for a user"""
        # Generate multiple keys
        result1 = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Key 1"
        )
        result2 = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Key 2"
        )
        
        # List keys
        keys = self.manager.list_api_keys(self.test_user_id)
        
        # Should have at least 2 keys
        self.assertGreaterEqual(len(keys), 2)
        
        # Check key names are present
        key_names = [k['name'] for k in keys]
        self.assertIn("Key 1", key_names)
        self.assertIn("Key 2", key_names)
        
        # Check structure
        for key in keys:
            self.assertIn('id', key)
            self.assertIn('key_prefix', key)
            self.assertIn('name', key)
            self.assertIn('scopes', key)
            self.assertIn('is_active', key)
    
    def test_9_custom_scopes(self):
        """Test API keys with custom scopes"""
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Custom Scopes Key",
            scopes=["chatbot:query", "ai:analyze", "custom:scope"]
        )
        
        key_info = self.manager.validate_api_key(result['api_key'])
        
        self.assertIn("chatbot:query", key_info['scopes'])
        self.assertIn("ai:analyze", key_info['scopes'])
        self.assertIn("custom:scope", key_info['scopes'])
        self.assertEqual(len(key_info['scopes']), 3)
    
    def test_10_custom_rate_limits(self):
        """Test API keys with custom rate limits"""
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Custom Rate Limits Key",
            rate_limit_per_minute=10,
            rate_limit_per_hour=500
        )
        
        key_info = self.manager.validate_api_key(result['api_key'])
        api_key_id = key_info['api_key_id']
        
        rate_limit = self.manager.check_rate_limit(api_key_id, 'minute')
        self.assertEqual(rate_limit['limit'], 10)
        
        rate_limit = self.manager.check_rate_limit(api_key_id, 'hour')
        self.assertEqual(rate_limit['limit'], 500)


if __name__ == '__main__':
    unittest.main()
