#!/usr/bin/env python3
"""
Email Service Manager Unit Tests
Tests for email_automation/service_manager.py
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class DummyProvider:
    def __init__(self, ok=True):
        self.service_name = "Dummy"
        self.authenticated = False
        self.ok = ok

    def authenticate(self) -> bool:
        self.authenticated = self.ok
        return self.ok

    def get_messages(self, limit: int = 10):
        return [{"id": "m1"}]

    def send_message(self, to: str, subject: str, body: str) -> bool:
        return True


class TestEmailServiceManager(unittest.TestCase):
    def setUp(self):
        from email_automation.service_manager import EmailServiceManager
        self.manager = EmailServiceManager()

    def test_add_provider_and_active(self):
        ok = self.manager.add_provider("dummy", DummyProvider(ok=True))
        self.assertTrue(ok)
        self.assertIsNotNone(self.manager.get_active_provider())
        self.assertEqual(self.manager.get_active_provider().service_name, "Dummy")

    def test_add_provider_rejects_on_auth_fail(self):
        ok = self.manager.add_provider("dummy", DummyProvider(ok=False))
        self.assertFalse(ok)
        self.assertIsNone(self.manager.get_active_provider())

    def test_switch_provider(self):
        self.manager.add_provider("a", DummyProvider(ok=True))
        self.manager.add_provider("b", DummyProvider(ok=True))
        self.assertTrue(self.manager.switch_provider("b"))
        self.assertEqual(self.manager.get_active_provider().service_name, "Dummy")

    def test_get_all_messages_and_send(self):
        self.manager.add_provider("dummy", DummyProvider(ok=True))
        self.assertEqual(self.manager.get_all_messages(1), [{"id": "m1"}])
        self.assertTrue(self.manager.send_message("x@y.com", "Subj", "Body"))


if __name__ == "__main__":
    unittest.main()
