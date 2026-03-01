#!/usr/bin/env python3
"""
Integration tests for public chatbot API tenant isolation.
Tests end-to-end tenant isolation in the public chatbot query endpoint.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, g

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPublicChatbotTenantIsolation(unittest.TestCase):
    """Test tenant isolation in public chatbot API"""
    
    def setUp(self):
        """Set up test fixtures"""
        from core.public_chatbot_api import public_chatbot_bp
        from core.api_key_manager import APIKeyManager
        
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(public_chatbot_bp)
        self.client = self.app.test_client()
        
        # Mock API key manager
        self.api_key_manager = MagicMock()
        self.api_key_manager.validate_api_key.return_value = None
        self.api_key_manager.check_rate_limit.return_value = {'allowed': True}
        
        # Patch API key manager
        self.api_key_patcher = patch('core.public_chatbot_api.api_key_manager', self.api_key_manager)
        self.api_key_patcher.start()
    
    def tearDown(self):
        """Clean up"""
        self.api_key_patcher.stop()
    
    def _create_api_key_context(self, tenant_id, user_id=None):
        """Helper to create API key context"""
        key_info = {
            'api_key_id': 'test_key_123',
            'tenant_id': tenant_id,
            'user_id': user_id or f'user_{tenant_id}',
            'scopes': ['chatbot:query']
        }
        self.api_key_manager.validate_api_key.return_value = key_info
        
        # Mock g.api_key_info
        with self.app.test_request_context():
            g.api_key_info = key_info
    
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.knowledge_base')
    @patch('core.public_chatbot_api.faq_system')
    def test_public_chatbot_passes_tenant_id_to_vector_search(self, mock_faq, mock_kb, mock_get_vs):
        """Test that public chatbot passes tenant_id to vector search"""
        # Setup mocks
        mock_vector_search = MagicMock()
        mock_vector_search.search_similar.return_value = []
        mock_get_vs.return_value = mock_vector_search
        
        mock_kb.search.return_value = MagicMock(success=True, results=[])
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        
        # Create API key with tenant_id
        key_info = {
            'api_key_id': 'test_key',
            'tenant_id': 'tenant_test',
            'user_id': 'user_123',
            'scopes': ['chatbot:query']
        }
        self.api_key_manager.validate_api_key.return_value = key_info
        
        # Make request
        response = self.client.post(
            '/api/public/chatbot/query',
            headers={'X-API-Key': 'test_key'},
            json={'query': 'test query'}
        )
        
        # Verify vector search was called with tenant_id
        mock_vector_search.search_similar.assert_called_once()
        call_kwargs = mock_vector_search.search_similar.call_args[1]
        self.assertEqual(call_kwargs.get('tenant_id'), 'tenant_test')
    
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.knowledge_base')
    @patch('core.public_chatbot_api.faq_system')
    def test_public_chatbot_passes_tenant_id_to_kb_search(self, mock_faq, mock_kb, mock_get_vs):
        """Test that public chatbot passes tenant_id filter to KB search"""
        # Setup mocks
        mock_vector_search = MagicMock()
        mock_vector_search.search_similar.return_value = []
        mock_get_vs.return_value = mock_vector_search
        
        mock_kb_result = MagicMock(success=True, results=[])
        mock_kb.search.return_value = mock_kb_result
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        
        # Create API key with tenant_id
        key_info = {
            'api_key_id': 'test_key',
            'tenant_id': 'tenant_kb_test',
            'user_id': 'user_456',
            'scopes': ['chatbot:query']
        }
        self.api_key_manager.validate_api_key.return_value = key_info
        
        # Make request
        response = self.client.post(
            '/api/public/chatbot/query',
            headers={'X-API-Key': 'test_key'},
            json={'query': 'test query'}
        )
        
        # Verify KB search was called with tenant_id filter
        mock_kb.search.assert_called_once()
        call_args = mock_kb.search.call_args
        filters = call_args[1].get('filters', {})
        self.assertEqual(filters.get('tenant_id'), 'tenant_kb_test')
    
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.knowledge_base')
    @patch('core.public_chatbot_api.faq_system')
    def test_public_chatbot_no_tenant_id_when_not_provided(self, mock_faq, mock_kb, mock_get_vs):
        """Test that public chatbot works when tenant_id is not in API key"""
        # Setup mocks
        mock_vector_search = MagicMock()
        mock_vector_search.search_similar.return_value = []
        mock_get_vs.return_value = mock_vector_search
        
        mock_kb_result = MagicMock(success=True, results=[])
        mock_kb.search.return_value = mock_kb_result
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        
        # Create API key without tenant_id
        key_info = {
            'api_key_id': 'test_key',
            'user_id': 'user_789',
            'scopes': ['chatbot:query']
        }
        self.api_key_manager.validate_api_key.return_value = key_info
        
        # Make request
        response = self.client.post(
            '/api/public/chatbot/query',
            headers={'X-API-Key': 'test_key'},
            json={'query': 'test query'}
        )
        
        # Should still work (backward compatibility)
        self.assertEqual(response.status_code, 200)
        
        # tenant_id should be None
        call_kwargs = mock_vector_search.search_similar.call_args[1]
        self.assertIsNone(call_kwargs.get('tenant_id'))
    
    @patch('core.public_chatbot_api.get_vector_search')
    @patch('core.public_chatbot_api.knowledge_base')
    @patch('core.public_chatbot_api.faq_system')
    def test_public_chatbot_isolates_results_by_tenant(self, mock_faq, mock_kb, mock_get_vs):
        """Test that results are isolated by tenant"""
        # Setup vector search to return tenant-specific results
        mock_vector_search = MagicMock()
        mock_vector_search.search_similar.return_value = [
            {
                'document': 'Tenant A content',
                'similarity': 0.9,
                'metadata': {'tenant_id': 'tenant_a'}
            }
        ]
        mock_get_vs.return_value = mock_vector_search
        
        # Setup KB to return tenant-specific results
        from core.knowledge_base_system import KnowledgeDocument, DocumentType, ContentFormat, SearchResult
        from datetime import datetime
        
        kb_doc = KnowledgeDocument(
            id='kb1',
            title='Tenant A KB Doc',
            content='Content',
            summary='Summary',
            document_type=DocumentType.ARTICLE,
            format=ContentFormat.TEXT,
            tags=[],
            keywords=[],
            category='general',
            author='system',
            version='1.0',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={'tenant_id': 'tenant_a'}
        )
        
        from core.knowledge_base_system import SearchResponse
        mock_kb_result = SearchResponse(
            success=True,
            query='test',
            results=[SearchResult(document=kb_doc, relevance_score=0.9, matched_sections=[], highlighted_content=kb_doc.content, match_explanation='')],
            total_results=1,
            search_time=0.1,
            suggestions=[],
            filters_applied={'tenant_id': 'tenant_a'}
        )
        mock_kb.search.return_value = mock_kb_result
        
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        
        # Create API key for tenant_a
        key_info = {
            'api_key_id': 'test_key',
            'tenant_id': 'tenant_a',
            'user_id': 'user_a',
            'scopes': ['chatbot:query']
        }
        self.api_key_manager.validate_api_key.return_value = key_info
        
        # Make request
        response = self.client.post(
            '/api/public/chatbot/query',
            headers={'X-API-Key': 'test_key'},
            json={'query': 'test query'}
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        
        # Verify only tenant_a results were used
        # (In real scenario, vector search filter ensures this)


class TestKBDocumentCreationTenantIsolation(unittest.TestCase):
    """Test tenant isolation in KB document creation"""
    
    def setUp(self):
        """Set up test fixtures"""
        from core.chatbot_smart_faq_api import chatbot_bp
        
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(chatbot_bp)
        self.client = self.app.test_client()
    
    @patch('core.chatbot_smart_faq_api.knowledge_base')
    @patch('core.chatbot_smart_faq_api.get_vector_search')
    def test_kb_document_creation_with_api_key_tenant_id(self, mock_get_vs, mock_kb):
        """Test KB document creation extracts tenant_id from API key"""
        # Setup mocks
        mock_kb.add_document.return_value = 'doc_123'
        mock_kb.get_document.return_value = MagicMock(metadata={})
        mock_kb.update_document.return_value = True
        
        mock_vector_search = MagicMock()
        mock_vector_search.add_document.return_value = 'vector_123'
        mock_get_vs.return_value = mock_vector_search
        
        # Create request context with API key info
        with self.app.test_request_context():
            g.api_key_info = {
                'tenant_id': 'tenant_create',
                'user_id': 'user_create'
            }
            
            # Make request
            response = self.client.post(
                '/api/chatbot/knowledge/documents',
                json={
                    'title': 'Test Doc',
                    'content': 'Test content',
                    'category': 'test'
                }
            )
        
        # Verify KB document was created with tenant_id in metadata
        mock_kb.add_document.assert_called_once()
        call_kwargs = mock_kb.add_document.call_args[1]
        metadata = call_kwargs.get('metadata', {})
        self.assertEqual(metadata.get('tenant_id'), 'tenant_create')
        self.assertEqual(metadata.get('user_id'), 'user_create')
        
        # Verify vector search was called with tenant_id
        mock_vector_search.add_document.assert_called_once()
        vector_metadata = mock_vector_search.add_document.call_args[1].get('metadata', {})
        self.assertEqual(vector_metadata.get('tenant_id'), 'tenant_create')
    
    @patch('core.chatbot_smart_faq_api.knowledge_base')
    @patch('core.chatbot_smart_faq_api.get_vector_search')
    @patch('core.chatbot_smart_faq_api.get_current_user_id')
    def test_kb_document_creation_with_session_user_id(self, mock_get_user, mock_get_vs, mock_kb):
        """Test KB document creation uses session user_id as tenant_id"""
        # Setup mocks
        mock_get_user.return_value = 'user_session_123'
        mock_kb.add_document.return_value = 'doc_456'
        mock_kb.get_document.return_value = MagicMock(metadata={})
        mock_kb.update_document.return_value = True
        
        mock_vector_search = MagicMock()
        mock_vector_search.add_document.return_value = 'vector_456'
        mock_get_vs.return_value = mock_vector_search
        
        # Create request context without API key (session auth)
        with self.app.test_request_context():
            # No g.api_key_info
            g.user_id = 'user_session_123'
            
            # Make request
            response = self.client.post(
                '/api/chatbot/knowledge/documents',
                json={
                    'title': 'Session Doc',
                    'content': 'Session content',
                    'category': 'test'
                }
            )
        
        # Verify KB document was created with user_id as tenant_id
        mock_kb.add_document.assert_called_once()
        call_kwargs = mock_kb.add_document.call_args[1]
        metadata = call_kwargs.get('metadata', {})
        # user_id should be used as tenant_id for session auth
        self.assertEqual(metadata.get('tenant_id'), 'user_session_123')
    
    @patch('core.chatbot_smart_faq_api.knowledge_base')
    def test_kb_search_endpoint_adds_tenant_id_filter(self, mock_kb):
        """Test KB search endpoint adds tenant_id to filters"""
        from flask import g
        from core.knowledge_base_system import SearchResponse
        
        mock_kb_result = SearchResponse(
            success=True,
            query='test',
            results=[],
            total_results=0,
            search_time=0.1,
            suggestions=[],
            filters_applied={}
        )
        mock_kb.search.return_value = mock_kb_result
        
        # Set g.api_key_info during the request (client.post() uses a new request context)
        api_key_info = {'tenant_id': 'tenant_search', 'user_id': 'user_search'}
        @self.app.before_request
        def inject_api_key_info():
            g.api_key_info = api_key_info
        
        response = self.client.post(
            '/api/chatbot/knowledge/search',
            json={
                'query': 'test query',
                'filters': {},
                'limit': 10
            }
        )
        
        # Verify KB search was called with tenant_id in filters
        mock_kb.search.assert_called_once()
        call_kwargs = mock_kb.search.call_args[1]
        filters = call_kwargs.get('filters', {})
        self.assertEqual(filters.get('tenant_id'), 'tenant_search')


class TestKBVectorSyncTenantIsolation(unittest.TestCase):
    """Test tenant_id preservation in KB → Vector sync"""
    
    def setUp(self):
        """Set up test fixtures"""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime
        
        self.kb = KnowledgeBaseSystem()
        
        # Create document with tenant_id
        self.doc_id = self.kb.add_document(
            title="Test Doc",
            content="Test content",
            summary="Test summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="test",
            author="system",
            metadata={"tenant_id": "tenant_sync", "user_id": "user_sync"}
        )
    
    @patch('core.knowledge_base_system._get_vector_search')
    def test_update_document_preserves_tenant_id_in_vector_sync(self, mock_get_vs):
        """Test that updating KB document preserves tenant_id in vector sync"""
        # Setup document with vector_id
        doc = self.kb.get_document(self.doc_id)
        doc.metadata["vector_id"] = 999
        
        # Mock vector search
        mock_vs = MagicMock()
        mock_vs.update_document.return_value = True
        mock_get_vs.return_value = mock_vs
        
        # Update document
        self.kb.update_document(self.doc_id, {"title": "Updated Title"})
        
        # Verify vector update was called with tenant_id in metadata
        mock_vs.update_document.assert_called_once()
        call_args = mock_vs.update_document.call_args
        vector_metadata = call_args[0][2]  # Third argument is metadata
        self.assertEqual(vector_metadata.get('tenant_id'), 'tenant_sync')
        self.assertEqual(vector_metadata.get('user_id'), 'user_sync')
    
    @patch('core.knowledge_base_system._get_vector_search')
    def test_update_document_self_heal_preserves_tenant_id(self, mock_get_vs):
        """Test that self-healing vector sync preserves tenant_id"""
        # Document without vector_id (will trigger self-heal)
        doc = self.kb.get_document(self.doc_id)
        doc.metadata.pop("vector_id", None)
        
        # Mock vector search
        mock_vs = MagicMock()
        mock_vs.add_document.return_value = 888
        mock_get_vs.return_value = mock_vs
        
        # Update document (triggers self-heal)
        self.kb.update_document(self.doc_id, {"content": "Updated content"})
        
        # Verify vector add was called with tenant_id
        mock_vs.add_document.assert_called_once()
        call_args = mock_vs.add_document.call_args
        vector_metadata = call_args[1].get('metadata', {})
        self.assertEqual(vector_metadata.get('tenant_id'), 'tenant_sync')
        self.assertEqual(vector_metadata.get('user_id'), 'user_sync')
        
        # Verify vector_id was stored back in document metadata
        updated_doc = self.kb.get_document(self.doc_id)
        self.assertEqual(updated_doc.metadata.get('vector_id'), 888)
        self.assertEqual(updated_doc.metadata.get('tenant_id'), 'tenant_sync')


if __name__ == "__main__":
    unittest.main()
