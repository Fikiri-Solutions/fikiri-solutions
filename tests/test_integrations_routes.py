#!/usr/bin/env python3
"""Integrations routes tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.integrations import integrations_bp


def _auth_headers():
    return {"Authorization": "Bearer testtoken"}


class TestIntegrationsRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(integrations_bp)
        self.client = self.app.test_client()

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.integrations.secrets.token_urlsafe", return_value="state123")
    @patch("routes.integrations.google_calendar_provider")
    @patch("routes.integrations.db_optimizer")
    def test_google_calendar_connect(self, mock_db, mock_provider, mock_state, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_provider.get_auth_url.return_value = "http://auth"
        response = self.client.get('/api/integrations/google-calendar/connect', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('auth_url', data)
        mock_db.execute_query.assert_called_once()

    @patch("routes.integrations.verify_oauth_state", return_value=None)
    def test_google_calendar_callback_invalid_state(self, mock_verify):
        response = self.client.get('/api/integrations/google-calendar/callback?code=abc&state=bad')
        self.assertEqual(response.status_code, 302)
        self.assertIn('invalid_state', response.location)

    @patch("routes.integrations.verify_oauth_state", return_value={"user_id": 1, "redirect_url": "/dashboard"})
    @patch("routes.integrations.google_calendar_provider")
    @patch("routes.integrations.integration_manager")
    @patch("routes.integrations.db_optimizer")
    def test_google_calendar_callback_success(self, mock_db, mock_manager, mock_provider, mock_verify):
        mock_provider.exchange_code_for_tokens.return_value = {"scope": "a b"}
        response = self.client.get('/api/integrations/google-calendar/callback?code=abc&state=good')
        self.assertEqual(response.status_code, 302)
        self.assertIn('calendar_connected=true', response.location)
        mock_manager.connect.assert_called_once()

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.integrations.integration_manager")
    def test_google_calendar_status(self, mock_manager, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_manager.get_status.return_value = {"connected": True}
        response = self.client.get('/api/integrations/google-calendar/status', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('connected'))

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.integrations.integration_manager")
    def test_google_calendar_disconnect(self, mock_manager, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_manager.disconnect.return_value = {"success": True}
        response = self.client.post('/api/integrations/google-calendar/disconnect', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.integrations.CalendarManager")
    def test_list_calendar_events_not_connected(self, mock_manager, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_manager.return_value.get_calendar_client.return_value = None
        response = self.client.get('/api/integrations/calendar/events', headers=_auth_headers())
        self.assertEqual(response.status_code, 400)

    @patch("core.jwt_auth.get_jwt_manager")
    def test_create_calendar_event_missing_body(self, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        response = self.client.post('/api/integrations/calendar/events', headers=_auth_headers(), json={})
        self.assertEqual(response.status_code, 400)

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.integrations.CalendarManager")
    def test_create_calendar_event_success(self, mock_manager, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_manager.return_value.create_event.return_value = {"id": "evt"}
        response = self.client.post(
            '/api/integrations/calendar/events',
            headers=_auth_headers(),
            json={"start": "2025-01-01T00:00:00", "end": "2025-01-01T01:00:00", "summary": "Call"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))


if __name__ == '__main__':
    unittest.main()
