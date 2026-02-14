#!/usr/bin/env python3
"""
Authentication Route Tests
Focused unit tests with mocked dependencies.
"""

import unittest
import json
from unittest.mock import patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class TestAuthRoutes(unittest.TestCase):
    """Tests for /api/auth endpoints."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
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
    @patch('routes.auth.jwt_auth_manager')
    @patch('routes.auth.user_auth_manager')
    def test_signup_success(self, mock_user_auth, mock_jwt_mgr, mock_session_mgr,
                            mock_log, mock_analytics, mock_email_jobs):
        mock_user_auth.create_user.return_value = {
            'success': True,
            'user': {
                'id': 2,
                'email': 'new@example.com',
                'name': 'New User',
                'role': 'user'
            }
        }
        mock_jwt_mgr.generate_tokens.return_value = {
            'access_token': 'access',
            'refresh_token': 'refresh',
            'expires_in': 1800,
            'token_type': 'Bearer'
        }
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

    @patch('routes.auth.db_optimizer')
    @patch('routes.auth.jwt_auth_manager')
    def test_refresh_token_uses_db_user(self, mock_jwt_mgr, mock_db):
        mock_jwt_mgr.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'test@example.com', 'name': 'Test', 'role': 'user'}]
        mock_jwt_mgr.generate_tokens.return_value = {
            'access_token': 'access',
            'refresh_token': 'refresh',
            'expires_in': 1800,
            'token_type': 'Bearer'
        }

        response = self.client.post('/api/auth/refresh', headers={
            'Authorization': 'Bearer validtoken'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('tokens', data.get('data', {}))

    @patch('routes.auth.db_optimizer')
    def test_whoami_fetches_latest_user(self, mock_db):
        mock_db.execute_query.return_value = [{'id': 1, 'email': 'test@example.com', 'name': 'Test', 'role': 'user'}]

        response = self.client.get('/api/auth/whoami')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertIn('user', data.get('data', {}))


if __name__ == '__main__':
    unittest.main()
