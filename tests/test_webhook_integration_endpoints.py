#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Integration Webhook Endpoints
Tests for POST /api/webhooks/forms/submit and POST /api/webhooks/leads/capture
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from core.webhook_api import webhook_bp


class TestWebhookIntegrationEndpoints(unittest.TestCase):
    """Comprehensive tests for integration webhook endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(webhook_bp)
        self.client = self.app.test_client()
        
        self.test_user_id = 999
        self.test_tenant_id = 'tenant-999'
        
        self.mock_key_info_full = {
            'api_key_id': 1,
            'user_id': self.test_user_id,
            'tenant_id': self.test_tenant_id,
            'scopes': ['webhooks:*', 'leads:*'],
            'allowed_origins': None
        }
        
        self.mock_key_info_restricted = {
            'api_key_id': 2,
            'user_id': self.test_user_id,
            'scopes': ['chatbot:query'],
            'allowed_origins': None
        }
        
        self.mock_key_info_origin_restricted = {
            'api_key_id': 3,
            'user_id': self.test_user_id,
            'tenant_id': self.test_tenant_id,
            'scopes': ['webhooks:forms', 'leads:create'],
            'allowed_origins': ['https://allowed-site.com']
        }
    
    def test_forms_submit_missing_api_key(self):
        """Test forms/submit requires API key"""
        response = self.client.post('/api/webhooks/forms/submit', json={'fields': {'email': 'test@example.com'}})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'MISSING_API_KEY')
    
    @patch('core.api_key_manager.api_key_manager')
    def test_forms_submit_invalid_api_key(self, mock_api_key_mgr):
        """Test forms/submit rejects invalid API key"""
        mock_api_key_mgr.validate_api_key.return_value = None
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'email': 'test@example.com'}},
            headers={'X-API-Key': 'invalid_key'}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error_code'], 'INVALID_API_KEY')
    
    @patch('core.api_key_manager.api_key_manager')
    def test_forms_submit_insufficient_scope(self, mock_api_key_mgr):
        """Test forms/submit requires correct scopes"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_restricted
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'email': 'test@example.com'}},
            headers={'X-API-Key': 'fik_test_key'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error_code'], 'INSUFFICIENT_SCOPE')
    
    @patch('core.api_key_manager.api_key_manager')
    def test_forms_submit_origin_not_allowed(self, mock_api_key_mgr):
        """Test forms/submit rejects non-allowed origins"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_origin_restricted
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'email': 'test@example.com'}},
            headers={'X-API-Key': 'fik_test_key', 'Origin': 'https://blocked-site.com'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error_code'], 'ORIGIN_NOT_ALLOWED')
    
    @patch('core.api_key_manager.api_key_manager')
    def test_forms_submit_missing_email(self, mock_api_key_mgr):
        """Test forms/submit requires email"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_full
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'name': 'John'}},
            headers={'X-API-Key': 'fik_test_key'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error_code'], 'MISSING_EMAIL')
    
    @patch('core.api_key_manager.api_key_manager')
    @patch('core.idempotency_manager.idempotency_manager')
    @patch('core.idempotency_manager.generate_deterministic_key')
    @patch('crm.service.enhanced_crm_service')
    def test_forms_submit_success(self, mock_crm, mock_gen_key, mock_idem, mock_api_key_mgr):
        """Test forms/submit successfully creates lead"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_full
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = 'test_key_123'
        mock_crm.create_lead.return_value = {'lead_id': 12345}
        
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'email': 'test@example.com', 'name': 'John'}},
            headers={'X-API-Key': 'fik_test_key'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['lead_id'], 12345)
        self.assertFalse(data['deduplicated'])
    
    @patch('core.api_key_manager.api_key_manager')
    @patch('core.idempotency_manager.idempotency_manager')
    @patch('core.idempotency_manager.generate_deterministic_key')
    def test_forms_submit_idempotency(self, mock_gen_key, mock_idem, mock_api_key_mgr):
        """Test forms/submit deduplicates duplicate submissions"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_full
        mock_idem.check_key.return_value = {'status': 'completed', 'response_data': {'lead_id': 12345}}
        mock_gen_key.return_value = 'test_key_123'
        
        response = self.client.post(
            '/api/webhooks/forms/submit',
            json={'fields': {'email': 'test@example.com'}},
            headers={'X-API-Key': 'fik_test_key'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['deduplicated'])
    
    def test_leads_capture_missing_api_key(self):
        """Test leads/capture requires API key"""
        response = self.client.post('/api/webhooks/leads/capture', json={'email': 'test@example.com'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error_code'], 'MISSING_API_KEY')
    
    @patch('core.api_key_manager.api_key_manager')
    @patch('core.idempotency_manager.idempotency_manager')
    @patch('core.idempotency_manager.generate_deterministic_key')
    @patch('crm.service.enhanced_crm_service')
    def test_leads_capture_success(self, mock_crm, mock_gen_key, mock_idem, mock_api_key_mgr):
        """Test leads/capture successfully creates lead"""
        mock_api_key_mgr.validate_api_key.return_value = self.mock_key_info_full
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = 'test_key_123'
        mock_crm.create_lead.return_value = {'lead_id': 12345}
        
        response = self.client.post(
            '/api/webhooks/leads/capture',
            json={'email': 'test@example.com', 'name': 'John'},
            headers={'X-API-Key': 'fik_test_key'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['lead_id'], 12345)


if __name__ == '__main__':
    unittest.main()
