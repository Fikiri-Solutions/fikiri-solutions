#!/usr/bin/env python3
"""Appointments routes tests."""

import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.appointments import appointments_bp


def _auth_headers():
    return {"Authorization": "Bearer testtoken"}


class TestAppointmentsRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(appointments_bp)
        self.client = self.app.test_client()

    @patch("core.jwt_auth.get_jwt_manager")
    def test_create_appointment_missing_body(self, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        response = self.client.post('/api/appointments', headers=_auth_headers(), json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'MISSING_BODY')

    @patch("core.jwt_auth.get_jwt_manager")
    def test_create_appointment_invalid_date(self, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        response = self.client.post(
            '/api/appointments',
            headers=_auth_headers(),
            json={"title": "Call", "start_time": "bad", "end_time": "bad"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'INVALID_DATE')

    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_create_appointment_success(self, mock_mgr, mock_service):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_service.return_value.create_appointment.return_value = {"id": 10, "title": "Call"}
        start = (datetime.now() + timedelta(hours=1)).isoformat()
        end = (datetime.now() + timedelta(hours=2)).isoformat()
        response = self.client.post(
            '/api/appointments',
            headers=_auth_headers(),
            json={"title": "Call", "start_time": start, "end_time": end}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))

    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_list_appointments_success(self, mock_mgr, mock_service):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_service.return_value.list_appointments.return_value = [{"id": 1}]
        response = self.client.get('/api/appointments', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data.get('data', {}).get('appointments', [])), 1)

    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_update_appointment_invalid_date(self, mock_mgr, mock_service):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        response = self.client.put(
            '/api/appointments/1',
            headers=_auth_headers(),
            json={"start_time": "bad"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('code'), 'INVALID_DATE')

    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_cancel_appointment_success(self, mock_mgr, mock_service):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_service.return_value.cancel_appointment.return_value = {"id": 1, "status": "canceled"}
        response = self.client.post('/api/appointments/1/cancel', headers=_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('status'), 'canceled')

    @patch("routes.appointments.integration_manager")
    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_get_freebusy_internal_only(self, mock_mgr, mock_service, mock_integration):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_integration.get_integration.return_value = None
        mock_service.return_value.get_freebusy.return_value = {
            "start": "s",
            "end": "e",
            "busy": [],
            "free": []
        }
        response = self.client.get(
            '/api/appointments/freebusy?start=2025-01-01T00:00:00Z&end=2025-01-01T01:00:00Z',
            headers=_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('source'), 'internal_only')

    @patch("routes.appointments.integration_manager")
    @patch("routes.appointments.AppointmentsService")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_check_conflicts_suggests_slots(self, mock_mgr, mock_service, mock_integration):
        mock_mgr.return_value.verify_access_token.return_value = {"id": 1, "user_id": 1}
        mock_integration.get_integration.return_value = None
        mock_service.return_value.check_conflicts.side_effect = [
            [{"id": 99}],
            [],
            [],
            []
        ]
        response = self.client.post(
            '/api/appointments/check-conflicts',
            headers=_auth_headers(),
            json={
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-01T00:30:00Z"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', {}).get('has_conflicts'))
        self.assertEqual(len(data.get('data', {}).get('suggested_slots', [])), 3)


if __name__ == '__main__':
    unittest.main()
