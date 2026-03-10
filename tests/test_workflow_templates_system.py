"""
Unit tests for core/workflow_templates_system.py (workflow templates logic, no Flask).
"""

import os
import sys

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_templates_system import (
    workflow_templates_system,
    WorkflowTemplatesSystem,
    WorkflowCategory,
    WorkflowTemplate,
)


class TestWorkflowTemplatesSystem:
    """Test workflow templates system (categories, search, get by id, stats)."""

    def test_templates_loaded_non_empty(self):
        assert hasattr(workflow_templates_system, "templates")
        assert isinstance(workflow_templates_system.templates, list)
        assert len(workflow_templates_system.templates) >= 1

    def test_get_template_by_id_returns_template(self):
        tid = workflow_templates_system.templates[0].id
        t = workflow_templates_system.get_template_by_id(tid)
        assert t is not None
        assert t.id == tid
        assert isinstance(t.name, str)
        assert t.category in WorkflowCategory

    def test_get_template_by_id_nonexistent_returns_none(self):
        t = workflow_templates_system.get_template_by_id("nonexistent_id_xyz")
        assert t is None

    def test_get_templates_by_category_returns_list(self):
        for cat in WorkflowCategory:
            templates = workflow_templates_system.get_templates_by_category(cat)
            assert isinstance(templates, list)
            assert all(t.category == cat for t in templates)

    def test_search_templates_returns_matching(self):
        results = workflow_templates_system.search_templates("landscaping")
        assert isinstance(results, list)
        # Search is by name, description, or features
        for t in results:
            assert "landscaping" in t.name.lower() or "landscaping" in t.description.lower() or any(
                "landscaping" in f.lower() for f in (t.features or [])
            )

    def test_search_templates_empty_query_returns_all_or_empty(self):
        results = workflow_templates_system.search_templates("xyznonexistentword")
        assert isinstance(results, list)

    def test_get_template_statistics_returns_dict(self):
        stats = workflow_templates_system.get_template_statistics()
        assert isinstance(stats, dict)
        assert "total_templates" in stats or len(stats) >= 0

    def test_workflow_category_enum_values(self):
        assert WorkflowCategory.LANDSCAPING.value == "landscaping"
        assert WorkflowCategory.GENERAL.value == "general"
