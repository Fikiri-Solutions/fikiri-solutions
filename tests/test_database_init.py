"""
Unit tests for core/database_init.py (init_database, check_database_health).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import database_init


class TestDatabaseInit:
    """Test database initialization and health check."""

    @patch("core.database_init.db_optimizer")
    def test_init_database_success(self, mock_db):
        mock_db._initialize_database = MagicMock()
        result = database_init.init_database()
        assert result is True
        mock_db._initialize_database.assert_called_once()

    @patch("core.database_init.db_optimizer")
    def test_init_database_failure_returns_false(self, mock_db):
        mock_db._initialize_database.side_effect = RuntimeError("db error")
        result = database_init.init_database()
        assert result is False

    @patch("core.database_init.db_optimizer")
    def test_check_database_health_ok_when_tables_exist(self, mock_db):
        mock_db.table_exists.side_effect = lambda t: True
        result = database_init.check_database_health()
        assert result is True
        assert mock_db.table_exists.call_count >= 1

    @patch("core.database_init.db_optimizer")
    def test_check_database_health_false_when_table_missing(self, mock_db):
        def exists(name):
            return name != "users"
        mock_db.table_exists.side_effect = exists
        result = database_init.check_database_health()
        assert result is False
