#!/usr/bin/env python3
"""Test/debug routes tests."""

import unittest
import json
from unittest.mock import patch
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.test import test_bp


class TestTestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(test_bp)
        self.client = self.app.test_client()

    @patch("core.redis_connection_helper.is_redis_available", return_value=True)
    def test_debug_endpoint(self, mock_redis):
        response = self.client.get('/api/test/debug')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    def test_signup_step_invalid(self):
        response = self.client.post('/api/test/signup-step', json={"step": 99})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'INVALID_STEP')

    def test_openai_key_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.get('/api/test/openai-key')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'OPENAI_NOT_CONFIGURED')

    @patch("routes.test.get_current_user_id", return_value=1)
    @patch("crm.service.enhanced_crm_service")
    def test_crm_get_leads(self, mock_crm, mock_user_id):
        mock_crm.get_leads_summary.return_value = {"success": True, "data": {"leads": [], "analytics": {}}}
        response = self.client.post('/api/test/crm', json={"action": "get_leads"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('action'), 'get_leads')


if __name__ == '__main__':
    unittest.main()
