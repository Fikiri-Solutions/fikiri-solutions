"""
Unit tests for email_automation/ai_assistant.py (MinimalAIEmailAssistant).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMinimalAIEmailAssistant:
    """Test AI email assistant (classification, fallbacks, extraction, stats)."""

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_init_disabled_when_no_api_key(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        assert assistant.is_enabled() is False

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_classify_email_intent_uses_fallback_when_disabled(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        result = assistant.classify_email_intent("I need a quote for landscaping", "Quote request")
        assert "intent" in result
        assert result["intent"] == "lead_inquiry"
        assert "confidence" in result
        assert "suggested_action" in result

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_classify_email_intent_fallback_support_keywords(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        result = assistant.classify_email_intent("I have a problem with the app", "Help")
        assert result["intent"] == "support_request"
        sug = result.get("suggested_action", "")
        assert "support" in sug.lower() or "escalate" in sug.lower()

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_extract_email_from_content(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        email = assistant._extract_email_from_content("Contact me at john@example.com please")
        assert email == "john@example.com"
        assert assistant._extract_email_from_content("no email here") is None

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_extract_name_from_content(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        # Implementation only extracts from lines with "name:" or "from:"
        name = assistant._extract_name_from_content("Name: Jane Doe")
        assert name == "Jane Doe"
        assert assistant._extract_name_from_content("No name here") == ""

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_generate_reply_uses_fallback_when_disabled(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        reply = assistant.generate_reply("Alice", "Question", email_body="Hello")
        assert "Alice" in reply
        assert "Question" in reply or "regarding" in reply.lower()
        assert "Fikiri" in reply or "team" in reply.lower()

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_extract_contact_info_returns_dict_when_disabled(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        info = assistant.extract_contact_info("Call me at 555-123-4567. Visit https://example.com")
        assert isinstance(info, dict)
        assert "phone" in info or "website" in info or "company" in info

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_get_ai_stats_returns_dict(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        assistant = MinimalAIEmailAssistant(api_key=None)
        stats = assistant.get_ai_stats()
        assert isinstance(stats, dict)
