"""
Helpers for running the existing SQLite-oriented schema/bootstrap on PostgreSQL
(e.g. Supabase Postgres via DATABASE_URL).

Supabase provides:
- HTTPS project URL + anon/service keys → REST / Auth clients (not used here for SQL).
- Postgres connection URI → use as DATABASE_URL for this layer (Session pooler URI recommended).
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


def is_postgresql_dsn(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith("postgresql://") or u.startswith("postgres://")


def adapt_qmark_params_to_psycopg2(sql: str) -> str:
    """
    Convert sqlite-style ? placeholders to psycopg2 %s placeholders.

    psycopg2 uses Python percent formatting internally for parameters. When a
    SQLite-oriented query also contains literal LIKE patterns such as '%ai%',
    those percent signs must be escaped or psycopg2 can treat them as format
    tokens and raise tuple-index errors.
    """
    if "?" not in sql:
        return sql
    return sql.replace("%", "%%").replace("?", "%s")


def translate_sqlite_ddl_to_postgres(sql: str) -> str:
    """Mechanical DDL tweaks for CREATE TABLE / INDEX statements generated for SQLite."""
    s = sql
    s = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "SERIAL PRIMARY KEY",
        s,
        flags=re.IGNORECASE,
    )
    s = s.replace("BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE")
    s = s.replace("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE")
    s = re.sub(r"\bDATETIME\b", "TIMESTAMP", s, flags=re.IGNORECASE)
    return s


def translate_postgres_ddl_to_sqlite(sql: str) -> str:
    """Mechanical DDL tweaks for PostgreSQL-oriented bootstrap DDL in SQLite fallback."""
    s = sql
    s = re.sub(
        r"\bBIGSERIAL\s+PRIMARY\s+KEY\b",
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bSERIAL\s+PRIMARY\s+KEY\b",
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        s,
        flags=re.IGNORECASE,
    )
    return s


def should_translate_sqlite_ddl(stripped_sql: str) -> bool:
    head = stripped_sql.split(None, 1)[0].upper() if stripped_sql else ""
    return head in ("CREATE", "DROP") or (head == "ALTER" and "TABLE" in stripped_sql.upper())


_PRAGMA_TABLE_INFO = re.compile(
    r"^\s*PRAGMA\s+table_info\s*\(\s*(?P<name>['\"]?)(?P<table>[a-zA-Z0-9_]+)\1\s*\)\s*$",
    re.IGNORECASE,
)


class PostgresBootstrapCursor:
    """
    Wraps a psycopg2 cursor so legacy SQLite PRAGMA table_info calls used during
    schema bootstrap return compatible rows (index 1 = column name).
    """

    __slots__ = ("_inner", "_fetch_override")

    def __init__(self, inner_cursor: Any) -> None:
        self._inner = inner_cursor
        self._fetch_override: Optional[List[Tuple[Any, ...]]] = None

    def execute(self, sql: Optional[str] = None, params: Optional[Sequence[Any]] = None) -> Any:
        """
        Execute a query against the wrapped psycopg2 cursor and return ``self``.

        Returning ``self`` matches sqlite3's behavior (sqlite3.Cursor.execute
        returns the cursor) so call-site idioms like
        ``cursor.execute(sql, params).fetchall()`` work uniformly across both
        backends. psycopg2's cursor.execute returns ``None`` natively, which
        is why the chained idiom silently breaks under Postgres.
        """
        self._fetch_override = None
        if not sql:
            self._inner.execute(sql, params)  # type: ignore[arg-type]
            return self

        stripped = sql.strip()
        m = _PRAGMA_TABLE_INFO.match(stripped)
        if m:
            table = m.group("table").lower()
            self._fetch_override = _information_schema_as_pragma_rows(self._inner, table)
            return self

        if should_translate_sqlite_ddl(stripped):
            tsql = translate_sqlite_ddl_to_postgres(stripped)
        else:
            tsql = stripped
        if params:
            self._inner.execute(adapt_qmark_params_to_psycopg2(tsql), params)
        else:
            self._inner.execute(tsql)
        return self

    def fetchall(self) -> Any:
        if self._fetch_override is not None:
            rows = self._fetch_override
            self._fetch_override = None
            return rows
        return self._inner.fetchall()

    def fetchone(self) -> Any:
        if self._fetch_override is not None:
            rows = self._fetch_override
            self._fetch_override = None
            return rows[0] if rows else None
        return self._inner.fetchone()

    @property
    def rowcount(self) -> int:
        return self._inner.rowcount

    def __getattr__(self, item: str) -> Any:
        return getattr(self._inner, item)


def _information_schema_as_pragma_rows(cursor: Any, table: str) -> List[Tuple[Any, ...]]:
    """
    Emulate sqlite PRAGMA table_info(tab):
    (cid, name, type, notnull, dflt_value, pk) with 0-based cid.
    """
    cursor.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default,
               CASE WHEN EXISTS (
                 SELECT 1 FROM information_schema.table_constraints tc
                 JOIN information_schema.key_column_usage kcu
                   ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'PRIMARY KEY'
                  AND kcu.column_name = c.column_name
               ) THEN 1 ELSE 0 END AS pk
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = %s
        ORDER BY c.ordinal_position
        """,
        (table, table),
    )
    raw = cursor.fetchall()
    out: List[Tuple[Any, ...]] = []
    for i, row in enumerate(raw):
        name = row[0]
        dtype = row[1]
        notnull = 1 if str(row[2]).upper() == "NO" else 0
        dflt = row[3]
        pk = int(row[4] or 0)
        out.append((i, name, dtype, notnull, dflt, pk))
    return out
