"""
Unit tests for core/ai/llm_client.py (LLMClient).
"""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.llm_client import LLMClient


class TestLLMClient:
    def test_init_test_mode_disabled(self):
        client = LLMClient(api_key="sk-test")
        assert client.enabled is False
        assert client.is_enabled() is False

    def test_init_no_api_key_disabled(self):
        with patch.dict(os.environ, {"FIKIRI_TEST_MODE": "0", "OPENAI_API_KEY": ""}, clear=False):
            client = LLMClient(api_key=None)
        assert client.enabled is False

    def test_call_llm_when_not_enabled_returns_structure(self):
        client = LLMClient(api_key=None)
        result = client.call_llm(model="gpt-3.5-turbo", prompt="Hello")
        assert result["success"] is False
        assert result["content"] == ""
        assert result["tokens_used"] == 0
        assert result["cost_usd"] == 0.0
        assert "error" in result
        assert "trace_id" in result
        assert result["model"] == "gpt-3.5-turbo"

    def test_call_llm_bounds_temperature_and_max_tokens(self):
        client = LLMClient(api_key=None)
        result = client.call_llm(
            model="gpt-3.5-turbo",
            prompt="Hi",
            max_tokens=99999,
            temperature=5.0,
        )
        assert result["success"] is False
        # Internal bounds: temperature 0-2, max_tokens 1-4000 (only applied when enabled; we just check no crash)

    def test_calculate_cost_gpt35(self):
        client = LLMClient(api_key=None)
        cost = client._calculate_cost("gpt-3.5-turbo", 1000)
        assert isinstance(cost, float)
        assert cost >= 0
        assert cost < 0.01

    def test_calculate_cost_gpt4(self):
        client = LLMClient(api_key=None)
        cost = client._calculate_cost("gpt-4", 1000)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_calculate_cost_unknown_model_uses_default(self):
        client = LLMClient(api_key=None)
        cost = client._calculate_cost("unknown-model", 100)
        assert isinstance(cost, float)
        assert cost >= 0
