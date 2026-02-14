#!/usr/bin/env python3
"""
Automation Readiness Report
Runs revenue-flow tests, static scans, and integration health checks.
Outputs a JSON summary suitable for CI or quick local checks.

Integration health uses os.getenv() and DB (oauth_tokens). To count keys from .env
when running locally, we load it here. In CI/deploy, set vars in the runtime env.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Iterable

ROOT = Path(__file__).resolve().parents[1]

def _load_dotenv() -> bool:
    """Load .env so os.getenv() sees it when script is run directly."""
    try:
        from dotenv import load_dotenv  # type: ignore
        return load_dotenv(ROOT / ".env")
    except Exception:
        return False

REVENUE_TESTS = [
    "tests/test_revenue_chatbot_flow.py",
    "tests/test_revenue_lead_intake.py",
    "tests/test_revenue_mailbox_automation.py",
    "tests/test_revenue_billing_security.py",
    "tests/test_workflow_routes.py",
    "tests/test_workflow_followups.py",
]

PROD_DIRS = [
    "core",
    "routes",
    "services",
    "integrations",
    "email_automation",
    "crm",
    "analytics",
    "auth",
]

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    "venv_local",
    "node_modules",
    "migrations",
    "tests",
    "docs",
    "scripts",
    "frontend",
}

OBSERVABILITY_TARGETS = {
    "chatbot": ["core/public_chatbot_api.py"],
    "crm_leads": ["core/webhook_intake_service.py"],
    "mailbox_automation": ["email_automation/pipeline.py"],
    "workflows": ["core/workflow_followups.py", "core/appointment_reminders.py"],
    "billing": ["core/billing_manager.py", "core/stripe_webhooks.py"],
    "security": ["core/secure_sessions.py", "core/api_key_manager.py"],
}

SERVICE_INTEGRATIONS = {
    "chatbot": ["llm_provider", "vector_db"],
    "crm_leads": [],
    "mailbox_automation": ["gmail", "outlook"],
    "workflows": ["gmail", "outlook", "sms_provider"],
    "billing": ["stripe"],
    "security": [],
}


def _iter_files(base_dirs: Iterable[str]) -> Iterable[Path]:
    for base in base_dirs:
        base_path = ROOT / base
        if not base_path.exists():
            continue
        for path in base_path.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            yield path


def _scan_direct_openai() -> List[str]:
    violations = []
    patterns = [
        re.compile(r"^\s*import\s+openai\b"),
        re.compile(r"^\s*from\s+openai\s+import\b"),
        re.compile(r"\bOpenAI\("),
        re.compile(r"\bopenai\.(?!com\b)")
    ]
    for path in _iter_files(PROD_DIRS):
        if "core/ai" in str(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if any(p.search(line) for p in patterns):
                violations.append(f"{path.relative_to(ROOT)}:{idx}: {line.strip()}")
    return violations


def _scan_prints() -> List[str]:
    violations = []
    pattern = re.compile(r"\bprint\s*\(")
    for path in _iter_files(PROD_DIRS):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{idx}: {line.strip()}")
    return violations


def _scan_frontend_hardcoded_urls() -> List[str]:
    violations = []
    frontend = ROOT / "frontend"
    if not frontend.exists():
        return violations
    pattern = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)")
    for path in frontend.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if pattern.search(content):
            violations.append(str(path.relative_to(ROOT)))
    return violations


def _run_pytest_once() -> Tuple[bool, str]:
    cmd = ["python3", "-m", "pytest", *REVENUE_TESTS]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output


def _run_pytest_stability(runs: int) -> Tuple[List[bool], List[str]]:
    results = []
    outputs = []
    for _ in range(runs):
        ok, out = _run_pytest_once()
        results.append(ok)
        outputs.append(out)
    return results, outputs


def _check_observability(targets: List[str]) -> bool:
    for rel in targets:
        path = ROOT / rel
        if not path.exists():
            return False
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return False
        if "logger." not in content and "structured_logger" not in content:
            return False
    return True


def _parse_datetime(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _oauth_status(service: str) -> Tuple[str, str]:
    try:
        from core.database_optimization import db_optimizer
    except Exception as e:
        return "missing", f"db unavailable: {e}"
    if not db_optimizer.table_exists("oauth_tokens"):
        return "missing", "oauth_tokens table missing"
    try:
        rows = db_optimizer.execute_query(
            "SELECT expires_at, is_active FROM oauth_tokens WHERE service = ? ORDER BY updated_at DESC LIMIT 1",
            (service,),
        )
    except Exception as e:
        return "missing", f"oauth query failed: {e}"
    if not rows:
        return "missing", "no tokens"
    row = rows[0]
    expires_at = None
    is_active = True
    if isinstance(row, dict):
        expires_at = row.get("expires_at")
        is_active = bool(row.get("is_active", True))
    else:
        if len(row) > 0:
            expires_at = row[0]
        if len(row) > 1:
            is_active = bool(row[1])
    expires_at = _parse_datetime(expires_at)
    if not is_active:
        return "expired", "token inactive"
    if expires_at and datetime.now() >= expires_at:
        return "expired", "token expired"
    return "connected", "token active"


def _integration_health() -> Dict[str, Dict[str, str]]:
    health = {}

    # LLM provider
    llm = "connected" if os.getenv("OPENAI_API_KEY") else "missing"
    health["llm_provider"] = llm

    # Vector DB (Pinecone optional)
    if os.getenv("PINECONE_API_KEY"):
        health["vector_db"] = "connected"
    else:
        health["vector_db"] = "missing"

    # Gmail / Outlook
    gmail_status, _ = _oauth_status("gmail")
    outlook_status, _ = _oauth_status("outlook")
    health["gmail"] = gmail_status
    health["outlook"] = outlook_status

    # SMS provider (stubbed unless configured)
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        health["sms_provider"] = "connected"
    else:
        health["sms_provider"] = "missing"

    # Stripe
    if os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET"):
        health["stripe"] = "connected"
    else:
        health["stripe"] = "missing"

    return health


def _gate_status(tests_ok: bool, guardrails_ok: bool, integration_ok: bool, observable_ok: bool) -> str:
    if not tests_ok or not guardrails_ok:
        return "NOT READY"
    if integration_ok and observable_ok:
        return "SELLABLE"
    return "BETA"


def main() -> int:
    parser = argparse.ArgumentParser(description="Automation readiness report")
    parser.add_argument("--runs", type=int, default=3, help="Number of test runs for stability")
    args = parser.parse_args()

    env_loaded = _load_dotenv()
    env_presence = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "PINECONE_API_KEY": bool(os.getenv("PINECONE_API_KEY")),
        "STRIPE_SECRET_KEY": bool(os.getenv("STRIPE_SECRET_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        "TWILIO_ACCOUNT_SID": bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "TWILIO_AUTH_TOKEN": bool(os.getenv("TWILIO_AUTH_TOKEN")),
    }

    # Test stability
    test_results, _ = _run_pytest_stability(args.runs)
    tests_passed = sum(1 for r in test_results if r)
    tests_stable = tests_passed == args.runs
    tests_flaky = 0 < tests_passed < args.runs

    # Static checks
    openai_violations = _scan_direct_openai()
    print_violations = _scan_prints()
    frontend_violations = _scan_frontend_hardcoded_urls()
    forbidden_ok = not (openai_violations or print_violations or frontend_violations)

    # Integration health
    integration_health = _integration_health()

    # Observability check
    observability = {
        service: _check_observability(paths)
        for service, paths in OBSERVABILITY_TARGETS.items()
    }

    notes = []
    if tests_stable:
        notes.append("Revenue-flow tests stable (pass 3/3)")
    elif tests_flaky:
        notes.append("Revenue-flow tests flaky (pass 1-2/3)")
    else:
        notes.append("Revenue-flow tests failing (pass 0/3)")
    if openai_violations:
        notes.append("Forbidden pattern: direct OpenAI usage outside core/ai")
    if print_violations:
        notes.append("Forbidden pattern: print() in production paths")
    if frontend_violations:
        notes.append("Forbidden pattern: hardcoded localhost URLs in frontend")

    # Guardrails: treat as OK if revenue tests stable + no forbidden patterns
    guardrails_ok = tests_stable and forbidden_ok

    # Service readiness
    services = {}
    for service, integrations in SERVICE_INTEGRATIONS.items():
        integration_ok = True
        if integrations:
            integration_ok = all(integration_health.get(name) == "connected" for name in integrations)
        observable_ok = observability.get(service, False)
        status = _gate_status(tests_stable, guardrails_ok, integration_ok, observable_ok)
        services[service] = status

    summary = {
        **services,
        "notes": notes,
        "details": {
            "env": {
                "dotenv_loaded": env_loaded,
                "present": env_presence,
            },
            "tests": {
                "runs": args.runs,
                "results": test_results,
                "stable": tests_stable,
                "flaky": tests_flaky,
            },
            "static_checks": {
                "openai_violations": openai_violations,
                "print_violations": print_violations,
                "frontend_violations": frontend_violations,
            },
            "integration_health": integration_health,
            "observability": observability,
        },
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    if "NOT READY" in services.values():
        return 2
    if "BETA" in services.values():
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
