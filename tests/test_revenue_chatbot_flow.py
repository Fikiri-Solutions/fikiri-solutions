#!/usr/bin/env python3
"""Revenue-critical chatbot flow tests."""

import json
import os
import sys
from unittest.mock import patch, Mock

import pytest
from flask import Flask
from core.public_chatbot_api import public_chatbot_bp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(public_chatbot_bp)
    return app.test_client()


class TestRevenueChatbotFlow:
    @patch('core.public_chatbot_api._check_plan_access')
    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.LLMRouter')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    @patch('core.public_chatbot_api.api_key_manager.record_usage')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.context_system.start_conversation')
    def test_chatbot_flow_vector_llm_schema(self, mock_start_conv, mock_kb_search,
                                            mock_faq_search, mock_record, mock_rate_limit,
                                            mock_validate, mock_llm_router, mock_vector_search,
                                            mock_flags, mock_plan, client, caplog):
        mock_validate.return_value = {
            'api_key_id': 1,
            'user_id': 5,
            'key_prefix': 'test1234',
            'name': 'Test Key',
            'tenant_id': 'tenant_a',
            'scopes': ['chatbot:query'],
            'rate_limit_per_minute': 60,
            'rate_limit_per_hour': 1000
        }
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}
        mock_flags.return_value.is_enabled.return_value = True
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}

        mock_faq_result = Mock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result

        mock_kb_result = Mock()
        mock_kb_result.success = True
        mock_kb_result.results = []
        mock_kb_search.return_value = mock_kb_result

        mock_start_conv.return_value.conversation_id = "conv_1"
        mock_vector_search.return_value.search_similar.return_value = [
            {"document": "Pricing info", "similarity": 0.9, "metadata": {"id": "doc_1"}}
        ]

        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "Our pricing starts at $29.",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": ["doc_1"]
            }),
            "trace_id": "trace_1"
        }
        mock_llm_router.return_value = mock_llm

        response = client.post('/api/public/chatbot/query',
                               json={'query': 'pricing?'},
                               headers={'X-API-Key': 'fik_test_key'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['schema_version'] == 'v1'
        assert data['response'] == 'Our pricing starts at $29.'
        assert data['sources']
        mock_vector_search.return_value.search_similar.assert_called_once()
        mock_llm.process.assert_called_once()

    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    def test_chatbot_rate_limit_enforced(self, mock_rate_limit, mock_validate, client):
        mock_validate.return_value = {
            'api_key_id': 1,
            'user_id': 5,
            'key_prefix': 'test1234',
            'name': 'Test Key',
            'tenant_id': 'tenant_a',
            'scopes': ['chatbot:query'],
            'rate_limit_per_minute': 60,
            'rate_limit_per_hour': 1000
        }
        mock_rate_limit.return_value = {'allowed': False, 'remaining': 0, 'limit': 60}

        response = client.post('/api/public/chatbot/query',
                               json={'query': 'pricing?'},
                               headers={'X-API-Key': 'fik_test_key'})

        assert response.status_code == 429
        data = json.loads(response.data)
        assert data['error_code'] == 'RATE_LIMIT_EXCEEDED'
