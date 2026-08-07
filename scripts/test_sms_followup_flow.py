#!/usr/bin/env python3
"""
End-to-end SMS follow-up test against the running local API.

Fixes the common local pitfalls:
  - Wrong DB (sqlite3 data/fikiri.db vs DATABASE_URL / Supabase Postgres)
  - Missing trialing subscription on the logged-in user
  - Global automation kill-switch blocking sends

Usage:
  python3 scripts/test_sms_followup_flow.py
  SMS_TEST_EMAIL=you@example.com SMS_TEST_PASSWORD='...' python3 scripts/test_sms_followup_flow.py
  SMS_TEST_PHONE=+15551234567 python3 scripts/test_sms_followup_flow.py

Requires: backend on http://localhost:5000, Twilio env vars, python-dotenv, requests.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
API = os.environ.get("FIKIRI_API_BASE", "http://localhost:5000").rstrip("/")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def _fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _ensure_postgres_prereqs(user_id: int) -> None:
    from core.database_optimization import db_optimizer
    from core.automation_safety import automation_safety_manager

    sub = db_optimizer.execute_query(
        "SELECT status FROM subscriptions WHERE user_id = ? ORDER BY current_period_end DESC NULLS LAST LIMIT 1",
        (user_id,),
    )
    if not sub or (sub[0].get("status") or "").lower() not in {"active", "trialing"}:
        stripe_sub = f"sub_sms_flow_test_{user_id}"
        db_optimizer.execute_query(
            """
            INSERT INTO subscriptions (
                user_id, stripe_customer_id, stripe_subscription_id,
                status, tier, billing_period, current_period_end
            ) VALUES (?, ?, ?, 'trialing', 'growth', 'monthly',
                EXTRACT(EPOCH FROM NOW())::bigint + 2592000)
            ON CONFLICT (stripe_subscription_id) DO UPDATE SET status = 'trialing'
            """,
            (user_id, f"cus_sms_flow_{user_id}", stripe_sub),
            fetch=False,
        )
        print(f"[fix] Added trialing subscription for user_id={user_id} (Postgres)")

    if automation_safety_manager.is_global_kill_switch_enabled():
        automation_safety_manager.toggle_global_kill_switch(False)
        print("[fix] Disabled global automation kill-switch")


def _login(email: str, password: str) -> tuple[str, int]:
    import requests

    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        _fail(f"Login failed ({r.status_code}): {r.text[:300]}")
    data = r.json().get("data") or {}
    token = data.get("access_token")
    user_id = (data.get("user") or {}).get("id")
    if not token or not user_id:
        _fail("Login response missing access_token or user.id")
    return token, int(user_id)


def _api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    import requests

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{API}{path}"
    r = requests.request(method, url, headers=headers, json=body, timeout=60)
    try:
        payload = r.json()
    except Exception:
        _fail(f"{method} {path} returned non-JSON ({r.status_code}): {r.text[:300]}")
    if r.status_code >= 400 or not payload.get("success", True):
        code = payload.get("code") or r.status_code
        err = payload.get("error") or payload.get("message") or r.text[:200]
        _fail(f"{method} {path} failed [{code}]: {err}")
    return payload


def main() -> None:
    _load_env()

    email = os.environ.get("SMS_TEST_EMAIL", "sms-test-1782905970@example.test")
    password = os.environ.get("SMS_TEST_PASSWORD", "").strip()
    if not password:
        _fail("Set SMS_TEST_PASSWORD in the environment (do not hardcode credentials)")
    phone = os.environ.get("SMS_TEST_PHONE", os.environ.get("TWILIO_TEST_TO", "+13525755715")).strip()
    if not phone.startswith("+"):
        digits = "".join(c for c in phone if c.isdigit())
        phone = f"+1{digits[-10:]}" if len(digits) >= 10 else f"+{digits}"

    try:
        import requests  # noqa: F401
    except ImportError:
        _fail("pip install requests")

    health = requests.get(f"{API}/api/health", timeout=10)
    if health.status_code != 200:
        _fail(f"Backend not reachable at {API} (start: python3 app.py)")

    print("Fikiri SMS follow-up flow test")
    print("=" * 40)
    print(f"API:   {API}")
    print(f"User:  {email}")
    print(f"Phone: {phone}")

    token, user_id = _login(email, password)
    print(f"[ok]  Logged in user_id={user_id}")

    _ensure_postgres_prereqs(user_id)

    lead_email = f"sms-flow-{int(time.time())}@example.test"
    created = _api(
        "POST",
        "/api/crm/leads",
        token,
        {"name": "SMS Flow Test", "email": lead_email, "phone": phone},
    )
    lead_id = (created.get("data") or {}).get("lead", {}).get("id")
    if not lead_id:
        _fail("Create lead response missing lead.id")
    print(f"[ok]  Lead created id={lead_id}")

    _api("PUT", f"/api/crm/leads/{lead_id}", token, {"sms_consent": True})
    print("[ok]  SMS consent set on lead")

    sched = _api(
        "POST",
        "/api/workflows/followups/schedule",
        token,
        {
            "lead_id": lead_id,
            "follow_up_date": "2026-01-01T00:00:00",
            "follow_up_type": "sms",
            "message": "Fikiri SMS follow-up test. Reply STOP to opt out.",
        },
    )
    follow_up_id = (sched.get("data") or {}).get("follow_up_id")
    print(f"[ok]  Follow-up scheduled id={follow_up_id}")

    executed = _api("POST", "/api/workflows/followups/execute", token)
    stats = executed.get("data") or {}
    print(f"[ok]  Execute: processed={stats.get('processed')} failed={stats.get('failed')}")

    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        "SELECT status, message FROM sms_messages WHERE lead_id = ? ORDER BY id DESC LIMIT 1",
        (lead_id,),
    )
    if rows:
        row = rows[0]
        print(f"[sms] status={row.get('status')} message={str(row.get('message', ''))[:60]}")
        if row.get("status") == "sent":
            print("=" * 40)
            print("PASS — check your phone for the SMS.")
            return
        _fail(f"SMS row status={row.get('status')} (expected sent)")
    _fail("No sms_messages row for lead — follow-up did not reach Twilio send")


if __name__ == "__main__":
    main()
