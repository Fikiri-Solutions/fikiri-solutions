#!/usr/bin/env python3
"""
Regression: legacy synced_emails schema + ensure_synced_emails_upsert_constraint.

Runs on SQLite (always) and PostgreSQL when FIKIRI_TEST_POSTGRES_URL is set
(disposable test DB only — not production Supabase).
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import DatabaseOptimizer
from tests.db_test_util import postgres_dsn_for_tests, skip_unless_postgres

INDEX_NAME = "idx_synced_emails_user_external_provider"

_UPSERT_SQL = """
    INSERT INTO synced_emails (
        user_id, gmail_id, external_id, provider, thread_id, subject, sender, recipient,
        date, body, labels, is_read
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (user_id, external_id, provider) DO UPDATE SET
        gmail_id = EXCLUDED.gmail_id,
        thread_id = EXCLUDED.thread_id,
        subject = EXCLUDED.subject,
        sender = EXCLUDED.sender,
        recipient = EXCLUDED.recipient,
        date = EXCLUDED.date,
        body = EXCLUDED.body,
        labels = EXCLUDED.labels,
        is_read = EXCLUDED.is_read
"""


def _upsert_params(
    user_id: int = 42,
    gmail_id: str = "msg_conflict_key",
    subject: str = "Subject",
    body: str = "body",
    labels: str = "[]",
    is_read: int = 1,
):
    return (
        user_id,
        gmail_id,
        gmail_id,
        "gmail",
        "thread_1",
        subject,
        "from@example.com",
        "to@example.com",
        "2026-05-20T08:00:00",
        body,
        labels,
        is_read,
    )


def _create_legacy_synced_emails_sqlite(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE synced_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gmail_id TEXT NOT NULL,
            thread_id TEXT,
            subject TEXT,
            sender TEXT,
            recipient TEXT,
            date TEXT,
            body TEXT,
            labels TEXT DEFAULT '[]',
            attachments TEXT DEFAULT '[]',
            processed BOOLEAN DEFAULT 0,
            lead_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            UNIQUE(user_id, gmail_id)
        )
        """
    )
    conn.execute("ALTER TABLE synced_emails ADD COLUMN external_id TEXT")
    conn.execute("ALTER TABLE synced_emails ADD COLUMN provider TEXT DEFAULT 'gmail'")
    conn.execute("ALTER TABLE synced_emails ADD COLUMN is_read BOOLEAN DEFAULT 0")
    conn.commit()
    conn.close()


def _create_legacy_synced_emails_postgres(dsn: str) -> None:
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS synced_emails CASCADE")
    cur.execute(
        """
        CREATE TABLE synced_emails (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            gmail_id TEXT NOT NULL,
            thread_id TEXT,
            subject TEXT,
            sender TEXT,
            recipient TEXT,
            date TIMESTAMP,
            body TEXT,
            labels TEXT DEFAULT '[]',
            attachments TEXT DEFAULT '[]',
            processed BOOLEAN DEFAULT FALSE,
            lead_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            UNIQUE (user_id, gmail_id)
        )
        """
    )
    cur.execute("ALTER TABLE synced_emails ADD COLUMN IF NOT EXISTS external_id TEXT")
    cur.execute(
        "ALTER TABLE synced_emails ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'gmail'"
    )
    cur.execute(
        "ALTER TABLE synced_emails ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE"
    )
    cur.close()
    conn.close()


def _assert_upsert_updated_row(opt: DatabaseOptimizer, user_id: int = 42) -> None:
    rows = opt.execute_query(
        """
        SELECT subject, body, labels, is_read, external_id, provider
        FROM synced_emails
        WHERE user_id = ? AND gmail_id = 'msg_conflict_key'
        """,
        (user_id,),
    )
    assert len(rows) == 1
    row = rows[0]
    if isinstance(row, dict):
        subject = row["subject"]
        body = row["body"]
        labels = row["labels"]
        is_read = row["is_read"]
        external_id = row["external_id"]
        provider = row["provider"]
    else:
        subject, body, labels, is_read, external_id, provider = row[:6]
    assert subject == "Updated via ON CONFLICT"
    assert body == "body v2"
    assert labels == '["INBOX","UNREAD"]'
    assert is_read in (0, False)
    assert external_id == "msg_conflict_key"
    assert provider == "gmail"


class TestBindBooleanColumn(unittest.TestCase):
    """Regression: Postgres rejects INTEGER for BOOLEAN columns (Gmail sync storage)."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self._tmp.name
        self._tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_postgres_binds_bool(self):
        opt = DatabaseOptimizer(db_path=self.db_path)
        opt.db_type = "postgresql"
        self.assertTrue(opt.bind_boolean_column(1))
        self.assertFalse(opt.bind_boolean_column(0))
        self.assertTrue(opt.bind_boolean_column(True))

    def test_sqlite_binds_int(self):
        opt = DatabaseOptimizer(db_path=self.db_path)
        self.assertEqual(opt.bind_boolean_column(1), 1)
        self.assertEqual(opt.bind_boolean_column(0), 0)
        self.assertEqual(opt.bind_boolean_column(False), 0)

    def test_upsert_passes_bool_is_read_on_postgres(self):
        opt = DatabaseOptimizer(db_path=self.db_path)
        opt.db_type = "postgresql"
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": 1}

        @contextmanager
        def fake_transaction():
            yield conn, cursor

        with patch.object(opt, "transaction", fake_transaction):
            with patch.object(opt, "ensure_synced_emails_upsert_constraint"):
                row_id = opt.upsert_synced_email_from_gmail(
                    1,
                    "msg_pg_bool",
                    "t1",
                    "Subj",
                    "a@b.com",
                    "c@d.com",
                    "2026-05-20T08:00:00",
                    "body",
                    "[]",
                    1,
                )
        self.assertEqual(row_id, 1)
        self.assertIs(cursor.execute.call_args.args[1][-1], True)

        cursor.reset_mock()
        cursor.fetchone.return_value = {"id": 2}
        with patch.object(opt, "transaction", fake_transaction):
            with patch.object(opt, "ensure_synced_emails_upsert_constraint"):
                row_id = opt.upsert_synced_email_from_gmail(
                    1,
                    "msg_pg_bool",
                    "t1",
                    "Subj",
                    "a@b.com",
                    "c@d.com",
                    "2026-05-20T09:00:00",
                    "body",
                    "[]",
                    0,
                )
        self.assertEqual(row_id, 2)
        self.assertIs(cursor.execute.call_args.args[1][-1], False)


class TestSyncedEmailsLegacyUpsertSqlite(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self._tmp.name
        self._tmp.close()
        _create_legacy_synced_emails_sqlite(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_legacy_shape_ensure_then_upsert_on_conflict(self):
        conn = sqlite3.connect(self.db_path)
        index_names = [row[1] for row in conn.execute("PRAGMA index_list('synced_emails')")]
        self.assertNotIn(INDEX_NAME, index_names)

        with self.assertRaises(sqlite3.OperationalError) as ctx:
            conn.execute(_UPSERT_SQL, _upsert_params())
            conn.commit()
        self.assertIn("ON CONFLICT", str(ctx.exception))
        conn.close()

        opt = DatabaseOptimizer(db_path=self.db_path)
        opt.ensure_synced_emails_upsert_constraint()

        conn = sqlite3.connect(self.db_path)
        index_names = [row[1] for row in conn.execute("PRAGMA index_list('synced_emails')")]
        conn.close()
        self.assertIn(INDEX_NAME, index_names)

        opt.upsert_synced_email_from_gmail(
            42, "msg_conflict_key", "thread_1", "Original",
            "from@example.com", "to@example.com", "2026-05-20T08:00:00",
            "body v1", '["INBOX"]', 1,
        )
        opt.upsert_synced_email_from_gmail(
            42, "msg_conflict_key", "thread_1", "Updated via ON CONFLICT",
            "from@example.com", "to@example.com", "2026-05-20T09:00:00",
            "body v2", '["INBOX","UNREAD"]', 0,
        )
        _assert_upsert_updated_row(opt)

    def test_dedupe_removes_duplicates_before_unique_index(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO synced_emails (
                user_id, gmail_id, external_id, provider, subject, is_read
            ) VALUES
                (9, 'dup_a', 'dup_a', 'gmail', 'older', 1),
                (9, 'dup_b', 'dup_a', 'gmail', 'newer', 0)
            """
        )
        conn.commit()
        conn.close()

        opt = DatabaseOptimizer(db_path=self.db_path)
        rows = opt.execute_query(
            "SELECT subject FROM synced_emails WHERE user_id = 9 AND external_id = 'dup_a'",
        )
        self.assertEqual(len(rows), 1)
        subject = rows[0]["subject"] if isinstance(rows[0], dict) else rows[0][0]
        self.assertEqual(subject, "newer")

        opt.upsert_synced_email_from_gmail(
            9, "dup_a", "t", "After dedupe",
            "s@x.com", "r@x.com", "2026-05-20T08:00:00",
            "body", "[]", 1,
        )
        rows = opt.execute_query(
            "SELECT subject FROM synced_emails WHERE user_id = 9 AND external_id = 'dup_a'",
        )
        self.assertEqual(len(rows), 1)
        subject = rows[0]["subject"] if isinstance(rows[0], dict) else rows[0][0]
        self.assertEqual(subject, "After dedupe")


try:
    import pytest

    _postgres_integration_mark = pytest.mark.integration
except ImportError:
    _postgres_integration_mark = lambda cls: cls  # type: ignore[misc]


@_postgres_integration_mark
@skip_unless_postgres()
class TestSyncedEmailsLegacyUpsertPostgres(unittest.TestCase):
    """Integration: legacy Postgres table shape (UNIQUE user_id + gmail_id only)."""

    @classmethod
    def setUpClass(cls):
        cls.dsn = postgres_dsn_for_tests()
        _create_legacy_synced_emails_postgres(cls.dsn)

    @classmethod
    def tearDownClass(cls):
        try:
            import psycopg2

            conn = psycopg2.connect(cls.dsn)
            conn.autocommit = True
            conn.cursor().execute("DROP TABLE IF EXISTS synced_emails CASCADE")
            conn.close()
        except Exception:
            pass

    def setUp(self):
        env = {
            "DATABASE_URL": self.dsn,
            "FIKIRI_FORCE_SQLITE": "0",
            "FLASK_ENV": "test",
        }
        self._env_patch = patch.dict(os.environ, env, clear=False)
        self._env_patch.start()
        _create_legacy_synced_emails_postgres(self.dsn)

    def tearDown(self):
        self._env_patch.stop()

    def test_postgres_legacy_ensure_then_upsert_on_conflict(self):
        import psycopg2
        from psycopg2 import sql as psql

        conn = psycopg2.connect(self.dsn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'synced_emails' AND indexname = %s
            """,
            (INDEX_NAME,),
        )
        self.assertIsNone(cur.fetchone())

        with self.assertRaises(Exception) as ctx:
            cur.execute(
                psql.SQL(
                    """
                    INSERT INTO synced_emails (
                        user_id, gmail_id, external_id, provider, thread_id, subject,
                        sender, recipient, date, body, labels, is_read
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, external_id, provider) DO UPDATE SET
                        subject = EXCLUDED.subject
                    """
                ),
                _upsert_params(),
            )
            conn.commit()
        self.assertIn("conflict", str(ctx.exception).lower())
        conn.close()

        from core.database_optimization import DatabaseOptimizer

        opt = DatabaseOptimizer()
        self.assertEqual(opt.db_type, "postgresql")
        opt.ensure_synced_emails_upsert_constraint()

        conn = psycopg2.connect(self.dsn)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE tablename = 'synced_emails' AND indexname = %s",
            (INDEX_NAME,),
        )
        self.assertIsNotNone(cur.fetchone())
        conn.close()

        opt.upsert_synced_email_from_gmail(
            42, "msg_conflict_key", "thread_1", "Original",
            "from@example.com", "to@example.com", "2026-05-20T08:00:00",
            "body v1", '["INBOX"]', 1,
        )
        opt.upsert_synced_email_from_gmail(
            42, "msg_conflict_key", "thread_1", "Updated via ON CONFLICT",
            "from@example.com", "to@example.com", "2026-05-20T09:00:00",
            "body v2", '["INBOX","UNREAD"]', 0,
        )
        _assert_upsert_updated_row(opt)


if __name__ == "__main__":
    unittest.main()
