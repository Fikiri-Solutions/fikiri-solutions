#!/usr/bin/env python3
"""
AI Analysis API Unit Tests
Tests for AI analysis endpoints with schema validation
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, Mock

# Set test environment
os.environ['FLASK_ENV'] = 'test'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.ai_analysis_api import ai_analysis_bp


class TestAIAnalysisAPI(unittest.TestCase):
    """Test AI analysis API endpoints"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(ai_analysis_bp)
        self.client = self.app.test_client()
        
        # Mock API key info
        self.mock_api_key_info = {
            'api_key_id': 1,
            'user_id': 999,
            'scopes': ['ai:analyze'],
            'rate_limit_per_minute': 60
        }
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    def test_1_contact_analysis_requires_api_key(self, mock_record, mock_rate_limit, mock_validate):
        """Test contact analysis requires API key"""
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        response = self.client.post('/api/public/ai/analyze/contact',
                                   json={'name': 'John Doe', 'email': 'john@example.com'})
        
        self.assertEqual(response.status_code, 401)
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_contact')
    def test_2_contact_analysis_validates_schema(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test contact analysis validates request schema"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        # Missing required field (email)
        response = self.client.post('/api/public/ai/analyze/contact',
                                   json={'name': 'John Doe'},
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_contact')
    def test_3_contact_analysis_works(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test contact analysis endpoint works with valid data"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        # Mock AI analysis result (analyze_contact returns body, correlation_id)
        mock_analyze.return_value = (
            {
                'score': 85,
                'engagement_level': 'high',
                'recommended_actions': ['Follow up'],
                'insights': ['High value contact'],
                'risk_factors': [],
                'opportunities': ['Potential deal'],
            },
            'corr-contact-1',
        )
        
        response = self.client.post('/api/public/ai/analyze/contact',
                                   json={
                                       'name': 'John Doe',
                                       'email': 'john@example.com',
                                       'company': 'Acme Corp',
                                       'correlation_id': 'from-body',
                                   },
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertEqual(data['analysis']['contact_score'], 85)
        self.assertEqual(data['analysis']['engagement_level'], 'high')
        self.assertEqual(data['correlation_id'], 'corr-contact-1')
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_lead')
    def test_4_lead_analysis_works(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test lead analysis endpoint works"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        mock_analyze.return_value = (
            {
                'score': 75,
                'conversion_probability': 0.75,
                'priority': 'high',
                'recommended_actions': ['Qualify'],
                'insights': ['Strong intent'],
                'next_steps': ['Schedule call'],
                'estimated_value': 50000,
            },
            'corr-lead-1',
        )
        
        response = self.client.post('/api/public/ai/analyze/lead',
                                   json={
                                       'name': 'Jane Smith',
                                       'email': 'jane@example.com',
                                       'company': 'Tech Corp',
                                       'source': 'website'
                                   },
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertEqual(data['analysis']['lead_score'], 75)
        self.assertEqual(data['analysis']['conversion_probability'], 0.75)
        self.assertEqual(data['correlation_id'], 'corr-lead-1')
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_business')
    def test_5_business_analysis_works(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test business analysis endpoint works"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        mock_analyze.return_value = (
            {
                'business_name': 'Acme Corp',
                'industry': 'Technology',
                'size_category': 'medium',
                'key_insights': ['Growing company'],
                'market_position': 'Established',
                'growth_potential': 'high',
                'recommendations': ['Focus on retention'],
            },
            'corr-biz-1',
        )
        
        response = self.client.post('/api/public/ai/analyze/business',
                                   json={
                                       'business_name': 'Acme Corporation',
                                       'industry': 'Technology',
                                       'employee_count': 100
                                   },
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertEqual(data['summary']['size_category'], 'medium')
        self.assertEqual(data['correlation_id'], 'corr-biz-1')
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    def test_6_invalid_email_format_rejected(self, mock_rate_limit, mock_validate):
        """Test that invalid email format is rejected"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        response = self.client.post('/api/public/ai/analyze/contact',
                                   json={
                                       'name': 'John Doe',
                                       'email': 'invalid-email'  # Invalid format
                                   },
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)

    @patch('core.ai_analysis_api.ai_budget_guardrails.evaluate')
    @patch('core.ai_analysis_api.check_tier_usage_cap')
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_contact')
    def test_7_tier_cap_receives_int_from_numeric_string_user_id(
        self, mock_analyze, mock_record, mock_rate_limit, mock_validate, mock_tier, mock_eval,
    ):
        mock_validate.return_value = {**self.mock_api_key_info, 'user_id': '999'}
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_tier.return_value = (True, '', '')
        mock_eval.return_value = MagicMock(allowed=True)
        mock_analyze.return_value = (
            {'score': 1, 'engagement_level': 'low', 'recommended_actions': [], 'insights': [],
             'risk_factors': [], 'opportunities': []},
            'corr-x',
        )
        self.client.post(
            '/api/public/ai/analyze/contact',
            json={'name': 'John Doe', 'email': 'john@example.com'},
            headers={'X-API-Key': 'fik_test_key'},
        )
        mock_tier.assert_called_once_with(999, 'ai_responses', projected_increment=1)
        mock_eval.assert_called_once_with(999, projected_increment=1)

    @patch('core.ai_analysis_api.ai_budget_guardrails.evaluate')
    @patch('core.ai_analysis_api.ai_budget_guardrails.record_ai_usage')
    @patch('core.ai_analysis_api.check_tier_usage_cap')
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_contact')
    def test_8_non_numeric_api_key_user_id_skips_tier_and_ai_usage(
        self, mock_analyze, mock_record, mock_rate_limit, mock_validate, mock_tier, mock_record_ai, mock_eval,
    ):
        mock_validate.return_value = {**self.mock_api_key_info, 'user_id': 'not-numeric'}
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_analyze.return_value = (
            {'score': 1, 'engagement_level': 'low', 'recommended_actions': [], 'insights': [],
             'risk_factors': [], 'opportunities': []},
            'corr-y',
        )
        self.client.post(
            '/api/public/ai/analyze/contact',
            json={'name': 'John Doe', 'email': 'john@example.com'},
            headers={'X-API-Key': 'fik_test_key'},
        )
        mock_tier.assert_not_called()
        mock_eval.assert_not_called()
        mock_record_ai.assert_not_called()


class TestCallLLMJson(unittest.TestCase):
    @patch('core.ai_analysis_api.llm_router')
    def test_returns_none_when_validated_false(self, mock_lr):
        from core.ai_analysis_api import _call_llm_json
        mock_lr.client.is_enabled.return_value = True
        mock_lr.process.return_value = {
            'success': True,
            'validated': False,
            'content': '{}',
            'correlation_id': 'c99',
        }
        out, cid = _call_llm_json('prompt', correlation_id='c0')
        self.assertIsNone(out)
        self.assertEqual(cid, 'c99')


if __name__ == '__main__':
    unittest.main()
