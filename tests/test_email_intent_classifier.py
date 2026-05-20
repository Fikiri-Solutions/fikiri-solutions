#!/usr/bin/env python3
"""Tests for business email intent taxonomy and classifier."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.email_intent_taxonomy import normalize_intent, recommended_action_type
from email_automation.email_intent_classifier import (
    build_rule_hints,
    classify_with_fallback,
    normalize_business_analysis,
)


class TestEmailIntentTaxonomy(unittest.TestCase):
    def test_normalize_legacy_lead(self):
        self.assertEqual(normalize_intent("lead_inquiry"), "new_lead")

    def test_normalize_partnership_alias(self):
        self.assertEqual(normalize_intent("partnership"), "partnership_request")

    def test_archive_spam_intent(self):
        self.assertEqual(recommended_action_type("spam_or_low_value"), "archive")


class TestEmailIntentClassifier(unittest.TestCase):
    def test_service_inquiry_hint(self):
        hints = build_rule_hints(
            subject="Services",
            body="Do you offer automation for small businesses?",
            client_config={"high_value_keywords": ["automation"]},
        )
        self.assertIn("service_inquiry", hints["suggested_intents"])

    def test_pricing_request_fallback(self):
        result = classify_with_fallback(
            subject="Pricing",
            body="Please send a quote and monthly cost breakdown.",
        )
        self.assertEqual(result["intent"], "pricing_request")
        self.assertGreaterEqual(result["lead_score"], 40)

    def test_job_inquiry_fallback(self):
        result = classify_with_fallback(
            subject="Job application",
            body="I'm interested in a career opportunity and attached my resume.",
        )
        self.assertEqual(result["intent"], "job_or_career_inquiry")

    def test_partnership_fallback(self):
        result = classify_with_fallback(
            subject="Partnership",
            body="We would like to explore a partnership collaboration.",
        )
        self.assertEqual(result["intent"], "partnership_request")

    def test_support_fallback(self):
        result = classify_with_fallback(
            subject="Help",
            body="The app is broken and not working for our team.",
        )
        self.assertEqual(result["intent"], "existing_customer_support")

    def test_complaint_requires_review(self):
        result = classify_with_fallback(
            subject="Complaint",
            body="I'm disappointed and need escalation immediately.",
        )
        self.assertEqual(result["intent"], "complaint_or_escalation")
        self.assertTrue(result["needs_human_review"])

    def test_newsletter_low_value(self):
        result = classify_with_fallback(
            subject="Newsletter",
            body="Unsubscribe from our weekly promo sale newsletter.",
        )
        self.assertIn(result["intent"], {"newsletter_or_marketing", "spam_or_low_value"})

    def test_normalize_ai_payload_with_secondary(self):
        raw = {
            "intent": "service_inquiry",
            "secondary_intents": ["pricing_request"],
            "confidence": 0.88,
            "urgency": "high",
            "business_value": "high",
            "summary": "Wants pricing for services",
            "crm_updates": {"stage": "qualified", "tags": [], "follow_up_needed": True, "priority": "high"},
            "suggested_reply": "Thanks for reaching out.",
            "should_auto_send": False,
            "needs_human_review": False,
            "reason_for_recommendation": "Clear service ask",
        }
        out = normalize_business_analysis(raw)
        self.assertEqual(out["intent"], "service_inquiry")
        self.assertIn("pricing_request", out["secondary_intents"])
        self.assertEqual(out["legacy_intent"], "lead_inquiry")

    def test_custom_high_value_keyword(self):
        cfg = {"high_value_keywords": ["acquisition"]}
        hints = build_rule_hints(
            subject="Deal",
            body="We are exploring an acquisition opportunity.",
            client_config=cfg,
        )
        self.assertTrue(hints["suggested_intents"])
        result = classify_with_fallback(
            subject="Deal",
            body="We are exploring an acquisition opportunity.",
            user_id=None,
        )
        self.assertIn(result["intent"], {"sales_opportunity", "partnership_request", "new_lead"})


if __name__ == "__main__":
    unittest.main()
