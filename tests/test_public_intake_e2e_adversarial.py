"""
Adversarial + client-path E2E for public consultation intake.

Covers typical failures and less-obvious workflow bugs:
- validation / honeypot / content-type
- short-form field capture & CRM routing
- unicode / XSS / oversized payloads
- email normalization & CRM merge
- duplicate correlation retries (no double-notify when CRM owner set)
- contact form remains independent
- rate-limit envelope shape
"""

from __future__ import annotations

import json
import os
import unittest
import uuid
from unittest.mock import patch

from core.lead_form_notifications import reset_lead_slack_dedupe_cache


def _payload(**overrides):
    base = {
        "contact_name": "Casey Client",
        "email": f"casey.{uuid.uuid4().hex[:8]}@example.test",
        "main_pain": "Leads stall after the first reply.",
        "service_interests": ["website_design_development"],
        "service_detail": "redesign",
        "preferred_next_step": "follow_up",
        "source": "e2e_adversarial",
        "correlation_id": f"e2e-{uuid.uuid4()}",
    }
    base.update(overrides)
    return base


class PublicIntakeE2EAdversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("FLASK_ENV", "development")
        os.environ["FIKIRI_INTAKE_LEAD_OWNER_USER_ID"] = "1"
        from app import app

        cls.app = app
        cls.client = app.test_client()

    def setUp(self):
        reset_lead_slack_dedupe_cache()

    def _post(self, payload, headers=None):
        return self.client.post(
            "/api/intake",
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers or {},
        )

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_happy_path_routes_interests_to_crm_and_backup(self, mock_email, mock_slack):
        from core.database_optimization import db_optimizer

        email = f"happy.{uuid.uuid4().hex[:8]}@example.test"
        payload = _payload(email=email, business_name="Happy Path Co", industry="Retail / ecommerce")
        res = self._post(payload)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        body = res.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["preferred_next_step"], "follow_up")
        self.assertTrue(body.get("crm_ok"))

        lead_rows = db_optimizer.execute_query(
            """
            SELECT name, company, metadata FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        self.assertTrue(lead_rows)
        meta = json.loads(lead_rows[0]["metadata"] or "{}")
        self.assertEqual(meta.get("intake_version"), 2)
        self.assertIn("website_design_development", meta.get("lead_interests") or [])
        self.assertEqual(meta.get("service_detail"), "redesign")
        self.assertEqual(meta.get("preferred_next_step"), "follow_up")
        self.assertEqual(lead_rows[0]["company"], "Happy Path Co")

        backup = db_optimizer.execute_query(
            """
            SELECT form_type, payload_json FROM customer_contact_submissions
            WHERE lower(email) = lower(?) AND form_type = 'consultation_intake'
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        self.assertTrue(backup)
        pj = json.loads(backup[0]["payload_json"] or "{}")
        self.assertEqual(pj.get("preferred_next_step"), "follow_up")
        mock_email.assert_called_once()
        mock_slack.assert_called_once()

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_priority_vetting_recomputed_server_side(self, mock_email, mock_slack):
        from core.database_optimization import db_optimizer

        email = f"priority.{uuid.uuid4().hex[:8]}@example.test"
        payload = _payload(
            email=email,
            service_detail=["redesign", "ecommerce"],
            project_clarity="know_exactly",
            timeline_readiness="ready_now",
            budget_readiness="budget_ready",
            lead_priority_band="nurture",
        )
        res = self._post(payload)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        lead_rows = db_optimizer.execute_query(
            """
            SELECT metadata FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        self.assertTrue(lead_rows)
        meta = json.loads(lead_rows[0]["metadata"] or "{}")
        self.assertEqual(meta.get("lead_priority_band"), "priority")
        self.assertEqual(meta.get("budget_readiness"), "budget_ready")
        self.assertIn("redesign", meta.get("service_detail") or "")
        self.assertIn("ecommerce", meta.get("service_detail") or "")
        slack_kwargs = mock_slack.call_args.kwargs
        self.assertTrue(str(slack_kwargs.get("title") or "").startswith("Priority intake"))
        mock_email.assert_called_once()
        mock_slack.assert_called_once()

    def test_rejects_non_json_content_type(self):
        res = self.client.post("/api/intake", data="contact_name=x", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    def test_missing_contact_name_and_bad_email(self):
        res = self._post(_payload(contact_name="", email="not-an-email"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("Contact name", res.get_json().get("error", ""))

        res2 = self._post(_payload(email="still-bad"))
        self.assertEqual(res2.status_code, 400)
        self.assertIn("email", res2.get_json().get("error", "").lower())

    @patch("core.lead_form_notifications.send_lead_slack_notification")
    @patch("core.contact_api._send_contact_email")
    def test_honeypot_pretends_success_without_side_effects(self, mock_email, mock_slack):
        res = self._post(_payload(leave_blank="http://spam.example"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))
        mock_email.assert_not_called()
        mock_slack.assert_not_called()

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_optional_business_name_not_fabricated(self, *_):
        from core.database_optimization import db_optimizer

        email = f"solo.{uuid.uuid4().hex[:8]}@example.test"
        res = self._post(_payload(email=email, business_name=""))
        self.assertEqual(res.status_code, 200)
        lead = db_optimizer.execute_query(
            """
            SELECT company FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            LIMIT 1
            """,
            (email,),
        )
        self.assertTrue(lead)
        company = lead[0]["company"]
        self.assertTrue(company is None or company == "")

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_unicode_and_script_payload_persisted_escaped_in_email(self, mock_email, _slack):
        email = f"unicode.{uuid.uuid4().hex[:8]}@example.test"
        pain = "Café leads — 日本語 <script>alert(1)</script> 🚀"
        res = self._post(
            _payload(
                email=email,
                contact_name="Amélie <b>Test</b>",
                main_pain=pain,
                service_interests=["custom_software_systems", "ai_business_automation"],
                service_detail="dashboards",
                preferred_next_step="book",
            )
        )
        self.assertEqual(res.status_code, 200)
        html_body = mock_email.call_args[0][2]
        self.assertIn("Amélie", html_body)
        self.assertIn("&lt;script&gt;", html_body)
        self.assertNotIn("<script>alert(1)</script>", html_body)
        self.assertIn("custom_software_systems", html_body)

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_oversized_fields_truncated_not_500(self, *_):
        email = f"big.{uuid.uuid4().hex[:8]}@example.test"
        res = self._post(
            _payload(
                email=email,
                main_pain="x" * 5000,
                service_interests=["scheduling_operations"] * 20,
                service_detail="y" * 1000,
            )
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_email_case_merge_updates_same_lead(self, mock_email, mock_slack):
        from core.database_optimization import db_optimizer

        local = uuid.uuid4().hex[:8]
        email_lower = f"merge.{local}@example.test"
        email_upper = f"MERGE.{local}@EXAMPLE.TEST"
        first = _payload(email=email_lower, main_pain="First submission", preferred_next_step="follow_up")
        second = _payload(
            email=email_upper,
            contact_name="Casey Updated",
            main_pain="Second submission with more context",
            service_interests=["leads_customer_management"],
            service_detail="",
            preferred_next_step="book",
            correlation_id=f"e2e-merge-{uuid.uuid4()}",
        )
        self.assertEqual(self._post(first).status_code, 200)
        self.assertEqual(self._post(second).status_code, 200)

        rows = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS c FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            """,
            (email_lower,),
        )
        self.assertEqual(rows[0]["c"], 1)
        lead = db_optimizer.execute_query(
            """
            SELECT name, notes, metadata FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            LIMIT 1
            """,
            (email_lower,),
        )[0]
        self.assertEqual(lead["name"], "Casey Updated")
        self.assertIn("Second submission", lead["notes"] or "")
        meta = json.loads(lead["metadata"] or "{}")
        self.assertIn("leads_customer_management", meta.get("lead_interests") or [])
        self.assertEqual(mock_email.call_count, 2)
        self.assertEqual(mock_slack.call_count, 2)

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_duplicate_correlation_skips_renotify(self, mock_email, mock_slack):
        email = f"dedupe.{uuid.uuid4().hex[:8]}@example.test"
        corr = f"e2e-dedupe-{uuid.uuid4()}"
        payload = _payload(email=email, correlation_id=corr)
        self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(mock_email.call_count, 1)
        self.assertEqual(mock_slack.call_count, 1)

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_service_interests_accepts_comma_string(self, *_):
        from core.database_optimization import db_optimizer

        email = f"csv.{uuid.uuid4().hex[:8]}@example.test"
        res = self._post(
            _payload(
                email=email,
                service_interests="website_design_development, scheduling_operations",
            )
        )
        self.assertEqual(res.status_code, 200)
        lead = db_optimizer.execute_query(
            """
            SELECT metadata FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            LIMIT 1
            """,
            (email,),
        )[0]
        meta = json.loads(lead["metadata"] or "{}")
        interests = meta.get("lead_interests") or []
        self.assertIn("website_design_development", interests)
        self.assertIn("scheduling_operations", interests)

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=True)
    @patch("core.contact_api._send_contact_email", return_value=True)
    def test_contact_form_still_independent(self, mock_email, mock_slack):
        from core.database_optimization import db_optimizer

        email = f"contact.{uuid.uuid4().hex[:8]}@example.test"
        with patch("core.contact_api.db_optimizer", db_optimizer):
            res = self.client.post(
                "/api/contact",
                json={
                    "name": "Contact Only",
                    "email": email,
                    "message": "Just a question, not intake.",
                },
            )
        self.assertEqual(res.status_code, 200)
        leads = db_optimizer.execute_query(
            """
            SELECT id FROM leads
            WHERE user_id = 1 AND lower(trim(email)) = lower(trim(?)) AND withdrawn_at IS NULL
            """,
            (email,),
        )
        # Contact must not silently create consultation CRM lead
        self.assertFalse(leads)
        backup = db_optimizer.execute_query(
            """
            SELECT form_type FROM customer_contact_submissions
            WHERE lower(email) = lower(?)
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        self.assertTrue(backup)
        self.assertNotEqual(backup[0]["form_type"], "consultation_intake")

    @patch("core.contact_api.check_public_intake_rate_limit")
    def test_rate_limit_returns_structured_429(self, mock_rl):
        from core.rate_limiter import RateLimitResult

        mock_rl.return_value = RateLimitResult(
            allowed=False, remaining=0, reset_time=0, retry_after=120, limit=10
        )
        res = self._post(_payload())
        self.assertEqual(res.status_code, 429)
        body = res.get_json()
        self.assertEqual(body.get("error_code"), "RATE_LIMIT_EXCEEDED")
        self.assertEqual(body.get("retry_after"), 120)

    @patch("core.lead_form_notifications.send_lead_slack_notification", return_value=False)
    @patch("core.contact_api._send_contact_email", return_value=False)
    def test_notification_failure_still_succeeds_when_crm_or_backup_ok(self, *_):
        email = f"notifyfail.{uuid.uuid4().hex[:8]}@example.test"
        res = self._post(_payload(email=email))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))


if __name__ == "__main__":
    unittest.main()
