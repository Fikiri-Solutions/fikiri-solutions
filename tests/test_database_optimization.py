"""
Unit tests for core/database_optimization.py (pure helpers: safe_json, safe_json_serialize).
"""

import sqlite3
import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import safe_json, safe_json_serialize, QueryMetrics, IndexInfo


class TestDatabaseOptimizationHelpers:
    """Test pure helper functions and dataclasses."""

    def test_safe_json_passes_through_json_serializable(self):
        assert safe_json({"a": 1}) == {"a": 1}
        assert safe_json([1, 2]) == [1, 2]
        assert safe_json("x") == "x"
        assert safe_json(1) == 1

    def test_safe_json_converts_sqlite3_row_to_dict(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT 1 AS a, 'b' AS b").fetchone()
        result = safe_json(row)
        assert isinstance(result, dict)
        assert result["a"] == 1
        assert result["b"] == "b"
        conn.close()

    def test_safe_json_non_serializable_returns_str(self):
        class C:
            pass
        result = safe_json(C())
        assert isinstance(result, str)

    def test_safe_json_serialize_dict_recursively(self):
        assert safe_json_serialize({"a": 1, "b": [2, 3]}) == {"a": 1, "b": [2, 3]}

    def test_safe_json_serialize_list_recursively(self):
        assert safe_json_serialize([1, {"x": 2}]) == [1, {"x": 2}]

    def test_safe_json_serialize_sqlite3_row_to_dict(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT 42 AS num").fetchone()
        result = safe_json_serialize(row)
        assert isinstance(result, dict)
        assert result["num"] == 42
        conn.close()

    def test_query_metrics_dataclass(self):
        from datetime import datetime, timezone
        m = QueryMetrics(
            query="SELECT 1",
            execution_time=0.01,
            rows_affected=1,
            timestamp=datetime.now(timezone.utc),
            success=True,
            error=None,
        )
        assert m.query == "SELECT 1"
        assert m.success is True
        assert m.rows_affected == 1

    def test_index_info_dataclass(self):
        i = IndexInfo(
            table_name="users",
            index_name="idx_email",
            columns=["email"],
            unique=True,
            size_bytes=1024,
        )
        assert i.table_name == "users"
        assert i.unique is True
