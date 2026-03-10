#!/usr/bin/env python3
"""
Unit Tests for Replit Integration Package
Tests for integrations/replit/fikiri_replit/client.py and helpers

Covers:
- FikiriClient initialization
- Leads operations (create, capture)
- Chatbot operations (query)
- Forms operations (submit)
- Flask helpers
- FastAPI helpers
- Error handling
- Timeout handling
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, Mock
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

# Import Replit package
try:
    from integrations.replit.fikiri_replit.client import FikiriClient
    from integrations.replit.fikiri_replit.flask_helpers import FikiriFlaskHelper
    from integrations.replit.fikiri_replit.fastapi_helpers import FikiriFastAPIHelper
    REPLIT_PACKAGE_AVAILABLE = True
except ImportError:
    REPLIT_PACKAGE_AVAILABLE = False


@unittest.skipUnless(REPLIT_PACKAGE_AVAILABLE, "Replit package not available")
class TestFikiriClient(unittest.TestCase):
    """Test FikiriClient for Replit"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = 'fik_test_key_123'
        self.api_url = 'https://api.fikirisolutions.com'
        self.client = FikiriClient(api_key=self.api_key, api_url=self.api_url)
    
    def test_client_initialization(self):
        """Test FikiriClient initializes correctly"""
        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.api_url, self.api_url)
        self.assertIsNotNone(self.client.session)
        self.assertEqual(self.client.session.headers['X-API-Key'], self.api_key)
        self.assertEqual(self.client.session.headers['Content-Type'], 'application/json')
    
    def test_client_initialization_default_url(self):
        """Test FikiriClient uses default URL when not provided"""
        client = FikiriClient(api_key=self.api_key)
        self.assertEqual(client.api_url, 'https://api.fikirisolutions.com')
    
    def test_client_has_leads_subclient(self):
        """Test FikiriClient has leads sub-client"""
        self.assertIsNotNone(self.client.leads)
        self.assertTrue(hasattr(self.client.leads, 'create'))
        self.assertTrue(hasattr(self.client.leads, 'capture'))
    
    def test_client_has_chatbot_subclient(self):
        """Test FikiriClient has chatbot sub-client"""
        self.assertIsNotNone(self.client.chatbot)
        self.assertTrue(hasattr(self.client.chatbot, 'query'))
    
    def test_client_has_forms_subclient(self):
        """Test FikiriClient has forms sub-client"""
        self.assertIsNotNone(self.client.forms)
        self.assertTrue(hasattr(self.client.forms, 'submit'))
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_leads_create_success(self, mock_request):
        """Test leads.create successfully creates lead"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'lead_id': 12345,
            'message': 'Lead captured successfully'
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.leads.create(
            email='test@example.com',
            name='John Doe',
            phone='+1-555-123-4567',
            source='replit_app'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['lead_id'], 12345)
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'POST')
        self.assertIn('/api/webhooks/leads/capture', call_args[0][1])
        self.assertEqual(call_args[1]['json']['email'], 'test@example.com')
        self.assertEqual(call_args[1]['json']['name'], 'John Doe')
        self.assertEqual(call_args[1]['json']['source'], 'replit_app')
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_leads_create_minimal(self, mock_request):
        """Test leads.create with minimal required fields"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'lead_id': 12345}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.leads.create(email='test@example.com')
        
        self.assertTrue(result['success'])
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['email'], 'test@example.com')
        self.assertNotIn('name', call_args[1]['json'])
        self.assertNotIn('phone', call_args[1]['json'])
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_leads_create_with_metadata(self, mock_request):
        """Test leads.create with metadata"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'lead_id': 12345}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        metadata = {'referrer': 'google.com', 'campaign': 'summer-2024'}
        result = self.client.leads.create(
            email='test@example.com',
            metadata=metadata
        )
        
        self.assertTrue(result['success'])
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['metadata'], metadata)
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_leads_capture_alias(self, mock_request):
        """Test leads.capture is alias for leads.create"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'lead_id': 12345}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.leads.capture(email='test@example.com')
        
        self.assertTrue(result['success'])
        mock_request.assert_called_once()
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_chatbot_query_success(self, mock_request):
        """Test chatbot.query successfully queries chatbot"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'response': 'Hello! How can I help you?',
            'confidence': 0.95
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.chatbot.query('What are your business hours?')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['response'], 'Hello! How can I help you?')
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'POST')
        self.assertIn('/api/public/chatbot/query', call_args[0][1])
        self.assertEqual(call_args[1]['json']['query'], 'What are your business hours?')
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_chatbot_query_with_conversation_id(self, mock_request):
        """Test chatbot.query with conversation context"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'response': 'Follow-up answer'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.chatbot.query(
            query='Tell me more',
            conversation_id='conv_123'
        )
        
        self.assertTrue(result['success'])
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['conversation_id'], 'conv_123')
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_forms_submit_success(self, mock_request):
        """Test forms.submit successfully submits form"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'lead_id': 12345,
            'message': 'Form submitted successfully'
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        fields = {
            'email': 'test@example.com',
            'name': 'John Doe',
            'message': 'Hello'
        }
        result = self.client.forms.submit(
            form_id='contact-form',
            fields=fields,
            source='replit_app'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['lead_id'], 12345)
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'POST')
        self.assertIn('/api/webhooks/forms/submit', call_args[0][1])
        self.assertEqual(call_args[1]['json']['form_id'], 'contact-form')
        self.assertEqual(call_args[1]['json']['fields'], fields)
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_forms_submit_default_form_id(self, mock_request):
        """Test forms.submit uses default form_id"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'lead_id': 12345}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        result = self.client.forms.submit(fields={'email': 'test@example.com'})
        
        self.assertTrue(result['success'])
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['form_id'], 'custom-form')
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_request_timeout(self, mock_request):
        """Test that requests include timeout"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.client.leads.create(email='test@example.com')
        
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['timeout'], 30)
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_request_error_handling(self, mock_request):
        """Test that request errors are handled gracefully"""
        mock_request.side_effect = requests.exceptions.RequestException('Connection error')
        
        result = self.client.leads.create(email='test@example.com')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Connection error', result['error'])
    
    @patch('integrations.replit.fikiri_replit.client.requests.Session.request')
    def test_http_error_handling(self, mock_request):
        """Test that HTTP errors are handled gracefully"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Not Found')
        mock_request.return_value = mock_response
        
        result = self.client.leads.create(email='test@example.com')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


@unittest.skipUnless(REPLIT_PACKAGE_AVAILABLE, "Replit package not available")
class TestFikiriFlaskHelper(unittest.TestCase):
    """Test FikiriFlaskHelper"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = 'fik_test_key_123'
        self.helper = FikiriFlaskHelper(api_key=self.api_key)
    
    def test_helper_initialization(self):
        """Test FikiriFlaskHelper initializes correctly"""
        self.assertIsNotNone(self.helper.client)
        self.assertEqual(self.helper.client.api_key, self.api_key)
    
    def test_create_blueprint(self):
        """Test create_blueprint returns Flask Blueprint"""
        from flask import Flask
        bp = self.helper.create_blueprint()
        
        self.assertIsNotNone(bp)
        self.assertEqual(bp.name, 'fikiri')
        
        # Register and test endpoints exist
        app = Flask(__name__)
        app.register_blueprint(bp)
        client = app.test_client()
        
        # Test chatbot endpoint exists
        with patch('integrations.replit.fikiri_replit.flask_helpers.FikiriClient') as mock_client:
            mock_client.return_value.chatbot.query.return_value = {'success': True, 'response': 'Test'}
            response = client.post('/fikiri/chatbot', json={'query': 'test'})
            self.assertEqual(response.status_code, 200)
    
    def test_render_chatbot_widget(self):
        """Test render_chatbot_widget returns HTML"""
        html = self.helper.render_chatbot_widget(
            theme='dark',
            position='bottom-left',
            title='Chat Support'
        )
        
        self.assertIsInstance(html, str)
        self.assertIn('fikiri-sdk.js', html)
        self.assertIn('dark', html)
        self.assertIn('bottom-left', html)
        self.assertIn('Chat Support', html)
        self.assertIn(self.api_key, html)
    
    def test_render_lead_capture_form(self):
        """Test render_lead_capture_form returns HTML"""
        html = self.helper.render_lead_capture_form(
            fields=['email', 'name', 'phone'],
            title='Get in Touch'
        )
        
        self.assertIsInstance(html, str)
        self.assertIn('Get in Touch', html)
        self.assertIn('email', html)
        self.assertIn('name', html)
        self.assertIn('phone', html)
        self.assertIn('fikiri-sdk.js', html)
    
    def test_render_lead_capture_form_default_fields(self):
        """Test render_lead_capture_form uses default fields"""
        html = self.helper.render_lead_capture_form()
        
        self.assertIn('email', html)
        self.assertIn('name', html)
        # Phone field HTML not rendered, but phone handling code exists in JS (which is fine)
        # Check that phone input field is not in HTML
        self.assertNotIn('<input type="tel" name="phone"', html)


@unittest.skipUnless(REPLIT_PACKAGE_AVAILABLE, "Replit package not available")
class TestFikiriFastAPIHelper(unittest.TestCase):
    """Test FikiriFastAPIHelper"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = 'fik_test_key_123'
        self.helper = FikiriFastAPIHelper(api_key=self.api_key)
    
    def test_helper_initialization(self):
        """Test FikiriFastAPIHelper initializes correctly"""
        self.assertIsNotNone(self.helper.client)
        self.assertEqual(self.helper.client.api_key, self.api_key)
    
    def test_create_router(self):
        """Test create_router returns FastAPI APIRouter"""
        router = self.helper.create_router()
        
        self.assertIsNotNone(router)
        self.assertEqual(router.prefix, '/fikiri')
        
        # Verify routes exist
        routes = [route.path for route in router.routes]
        self.assertIn('/fikiri/chatbot', routes)
        self.assertIn('/fikiri/leads/capture', routes)
        self.assertIn('/fikiri/forms/submit', routes)


if __name__ == '__main__':
    unittest.main()
