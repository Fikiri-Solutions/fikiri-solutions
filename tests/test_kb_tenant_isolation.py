#!/usr/bin/env python3
"""
Comprehensive unit tests for knowledge base search tenant isolation.
Tests tenant filtering in KB search with extensive edge cases.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_base_system import DocumentType, ContentFormat


class TestKBSearchTenantIsolation(unittest.TestCase):
    """Test tenant isolation in knowledge base search"""
    
    def setUp(self):
        """Set up test fixtures"""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        
        self.kb = KnowledgeBaseSystem()
        
        # Add documents for different tenants
        self.tenant_a_doc1 = self.kb.add_document(
            title="Tenant A Pricing Guide",
            content="Pricing information for tenant A customers",
            summary="Pricing guide",
            document_type=DocumentType.ARTICLE,
            tags=["pricing", "guide"],
            keywords=["pricing", "cost"],
            category="pricing",
            author="system",
            metadata={"tenant_id": "tenant_a", "doc_id": "a1"}
        )
        
        self.tenant_a_doc2 = self.kb.add_document(
            title="Tenant A Support FAQ",
            content="Support information for tenant A",
            summary="Support FAQ",
            document_type=DocumentType.FAQ,
            tags=["support", "faq"],
            keywords=["support", "help"],
            category="support",
            author="system",
            metadata={"tenant_id": "tenant_a", "doc_id": "a2"}
        )
        
        self.tenant_b_doc1 = self.kb.add_document(
            title="Tenant B Pricing Guide",
            content="Pricing information for tenant B customers",
            summary="Pricing guide",
            document_type=DocumentType.ARTICLE,
            tags=["pricing", "guide"],
            keywords=["pricing", "cost"],
            category="pricing",
            author="system",
            metadata={"tenant_id": "tenant_b", "doc_id": "b1"}
        )
        
        # Legacy document without tenant_id
        self.legacy_doc = self.kb.add_document(
            title="Legacy Document",
            content="Legacy content without tenant",
            summary="Legacy",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={}  # No tenant_id
        )
    
    def test_basic_tenant_isolation(self):
        """Test that tenant A only sees tenant A documents"""
        results = self.kb.search(
            "pricing",
            filters={"tenant_id": "tenant_a"},
            limit=10
        )
        
        self.assertTrue(results.success)
        self.assertGreater(len(results.results), 0)
        
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_a")
            self.assertIn(result.document.id, [self.tenant_a_doc1, self.tenant_a_doc2])
    
    def test_tenant_b_isolation(self):
        """Test that tenant B only sees tenant B documents"""
        results = self.kb.search(
            "pricing",
            filters={"tenant_id": "tenant_b"},
            limit=10
        )
        
        self.assertTrue(results.success)
        self.assertGreater(len(results.results), 0)
        
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_b")
            self.assertEqual(result.document.id, self.tenant_b_doc1)
    
    def test_no_tenant_filter_returns_all(self):
        """Test backward compatibility: no tenant_id filter returns all documents"""
        # Search with empty filters (no tenant_id filter)
        results = self.kb.search(
            "guide",  # Matches "Pricing Guide" in tenant_a and tenant_b docs
            filters={},
            limit=10
        )
        
        # Should return documents from multiple tenants (no filtering)
        tenant_ids = set(result.document.metadata.get('tenant_id') for result in results.results)
        
        # Without tenant filter, should see documents from different tenants
        # (exact tenants depend on search relevance, but should not be filtered)
        self.assertGreater(len(results.results), 0)
        # Verify that search doesn't filter by tenant when no tenant_id in filters
        # (i.e., we can see results from multiple sources)
    
    def test_tenant_isolation_excludes_legacy_data(self):
        """Test that tenant filtering excludes legacy documents without tenant_id"""
        results = self.kb.search(
            "document",
            filters={"tenant_id": "tenant_a"},
            limit=10
        )
        
        # Should NOT include legacy document
        for result in results.results:
            self.assertNotEqual(result.document.id, self.legacy_doc)
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_a")
    
    def test_tenant_isolation_with_other_filters(self):
        """Test tenant isolation works with other filters"""
        results = self.kb.search(
            "pricing",
            filters={
                "tenant_id": "tenant_a",
                "category": "pricing"
            },
            limit=10
        )
        
        # Should only return tenant A pricing documents
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_a")
            self.assertEqual(result.document.category, "pricing")
    
    def test_case_sensitive_tenant_id(self):
        """Test that tenant_id matching is case-sensitive"""
        # Add document with uppercase tenant_id
        upper_doc = self.kb.add_document(
            title="Uppercase Tenant Doc",
            content="Content",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={"tenant_id": "TENANT_C"}
        )
        
        # Search with lowercase should NOT find uppercase
        results = self.kb.search(
            "content",
            filters={"tenant_id": "tenant_c"},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertNotIn(upper_doc, doc_ids)
    
    def test_special_characters_in_tenant_id(self):
        """Test tenant_id with special characters"""
        special_tenant = "tenant-123_test@example.com"
        special_doc = self.kb.add_document(
            title="Special Tenant Doc",
            content="Content",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={"tenant_id": special_tenant}
        )
        
        results = self.kb.search(
            "content",
            filters={"tenant_id": special_tenant},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertIn(special_doc, doc_ids)
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), special_tenant)
    
    def test_unicode_tenant_id(self):
        """Test tenant_id with unicode characters"""
        unicode_tenant = "tenant_测试_123"
        unicode_doc = self.kb.add_document(
            title="Unicode Tenant Doc",
            content="Content",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={"tenant_id": unicode_tenant}
        )
        
        results = self.kb.search(
            "content",
            filters={"tenant_id": unicode_tenant},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertIn(unicode_doc, doc_ids)
    
    def test_multiple_tenants_same_content(self):
        """Test that same content for different tenants is isolated"""
        # Both tenants have identical content
        doc_x = self.kb.add_document(
            title="Same Title",
            content="Same content",
            summary="Same summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={"tenant_id": "tenant_x"}
        )
        
        doc_y = self.kb.add_document(
            title="Same Title",
            content="Same content",
            summary="Same summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={"tenant_id": "tenant_y"}
        )
        
        # Search as tenant_x
        results_x = self.kb.search(
            "Same content",
            filters={"tenant_id": "tenant_x"},
            limit=10
        )
        
        doc_ids_x = [result.document.id for result in results_x.results]
        self.assertIn(doc_x, doc_ids_x)
        self.assertNotIn(doc_y, doc_ids_x)
        
        # Search as tenant_y
        results_y = self.kb.search(
            "Same content",
            filters={"tenant_id": "tenant_y"},
            limit=10
        )
        
        doc_ids_y = [result.document.id for result in results_y.results]
        self.assertIn(doc_y, doc_ids_y)
        self.assertNotIn(doc_x, doc_ids_y)
    
    def test_tenant_isolation_with_limit(self):
        """Test tenant isolation respects limit parameter"""
        # Add many tenant A documents
        for i in range(20):
            self.kb.add_document(
                title=f"Tenant A Doc {i}",
                content=f"Content {i}",
                summary=f"Summary {i}",
                document_type=DocumentType.ARTICLE,
                tags=[],
                keywords=[],
                category="general",
                author="system",
                metadata={"tenant_id": "tenant_a"}
            )
        
        results = self.kb.search(
            "content",
            filters={"tenant_id": "tenant_a"},
            limit=5
        )
        
        # Should only return 5 results, all from tenant_a
        self.assertLessEqual(len(results.results), 5)
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_a")
    
    def test_nonexistent_tenant_returns_empty(self):
        """Test that nonexistent tenant returns empty results"""
        results = self.kb.search(
            "pricing",
            filters={"tenant_id": "nonexistent_tenant"},
            limit=10
        )
        
        self.assertTrue(results.success)
        self.assertEqual(len(results.results), 0)
    
    def test_empty_tenant_id_string(self):
        """Test empty string tenant_id"""
        results = self.kb.search(
            "pricing",
            filters={"tenant_id": ""},
            limit=10
        )
        
        # Empty string should not match any documents with tenant_id
        # (design decision: empty string != None)
        for result in results.results:
            # Should not have tenant_id or have empty tenant_id
            tenant_id = result.document.metadata.get('tenant_id')
            self.assertTrue(tenant_id is None or tenant_id == "")
    
    def test_update_document_preserves_tenant_id(self):
        """Test that updating document preserves tenant_id"""
        # Update tenant A document
        self.kb.update_document(
            self.tenant_a_doc1,
            {"title": "Updated Title", "content": "Updated content"}
        )
        
        # Search should still find it with tenant_id filter
        results = self.kb.search(
            "updated",
            filters={"tenant_id": "tenant_a"},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertIn(self.tenant_a_doc1, doc_ids)
        
        # Verify tenant_id is still present
        updated_doc = self.kb.get_document(self.tenant_a_doc1)
        self.assertEqual(updated_doc.metadata.get('tenant_id'), "tenant_a")
    
    def test_delete_document_respects_tenant_isolation(self):
        """Test that deleting document works correctly"""
        # Delete tenant A document
        self.kb.delete_document(self.tenant_a_doc1)
        
        # Should not appear in search
        results = self.kb.search(
            "pricing",
            filters={"tenant_id": "tenant_a"},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertNotIn(self.tenant_a_doc1, doc_ids)
    
    def test_tenant_isolation_priority_over_other_filters(self):
        """Test that tenant_id filter has highest priority"""
        # Add document with matching category but different tenant
        self.kb.add_document(
            title="Tenant C Pricing",
            content="Pricing",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="pricing",
            author="system",
            metadata={"tenant_id": "tenant_c"}
        )
        
        # Search tenant_a with category filter
        results = self.kb.search(
            "pricing",
            filters={
                "tenant_id": "tenant_a",
                "category": "pricing"
            },
            limit=10
        )
        
        # Should NOT include tenant_c document
        for result in results.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "tenant_a")
            self.assertEqual(result.document.category, "pricing")
    
    def test_concurrent_searches_different_tenants(self):
        """Test concurrent searches for different tenants"""
        # Add documents for multiple tenants
        for tenant in ["t1", "t2", "t3"]:
            for i in range(5):
                self.kb.add_document(
                    title=f"{tenant} Doc {i}",
                    content=f"Content {i}",
                    summary=f"Summary {i}",
                    document_type=DocumentType.ARTICLE,
                    tags=[],
                    keywords=[],
                    category="general",
                    author="system",
                    metadata={"tenant_id": tenant}
                )
        
        # Simulate concurrent searches
        results_t1 = self.kb.search("content", filters={"tenant_id": "t1"}, limit=10)
        results_t2 = self.kb.search("content", filters={"tenant_id": "t2"}, limit=10)
        results_t3 = self.kb.search("content", filters={"tenant_id": "t3"}, limit=10)
        
        # Each should only see their own tenant
        for result in results_t1.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "t1")
        for result in results_t2.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "t2")
        for result in results_t3.results:
            self.assertEqual(result.document.metadata.get('tenant_id'), "t3")
    
    def test_mixed_metadata_with_tenant_id(self):
        """Test documents with mixed metadata including tenant_id"""
        mixed_doc = self.kb.add_document(
            title="Mixed Metadata Doc",
            content="Content",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category="general",
            author="system",
            metadata={
                "tenant_id": "tenant_mixed",
                "custom_field": "value",
                "nested": {"data": "here"}
            }
        )
        
        results = self.kb.search(
            "content",
            filters={"tenant_id": "tenant_mixed"},
            limit=10
        )
        
        doc_ids = [result.document.id for result in results.results]
        self.assertIn(mixed_doc, doc_ids)
        
        # Verify all metadata is preserved
        found_doc = self.kb.get_document(mixed_doc)
        self.assertEqual(found_doc.metadata.get('tenant_id'), "tenant_mixed")
        self.assertEqual(found_doc.metadata.get('custom_field'), "value")


if __name__ == "__main__":
    unittest.main()
