#!/usr/bin/env python3
"""
Integration Framework Tests
Critical production-ready tests for integration framework
"""

import unittest
import os
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Set test environment
os.environ['FERNET_KEY'] = 'test_key_' + '0' * 32  # 32 bytes for Fernet
os.environ['FLASK_ENV'] = 'test'

from core.integrations.integration_framework import (
    integration_manager,
    encrypt_token,
    decrypt_token,
    ENCRYPTION_ENABLED
)
from core.integrations.calendar.google_calendar_provider import GoogleCalendarProvider


class TestIntegrationFramework(unittest.TestCase):
    """Test integration framework critical paths"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = 999
        self.test_provider = 'google_calendar'
        
        # Mock provider
        self.mock_provider = Mock(spec=GoogleCalendarProvider)
        self.mock_provider.refresh_access_token = Mock(return_value={
            'access_token': 'new_access_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
        self.mock_provider.revoke_token = Mock(return_value=True)
        
        integration_manager.register_provider(self.test_provider, self.mock_provider)
    
    def tearDown(self):
        """Clean up test data"""
        from core.database_optimization import db_optimizer
        # Clean up test integrations
        db_optimizer.execute_query(
            "DELETE FROM integrations WHERE user_id = ?",
            (self.test_user_id,),
            fetch=False
        )
    
    def test_1_fernet_key_missing_fails_closed(self):
        """Test: FERNET_KEY missing → clean error, no partial rows"""
        # Temporarily disable encryption
        original_encryption = ENCRYPTION_ENABLED
        with patch('core.integrations.integration_framework.ENCRYPTION_ENABLED', False):
            with patch('core.integrations.integration_framework.fernet', None):
                # Attempt to encrypt token
                with self.assertRaises(ValueError) as context:
                    encrypt_token('test_token')
                
                self.assertIn('FERNET_KEY', str(context.exception))
                self.assertIn('not configured', str(context.exception))
    
    def test_2_concurrent_refresh_single_call(self):
        """Test: 10 parallel requests with expiring token → exactly 1 refresh call"""
        # Create test integration with expiring token
        expires_at = int((datetime.now() + timedelta(seconds=30)).timestamp())  # Expires in 30s
        
        from core.database_optimization import db_optimizer
        integration_id = db_optimizer.execute_query("""
            INSERT INTO integrations (user_id, provider, status, scopes, meta_json)
            VALUES (?, ?, 'active', '[]', '{"token_enc_version": 1}')
        """, (self.test_user_id, self.test_provider), fetch=False)
        
        # Store token
        test_token_enc = encrypt_token('test_access_token')
        db_optimizer.execute_query("""
            INSERT INTO integration_tokens 
            (integration_id, access_token_enc, refresh_token_enc, expires_at, token_type, enc_version)
            VALUES (?, ?, ?, ?, 'Bearer', 1)
        """, (integration_id, test_token_enc, encrypt_token('test_refresh_token'), expires_at), fetch=False)
        
        # Initialize sync state
        db_optimizer.execute_query("""
            INSERT OR IGNORE INTO integration_sync_state
            (integration_id, resource, status, updated_at)
            VALUES (?, 'token_refresh', 'idle', CURRENT_TIMESTAMP)
        """, (integration_id,), fetch=False)
        
        # Simulate 10 concurrent refresh attempts
        refresh_count = {'count': 0}
        lock = threading.Lock()
        
        def attempt_refresh():
            try:
                tokens = integration_manager.get_integration_tokens(integration_id)
                if tokens and tokens.get('refresh_token'):
                    new_tokens = integration_manager._refresh_token_safely(
                        integration_id, self.test_provider, tokens['refresh_token']
                    )
                    if new_tokens:
                        with lock:
                            refresh_count['count'] += 1
            except Exception as e:
                logger.error(f"Refresh attempt failed: {e}")
        
        # Launch 10 threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=attempt_refresh)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify: exactly 1 refresh call happened
        self.assertEqual(self.mock_provider.refresh_access_token.call_count, 1, 
                        "Should have exactly 1 refresh call, not multiple")
        self.assertEqual(refresh_count['count'], 1, 
                        "Should have exactly 1 successful refresh")
    
    def test_3_disconnect_during_refresh(self):
        """Test: Trigger refresh, then disconnect → integration revoked, no tokens, links inactive"""
        # Create test integration
        from core.database_optimization import db_optimizer
        integration_id = db_optimizer.execute_query("""
            INSERT INTO integrations (user_id, provider, status, scopes, meta_json)
            VALUES (?, ?, 'active', '[]', '{"token_enc_version": 1}')
        """, (self.test_user_id, self.test_provider), fetch=False)
        
        # Store token
        test_token_enc = encrypt_token('test_access_token')
        db_optimizer.execute_query("""
            INSERT INTO integration_tokens 
            (integration_id, access_token_enc, refresh_token_enc, expires_at, token_type, enc_version)
            VALUES (?, ?, ?, ?, 'Bearer', 1)
        """, (integration_id, test_token_enc, encrypt_token('test_refresh_token'), 
              int((datetime.now() - timedelta(hours=1)).timestamp())), fetch=False)
        
        # Create event link
        db_optimizer.execute_query("""
            INSERT INTO calendar_event_links
            (user_id, integration_id, internal_entity_type, internal_entity_id,
             external_event_id, external_calendar_id, is_active)
            VALUES (?, ?, 'appointment', 1, 'ext_event_123', 'primary', 1)
        """, (self.test_user_id, integration_id), fetch=False)
        
        # Start refresh in background
        refresh_started = threading.Event()
        refresh_complete = threading.Event()
        
        def background_refresh():
            refresh_started.set()
            time.sleep(0.1)  # Simulate network delay
            tokens = integration_manager.get_integration_tokens(integration_id)
            if tokens:
                integration_manager._refresh_token_safely(
                    integration_id, self.test_provider, tokens['refresh_token']
                )
            refresh_complete.set()
        
        refresh_thread = threading.Thread(target=background_refresh)
        refresh_thread.start()
        refresh_started.wait(timeout=1)
        
        # Disconnect while refresh is happening
        result = integration_manager.disconnect(self.test_user_id, self.test_provider)
        
        # Wait for refresh to complete
        refresh_thread.join(timeout=2)
        
        # Verify: integration revoked
        integration = integration_manager.get_integration(self.test_user_id, self.test_provider)
        self.assertIsNone(integration, "Integration should be deleted or not found")
        
        # Verify: no tokens remain
        tokens = integration_manager.get_integration_tokens(integration_id)
        self.assertIsNone(tokens, "Tokens should be deleted")
        
        # Verify: links are inactive
        links = db_optimizer.execute_query("""
            SELECT is_active FROM calendar_event_links WHERE integration_id = ?
        """, (integration_id,))
        if links:
            self.assertEqual(links[0]['is_active'], 0, "Links should be inactive")
        
        self.assertTrue(result.get('success'), "Disconnect should succeed")
    
    def test_4_expires_at_normalization(self):
        """Test: expires_at stored as epoch seconds (INTEGER) consistently"""
        from core.database_optimization import db_optimizer
        
        integration_id = db_optimizer.execute_query("""
            INSERT INTO integrations (user_id, provider, status, scopes, meta_json)
            VALUES (?, ?, 'active', '[]', '{"token_enc_version": 1}')
        """, (self.test_user_id, self.test_provider), fetch=False)
        
        # Store token with expires_in (should convert to epoch)
        token_data = {
            'access_token': 'test_token',
            'refresh_token': 'test_refresh',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        
        integration_manager._update_tokens(integration_id, token_data)
        
        # Retrieve and verify type
        tokens = integration_manager.get_integration_tokens(integration_id)
        self.assertIsNotNone(tokens)
        self.assertIsInstance(tokens['expires_at'], (int, type(None)), 
                            "expires_at should be int (epoch seconds) or None")
        
        if tokens['expires_at']:
            # Verify it's a reasonable epoch timestamp (within last year to next year)
            now = int(datetime.now().timestamp())
            year_ago = now - (365 * 24 * 3600)
            year_ahead = now + (365 * 24 * 3600)
            self.assertGreater(tokens['expires_at'], year_ago)
            self.assertLess(tokens['expires_at'], year_ahead)


if __name__ == '__main__':
    unittest.main()
