"""Outbound SMS consent checks for CRM leads (recorded on leads.metadata)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# User-facing copy when lead_row_allows_sms fails for missing consent.
SMS_CONSENT_BLOCKED_MESSAGE = (
    "SMS was not sent because this lead has not consented to SMS follow-ups."
)


def parse_lead_metadata(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return {}
    return {}


def lead_row_allows_sms(lead: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    True only when leads.metadata has sms_consent explicitly True.
    Store consent with: {"sms_consent": true, "sms_consent_at": "<ISO8601>"}
    """
    if not lead:
        return False, "lead_not_found"
    meta = parse_lead_metadata(lead.get("metadata"))
    if meta.get("sms_consent") is True:
        return True, ""
    return False, "sms_consent_required"


def sms_consent_denial_message(reason: str) -> str:
    """Map lead_row_allows_sms reason codes to a single user-facing message."""
    if reason == "sms_consent_required":
        return SMS_CONSENT_BLOCKED_MESSAGE
    return reason or SMS_CONSENT_BLOCKED_MESSAGE


def sms_consent_denial_payload(reason: str) -> Dict[str, Any]:
    """Shared blocked/skipped result for send_sms and scheduled SMS follow-ups."""
    msg = sms_consent_denial_message(reason)
    return {
        "success": False,
        "skipped": True,
        "error": msg,
        "error_code": "SMS_CONSENT_REQUIRED",
        "message": msg,
    }


def apply_lead_sms_consent_to_metadata(
    base_meta: Optional[Dict[str, Any]],
    consent_flag: bool,
    *,
    source: str = "manual_crm",
) -> Dict[str, Any]:
    """
    Merge SMS consent fields into existing lead metadata (does not replace unrelated keys).
    """
    meta = dict(base_meta or {})
    consent_true = consent_flag is True
    meta["sms_consent"] = consent_true
    meta["sms_consent_at"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if consent_true
        else None
    )
    if consent_true:
        meta["sms_consent_source"] = source
    return meta


def normalize_phone_digits(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return "".join(c for c in str(phone) if c.isdigit())


def lead_sms_destination_matches(lead_phone: Optional[str], requested_to: Optional[str]) -> bool:
    """If requested_to is empty, caller should use lead_phone only."""
    if not requested_to or not str(requested_to).strip():
        return True
    a = normalize_phone_digits(lead_phone)
    b = normalize_phone_digits(requested_to)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 10 and len(b) >= 10 and a[-10:] == b[-10:]:
        return True
    return False


def lead_has_valid_phone(lead: Optional[Dict[str, Any]]) -> bool:
    if not lead:
        return False
    return bool(str(lead.get("phone") or "").strip())
