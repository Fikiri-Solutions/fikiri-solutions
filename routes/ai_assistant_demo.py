#!/usr/bin/env python3
"""
Public AI assistant demo route at /api/test/ai-assistant.

The rest of ``routes.test`` is registered only in development. The marketing SPA
on the custom domain calls this path from production; it must exist on Render
with POST + OPTIONS so browser CORS preflight succeeds.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from core.api_validation import handle_api_errors
from email_automation.ai_assistant import MinimalAIEmailAssistant

logger = logging.getLogger(__name__)

ai_assistant_demo_bp = Blueprint("ai_assistant_demo", __name__, url_prefix="/api")


def create_ai_assistant(api_key=None):
    return MinimalAIEmailAssistant(api_key=api_key)


def create_test_response(
    success: bool,
    data: dict,
    message: str,
    error_code: str = None,
    *,
    correlation_id: str = None,
):
    """Same contract as routes.test /api/test/* helpers (HTTP 200 + body.success)."""
    payload = {
        "success": bool(success),
        "message": message,
        "timestamp": None,
        "data": data,
    }
    if error_code:
        payload["error_code"] = error_code
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return jsonify(payload), 200


@ai_assistant_demo_bp.route("/test/ai-assistant", methods=["POST", "OPTIONS"])
@handle_api_errors
def ai_assistant_demo():
    """Demo AI assistant (intent + reply + contact extraction)."""
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    data = request.get_json() or {}

    content = data.get("content", "Hi, I need help with your services.")
    sender = data.get("sender", "User")
    subject = data.get("subject", "Inquiry")

    prompt = data.get("prompt")
    if prompt:
        lines = prompt.split("\n")
        for i, line in enumerate(lines):
            if line.lower().startswith("from:"):
                sender = line.split(":", 1)[1].strip()
            elif line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif line.strip() and not line.startswith("From:") and not line.startswith("Subject:"):
                content = "\n".join(lines[i:]).strip()
                break

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return create_test_response(
                True,
                {
                    "classification": {
                        "confidence": 0,
                        "intent": "unknown",
                        "suggested_action": "configure_openai",
                        "urgency": "low",
                    },
                    "response": (
                        "OpenAI API key not configured. "
                        "Configure OPENAI_API_KEY to run live assistant checks."
                    ),
                    "contact_info": {},
                    "stats": {
                        "api_key_configured": False,
                        "client_initialized": False,
                        "enabled": False,
                    },
                },
                "OpenAI API key not configured (diagnostics only)",
                error_code="OPENAI_NOT_CONFIGURED",
            )

        assistant = create_ai_assistant(api_key)
        start_time = datetime.now(timezone.utc)

        intent_result = assistant.classify_email_intent(content, subject)
        intent = intent_result.get("intent", "general")

        response = assistant.generate_response(content, sender, subject, intent)

        contact_info = assistant.extract_contact_info(content)

        end_time = datetime.now(timezone.utc)

        operational_success = True
        error_code = None
        redis_client = getattr(assistant, "redis_client", None)
        if redis_client:
            try:
                relevant_ops = {"classify_intent", "generate_response", "extract_contact"}
                records = redis_client.lrange("fikiri:ai:usage", 0, 200) or []
                failures = []
                for record in records:
                    try:
                        parsed = json.loads(record)
                    except Exception:
                        continue
                    op = parsed.get("operation")
                    if op not in relevant_ops:
                        continue
                    ts = parsed.get("timestamp")
                    if not ts:
                        continue
                    try:
                        parsed_ts = datetime.fromisoformat(ts)
                    except Exception:
                        continue
                    if not (start_time <= parsed_ts <= end_time):
                        continue
                    if parsed.get("success") is False:
                        failures.append(op)
                if failures:
                    operational_success = False
                    error_code = "AI_LLM_FAILURE"
            except Exception:
                operational_success = True

        ai_stats = assistant.get_ai_stats()

        return create_test_response(
            operational_success,
            {
                "success": operational_success,
                "classification": intent_result,
                "response": response,
                "contact_info": contact_info,
                "stats": {
                    "api_key_configured": ai_stats.get("enabled", True),
                    "client_initialized": True,
                    "enabled": ai_stats.get("enabled", True),
                },
            },
            (
                "AI assistant test completed"
                if operational_success
                else "AI assistant test failed (LLM call(s) failed)"
            ),
            error_code=error_code,
        )

    except Exception as e:
        logger.error(f"AI assistant test error: {e}")
        return create_test_response(
            False,
            {
                "success": False,
                "classification": {},
                "response": "",
                "contact_info": {},
                "stats": {
                    "api_key_configured": True,
                    "client_initialized": False,
                    "enabled": False,
                },
            },
            "AI assistant test failed",
            error_code="AI_ASSISTANT_TEST_ERROR",
        )
