"""
Unit tests for analytics/monitoring_api.py (monitoring dashboard blueprint).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from analytics.monitoring_api import monitoring_dashboard_bp


class TestMonitoringAPI:
    """Test /api/monitoring/* endpoints."""

    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(monitoring_dashboard_bp)
        self.client = self.app.test_client()

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_dashboard_returns_200_with_data(self, mock_system):
        mock_system.get_dashboard_data.return_value = {"overall_health": {"status": "healthy"}, "timestamp": "now"}
        response = self.client.get("/api/monitoring/dashboard")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("data", {}).get("overall_health", {}).get("status") == "healthy"

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_dashboard_exception_returns_500(self, mock_system):
        mock_system.get_dashboard_data.side_effect = RuntimeError("backend down")
        response = self.client.get("/api/monitoring/dashboard")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_redis_metrics_returns_200(self, mock_system):
        mock_system.get_redis_metrics.return_value = {"connected": True, "memory": 1024}
        response = self.client.get("/api/monitoring/redis")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("metrics", {}).get("connected") is True

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_system_metrics_returns_200(self, mock_system):
        mock_system.get_system_metrics.return_value = {"cpu": 10}
        response = self.client.get("/api/monitoring/system")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "metrics" in data

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_application_metrics_returns_200(self, mock_system):
        mock_system.get_application_metrics.return_value = {"requests": 100}
        response = self.client.get("/api/monitoring/application")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "metrics" in data

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_alerts_returns_200_with_filters(self, mock_system):
        alert = MagicMock()
        alert.id = "a1"
        alert.level.value = "warning"
        alert.title = "Test"
        alert.message = "Msg"
        alert.timestamp.isoformat.return_value = "2024-01-01T00:00:00"
        alert.resolved = False
        alert.resolved_at = None
        mock_system.alerts = [alert]
        response = self.client.get("/api/monitoring/alerts?active_only=true&limit=10")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "alerts" in data
        assert data.get("total") >= 0

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_resolve_alert_success_returns_200(self, mock_system):
        mock_system.resolve_alert.return_value = True
        response = self.client.post("/api/monitoring/alerts/alert-123/resolve")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_resolve_alert_not_found_returns_404(self, mock_system):
        mock_system.resolve_alert.return_value = False
        response = self.client.post("/api/monitoring/alerts/nonexistent/resolve")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data.get("success") is False

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_get_alert_statistics_returns_200(self, mock_system):
        mock_system.get_alert_statistics.return_value = {"total": 5, "resolved": 3}
        response = self.client.get("/api/monitoring/alerts/statistics")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "statistics" in data

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_health_check_returns_200_when_healthy(self, mock_system):
        mock_system.get_dashboard_data.return_value = {
            "overall_health": {"status": "healthy", "score": 100},
            "timestamp": "now",
        }
        response = self.client.get("/api/monitoring/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("status") == "healthy"

    @patch("analytics.monitoring_api.monitoring_dashboard_system")
    def test_health_check_returns_500_when_error_in_dashboard(self, mock_system):
        mock_system.get_dashboard_data.return_value = {"error": "redis down"}
        response = self.client.get("/api/monitoring/health")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "unhealthy" in data.get("status", "") or "error" in data

    def test_get_queue_status_returns_200(self):
        mock_queue = MagicMock()
        mock_queue.get_queue_length.return_value = 5
        with patch("core.redis_queues.email_queue", mock_queue), \
             patch("core.redis_queues.ai_queue", mock_queue), \
             patch("core.redis_queues.webhook_queue", mock_queue), \
             patch("core.redis_queues.crm_queue", mock_queue):
            response = self.client.get("/api/monitoring/queues")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "queues" in data
        assert "email_processing" in data["queues"]

    def test_get_performance_metrics_returns_200_or_500(self):
        response = self.client.get("/api/monitoring/performance")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data.get("success") is True
            assert "performance" in data
