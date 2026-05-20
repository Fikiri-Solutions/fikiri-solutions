#!/usr/bin/env python3
"""Live Mail local classification/workflow overlay."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database_optimization import db_optimizer
from core.email_triage_store import ensure_email_classifications_table, upsert_classification
from email_automation.email_workflow_state import (
    ensure_email_workflow_state_table,
    mark_action_applied,
    mark_classified,
)
from email_automation.live_mail_overlay import enrich_live_mail_messages


class TestLiveMailOverlayHelper(unittest.TestCase):
    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = 1

    def tearDown(self):
        for tbl in ("email_workflow_state", "email_classifications"):
            db_optimizer.execute_query(
                f"DELETE FROM {tbl} WHERE user_id = ?",
                (self.user_id,),
                fetch=False,
            )

    def test_enrich_adds_classification_fields(self):
        ext = "overlay-msg-001"
        upsert_classification(
            self.user_id,
            external_id=ext,
            triage={
                "category": "business_lead",
                "lead_score": 72,
                "business_relevance_score": 70,
                "urgency_score": 45,
                "cleanup_action": "keep",
                "confidence": 0.88,
                "reason": "test",
            },
        )
        emails = [{"id": ext, "subject": "Hi"}]
        enrich_live_mail_messages(self.user_id, emails)
        self.assertEqual(emails[0]["classification_category"], "business_lead")
        self.assertEqual(emails[0]["lead_score"], 72)
        self.assertAlmostEqual(float(emails[0]["classification_confidence"]), 0.88)

    def test_enrich_archived_workflow_handled_flags(self):
        ext = "overlay-msg-002"
        mark_classified(self.user_id, ext, provider="gmail")
        mark_action_applied(self.user_id, ext, action="archive", provider="gmail")
        emails = [{"id": ext}]
        enrich_live_mail_messages(self.user_id, emails)
        self.assertEqual(emails[0]["workflow_status"], "archived")
        self.assertTrue(emails[0]["is_locally_archived"])
        self.assertTrue(emails[0]["is_locally_handled"])

    def test_unsynced_message_unchanged(self):
        emails = [{"id": "never-synced-xyz", "subject": "x"}]
        original_keys = set(emails[0].keys())
        enrich_live_mail_messages(self.user_id, emails)
        self.assertEqual(set(emails[0].keys()), original_keys)

    def test_empty_workflow_table_safe(self):
        emails = [{"id": "no-state-1"}]
        with patch(
            "email_automation.live_mail_overlay.fetch_workflow_by_external_ids",
            return_value={},
        ):
            with patch(
                "email_automation.live_mail_overlay.fetch_classifications_by_external_ids",
                return_value={},
            ):
                enrich_live_mail_messages(self.user_id, emails)
        self.assertNotIn("workflow_status", emails[0])


class TestLiveMailOverlayRoute(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = 1
        self.ext_id = "overlay-route-001"

    def tearDown(self):
        for tbl in ("email_workflow_state", "email_classifications"):
            db_optimizer.execute_query(
                f"DELETE FROM {tbl} WHERE user_id = ?",
                (self.user_id,),
                fetch=False,
            )

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.db_optimizer")
    @patch("routes.business.get_current_user_id")
    def test_gmail_live_message_gets_overlay(
        self, mock_get_user, mock_db, mock_gmail
    ):
        mock_get_user.return_value = self.user_id
        mock_db.execute_query.return_value = []

        upsert_classification(
            self.user_id,
            external_id=self.ext_id,
            triage={
                "category": "action_needed",
                "lead_score": 30,
                "business_relevance_score": 40,
                "urgency_score": 55,
                "cleanup_action": "keep",
                "confidence": 0.75,
                "reason": "route test",
            },
        )
        mark_classified(self.user_id, self.ext_id, provider="gmail")

        mock_service = MagicMock()
        mock_gmail.get_gmail_service_for_user.return_value = mock_service
        list_execute = mock_service.users.return_value.messages.return_value.list.return_value.execute
        list_execute.return_value = {"messages": [{"id": self.ext_id}]}
        get_execute = mock_service.users.return_value.messages.return_value.get.return_value.execute
        get_execute.return_value = {
            "id": self.ext_id,
            "labelIds": ["INBOX"],
            "snippet": "Body",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "From", "value": "a@b.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2025 12:00:00 +0000"},
                ]
            },
        }

        response = self.client.get("/api/email/messages?use_synced=false")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        emails = data.get("data", {}).get("emails", [])
        self.assertEqual(len(emails), 1)
        row = emails[0]
        self.assertEqual(row.get("id"), self.ext_id)
        self.assertEqual(row.get("classification_category"), "action_needed")
        self.assertIn("subject", row)
        self.assertNotIn("local_state", row)

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.get_current_user_id")
    def test_gmail_message_without_overlay_backward_compatible(
        self, mock_get_user, mock_gmail
    ):
        mock_get_user.return_value = self.user_id
        mock_service = MagicMock()
        mock_gmail.get_gmail_service_for_user.return_value = mock_service
        ext = "overlay-route-none"
        list_execute = mock_service.users.return_value.messages.return_value.list.return_value.execute
        list_execute.return_value = {"messages": [{"id": ext}]}
        get_execute = mock_service.users.return_value.messages.return_value.get.return_value.execute
        get_execute.return_value = {
            "id": ext,
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "x",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "No overlay"},
                    {"name": "From", "value": "z@y.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2025 12:00:00 +0000"},
                ]
            },
        }

        with patch("routes.business.db_optimizer") as mock_db:
            mock_db.execute_query.return_value = []
            response = self.client.get("/api/email/messages?use_synced=false")

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        row = data["data"]["emails"][0]
        self.assertEqual(row["id"], ext)
        self.assertNotIn("classification_category", row)
        self.assertNotIn("workflow_status", row)


if __name__ == "__main__":
    unittest.main()
