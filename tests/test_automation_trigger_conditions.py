#!/usr/bin/env python3
"""Unit tests for core/automation_trigger_conditions.py (IF-group AND logic)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from core.automation_trigger_conditions import (  # noqa: E402
    evaluate_if_group,
    validate_if_group_structure,
)


class TestTriggerIfGroup(unittest.TestCase):
    def test_validate_rejects_bad_match(self):
        ok, msg = validate_if_group_structure(
            "email_received",
            {"match": "any", "conditions": [{"field": "subject", "op": "contains", "value": "x"}]},
        )
        self.assertFalse(ok)
        self.assertIn("match", msg or "")

    def test_validate_scheduled_run_operator(self):
        ok, msg = validate_if_group_structure(
            "time_based",
            {
                "match": "all",
                "conditions": [{"field": "scheduled_run", "op": "contains", "value": "x"}],
            },
        )
        self.assertFalse(ok)
        self.assertIn("not valid", msg or "")

    def test_validate_numeric_op_on_subject_fails(self):
        ok, msg = validate_if_group_structure(
            "email_received",
            {
                "match": "all",
                "conditions": [{"field": "subject", "op": "gt", "value": 1}],
            },
        )
        self.assertFalse(ok)

    def test_validate_score_cannot_use_contains(self):
        ok, msg = validate_if_group_structure(
            "lead_created",
            {
                "match": "all",
                "conditions": [{"field": "score", "op": "contains", "value": "1"}],
            },
        )
        self.assertFalse(ok)
        self.assertIn("not valid for numeric field", msg or "")

    def test_empty_conditions_is_vacuous_true(self):
        self.assertTrue(
            evaluate_if_group(
                "email_received",
                {"sender_email": "a@b.co"},
                {"match": "all", "conditions": []},
            )
        )

    def test_email_received_and_two_conditions(self):
        block = {
            "match": "all",
            "conditions": [
                {"field": "sender_email", "op": "ends_with", "value": "@acme.com"},
                {"field": "subject", "op": "contains", "value": "quote"},
            ],
        }
        self.assertTrue(
            evaluate_if_group(
                "email_received",
                {"sender_email": "x@acme.com", "subject": "Please send a quote"},
                block,
            )
        )
        self.assertFalse(
            evaluate_if_group(
                "email_received",
                {"sender_email": "x@other.com", "subject": "Please send a quote"},
                block,
            )
        )

    def test_lead_score_gte(self):
        block = {
            "match": "all",
            "conditions": [{"field": "score", "op": "gte", "value": 7}],
        }
        self.assertTrue(
            evaluate_if_group(
                "lead_created",
                {"lead_id": 1, "source": "gmail", "score": 8},
                block,
            )
        )
        self.assertFalse(
            evaluate_if_group(
                "lead_created",
                {"lead_id": 1, "source": "gmail", "score": 5},
                block,
            )
        )

    def test_scheduled_run_equals(self):
        block = {
            "match": "all",
            "conditions": [{"field": "scheduled_run", "op": "equals", "value": "true"}],
        }
        self.assertTrue(
            evaluate_if_group(
                "time_based",
                {"scheduled_run": True, "frequency": "daily"},
                block,
            )
        )
        self.assertFalse(
            evaluate_if_group(
                "time_based",
                {"scheduled_run": False, "frequency": "daily"},
                block,
            )
        )

    def test_scheduled_run_string_false_not_truthy(self):
        """Regression: bool("false") is True in Python; evaluator must use truthy parsing."""
        block = {
            "match": "all",
            "conditions": [{"field": "scheduled_run", "op": "equals", "value": False}],
        }
        self.assertTrue(
            evaluate_if_group(
                "time_based",
                {"scheduled_run": "false", "frequency": "daily"},
                block,
            )
        )


class TestEngineTriggerIntegration(unittest.TestCase):
    def test_check_trigger_if_group_runs_before_legacy(self):
        from unittest.mock import patch

        with patch("services.automation_engine.db_optimizer") as mock_db:
            with patch("services.automation_engine.enhanced_crm_service"):
                with patch("services.automation_engine.MinimalEmailParser"):
                    mock_db.execute_query.return_value = []
                    from services.automation_engine import (
                        AutomationEngine,
                        AutomationRule,
                        AutomationStatus,
                        ActionType,
                        TriggerType,
                    )
                    from datetime import datetime

                    eng = AutomationEngine()
                    rule = AutomationRule(
                        id=1,
                        user_id=1,
                        name="t",
                        description="",
                        trigger_type=TriggerType.EMAIL_RECEIVED,
                        trigger_conditions={
                            "slug": "x",
                            "if": {
                                "match": "all",
                                "conditions": [
                                    {"field": "subject", "op": "contains", "value": "invoice"}
                                ],
                            },
                        },
                        action_type=ActionType.UPDATE_CRM_FIELD,
                        action_parameters={"slug": "gmail_crm"},
                        status=AutomationStatus.ACTIVE,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        last_executed=None,
                        execution_count=0,
                        success_count=0,
                        error_count=0,
                    )
                    self.assertTrue(
                        eng._check_trigger_conditions(
                            rule,
                            {"sender_email": "a@b.com", "subject": "Pay this invoice"},
                        )
                    )
                    self.assertFalse(
                        eng._check_trigger_conditions(
                            rule,
                            {"sender_email": "a@b.com", "subject": "Hello"},
                        )
                    )


if __name__ == "__main__":
    unittest.main()
