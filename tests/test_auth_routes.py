#!/usr/bin/env python3
"""
Authentication Route Tests
Focused unit tests with mocked dependencies.
"""

import unittest
import json
import time
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.auth import auth_bp


class TestAuthRoutes(unittest.TestCase):
    """Tests for /api/auth endpoints."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.secret_key = "test-secret"
        self.app.register_blueprint(auth_bp)
        self.client = self.app.test_client()

    @patch('routes.auth.email_job_manager')
    @patch('routes.auth.business_analytics')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.secure_session_manager')
    @patch('routes.auth.user_auth_manager')
    def test_login_success_includes_refresh_token(self, mock_user_auth, mock_session_mgr,
                                                  mock_log, mock_analytics, mock_email_jobs):
        mock_user_auth.authenticate_user.return_value = {
            'success': True,
            'user': {
                'id': 1,
                'email': 'test@example.com',
                'name': 'Test User',
                'role': 'user',
                'onboarding_completed': False,
                'onboarding_step': 1
            },
            'tokens': {
                'access_token': 'access',
                'refresh_token': 'refresh',
                'expires_in': 1800,
                'token_type': 'Bearer'
            }
        }
        mock_session_mgr.create_session.return_value = (
            'session-id',
            {
                'name': 'fikiri_session',
                'value': 'session-id',
                'httponly': True
            }
        )

        response = self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'Password123!'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('data', data)
        self.assertIn('access_token', data['data'])
        self.assertIn('refresh_token', data['data'])

    @patch('routes.auth.user_auth_manager')
    def test_login_invalid_credentials(self, mock_user_auth):
        mock_user_auth.authenticate_user.return_value = {
            'success': False,
            'error': 'Invalid email or password',
            'error_code': 'INVALID_CREDENTIALS'
        }

        response = self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrong'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'INVALID_CREDENTIALS')

    @patch('routes.auth.email_job_manager')
    @patch('routes.auth.business_analytics')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.secure_session_manager')
    @patch('routes.auth.get_jwt_manager')
    @patch('routes.auth.check_email_domain_has_mx_for_signup')
    @patch('routes.auth.user_auth_manager')
    def test_signup_success(
        self,
        mock_user_auth,
        mock_check_email_domain_has_mx,
        mock_get_jwt_mgr,
        mock_session_mgr,
        mock_log,
        mock_analytics,
        mock_email_jobs,
    ):
        mock_user_auth.create_user.return_value = {
            'success': True,
            'user': {
                'id': 2,
                'email': 'new@example.com',
                'name': 'New User',
                'role': 'user'
            }
        }
        mock_check_email_domain_has_mx.return_value = {
            "domain": "example.com",
            "has_mx": True,
            "mx_records": 1,
            "reason": "OK",
        }
        jwt_mgr = MagicMock()
        jwt_mgr.generate_tokens.return_value = {
            'access_token': 'access',
            'refresh_token': 'refresh',
            'expires_in': 1800,
            'token_type': 'Bearer'
        }
        mock_get_jwt_mgr.return_value = jwt_mgr
        mock_session_mgr.create_session.return_value = (
            'session-id',
            {
                'name': 'fikiri_session',
                'value': 'session-id',
                'httponly': True
            }
        )

        response = self.client.post('/api/auth/signup', json={
            'email': 'new@example.com',
            'password': 'Password123!'
            , 'name': 'New User'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('data', data)
        self.assertIn('tokens', data['data'])

    @patch('routes.auth.email_job_manager')
    @patch('routes.auth.business_analytics')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.secure_session_manager')
    @patch('routes.auth.get_jwt_manager')
    @patch('routes.auth.user_auth_manager')
    def test_signup_soft_validation_does_not_block(
        self,
        mock_user_auth,
        mock_get_jwt_mgr,
        mock_session_mgr,
        mock_log,
        mock_analytics,
        mock_email_jobs,
    ):
        """Signup should succeed even if helper validators fail (default behavior)."""
        # Ensure strict mode is disabled for this test.
        original = os.environ.get("FIKIRI_SIGNUP_STRICT_VALIDATION")
        os.environ.pop("FIKIRI_SIGNUP_STRICT_VALIDATION", None)
        try:
            mock_user_auth.create_user.return_value = {
                'success': True,
                'user': {
                    'id': 2,
                    'email': 'new@example.com',
                    'name': 'New User',
                    'role': 'user'
                }
            }
            jwt_mgr = MagicMock()
            jwt_mgr.generate_tokens.return_value = {
                'access_token': 'access',
                'refresh_token': 'refresh',
                'expires_in': 1800,
                'token_type': 'Bearer'
            }
            mock_get_jwt_mgr.return_value = jwt_mgr
            mock_session_mgr.create_session.return_value = (
                'session-id',
                {
                    'name': 'fikiri_session',
                    'value': 'session-id',
                    'httponly': True
                }
            )

            response = self.client.post('/api/auth/signup', json={
                'email': 'not-an-email',
                'password': 'short',
                'name': 'New User',
            })

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data.get('success'))
            self.assertIn('validation_warnings', data['data'])
            self.assertEqual(
                data['data']['validation_warnings'][0]['code'],
                'INVALID_EMAIL',
            )
            mock_user_auth.create_user.assert_called_once()
        finally:
            if original is None:
                os.environ.pop("FIKIRI_SIGNUP_STRICT_VALIDATION", None)
            else:
                os.environ["FIKIRI_SIGNUP_STRICT_VALIDATION"] = original

    @patch('routes.auth.email_job_manager')
    @patch('routes.auth.business_analytics')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.secure_session_manager')
    @patch('routes.auth.get_jwt_manager')
    @patch('routes.auth.user_auth_manager')
    def test_signup_strict_validation_blocks_invalid_email(
        self,
        mock_user_auth,
        mock_get_jwt_mgr,
        mock_session_mgr,
        mock_log,
        mock_analytics,
        mock_email_jobs,
    ):
        """In strict mode, invalid inputs should be rejected."""
        original = os.environ.get("FIKIRI_SIGNUP_STRICT_VALIDATION")
        os.environ["FIKIRI_SIGNUP_STRICT_VALIDATION"] = "1"
        try:
            response = self.client.post('/api/auth/signup', json={
                'email': 'not-an-email',
                'password': 'Password123!',
                'name': 'New User',
            })

            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertFalse(data.get('success'))
            self.assertEqual(data.get('code'), 'INVALID_EMAIL')
            mock_user_auth.create_user.assert_not_called()
        finally:
            if original is None:
                os.environ.pop("FIKIRI_SIGNUP_STRICT_VALIDATION", None)
            else:
                os.environ["FIKIRI_SIGNUP_STRICT_VALIDATION"] = original

    @patch('routes.auth.db_optimizer')
    @patch('routes.auth.get_jwt_manager')
    def test_refresh_token_uses_db_user(self, mock_get_jwt_mgr, mock_db):
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'test@example.com', 'name': 'Test', 'role': 'user'}]
        jwt_mgr.generate_tokens.return_value = {
            'access_token': 'access',
            'refresh_token': 'refresh',
            'expires_in': 1800,
            'token_type': 'Bearer'
        }
        mock_get_jwt_mgr.return_value = jwt_mgr

        response = self.client.post('/api/auth/refresh', headers={
            'Authorization': 'Bearer validtoken'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('tokens', data.get('data', {}))

    @patch('routes.auth.get_jwt_manager')
    def test_refresh_token_accepts_refresh_token_body(self, mock_get_jwt_mgr):
        """Expired access tokens can be renewed via refresh_token in JSON body."""
        jwt_mgr = MagicMock()
        jwt_mgr.refresh_access_token.return_value = {
            'access_token': 'new_access',
            'refresh_token': 'new_refresh',
            'expires_in': 1800,
            'token_type': 'Bearer',
        }
        jwt_mgr.verify_access_token.return_value = {'user_id': 42}
        mock_get_jwt_mgr.return_value = jwt_mgr

        response = self.client.post(
            '/api/auth/refresh',
            json={'refresh_token': 'valid_refresh'},
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('user_id'), 42)
        jwt_mgr.refresh_access_token.assert_called_once_with('valid_refresh')

    @patch('routes.auth.db_optimizer')
    def test_whoami_fetches_latest_user(self, mock_db):
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'test@example.com', 'name': 'Test', 'role': 'user'}]

        response = self.client.get('/api/auth/whoami')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('user', data.get('data', {}))

    @patch('routes.auth.db_optimizer')
    def test_whoami_accepts_post_same_as_get(self, mock_db):
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'test@example.com', 'name': 'Test', 'role': 'user'}]

        response = self.client.post('/api/auth/whoami')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('user', data.get('data', {}))

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.user_auth_manager')
    def test_forgot_password_success(self, mock_user_auth, mock_log, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_user_auth.request_password_reset.return_value = {"success": True}
        response = self.client.post('/api/auth/forgot-password', json={'email': 'a@b.com'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch('core.rate_limiter.enhanced_rate_limiter')
    def test_forgot_password_missing_email(self, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        response = self.client.post('/api/auth/forgot-password', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_EMAIL')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    def test_reset_password_empty_body(self, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        response = self.client.post('/api/auth/reset-password', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'EMPTY_REQUEST_BODY')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    def test_reset_password_weak_password(self, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        response = self.client.post('/api/auth/reset-password', json={'token': 't', 'new_password': '123'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'WEAK_PASSWORD')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('routes.auth.db_optimizer')
    def test_reset_password_invalid_token(self, mock_db, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_db.execute_query.return_value = []
        response = self.client.post('/api/auth/reset-password', json={'token': 'bad', 'new_password': 'Password123!'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'INVALID_TOKEN')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    def test_verify_email_missing_token(self, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        response = self.client.get('/api/auth/verify-email')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_TOKEN')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('routes.auth.user_auth_manager')
    def test_verify_email_invalid_token(self, mock_user_auth, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_user_auth.verify_email_token.return_value = {
            'success': False,
            'error': 'Invalid or expired verification token',
            'error_code': 'INVALID_TOKEN'
        }

        response = self.client.get('/api/auth/verify-email?token=bad')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'INVALID_TOKEN')

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.user_auth_manager')
    def test_verify_email_success(self, mock_user_auth, mock_log, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_user_auth.verify_email_token.return_value = {
            'success': True,
            'user': {
                'id': 1,
                'email': 'a@b.com',
                'name': 'User',
                'role': 'user',
                'onboarding_completed': False,
                'onboarding_step': 1,
                'email_verified': True
            }
        }

        response = self.client.get('/api/auth/verify-email?token=good')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('data', {}).get('email_verified'))

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.db_optimizer')
    @patch('routes.auth.user_auth_manager')
    def test_resend_email_verification_success(self, mock_user_auth, mock_db, mock_get_jwt, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_get_jwt.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'a@b.com', 'name': 'User', 'email_verified': 0}]
        mock_user_auth.request_email_verification.return_value = {'success': True, 'message': 'Verification email queued'}

        response = self.client.post('/api/auth/resend-email-verification', headers={'Authorization': 'Bearer token'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.db_optimizer')
    @patch('routes.auth.user_auth_manager')
    def test_resend_email_verification_already_verified(self, mock_user_auth, mock_db, mock_get_jwt, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_get_jwt.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'a@b.com', 'name': 'User', 'email_verified': 1}]

        response = self.client.post('/api/auth/resend-email-verification', headers={'Authorization': 'Bearer token'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        mock_user_auth.request_email_verification.assert_not_called()

    @patch('core.rate_limiter.enhanced_rate_limiter')
    @patch('routes.auth.log_security_event')
    @patch('routes.auth.user_auth_manager')
    @patch('routes.auth.db_optimizer')
    def test_reset_password_success(self, mock_db, mock_user_auth, mock_log, mock_rate):
        mock_rate.check_rate_limit.return_value = type("R", (), {"allowed": True, "retry_after": 0, "limit": 10, "remaining": 9})()
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'a@b.com', 'metadata': {}}]
        mock_user_auth.reset_user_password.return_value = {'success': True}
        response = self.client.post('/api/auth/reset-password', json={'token': 't', 'new_password': 'Password123!'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch('core.rate_limiter.enhanced_rate_limiter')
    def test_reset_rate_limit_success(self, mock_rate):
        mock_rate.reset_rate_limit.return_value = None
        response = self.client.post('/api/auth/reset-rate-limit')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch('core.secure_sessions.get_current_user_id', return_value=None)
    def test_gmail_status_missing_user(self, mock_get_user):
        response = self.client.get('/api/auth/gmail/status')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'AUTHENTICATION_REQUIRED')

    @patch('routes.auth.db_optimizer')
    @patch('core.secure_sessions.get_current_user_id', return_value=1)
    def test_gmail_status_connected_from_db(self, mock_get_user, mock_db):
        mock_db.execute_query.return_value = [{
            'access_token_enc': 'enc',
            'access_token': None,
            'expiry_timestamp': str(int(time.time()) + 3600),
            'scopes_json': '["scope"]',
            'updated_at': 'now'
        }]
        response = self.client.get('/api/auth/gmail/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', {}).get('connected'))

    @patch('core.secure_sessions.get_current_user_id', return_value=None)
    def test_outlook_status_missing_user(self, mock_get_user):
        response = self.client.get('/api/auth/outlook/status')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('data', {}).get('connected'))

    def test_gmail_disconnect_requires_user(self):
        response = self.client.post('/api/auth/gmail/disconnect', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_USER_ID')

    @patch('routes.auth.db_optimizer')
    @patch('core.oauth_token_manager.oauth_token_manager')
    def test_gmail_disconnect_success(self, mock_oauth, mock_db):
        mock_db.execute_query.return_value = [{'access_token': 'token', 'access_token_enc': None, 'refresh_token_enc': None}]
        with patch('requests.post') as mock_post:
            response = self.client.post('/api/auth/gmail/disconnect', json={'user_id': 1})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    def test_outlook_disconnect_requires_user(self):
        response = self.client.post('/api/auth/outlook/disconnect', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_USER_ID')

    @patch('routes.auth.db_optimizer')
    @patch('core.oauth_token_manager.oauth_token_manager')
    def test_outlook_disconnect_success(self, mock_oauth, mock_db):
        mock_db.execute_query.return_value = [{'access_token': 'token', 'access_token_enc': None, 'refresh_token_enc': None, 'tenant_id': 't'}]
        with patch('requests.get') as mock_get:
            response = self.client.post('/api/auth/outlook/disconnect', json={'user_id': 1})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    def test_logout_options(self):
        response = self.client.open('/api/auth/logout', method='OPTIONS', headers={'Origin': 'http://localhost:5174'})
        self.assertEqual(response.status_code, 200)

    @patch('routes.auth.secure_session_manager')
    def test_logout_post(self, mock_sessions):
        response = self.client.post('/api/auth/logout', headers={'Origin': 'http://localhost:5174'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.user_auth_manager')
    @patch('routes.auth.get_current_user_id', return_value=1)
    def test_change_password_success(self, mock_user_id, mock_user_auth, mock_get_jwt):
        """POST /api/auth/change-password happy path."""
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_get_jwt.return_value = jwt_mgr
        mock_user_auth.change_password.return_value = {
            'success': True,
            'message': 'Password changed successfully'
        }

        response = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': 'Bearer validtoken'},
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword123!',
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(
            data.get('data', {}).get('message'),
            'Password changed successfully',
        )
        mock_user_auth.change_password.assert_called_once_with(
            1, 'OldPassword123!', 'NewPassword123!'
        )

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.get_current_user_id', return_value=1)
    def test_change_password_missing_fields(self, mock_user_id, mock_get_jwt):
        """Missing fields should return 400 with MISSING_FIELDS code."""
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_get_jwt.return_value = jwt_mgr

        response = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': 'Bearer validtoken'},
            json={'current_password': 'x'},  # no new_password
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_FIELDS')

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.get_current_user_id', return_value=1)
    def test_change_password_weak_password(self, mock_user_id, mock_get_jwt):
        """Too-short new password should be rejected."""
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_get_jwt.return_value = jwt_mgr

        response = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': 'Bearer validtoken'},
            json={'current_password': 'OldPassword123!', 'new_password': '123'},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'WEAK_PASSWORD')

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('routes.auth.user_auth_manager')
    @patch('routes.auth.get_current_user_id', return_value=1)
    def test_change_password_invalid_current(self, mock_user_id, mock_user_auth, mock_get_jwt):
        """Backend error from change_password should surface appropriate error_code."""
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_get_jwt.return_value = jwt_mgr
        mock_user_auth.change_password.return_value = {
            'success': False,
            'error': 'Current password is incorrect',
            'error_code': 'INVALID_CURRENT_PASSWORD',
        }

        response = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': 'Bearer validtoken'},
            json={
                'current_password': 'WrongPassword!',
                'new_password': 'NewPassword123!',
            },
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'INVALID_CURRENT_PASSWORD')


if __name__ == '__main__':
    unittest.main()
