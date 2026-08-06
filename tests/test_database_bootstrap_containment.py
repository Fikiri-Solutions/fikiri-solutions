"""
Regression: schema bootstrap must not run on ordinary request / manager paths.

Covers process-once guards, PostgreSQL opt-in, migration failure ≠ success log,
and request-path DatabaseOptimizer singleton usage.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_ENV", "test")
os.environ["FIKIRI_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def _reset_bootstrap_guards(monkeypatch):
    monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", raising=False)
    from core.database_optimization import reset_schema_bootstrap_state_for_tests

    reset_schema_bootstrap_state_for_tests()
    yield
    reset_schema_bootstrap_state_for_tests()


class TestSchemaBootstrapAllowed:
    def test_postgres_dsn_disallows_bootstrap_by_default(self, monkeypatch):
        from core.database_optimization import schema_bootstrap_allowed

        monkeypatch.delenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", raising=False)
        monkeypatch.delenv("FIKIRI_FORCE_SQLITE", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )
        assert schema_bootstrap_allowed() is False

    def test_postgres_opt_in_allows_bootstrap(self, monkeypatch):
        from core.database_optimization import schema_bootstrap_allowed

        monkeypatch.setenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", "1")
        monkeypatch.delenv("FIKIRI_FORCE_SQLITE", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )
        assert schema_bootstrap_allowed() is True

    def test_sqlite_force_allows_bootstrap(self, monkeypatch):
        from core.database_optimization import schema_bootstrap_allowed

        monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
        monkeypatch.delenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )
        assert schema_bootstrap_allowed() is True


class TestInitializeDatabaseOnce:
    def test_second_call_skips_ddl(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        from core.database_optimization import DatabaseOptimizer

        db_path = str(tmp_path / "once.db")
        opt = DatabaseOptimizer(db_path=db_path)
        with patch.object(opt, "_create_optimized_tables") as create_tables, patch.object(
            opt, "_run_migrations", return_value=True
        ) as run_mig:
            again = opt._initialize_database()
            assert again is True
            create_tables.assert_not_called()
            run_mig.assert_not_called()

    def test_concurrent_calls_run_migrations_at_most_once(self, tmp_path, monkeypatch):
        """PostgreSQL process-once guard under concurrent _initialize_database."""
        monkeypatch.setenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", "1")
        monkeypatch.delenv("FIKIRI_FORCE_SQLITE", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )

        from core import database_optimization as dbo

        dbo.reset_schema_bootstrap_state_for_tests()
        instance = dbo.DatabaseOptimizer.__new__(dbo.DatabaseOptimizer)
        instance.db_type = "postgresql"
        instance._postgres_dsn = "postgresql://user:pass@localhost:5432/fikiri"
        instance.connection_pool = MagicMock()

        calls = []
        lock = threading.Lock()

        def tracking_migrations(cursor):
            with lock:
                calls.append(1)
                time.sleep(0.02)
            return True

        with patch.object(instance, "_create_optimized_tables"), patch.object(
            instance, "_create_indexes"
        ), patch.object(instance, "_create_metrics_table"), patch.object(
            instance, "_run_migrations", side_effect=tracking_migrations
        ), patch.object(instance, "get_connection") as get_conn:
            cm = MagicMock()
            conn = MagicMock()
            cm.__enter__.return_value = conn
            cm.__exit__.return_value = None
            get_conn.return_value = cm

            def worker():
                instance._initialize_database()

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)
            assert len(calls) == 1

    def test_migration_failure_does_not_log_complete(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        from core import database_optimization as dbo

        dbo.reset_schema_bootstrap_state_for_tests()
        instance = dbo.DatabaseOptimizer(db_path=str(tmp_path / "fail.db"))
        dbo.reset_schema_bootstrap_state_for_tests()

        with patch.object(instance, "_create_optimized_tables"), patch.object(
            instance, "_create_indexes"
        ), patch.object(instance, "_create_views"), patch.object(
            instance, "_create_metrics_table"
        ), patch.object(
            instance, "_run_migrations", return_value=False
        ), patch.object(instance, "get_connection") as get_conn, caplog.at_level(
            "INFO"
        ):
            cm = MagicMock()
            conn = MagicMock()
            cm.__enter__.return_value = conn
            cm.__exit__.return_value = None
            get_conn.return_value = cm

            with pytest.raises(RuntimeError, match="migration failed"):
                instance._initialize_database(force=True)

        assert "initialized with optimized schema" not in caplog.text.lower()
        assert "schema bootstrap complete" not in caplog.text.lower()


class TestEnsureSyncedEmailsConstraint:
    def test_upsert_does_not_call_ensure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        from core.database_optimization import DatabaseOptimizer, reset_schema_bootstrap_state_for_tests

        reset_schema_bootstrap_state_for_tests()
        opt = DatabaseOptimizer(db_path=str(tmp_path / "upsert.db"))
        with patch.object(opt, "ensure_synced_emails_upsert_constraint") as ensure, patch.object(
            opt, "transaction"
        ) as txn:
            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.return_value = {"id": 42}
            txn.return_value.__enter__.return_value = (conn, cursor)
            txn.return_value.__exit__.return_value = None
            row_id = opt.upsert_synced_email_from_gmail(
                user_id=1,
                gmail_id="m1",
                thread_id="t1",
                subject="s",
                sender="a@b.c",
                recipient="d@e.f",
                date_iso="2026-01-01",
                body="x",
                labels_json="[]",
                is_read=0,
            )
            assert row_id == 42
            ensure.assert_not_called()

    def test_postgres_without_opt_in_skips_ensure(self, monkeypatch):
        from core.database_optimization import DatabaseOptimizer

        opt = DatabaseOptimizer.__new__(DatabaseOptimizer)
        opt.db_type = "postgresql"
        monkeypatch.delenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", raising=False)
        monkeypatch.delenv("FIKIRI_FORCE_SQLITE", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )
        with patch.object(opt, "table_exists") as exists:
            opt.ensure_synced_emails_upsert_constraint()
            exists.assert_not_called()


class TestInitDatabaseStartup:
    def test_postgres_startup_skips_initialize(self, monkeypatch):
        monkeypatch.delenv("FIKIRI_ALLOW_SCHEMA_BOOTSTRAP", raising=False)
        monkeypatch.delenv("FIKIRI_FORCE_SQLITE", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/fikiri",
        )
        with patch("core.database_init.db_optimizer") as mock_db, patch(
            "core.database_init.schema_bootstrap_allowed", return_value=False
        ), patch("core.database_init.check_database_health", return_value=True) as health:
            mock_db.execute_query.return_value = [{"ok": 1}]
            from core import database_init

            assert database_init.init_database() is True
            mock_db._initialize_database.assert_not_called()
            health.assert_called_once()


class TestBillingUsesSingleton:
    def test_get_user_email_does_not_construct_optimizer(self, monkeypatch):
        monkeypatch.setenv("FIKIRI_FORCE_SQLITE", "1")
        with patch(
            "core.database_optimization.DatabaseOptimizer"
        ) as ctor, patch(
            "core.database_optimization.db_optimizer"
        ) as singleton:
            singleton.execute_query.return_value = [{"email": "a@b.c"}]
            from core.billing_api import get_user_email

            email = get_user_email(1)
            assert email == "a@b.c"
            ctor.assert_not_called()


class TestSlackAlertNonBlocking:
    def test_cooldown_suppresses_duplicate(self, monkeypatch):
        from core.monitoring import AlertManager

        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/test")
        monkeypatch.setenv("FIKIRI_SLACK_ALERT_COOLDOWN_SECONDS", "60")
        mgr = AlertManager()
        with patch.object(mgr, "_send_slack_alert_sync") as send:
            mgr.send_slack_alert("High response time: 1000ms", "warning", blocking=True)
            mgr.send_slack_alert("High response time: 2000ms", "warning", blocking=True)
            assert send.call_count == 1
