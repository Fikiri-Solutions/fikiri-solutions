"""
Unit tests for core/document_templates_system.py (DocumentTemplatesSystem, enums, dataclasses).
"""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_templates_system import (
    DocumentType,
    TemplateFormat,
    TemplateVariable,
    DocumentTemplatesSystem,
    DocumentTemplate,
    GeneratedDocument,
)


class TestDocumentTemplatesEnumsAndDataclasses:
    def test_document_type_values(self):
        assert DocumentType.CONTRACT.value == "contract"
        assert DocumentType.PROPOSAL.value == "proposal"
        assert DocumentType.INVOICE.value == "invoice"

    def test_template_format_values(self):
        assert TemplateFormat.MARKDOWN.value == "markdown"
        assert TemplateFormat.HTML.value == "html"

    def test_template_variable_dataclass(self):
        v = TemplateVariable("client_name", "Client Name", "text", required=True)
        assert v.name == "client_name"
        assert v.required is True


class TestDocumentTemplatesSystem:
    @patch("core.document_templates_system.get_config")
    def test_list_templates_returns_list(self, mock_config):
        mock_config.return_value = {}
        system = DocumentTemplatesSystem()
        templates = system.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 1

    @patch("core.document_templates_system.get_config")
    def test_get_template_returns_template_or_none(self, mock_config):
        mock_config.return_value = {}
        system = DocumentTemplatesSystem()
        t = system.get_template("landscaping_agreement")
        assert t is not None
        assert t.id == "landscaping_agreement"
        assert t.name == "Landscaping Service Agreement"
        assert system.get_template("nonexistent") is None

    @patch("core.document_templates_system.get_config")
    def test_generate_document_returns_generated_doc(self, mock_config):
        mock_config.return_value = {}
        system = DocumentTemplatesSystem()
        variables = {
            "client_name": "Acme",
            "client_address": "123 Main",
            "client_phone": "555-0000",
            "client_email": "a@b.com",
            "company_name": "Fikiri",
            "company_address": "456 Oak",
            "company_phone": "555-1111",
            "company_email": "c@d.com",
            "service_description": "Lawn care",
            "service_price": 500,
            "start_date": "2024-01-01",
            "payment_terms": "Net 30",
            "warranty_period": "1 year",
        }
        doc = system.generate_document("landscaping_agreement", variables, user_id=1)
        assert isinstance(doc, GeneratedDocument)
        assert doc.template_id == "landscaping_agreement"
        assert doc.user_id == 1
        assert "Acme" in doc.content or "Fikiri" in doc.content

    @patch("core.document_templates_system.get_config")
    def test_get_template_statistics_returns_dict(self, mock_config):
        mock_config.return_value = {}
        system = DocumentTemplatesSystem()
        stats = system.get_template_statistics()
        assert "total_templates" in stats
        assert "total_generated_documents" in stats
        assert isinstance(stats["total_templates"], int)
