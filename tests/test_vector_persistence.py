#!/usr/bin/env python3
"""
Vector Index Persistence Tests
Tests that Chatbot Builder properly persists FAQs and documents to vector index
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, Mock

# Set test environment
os.environ['FLASK_ENV'] = 'test'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVectorPersistence(unittest.TestCase):
    """Test vector index persistence from Chatbot Builder"""
    
    @patch('core.chatbot_smart_faq_api.get_vector_search')
    @patch('core.chatbot_smart_faq_api.faq_system.add_faq')
    def test_1_faq_persists_to_vector_index(self, mock_add_faq, mock_get_vector_search):
        """Test that FAQ creation persists to vector index"""
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()
        
        # Mock FAQ creation
        mock_add_faq.return_value = 123
        
        # Mock vector search
        mock_vector_search = MagicMock()
        mock_vector_search.add_document.return_value = "vector_123"
        mock_get_vector_search.return_value = mock_vector_search
        
        # Create FAQ
        response = client.post('/api/chatbot/faq',
                              json={
                                  'question': 'What are your hours?',
                                  'answer': 'We are open 9am-5pm',
                                  'category': 'general'
                              })
        
        # Verify FAQ was created
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['faq_id'], 123)
        
        # Verify vector search was called
        mock_get_vector_search.assert_called()
        mock_vector_search.add_document.assert_called_once()
        
        # Verify content includes question and answer
        call_args = mock_vector_search.add_document.call_args
        content = call_args.kwargs.get('content') if call_args.kwargs else call_args[0][0]
        self.assertIn('What are your hours?', content)
        self.assertIn('We are open 9am-5pm', content)
        
        # Verify metadata
        metadata = call_args.kwargs.get('metadata') if call_args.kwargs else call_args[0][1]
        self.assertEqual(metadata['type'], 'faq')
        self.assertEqual(metadata['faq_id'], 123)
    
    @patch('core.chatbot_smart_faq_api.get_vector_search')
    @patch('core.chatbot_smart_faq_api.knowledge_base.add_document')
    def test_2_knowledge_document_persists_to_vector_index(self, mock_add_doc, mock_get_vector_search):
        """Test that knowledge base document creation persists to vector index"""
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()
        
        # Mock document creation
        mock_add_doc.return_value = 456
        
        # Mock vector search
        mock_vector_search = MagicMock()
        mock_vector_search.add_document.return_value = "vector_456"
        mock_get_vector_search.return_value = mock_vector_search
        
        # Create document
        response = client.post('/api/chatbot/knowledge/documents',
                              json={
                                  'title': 'Product Guide',
                                  'content': 'This is a comprehensive product guide...',
                                  'category': 'product'
                              })
        
        # Verify document was created
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['document_id'], 456)
        
        # Verify vector search was called
        mock_get_vector_search.assert_called()
        mock_vector_search.add_document.assert_called_once()
        
        # Verify content includes title and content
        call_args = mock_vector_search.add_document.call_args
        content = call_args.kwargs.get('content') if call_args.kwargs else call_args[0][0]
        self.assertIn('Product Guide', content)
        self.assertIn('comprehensive product guide', content)
        
        # Verify metadata
        metadata = call_args.kwargs.get('metadata') if call_args.kwargs else call_args[0][1]
        self.assertEqual(metadata['type'], 'knowledge_base')
        self.assertEqual(metadata['document_id'], 456)
    
    @patch('core.chatbot_smart_faq_api.get_vector_search')
    @patch('core.chatbot_smart_faq_api.faq_system.add_faq')
    def test_3_vector_persistence_failure_doesnt_break_faq_creation(self, mock_add_faq, mock_get_vector_search):
        """Test that vector persistence failure doesn't break FAQ creation"""
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()
        
        # Mock FAQ creation
        mock_add_faq.return_value = 789
        
        # Mock vector search to raise exception
        mock_vector_search = MagicMock()
        mock_vector_search.add_document.side_effect = Exception("Vector service unavailable")
        mock_get_vector_search.return_value = mock_vector_search
        
        # Create FAQ (should still succeed even if vectorization fails)
        response = client.post('/api/chatbot/faq',
                              json={
                                  'question': 'Test question?',
                                  'answer': 'Test answer',
                                  'category': 'general'
                              })
        
        # Should still succeed
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['faq_id'], 789)
        # vector_id should be None if vectorization failed
        self.assertIsNone(data.get('vector_id'))


if __name__ == '__main__':
    unittest.main()
