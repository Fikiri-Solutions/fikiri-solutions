#!/usr/bin/env python3
"""
Scan Python sources for SQLite-specific SQL and DB-access patterns that break
or behave incorrectly under PostgreSQL.

This is the comprehensive scanner used by the PG migration audit
(see docs/POSTGRES_MIGRATION_AUDIT.md). It supersedes the narrow
five-pattern check we had before by:

  * reporting line numbers (not just file names),
  * matching every pattern in every file (no `break` after first hit),
  * tagging each hit with severity and a short fix hint,
  * emitting JSON or Markdown so the audit doc / CI can consume it
    without human reformatting,
  * grouping by feature area (the unit of work in the audit's PR plan),
  * honoring an inline `# noqa: pg-audit` suppression for vetted lines.

Default human output exits 0 (advisory). Use --fail for CI.

Usage:
  python3 scripts/check_postgres_sql_patterns.py
  python3 scripts/check_postgres_sql_patterns.py --json
  python3 scripts/check_postgres_sql_patterns.py --format markdown
  python3 scripts/check_postgres_sql_patterns.py --feature "CRM"
  python3 scripts/check_postgres_sql_patterns.py --fail   # CI gate
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = (
    "analytics",
    "core",
    "crm",
    "email_automation",
    "integrations",
    "routes",
    "services",
)

EXTRA_FILES = (ROOT / "app.py",)
SCAN_SCRIPTS = (ROOT / "scripts" / "prestart.py",)

SKIP_PREFIXES = (
    "tests/",
    "scripts/migrations/",
    "venv/",
    ".venv/",
)

# Modules whose job is to encapsulate cross-DB compatibility — they legitimately
# contain SQLite SQL/branches. Don't flag them.
SKIP_FILES = frozenset(
    {
        "core/postgres_compat.py",
        "core/database_optimization.py",
        "scripts/check_postgres_sql_patterns.py",
    }
)

# Boolean columns we know about across the schema. Used to flag
# `WHERE <col> = 1/0` (Postgres rejects BOOLEAN = INTEGER).
BOOLEAN_COLUMNS = (
    "is_active", "is_admin", "is_default", "is_anonymous", "is_verified",
    "is_enabled", "is_revoked", "is_deleted", "is_archived", "is_paid",
    "is_complete", "is_completed", "is_blocked", "is_test", "is_recurring",
    "is_template", "is_primary",
    "enabled", "active", "verified", "completed", "archived", "processed",
    "sent", "read", "granted", "revoked", "deleted", "success", "failed",
    "published", "draft", "blocked", "muted",
    "email_verified", "email_scanning_enabled", "personal_email_exclusion",
    "auto_labeling_enabled", "lead_detection_enabled",
    "analytics_tracking_enabled", "onboarding_completed", "added_to_kb",
    "two_factor_enabled", "sms_consent", "cancel_at_period_end",
    "has_token", "has_redirect", "allow_retry",
)
_BOOL_COLS_RE = "|".join(re.escape(c) for c in BOOLEAN_COLUMNS)


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    severity: str  # "high" | "medium" | "low"
    fix_hint: str
    # If True, only the line-level scanner emits this. (Reserved for AST-only patterns.)
    line_level: bool = True


PATTERNS: tuple[Pattern, ...] = (
    Pattern(
        "INSERT OR REPLACE",
        re.compile(r"INSERT\s+OR\s+REPLACE", re.IGNORECASE),
        "high",
        "Use `INSERT ... ON CONFLICT (cols) DO UPDATE SET ...`.",
    ),
    Pattern(
        "INSERT OR IGNORE",
        re.compile(r"INSERT\s+OR\s+IGNORE", re.IGNORECASE),
        "high",
        "Use `INSERT ... ON CONFLICT (cols) DO NOTHING`.",
    ),
    Pattern(
        "AUTOINCREMENT",
        re.compile(r"\bAUTOINCREMENT\b", re.IGNORECASE),
        "high",
        "SQLite-only DDL. PG uses `BIGSERIAL` or `GENERATED ... AS IDENTITY` "
        "— schema change, requires approval.",
    ),
    Pattern(
        "last_insert_rowid()",
        re.compile(r"\blast_insert_rowid\s*\(", re.IGNORECASE),
        "high",
        "Use `INSERT ... RETURNING id` and read the returned row.",
    ),
    Pattern(
        "cursor.lastrowid",
        re.compile(r"\.lastrowid\b"),
        "high",
        "psycopg2's cursor.lastrowid is always None. Use `INSERT ... RETURNING id`.",
    ),
    Pattern(
        "datetime('now', ...)",
        re.compile(r"datetime\s*\(\s*['\"]now['\"]", re.IGNORECASE),
        "high",
        "Use `NOW()` / `CURRENT_TIMESTAMP` / `NOW() - INTERVAL '...'`.",
    ),
    Pattern(
        "date('now')",
        re.compile(r"\bdate\s*\(\s*['\"]now['\"]\s*\)", re.IGNORECASE),
        "high",
        "Use `CURRENT_DATE`.",
    ),
    Pattern(
        "strftime(",
        re.compile(r"\bstrftime\s*\(", re.IGNORECASE),
        "high",
        "Use `to_char()`, `EXTRACT()`, or `date_trunc()`.",
    ),
    Pattern(
        "julianday(",
        re.compile(r"\bjulianday\s*\(", re.IGNORECASE),
        "high",
        "Use `EXTRACT(EPOCH FROM ...)` for second-precision math.",
    ),
    Pattern(
        "IFNULL(",
        re.compile(r"\bIFNULL\s*\(", re.IGNORECASE),
        "medium",
        "Use `COALESCE(a, b)`.",
    ),
    Pattern(
        "GLOB",
        re.compile(r"\bGLOB\s+['\"]"),
        "medium",
        "Use `LIKE`/`ILIKE`/`SIMILAR TO`/`~`.",
    ),
    Pattern(
        "REGEXP",
        re.compile(r"\bREGEXP\s+['\"]"),
        "medium",
        "Use `~` / `~*` (case-insensitive) or `SIMILAR TO`.",
    ),
    Pattern(
        "COLLATE NOCASE",
        re.compile(r"COLLATE\s+NOCASE", re.IGNORECASE),
        "high",
        "PG has no NOCASE. Use `LOWER(col) = LOWER(?)`, `ILIKE`, or the CITEXT extension.",
    ),
    Pattern(
        "sqlite_master",
        re.compile(r"\bsqlite_master\b", re.IGNORECASE),
        "high",
        "Use `information_schema.tables` or `pg_catalog.pg_tables`.",
    ),
    Pattern(
        "PRAGMA",
        re.compile(r"\bPRAGMA\s+\w+", re.IGNORECASE),
        "high",
        "Drop the PRAGMA. Use session-level `SET` or connection options if needed.",
    ),
    Pattern(
        "boolean = integer literal",
        re.compile(rf"\b(?:{_BOOL_COLS_RE})\s*=\s*[01]\b", re.IGNORECASE),
        "high",
        "Postgres rejects `BOOLEAN = INTEGER`. Use `= TRUE` / `= FALSE` "
        "(portable; SQLite accepts both).",
    ),
    Pattern(
        "fromisoformat on row column",
        re.compile(
            r"datetime\.fromisoformat\s*\(\s*[\w_]+\s*[\[\.]\s*['\"]?[\w_]+['\"]?\s*[\]\)]",
        ),
        "high",
        "psycopg2 returns native datetime; guard with `isinstance(x, datetime)` or "
        "use a `_coerce_dt`-style helper.",
    ),
    Pattern(
        "raw sqlite3 import",
        re.compile(r"^\s*import\s+sqlite3\b", re.MULTILINE),
        "high",
        "Route DB access through `db_optimizer` (which adapts to PG in prod).",
    ),
    Pattern(
        "sqlite3.connect(",
        re.compile(r"\bsqlite3\.connect\s*\("),
        "high",
        "Route through `db_optimizer` so the connection respects the configured DB.",
    ),
    Pattern(
        "SELECT DISTINCT",
        re.compile(r"SELECT\s+DISTINCT\b", re.IGNORECASE),
        "low",
        "Manual review: PG rejects DISTINCT when ORDER BY references columns not in "
        "the SELECT list. Prefer `GROUP BY` for per-group ordering.",
    ),
    Pattern(
        "ROWID",
        re.compile(r"(?<![\w.])ROWID\b(?!_)", re.IGNORECASE),
        "medium",
        "PG has no implicit rowid. Use the explicit primary key column.",
    ),
    Pattern(
        "ON DUPLICATE KEY UPDATE (MySQL)",
        re.compile(r"ON\s+DUPLICATE\s+KEY\s+UPDATE", re.IGNORECASE),
        "high",
        "MySQL-only. Use `ON CONFLICT (cols) DO UPDATE SET ...`.",
    ),
    Pattern(
        "WITHOUT ROWID",
        re.compile(r"\bWITHOUT\s+ROWID\b", re.IGNORECASE),
        "high",
        "SQLite-only DDL. Remove from PG CREATE TABLE statements.",
    ),
    Pattern(
        "sqlite (::) qualifier",
        re.compile(r"(?<![\w])(?:SQLite|sqlite)::", re.IGNORECASE),
        "low",
        "Stray SQLite-qualified reference; check intent.",
    ),
)


# Feature-area mapping. First match wins, so order matters.
FEATURE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^crm/"), "CRM"),
    (re.compile(r"^email_automation/"), "Email Automation"),
    (re.compile(r"^analytics/"), "Analytics"),
    (re.compile(r"^integrations/"), "Integrations"),
    (re.compile(r"^services/automation_"), "Automations"),
    (re.compile(r"^services/business_operations\.py"), "Misc"),
    (re.compile(r"^services/"), "Misc"),
    (re.compile(r"^core/(?:secure_sessions|jwt_auth|user_auth|api_key_manager)\.py"), "Auth & Sessions"),
    (re.compile(r"^core/(?:webhook_|stripe_webhooks)\b"), "Webhooks"),
    (re.compile(r"^core/(?:billing_|fikiri_stripe_manager)\b"), "Billing"),
    (re.compile(r"^core/privacy_manager\.py"), "Privacy"),
    (re.compile(r"^core/(?:app_onboarding|onboarding_jobs)\.py"), "Onboarding"),
    (re.compile(r"^core/(?:automation_|expert_)"), "Automations"),
    (re.compile(r"^core/(?:idempotency_manager|rate_limiter|enterprise_logging)\.py"), "Infra"),
    (re.compile(r"^core/(?:oauth_token_manager|integrations/)"), "Integrations"),
    (re.compile(r"^core/kpi_tracker\.py"), "Analytics"),
    (re.compile(r"^core/"), "Misc (core)"),
    (re.compile(r"^routes/business\.py"), "Privacy"),  # privacy lives here
    (re.compile(r"^routes/monitoring\.py"), "Integrations"),  # sync status lives here
    (re.compile(r"^routes/"), "Routes (misc)"),
    (re.compile(r"^app\.py$"), "App entry"),
    (re.compile(r"^scripts/prestart\.py$"), "App entry"),
)


def feature_for(rel_path: str) -> str:
    for rx, label in FEATURE_RULES:
        if rx.search(rel_path):
            return label
    return "Misc"


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    pattern: str
    severity: str
    text: str
    fix_hint: str
    feature: str


SUPPRESS_RE = re.compile(r"#\s*noqa\s*:\s*pg-audit\b", re.IGNORECASE)


def should_skip_path(rel: str) -> bool:
    if rel.startswith(SKIP_PREFIXES):
        return True
    if rel in SKIP_FILES:
        return True
    return False


def scan_file(path: Path, rel: str) -> list[Hit]:
    hits: list[Hit] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    feat = feature_for(rel)
    lines = text.splitlines()
    for ln_idx, line in enumerate(lines, start=1):
        if SUPPRESS_RE.search(line):
            continue
        for pat in PATTERNS:
            if pat.regex.search(line):
                hits.append(
                    Hit(
                        file=rel,
                        line=ln_idx,
                        pattern=pat.name,
                        severity=pat.severity,
                        text=line.strip()[:180],
                        fix_hint=pat.fix_hint,
                        feature=feat,
                    )
                )
    return hits


def collect_candidates() -> list[Path]:
    candidates: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if base.is_dir():
            candidates.extend(sorted(base.rglob("*.py")))
    candidates.extend(p for p in EXTRA_FILES if p.exists())
    candidates.extend(p for p in SCAN_SCRIPTS if p.exists())
    return sorted(set(candidates))


def render_human(hits: list[Hit]) -> str:
    if not hits:
        return "OK: no flagged SQLite-centric patterns.\n"
    out = ["Postgres safety scan — flagged patterns:\n"]
    by_file: dict[str, list[Hit]] = defaultdict(list)
    for h in hits:
        by_file[h.file].append(h)
    for f in sorted(by_file):
        out.append(f"\n{f}")
        for h in by_file[f]:
            out.append(f"  L{h.line:>4} [{h.severity:^6}] {h.pattern}")
            out.append(f"         {h.text}")
            out.append(f"         → {h.fix_hint}")
    out.append("")
    return "\n".join(out)


def render_markdown(hits: list[Hit]) -> str:
    """Markdown for direct paste into docs/POSTGRES_MIGRATION_AUDIT.md."""
    if not hits:
        return "_Scanner found no flagged patterns._\n"
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    by_feature: dict[str, list[Hit]] = defaultdict(list)
    for h in hits:
        by_feature[h.feature].append(h)
    out: list[str] = []
    out.append(f"_Generated by `scripts/check_postgres_sql_patterns.py` — {len(hits)} hits across {len(by_feature)} feature areas._\n")
    out.append("| Feature | File | Line | Severity | Pattern | Fix hint |")
    out.append("|---|---|---:|---|---|---|")
    for feat in sorted(by_feature):
        rows = sorted(
            by_feature[feat],
            key=lambda h: (sev_rank.get(h.severity, 9), h.file, h.line),
        )
        for h in rows:
            out.append(
                f"| {feat} | `{h.file}` | {h.line} | {h.severity} | "
                f"{h.pattern} | {h.fix_hint} |"
            )
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail", action="store_true",
                        help="Exit 1 if any flagged patterns are found.")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON (one hit per record).")
    parser.add_argument("--format", choices=("human", "markdown"),
                        default="human",
                        help="Output format (ignored if --json is set).")
    parser.add_argument("--feature", default=None,
                        help="Filter to a single feature area "
                             "(e.g. \"CRM\", \"Email Automation\", \"Billing\").")
    parser.add_argument("--severity", default=None,
                        choices=("high", "medium", "low"),
                        help="Filter to a single severity.")
    args = parser.parse_args()

    hits: list[Hit] = []
    for path in collect_candidates():
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if should_skip_path(rel):
            continue
        hits.extend(scan_file(path, rel))

    if args.feature:
        hits = [h for h in hits if h.feature == args.feature]
    if args.severity:
        hits = [h for h in hits if h.severity == args.severity]

    if args.json:
        print(json.dumps([asdict(h) for h in hits], indent=2))
    elif args.format == "markdown":
        print(render_markdown(hits))
    else:
        print(render_human(hits))

    return 1 if args.fail and hits else 0


if __name__ == "__main__":
    sys.exit(main())
