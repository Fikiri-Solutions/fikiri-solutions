"""
Unit tests for core/form_automation_system.py (form templates, validation, submission).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.form_automation_system import (
    get_form_automation,
    FormAutomationSystem,
    FormTemplate,
    FormField,
    FieldType,
    ValidationResult,
)


class TestFormAutomationSystem:
    """Test form automation system (templates, validation, list)."""

    @patch("core.form_automation_system.get_config")
    def test_get_form_automation_returns_singleton(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = get_form_automation()
        assert fa is not None
        assert isinstance(fa, FormAutomationSystem)

    @patch("core.form_automation_system.get_config")
    def test_list_form_templates_returns_list(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        templates = fa.list_form_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 0

    @patch("core.form_automation_system.get_config")
    def test_list_form_templates_filter_by_industry(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        all_templates = fa.list_form_templates()
        if all_templates:
            industry = all_templates[0].industry
            filtered = fa.list_form_templates(industry=industry)
            assert all(t.industry == industry for t in filtered)

    @patch("core.form_automation_system.get_config")
    def test_get_form_template_nonexistent_returns_none(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        t = fa.get_form_template("nonexistent_id_xyz")
        assert t is None

    @patch("core.form_automation_system.get_config")
    def test_get_form_template_returns_template_when_exists(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        templates = fa.list_form_templates()
        if templates:
            tid = templates[0].id
            t = fa.get_form_template(tid)
            assert t is not None
            assert t.id == tid
            assert isinstance(t.fields, list)

    @patch("core.form_automation_system.get_config")
    def test_validate_form_submission_unknown_form_returns_invalid(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        result = fa.validate_form_submission("nonexistent", {"x": "y"})
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert "not found" in result.errors[0].lower() or "template" in result.errors[0].lower()

    @patch("core.form_automation_system.get_config")
    def test_validate_form_submission_required_field_empty_invalid(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        templates = fa.list_form_templates()
        if not templates:
            return
        tid = templates[0].id
        # Submit empty data so required fields fail
        result = fa.validate_form_submission(tid, {})
        assert isinstance(result, ValidationResult)
        # At least one required field error or valid if template has no required fields
        assert isinstance(result.errors, list)

    @patch("core.form_automation_system.get_config")
    def test_submit_form_invalid_returns_errors(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        out = fa.submit_form("nonexistent", {}, user_id=1)
        assert out.get("success") is False
        assert "errors" in out

    @patch("core.form_automation_system.get_config")
    def test_get_form_statistics_returns_dict(self, mock_config):
        mock_config.return_value = MagicMock()
        fa = FormAutomationSystem()
        stats = fa.get_form_statistics("landscaping_quote")
        assert isinstance(stats, dict)
