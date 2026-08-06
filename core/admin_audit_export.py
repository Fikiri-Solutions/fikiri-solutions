"""Bounded, allowlisted audit export helpers (no raw metadata)."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, List, Optional

REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
EXPORT_MAX_ROWS = 200


def controlled_reason_from_metadata(metadata: Any) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("reason") or metadata.get("error_code") or metadata.get("code")
    if not raw:
        return None
    code = str(raw).strip()
    if not REASON_CODE_RE.match(code):
        return None
    return code


def sanitize_audit_export_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """Explicit allowlist — never serialize full audit rows."""
    out: Dict[str, Any] = {}
    if item.get("created_at") is not None:
        out["timestamp"] = str(item.get("created_at"))
    if item.get("action"):
        out["action"] = str(item.get("action"))
    if item.get("outcome"):
        out["outcome"] = str(item.get("outcome"))
    reason = controlled_reason_from_metadata(item.get("metadata"))
    if reason:
        out["reason"] = reason
    if item.get("actor_user_id") is not None:
        out["actor_id"] = int(item.get("actor_user_id"))
    if item.get("target_type"):
        out["target_type"] = str(item.get("target_type"))
    if item.get("target_id") is not None and item.get("target_id") != "":
        out["target_id"] = str(item.get("target_id"))
    if item.get("correlation_id"):
        corr = str(item.get("correlation_id")).strip()
        if corr:
            out["correlation_id"] = corr
    if item.get("capability"):
        out["capability"] = str(item.get("capability"))
    return out


def build_audit_export_payload(
    items: List[Dict[str, Any]],
    *,
    fmt: str = "json",
) -> Dict[str, Any]:
    rows = [sanitize_audit_export_row(item) for item in items]
    fmt_norm = (fmt or "json").strip().lower()
    if fmt_norm not in ("json", "csv"):
        fmt_norm = "json"
    body: str
    content_type: str
    if fmt_norm == "csv":
        fieldnames = [
            "timestamp",
            "action",
            "outcome",
            "reason",
            "actor_id",
            "target_type",
            "target_id",
            "correlation_id",
            "capability",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        body = buf.getvalue()
        content_type = "text/csv; charset=utf-8"
    else:
        body = json.dumps({"items": rows, "count": len(rows)}, default=str)
        content_type = "application/json; charset=utf-8"
    return {
        "format": fmt_norm,
        "count": len(rows),
        "content_type": content_type,
        "body": body,
        "items": rows if fmt_norm == "json" else None,
    }
