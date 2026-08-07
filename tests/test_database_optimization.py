"""
Unit tests for core/database_optimization.py (pure helpers: safe_json, safe_json_serialize).
"""

import sqlite3
import os
import sys
from unittest.mock import patch

import pytest

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import (
    safe_json,
    safe_json_serialize,
    QueryMetrics,
    IndexInfo,
    _production_requires_postgres_uri,
    db_optimizer,
)


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

    def test_production_requires_postgres_uri_respects_override(self, monkeypatch):
        monkeypatch.setenv("FLASK_ENV", "production")
        monkeypatch.delenv("FIKIRI_ALLOW_SQLITE_PRODUCTION", raising=False)
        assert _production_requires_postgres_uri() is True
        monkeypatch.setenv("FIKIRI_ALLOW_SQLITE_PRODUCTION", "1")
        assert _production_requires_postgres_uri() is False
        monkeypatch.setenv("FLASK_ENV", "test")
        assert _production_requires_postgres_uri() is False

    def test_list_table_columns_users_includes_email(self):
        if db_optimizer.db_type != "sqlite":
            pytest.skip("requires default test sqlite schema")
        cols = db_optimizer.list_table_columns("users")
        assert isinstance(cols, list)
        assert "email" in cols

    def test_is_retryable_sqlite_lock_error(self):
        assert db_optimizer._is_retryable_sqlite_lock_error(
            sqlite3.OperationalError("database is locked")
        )
        assert db_optimizer._is_retryable_sqlite_lock_error(
            sqlite3.OperationalError("database is busy")
        )
        assert not db_optimizer._is_retryable_sqlite_lock_error(
            sqlite3.OperationalError("no such table: foo")
        )

    def test_execute_query_retries_sqlite_lock(self, monkeypatch):
        calls = {"n": 0}

        class _Conn:
            def cursor(self):
                return self

            def execute(self, *a, **k):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise sqlite3.OperationalError("database is locked")
                return None

            @property
            def rowcount(self):
                return 1

            def fetchall(self):
                return []

            def commit(self):
                return None

            def close(self):
                return None

        class _Ctx:
            def __enter__(self):
                return _Conn()

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(db_optimizer, "db_type", "sqlite")
        monkeypatch.setattr(db_optimizer, "get_connection", lambda *a, **k: _Ctx())
        monkeypatch.setattr(db_optimizer, "_ready", False)
        result = db_optimizer.execute_query("DELETE FROM admin_audit_log", fetch=False)
        assert calls["n"] == 3
        assert result == 1


def test_clear_admin_audit_for_tests_soft_fails_on_persistent_lock(monkeypatch):
    from core import admin_audit

    monkeypatch.setattr(admin_audit, "ensure_admin_audit_table", lambda: None)

    def _always_locked(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(admin_audit.db_optimizer, "execute_query", _always_locked)
    admin_audit.clear_admin_audit_for_tests()  # must not raise
    assert admin_audit._TABLE_READY is False
