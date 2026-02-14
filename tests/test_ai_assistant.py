#!/usr/bin/env python3
"""AI assistant unit tests."""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_automation import ai_assistant


class TestAIEmailAssistant(unittest.TestCase):
    @patch("email_automation.ai_assistant.LLMRouter")
    def test_classify_intent_uses_llm_router_with_schema(self, mock_router_cls):
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = True
        mock_router.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "intent": "general_info",
                "confidence": 0.9,
                "urgency": "low",
                "suggested_action": "review"
            }),
            "tokens_used": 1
        }
        mock_router_cls.return_value = mock_router

        assistant = ai_assistant.MinimalAIEmailAssistant(api_key="test")
        result = assistant.classify_email_intent("hello", "Hi")

        self.assertEqual(result.get("intent"), "general_info")
        mock_router.process.assert_called_once()
        _, kwargs = mock_router.process.call_args
        self.assertEqual(kwargs.get("output_schema"), ai_assistant.CLASSIFICATION_SCHEMA)
        self.assertEqual(kwargs.get("intent"), "classification")


if __name__ == "__main__":
    unittest.main()
