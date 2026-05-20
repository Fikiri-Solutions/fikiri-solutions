"""
Read per-user service preferences from ``user_services``.

Defaults are permissive (enabled) when no row exists so existing accounts
keep current behavior until they save preferences on the Services page.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_SERVICE_ID_ALIASES = {
    "ai_email_assistant": "ai-assistant",
    "email_parser": "email-parser",
    "ml_lead_scoring": "ml-scoring",
}


def _normalize_service_id(service_id: str) -> str:
    sid = (service_id or "").strip()
    return _SERVICE_ID_ALIASES.get(sid, sid)


def _parse_settings(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.debug("user_services: invalid settings JSON")
    return {}


def get_user_service_row(user_id: int, service_id: str) -> Optional[Dict[str, Any]]:
    """Return one ``user_services`` row or ``None``."""
    sid = _normalize_service_id(service_id)
    if not user_id or not sid:
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT service_id, service_name, enabled, status, settings
        FROM user_services
        WHERE user_id = ? AND service_id = ?
        """,
        (user_id, sid),
    )
    if not rows:
        return None
    row = dict(rows[0])
    row["settings"] = _parse_settings(row.get("settings"))
    row["enabled"] = bool(row.get("enabled"))
    return row


def is_service_enabled(user_id: int, service_id: str, *, default: bool = True) -> bool:
    row = get_user_service_row(user_id, service_id)
    if row is None:
        return default
    return bool(row.get("enabled"))


def get_service_settings(user_id: int, service_id: str) -> Dict[str, Any]:
    row = get_user_service_row(user_id, service_id)
    if not row or not row.get("enabled"):
        return {}
    return row.get("settings") or {}


def is_crm_inbound_capture_enabled(user_id: int) -> bool:
    if not is_service_enabled(user_id, "crm", default=True):
        return False
    settings = get_service_settings(user_id, "crm")
    if "autoLeadCreation" in settings:
        return bool(settings.get("autoLeadCreation"))
    return True


def should_run_mailbox_ai(user_id: int) -> bool:
    return is_service_enabled(user_id, "ai-assistant", default=True)
