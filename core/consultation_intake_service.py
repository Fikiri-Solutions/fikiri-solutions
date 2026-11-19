"""
Public consultation intake — domain logic separate from HTTP handlers.

How this fits in the architecture
----------------------------------
1. **CRM (canonical pipeline)** — `crm.service.enhanced_crm_service` → `leads`. Scored leads,
   automations, and dashboard UI read from here.

2. **POST /api/intake** (browser, no API key) — This module. Writes to CRM when
   `FIKIRI_INTAKE_LEAD_OWNER_USER_ID` is set; sends notification email + Slack;
   always appends a backup row in `customer_contact_submissions`
   (`form_type=consultation_intake`). Does **not** write to
   `customer_form_intake_submissions` (that table is reserved for
   **authenticated** `/api/webhooks/forms/submit` flows in `core/webhook_api.py`).

3. **POST /api/contact** — Short unstructured message; email + Slack +
   `customer_contact_submissions`; no CRM row (different product intent).

Failure isolation
-----------------
- CRM `create_lead` / `update_lead` exceptions are caught; the request can still succeed via email
  + Slack + backup row so ops is not blind.
- Email or Slack failure after CRM success does not fail the HTTP response (lead is already stored).
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

# Keep in sync with frontend `Intake.tsx` / short-form helpers (character caps).
# Legacy long-form keys remain accepted for compatibility with older clients.
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
    # Short-form v2
    "service_interests": 500,
    "service_detail": 200,
    "preferred_next_step": 40,
    "project_clarity": 40,
    "timeline_readiness": 40,
    "budget_readiness": 40,
    "lead_priority_band": 20,
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
    ("Service interests", "service_interests"),
    ("Service detail", "service_detail"),
    ("Project clarity", "project_clarity"),
    ("Timeline readiness", "timeline_readiness"),
    ("Budget readiness", "budget_readiness"),
    ("Lead priority", "lead_priority_band"),
    ("Preferred next step", "preferred_next_step"),
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
    "service_interests",
    "service_detail",
    "project_clarity",
    "timeline_readiness",
    "budget_readiness",
    "lead_priority_band",
    "preferred_next_step",
)

_PROJECT_CLARITY = frozenset({"exploring", "strong_idea", "know_exactly"})
_TIMELINE_READINESS = frozenset({"researching", "within_1_3_months", "ready_now"})
_BUDGET_READINESS = frozenset({"not_sure", "researching", "budget_ready"})
_LEAD_PRIORITY_BANDS = frozenset({"priority", "warm", "nurture"})


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


def _normalize_service_interests(raw: Any) -> str:
    """Accept a list or comma/newline-separated string; store as comma-separated ids."""
    mx = INTAKE_LIMITS["service_interests"]
    items: list[str] = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            token = _truncate(str(item or ""), 80)
            if token and token not in items:
                items.append(token)
            if len(items) >= 12:
                break
    else:
        text = str(raw or "").replace("\n", ",")
        for part in text.split(","):
            token = _truncate(part, 80)
            if token and token not in items:
                items.append(token)
            if len(items) >= 12:
                break
    return ",".join(items)[:mx]


def parse_service_interests_list(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _normalize_csv_field(raw: Any, *, max_len: int, max_items: int = 12) -> str:
    """Accept list or comma/newline-separated string; store as comma-separated tokens."""
    items: list[str] = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            token = _truncate(str(item or ""), 80)
            if token and token not in items:
                items.append(token)
            if len(items) >= max_items:
                break
    else:
        text = str(raw or "").replace("\n", ",")
        for part in text.split(","):
            token = _truncate(part, 80)
            if token and token not in items:
                items.append(token)
            if len(items) >= max_items:
                break
    return ",".join(items)[:max_len]


def derive_lead_priority_band(
    clarity: str, timeline: str, budget: str
) -> str:
    """
    Ops queue signal from soft vetting answers.
    priority = clear + ready + budget; warm = partial intent; nurture = exploring.
    """
    clear = clarity in ("strong_idea", "know_exactly")
    ready = timeline == "ready_now"
    funded = budget == "budget_ready"
    if clear and ready and funded:
        return "priority"
    if (ready or funded) and clarity != "exploring":
        return "warm"
    if ready or funded or clear:
        return "warm"
    return "nurture"


def parse_intake_body(data: Dict[str, Any]) -> Dict[str, str]:
    """Normalize and truncate intake fields from JSON (legacy + short-form)."""
    out: Dict[str, str] = {}
    skip_keys = {"service_interests", "service_detail", "lead_priority_band"}
    for key, mx in INTAKE_LIMITS.items():
        if key in skip_keys:
            continue
        out[key] = _truncate(str(data.get(key) or ""), mx)
    out["service_interests"] = _normalize_service_interests(data.get("service_interests"))
    out["service_detail"] = _normalize_csv_field(
        data.get("service_detail"), max_len=INTAKE_LIMITS["service_detail"]
    )
    out["leave_blank"] = _truncate(str(data.get("leave_blank") or ""), 20)
    preferred = (out.get("preferred_next_step") or "").strip().lower()
    if preferred in ("book", "booking", "calendar"):
        out["preferred_next_step"] = "book"
    elif preferred in ("follow_up", "follow-up", "email", "contact"):
        out["preferred_next_step"] = "follow_up"
    else:
        out["preferred_next_step"] = preferred

    clarity = (out.get("project_clarity") or "").strip().lower()
    timeline = (out.get("timeline_readiness") or "").strip().lower()
    budget = (out.get("budget_readiness") or "").strip().lower()
    out["project_clarity"] = clarity if clarity in _PROJECT_CLARITY else ""
    out["timeline_readiness"] = timeline if timeline in _TIMELINE_READINESS else ""
    out["budget_readiness"] = budget if budget in _BUDGET_READINESS else ""

    # Always recompute band server-side when vetting answers exist (ignore client spoof).
    if out["project_clarity"] and out["timeline_readiness"] and out["budget_readiness"]:
        out["lead_priority_band"] = derive_lead_priority_band(
            out["project_clarity"], out["timeline_readiness"], out["budget_readiness"]
        )
    else:
        raw_band = _truncate(str(data.get("lead_priority_band") or ""), 20).lower()
        out["lead_priority_band"] = raw_band if raw_band in _LEAD_PRIORITY_BANDS else ""
    return out


def validate_email(email: str, max_len: int = 254) -> bool:
    if not email or len(email) > max_len:
        return False
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def build_intake_plain_notes(p: Dict[str, str]) -> str:
    lines = [
        "Consultation intake (pre-call)",
        f"Contact: {p['contact_name']}",
        f"Email: {p['email']}",
    ]
    if p.get("business_name"):
        lines.insert(1, f"Business: {p['business_name']}")
    for label, k in _INTAKE_OPTIONAL_FIELDS:
        if p.get(k):
            lines.append(f"{label}: {p[k]}")
    return "\n".join(lines)


def build_intake_email_html(p: Dict[str, str]) -> str:
    from core.email_branding import wrap_html_email_body

    parts = [
        "<p><strong>Consultation intake</strong> (submitted via fikirisolutions.com)</p>",
        f"<p><strong>Contact:</strong> {html.escape(p['contact_name'])}</p>",
        f"<p><strong>Email:</strong> {html.escape(p['email'])}</p>",
    ]
    if p.get("business_name"):
        parts.insert(
            1,
            f"<p><strong>Business:</strong> {html.escape(p['business_name'])}</p>",
        )
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
        ("Service interests", "service_interests"),
        ("Service detail", "service_detail"),
        ("Project clarity", "project_clarity"),
        ("Timeline readiness", "timeline_readiness"),
        ("Budget readiness", "budget_readiness"),
        ("Lead priority", "lead_priority_band"),
        ("Preferred next step", "preferred_next_step"),
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
) -> bool:
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
                False,
                "sent" if sent else "failed",
                None if sent else "email_send_failed",
                request_ip,
                user_agent,
            ),
            fetch=False,
        )
        return True
    except Exception as e:
        logger.error("Failed to persist consultation intake submission: %s", e)
        return False


def _crm_create_or_merge_lead(
    owner_id: int,
    p: Dict[str, str],
    plain_notes: str,
    meta: Dict[str, Any],
    correlation_id: str,
) -> str:
    """
    Persist intake to CRM.

    Returns: ``created`` | ``merged`` | ``duplicate`` | ``failed``.
    ``duplicate`` = same correlation_id already applied (retry) — skip re-notify.
    """
    from crm.service import enhanced_crm_service

    lead_data = {
        "email": p["email_norm"],
        "name": p["contact_name"],
        "phone": p.get("phone") or None,
        "company": p.get("business_name") or None,
        "source": p.get("source") or "consultation_intake",
        "stage": "new",
        "notes": plain_notes,
        "metadata": meta,
        "correlation_id": correlation_id,
    }
    try:
        result = enhanced_crm_service.create_lead(owner_id, lead_data)
        if result.get("success"):
            return "created"
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
                return "failed"
            lid = row[0]["id"]
            old_notes = row[0].get("notes") or ""
            try:
                old_meta = json.loads(row[0].get("metadata") or "{}")
            except Exception:
                old_meta = {}
            if not isinstance(old_meta, dict):
                old_meta = {}
            if correlation_id and old_meta.get("correlation_id") == correlation_id:
                return "duplicate"
            merged_meta = {
                **old_meta,
                **meta,
                "correlation_id": correlation_id,
                "last_intake_resubmission_at": utc_now_iso(),
            }
            block = f"\n\n--- Intake update ({utc_now_iso()}) ---\n{plain_notes}"
            new_notes = (old_notes + block) if old_notes else plain_notes
            # Refresh identity fields on resubmit so typos / preferred name stick.
            update_fields: Dict[str, Any] = {
                "notes": new_notes[:65000],
                "metadata": merged_meta,
                "correlation_id": correlation_id,
            }
            if p.get("contact_name"):
                update_fields["name"] = p["contact_name"]
            if p.get("phone"):
                update_fields["phone"] = p["phone"]
            if p.get("business_name"):
                update_fields["company"] = p["business_name"]
            upd = enhanced_crm_service.update_lead(
                lid,
                owner_id,
                update_fields,
            )
            return "merged" if upd.get("success") else "failed"
        logger.warning("Intake CRM create failed: %s", result.get("error"))
        return "failed"
    except Exception:
        logger.exception("Intake CRM create/update raised (fail open to email/backup)")
        return "failed"


@dataclass
class PublicIntakeProcessResult:
    """Outcome for the HTTP layer to map to status codes and JSON."""

    crm_ok: bool
    email_sent: bool
    slack_sent: bool
    email_failed_after_crm: bool
    persisted: bool
    duplicate_retry: bool = False


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
    from core.lead_form_notifications import lead_dedupe_key, send_lead_slack_notification

    # Normalize email for CRM uniqueness (case-insensitive pipeline key for intake).
    p = dict(p)
    p["email_norm"] = p.get("email", "").strip().lower()

    plain_notes = build_intake_plain_notes(p)
    interests = parse_service_interests_list(p.get("service_interests") or "")
    is_short_form = bool(
        interests
        or p.get("preferred_next_step")
        or p.get("service_detail")
        or p.get("lead_priority_band")
        or p.get("project_clarity")
    )
    meta: Dict[str, Any] = {
        "intake_version": 2 if is_short_form else 1,
        "form": "consultation_intake",
        "business_name": p.get("business_name") or None,
        "contact_name": p.get("contact_name"),
        "email_submitted": p.get("email"),
        "industry": p.get("industry") or None,
        "source_channel": p.get("source") or None,
        "correlation_id": correlation_id,
        "submitted_at": utc_now_iso(),
    }
    if interests:
        meta["service_interests"] = interests
        meta["lead_interests"] = interests
    for k in _META_EXTRA_KEYS:
        if k == "service_interests":
            continue
        if p.get(k):
            meta[k] = p[k]

    subject_label = p.get("business_name") or p.get("contact_name") or "lead"
    email_subject = f"Consultation intake: {subject_label}"
    if len(email_subject) > 200:
        email_subject = email_subject[:197] + "..."
    body_html = build_intake_email_html(p)

    owner_id = intake_owner_user_id()
    crm_status = "failed"
    if owner_id:
        crm_status = _crm_create_or_merge_lead(owner_id, p, plain_notes, meta, correlation_id)
    crm_ok = crm_status in ("created", "merged", "duplicate")
    duplicate_retry = crm_status == "duplicate"

    sent = False
    slack_sent = False
    if not duplicate_retry:
        try:
            sent = bool(send_notification_email(contact_to_email, email_subject, body_html))
        except Exception:
            logger.exception("Intake notification email send raised")

        slack_title_label = p.get("business_name") or p.get("contact_name") or "lead"
        interest_preview = ", ".join(interests[:4]) if interests else "—"
        priority_band = (p.get("lead_priority_band") or "").strip().lower()
        priority_label = {
            "priority": "PRIORITY — ready to engage",
            "warm": "Warm — nurture with intent",
            "nurture": "Exploring — nurture",
        }.get(priority_band, "—")
        title_prefix = "Priority intake" if priority_band == "priority" else "Consultation intake"
        slack_sent = send_lead_slack_notification(
            title=f"{title_prefix}: {slack_title_label}",
            text=plain_notes[:1500],
            fields=[
                {"title": "Queue", "value": priority_label, "short": True},
                {"title": "Contact", "value": p["contact_name"], "short": True},
                {"title": "Email", "value": p["email"], "short": True},
                {"title": "Phone", "value": p.get("phone") or "—", "short": True},
                {"title": "Industry", "value": p.get("industry") or "—", "short": True},
                {
                    "title": "Clarity",
                    "value": p.get("project_clarity") or "—",
                    "short": True,
                },
                {
                    "title": "Timeline",
                    "value": p.get("timeline_readiness") or "—",
                    "short": True,
                },
                {
                    "title": "Budget",
                    "value": p.get("budget_readiness") or "—",
                    "short": True,
                },
                {"title": "Interests", "value": interest_preview, "short": False},
                {
                    "title": "Next step",
                    "value": p.get("preferred_next_step") or "—",
                    "short": True,
                },
                {"title": "CRM", "value": "saved" if crm_ok else "not saved", "short": True},
                {
                    "title": "Email delivery",
                    "value": "sent" if sent else "FAILED",
                    "short": True,
                },
                {"title": "Correlation", "value": correlation_id, "short": False},
            ],
            dedupe_key=lead_dedupe_key("intake", correlation_id or p.get("email_norm")),
            blocking=False,
        )
    else:
        logger.info(
            "Intake duplicate retry skipped notifications correlation_id=%s",
            correlation_id,
        )

    payload_obj = {
        **{k: v for k, v in p.items() if k not in ("leave_blank", "email_norm")},
        "correlation_id": correlation_id,
        "crm_ok": crm_ok,
        "crm_status": crm_status,
        "slack_sent": slack_sent,
        "duplicate_retry": duplicate_retry,
    }

    # Always append a durable backup row so ops never depends on CRM or mail alone.
    # Skip a second backup row on pure duplicate retries to limit noise.
    persisted = True
    if not duplicate_retry:
        persisted = _persist_intake_contact_fallback(
            p=p,
            plain_notes=plain_notes,
            payload_obj=payload_obj,
            email_subject=email_subject,
            sent=bool(sent or slack_sent),
            contact_to_email=contact_to_email,
            contact_from_email=contact_from_email,
            request_ip=request_ip,
            user_agent=user_agent,
        )

    return PublicIntakeProcessResult(
        crm_ok=crm_ok,
        email_sent=sent,
        slack_sent=slack_sent,
        email_failed_after_crm=bool(crm_ok and not sent and not duplicate_retry),
        persisted=persisted,
        duplicate_retry=duplicate_retry,
    )
