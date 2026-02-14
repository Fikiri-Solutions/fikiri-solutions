#!/usr/bin/env python3
"""OAuth token manager tests."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.oauth_token_manager import OAuthTokenManager


class TestOAuthTokenManager(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.manager = OAuthTokenManager(db_optimizer=self.db)

    def test_encrypt_decrypt_roundtrip_base64(self):
        # Force base64 fallback by disabling crypto
        with patch('core.oauth_token_manager.CRYPTOGRAPHY_AVAILABLE', False):
            manager = OAuthTokenManager(db_optimizer=MagicMock())
            token = 'test-token'
            encrypted = manager.encrypt_token(token)
            decrypted = manager.decrypt_token(encrypted)
            self.assertEqual(decrypted, token)

    @patch('core.oauth_token_manager.db_optimizer')
    def test_store_tokens_success(self, mock_db):
        manager = OAuthTokenManager(db_optimizer=mock_db)
        token_data = {
            'access_token': 'access',
            'refresh_token': 'refresh',
            'expires_in': 3600,
            'token_type': 'Bearer',
            'scope': 'scope'
        }
        result = manager.store_tokens(1, 'gmail', token_data)
        self.assertTrue(result.get('success'))

    @patch('core.oauth_token_manager.db_optimizer')
    def test_get_tokens_inactive(self, mock_db):
        manager = OAuthTokenManager(db_optimizer=mock_db)
        mock_db.execute_query.return_value = []
        result = manager.get_tokens(1, 'gmail')
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'NO_TOKENS_FOUND')


if __name__ == '__main__':
    unittest.main()
