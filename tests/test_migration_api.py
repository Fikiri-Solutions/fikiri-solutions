#!/usr/bin/env python3
"""Tests for GET /api/migration/capabilities."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask  # noqa: E402

from core.migration_api import migration_bp  # noqa: E402


class TestMigrationApi(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(migration_bp)
        self.client = self.app.test_client()

    @patch("core.migration_api.get_current_user_id")
    def test_capabilities_requires_auth(self, mock_uid):
        mock_uid.return_value = None
        response = self.client.get("/api/migration/capabilities")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data.get("success", True))

    @patch("core.migration_api.get_current_user_id")
    @patch("core.migration_api.get_form_automation")
    @patch("core.migration_api.get_document_templates")
    @patch("core.migration_api.get_document_processor")
    def test_capabilities_returns_structure(self, mock_proc, mock_doc_t, mock_form, mock_uid):
        mock_uid.return_value = 42

        proc = mock_proc.return_value
        proc.supported_formats = {
            "pdf": [".pdf"],
            "text": [".txt"],
        }

        tmpl = Mock()
        tmpl.id = "invoice"
        tmpl.name = "Invoice"
        tmpl.document_type = Mock(value="invoice")
        tmpl.industry = "general"
        tmpl.variables = [Mock(), Mock()]

        mock_doc_t.return_value.list_templates.return_value = [tmpl]

        ft = Mock()
        ft.id = "quote_form"
        ft.name = "Quote"
        ft.industry = "landscaping"
        ft.purpose = "leads"
        ft.fields = [Mock()]
        mock_form.return_value.list_form_templates.return_value = [ft]

        response = self.client.get("/api/migration/capabilities")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        inner = data.get("data") or {}
        self.assertEqual(inner.get("feature"), "content_migration")
        self.assertEqual(inner.get("version"), 1)
        sections = inner.get("sections", {})
        self.assertIn("knowledge_marketing", sections)
        self.assertIn("documents", sections)
        self.assertIn("forms", sections)
        self.assertIn("contacts", sections)

        doc_section = sections["documents"]
        self.assertIn(".pdf", doc_section["supported_file_extensions"])
        self.assertEqual(len(doc_section["document_templates"]), 1)
        self.assertEqual(doc_section["document_templates"][0]["id"], "invoice")

        self.assertEqual(len(sections["forms"]["form_templates"]), 1)
        self.assertEqual(sections["forms"]["form_templates"][0]["id"], "quote_form")


if __name__ == "__main__":
    unittest.main()
