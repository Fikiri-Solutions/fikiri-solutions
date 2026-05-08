#!/usr/bin/env python3
"""
Scan Python sources for SQLite-specific SQL fragments that commonly break PostgreSQL.

Skips migration scripts, compat layers, generated noise, and the central DB shim.
Default: print matches and exit 0. Use --fail for CI once the tree is clean.

Usage:
  python3 scripts/check_postgres_sql_patterns.py
  python3 scripts/check_postgres_sql_patterns.py --fail
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Top-level dirs to scan fully (excluding __pycache__ / venv handled by walker)
SCAN_DIRS = (
    "analytics",
    "core",
    "crm",
    "email_automation",
    "integrations",
    "routes",
    "services",
)

# Explicit root module(s)
EXTRA_FILES = (ROOT / "app.py",)

# Scripts under repo root that are invoked in prod (not one-off migrations)
SCAN_SCRIPTS = (ROOT / "scripts" / "prestart.py",)

SKIP_PREFIXES = (
    "tests/",
    "scripts/migrations/",
    "venv/",
    ".venv/",
)

SKIP_FILES = frozenset(
    {
        "core/postgres_compat.py",
        "core/database_optimization.py",
        "scripts/check_postgres_sql_patterns.py",
    }
)

PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"INSERT\s+OR\s+REPLACE", re.I), "INSERT OR REPLACE"),
    (re.compile(r"datetime\s*\(\s*'now'"), "datetime('now'...)"),
    (re.compile(r"\bsqlite_master\b", re.I), "sqlite_master"),
    (
        re.compile(r"\b(?:is_active|onboarding_completed|added_to_kb)\s*=\s*[01]\b", re.I),
        "numeric literal assigned/compared to boolean column",
    ),
    (re.compile(r"(?<![\w])(?:SQLite|sqlite)::", re.I), "sqlite (::) qualifier"),
)


def should_skip(rel: str) -> bool:
    if rel.startswith(SKIP_PREFIXES):
        return True
    if rel in SKIP_FILES:
        return True
    return False


def scan_file(path: Path) -> list[str]:
    hits: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"read_error: {e}"]
    for rx, label in PATTERNS:
        if rx.search(text):
            hits.append(label)
            break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit 1 when any flagged pattern is found outside skip lists.",
    )
    args = parser.parse_args()

    candidates: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if base.is_dir():
            candidates.extend(sorted(base.rglob("*.py")))
    candidates.extend(EXTRA_FILES)
    candidates.extend([p for p in SCAN_SCRIPTS if p.exists()])

    bad: list[tuple[str, str]] = []
    for path in sorted(set(candidates)):
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if should_skip(rel):
            continue
        for label in scan_file(path):
            if label.startswith("read_error"):
                bad.append((rel, label))
            elif label:
                bad.append((rel, label))

    if not bad:
        print(f"OK: no flagged SQLite-centric SQL patterns in scanned paths ({len(candidates)} files checked).")
        return 0

    print(
        "Postgres safety scan — possible SQLite-specific SQL "
        "(use db_optimizer helpers, ON CONFLICT, information_schema, etc.):\n"
    )
    for rel, label in sorted(bad, key=lambda x: (x[0], x[1])):
        print(f"  {rel}: {label}")
    return 1 if args.fail else 0


if __name__ == "__main__":
    sys.exit(main())
