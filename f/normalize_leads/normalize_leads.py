"""Deterministic lead normalization for the Windmill CE development pilot.

Pure functions only: no network, LLM, database, or secrets.
"""


import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MAX_BATCH_SIZE = 500
MAX_FIELD_LEN = 320
MAX_EMAIL_LEN = 254

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class LeadInput:
    email: str
    name: str
    company: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class RejectedLead:
    index: int
    reason: str
    email: Optional[str] = None


@dataclass
class LeadNormalizationResult:
    accepted: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_count: int = 0
    error_summary: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "accepted": list(self.accepted),
            "rejected": list(self.rejected),
            "duplicate_count": self.duplicate_count,
            "error_summary": list(self.error_summary),
        }


def _collapse_ws(value: str) -> str:
    return _WS_RE.sub(" ", (value or "").strip())


def _normalize_email(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    if raw is None:
        return None, "missing_email"
    if not isinstance(raw, str):
        return None, "invalid_email_type"
    email = raw.strip().lower()
    if not email:
        return None, "missing_email"
    if len(email) > MAX_EMAIL_LEN:
        return None, "email_too_long"
    if not _EMAIL_RE.match(email):
        return None, "malformed_email"
    return email, None


def _normalize_name(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    if raw is None:
        return None, "missing_name"
    if not isinstance(raw, str):
        return None, "invalid_name_type"
    name = _collapse_ws(raw)
    if not name:
        return None, "missing_name"
    if len(name) > MAX_FIELD_LEN:
        return None, "name_too_long"
    return name, None


def _optional_field(raw: Any, field_name: str) -> Tuple[Optional[str], Optional[str]]:
    if raw is None or raw == "":
        return None, None
    if not isinstance(raw, str):
        return None, f"invalid_{field_name}_type"
    value = _collapse_ws(raw)
    if not value:
        return None, None
    if len(value) > MAX_FIELD_LEN:
        return None, f"{field_name}_too_long"
    return value, None


def _coerce_record(raw: Any, index: int) -> Tuple[Optional[LeadInput], Optional[RejectedLead]]:
    if not isinstance(raw, dict):
        return None, RejectedLead(index=index, reason="not_an_object")
    email, email_err = _normalize_email(raw.get("email"))
    if email_err:
        return None, RejectedLead(index=index, reason=email_err, email=None)
    name, name_err = _normalize_name(raw.get("name"))
    if name_err:
        return None, RejectedLead(index=index, reason=name_err, email=email)
    company, company_err = _optional_field(raw.get("company"), "company")
    if company_err:
        return None, RejectedLead(index=index, reason=company_err, email=email)
    phone, phone_err = _optional_field(raw.get("phone"), "phone")
    if phone_err:
        return None, RejectedLead(index=index, reason=phone_err, email=email)
    return LeadInput(email=email, name=name, company=company, phone=phone), None


def normalize_leads(records: List[Any]) -> LeadNormalizationResult:
    """Normalize, validate, and dedupe lead records deterministically."""
    result = LeadNormalizationResult()
    if not isinstance(records, list):
        result.error_summary.append("records_must_be_a_list")
        result.rejected.append({"index": -1, "reason": "records_must_be_a_list"})
        return result

    if len(records) > MAX_BATCH_SIZE:
        result.error_summary.append("batch_too_large")
        result.rejected.append(
            {
                "index": -1,
                "reason": "batch_too_large",
                "max_batch_size": MAX_BATCH_SIZE,
                "received": len(records),
            }
        )
        return result

    if len(records) == 0:
        return result

    seen_emails: Dict[str, int] = {}
    accepted_rows: List[Tuple[str, str, Dict[str, Any]]] = []

    for index, raw in enumerate(records):
        lead, rejected = _coerce_record(raw, index)
        if rejected is not None:
            result.rejected.append(
                {
                    "index": rejected.index,
                    "reason": rejected.reason,
                    "email": rejected.email,
                }
            )
            continue
        assert lead is not None
        if lead.email in seen_emails:
            result.duplicate_count += 1
            result.rejected.append(
                {
                    "index": index,
                    "reason": "duplicate_email",
                    "email": lead.email,
                    "first_index": seen_emails[lead.email],
                }
            )
            continue
        seen_emails[lead.email] = index
        row = {
            "email": lead.email,
            "name": lead.name,
        }
        if lead.company is not None:
            row["company"] = lead.company
        if lead.phone is not None:
            row["phone"] = lead.phone
        accepted_rows.append((lead.email, lead.name, row))

    accepted_rows.sort(key=lambda item: (item[0], item[1], item[2].get("company") or ""))
    result.accepted = [row for _, _, row in accepted_rows]

    reason_counts: Dict[str, int] = {}
    for item in result.rejected:
        reason = str(item.get("reason") or "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    result.error_summary = [
        f"{reason}:{count}" for reason, count in sorted(reason_counts.items())
    ]
    return result


def normalize_leads_from_raw(records: Optional[List[Any]] = None) -> Dict[str, Any]:
    return normalize_leads(list(records or [])).as_dict()

def main(records=None):
    return normalize_leads_from_raw(records or [])
