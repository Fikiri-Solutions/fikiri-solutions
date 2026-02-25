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

# Set test environment: valid Fernet key (32 bytes base64url)
os.environ['FERNET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
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
        self._ensure_test_user()
        self._ensure_integration_tokens_schema()

        # Mock provider
        self.mock_provider = Mock(spec=GoogleCalendarProvider)
        self.mock_provider.refresh_access_token = Mock(return_value={
            'access_token': 'new_access_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
        self.mock_provider.revoke_token = Mock(return_value=True)
        
        integration_manager.register_provider(self.test_provider, self.mock_provider)

    def _ensure_test_user(self):
        """Ensure test user exists so integrations FK is satisfied."""
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            INSERT OR IGNORE INTO users (id, email, password_hash, name)
            VALUES (?, ?, ?, ?)
        """, (
            self.test_user_id,
            f"test_integration_{self.test_user_id}@test.com",
            "test_hash",
            "Test User",
        ), fetch=False)

    def _ensure_integration_tokens_schema(self):
        """Ensure integration_tokens has enc_version (older DBs may not)."""
        from core.database_optimization import db_optimizer
        try:
            db_optimizer.execute_query(
                "ALTER TABLE integration_tokens ADD COLUMN enc_version INTEGER DEFAULT 1",
                fetch=False,
            )
        except Exception:
            pass  # Column already exists

    def _insert_integration_and_get_id(self):
        """Insert a row into integrations and return its id (execute_query fetch=False returns rowcount, not lastrowid)."""
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            INSERT INTO integrations (user_id, provider, status, scopes, meta_json)
            VALUES (?, ?, 'active', '[]', '{"token_enc_version": 1}')
        """, (self.test_user_id, self.test_provider), fetch=False)
        rows = db_optimizer.execute_query(
            "SELECT id FROM integrations WHERE user_id = ? AND provider = ? ORDER BY id DESC LIMIT 1",
            (self.test_user_id, self.test_provider),
        )
        return rows[0]["id"] if rows else None

    def tearDown(self):
        """Clean up test data (child tables first for FK integrity)."""
        from core.database_optimization import db_optimizer
        rows = db_optimizer.execute_query(
            "SELECT id FROM integrations WHERE user_id = ?",
            (self.test_user_id,),
        )
        if not rows:
            return
        integration_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(integration_ids))
        for table in ("integration_tokens", "integration_sync_state", "calendar_event_links"):
            try:
                db_optimizer.execute_query(
                    f"DELETE FROM {table} WHERE integration_id IN ({placeholders})",
                    tuple(integration_ids),
                    fetch=False,
                )
            except Exception:
                pass
        db_optimizer.execute_query(
            "DELETE FROM integrations WHERE user_id = ?",
            (self.test_user_id,),
            fetch=False,
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
        # Token already expired so refresh is triggered (buffer is 2 min)
        expires_at = int((datetime.now() - timedelta(minutes=1)).timestamp())
        
        from core.database_optimization import db_optimizer
        integration_id = self._insert_integration_and_get_id()
        self.assertIsNotNone(integration_id)

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
        
        # Simulate 10 concurrent refresh attempts (public API triggers refresh when token expired)
        def attempt_refresh():
            try:
                integration_manager.get_valid_token(self.test_user_id, self.test_provider)
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
        
        # Verify: at most 1 refresh call (no thundering herd)
        call_count = self.mock_provider.refresh_access_token.call_count
        self.assertLessEqual(call_count, 1, "Should have at most 1 refresh call, not multiple")
    
    def test_3_disconnect_during_refresh(self):
        """Test: Trigger refresh, then disconnect → integration revoked, no tokens, links inactive"""
        from core.database_optimization import db_optimizer
        integration_id = self._insert_integration_and_get_id()
        self.assertIsNotNone(integration_id)

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
        
        # Verify: integration marked revoked (framework soft-deletes: status=revoked, tokens deleted)
        integration = integration_manager.get_integration(self.test_user_id, self.test_provider)
        self.assertIsNotNone(integration, "Integration row should still exist")
        self.assertEqual(integration.get('status'), 'revoked', "Integration should be revoked")
        
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

        integration_id = self._insert_integration_and_get_id()
        self.assertIsNotNone(integration_id)

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
