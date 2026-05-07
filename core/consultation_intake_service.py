"""
Public consultation intake — domain logic separate from HTTP handlers.

How this fits in the architecture
----------------------------------
1. **CRM (canonical pipeline)** — `crm.service.enhanced_crm_service` → `leads`. Scored leads,
   automations, and dashboard UI read from here.

2. **POST /api/intake** (browser, no API key) — This module. Writes to CRM when
   `FIKIRI_INTAKE_LEAD_OWNER_USER_ID` is set; sends notification email; on CRM or total failure
   paths, append-only backup in `customer_contact_submissions` (`form_type=consultation_intake`).
   Does **not** write to `customer_form_intake_submissions` (that table is reserved for
   **authenticated** `/api/webhooks/forms/submit` flows in `core/webhook_api.py`).

3. **POST /api/contact** — Short unstructured message; email + `customer_contact_submissions` only;
   no CRM row (different product intent).

Failure isolation
-----------------
- CRM `create_lead` / `update_lead` exceptions are caught; the request can still succeed via email
  + backup row so ops is not blind.
- Email failure **after** CRM success does not fail the HTTP response (lead is already stored).
- Rate limiting and honeypot remain in the Flask route (HTTP concerns).
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

INTAKE_OWNER_ENV = "FIKIRI_INTAKE_LEAD_OWNER_USER_ID"

# Keep in sync with frontend `Intake.tsx` LIMITS (character caps).
INTAKE_LIMITS: Dict[str, int] = {
    "business_name": 200,
    "contact_name": 200,
    "email": 254,
    "phone": 50,
    "website": 300,
    "location": 120,
    "industry": 80,
    "source": 80,
    "business_size": 40,
    "monthly_revenue_range": 80,
    "weekly_volume": 80,
    "current_tools": 1500,
    "workflow_focus": 400,
    "input_summary": 1500,
    "decision_bottleneck": 1500,
    "execution_process": 1500,
    "follow_up_process": 1500,
    "money_impact": 1500,
    "main_pain": 1500,
    "automation_opportunity": 1500,
    "fixed_looks_like": 500,
}

_INTAKE_OPTIONAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("Phone", "phone"),
    ("Website", "website"),
    ("Location", "location"),
    ("Industry", "industry"),
    ("How they heard about us", "source"),
    ("Business size", "business_size"),
    ("Monthly revenue (band)", "monthly_revenue_range"),
    ("Weekly volume (band)", "weekly_volume"),
    ("Current tools", "current_tools"),
    ("Workflow to map (one line)", "workflow_focus"),
    ("Input — where work enters", "input_summary"),
    ("Decision bottleneck", "decision_bottleneck"),
    ("Execution", "execution_process"),
    ("Follow-up", "follow_up_process"),
    ("Money / revenue impact", "money_impact"),
    ("Main pain", "main_pain"),
    ("Automation opportunity", "automation_opportunity"),
    ('What “fixed” looks like', "fixed_looks_like"),
)

_META_EXTRA_KEYS = (
    "website",
    "location",
    "business_size",
    "monthly_revenue_range",
    "weekly_volume",
    "current_tools",
    "workflow_focus",
    "input_summary",
    "decision_bottleneck",
    "execution_process",
    "follow_up_process",
    "money_impact",
    "main_pain",
    "automation_opportunity",
    "fixed_looks_like",
)


def _truncate(s: str, max_len: int) -> str:
    if s is None:
        return ""
    return (s.strip() or "")[:max_len]


def intake_owner_user_id() -> Optional[int]:
    raw = os.getenv(INTAKE_OWNER_ENV, "").strip()
    if not raw:
        return None
    try:
        uid = int(raw)
        return uid if uid > 0 else None
    except ValueError:
        logger.warning("Invalid %s — expected positive integer user id", INTAKE_OWNER_ENV)
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_intake_body(data: Dict[str, Any]) -> Dict[str, str]:
    """Normalize and truncate intake fields from JSON."""
    out: Dict[str, str] = {}
    for key, mx in INTAKE_LIMITS.items():
        out[key] = _truncate(str(data.get(key) or ""), mx)
    out["leave_blank"] = _truncate(str(data.get("leave_blank") or ""), 20)
    return out


def validate_email(email: str, max_len: int = 254) -> bool:
    if not email or len(email) > max_len:
        return False
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def build_intake_plain_notes(p: Dict[str, str]) -> str:
    lines = [
        "Consultation intake (pre-call)",
        f"Business: {p['business_name']}",
        f"Contact: {p['contact_name']}",
        f"Email: {p['email']}",
    ]
    for label, k in _INTAKE_OPTIONAL_FIELDS:
        if p.get(k):
            lines.append(f"{label}: {p[k]}")
    return "\n".join(lines)


def build_intake_email_html(p: Dict[str, str]) -> str:
    from core.email_branding import wrap_html_email_body

    parts = [
        "<p><strong>Consultation intake</strong> (submitted via fikirisolutions.com)</p>",
        f"<p><strong>Business:</strong> {html.escape(p['business_name'])}</p>",
        f"<p><strong>Contact:</strong> {html.escape(p['contact_name'])}</p>",
        f"<p><strong>Email:</strong> {html.escape(p['email'])}</p>",
    ]
    email_labels = (
        ("Phone", "phone"),
        ("Website", "website"),
        ("Location", "location"),
        ("Industry", "industry"),
        ("Source", "source"),
        ("Business size", "business_size"),
        ("Monthly revenue", "monthly_revenue_range"),
        ("Weekly volume", "weekly_volume"),
        ("Current tools", "current_tools"),
        ("Workflow focus", "workflow_focus"),
        ("Input summary", "input_summary"),
        ("Decision bottleneck", "decision_bottleneck"),
        ("Execution", "execution_process"),
        ("Follow-up", "follow_up_process"),
        ("Money impact", "money_impact"),
        ("Main pain", "main_pain"),
        ("Automation opportunity", "automation_opportunity"),
        ('What “fixed” looks like', "fixed_looks_like"),
    )
    for label, k in email_labels:
        if p.get(k):
            esc = html.escape(p[k]).replace("\n", "<br>")
            parts.append(f"<p><strong>{html.escape(label)}:</strong><br>{esc}</p>")
    return wrap_html_email_body("\n".join(parts))


def _persist_intake_contact_fallback(
    *,
    p: Dict[str, str],
    plain_notes: str,
    payload_obj: Dict[str, Any],
    email_subject: str,
    sent: bool,
    contact_to_email: str,
    contact_from_email: str,
    request_ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    try:
        payload_json = json.dumps(payload_obj, ensure_ascii=False)
        db_optimizer.execute_query(
            """
            INSERT INTO customer_contact_submissions (
                form_type, name, email, phone, company, subject, message,
                email_subject, to_email, from_email, payload_json, payload_truncated,
                send_status, send_error,
                request_ip, user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "consultation_intake",
                p["contact_name"],
                p["email"],
                p.get("phone") or None,
                p.get("business_name") or None,
                "Consultation intake",
                plain_notes,
                email_subject,
                contact_to_email,
                contact_from_email,
                payload_json,
                0,
                "sent" if sent else "failed",
                None if sent else "email_send_failed",
                request_ip,
                user_agent,
            ),
            fetch=False,
        )
    except Exception as e:
        logger.error("Failed to persist consultation intake submission: %s", e)


def _crm_create_or_merge_lead(
    owner_id: int,
    p: Dict[str, str],
    plain_notes: str,
    meta: Dict[str, Any],
    correlation_id: str,
) -> bool:
    """Return True if CRM reflects this intake. Swallows exceptions (fail open to backup path)."""
    from crm.service import enhanced_crm_service

    lead_data = {
        "email": p["email_norm"],
        "name": p["contact_name"],
        "phone": p.get("phone") or None,
        "company": p["business_name"],
        "source": p.get("source") or "consultation_intake",
        "stage": "new",
        "notes": plain_notes,
        "metadata": meta,
        "correlation_id": correlation_id,
    }
    try:
        result = enhanced_crm_service.create_lead(owner_id, lead_data)
        if result.get("success"):
            return True
        if result.get("error_code") == "LEAD_EXISTS":
            row = db_optimizer.execute_query(
                """
                SELECT id, notes, metadata FROM leads
                WHERE user_id = ? AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
                LIMIT 1
                """,
                (owner_id, p["email_norm"]),
            )
            if not row:
                logger.warning("LEAD_EXISTS but row missing for email=%s", p["email_norm"])
                return False
            lid = row[0]["id"]
            old_notes = row[0].get("notes") or ""
            try:
                old_meta = json.loads(row[0].get("metadata") or "{}")
            except Exception:
                old_meta = {}
            if not isinstance(old_meta, dict):
                old_meta = {}
            merged_meta = {**old_meta, **meta, "last_intake_resubmission_at": utc_now_iso()}
            block = f"\n\n--- Intake update ({utc_now_iso()}) ---\n{plain_notes}"
            new_notes = (old_notes + block) if old_notes else plain_notes
            upd = enhanced_crm_service.update_lead(
                lid,
                owner_id,
                {
                    "notes": new_notes[:65000],
                    "metadata": merged_meta,
                    "correlation_id": correlation_id,
                },
            )
            return bool(upd.get("success"))
        logger.warning("Intake CRM create failed: %s", result.get("error"))
        return False
    except Exception:
        logger.exception("Intake CRM create/update raised (fail open to email/backup)")
        return False


@dataclass
class PublicIntakeProcessResult:
    """Outcome for the HTTP layer to map to status codes and JSON."""

    crm_ok: bool
    email_sent: bool
    email_failed_after_crm: bool


def process_public_intake(
    *,
    p: Dict[str, str],
    correlation_id: str,
    send_notification_email,
    contact_to_email: str,
    contact_from_email: str,
    request_ip: Optional[str],
    user_agent: Optional[str],
) -> PublicIntakeProcessResult:
    """
    Apply CRM + notification + backup persistence. Caller handles rate limit / honeypot / JSON.

    ``send_notification_email`` is a callable ``(to_email: str, subject: str, html_body: str) -> bool``
    injected from ``contact_api`` so mail transport stays in one place.
    """
    # Normalize email for CRM uniqueness (case-insensitive pipeline key for intake).
    p = dict(p)
    p["email_norm"] = p.get("email", "").strip().lower()

    plain_notes = build_intake_plain_notes(p)
    meta: Dict[str, Any] = {
        "intake_version": 1,
        "form": "consultation_intake",
        "business_name": p.get("business_name"),
        "contact_name": p.get("contact_name"),
        "email_submitted": p.get("email"),
        "industry": p.get("industry") or None,
        "source_channel": p.get("source") or None,
        "submitted_at": utc_now_iso(),
    }
    for k in _META_EXTRA_KEYS:
        if p.get(k):
            meta[k] = p[k]

    email_subject = f"Consultation intake: {p['business_name']}"
    if len(email_subject) > 200:
        email_subject = email_subject[:197] + "..."
    body_html = build_intake_email_html(p)

    owner_id = intake_owner_user_id()
    crm_ok = False
    if owner_id:
        crm_ok = _crm_create_or_merge_lead(owner_id, p, plain_notes, meta, correlation_id)

    sent = False
    try:
        sent = bool(send_notification_email(contact_to_email, email_subject, body_html))
    except Exception:
        logger.exception("Intake notification email send raised")

    payload_obj = {
        **{k: v for k, v in p.items() if k not in ("leave_blank", "email_norm")},
        "correlation_id": correlation_id,
    }

    if not crm_ok:
        _persist_intake_contact_fallback(
            p=p,
            plain_notes=plain_notes,
            payload_obj=payload_obj,
            email_subject=email_subject,
            sent=sent,
            contact_to_email=contact_to_email,
            contact_from_email=contact_from_email,
            request_ip=request_ip,
            user_agent=user_agent,
        )

    return PublicIntakeProcessResult(
        crm_ok=crm_ok,
        email_sent=sent,
        email_failed_after_crm=bool(crm_ok and not sent),
    )
