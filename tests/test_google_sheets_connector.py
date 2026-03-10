"""
Unit tests for core/google_sheets_connector.py (SheetsConfig, GoogleSheetsConnector).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.google_sheets_connector import SheetsConfig, GoogleSheetsConnector


class TestSheetsConfig:
    def test_sheets_config_dataclass(self):
        c = SheetsConfig(
            spreadsheet_id="id1",
            worksheet_name="Leads",
            credentials_path="auth/creds.json",
            token_path="auth/token.pkl",
        )
        assert c.spreadsheet_id == "id1"
        assert c.worksheet_name == "Leads"


class TestGoogleSheetsConnector:
    @patch.object(GoogleSheetsConnector, "_authenticate", return_value=None)
    def test_init_sets_config(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        assert conn.config is config
        mock_auth.assert_called_once()

    @patch.object(GoogleSheetsConnector, "_authenticate")
    def test_add_lead_not_authenticated_returns_error(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        conn.authenticated = False
        result = conn.add_lead({"email": "a@b.com", "name": "A"})
        assert result.get("success") is False
        assert "authenticated" in result.get("error", "").lower()

    @patch.object(GoogleSheetsConnector, "_authenticate")
    def test_add_lead_authenticated_appends_row(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        conn.authenticated = True
        conn.service = MagicMock()
        result = conn.add_lead({
            "id": "1",
            "name": "Jane",
            "email": "jane@example.com",
            "company": "Acme",
        })
        assert result.get("success") is True
        conn.service.spreadsheets.return_value.values.return_value.append.assert_called_once()

    @patch.object(GoogleSheetsConnector, "_authenticate")
    def test_get_leads_not_authenticated_returns_error(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        conn.authenticated = False
        result = conn.get_leads()
        assert result.get("success") is False

    @patch.object(GoogleSheetsConnector, "_authenticate")
    def test_get_leads_authenticated_returns_parsed_rows(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        conn.authenticated = True
        conn.service = MagicMock()
        conn.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["ID", "Name", "Email"],
                ["1", "Jane", "jane@example.com"],
            ]
        }
        result = conn.get_leads()
        assert result.get("success") is True
        assert result.get("leads") == [{"id": "1", "name": "Jane", "email": "jane@example.com"}]

    @patch.object(GoogleSheetsConnector, "_authenticate")
    def test_update_lead_not_authenticated_returns_error(self, mock_auth):
        config = SheetsConfig("sid", "Leads", "creds.json", "token.pkl")
        conn = GoogleSheetsConnector(config)
        conn.authenticated = False
        result = conn.update_lead("1", {"status": "contacted"})
        assert result.get("success") is False
