#!/usr/bin/env python3
"""
Onboarding route tests (JWT-protected endpoints).
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
    def test_save_onboarding_missing_fields(self, mock_jwt_mgr):
        mock_jwt_mgr.return_value.verify_access_token.return_value = {'user_id': 1}

        response = self.client.post('/api/onboarding', headers=self.auth_header, json={
            'company': 'Test Co'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'MISSING_NAME')

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


if __name__ == '__main__':
    unittest.main()
