#!/usr/bin/env python3
"""
Onboarding route tests (JWT-protected endpoints).
Covers all facets:
- POST /api/onboarding: step 1 validation (name + company required), auth, empty body.
- GET /api/onboarding/status: completed vs not completed, step, auth.
- GET /api/onboarding/resume: redirect_to /dashboard when completed, recommended_step and redirect_to when not, auth.
Note: /onboarding-flow -> /onboarding redirect is frontend-only (App.tsx).
"""

import unittest
import json
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class TestOnboardingRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.auth_header = {'Authorization': 'Bearer testtoken'}

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('core.app_onboarding.db_optimizer')
    def test_save_onboarding_success(self, mock_db, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = None

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={
            'name': 'Test User',
            'company': 'Test Co',
            'industry': 'SaaS'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('user_id'), 1)

    @patch('core.jwt_auth.get_jwt_manager')
    def test_save_onboarding_missing_name(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={
            'company': 'Test Co'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'MISSING_NAME')

    @patch('core.jwt_auth.get_jwt_manager')
    def test_save_onboarding_missing_company(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={
            'name': 'Test User'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'MISSING_COMPANY')

    @patch('core.jwt_auth.get_jwt_manager')
    def test_save_onboarding_empty_body(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertIn(data.get('code'), ('MISSING_NAME', 'MISSING_COMPANY', 'EMPTY_BODY'))

    @patch('core.jwt_auth.get_jwt_manager')
    def test_save_onboarding_requires_auth(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = None

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={
            'name': 'Test', 'company': 'Co'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))

    # --- GET /api/onboarding/status ---
    @patch('core.jwt_auth.get_jwt_manager')
    @patch('core.app_onboarding.db_optimizer')
    def test_onboarding_status_completed(self, mock_db, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.side_effect = [
            [{'name': 'Test', 'company': 'Test Co', 'industry': 'SaaS'}],
            [{'onboarding_completed': 1, 'onboarding_step': 4}]
        ]

        response = self.client.get('/api/onboarding/status', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('data', {}).get('completed'))
        self.assertEqual(data.get('data', {}).get('step'), 4)

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('core.app_onboarding.db_optimizer')
    def test_onboarding_status_not_completed(self, mock_db, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.side_effect = [
            [],
            [{'onboarding_completed': 0, 'onboarding_step': 1}]
        ]

        response = self.client.get('/api/onboarding/status', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertFalse(data.get('data', {}).get('completed'))
        self.assertEqual(data.get('data', {}).get('step'), 1)

    @patch('core.jwt_auth.get_jwt_manager')
    def test_onboarding_status_requires_auth(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = None

        response = self.client.get('/api/onboarding/status', headers=self.auth_header)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))

    # --- GET /api/onboarding/resume ---
    @patch('core.jwt_auth.get_jwt_manager')
    @patch('core.app_onboarding.db_optimizer')
    def test_onboarding_resume_completed_redirects_dashboard(self, mock_db, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'onboarding_completed': 1, 'onboarding_step': 4}]

        response = self.client.get('/api/onboarding/resume', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('data', {}).get('completed'))
        self.assertEqual(data.get('data', {}).get('redirect_to'), '/dashboard')

    @patch('core.jwt_auth.get_jwt_manager')
    @patch('core.app_onboarding.db_optimizer')
    def test_onboarding_resume_not_completed_returns_step(self, mock_db, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}
        mock_db.execute_query.return_value = [{'onboarding_completed': 0, 'onboarding_step': 2}]

        response = self.client.get('/api/onboarding/resume', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertFalse(data.get('data', {}).get('completed'))
        self.assertEqual(data.get('data', {}).get('recommended_step'), 2)
        self.assertIn('step=2', data.get('data', {}).get('redirect_to', ''))

    @patch('core.jwt_auth.get_jwt_manager')
    def test_onboarding_resume_requires_auth(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = None

        response = self.client.get('/api/onboarding/resume', headers=self.auth_header)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))


if __name__ == '__main__':
    unittest.main()
