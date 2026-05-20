#!/usr/bin/env python3
"""Email triage engine: rules-first classification and safety."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.email_triage_taxonomy import (
    category_from_intent,
    normalize_triage_category,
)
from email_automation.email_triage_engine import classify_email_triage


class TestEmailTriageRules(unittest.TestCase):
    def test_newsletter_unsubscribe(self):
        result = classify_email_triage(
            subject="Weekly deals",
            body="Click unsubscribe to stop receiving emails.",
            headers={"list_unsubscribe": True},
        )
        self.assertEqual(result["category"], "newsletter_marketing")
        self.assertEqual(result["cleanup_action"], "archive")
        self.assertGreaterEqual(result["confidence"], 0.85)
        self.assertFalse(result.get("needs_ai"))

    def test_spam_risk_lottery(self):
        result = classify_email_triage(
            subject="Winner",
            body="You won the lottery — send gift card via wire transfer act now.",
        )
        self.assertEqual(result["category"], "spam_risk")
        self.assertEqual(result["cleanup_action"], "spam_candidate")

    def test_system_notification(self):
        result = classify_email_triage(
            subject="Security",
            body="Your password reset link expires in 1 hour.",
        )
        self.assertEqual(result["category"], "personal_non_business")
        self.assertEqual(result["cleanup_action"], "archive")

    def test_possible_lead_quote(self):
        result = classify_email_triage(
            subject="Estimate request",
            body="We are interested in a quote and consultation for your services.",
            sender_email="prospect@fau.edu",
        )
        self.assertEqual(result["category"], "business_lead")
        self.assertGreaterEqual(result["lead_score"], 50)
        self.assertIn(result["cleanup_action"], ("keep", "label"))

    def test_uncertain_needs_ai_flag(self):
        result = classify_email_triage(
            subject="Hello",
            body="Just checking in.",
        )
        self.assertEqual(result["category"], "review_needed")
        self.assertTrue(result.get("needs_ai"))

    def test_fau_style_inquiry(self):
        result = classify_email_triage(
            subject="Florida Atlantic University partnership",
            body="Florida Atlantic University would like pricing for automation.",
            sender_email="contact@fau.edu",
        )
        self.assertIn(
            result["category"],
            ("business_lead", "review_needed", "vendor_partner"),
        )


class TestEmailTriageFromAnalysis(unittest.TestCase):
    def test_enrich_from_mailbox_analysis(self):
        analysis = {
            "intent": "pricing_request",
            "lead_score": 72,
            "business_value_score": 80,
            "urgency_score": 55,
            "confidence_score": 0.91,
            "reasoning_summary": "Pricing inquiry from prospect.",
            "classification_source": "v2_ai",
        }
        result = classify_email_triage(
            subject="Pricing",
            body="Send pricing please",
            analysis=analysis,
        )
        self.assertEqual(result["category"], "business_lead")
        self.assertGreaterEqual(result["lead_score"], 70)
        self.assertEqual(result["classification_source"], "v2_ai")
        self.assertFalse(result.get("needs_ai"))


class TestTriageTaxonomyMapping(unittest.TestCase):
    def test_intent_maps_to_lead(self):
        self.assertEqual(category_from_intent("new_lead"), "business_lead")

    def test_normalize_category(self):
        self.assertEqual(normalize_triage_category("spam"), "spam_risk")


class TestBulkActionSafety(unittest.TestCase):
    def test_destructive_requires_confirmation(self):
        from services.email_triage_service import execute_bulk_action

        with unittest.mock.patch(
            "integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user"
        ) as mock_gmail:
            mock_gmail.return_value = unittest.mock.MagicMock()
            result = execute_bulk_action(
                1,
                action="delete_candidate",
                email_ids=["msg1"],
                confirm_destructive=False,
            )
        self.assertEqual(result.get("code"), "CONFIRMATION_REQUIRED")
        self.assertEqual(result.get("processed"), 0)


if __name__ == "__main__":
    unittest.main()
