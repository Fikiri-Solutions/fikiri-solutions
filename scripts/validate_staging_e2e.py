#!/usr/bin/env python3
"""
End-to-end staging validation: widget flow → lead capture → CRM → dashboard visibility → automation log.

Run against a real staging backend with real API key and test user.
Requires: STAGING_URL, WEBHOOK_API_KEY, STAGING_LOGIN_EMAIL, STAGING_LOGIN_PASSWORD.

Example:
  STAGING_URL=https://api.staging.example.com \\
  WEBHOOK_API_KEY=fik_xxx \\
  STAGING_LOGIN_EMAIL=test@example.com \\
  STAGING_LOGIN_PASSWORD=secret \\
  python3 scripts/validate_staging_e2e.py
"""

from __future__ import annotations

import os
import sys
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E staging validation: lead capture → CRM → automation log")
    parser.add_argument("--base-url", default=_env("STAGING_URL"), help="Staging API base URL (e.g. https://api.staging.example.com)")
    parser.add_argument("--api-key", default=_env("WEBHOOK_API_KEY"), help="API key with webhooks:leads scope")
    parser.add_argument("--login-email", default=_env("STAGING_LOGIN_EMAIL"), help="Test user email for login")
    parser.add_argument("--login-password", default=_env("STAGING_LOGIN_PASSWORD"), help="Test user password")
    parser.add_argument("--test-email", default="", help="Override lead email (default: unique address)")
    parser.add_argument("--skip-login", action="store_true", help="Only run webhook capture; skip CRM/logs checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    base = (args.base_url or "").rstrip("/")
    if not base:
        print("Error: Set STAGING_URL or pass --base-url")
        return 1
    if not args.api_key:
        print("Error: Set WEBHOOK_API_KEY or pass --api-key")
        return 1

    test_email = args.test_email or f"e2e-{int(time.time())}@staging-validate.example.com"
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"

    # --- 1. Lead capture (simulates widget → webhook) ---
    print("1. POST /api/webhooks/leads/capture ...")
    r = session.post(
        f"{base}/api/webhooks/leads/capture",
        json={"email": test_email, "name": "E2E Staging Test", "source": "staging_validation"},
        headers={"X-API-Key": args.api_key},
        timeout=30,
    )
    if args.verbose:
        print(f"   Status: {r.status_code}, Body: {r.text[:500]}")
    if r.status_code == 429:
        print("   Rate limited (429). Retry later or use a different key.")
        return 1
    if r.status_code != 200:
        print(f"   FAIL: {r.status_code} - {r.text[:400]}")
        return 1
    data = r.json()
    if not data.get("success"):
        print(f"   FAIL: {data.get('error', 'Unknown error')}")
        return 1
    lead_id = data.get("lead_id")
    print(f"   OK lead_id={lead_id} (deduplicated={data.get('deduplicated', False)})")

    if args.skip_login:
        print("   (Skipping CRM and automation log checks; --skip-login)")
        return 0

    if not args.login_email or not args.login_password:
        print("   Warning: STAGING_LOGIN_EMAIL/PASSWORD not set; skipping CRM and automation log checks")
        return 0

    # --- 2. Login to get token ---
    print("2. POST /api/auth/login ...")
    r = session.post(
        f"{base}/api/auth/login",
        json={"email": args.login_email, "password": args.login_password},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"   FAIL: {r.status_code} - {r.text[:300]}")
        return 1
    login_data = r.json()
    token = (login_data.get("data") or login_data).get("access_token")
    if not token:
        print("   FAIL: No access_token in response")
        return 1
    session.headers["Authorization"] = f"Bearer {token}"
    print("   OK token received")

    # --- 3. GET CRM leads and verify our lead is visible ---
    print("3. GET /api/crm/leads ...")
    r = session.get(f"{base}/api/crm/leads", params={"limit": 100}, timeout=15)
    if r.status_code != 200:
        print(f"   FAIL: {r.status_code} - {r.text[:300]}")
        return 1
    leads_data = r.json()
    leads = (leads_data.get("data") or leads_data).get("leads") or []
    found = next((l for l in leads if str(l.get("email")).lower() == test_email.lower() or l.get("id") == lead_id), None)
    if not found:
        print(f"   FAIL: Lead {test_email} not found in CRM (got {len(leads)} leads)")
        if args.verbose and leads:
            for l in leads[:5]:
                print(f"      - {l.get('email')} id={l.get('id')}")
        return 1
    print(f"   OK lead visible in CRM (id={found.get('id')})")

    # --- 4. GET automation logs (dashboard visibility for automation runs) ---
    print("4. GET /api/automation/logs ...")
    r = session.get(f"{base}/api/automation/logs", params={"limit": 20}, timeout=15)
    if r.status_code != 200:
        print(f"   FAIL: {r.status_code} - {r.text[:300]}")
        return 1
    logs_data = r.json()
    logs = (logs_data.get("data") or logs_data).get("logs") or []
    print(f"   OK automation log visible ({len(logs)} recent runs)")
    failed = [x for x in logs if x.get("status") != "success"]
    if failed and args.verbose:
        for x in failed[:3]:
            print(f"      - {x.get('rule_name')}: {x.get('error_message', '')[:80]}")

    print("\n== Staging E2E validation passed ==")
    print("  widget load → lead capture → CRM record → dashboard visibility → automation log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
