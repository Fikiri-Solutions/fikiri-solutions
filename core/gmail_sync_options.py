"""
Gmail sync request options: lookback windows and per-job batch size.

Used by POST /api/crm/sync-gmail and GmailSyncJobManager job metadata.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Preset id -> days (investor / power-user historical windows)
GMAIL_LOOKBACK_PRESETS: Dict[str, int] = {
    "60d": 60,
    "90d": 90,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
}

ALLOWED_LOOKBACK_DAYS = frozenset(GMAIL_LOOKBACK_PRESETS.values())
DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_MAX_MESSAGES_PER_JOB = 200
MAX_MESSAGES_PER_JOB = 500
MIN_MESSAGES_PER_JOB = 10


@dataclass(frozen=True)
class GmailSyncRequestParams:
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    max_messages: int = DEFAULT_MAX_MESSAGES_PER_JOB
    page_token: Optional[str] = None


def lookback_preset_for_days(days: int) -> str:
    """Map allowed day count back to canonical preset id (defaults to ``90d``)."""
    for preset_id, preset_days in GMAIL_LOOKBACK_PRESETS.items():
        if preset_days == days:
            return preset_id
    return "90d"


def lookback_from_start_params(
    lookback: Any = None,
    lookback_days: Any = None,
) -> tuple[int, str]:
    """
    Resolve lookback for OAuth start from query params.

    Accepts preset id (``1y``) or integer days; invalid values fall back to DEFAULT_LOOKBACK_DAYS.
    """
    raw = lookback_days if lookback_days not in (None, "") else lookback
    days = parse_lookback_days(raw)
    return days, lookback_preset_for_days(days)


def lookback_days_from_oauth_metadata(metadata: Optional[Dict[str, Any]]) -> int:
    """Read lookback_days from oauth_states.metadata; fallback to default."""
    if not isinstance(metadata, dict):
        return DEFAULT_LOOKBACK_DAYS
    raw = metadata.get("lookback_days")
    if raw is not None:
        try:
            days = int(raw)
            if days in ALLOWED_LOOKBACK_DAYS:
                return days
        except (TypeError, ValueError):
            pass
    preset = metadata.get("lookback_preset")
    if isinstance(preset, str) and preset.strip().lower() in GMAIL_LOOKBACK_PRESETS:
        return GMAIL_LOOKBACK_PRESETS[preset.strip().lower()]
    return DEFAULT_LOOKBACK_DAYS


def lookback_presets_for_api() -> List[Dict[str, Any]]:
    labels = {
        "60d": "Last 60 days",
        "90d": "Last 90 days",
        "1y": "Last year",
        "2y": "Last 2 years",
        "5y": "Last 5 years",
    }
    return [
        {"id": pid, "label": labels.get(pid, pid), "days": days}
        for pid, days in GMAIL_LOOKBACK_PRESETS.items()
    ]


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_lookback_days(raw: Any, *, default: int = DEFAULT_LOOKBACK_DAYS) -> int:
    """Accept preset id (e.g. ``1y``), integer days, or numeric string."""
    if raw is None or raw == "":
        return default
    if isinstance(raw, str):
        key = raw.strip().lower()
        if key in GMAIL_LOOKBACK_PRESETS:
            return GMAIL_LOOKBACK_PRESETS[key]
        if key.endswith("d") and key[:-1].isdigit():
            days = int(key[:-1])
            if days in ALLOWED_LOOKBACK_DAYS:
                return days
        if key.isdigit():
            days = int(key)
            if days in ALLOWED_LOOKBACK_DAYS:
                return days
            logger.warning("lookback_days %s not in allowed presets; using default", days)
            return default
    if isinstance(raw, (int, float)):
        days = int(raw)
        if days in ALLOWED_LOOKBACK_DAYS:
            return days
        logger.warning("lookback_days %s not in allowed presets; using default", days)
        return default
    return default


def clamp_max_messages(raw: Any, *, default: int = DEFAULT_MAX_MESSAGES_PER_JOB) -> int:
    n = _coerce_int(raw, default)
    return max(MIN_MESSAGES_PER_JOB, min(MAX_MESSAGES_PER_JOB, n))


def parse_sync_params_from_body(
    body: Optional[Dict[str, Any]],
    *,
    cursor_metadata: Optional[Dict[str, Any]] = None,
) -> GmailSyncRequestParams:
    """
    Build sync params from POST JSON.

    ``continue_sync`` / ``continue``: reuse ``page_token`` and ``lookback_days`` from
    the latest job cursor when the client does not pass a new ``page_token``.
    """
    body = body if isinstance(body, dict) else {}
    continue_sync = bool(body.get("continue_sync") or body.get("continue"))

    lookback = body.get("lookback_days", body.get("lookback"))
    page_token = body.get("page_token")
    if isinstance(page_token, str):
        page_token = page_token.strip() or None
    else:
        page_token = None

    if continue_sync and cursor_metadata:
        if not page_token:
            page_token = cursor_metadata.get("next_page_token") or None
        if lookback is None and cursor_metadata.get("lookback_days") is not None:
            lookback = cursor_metadata.get("lookback_days")

    return GmailSyncRequestParams(
        lookback_days=parse_lookback_days(lookback),
        max_messages=clamp_max_messages(body.get("max_messages")),
        page_token=page_token,
    )


def sync_params_to_job_metadata(params: GmailSyncRequestParams) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "lookback_days": params.lookback_days,
        "max_messages": params.max_messages,
    }
    if params.page_token:
        meta["page_token"] = params.page_token
    return meta


def parse_job_metadata(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def extract_sync_cursor(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Subset exposed to clients via sync status (no page_token)."""
    if not metadata.get("has_more"):
        return {"has_more": False}
    return {
        "has_more": True,
        "lookback_days": metadata.get("lookback_days"),
        "lookback_preset": metadata.get("lookback_preset"),
        "max_messages": metadata.get("max_messages"),
        "last_batch_count": metadata.get("last_batch_count"),
    }
