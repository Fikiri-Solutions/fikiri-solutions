#!/usr/bin/env python3
"""
Public Chatbot API Unit Tests
Tests for public chatbot endpoint authentication, CORS, and functionality
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, Mock

# Set test environment
os.environ['FLASK_ENV'] = 'test'
os.environ.setdefault('SKIP_HEAVY_DEP_CHECKS', 'true')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.public_chatbot_api import public_chatbot_bp, require_api_key


class TestPublicChatbotAPI(unittest.TestCase):
    """Test public chatbot API endpoints"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(public_chatbot_bp)
        self.client = self.app.test_client()
        
        # Mock API key manager
        self.mock_api_key_info = {
            'api_key_id': 1,
            'user_id': 999,
            'key_prefix': 'test1234',
            'name': 'Test Key',
            'tenant_id': 'test_tenant',
            'scopes': ['chatbot:query'],
            'rate_limit_per_minute': 60,
            'rate_limit_per_hour': 1000
        }
    
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.api_key_manager.record_usage')
    def test_1_query_endpoint_requires_api_key(self, mock_record, mock_rate_limit, mock_validate):
        """Test that query endpoint requires API key"""
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        # Request without API key
        response = self.client.post('/api/public/chatbot/query',
                                   json={'query': 'test'})
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'MISSING_API_KEY')
    
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.api_key_manager.record_usage')
    def test_2_query_endpoint_rejects_invalid_api_key(self, mock_record, mock_rate_limit, mock_validate):
        """Test that query endpoint rejects invalid API keys"""
        mock_validate.return_value = None  # Invalid key
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        response = self.client.post('/api/public/chatbot/query',
                                   json={'query': 'test'},
                                   headers={'X-API-Key': 'fik_invalid_key'})
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'INVALID_API_KEY')
    
    @patch('core.public_chatbot_api._check_plan_access')
    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api.LLMRouter')
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.api_key_manager.record_usage')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.context_system.start_conversation')
    def test_3_query_endpoint_works_with_valid_key(self, mock_start_conv, mock_kb_search,
                                                   mock_faq_search, mock_record, mock_rate_limit,
                                                   mock_validate, mock_vector_search, mock_llm_router,
                                                   mock_flags, mock_plan):
        """Test that query endpoint works with valid API key"""
        # Setup mocks
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_flags.return_value.is_enabled.return_value = False
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}
        mock_vector_search.return_value.search_similar.return_value = []
        
        # Mock FAQ search
        mock_faq_result = Mock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result
        
        # Mock KB search
        mock_doc = Mock()
        mock_doc.id = "doc_1"
        mock_doc.title = "Hours"
        mock_doc.content = "We are open 9am-5pm."
        mock_kb_entry = Mock()
        mock_kb_entry.document = mock_doc
        mock_kb_entry.relevance_score = 0.9
        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = [mock_kb_entry]
        mock_kb_search.return_value = mock_kb_result
        
        # Mock conversation
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_123"
        mock_start_conv.return_value = mock_conversation

        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "Test response",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": []
            }),
            "trace_id": "trace_1"
        }
        mock_llm_router.return_value = mock_llm
        
        # Make request
        response = self.client.post('/api/public/chatbot/query',
                                   json={'query': 'What are your hours?'},
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['query'], 'What are your hours?')
        self.assertIn('response', data)
        self.assertIn('conversation_id', data)
        self.assertEqual(data['tenant_id'], 'test_tenant')
        self.assertEqual(data['schema_version'], 'v1')
        mock_llm.process.assert_called_once()
        
        # Verify usage was recorded
        mock_record.assert_called_once()
    
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    def test_4_query_endpoint_rate_limit_exceeded(self, mock_rate_limit, mock_validate):
        """Test that query endpoint enforces rate limits"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {
            'allowed': False,
            'remaining': 0,
            'limit': 60,
            'used': 60
        }
        
        response = self.client.post('/api/public/chatbot/query',
                                   json={'query': 'test'},
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'RATE_LIMIT_EXCEEDED')
    
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    def test_5_query_endpoint_missing_query(self, mock_rate_limit, mock_validate):
        """Test that query endpoint requires query parameter"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        
        response = self.client.post('/api/public/chatbot/query',
                                   json={},
                                   headers={'X-API-Key': 'fik_test_key'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'MISSING_QUERY')
    
    def test_6_health_endpoint_no_auth(self):
        """Test that health endpoint doesn't require authentication"""
        response = self.client.get('/api/public/chatbot/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_7_cors_headers_present(self):
        """Test that CORS headers are present in responses"""
        response = self.client.get('/api/public/chatbot/health')
        
        self.assertIn('Access-Control-Allow-Origin', response.headers)
        self.assertIn('Access-Control-Allow-Methods', response.headers)
        self.assertIn('Access-Control-Allow-Headers', response.headers)
    
    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.context_system.start_conversation')
    def test_8_bearer_token_auth(self, mock_start_conv, mock_kb_search, mock_faq_search,
                                 mock_rate_limit, mock_validate, mock_flags):
        """Test that Bearer token format works"""
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_flags.return_value.is_enabled.return_value = False

        mock_faq_result = Mock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result

        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = []
        mock_kb_search.return_value = mock_kb_result

        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_123"
        mock_start_conv.return_value = mock_conversation
        
        response = self.client.post('/api/public/chatbot/query',
                                   json={'query': 'test'},
                                   headers={'Authorization': 'Bearer fik_test_key'})
        
        # Should work (will fail on actual processing but auth should pass)
        # We're just testing the auth mechanism
        mock_validate.assert_called_once()

    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.LLMRouter')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.context_system.start_conversation')
    def test_9_vector_search_invoked_when_enabled(self, mock_start_conv, mock_kb_search, mock_faq_search,
                                                  mock_rate_limit, mock_validate, mock_llm_router,
                                                  mock_vector_search, mock_flags):
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_flags.return_value.is_enabled.return_value = True
        mock_vector_search.return_value.search_similar.return_value = []

        mock_faq_result = Mock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result

        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = []
        mock_kb_search.return_value = mock_kb_result

        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_123"
        mock_start_conv.return_value = mock_conversation

        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "Test response",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": []
            })
        }
        mock_llm_router.return_value = mock_llm

        self.client.post('/api/public/chatbot/query',
                         json={'query': 'test'},
                         headers={'X-API-Key': 'fik_test_key'})

        mock_vector_search.return_value.search_similar.assert_called_once()

    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api.enhanced_crm_service.create_lead')
    @patch('core.public_chatbot_api.enhanced_crm_service.add_lead_activity')
    @patch('core.public_chatbot_api.db_optimizer.execute_query')
    @patch('core.public_chatbot_api.LLMRouter')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.context_system.start_conversation')
    def test_10_lead_capture_stores_lead(self, mock_start_conv, mock_kb_search, mock_faq_search,
                                         mock_rate_limit, mock_validate, mock_llm_router,
                                         mock_execute, mock_add_activity, mock_create_lead,
                                         mock_flags):
        mock_validate.return_value = self.mock_api_key_info
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_flags.return_value.is_enabled.return_value = False

        mock_faq_result = Mock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result

        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = []
        mock_kb_search.return_value = mock_kb_result

        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_123"
        mock_start_conv.return_value = mock_conversation

        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "Test response",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": []
            })
        }
        mock_llm_router.return_value = mock_llm

        mock_execute.return_value = []
        mock_create_lead.return_value = {"success": True, "data": {"lead_id": 123}}

        response = self.client.post('/api/public/chatbot/query',
                                    json={'query': 'Contact me at test@example.com'},
                                    headers={'X-API-Key': 'fik_test_key'})

        data = json.loads(response.data)
        self.assertEqual(data.get("lead_id"), 123)
        mock_create_lead.assert_called_once()
        mock_add_activity.assert_called_once()


if __name__ == '__main__':
    unittest.main()
