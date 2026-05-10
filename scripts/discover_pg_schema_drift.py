#!/usr/bin/env python3
"""
Static + live audit of column-type drift between our `CREATE TABLE` bootstrap
DDL (in the codebase) and what Postgres actually wants.

Run modes:

  # Static — scan the codebase only, no credentials needed:
  python3 scripts/discover_pg_schema_drift.py

  # Live — also connect to the configured Postgres and dump information_schema
  # for every table we discover statically, so we can compare declared-vs-actual:
  DATABASE_URL=postgresql://... \\
      python3 scripts/discover_pg_schema_drift.py --live

Heuristics it flags (high signal, low false-positive):

  * Columns whose NAME implies a timestamp (`*_at`, `*_time`, `*_date`,
    `last_*`, `expires_at`, ...) but whose DECLARED type is TEXT / VARCHAR /
    CHAR. Postgres comparisons against `TIMESTAMPTZ` fail without a cast.

  * Columns whose NAME implies a boolean (`is_*`, `*_enabled`, `granted`,
    `revoked`, `onboarding_completed`, ...) but whose DECLARED type is
    INTEGER. Postgres rejects `BOOLEAN = INTEGER` against a `BOOLEAN`
    column and rejects `BOOLEAN` semantics against an `INTEGER` column.

  * Columns whose NAME implies JSON (`metadata`, `tags`, `*_json`,
    `payload`, ...) but whose DECLARED type is TEXT. Works, but JSONB is the
    PG-native choice.

Output is Markdown, ready to paste into docs/POSTGRES_MIGRATION_AUDIT.md.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = ("analytics", "core", "crm", "email_automation",
             "integrations", "routes", "services")
EXTRA = (ROOT / "app.py", ROOT / "scripts" / "prestart.py")

# CREATE TABLE [IF NOT EXISTS] <name> ( ... ) — capture name + body.
# Body is everything between the opening paren and the next `)` that sits on
# its own line (this is how every CREATE TABLE in the codebase is formatted,
# because they live inside Python triple-quoted strings).
CREATE_TABLE_RE = re.compile(
    r"""CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<table>[\w."]+)\s*\(
        (?P<body>.*?)
        \n\s*\)""",
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

# One column declaration per line: name + type + optional rest. We skip
# table-level constraints (lines starting with PRIMARY KEY, FOREIGN KEY, UNIQUE,
# CHECK, CONSTRAINT — those don't declare a column).
TABLE_LEVEL_PREFIXES = (
    "PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT",
)
COL_LINE_RE = re.compile(
    r"^\s*(?P<name>[\w]+)\s+(?P<type>[A-Z][A-Z0-9_ ()]*?)(?:\s|,|$)",
    re.IGNORECASE,
)

TIMESTAMP_NAME_HINTS = (
    "_at", "_time", "_date", "timestamp", "expires", "started", "ended",
    "scheduled", "processed_until", "valid_from", "valid_until",
    "last_sync", "last_seen", "last_activity",
)
BOOLEAN_NAME_HINTS = (
    "is_", "_enabled", "_verified", "_completed", "_blocked", "_revoked",
    "_active", "_archived", "_deleted", "_sent", "_read", "_processed",
    "_default", "_paid", "_recurring", "_template", "_primary",
    "granted", "enabled", "active", "verified", "completed", "archived",
    "deleted", "sent", "read", "granted", "revoked", "success", "failed",
    "two_factor_enabled", "onboarding_completed", "added_to_kb",
    "cancel_at_period_end", "has_token",
)
JSON_NAME_HINTS = (
    "metadata", "tags", "_json", "payload", "params", "config",
    "settings_blob", "raw_event",
)


def looks_like_timestamp(name: str) -> bool:
    n = name.lower()
    return any(n.endswith(h) or h in n for h in TIMESTAMP_NAME_HINTS) and not n.endswith("_id")


def looks_like_boolean(name: str) -> bool:
    n = name.lower()
    return (
        n in BOOLEAN_NAME_HINTS
        or any(n.startswith(h) for h in BOOLEAN_NAME_HINTS if h.startswith(("is_",)))
        or any(n.endswith(h) for h in BOOLEAN_NAME_HINTS if h.startswith("_"))
    )


def looks_like_json(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in JSON_NAME_HINTS)


def normalize_type(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().upper())


def is_textual(t: str) -> bool:
    norm = normalize_type(t)
    return norm.startswith("TEXT") or norm.startswith("VARCHAR") or norm.startswith("CHAR")


def is_integer(t: str) -> bool:
    norm = normalize_type(t)
    return norm.startswith("INTEGER") or norm.startswith("INT") or norm.startswith("BIGINT") or norm.startswith("SMALLINT")


def parse_columns(body: str) -> list[tuple[str, str]]:
    """Return [(col_name, declared_type), ...] for the body of one CREATE TABLE."""
    cols: list[tuple[str, str]] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        upper = line.upper()
        if any(upper.startswith(p) for p in TABLE_LEVEL_PREFIXES):
            continue
        m = COL_LINE_RE.match(line)
        if not m:
            continue
        cols.append((m.group("name"), normalize_type(m.group("type"))))
    return cols


def collect_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if base.is_dir():
            files.extend(sorted(base.rglob("*.py")))
    files.extend(p for p in EXTRA if p.exists())
    return sorted(set(files))


def scan_static() -> dict[str, dict[str, str]]:
    """Returns {table_name: {col_name: declared_type, ...}, ...} merged across files."""
    schema: dict[str, dict[str, str]] = defaultdict(dict)
    for path in collect_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in CREATE_TABLE_RE.finditer(text):
            table = m.group("table").strip(' "\'')
            for name, typ in parse_columns(m.group("body")):
                # First declaration wins so we don't shadow with stub copies.
                if name not in schema[table]:
                    schema[table][name] = typ
    return schema


def classify(schema: dict[str, dict[str, str]]) -> list[tuple[str, str, str, str, str]]:
    """Return [(severity, table, column, declared_type, reason), ...]."""
    rows: list[tuple[str, str, str, str, str]] = []
    for table, cols in sorted(schema.items()):
        for col, typ in sorted(cols.items()):
            reason = None
            sev = "low"
            if looks_like_timestamp(col) and is_textual(typ):
                reason = "name looks like a timestamp but column is TEXT/VARCHAR"
                sev = "high"
            elif looks_like_boolean(col) and is_integer(typ):
                reason = "name looks like a boolean but column is INTEGER"
                sev = "medium"
            elif looks_like_json(col) and is_textual(typ):
                reason = "name looks like JSON but column is TEXT"
                sev = "low"
            if reason:
                rows.append((sev, table, col, typ, reason))
    return rows


def render_markdown_static(rows: list[tuple[str, str, str, str, str]]) -> str:
    if not rows:
        return "_Static scan: no suspicious column declarations found._\n"
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    out = [
        f"_Static scan — {len(rows)} suspicious column declaration(s) "
        "across the codebase's bootstrap DDL._\n",
        "| Severity | Table | Column | Declared type | Suspicion |",
        "|---|---|---|---|---|",
    ]
    for sev, table, col, typ, reason in sorted(rows, key=lambda r: (sev_rank[r[0]], r[1], r[2])):
        out.append(f"| {sev} | `{table}` | `{col}` | `{typ}` | {reason} |")
    out.append("")
    return "\n".join(out)


def live_dump(tables: list[str]) -> str:
    """Connect to DATABASE_URL and dump actual column types from information_schema."""
    try:
        import psycopg2  # type: ignore
    except ImportError:
        return "_Live scan: skipped — `psycopg2` not installed._\n"
    url = os.getenv("DATABASE_URL")
    if not url:
        return "_Live scan: skipped — DATABASE_URL not set._\n"
    if not url.startswith(("postgres://", "postgresql://")):
        return f"_Live scan: skipped — DATABASE_URL is not a Postgres URL (`{url[:30]}...`)._\n"
    try:
        conn = psycopg2.connect(url)
    except Exception as e:  # noqa: BLE001
        return f"_Live scan: connection failed — {e!r}_\n"
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ANY(%s)
                ORDER BY table_name, ordinal_position
                """,
                (tables,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        return "_Live scan: no matching tables found in the configured DB._\n"
    out = [
        f"_Live scan — {len(rows)} columns inspected across "
        f"{len({r[0] for r in rows})} tables._\n",
        "| Table | Column | Actual data_type | Nullable | Default |",
        "|---|---|---|---|---|",
    ]
    for table, col, dtype, nullable, default in rows:
        default_repr = (default or "").replace("|", "\\|")
        out.append(f"| `{table}` | `{col}` | `{dtype}` | {nullable} | `{default_repr}` |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Also query information_schema on DATABASE_URL.")
    args = parser.parse_args()

    schema = scan_static()
    rows = classify(schema)

    print("## Schema drift discovery (auto-generated)\n")
    print(f"_Tables discovered in codebase DDL: {len(schema)}_\n")
    print("### Static scan — suspicious column declarations\n")
    print(render_markdown_static(rows))

    if args.live:
        print("\n### Live scan — actual `information_schema.columns` in DATABASE_URL\n")
        print(live_dump(sorted(schema.keys())))

    return 0


if __name__ == "__main__":
    sys.exit(main())
