"""
Authenticated service diagnostics for the Services dashboard.

Uses the same contracts as ``routes/test.py`` (HTTP 200 + top-level ``success``)
so production and development behave consistently.
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime

from core.ml_scoring import MinimalMLScoring
from crm.service import enhanced_crm_service
from email_automation.parser import MinimalEmailParser
from routes.test import create_test_response

logger = logging.getLogger(__name__)

_ALLOWED = frozenset({"ai-assistant", "email-parser", "crm", "ml-scoring"})


def run_service_test(service_id: str, user_id: int, payload: dict | None = None):
    sid = (service_id or "").strip()
    if sid not in _ALLOWED:
        return create_test_response(
            False,
            {},
            f"Unknown service: {service_id}",
            error_code="UNKNOWN_SERVICE",
        )

    if not user_id:
        return create_test_response(
            False,
            {},
            "Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
        )

    payload = payload or {}
    try:
        if sid == "ai-assistant":
            return _test_ai_assistant(payload)
        if sid == "email-parser":
            return _test_email_parser(payload)
        if sid == "crm":
            return _test_crm(user_id, payload)
        if sid == "ml-scoring":
            return _test_ml_scoring()
    except Exception as exc:
        logger.exception("service test failed service_id=%s user_id=%s", sid, user_id)
        return create_test_response(
            False,
            {"error": str(exc)},
            f"{sid} test failed",
            error_code="SERVICE_TEST_ERROR",
        )


def _test_ai_assistant(payload: dict):
    from email_automation.ai_assistant import MinimalAIEmailAssistant

    content = payload.get("content", "Hi, I need help with your services.")
    sender = payload.get("sender", "Test User")
    subject = payload.get("subject", "Test Subject")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return create_test_response(
            True,
            {
                "classification": {
                    "intent": "unknown",
                    "confidence": 0,
                    "suggested_action": "configure_openai",
                },
                "response": (
                    "OpenAI API key not configured. "
                    "Configure OPENAI_API_KEY to run live assistant checks."
                ),
                "contact_info": {},
                "stats": {"api_key_configured": False},
            },
            "OpenAI API key not configured (diagnostics only)",
            error_code="OPENAI_NOT_CONFIGURED",
        )

    assistant = MinimalAIEmailAssistant(api_key=api_key)
    analysis = assistant.analyze_incoming_email(
        sender_email=sender,
        sender_name=sender,
        subject=subject,
        body=content,
        classification_source="legacy_wrapper",
    )
    intent_result = analysis
    intent = analysis.get("intent", "general")
    response = assistant.generate_response(
        content, sender, subject, intent, analysis=analysis
    )
    contact_info = assistant.extract_contact_info(content)
    return create_test_response(
        True,
        {
            "classification": intent_result,
            "response": response,
            "contact_info": contact_info,
        },
        "AI assistant test completed",
    )


def _test_email_parser(payload: dict):
    default_email = """Subject: Test Email - Inquiry about Services

Hi there,

I'm interested in learning more about your services.

Best regards,
Test User
test@example.com"""
    email_content = payload.get("email_content", default_email)
    parser = MinimalEmailParser()
    mock_message = {
        "id": "test_message_123",
        "threadId": "test_thread_123",
        "snippet": email_content[:100] if len(email_content) > 100 else email_content,
        "labelIds": ["UNREAD"],
        "payload": {
            "headers": [
                {
                    "name": "Subject",
                    "value": email_content.split("\n")[0].replace("Subject:", "").strip()
                    if "Subject:" in email_content
                    else "Test Email",
                },
                {"name": "From", "value": "test@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": datetime.now().isoformat()},
            ],
            "body": {
                "data": base64.urlsafe_b64encode(email_content.encode("utf-8")).decode("utf-8")
            },
            "mimeType": "text/plain",
        },
    }
    parsed_result = parser.parse_message(mock_message)
    return create_test_response(
        True,
        {"original_content": email_content, "parsed_result": parsed_result},
        "Email parser test completed",
    )


def _test_crm(user_id: int, payload: dict):
    test_action = payload.get("action", "get_leads")
    if test_action == "get_leads":
        result = enhanced_crm_service.get_leads_summary(user_id)
        if not result.get("success"):
            return create_test_response(
                False,
                {"action": test_action},
                result.get("error", "Failed to retrieve leads"),
                error_code="CRM_GET_LEADS_ERROR",
            )
        leads = result.get("data", {}).get("leads", [])
        return create_test_response(
            True,
            {
                "action": test_action,
                "leads_count": len(leads) if leads else 0,
                "leads": leads[:5] if leads else [],
                "analytics": result.get("data", {}).get("analytics", {}),
            },
            "CRM test completed",
        )
    return create_test_response(
        False,
        {},
        "Invalid test action. Use 'get_leads'",
        error_code="INVALID_TEST_ACTION",
    )


def _test_ml_scoring():
    scorer = MinimalMLScoring()
    scoring_log_exists = False
    if getattr(scorer, "db_optimizer", None):
        try:
            scoring_log_exists = bool(scorer.db_optimizer.table_exists("ml_scoring_log"))
        except Exception:
            scoring_log_exists = False

    high_value_email = {
        "subject": "URGENT: Need Premium Services - Budget $50,000",
        "content": "Hi, I need your premium services immediately.",
        "timestamp": datetime.now().isoformat(),
    }
    high_value_lead = {
        "email": "ceo@enterprise-corp.com",
        "name": "John Smith",
        "company": "Enterprise Corp",
        "contact_count": 3,
    }
    low_value_email = {
        "subject": "Hello",
        "content": "Hi there, just saying hello.",
        "timestamp": datetime.now().isoformat(),
    }
    low_value_lead = {
        "email": "test@gmail.com",
        "name": "Test User",
        "company": None,
        "contact_count": 0,
    }

    high_score_result = scorer.calculate_lead_score(high_value_email, high_value_lead)
    low_score_result = scorer.calculate_lead_score(low_value_email, low_value_lead)

    validation_results = {
        "service_initialized": True,
        "high_value_score_valid": 0 <= high_score_result.get("total_score", 0) <= 100,
        "low_value_score_valid": 0 <= low_score_result.get("total_score", 0) <= 100,
        "score_differentiation": high_score_result.get("total_score", 0)
        > low_score_result.get("total_score", 0),
        "ml_scoring_log_table_exists": scoring_log_exists,
    }
    passed_checks = sum(1 for v in validation_results.values() if v)
    total_checks = len(validation_results)
    pass_rate = (passed_checks / total_checks) * 100 if total_checks else 0
    test_passed = pass_rate >= 80

    return create_test_response(
        test_passed,
        {
            "test_status": "PASSED" if test_passed else "FAILED",
            "pass_rate": f"{pass_rate:.1f}%",
            "validation_results": validation_results,
            "high_value_lead": high_score_result,
            "low_value_lead": low_score_result,
        },
        "ML scoring test completed" if test_passed else "ML scoring test failed",
        error_code=None if test_passed else "ML_SCORING_TEST_FAILED",
    )
