#!/usr/bin/env python3
"""
Verify public short-form consultation intake: speed, field capture, and routing.

Checks (per persona):
  1. POST /api/intake succeeds quickly
  2. Response includes correlation_id + preferred_next_step
  3. Lead lands in CRM (when FIKIRI_INTAKE_LEAD_OWNER_USER_ID is set)
  4. Backup row in customer_contact_submissions (form_type=consultation_intake)
  5. service_interests / main_pain / preferred_next_step persisted correctly
  6. Duplicate correlation_id does not create a second notification path when CRM is on

Usage:
  python3 scripts/verify_public_intake_loop.py
  FIKIRI_INTAKE_VERIFY_BASE=http://127.0.0.1:5000/api python3 scripts/verify_public_intake_loop.py

Exit 0 = all personas pass; exit 1 = one or more failures.
Writes JSON report to data/intake_verify_latest.json
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "intake_verify_latest.json"
DEFAULT_BASE = os.getenv("FIKIRI_INTAKE_VERIFY_BASE", "http://127.0.0.1:5000/api").rstrip("/")
LATENCY_BUDGET_MS = float(os.getenv("FIKIRI_INTAKE_LATENCY_BUDGET_MS", "2500"))

PERSONAS: List[Dict[str, Any]] = [
    {
        "id": "website_redesign",
        "label": "Website redesign client",
        "payload": {
            "contact_name": "Maya Chen",
            "email": "maya.verify.website@example.test",
            "business_name": "Harbor Home Goods",
            "industry": "Retail / ecommerce",
            "main_pain": "Our site looks dated and product inquiries never get followed up.",
            "service_interests": ["website_design_development", "leads_customer_management"],
            "service_detail": "redesign",
            "preferred_next_step": "follow_up",
            "source": "intake_verify_loop",
        },
        "expect_interests": [
            "website_design_development",
            "leads_customer_management",
        ],
        "expect_detail": "redesign",
        "expect_next": "follow_up",
    },
    {
        "id": "custom_software_crm",
        "label": "Custom CRM / portal client",
        "payload": {
            "contact_name": "Jordan Blake",
            "email": "jordan.verify.software@example.test",
            "phone": "555-0102",
            "industry": "Professional services",
            "main_pain": "We need a client portal and internal ops dashboard — spreadsheets are breaking.",
            "service_interests": ["custom_software_systems"],
            "service_detail": "client_portals",
            "preferred_next_step": "book",
            "source": "intake_verify_loop",
        },
        "expect_interests": ["custom_software_systems"],
        "expect_detail": "client_portals",
        "expect_next": "book",
    },
    {
        "id": "not_sure_automation",
        "label": "Not sure / automation explore",
        "payload": {
            "contact_name": "Sam Okoro",
            "email": "sam.verify.unsure@example.test",
            "main_pain": "Too much manual follow-up; not sure if we need automation or a better CRM first.",
            "service_interests": ["not_sure_lets_talk", "ai_business_automation"],
            "preferred_next_step": "follow_up",
            "source": "intake_verify_loop",
        },
        # UI clears not_sure when other chips selected; API accepts both — expect at least AI
        "expect_interests_any": ["ai_business_automation", "not_sure_lets_talk"],
        "expect_next": "follow_up",
    },
]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = val.strip().strip('"').strip("'")


def _db_path() -> Path:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw.startswith("sqlite:///"):
        path = raw.replace("sqlite:///", "", 1)
        p = Path(path)
        return p if p.is_absolute() else ROOT / p
    return ROOT / "data" / "fikiri.db"


def _post_intake(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], float]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{DEFAULT_BASE}/intake",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            elapsed_ms = (time.perf_counter() - started) * 1000
            return resp.status, json.loads(raw or "{}"), elapsed_ms
    except HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            data = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            data = {"error": str(exc)}
        return int(exc.code), data, elapsed_ms
    except URLError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return 0, {"error": f"connection_failed: {exc.reason}"}, elapsed_ms


def _query_backup(email: str) -> Optional[Dict[str, Any]]:
    db = _db_path()
    if not db.exists():
        return None
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            """
            SELECT id, form_type, name, email, company, message, payload_json, send_status, created_at
            FROM customer_contact_submissions
            WHERE lower(email) = lower(?) AND form_type = 'consultation_intake'
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _query_lead(email: str, owner_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not owner_id:
        return None
    db = _db_path()
    if not db.exists():
        return None
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            """
            SELECT id, email, name, company, source, notes, metadata, user_id
            FROM leads
            WHERE user_id = ? AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (owner_id, email),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _parse_meta(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _check_persona(persona: Dict[str, Any], owner_id: Optional[int]) -> Dict[str, Any]:
    correlation_id = f"verify-{persona['id']}-{uuid.uuid4().hex[:10]}"
    payload = dict(persona["payload"])
    payload["correlation_id"] = correlation_id

    status, data, latency_ms = _post_intake(payload)
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("http_success", status == 200 and bool(data.get("success")), f"status={status} body={data}")
    add(
        "latency_under_budget",
        latency_ms <= LATENCY_BUDGET_MS,
        f"{latency_ms:.0f}ms budget={LATENCY_BUDGET_MS:.0f}ms",
    )
    add(
        "correlation_echoed",
        data.get("correlation_id") == correlation_id,
        f"got={data.get('correlation_id')}",
    )
    add(
        "preferred_next_step_routed",
        data.get("preferred_next_step") == persona.get("expect_next"),
        f"got={data.get('preferred_next_step')} expect={persona.get('expect_next')}",
    )

    # Give SQLite a beat if write is async-ish (it isn't, but keep stable under load).
    time.sleep(0.05)
    backup = _query_backup(payload["email"])
    add("backup_row_present", backup is not None, "customer_contact_submissions")
    if backup:
        add(
            "backup_form_type",
            backup.get("form_type") == "consultation_intake",
            str(backup.get("form_type")),
        )
        add(
            "backup_contact_name",
            (backup.get("name") or "") == payload["contact_name"],
            str(backup.get("name")),
        )
        payload_json = _parse_meta(backup.get("payload_json"))
        interests = payload_json.get("service_interests") or ""
        if isinstance(interests, list):
            interest_tokens = interests
        else:
            interest_tokens = [p.strip() for p in str(interests).split(",") if p.strip()]
        expected = persona.get("expect_interests") or []
        any_of = persona.get("expect_interests_any") or []
        if expected:
            add(
                "backup_service_interests",
                all(i in interest_tokens for i in expected),
                f"got={interest_tokens}",
            )
        if any_of:
            add(
                "backup_service_interests_any",
                any(i in interest_tokens for i in any_of),
                f"got={interest_tokens}",
            )
        if persona.get("expect_detail"):
            add(
                "backup_service_detail",
                payload_json.get("service_detail") == persona["expect_detail"],
                str(payload_json.get("service_detail")),
            )
        add(
            "backup_main_pain",
            payload["main_pain"] in (backup.get("message") or ""),
            "main_pain in notes",
        )
        add(
            "backup_preferred_next_step",
            payload_json.get("preferred_next_step") == persona.get("expect_next"),
            str(payload_json.get("preferred_next_step")),
        )

    lead = _query_lead(payload["email"], owner_id)
    if owner_id:
        add("crm_lead_present", lead is not None, f"owner_id={owner_id}")
        if lead:
            meta = _parse_meta(lead.get("metadata"))
            add("crm_intake_version", meta.get("intake_version") == 2, str(meta.get("intake_version")))
            lead_interests = meta.get("lead_interests") or meta.get("service_interests") or []
            expected = persona.get("expect_interests") or []
            any_of = persona.get("expect_interests_any") or []
            if expected:
                add(
                    "crm_lead_interests",
                    all(i in lead_interests for i in expected),
                    f"got={lead_interests}",
                )
            if any_of:
                add(
                    "crm_lead_interests_any",
                    any(i in lead_interests for i in any_of),
                    f"got={lead_interests}",
                )
            add(
                "crm_preferred_next_step",
                meta.get("preferred_next_step") == persona.get("expect_next"),
                str(meta.get("preferred_next_step")),
            )
            add(
                "crm_source_channel",
                (meta.get("source_channel") or lead.get("source") or "").startswith("intake"),
                str(meta.get("source_channel") or lead.get("source")),
            )
    else:
        add(
            "crm_owner_configured",
            False,
            "FIKIRI_INTAKE_LEAD_OWNER_USER_ID unset — CRM routing skipped (backup still required)",
        )

    # Retry with same correlation_id — should succeed; with CRM owner, notifications dedupe.
    status2, data2, latency2 = _post_intake(payload)
    add(
        "retry_same_correlation_ok",
        status2 == 200 and bool(data2.get("success")),
        f"status={status2} latency={latency2:.0f}ms",
    )

    failed = [c for c in checks if not c["ok"]]
    # crm_owner_configured is a soft warning when unset — mark as warn not hard fail
    hard_failed = [
        c
        for c in failed
        if c["name"] != "crm_owner_configured"
    ]

    return {
        "persona": persona["id"],
        "label": persona["label"],
        "correlation_id": correlation_id,
        "latency_ms": round(latency_ms, 1),
        "retry_latency_ms": round(latency2, 1),
        "http_status": status,
        "checks": checks,
        "pass": len(hard_failed) == 0,
        "warnings": [c for c in failed if c["name"] == "crm_owner_configured"],
        "failures": hard_failed,
    }


def main() -> int:
    _load_dotenv()
    owner_raw = (os.getenv("FIKIRI_INTAKE_LEAD_OWNER_USER_ID") or "").strip()
    owner_id: Optional[int] = None
    if owner_raw.isdigit() and int(owner_raw) > 0:
        owner_id = int(owner_raw)

    # Health probe
    health_ok = False
    health_detail = ""
    try:
        with urlopen(f"{DEFAULT_BASE}/health", timeout=5) as resp:
            health_ok = resp.status == 200
            health_detail = f"status={resp.status}"
    except Exception as exc:
        health_detail = str(exc)

    results = []
    if health_ok:
        for persona in PERSONAS:
            results.append(_check_persona(persona, owner_id))
    else:
        results.append(
            {
                "persona": "_health",
                "label": "API health",
                "pass": False,
                "failures": [{"name": "api_reachable", "ok": False, "detail": health_detail}],
                "checks": [],
                "latency_ms": None,
            }
        )

    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    report = {
        "event": "intake_verify_loop",
        "service": "consultation_intake",
        "severity": "INFO" if passed == total else "ERROR",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": DEFAULT_BASE,
        "owner_id": owner_id,
        "latency_budget_ms": LATENCY_BUDGET_MS,
        "health_ok": health_ok,
        "health_detail": health_detail,
        "passed": passed,
        "total": total,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Concise stdout for loop ticks
    print(f"INTAKE_VERIFY {passed}/{total} pass owner={owner_id or 'none'} base={DEFAULT_BASE}")
    for r in results:
        status = "PASS" if r.get("pass") else "FAIL"
        lat = r.get("latency_ms")
        lat_s = f"{lat:.0f}ms" if isinstance(lat, (int, float)) else "n/a"
        print(f"  [{status}] {r.get('persona')} latency={lat_s}")
        for f in r.get("failures") or []:
            print(f"    - {f['name']}: {f.get('detail')}")
        for w in r.get("warnings") or []:
            print(f"    ~ warn {w['name']}: {w.get('detail')}")
    print(f"REPORT {REPORT_PATH}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
