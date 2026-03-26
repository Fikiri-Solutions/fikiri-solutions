"""Outbound SMS consent checks for CRM leads (recorded on leads.metadata)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


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
