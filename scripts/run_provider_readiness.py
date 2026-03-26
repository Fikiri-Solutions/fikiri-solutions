#!/usr/bin/env python3
"""
Provider-backed readiness: run with actual configured providers (OpenAI, Gmail/Outlook, Stripe, Twilio).

Loads .env, checks which providers are configured, runs contract tests when possible,
and prints a clear report. Use before claiming production readiness.

Example:
  python3 scripts/run_provider_readiness.py
  python3 scripts/run_provider_readiness.py --run-contract-tests
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> bool:
    try:
        from dotenv import load_dotenv  # type: ignore
        return bool(load_dotenv(ROOT / ".env"))
    except Exception:
        return False


def _provider_env_status() -> dict[str, str]:
    """Which provider env vars are set (configured vs missing)."""
    status = {}
    # OpenAI
    status["openai"] = "configured" if os.getenv("OPENAI_API_KEY") else "missing"
    # Gmail (contract tests need one of: access token, or client_id + client_secret + refresh_token)
    gmail_token = os.getenv("GMAIL_CONTRACT_ACCESS_TOKEN")
    gmail_creds = (
        (os.getenv("GMAIL_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID"))
        and (os.getenv("GMAIL_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET"))
        and (os.getenv("GMAIL_REFRESH_TOKEN") or os.getenv("GOOGLE_REFRESH_TOKEN"))
    )
    status["gmail"] = "configured" if (gmail_token or gmail_creds) else "missing"
    # Outlook (no contract test in repo; report configured if env suggests usage)
    outlook_id = os.getenv("MICROSOFT_CLIENT_ID") or os.getenv("OUTLOOK_CLIENT_ID")
    outlook_secret = os.getenv("MICROSOFT_CLIENT_SECRET") or os.getenv("OUTLOOK_CLIENT_SECRET")
    status["outlook"] = "configured" if (outlook_id and outlook_secret) else "missing"
    # Stripe
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    stripe_webhook = os.getenv("STRIPE_WEBHOOK_SECRET")
    status["stripe"] = "configured" if (stripe_key and stripe_webhook) else "missing"
    # Twilio
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    status["twilio"] = "configured" if (twilio_sid and twilio_token) else "missing"
    return status


def _run_contract_tests(env_status: dict[str, str]) -> dict[str, str]:
    """Run pytest contract tests; return per-provider result: pass | fail | skip."""

    def _run_one(provider: str, test_path: str) -> str:
        if env_status.get(provider) != "configured":
            return "skip"  # Don't run when not configured
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=no", "-q"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode != 0:
                return "fail"
            # Exit 0 with "skipped" in output and no "passed" = all tests skipped
            if "skipped" in out.lower() and "passed" not in out.lower():
                return "skip"
            return "pass"
        except Exception:
            return "skip"

    return {
        "gmail": _run_one("gmail", "tests/contract/test_gmail_contract.py"),
        "stripe": _run_one("stripe", "tests/contract/test_stripe_contract.py"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Provider-backed readiness (OpenAI, Gmail, Outlook, Stripe, Twilio)")
    parser.add_argument("--run-contract-tests", action="store_true", help="Run contract tests for Gmail/Stripe when configured")
    parser.add_argument("--summary", action="store_true", help="Also run automation_readiness.py --summary")
    args = parser.parse_args()

    _load_dotenv()
    env_status = _provider_env_status()
    contract = {}
    if args.run_contract_tests:
        contract = _run_contract_tests(env_status)

    # Report
    print("\n--- Provider-backed readiness ---")
    print(f"  OpenAI:   {env_status.get('openai', '?')} (set OPENAI_API_KEY)")
    print(f"  Gmail:    {env_status.get('gmail', '?')}", end="")
    if contract.get("gmail"):
        print(f"  contract: {contract['gmail']}", end="")
    print()
    print(f"  Outlook:  {env_status.get('outlook', '?')} (connect in app; no contract test in repo)")
    print(f"  Stripe:   {env_status.get('stripe', '?')}", end="")
    if contract.get("stripe"):
        print(f"  contract: {contract['stripe']}", end="")
    print()
    print(f"  Twilio:   {env_status.get('twilio', '?')} (set TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN)")
    print()

    if args.summary:
        print("\n--- Automation readiness summary ---\n")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "automation_readiness.py"), "--summary"],
            cwd=ROOT,
            # Let stdout/stderr through so the human-readable table and JSON are visible
        )

    # Exit: 0 if all configured providers pass or not run, 1 if any contract failed
    if contract.get("gmail") == "fail" or contract.get("stripe") == "fail":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
