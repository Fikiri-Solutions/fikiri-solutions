#!/usr/bin/env python3
"""User routes tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.user import user_bp


def _auth_headers():
    return {"Authorization": "Bearer testtoken"}


class TestUserRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(user_bp)
        self.client = self.app.test_client()

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.db_optimizer")
    def test_get_user_profile_success(self, mock_db, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db.execute_query.return_value = [{
            "id": 1,
            "email": "a@example.com",
            "name": "A",
            "role": "user",
            "onboarding_completed": 1,
            "onboarding_step": 2,
            "metadata": "{}",
            "created_at": "now",
            "last_login": "now",
        }]
        response = self.client.get('/api/user/profile', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('user', {}).get('email'), "a@example.com")

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.db_optimizer")
    def test_get_user_profile_not_found(self, mock_db, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db.execute_query.return_value = []
        response = self.client.get('/api/user/profile', headers=_auth_headers())
        self.assertEqual(response.status_code, 404)

    @patch("routes.user.get_current_user_id", return_value=None)
    def test_update_user_profile_requires_auth(self, mock_user_id):
        response = self.client.put('/api/user/profile', json={"name": "X"})
        self.assertEqual(response.status_code, 401)

    @patch("routes.user.get_current_user_id", return_value=1)
    def test_update_user_profile_no_valid_fields(self, mock_user_id):
        response = self.client.put('/api/user/profile', json={"bad": "x"})
        self.assertEqual(response.status_code, 400)

    @patch("routes.user.user_auth_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    def test_update_user_profile_success(self, mock_user_id, mock_manager):
        mock_manager.update_user_profile.return_value = {
            "success": True,
            "user": {"id": 1, "name": "New"}
        }
        response = self.client.put('/api/user/profile', json={"name": "New"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('user', {}).get('name'), "New")

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    def test_update_onboarding_step_invalid(self, mock_user_id, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        response = self.client.put('/api/user/onboarding-step', headers=_auth_headers(), json={"step": 0})
        self.assertEqual(response.status_code, 400)

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.db_optimizer")
    @patch("routes.user.get_current_user_id", return_value=1)
    def test_update_onboarding_step_success(self, mock_user_id, mock_db, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        response = self.client.put('/api/user/onboarding-step', headers=_auth_headers(), json={"step": 4})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', {}).get('onboarding_completed'))

    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("core.oauth_token_manager.oauth_token_manager")
    def test_get_gmail_connect_status_connected(self, mock_oauth, mock_user_id):
        mock_oauth.get_token_status.return_value = {"success": True, "last_sync": "now", "expires_at": "later"}
        response = self.client.get('/api/user/gmail-connect-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', {}).get('connected'))

    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("routes.user.automation_safety_manager")
    def test_get_automation_status(self, mock_safety, mock_user_id):
        mock_safety.get_safety_status.return_value = {"automation_enabled": False, "safety_level": "strict"}
        response = self.client.get('/api/user/automation-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data.get('data', {}).get('automation_enabled'))

    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("crm.service.enhanced_crm_service")
    @patch("core.oauth_token_manager.oauth_token_manager")
    @patch("routes.user.user_auth_manager")
    def test_get_dashboard_data(self, mock_user_mgr, mock_oauth, mock_crm, mock_user_id):
        mock_crm.get_leads.return_value = []
        mock_oauth.get_token_status.return_value = {"success": True}
        mock_user_mgr.get_user_profile.return_value = {"name": "A", "onboarding_completed": True, "onboarding_step": 4}
        response = self.client.get('/api/user/dashboard-data')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('quick_stats', data.get('data', {}))

    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("crm.service.enhanced_crm_service")
    @patch("routes.user.user_auth_manager")
    def test_export_user_data(self, mock_user_mgr, mock_crm, mock_user_id):
        mock_user_mgr.get_user_profile.return_value = {"id": 1}
        mock_crm.get_leads.return_value = []
        response = self.client.post('/api/user/export-data', json={})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('export_status'), 'completed')


if __name__ == '__main__':
    unittest.main()
