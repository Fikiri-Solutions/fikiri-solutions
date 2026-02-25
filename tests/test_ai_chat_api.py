"""
Unit tests for core/ai_chat_api.py (AI chat and status endpoints).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.ai_chat_api import ai_bp


class TestAIChatAPI:
    """Test /api/ai/chat and /api/ai/status."""

    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(ai_bp)
        self.client = self.app.test_client()

    def test_chat_empty_or_invalid_body_returns_error(self):
        response = self.client.post(
            "/api/ai/chat",
            data="",
            content_type="application/json",
        )
        assert response.status_code in (400, 500)
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "error" in data or "message" in data

    def test_chat_missing_message_returns_400(self):
        response = self.client.post(
            "/api/ai/chat",
            json={"message": ""},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data.get("success") is False
        assert "message" in data.get("error", "").lower()

    def test_chat_no_auth_returns_401(self):
        response = self.client.post(
            "/api/ai/chat",
            json={"message": "hello"},
            content_type="application/json",
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data.get("success") is False
        assert data.get("code") == "AUTHENTICATION_REQUIRED"

    @patch("core.ai_chat_api.get_current_user_id")
    @patch("core.ai_chat_api.get_current_user")
    def test_chat_with_user_id_in_body_succeeds_with_fallback(self, mock_get_user, mock_get_user_id):
        mock_get_user.side_effect = Exception("no jwt")
        mock_get_user_id.return_value = None

        response = self.client.post(
            "/api/ai/chat",
            json={"message": "hello", "user_id": 1},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "data" in data
        assert "response" in data["data"]
        assert "suggested_actions" in data["data"]

    @patch("core.ai_chat_api._get_llm_router")
    @patch("core.ai_chat_api.get_current_user_id")
    @patch("core.ai_chat_api.get_current_user")
    def test_chat_uses_llm_when_available(self, mock_get_user, mock_get_user_id, mock_get_router):
        mock_get_user.side_effect = Exception("no jwt")
        mock_get_user_id.return_value = None
        router = MagicMock()
        router.client.is_enabled.return_value = True
        router.process.return_value = {"success": True, "content": "LLM reply"}
        mock_get_router.return_value = router

        response = self.client.post(
            "/api/ai/chat",
            json={"message": "analyze my leads", "user_id": 1},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data["data"]["response"] == "LLM reply"
        router.process.assert_called_once()

    @patch("core.ai_chat_api.get_current_user_id")
    def test_chat_contextual_fallback_for_lead_query(self, mock_get_user_id):
        mock_get_user_id.return_value = 1

        response = self.client.post(
            "/api/ai/chat",
            json={"message": "analyze my leads", "user_id": 1},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "lead" in data["data"]["response"].lower() or "crm" in data["data"]["response"].lower()

    def test_status_returns_200_and_services(self):
        response = self.client.get("/api/ai/status")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert "data" in data
        assert data["data"].get("ai_available") is True
        assert "services" in data["data"]
        assert "timestamp" in data["data"]
