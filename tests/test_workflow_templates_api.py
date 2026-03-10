"""
Unit tests for core/workflow_templates_api.py (workflow templates REST API).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.workflow_templates_api import workflow_templates_bp
from core.workflow_templates_system import WorkflowCategory, WorkflowTemplate


def _make_mock_template(tid="t1", name="Test", category=WorkflowCategory.GENERAL):
    return WorkflowTemplate(
        id=tid,
        name=name,
        description="Desc",
        category=category,
        industry="General",
        complexity="simple",
        estimated_setup_time="5 min",
        features=[],
        trigger={},
        actions=[],
        variables={},
        prerequisites=[],
        success_metrics=[],
    )


class TestWorkflowTemplatesAPI:
    """Test /api/workflow-templates/* endpoints."""

    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(workflow_templates_bp)
        self.client = self.app.test_client()

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_templates_returns_list(self, mock_sys):
        t = _make_mock_template()
        mock_sys.templates = [t]
        mock_sys.get_templates_by_category.return_value = [t]
        mock_sys.search_templates.return_value = [t]

        response = self.client.get("/api/workflow-templates/templates")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "templates" in data
        assert data["total"] >= 0

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_templates_invalid_category_returns_400(self, mock_sys):
        response = self.client.get("/api/workflow-templates/templates?category=invalid")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "category" in data["error"].lower()

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_template_by_id_found(self, mock_sys):
        t = _make_mock_template("landscaping_quote_request")
        mock_sys.get_template_by_id.return_value = t

        response = self.client.get("/api/workflow-templates/templates/landscaping_quote_request")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data["template"]["id"] == "landscaping_quote_request"
        assert data["template"]["name"] == "Test"

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_template_by_id_not_found_returns_404(self, mock_sys):
        mock_sys.get_template_by_id.return_value = None

        response = self.client.get("/api/workflow-templates/templates/nonexistent")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_create_automation_from_template_missing_user_id_returns_400(self, mock_sys):
        response = self.client.post(
            "/api/workflow-templates/templates/t1/create",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "user_id" in data["error"].lower()

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_create_automation_from_template_success(self, mock_sys):
        mock_sys.create_automation_from_template.return_value = {"success": True, "automation_id": 1}

        response = self.client.post(
            "/api/workflow-templates/templates/t1/create",
            json={"user_id": 1, "customizations": {}},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        mock_sys.create_automation_from_template.assert_called_once_with("t1", 1, {})

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_categories_returns_list(self, mock_sys):
        response = self.client.get("/api/workflow-templates/categories")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "categories" in data
        assert isinstance(data["categories"], list)

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_industries_returns_list(self, mock_sys):
        mock_sys.templates = [_make_mock_template()]
        response = self.client.get("/api/workflow-templates/industries")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "industries" in data

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_get_statistics_returns_stats(self, mock_sys):
        mock_sys.get_template_statistics.return_value = {"total_templates": 5}
        response = self.client.get("/api/workflow-templates/statistics")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "statistics" in data

    def test_search_missing_query_returns_400(self):
        response = self.client.get("/api/workflow-templates/search")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "query" in data["error"].lower() or "search" in data["error"].lower()

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_search_with_query_returns_templates(self, mock_sys):
        t = _make_mock_template()
        mock_sys.search_templates.return_value = [t]

        response = self.client.get("/api/workflow-templates/search?q=landscaping")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "templates" in data
        assert data.get("query") == "landscaping"
        mock_sys.search_templates.assert_called_once_with("landscaping")

    @patch("core.workflow_templates_api.workflow_templates_system")
    def test_health_returns_healthy(self, mock_sys):
        mock_sys.get_template_statistics.return_value = {"total_templates": 3}
        response = self.client.get("/api/workflow-templates/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("status") == "healthy"
        assert "templates_loaded" in data
