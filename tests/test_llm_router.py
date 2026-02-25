"""
Unit tests for core/ai/llm_router.py (LLMRouter).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.llm_router import LLMRouter


class TestLLMRouterPipelineMethods:
    def test_preprocess_normalizes_whitespace(self):
        router = LLMRouter(api_key=None)
        out = router.preprocess("  hello   world  \n  ", None)
        assert out == "hello world"

    def test_preprocess_adds_context(self):
        router = LLMRouter(api_key=None)
        out = router.preprocess("hi", {"context": "user_id=1"})
        assert "hi" in out and "user_id=1" in out

    def test_preprocess_truncates_long_input(self):
        router = LLMRouter(api_key=None)
        long_text = "x" * 10000
        out = router.preprocess(long_text, None)
        assert len(out) <= 8015 and "[truncated]" in out

    def test_detect_intent_email_reply(self):
        router = LLMRouter(api_key=None)
        assert router.detect_intent("please reply to this email") == "email_reply"

    def test_detect_intent_classification(self):
        router = LLMRouter(api_key=None)
        assert router.detect_intent("classify this") == "classification"

    def test_detect_intent_general(self):
        router = LLMRouter(api_key=None)
        assert router.detect_intent("hello world") == "general"

    def test_choose_model_returns_dict(self):
        router = LLMRouter(api_key=None)
        config = router.choose_model("email_reply", None, None)
        assert "model" in config and "max_tokens" in config and "temperature" in config

    def test_postprocess_strips_quotes(self):
        router = LLMRouter(api_key=None)
        out = router.postprocess('  "quoted text"  ', "general", None)
        assert out == "quoted text"


class TestLLMRouterProcess:
    @patch("core.ai.llm_router.LLMClient")
    def test_process_returns_failure_when_llm_fails(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.call_llm.return_value = {
            "success": False, "content": "", "error": "API error",
            "latency_ms": 100, "tokens_used": 0, "cost_usd": 0.0,
        }
        mock_client_class.return_value = mock_client
        router = LLMRouter(api_key=None)
        router.client = mock_client
        result = router.process("Hello", intent="general")
        assert result["success"] is False and result["validated"] is False

    @patch("core.ai.llm_router.LLMClient")
    def test_process_success_when_no_schema_validated_true(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.call_llm.return_value = {
            "success": True, "content": "Hi", "tokens_used": 10,
            "cost_usd": 0.0001, "latency_ms": 50,
        }
        mock_client_class.return_value = mock_client
        router = LLMRouter(api_key=None)
        router.client = mock_client
        result = router.process("Hello", intent="general")
        assert result["success"] is True and result["validated"] is True
