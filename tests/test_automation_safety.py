#!/usr/bin/env python3
"""
Automation Safety Unit Tests
Tests for core/automation_safety.py (kill-switch, limits, can_execute)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestAutomationSafetyManager(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_db.execute_query.return_value = None
        with patch("core.automation_safety.db_optimizer", self.mock_db):
            from core.automation_safety import AutomationSafetyManager

            self.manager = AutomationSafetyManager(self.mock_db)

    def test_config_has_expected_attributes(self):
        self.assertHasAttr(self.manager.config, "global_kill_switch")
        self.assertHasAttr(self.manager.config, "dry_run_mode")
        self.assertHasAttr(self.manager.config, "max_actions_per_user_per_5min")

    def assertHasAttr(self, obj, name):
        self.assertTrue(hasattr(obj, name), f"Missing attribute: {name}")

    def test_check_rate_limits_blocks_when_kill_switch_enabled(self):
        with patch.object(self.manager, "is_global_kill_switch_enabled", return_value=True):
            result = self.manager.check_rate_limits(
                user_id=1, action_type="send_email", target_contact="a@b.com"
            )
        self.assertFalse(result.get("allowed", True))
        self.assertIn("reason", result)

    def test_check_rate_limits_allowed_when_under_limits(self):
        with patch.object(self.manager, "is_global_kill_switch_enabled", return_value=False):
            # _get_user_safety_config returns default when no row; _get_user_action_count needs [(0,)]
            self.mock_db.execute_query.side_effect = [[], [(0,)], [(0,)]]
            result = self.manager.check_rate_limits(
                user_id=1, action_type="send_email", target_contact="a@b.com"
            )
        self.assertIsInstance(result, dict)
        self.assertIn("allowed", result)
        self.assertTrue(result.get("allowed"))

    def test_toggle_global_kill_switch_returns_success(self):
        self.mock_db.execute_query.return_value = None
        result = self.manager.toggle_global_kill_switch(True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("kill_switch_enabled"))


if __name__ == "__main__":
    unittest.main()
