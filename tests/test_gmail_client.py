#!/usr/bin/env python3
"""
Gmail Client Unit Tests
Tests for integrations/gmail/gmail_client.py
"""

import unittest
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestGmailClient(unittest.TestCase):
    def setUp(self):
        import importlib
        # GmailClient() reads FERNET_KEY; avoid invalid key from .env breaking tests
        self._saved_fernet = os.environ.pop("FERNET_KEY", None)
        try:
            self.module = importlib.import_module("integrations.gmail.gmail_client")
            self.client = self.module.GmailClient()
        finally:
            if self._saved_fernet is not None:
                os.environ["FERNET_KEY"] = self._saved_fernet

    def tearDown(self):
        if getattr(self, "_saved_fernet", None) is not None:
            os.environ["FERNET_KEY"] = self._saved_fernet
        elif "FERNET_KEY" in os.environ:
            os.environ.pop("FERNET_KEY", None)

    def test_get_credentials_returns_none_without_tokens(self):
        with patch.object(self.client, "_get_gmail_tokens", return_value=None):
            with patch.object(self.module, "GOOGLE_API_AVAILABLE", True):
                creds = self.client.get_credentials_for_user(1)
        self.assertIsNone(creds)

    def test_get_credentials_returns_none_without_google_libs(self):
        with patch.object(self.client, "_get_gmail_tokens", return_value={"access_token": "a", "refresh_token": "r", "expiry": None, "scopes": []}):
            with patch.object(self.module, "GOOGLE_API_AVAILABLE", False):
                creds = self.client.get_credentials_for_user(1)
        self.assertIsNone(creds)

    def test_get_credentials_refreshes_and_saves_tokens(self):
        token_data = {"access_token": "a", "refresh_token": "r", "expiry": None, "scopes": ["s1"]}
        fake_creds = SimpleNamespace(
            valid=False,
            expired=True,
            refresh_token="r",
            token="newtoken",
            expiry=None,
        )
        fake_creds.refresh = MagicMock()

        with patch.object(self.client, "_get_gmail_tokens", return_value=token_data):
            with patch.object(self.client, "_save_gmail_tokens") as mock_save:
                with patch.object(self.module, "GOOGLE_API_AVAILABLE", True):
                    with patch.object(self.module, "Credentials", return_value=fake_creds):
                        with patch.object(self.module, "Request"):
                            creds = self.client.get_credentials_for_user(1)
        self.assertIs(creds, fake_creds)
        fake_creds.refresh.assert_called_once()
        mock_save.assert_called_once()

    def test_get_credentials_non_refreshable_returns_none(self):
        token_data = {"access_token": "a", "refresh_token": None, "expiry": None, "scopes": []}
        fake_creds = SimpleNamespace(valid=False, expired=True, refresh_token=None)
        fake_creds.refresh = MagicMock()

        with patch.object(self.client, "_get_gmail_tokens", return_value=token_data):
            with patch.object(self.module, "GOOGLE_API_AVAILABLE", True):
                with patch.object(self.module, "Credentials", return_value=fake_creds):
                    creds = self.client.get_credentials_for_user(1)
        self.assertIsNone(creds)

    def test_get_gmail_service_for_user_builds_service(self):
        fake_creds = object()
        with patch.object(self.client, "get_credentials_for_user", return_value=fake_creds):
            with patch.object(self.module, "build", return_value="service") as mock_build:
                service = self.client.get_gmail_service_for_user(1)
        self.assertEqual(service, "service")
        mock_build.assert_called_once()

    def test_get_gmail_service_for_user_raises_when_no_creds(self):
        with patch.object(self.client, "get_credentials_for_user", return_value=None):
            with self.assertRaises(RuntimeError):
                self.client.get_gmail_service_for_user(1)


if __name__ == "__main__":
    unittest.main()
