#!/usr/bin/env python3
"""
UserAuthManager unit tests (core auth primitives).
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.user_auth import UserAuthManager


class TestUserAuthManager(unittest.TestCase):
    def setUp(self):
        self.manager = UserAuthManager()

    def test_hash_and_verify_password_roundtrip(self):
        password = "Password123!"
        password_hash, salt = self.manager._hash_password(password)
        self.assertTrue(self.manager._verify_password(password, password_hash, salt))
        self.assertFalse(self.manager._verify_password("wrong", password_hash, salt))

    def test_verify_password_handles_wrapped_salt(self):
        password = "Password123!"
        password_hash, salt = self.manager._hash_password(password)
        wrapped_salt = f'["{salt}"]'
        self.assertTrue(self.manager._verify_password(password, password_hash, wrapped_salt))

    def test_verify_legacy_password_sha256(self):
        import hashlib
        password = "legacy-pass"
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        self.assertTrue(self.manager._verify_legacy_password(password, legacy_hash))
        self.assertFalse(self.manager._verify_legacy_password("bad", legacy_hash))

    @patch('core.user_auth.db_optimizer')
    def test_create_user_duplicate_email(self, mock_db):
        mock_db.execute_query.return_value = [{'id': 1}]
        result = self.manager.create_user("test@example.com", "Password123!", "Test")
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'USER_EXISTS')

    @patch.object(UserAuthManager, 'revoke_all_user_sessions')
    @patch('core.user_auth.db_optimizer')
    @patch('core.jwt_auth.get_jwt_manager')
    def test_reset_user_password_revokes_refresh_tokens(self, mock_jwt_mgr, mock_db, mock_revoke_sessions):
        mock_db.execute_query.side_effect = [
            [{'metadata': '{}'}],
            None
        ]
        mock_jwt_mgr.return_value.revoke_all_refresh_tokens = MagicMock()

        result = self.manager.reset_user_password(1, "NewPassword123!")
        self.assertTrue(result.get('success'))
        mock_revoke_sessions.assert_called_once()
        mock_jwt_mgr.return_value.revoke_all_refresh_tokens.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main()
