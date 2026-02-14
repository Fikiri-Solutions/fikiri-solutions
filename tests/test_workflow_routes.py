#!/usr/bin/env python3
"""Workflow route tests for documents and tables."""

import unittest
import os
import sys
import json
from types import SimpleNamespace
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from routes.business import business_bp


class TestWorkflowRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(business_bp)
        self.client = self.app.test_client()

    @patch('routes.business.get_current_user_id')
    @patch('routes.business.db_optimizer')
    @patch('routes.business.generate_document')
    @patch('routes.business.automation_safety_manager')
    def test_document_generate_returns_file(self, mock_safety, mock_generate, mock_db, mock_user_id):
        mock_user_id.return_value = 1
        mock_db.table_exists.return_value = False
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        doc = SimpleNamespace(id="doc_1", content="Hello")
        mock_generate.return_value = {
            "document": doc,
            "content_bytes": b"%PDF-1.4",
            "content_type": "application/pdf",
            "filename": "test.pdf",
            "format": "pdf"
        }

        response = self.client.post('/api/workflows/documents/generate', json={
            "template_id": "landscaping_agreement",
            "variables": {"client_name": "A"},
            "format": "pdf"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/pdf")
        self.assertIn(b"%PDF", response.data)
        self.assertTrue(mock_db.execute_query.called)

    @patch('routes.business.get_current_user_id')
    @patch('routes.business.db_optimizer')
    @patch('routes.business.automation_safety_manager')
    @patch('routes.business.enhanced_crm_service')
    def test_table_export_csv(self, mock_crm, mock_safety, mock_db, mock_user_id):
        mock_user_id.return_value = 1
        mock_db.table_exists.return_value = False
        mock_safety.check_rate_limits.return_value = {"allowed": True}

        response = self.client.post('/api/workflows/tables/export', json={
            "name": "leads",
            "columns": ["email", "score"],
            "rows": [
                ["a@example.com", 10],
                ["b@example.com", 20]
            ],
            "format": "csv",
            "lead_id": 10
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("text/csv"))
        body = response.data.decode('utf-8')
        self.assertIn("email,score", body)
        self.assertIn("a@example.com,10", body)
        self.assertTrue(mock_db.execute_query.called)
        self.assertTrue(mock_crm.add_lead_activity.called)


if __name__ == '__main__':
    unittest.main()
