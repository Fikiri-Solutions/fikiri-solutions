"""Webhook automation action handler."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict


class WebhookActionHandler:
    """Owns TRIGGER_WEBHOOK execution details for automation rules."""

    def __init__(self, logger):
        self.logger = logger

    def execute_trigger_webhook(
        self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Trigger a webhook via HTTP POST with timeout, retries, and optional signature."""
        try:
            webhook_url = (parameters.get("webhook_url") or parameters.get("sheet_url") or "").strip()
            if not webhook_url:
                return {"success": False, "error": "Missing webhook_url", "error_code": "MISSING_URL"}
            payload = dict(parameters.get("payload", {}))
            payload["user_id"] = user_id
            payload["timestamp"] = datetime.now().isoformat()
            payload.setdefault("event", trigger_data.get("event_type", "automation_triggered"))
            for k, v in trigger_data.items():
                if k not in payload:
                    payload[k] = v

            secret = parameters.get("webhook_secret")
            body_bytes = json.dumps(payload, sort_keys=True).encode()
            headers = {"Content-Type": "application/json"}
            if secret:
                import hmac
                import hashlib

                sig = hmac.new(
                    secret.encode() if isinstance(secret, str) else secret,
                    body_bytes,
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Fikiri-Signature"] = f"sha256={sig}"

            timeout_sec = min(30, max(5, int(parameters.get("timeout_seconds", 10))))
            max_attempts = max(1, min(3, int(parameters.get("max_retries", 2)) + 1))

            last_error = None
            for attempt in range(max_attempts):
                try:
                    import requests

                    response = requests.post(
                        webhook_url,
                        data=body_bytes,
                        headers=headers,
                        timeout=timeout_sec,
                    )
                    response.raise_for_status()
                    self.logger.info(
                        "Webhook delivered to %s status=%s",
                        webhook_url[:80],
                        response.status_code,
                    )
                    return {
                        "success": True,
                        "data": {"webhook_url": webhook_url, "status_code": response.status_code},
                    }
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        import time

                        time.sleep(0.5 * (2 ** attempt))
            self.logger.warning(
                "Webhook failed after %s attempts to %s: %s",
                max_attempts,
                webhook_url[:80],
                last_error,
            )
            return {
                "success": False,
                "error": str(last_error),
                "error_code": "WEBHOOK_DELIVERY_FAILED",
            }
        except Exception as e:
            self.logger.error("Error triggering webhook: %s", e)
            return {"success": False, "error": str(e), "error_code": "WEBHOOK_ERROR"}
