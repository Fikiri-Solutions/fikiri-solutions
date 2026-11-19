"""
Lead-form notifications for public /contact, /intake, site-chat handoffs, and webhook leads.

Email transport stays in ``core.contact_api``. This module owns Slack delivery so
marketing leads are never subject to monitoring alert cooldown/dedup.

Preferred flow (callers):
  validate → persist CRM/DB → enqueue Slack (async) → email (independent)

``send_lead_slack_notification`` returning True means the alert was *accepted*
for delivery (configured + not deduped). With ``blocking=False`` (default) that
is not proof Slack HTTP succeeded — check logs for ``Lead Slack notification sent``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_dedupe_lock = threading.Lock()
_recent_dedupe: Dict[str, float] = {}


def lead_slack_webhook_url() -> str:
    """Prefer a dedicated leads webhook; fall back to the shared ops webhook."""
    return (
        os.getenv("LEAD_SLACK_WEBHOOK_URL")
        or os.getenv("SLACK_WEBHOOK_URL")
        or ""
    ).strip()


def uses_dedicated_lead_webhook() -> bool:
    return bool((os.getenv("LEAD_SLACK_WEBHOOK_URL") or "").strip())


def _dedupe_ttl_seconds() -> float:
    raw = (os.getenv("FIKIRI_LEAD_SLACK_DEDUPE_SECONDS") or "900").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 900.0


def _should_send_for_dedupe_key(dedupe_key: Optional[str]) -> bool:
    """Return False if this key was already accepted within the TTL window."""
    if not dedupe_key:
        return True
    key = dedupe_key.strip()[:240]
    if not key:
        return True
    ttl = _dedupe_ttl_seconds()
    if ttl <= 0:
        return True
    now = time.time()
    with _dedupe_lock:
        last = _recent_dedupe.get(key)
        if last is not None and (now - last) < ttl:
            return False
        _recent_dedupe[key] = now
        if len(_recent_dedupe) > 2000:
            cutoff = now - ttl
            stale = [k for k, v in _recent_dedupe.items() if v < cutoff]
            for k in stale:
                _recent_dedupe.pop(k, None)
        return True


def reset_lead_slack_dedupe_cache() -> None:
    """Test helper — clear in-process dedupe state."""
    with _dedupe_lock:
        _recent_dedupe.clear()


def lead_dedupe_key(*parts: Any) -> str:
    """Stable short key from opaque parts (emails hashed; no raw PII in the key)."""
    chunks: List[str] = []
    for part in parts:
        text = str(part or "").strip().lower()
        if not text:
            continue
        if "@" in text and "." in text.split("@")[-1]:
            text = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        chunks.append(text[:80])
    raw = "|".join(chunks)
    if len(raw) <= 120:
        return raw
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def send_lead_slack_notification(
    *,
    title: str,
    text: str,
    fields: Optional[List[Dict[str, Any]]] = None,
    dedupe_key: Optional[str] = None,
    blocking: bool = False,
) -> bool:
    """
    Post a lead alert to Slack Incoming Webhooks.

    Returns True when delivery is accepted (webhook configured and not deduped).
    When ``blocking=False`` (default), posts on a daemon thread so the visitor
    request is not delayed by Slack latency. Never raises.

    Does **not** use monitoring cooldown (every genuine lead must notify; retries
    are suppressed only via ``dedupe_key``).
    """
    webhook = lead_slack_webhook_url()
    if not webhook:
        logger.warning(
            "Lead Slack webhook not configured (LEAD_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL)"
        )
        return False

    if not _should_send_for_dedupe_key(dedupe_key):
        logger.info("Lead Slack notification suppressed by dedupe key")
        return False

    payload = _build_payload(title=title, text=text, fields=fields)

    if blocking or _is_test_mode():
        return _post_slack(webhook, payload, title)

    threading.Thread(
        target=_post_slack,
        args=(webhook, payload, title),
        daemon=True,
        name="lead-slack-alert",
    ).start()
    return True


def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def _build_payload(
    *,
    title: str,
    text: str,
    fields: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    attachment: Dict[str, Any] = {
        "color": "#FF6B35",
        "title": title[:200],
        "text": (text or "")[:1500],
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
            if f.get("title") and f.get("value") is not None and str(f.get("value")).strip() != ""
        ][:12]

    payload: Dict[str, Any] = {
        "text": title[:200],
        "attachments": [attachment],
    }
    # Incoming webhooks are bound to a channel. Only set channel override when
    # falling back to the shared ops webhook (legacy). Prefer LEAD_SLACK_WEBHOOK_URL
    # pointed at #leads so routing does not depend on payload overrides.
    if not uses_dedicated_lead_webhook():
        channel = (os.getenv("LEAD_SLACK_CHANNEL") or os.getenv("SLACK_CHANNEL") or "").strip()
        if channel:
            payload["channel"] = channel
    return payload


def _post_slack(webhook: str, payload: Dict[str, Any], title: str) -> bool:
    try:
        import requests

        response = requests.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Lead Slack notification sent: %s", title[:120])
        return True
    except Exception as e:
        logger.error("Lead Slack notification failed: %s", e)
        return False
