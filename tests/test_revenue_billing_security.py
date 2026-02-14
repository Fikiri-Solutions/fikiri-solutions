#!/usr/bin/env python3
"""Revenue-critical billing gate and security tests."""

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from core.public_chatbot_api import public_chatbot_bp
from core.webhook_api import webhook_bp
from routes.business import business_bp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(public_chatbot_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(business_bp)
    return app.test_client()


class TestRevenueBillingSecurity:
    @patch('core.public_chatbot_api.context_system.start_conversation')
    @patch('core.public_chatbot_api.knowledge_base.search')
    @patch('core.public_chatbot_api.faq_system.search_faqs')
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.get_feature_flags')
    @patch('core.public_chatbot_api._check_plan_access')
    @patch('core.public_chatbot_api.api_key_manager.record_usage')
    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    def test_plan_blocks_chatbot(self, mock_rate_limit, mock_validate, mock_record, mock_plan,
                                 mock_flags, mock_vector_search, mock_faq_search, mock_kb_search,
                                 mock_start_conv, client):
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
        mock_plan.return_value = {"plan": "free", "allow_llm": False}
        mock_flags.return_value.is_enabled.return_value = False
        mock_vector_search.return_value.search_similar.return_value = []
        mock_faq_result = MagicMock()
        mock_faq_result.success = True
        mock_faq_result.matches = []
        mock_faq_search.return_value = mock_faq_result
        mock_kb_result = MagicMock()
        mock_kb_result.success = True
        mock_kb_result.results = []
        mock_kb_search.return_value = mock_kb_result
        mock_start_conv.return_value.conversation_id = "conv_1"

        response = client.post('/api/public/chatbot/query',
                               json={'query': 'pricing?'},
                               headers={'X-API-Key': 'fik_test_key'})

        assert response.status_code == 402
        data = json.loads(response.data)
        assert data['error_code'] == 'PLAN_LIMIT_EXCEEDED'

    @patch('routes.business._require_paid_plan')
    @patch('routes.business.get_current_user_id')
    def test_plan_blocks_workflow_automation(self, mock_user, mock_plan, client):
        mock_user.return_value = 1
        mock_plan.return_value = False

        response = client.post('/api/workflows/followups/execute', json={})
        assert response.status_code == 402
        data = json.loads(response.data)
        assert data.get('code') == 'PLAN_LIMIT_EXCEEDED'

    @patch('core.webhook_api.get_webhook_service')
    def test_invalid_webhook_signature_rejected(self, mock_service, client, caplog):
        svc = MagicMock()
        svc.config.enable_verification = True
        svc.config.secret_key = "secret"
        svc.verify_webhook_signature.return_value = False
        mock_service.return_value = svc

        with caplog.at_level("WARNING"):
            response = client.post('/api/webhooks/tally', json={"data": {"email": "x@y.com"}})

        assert response.status_code == 401
        assert any("Invalid Tally webhook signature" in rec.message for rec in caplog.records)

    @patch('core.public_chatbot_api.api_key_manager.validate_api_key')
    @patch('core.public_chatbot_api.api_key_manager.check_rate_limit')
    def test_invalid_api_key_rejected(self, mock_rate_limit, mock_validate, client):
        mock_validate.return_value = None
        mock_rate_limit.return_value = {'allowed': True, 'remaining': 60, 'limit': 60}

        response = client.post('/api/public/chatbot/query',
                               json={'query': 'pricing?'},
                               headers={'X-API-Key': 'fik_invalid'})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_code'] == 'INVALID_API_KEY'

    def test_session_required_for_workflow(self, client):
        response = client.post('/api/workflows/tables/export', json={
            "name": "leads",
            "columns": ["email"],
            "rows": []
        })
        assert response.status_code == 401
