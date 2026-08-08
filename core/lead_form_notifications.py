"""
Lead-form notifications for public /contact and /intake.

Email transport stays in ``core.contact_api``. This module owns Slack delivery so
marketing leads are never subject to monitoring alert cooldown/dedup.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def lead_slack_webhook_url() -> str:
    """Prefer a dedicated leads webhook; fall back to the shared ops webhook."""
    return (
        os.getenv("LEAD_SLACK_WEBHOOK_URL")
        or os.getenv("SLACK_WEBHOOK_URL")
        or ""
    ).strip()


def send_lead_slack_notification(
    *,
    title: str,
    text: str,
    fields: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """
    Post a lead alert to Slack Incoming Webhooks.

    Returns True on HTTP success. Never raises — callers must still persist/email.
    Does **not** use monitoring cooldown (every real lead must notify).
    """
    webhook = lead_slack_webhook_url()
    if not webhook:
        logger.warning("Lead Slack webhook not configured (LEAD_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL)")
        return False

    channel = (os.getenv("LEAD_SLACK_CHANNEL") or os.getenv("SLACK_CHANNEL") or "").strip()
    attachment: Dict[str, Any] = {
        "color": "#FF6B35",
        "title": title,
        "text": text[:3500],
        "footer": "Fikiri lead intake",
    }
    if fields:
        attachment["fields"] = [
            {
                "title": str(f.get("title") or "")[:80],
                "value": str(f.get("value") or "")[:500],
                "short": bool(f.get("short", True)),
            }
            for f in fields
            if f.get("title") and f.get("value")
        ][:20]

    payload: Dict[str, Any] = {
        "text": title,
        "attachments": [attachment],
    }
    if channel:
        payload["channel"] = channel

    try:
        import requests

        response = requests.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Lead Slack notification sent: %s", title[:120])
        return True
    except Exception as e:
        logger.error("Lead Slack notification failed: %s", e)
        return False
