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
        
        # Mock AI analysis result
        mock_analyze.return_value = {
            'score': 85,
            'engagement_level': 'high',
            'recommended_actions': ['Follow up'],
            'insights': ['High value contact'],
            'risk_factors': [],
            'opportunities': ['Potential deal']
        }
        
        response = self.client.post('/api/public/ai/analyze/contact',
                                   json={
                                       'name': 'John Doe',
                                       'email': 'john@example.com',
                                       'company': 'Acme Corp'
                                   },
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertEqual(data['analysis']['contact_score'], 85)
        self.assertEqual(data['analysis']['engagement_level'], 'high')
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_lead')
    def test_4_lead_analysis_works(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test lead analysis endpoint works"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        mock_analyze.return_value = {
            'score': 75,
            'conversion_probability': 0.75,
            'priority': 'high',
            'recommended_actions': ['Qualify'],
            'insights': ['Strong intent'],
            'next_steps': ['Schedule call'],
            'estimated_value': 50000
        }
        
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
    
    @patch('core.ai_analysis_api.api_key_manager.validate_api_key')
    @patch('core.ai_analysis_api.api_key_manager.check_rate_limit')
    @patch('core.ai_analysis_api.api_key_manager.record_usage')
    @patch('core.ai_analysis_api.analyze_business')
    def test_5_business_analysis_works(self, mock_analyze, mock_record, mock_rate_limit, mock_validate):
        """Test business analysis endpoint works"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        mock_analyze.return_value = {
            'business_name': 'Acme Corp',
            'industry': 'Technology',
            'size_category': 'medium',
            'key_insights': ['Growing company'],
            'market_position': 'Established',
            'growth_potential': 'high',
            'recommendations': ['Focus on retention']
        }
        
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


if __name__ == '__main__':
    unittest.main()
