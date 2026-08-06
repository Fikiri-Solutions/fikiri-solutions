#!/usr/bin/env python3
"""
JWT auth manager unit tests.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.jwt_auth import JWTAuthManager


class TestJWTAuthManager(unittest.TestCase):
    def setUp(self):
        self.manager = JWTAuthManager()

    @patch('core.auth_session_version.get_auth_session_version', return_value=1)
    @patch('core.auth_session_version.ensure_auth_session_version_column')
    @patch('core.jwt_auth.jwt.encode')
    @patch('core.jwt_auth.db_optimizer')
    def test_generate_tokens_persists_refresh(self, mock_db, mock_encode, _ensure, _asv):
        mock_encode.return_value = 'access-token'
        mock_db.execute_query.return_value = None
        self.manager.redis_client = None

        tokens = self.manager.generate_tokens(
            user_id=1,
            user_data={'email': 'test@example.com', 'role': 'user'},
            device_info='agent',
            ip_address='127.0.0.1'
        )

        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        self.assertIn('expires_in', tokens)
        self.assertEqual(tokens['token_type'], 'Bearer')
        self.assertTrue(mock_db.execute_query.called)
        # asv must be embedded in access payload
        payload = mock_encode.call_args[0][0]
        self.assertEqual(payload.get('asv'), 1)


if __name__ == '__main__':
    unittest.main()
