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
from typing import Dict, List, Optional, Tuple, Iterable

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
        # Allow print() in example/demo scripts (e.g. integrations/replit/examples/)
        if "examples" in path.parts or (path.parent.name == "examples"):
            continue
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


def _run_pytest_once(use_full_backend: bool = False) -> Tuple[bool, str]:
    if use_full_backend:
        cmd = ["python3", "-m", "pytest", "-q", "tests", "-m", "not contract and not integration", "--tb=no"]
    else:
        cmd = ["python3", "-m", "pytest", "-q", *REVENUE_TESTS, "--tb=no"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output


def _run_pytest_stability(runs: int, use_full_backend: bool = False) -> Tuple[List[bool], List[str]]:
    results = []
    outputs = []
    for _ in range(runs):
        ok, out = _run_pytest_once(use_full_backend=use_full_backend)
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
    """Check if Gmail or Outlook has valid tokens. Uses oauth_tokens first, then app tables (gmail_tokens, outlook_tokens)."""
    try:
        from core.database_optimization import db_optimizer
    except Exception as e:
        return "missing", f"db unavailable: {e}"
    now_ts = int(datetime.now().timestamp())

    # 1) Try oauth_tokens (used by oauth_token_manager)
    if db_optimizer.table_exists("oauth_tokens"):
        try:
            rows = db_optimizer.execute_query(
                "SELECT expires_at, is_active FROM oauth_tokens WHERE service = ? ORDER BY updated_at DESC LIMIT 1",
                (service,),
            )
            if rows:
                row = rows[0]
                expires_at = row.get("expires_at") if isinstance(row, dict) else (row[0] if len(row) > 0 else None)
                is_active = bool(row.get("is_active", True) if isinstance(row, dict) else (row[1] if len(row) > 1 else True))
                expires_at_parsed = _parse_datetime(expires_at)
                if is_active and (not expires_at_parsed or expires_at_parsed >= datetime.now()):
                    return "connected", "token active"
                if not is_active:
                    return "expired", "token inactive"
                if expires_at_parsed and datetime.now() >= expires_at_parsed:
                    return "expired", "token expired"
        except Exception as e:
            pass  # Fall through to app tables

    # 2) Try app-specific tables (used by core/app_oauth.py when you "Connect Gmail" / "Connect Outlook")
    if service == "gmail" and db_optimizer.table_exists("gmail_tokens"):
        try:
            rows = db_optimizer.execute_query(
                "SELECT expiry_timestamp, is_active FROM gmail_tokens WHERE is_active = TRUE ORDER BY updated_at DESC LIMIT 1",
                (),
            )
            if rows:
                row = rows[0]
                expiry_ts = row.get("expiry_timestamp") if isinstance(row, dict) else (row[0] if len(row) > 0 else None)
                is_active = bool(row.get("is_active", True) if isinstance(row, dict) else (row[1] if len(row) > 1 else True))
                if is_active and expiry_ts and int(expiry_ts) > now_ts:
                    return "connected", "token active"
        except Exception as e:
            pass
    if service == "outlook" and db_optimizer.table_exists("outlook_tokens"):
        try:
            rows = db_optimizer.execute_query(
                "SELECT expiry_timestamp, is_active FROM outlook_tokens WHERE is_active = TRUE ORDER BY updated_at DESC LIMIT 1",
                (),
            )
            if rows:
                row = rows[0]
                expiry_ts = row.get("expiry_timestamp") if isinstance(row, dict) else (row[0] if len(row) > 0 else None)
                is_active = bool(row.get("is_active", True) if isinstance(row, dict) else (row[1] if len(row) > 1 else True))
                if is_active and expiry_ts and int(expiry_ts) > now_ts:
                    return "connected", "token active"
        except Exception as e:
            pass

    return "missing", "no tokens"


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


def _provider_contract_results() -> Dict[str, Dict[str, object]]:
    """Load provider contract test results from a JSON file if present."""
    results_path = os.getenv("PROVIDER_CONTRACT_RESULTS", str(ROOT / "reports" / "provider_contract.json"))
    results = {}

    # Defaults (configured based on env presence only)
    gmail_configured = bool(
        os.getenv("GMAIL_CONTRACT_ACCESS_TOKEN")
        or (os.getenv("GMAIL_OAUTH_CLIENT_ID") and os.getenv("GMAIL_OAUTH_CLIENT_SECRET") and os.getenv("GMAIL_REFRESH_TOKEN"))
    )
    stripe_configured = bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET"))

    results["gmail"] = {"configured": gmail_configured, "contract_pass": None, "reason": "not_run"}
    results["stripe"] = {"configured": stripe_configured, "contract_pass": None, "reason": "not_run"}

    try:
        path = Path(results_path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for provider, payload in data.items():
                if provider not in results:
                    results[provider] = {}
                results[provider]["configured"] = payload.get("configured", results[provider].get("configured", False))
                results[provider]["contract_pass"] = payload.get("contract_pass", results[provider].get("contract_pass"))
                results[provider]["reason"] = payload.get("reason", results[provider].get("reason", ""))
    except Exception as e:
        results["load_error"] = {"configured": False, "contract_pass": False, "reason": f"failed_to_load: {e}"}

    return results


def _gate_status(tests_ok: bool, guardrails_ok: bool, integration_ok: bool, observable_ok: bool) -> str:
    if not tests_ok or not guardrails_ok:
        return "NOT READY"
    if integration_ok and observable_ok:
        return "SELLABLE"
    return "BETA"


def _why_provider_missing(missing: List[str], integration_health: Dict[str, str], provider_contract: Dict[str, Dict[str, object]]) -> str:
    """Short hint why each provider is missing (for why_beta)."""
    hints = []
    if "gmail" in missing or "outlook" in missing:
        hints.append("Gmail/Outlook: need OAuth tokens in DB (connect via app first)")
    if "sms_provider" in missing:
        hints.append("Twilio: set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
    if "stripe" in missing:
        pc = provider_contract.get("stripe", {})
        if not os.getenv("STRIPE_WEBHOOK_SECRET"):
            hints.append("Stripe: set STRIPE_WEBHOOK_SECRET (and STRIPE_SECRET_KEY)")
        elif not os.getenv("STRIPE_SECRET_KEY"):
            hints.append("Stripe: set STRIPE_SECRET_KEY")
        else:
            hints.append("Stripe: run contract tests or check webhook secret")
    return " ".join(hints) if hints else "Check env and run contract tests."


def _sellability_reason(service: str, status: str, integration_health: Dict[str, str], integrations: List[str], observability: bool) -> str:
    """One-line reason for BETA/NOT READY (e.g. 'BETA until Gmail/Outlook tokens + contract tests')."""
    if status == "SELLABLE":
        return ""
    reasons = []
    if not observability:
        reasons.append("observability")
    if integrations:
        missing = [n for n in integrations if integration_health.get(n) != "connected"]
        if missing:
            reasons.append(f"{'/'.join(missing)} configured")
        reasons.append("contract tests")
    if not reasons:
        return "tests or guardrails failing"
    return " until " + " + ".join(reasons)


def _print_summary(
    services: Dict[str, str],
    tests_stable: bool,
    guardrails_ok: bool,
    integration_health: Dict[str, str],
    observability: Dict[str, bool],
    provider_contract: Dict[str, Dict[str, object]],
    why_beta: Optional[Dict[str, str]] = None,
) -> None:
    """Print human-readable per-service table and sellability lines."""
    print("\n--- Readiness ---")
    print(f"  Tests (backend):    {'PASS' if tests_stable else 'FAIL'}")
    print(f"  Guardrails (scan):  {'PASS' if guardrails_ok else 'FAIL'}")
    print("\n--- Per service ---")
    for service, integrations in SERVICE_INTEGRATIONS.items():
        status = services.get(service, "?")
        integration_ok = all(integration_health.get(n) == "connected" for n in integrations) if integrations else True
        provider_ok = True
        if integrations:
            for name in integrations:
                pc = provider_contract.get(name)
                if pc and pc.get("contract_pass") is False:
                    provider_ok = False
        contract_str = "pass" if (not integrations or provider_ok) else "fail"
        if integrations and not all(integration_health.get(n) == "connected" for n in integrations):
            contract_str = "skip (provider not configured)"
        obs = "yes" if observability.get(service, False) else "no"
        print(f"  {service}")
        print(f"    tests: {'PASS' if tests_stable else 'FAIL'}  guardrails: {'PASS' if guardrails_ok else 'FAIL'}  provider: {'OK' if integration_ok else 'MISSING'}  contract: {contract_str}  observability: {obs}")
        print(f"    => {status}")
    print("\n--- Sellability ---")
    for service, integrations in SERVICE_INTEGRATIONS.items():
        status = services.get(service, "?")
        reason = _sellability_reason(service, status, integration_health, integrations, observability.get(service, False))
        line = f"  {service} = {status}{reason}"
        print(line)
    if why_beta:
        print("\n--- Why BETA? (to get SELLABLE) ---")
        for svc, msg in why_beta.items():
            print(f"  {svc}: {msg}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Automation readiness report (sellability gate)")
    parser.add_argument("--runs", type=int, default=3, help="Number of test runs for stability")
    parser.add_argument("--full-backend", action="store_true", help="Run full backend suite (pytest -m 'not contract and not integration') instead of revenue subset")
    parser.add_argument("--summary", action="store_true", help="Print human-readable per-service table and sellability lines")
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

    # Test stability (full backend or revenue subset)
    test_results, _ = _run_pytest_stability(args.runs, use_full_backend=args.full_backend)
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
    provider_contract = _provider_contract_results()

    # Observability check
    observability = {
        service: _check_observability(paths)
        for service, paths in OBSERVABILITY_TARGETS.items()
    }

    notes = []
    suite_name = "Backend tests" if args.full_backend else "Revenue-flow tests"
    if tests_stable:
        notes.append(f"{suite_name} stable (pass {args.runs}/{args.runs})")
    elif tests_flaky:
        notes.append(f"{suite_name} flaky (pass {tests_passed}/{args.runs})")
    else:
        notes.append(f"{suite_name} failing (pass 0/{args.runs})")
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
            provider_ok = True
            for name in integrations:
                provider_status = provider_contract.get(name)
                if provider_status and provider_status.get("contract_pass") is False:
                    provider_ok = False
            integration_ok = integration_ok and provider_ok
        observable_ok = observability.get(service, False)
        status = _gate_status(tests_stable, guardrails_ok, integration_ok, observable_ok)
        services[service] = status

    # Explain why each BETA service is not SELLABLE (for JSON and summary)
    why_beta = {}
    for svc, integrations in SERVICE_INTEGRATIONS.items():
        if services.get(svc) != "BETA":
            continue
        missing = [n for n in (integrations or []) if integration_health.get(n) != "connected"]
        if missing:
            why_beta[svc] = f"Providers not connected: {', '.join(missing)}. " + _why_provider_missing(missing, integration_health, provider_contract)
        else:
            why_beta[svc] = "Contract tests failing or not run."

    if args.summary:
        _print_summary(
            services, tests_stable, guardrails_ok,
            integration_health, observability, provider_contract,
            why_beta=why_beta or None,
        )

    summary = {
        **services,
        "notes": notes,
        "why_beta": why_beta if why_beta else None,
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
            "providers": provider_contract,
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
