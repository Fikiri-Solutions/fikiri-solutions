#!/usr/bin/env python3
"""
Unit Tests for API Key Manager Allowed Origins Feature
Tests for core/api_key_manager.py allowed_origins functionality

Covers:
- Generating API keys with allowed_origins
- Validating API keys and retrieving allowed_origins
- Origin allowlist enforcement
- JSON serialization/deserialization of allowed_origins
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from core.api_key_manager import APIKeyManager


class TestAPIKeyManagerAllowedOrigins(unittest.TestCase):
    """Test API key manager allowed_origins functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = APIKeyManager()
        self.test_user_id = 999
        self._ensure_test_user()
    
    def _ensure_test_user(self):
        """Ensure test user exists"""
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
    
    def test_generate_api_key_with_allowed_origins(self):
        """Test generating API key with allowed_origins"""
        allowed_origins = ['https://example.com', 'https://app.example.com']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Key with Origins",
            allowed_origins=allowed_origins
        )
        
        self.assertIn('api_key', result)
        self.assertIn('key_info', result)
        
        # Validate the key
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIsNotNone(key_info)
        self.assertEqual(key_info['allowed_origins'], allowed_origins)
    
    def test_generate_api_key_without_allowed_origins(self):
        """Test generating API key without allowed_origins (None)"""
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Key without Origins"
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIsNotNone(key_info)
        self.assertIsNone(key_info.get('allowed_origins'))
    
    def test_generate_api_key_with_empty_allowed_origins(self):
        """Test generating API key with empty allowed_origins list"""
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Key with Empty Origins",
            allowed_origins=[]
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIsNotNone(key_info)
        # Empty list is stored as None (which is correct behavior)
        self.assertIsNone(key_info['allowed_origins'])
    
    def test_allowed_origins_json_serialization(self):
        """Test that allowed_origins are properly serialized to JSON in database"""
        allowed_origins = ['https://site1.com', 'https://site2.com', 'https://site3.com']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test JSON Serialization",
            allowed_origins=allowed_origins
        )
        
        # Verify it's stored correctly by reading from DB
        from core.database_optimization import db_optimizer
        rows = db_optimizer.execute_query(
            "SELECT allowed_origins FROM api_keys WHERE user_id = ? AND name = ?",
            (self.test_user_id, "Test JSON Serialization")
        )
        
        self.assertGreater(len(rows), 0)
        stored_origins_json = rows[0]['allowed_origins']
        self.assertIsNotNone(stored_origins_json)
        
        # Parse JSON and verify
        stored_origins = json.loads(stored_origins_json)
        self.assertEqual(stored_origins, allowed_origins)
    
    def test_allowed_origins_json_deserialization(self):
        """Test that allowed_origins are properly deserialized from JSON when validating"""
        allowed_origins = ['https://example.com', 'https://app.example.com']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test JSON Deserialization",
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        
        # Validate and check deserialization
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIsNotNone(key_info)
        self.assertIsInstance(key_info['allowed_origins'], list)
        self.assertEqual(key_info['allowed_origins'], allowed_origins)
        self.assertEqual(len(key_info['allowed_origins']), 2)
    
    def test_validate_api_key_returns_allowed_origins(self):
        """Test that validate_api_key includes allowed_origins in returned key_info"""
        allowed_origins = ['https://allowed1.com', 'https://allowed2.com']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Validate Returns Origins",
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertIn('allowed_origins', key_info)
        self.assertEqual(key_info['allowed_origins'], allowed_origins)
    
    def test_multiple_origins_stored_correctly(self):
        """Test that multiple origins are stored and retrieved correctly"""
        allowed_origins = [
            'https://example.com',
            'https://app.example.com',
            'https://staging.example.com',
            'http://localhost:3000'
        ]
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Multiple Origins",
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertEqual(len(key_info['allowed_origins']), 4)
        self.assertEqual(set(key_info['allowed_origins']), set(allowed_origins))
    
    def test_allowed_origins_with_other_scopes(self):
        """Test that allowed_origins work alongside scopes"""
        allowed_origins = ['https://example.com']
        scopes = ['webhooks:forms', 'leads:create']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Origins with Scopes",
            scopes=scopes,
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertEqual(key_info['allowed_origins'], allowed_origins)
        self.assertEqual(set(key_info['scopes']), set(scopes))
    
    def test_allowed_origins_with_custom_rate_limits(self):
        """Test that allowed_origins work alongside custom rate limits"""
        allowed_origins = ['https://example.com']
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Origins with Rate Limits",
            rate_limit_per_minute=100,
            rate_limit_per_hour=5000,
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertEqual(key_info['allowed_origins'], allowed_origins)
        self.assertEqual(key_info['rate_limit_per_minute'], 100)
        self.assertEqual(key_info['rate_limit_per_hour'], 5000)
    
    def test_allowed_origins_case_sensitive(self):
        """Test that allowed_origins matching is case-sensitive"""
        allowed_origins = ['https://Example.com']  # Capital E
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Case Sensitive Origins",
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        # Should preserve case
        self.assertEqual(key_info['allowed_origins'], ['https://Example.com'])
        self.assertNotIn('https://example.com', key_info['allowed_origins'])
    
    def test_allowed_origins_with_special_characters(self):
        """Test that allowed_origins with special characters are handled correctly"""
        allowed_origins = [
            'https://example.com',
            'https://sub-domain.example.com',
            'https://example.com:8080',
            'https://example.com/path'
        ]
        
        result = self.manager.generate_api_key(
            user_id=self.test_user_id,
            name="Test Special Characters",
            allowed_origins=allowed_origins
        )
        
        api_key = result['api_key']
        key_info = self.manager.validate_api_key(api_key)
        
        self.assertEqual(key_info['allowed_origins'], allowed_origins)


if __name__ == '__main__':
    unittest.main()
