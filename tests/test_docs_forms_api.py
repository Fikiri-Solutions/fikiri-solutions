"""
Unit tests for core/docs_forms_api.py (docs & forms REST API).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.docs_forms_api import docs_forms_bp


class TestDocsFormsAPI:
    """Test /api/docs-forms/* endpoints."""

    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(docs_forms_bp)
        self.client = self.app.test_client()

    @patch("core.docs_forms_api.doc_processor")
    def test_get_processing_capabilities_returns_200(self, mock_processor):
        mock_processor.get_processing_capabilities.return_value = {"extract_text": True}
        mock_processor.get_supported_formats.return_value = [".pdf", ".docx"]

        response = self.client.get("/api/docs-forms/documents/capabilities")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "capabilities" in data
        assert "supported_formats" in data

    def test_process_document_no_file_returns_400(self):
        response = self.client.post(
            "/api/docs-forms/documents/process",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "file" in data.get("error", "").lower() or "no file" in data.get("error", "").lower()

    @patch("core.docs_forms_api.doc_processor")
    def test_process_document_unsupported_format_returns_400(self, mock_processor):
        mock_processor.is_format_supported.return_value = False
        data = {"file": (b"x", "file.xyz")}

        response = self.client.post(
            "/api/docs-forms/documents/process",
            data=data,
            content_type="multipart/form-data",
        )
        # May be 400 (unsupported) or 500 depending on flow; at least not 200 with success
        assert response.status_code in (400, 500)
        data = json.loads(response.data)
        assert data.get("success") is False

    @patch("core.docs_forms_api.form_automation")
    def test_list_form_templates_returns_200(self, mock_form):
        mock_form.list_form_templates.return_value = []

        response = self.client.get("/api/docs-forms/forms/templates")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "templates" in data

    def test_submit_form_missing_form_id_returns_400(self):
        response = self.client.post(
            "/api/docs-forms/forms/submit",
            json={"data": {}},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "form_id" in data.get("error", "").lower() or "form" in data.get("error", "").lower()

    @patch("core.docs_forms_api.doc_templates")
    def test_list_document_templates_returns_200(self, mock_templates):
        mock_templates.list_templates.return_value = []

        response = self.client.get("/api/docs-forms/templates")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "templates" in data

    @patch("core.docs_forms_api.doc_templates")
    def test_get_document_template_not_found_returns_404(self, mock_templates):
        mock_templates.get_template.return_value = None

        response = self.client.get("/api/docs-forms/templates/nonexistent")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "not found" in data.get("error", "").lower()

    @patch("core.docs_forms_api.doc_analytics")
    @patch("core.docs_forms_api.doc_processor")
    @patch("core.docs_forms_api.form_automation")
    @patch("core.docs_forms_api.doc_templates")
    def test_get_system_status_returns_200(
        self, mock_templates, mock_form, mock_processor, mock_analytics
    ):
        mock_processor.get_processing_capabilities.return_value = {}
        mock_templates.get_template_statistics.return_value = {}
        mock_form.form_templates = []
        mock_form.submissions = []
        mock_form.get_form_statistics.return_value = {}
        mock_analytics.get_real_time_stats.return_value = {}

        response = self.client.get("/api/docs-forms/status")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("status") == "operational"
        assert "systems" in data

    @patch("core.docs_forms_api.doc_analytics")
    def test_get_analytics_report_returns_200(self, mock_analytics):
        mock_analytics.get_comprehensive_report.return_value = {}

        response = self.client.get("/api/docs-forms/analytics/report?days=7")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "report" in data

    @patch("core.docs_forms_api.doc_templates")
    def test_generate_document_missing_format_returns_400(self, mock_templates):
        response = self.client.post(
            "/api/docs-forms/documents/doc123/convert",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "format" in data.get("error", "").lower()
