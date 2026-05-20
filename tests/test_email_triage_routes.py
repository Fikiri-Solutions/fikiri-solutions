#!/usr/bin/env python3
"""Inbox Command Center API routes."""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.email_triage_store import ensure_email_classifications_table, upsert_classification


class TestEmailTriageRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        ensure_email_classifications_table()

    def test_list_requires_auth(self):
        response = self.client.get("/api/email/triage")
        self.assertEqual(response.status_code, 401)

    @patch("routes.email_triage.get_current_user_id", return_value=1)
    def test_list_by_category(self, _mock_user):
        upsert_classification(
            1,
            external_id="msg-fau-1",
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": 80,
                "business_relevance_score": 85,
                "urgency_score": 40,
                "cleanup_action": "keep",
                "confidence": 0.9,
                "reason": "FAU pricing inquiry",
                "suggested_labels": ["Fikiri/business_lead"],
            },
        )
        response = self.client.get("/api/email/triage?category=business_lead&limit=10")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        emails = data.get("data", {}).get("emails", [])
        self.assertGreaterEqual(len(emails), 1)
        self.assertEqual(emails[0].get("category"), "business_lead")

    @patch("routes.email_triage.get_current_user_id", return_value=1)
    def test_bulk_delete_requires_confirm(self, _mock_user):
        response = self.client.post(
            "/api/email/triage/bulk-action",
            json={"action": "delete_candidate", "email_ids": ["x1"]},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get("code"), "CONFIRMATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
