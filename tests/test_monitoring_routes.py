#!/usr/bin/env python3
"""Monitoring routes tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.monitoring import monitoring_bp


class TestMonitoringRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(monitoring_bp)
        self.client = self.app.test_client()

    @patch("routes.monitoring.db_optimizer")
    @patch("core.redis_connection_helper.is_redis_available", return_value=True)
    def test_health_old(self, mock_redis, mock_db):
        mock_db.execute_query.return_value = [(1,)]
        response = self.client.get('/api/health-old')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('status'), 'healthy')

    @patch("routes.monitoring.get_current_user_id", return_value=None)
    def test_gmail_status_requires_auth(self, mock_user_id):
        response = self.client.get('/api/gmail/status')
        self.assertEqual(response.status_code, 401)

    @patch("routes.monitoring.get_current_user_id", return_value=1)
    @patch("routes.monitoring.oauth_token_manager")
    def test_gmail_status_connected(self, mock_oauth, mock_user_id):
        mock_oauth.get_token_status.return_value = {"success": True, "last_sync": "now", "expires_at": "later"}
        response = self.client.get('/api/gmail/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', {}).get('connected'))

    @patch("routes.monitoring.get_current_user_id", return_value=None)
    @patch("routes.monitoring.db_optimizer")
    @patch("core.oauth_token_manager.oauth_token_manager")
    def test_email_sync_status_not_connected(self, mock_oauth, mock_db, mock_user_id):
        mock_db.execute_query.return_value = []
        mock_oauth.get_token_status.return_value = {"success": False, "has_token": False}
        response = self.client.get('/api/email/sync/status?user_id=1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('sync_status'), 'not_connected')

    @patch("routes.monitoring.get_current_user_id", return_value=None)
    def test_rate_limits_requires_auth(self, mock_user_id):
        response = self.client.get('/api/rate-limits/status')
        self.assertEqual(response.status_code, 401)

    @patch("routes.monitoring.get_current_user_id", return_value=1)
    @patch("core.rate_limiter.enhanced_rate_limiter")
    def test_rate_limits_status(self, mock_limiter, mock_user_id):
        mock_limiter.get_user_limits.return_value = {"limit": 10}
        mock_limiter.get_current_usage.return_value = {"used": 1}
        mock_limiter.get_reset_time.return_value = "soon"
        response = self.client.get('/api/rate-limits/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('limits', {}).get('limit'), 10)

    @patch("core.performance_monitor.performance_monitor")
    def test_system_metrics(self, mock_perf):
        mock_perf.get_system_metrics.return_value = {"cpu": 1}
        response = self.client.get('/api/system/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('cpu'), 1)

    @patch("routes.monitoring.get_current_user_id", return_value=1)
    @patch("routes.monitoring.db_optimizer")
    def test_get_alerts(self, mock_db, mock_user_id):
        mock_db.execute_query.return_value = [{
            "id": 1,
            "alert_type": "test",
            "alert_level": "info",
            "message": "hello",
            "timestamp": "now",
            "resolved": 0,
        }]
        response = self.client.get('/api/alerts')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data.get('data', {}).get('alerts', [])), 1)


if __name__ == '__main__':
    unittest.main()
