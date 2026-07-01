#!/usr/bin/env python3
"""
UserAuthManager unit tests (core auth primitives).
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.user_auth import UserAuthManager, _normalize_email


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

    def test_normalize_email_strips_and_lowercases(self):
        self.assertEqual(_normalize_email("  User@Example.COM  "), "user@example.com")

    @patch('email_automation.jobs.email_job_manager')
    @patch('core.user_auth.db_optimizer')
    def test_request_password_reset_preserves_metadata_salt(self, mock_db, mock_email_mgr):
        existing_salt = "abc123salt"
        mock_db.execute_query.side_effect = [
            [{'id': 7, 'email': 'user@example.com', 'name': 'User', 'metadata': json.dumps({'salt': existing_salt})}],
            None,
        ]
        mock_email_mgr.queue_password_reset_email.return_value = "reset_job_1"
        mock_email_mgr.process_job_by_id.return_value = 1

        result = self.manager.request_password_reset("User@Example.COM")

        self.assertTrue(result.get('success'))
        update_call = mock_db.execute_query.call_args_list[1]
        updated_metadata = json.loads(update_call[0][1][0])
        self.assertEqual(updated_metadata.get('salt'), existing_salt)
        self.assertIn('reset_token', updated_metadata)
        self.assertIn('reset_token_expires', updated_metadata)
        mock_email_mgr.queue_password_reset_email.assert_called_once()
        mock_email_mgr.process_job_by_id.assert_called_once_with("reset_job_1")

    @patch('core.user_auth.db_optimizer')
    def test_authenticate_user_uses_case_insensitive_lookup(self, mock_db):
        mock_db.sql_cast_int_eq_one.return_value = "is_active = 1"
        mock_db.execute_query.return_value = []

        self.manager.authenticate_user("User@Example.COM", "Password123!")

        query_sql = mock_db.execute_query.call_args[0][0]
        self.assertIn("LOWER(email)", query_sql)
        self.assertEqual(mock_db.execute_query.call_args[0][1], ("user@example.com",))

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
