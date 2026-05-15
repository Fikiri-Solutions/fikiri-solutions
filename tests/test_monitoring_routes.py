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

    @patch("routes.monitoring.resolve_request_user_id", return_value=1)
    @patch("routes.monitoring.db_optimizer")
    @patch("core.oauth_token_manager.oauth_token_manager")
    def test_email_sync_status_not_connected(self, mock_oauth, mock_db, mock_resolve):
        mock_db.execute_query.return_value = []
        mock_oauth.get_token_status.return_value = {"success": False, "has_token": False}
        response = self.client.get('/api/email/sync/status?user_id=1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('data', {}).get('sync_status'), 'not_connected')

    @patch("routes.monitoring.resolve_request_user_id", return_value=1)
    @patch("routes.monitoring.db_optimizer")
    def test_email_sync_status_pending_idle_not_marked_syncing(self, mock_db, mock_resolve):
        """pending + syncing=0 must not set syncing:true (was infinite spinner at 1%)."""

        def exec_side_effect(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM GMAIL_TOKENS" in s:
                return [{"access_token_enc": "tok", "access_token": None, "is_active": True}]
            if "FROM USER_SYNC_STATUS" in s:
                return [
                    {
                        "last_sync": None,
                        "sync_status": "pending",
                        "total_emails": 0,
                        "syncing": 0,
                    }
                ]
            return []

        mock_db.execute_query.side_effect = exec_side_effect
        mock_db.table_exists.return_value = True

        response = self.client.get("/api/email/sync/status?user_id=1")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        payload = data.get("data") or {}
        self.assertFalse(payload.get("syncing"))
        self.assertEqual(payload.get("progress"), 0)

    @patch("routes.monitoring._reconcile_stale_gmail_sync_queue", return_value=False)
    @patch("routes.monitoring.resolve_request_user_id", return_value=1)
    @patch("routes.monitoring.db_optimizer")
    def test_email_sync_status_queued_is_syncing_without_fake_one_percent(
        self, mock_db, mock_resolve, _mock_reconcile
    ):
        """After sync-gmail, row is queued + syncing=0; API still polls as in-flight with progress 0."""

        def exec_side_effect(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM GMAIL_TOKENS" in s:
                return [{"access_token_enc": "tok", "access_token": None, "is_active": True}]
            if "FROM USER_SYNC_STATUS" in s:
                return [
                    {
                        "last_sync": None,
                        "sync_status": "queued",
                        "total_emails": 0,
                        "syncing": 0,
                    }
                ]
            if "FROM SYNCED_EMAILS" in s and "COUNT" in s:
                return [{"count": 0}]
            if "GMAIL_SYNC_JOBS" in s:
                return [
                    {
                        "progress": 0,
                        "emails_synced": 0,
                        "status": "pending",
                        "job_id": "gmail_sync_1_1",
                        "created_at": "now",
                        "started_at": None,
                    }
                ]
            return []

        mock_db.execute_query.side_effect = exec_side_effect
        mock_db.table_exists.return_value = True

        response = self.client.get("/api/email/sync/status?user_id=1")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        payload = data.get("data") or {}
        self.assertTrue(payload.get("syncing"))
        self.assertEqual(payload.get("sync_status"), "queued")
        self.assertEqual(payload.get("progress"), 0)

    @patch("routes.monitoring.resolve_request_user_id", return_value=1)
    @patch("routes.monitoring.db_optimizer")
    def test_email_sync_status_stale_queued_resets_idle(self, mock_db, mock_resolve):
        """Orphaned queued + old pending job should not report syncing forever."""

        def exec_side_effect(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM GMAIL_TOKENS" in s:
                return [{"access_token_enc": "tok", "access_token": None, "is_active": True}]
            if "FROM USER_SYNC_STATUS" in s and "SELECT" in s:
                return [
                    {
                        "last_sync": None,
                        "sync_status": "queued",
                        "total_emails": 0,
                        "syncing": 0,
                    }
                ]
            if "FROM GMAIL_SYNC_JOBS" in s and "JOB_ID" in s:
                return [{"job_id": "gmail_sync_1_stale"}]
            if "UPDATE GMAIL_SYNC_JOBS" in s:
                return []
            if "FROM SYNCED_EMAILS" in s and "COUNT" in s:
                return [{"count": 0}]
            if "GMAIL_SYNC_JOBS" in s and "PROGRESS" in s:
                return []
            return []

        mock_db.execute_query.side_effect = exec_side_effect
        mock_db.table_exists.return_value = True
        mock_db.sql_column_older_than_n_minutes_ago.return_value = "1=1"

        response = self.client.get("/api/email/sync/status?user_id=1")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.data).get("data") or {}
        self.assertFalse(payload.get("syncing"))
        self.assertEqual(payload.get("sync_status"), "connected_pending_sync")
        mock_db.upsert_user_sync_status_merge.assert_called_once()

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
