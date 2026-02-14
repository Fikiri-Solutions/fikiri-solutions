#!/usr/bin/env python3
"""AI email analysis route tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class TestAIEmailAnalysis(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_analyze_email_requires_auth(self):
        response = self.client.post('/api/ai/analyze-email', json={
            'content': 'hello'
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'AUTHENTICATION_REQUIRED')

    @patch('routes.business.get_current_user_id')
    def test_analyze_email_missing_content(self, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post('/api/ai/analyze-email', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'MISSING_CONTENT')

    @patch('routes.business.get_current_user_id')
    @patch('email_automation.ai_assistant.MinimalAIEmailAssistant')
    def test_analyze_email_ai_unavailable(self, mock_ai, mock_get_user):
        mock_get_user.return_value = 1
        mock_ai.return_value.is_enabled.return_value = False

        response = self.client.post('/api/ai/analyze-email', json={
            'content': 'test',
            'subject': 'subj'
        })
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'AI_UNAVAILABLE')

    @patch('routes.business.get_current_user_id')
    @patch('email_automation.ai_assistant.MinimalAIEmailAssistant')
    def test_analyze_email_success(self, mock_ai, mock_get_user):
        mock_get_user.return_value = 1
        mock_ai.return_value.is_enabled.return_value = True
        mock_ai.return_value.classify_email_intent.return_value = {
            'intent': 'general_info',
            'urgency': 'low',
            'suggested_action': 'Review',
            'confidence': 0.9
        }

        response = self.client.post('/api/ai/analyze-email', json={
            'content': 'hello world',
            'subject': 'Hi'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        analysis = data.get('data', {})
        self.assertEqual(analysis.get('intent'), 'general_info')
        self.assertEqual(analysis.get('urgency'), 'low')


if __name__ == '__main__':
    unittest.main()
