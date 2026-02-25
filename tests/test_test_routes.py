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

    @patch("routes.test.user_auth_manager")
    def test_signup_step_valid(self, mock_auth):
        mock_auth.create_user.return_value = {"success": True, "user": {"id": 1}}
        response = self.client.post('/api/test/signup-step', json={"step": 1, "email": "a@b.com"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('step'), 1)

    def test_openai_key_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.get('/api/test/openai-key')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'OPENAI_NOT_CONFIGURED')

    @patch("routes.test.MinimalEmailParser")
    def test_email_parser_success(self, mock_parser):
        mock_parser.return_value.parse_message.return_value = {"subject": "Test"}
        response = self.client.post('/api/test/email-parser', json={"email_content": "Subject: Test\n\nBody"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    def test_email_actions_requires_body(self):
        response = self.client.post('/api/test/email-actions', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'EMPTY_REQUEST_BODY')

    @patch("routes.test.MinimalEmailActions")
    def test_email_actions_success(self, mock_actions):
        mock_actions.return_value.execute_action.return_value = {"success": True}
        response = self.client.post('/api/test/email-actions', json={"action_type": "mark_read"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch("routes.test.get_current_user_id", return_value=1)
    @patch("crm.service.enhanced_crm_service")
    def test_crm_get_leads(self, mock_crm, mock_user_id):
        mock_crm.get_leads_summary.return_value = {"success": True, "data": {"leads": [], "analytics": {}}}
        response = self.client.post('/api/test/crm', json={"action": "get_leads"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('action'), 'get_leads')

    @patch("routes.test.MinimalAIEmailAssistant")
    def test_ai_assistant_no_key(self, mock_ai):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post('/api/test/ai-assistant', json={})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertFalse(data.get('data', {}).get('stats', {}).get('api_key_configured'))

    @patch("routes.test.MinimalMLScoring")
    def test_ml_scoring_success(self, mock_scorer):
        mock_scorer.return_value.calculate_lead_score.side_effect = [
            {"total_score": 80, "priority": "high", "individual_scores": {"a": 1}, "model_type": "x", "recommended_action": "y", "confidence": 0.8},
            {"total_score": 10, "priority": "low", "individual_scores": {"a": 0.1}, "model_type": "x", "recommended_action": "y", "confidence": 0.3},
        ]
        response = self.client.post('/api/test/ml-scoring', json={})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    def test_ai_test_missing_body(self):
        response = self.client.post('/api/ai/test', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'EMPTY_REQUEST_BODY')

    @patch("routes.test.create_ai_assistant")
    def test_ai_test_success(self, mock_ai):
        mock_ai.return_value.test_functionality.return_value = {"ok": True}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}):
            response = self.client.post('/api/ai/test', json={"test_type": "response_generation", "prompt": "Hi"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))


if __name__ == '__main__':
    unittest.main()
