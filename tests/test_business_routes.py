#!/usr/bin/env python3
"""
Business Routes Unit Tests
Dedicated tests for routes/business.py core product flows (CRM leads, metrics, etc.)
Uses a minimal app with only the business blueprint to avoid slow full app import.
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


def _make_client():
    from flask import Flask
    from routes.business import business_bp
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(business_bp)
    return test_app.test_client()


class TestBusinessRoutes(unittest.TestCase):
    """Tests for /api/crm/* and business-related endpoints in routes/business.py"""

    def setUp(self):
        self.client = _make_client()

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_leads_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.get("/api/crm/leads")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data.get("success", True))
        self.assertEqual(data.get("code"), "AUTHENTICATION_REQUIRED")

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_leads_success_returns_pagination(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.get_leads_summary.return_value = {
            "success": True,
            "data": {
                "leads": [{"id": 1, "email": "a@b.com", "name": "Lead A"}],
                "total_count": 1,
                "returned_count": 1,
                "limit": 100,
                "offset": 0,
                "has_more": False,
                "analytics": {},
            },
        }
        response = self.client.get("/api/crm/leads")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("leads", data.get("data", {}))
        self.assertIn("pagination", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_create_lead_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post(
            "/api/crm/leads",
            json={"email": "x@y.com", "name": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_create_lead_requires_email_and_name(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post(
            "/api/crm/leads",
            json={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        response2 = self.client.post(
            "/api/crm/leads",
            json={"name": "Only Name"},
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 400)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_create_lead_success(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.create_lead.return_value = {"id": 99, "email": "n@m.com", "name": "New Lead"}
        response = self.client.post(
            "/api/crm/leads",
            json={"email": "n@m.com", "name": "New Lead"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("lead", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_import_leads(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.import_leads.return_value = {"success": True, "data": {"created": 1, "updated": 0, "errors": [], "total": 1}}
        response = self.client.post(
            "/api/crm/leads/import",
            json={"leads": [{"email": "a@b.com", "name": "A"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("created"), 1)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_recalculate_lead_score(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.recalculate_lead_score.return_value = {"success": True, "data": {"lead": {"id": 1, "score": 80}}}
        response = self.client.post(
            "/api/crm/leads/1/score",
            json={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("lead", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_update_lead_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.put(
            "/api/crm/leads/1",
            json={"status": "contacted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_update_lead_not_found(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.get_lead.return_value = None
        response = self.client.put(
            "/api/crm/leads/999",
            json={"status": "contacted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_update_lead_forbidden_wrong_user(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.get_lead.return_value = {"id": 999, "user_id": 2}
        response = self.client.put(
            "/api/crm/leads/999",
            json={"status": "contacted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_pipeline_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.get("/api/crm/pipeline")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_pipeline_success(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.get_pipeline.return_value = {"stages": []}
        response = self.client.get("/api/crm/pipeline")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("pipeline", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_add_lead_activity_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post(
            "/api/crm/leads/1/activities",
            json={"type": "note", "description": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_add_lead_activity_success(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.add_lead_activity.return_value = {"id": 1, "type": "note"}
        response = self.client.post(
            "/api/crm/leads/1/activities",
            json={"type": "note", "description": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("activity", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_lead_activities_requires_auth(self, mock_crm, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.get("/api/crm/leads/1/activities")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    @patch("routes.business.enhanced_crm_service")
    def test_get_lead_activities_success(self, mock_crm, mock_get_user):
        mock_get_user.return_value = 1
        mock_crm.get_lead.return_value = {"id": 1, "user_id": 1}
        mock_crm.get_lead_activities.return_value = []
        response = self.client.get("/api/crm/leads/1/activities")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("activities", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    def test_sync_gmail_requires_auth(self, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post("/api/crm/sync-gmail", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.oauth_token_manager")
    @patch("routes.business.db_optimizer")
    @patch("routes.business.get_current_user_id")
    def test_sync_gmail_requires_oauth(self, mock_get_user, mock_db, mock_oauth):
        mock_get_user.return_value = 1
        mock_db.execute_query.return_value = []
        mock_oauth.get_token_status.return_value = {"success": False}
        response = self.client.post("/api/crm/sync-gmail", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    @patch("threading.Thread")
    @patch("routes.business.enhanced_crm_service")
    @patch("routes.business.oauth_token_manager")
    @patch("routes.business.db_optimizer")
    @patch("routes.business.get_current_user_id")
    def test_sync_gmail_success_with_job_queue(
        self, mock_get_user, mock_db, mock_oauth, mock_crm, mock_thread
    ):
        mock_get_user.return_value = 1
        # gmail_tokens check -> connected
        mock_db.execute_query.side_effect = [
            [{"id": 1}],  # gmail_tokens check
            None,  # user_sync_status insert
            [{"total": 0}],  # synced_emails count
            None,  # user_sync_status completed
        ]
        mock_oauth.get_token_status.return_value = {"success": True}
        mock_crm.sync_gmail_leads.return_value = {"success": True, "data": {"count": 2}}
        mock_thread.return_value.start.return_value = None

        with patch("email_automation.gmail_sync_jobs.GmailSyncJobManager") as mock_mgr:
            mock_mgr.return_value.queue_sync_job.return_value = "job1"
            mock_mgr.return_value.process_sync_job.return_value = {"success": True}
            response = self.client.post("/api/crm/sync-gmail", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("data", {}).get("sync_job_queued"))

    @patch("routes.business.get_current_user_id")
    def test_send_email_requires_auth(self, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post("/api/email/send", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    def test_send_email_missing_fields(self, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post("/api/email/send", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response2 = self.client.post(
            "/api/email/send", json={"to": "a@b.com"}, content_type="application/json"
        )
        self.assertEqual(response2.status_code, 400)

    @patch("routes.business.oauth_token_manager")
    @patch("routes.business.get_current_user_id")
    def test_send_email_requires_gmail_connection(self, mock_get_user, mock_oauth):
        mock_get_user.return_value = 1
        mock_oauth.get_token_status.return_value = {"success": False, "has_token": False}
        response = self.client.post(
            "/api/email/send",
            json={"to": "a@b.com", "subject": "Hi", "body": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.oauth_token_manager")
    @patch("routes.business.get_current_user_id")
    def test_send_email_success(self, mock_get_user, mock_oauth, mock_gmail_client):
        mock_get_user.return_value = 1
        mock_oauth.get_token_status.return_value = {"success": True, "has_token": True}
        gmail_service = MagicMock()
        gmail_service.users().messages().send().execute.return_value = {"id": "m1", "threadId": "t1"}
        mock_gmail_client.get_gmail_service_for_user.return_value = gmail_service
        response = self.client.post(
            "/api/email/send",
            json={"to": "a@b.com", "subject": "Hi", "body": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("message_id"), "m1")

    @patch("routes.business.get_current_user_id")
    def test_archive_email_requires_auth(self, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post("/api/email/archive", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    def test_archive_email_missing_id(self, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post("/api/email/archive", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.get_current_user_id")
    def test_archive_email_success(self, mock_get_user, mock_gmail_client):
        mock_get_user.return_value = 1
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail_client.get_gmail_service_for_user.return_value = gmail_service
        response = self.client.post(
            "/api/email/archive",
            json={"email_id": "m1"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("email_id"), "m1")

    @patch("routes.business.get_current_user_id")
    def test_get_automation_rules_requires_auth(self, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.get("/api/automation/rules")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_get_automation_rules_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.get_automation_rules.return_value = {
            "success": True,
            "data": {"rules": [], "total_count": 0, "count": 0, "has_more": False},
        }
        response = self.client.get("/api/automation/rules")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("rules", data.get("data", {}))

    @patch("routes.business.get_current_user_id")
    def test_create_automation_rule_requires_auth(self, mock_get_user):
        mock_get_user.return_value = None
        response = self.client.post("/api/automation/rules", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("routes.business.get_current_user_id")
    def test_create_automation_rule_missing_fields(self, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post("/api/automation/rules", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_create_automation_rule_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.create_automation_rule.return_value = {"success": True, "data": {"rule_id": 1}}
        mock_engine.get_automation_rules.return_value = {"success": True, "data": {"rules": []}}
        response = self.client.post(
            "/api/automation/rules",
            json={"trigger_type": "email_received", "action_type": "send_email"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.db_optimizer")
    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_update_automation_rule_success(self, mock_get_user, mock_engine, mock_db):
        mock_get_user.return_value = 1
        mock_db.execute_query.return_value = [{"user_id": 1}]
        mock_engine.update_automation_rule.return_value = {"success": True, "data": {"rule_id": 1}}
        response = self.client.put(
            "/api/automation/rules/1",
            json={"status": "inactive"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_get_automation_suggestions_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.get_automation_suggestions.return_value = {"success": True, "data": {"suggestions": []}}
        response = self.client.get("/api/automation/suggestions")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.get_current_user_id")
    def test_execute_automation_requires_rule_ids(self, mock_get_user):
        mock_get_user.return_value = 1
        response = self.client.post("/api/automation/execute", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_execute_automation_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.execute_rules.return_value = []
        response = self.client.post(
            "/api/automation/execute",
            json={"rule_ids": [1]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.automation_safety_manager")
    @patch("routes.business.get_current_user_id")
    def test_automation_kill_switch_success(self, mock_get_user, mock_safety):
        mock_get_user.return_value = 1
        mock_safety.disable_all_automations.return_value = None
        response = self.client.post("/api/automation/kill-switch", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.automation_safety_manager")
    @patch("routes.business.get_current_user_id")
    def test_get_automation_safety_status_success(self, mock_get_user, mock_safety):
        mock_get_user.return_value = 1
        mock_safety.get_safety_status.return_value = {"success": True, "data": {"status": "active"}}
        response = self.client.get("/api/automation/safety-status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_get_automation_logs_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.get_execution_logs.return_value = {"success": True, "data": {"logs": []}}
        response = self.client.get("/api/automation/logs")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_automation_test_requires_rule_id(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        response = self.client.post("/api/automation/test", json={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("routes.business.automation_engine")
    @patch("routes.business.get_current_user_id")
    def test_automation_test_success(self, mock_get_user, mock_engine):
        mock_get_user.return_value = 1
        mock_engine.test_rule.return_value = {"success": True}
        response = self.client.post(
            "/api/automation/test",
            json={"rule_id": 1, "test_data": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))


if __name__ == "__main__":
    unittest.main()
