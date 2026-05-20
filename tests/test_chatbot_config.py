#!/usr/bin/env python3
"""Unit tests for core.chatbot_config."""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_config import (
    ChatbotConfig,
    _apply_partial,
    _sanitize_text,
    load_chatbot_config,
    sanitize_chatbot_config_patch,
)


def test_default_config_loads_without_user():
    cfg = load_chatbot_config(None)
    assert isinstance(cfg, ChatbotConfig)
    assert cfg.business_name == "our business"
    assert cfg.chatbot_name == "Assistant"
    assert cfg.lead_capture_enabled is True


def test_user_metadata_overrides_defaults():
    meta = {
        "chatbot": {
            "businessName": "Acme Corp",
            "chatbotName": "Acme Bot",
            "tone": "friendly",
            "fallbackMessage": "Please contact Acme support.",
            "restrictedTopics": ["legal advice", "medical advice"],
            "secretInternalKey": "must not appear",
        }
    }
    with patch("core.database_optimization.db_optimizer") as mock_db:
        mock_db.execute_query.return_value = [
            {"business_name": "Acme Corp", "metadata": meta}
        ]
        with patch("core.user_services.get_service_settings", return_value={}):
            cfg = load_chatbot_config(42)

    assert cfg.business_name == "Acme Corp"
    assert cfg.chatbot_name == "Acme Bot"
    assert cfg.tone == "friendly"
    assert "Acme support" in cfg.fallback_message
    assert "legal advice" in cfg.restricted_topics
    assert not hasattr(cfg, "secretInternalKey")


def test_oversized_fields_are_sanitized():
    cfg = ChatbotConfig()
    huge = "x" * 2000
    _apply_partial(cfg, {"fallback_message": huge, "tone": huge})
    assert len(cfg.fallback_message) <= 803
    assert len(cfg.tone) <= 203


def test_load_failure_returns_defaults():
    with patch("core.database_optimization.db_optimizer") as mock_db:
        mock_db.execute_query.side_effect = RuntimeError("db down")
        cfg = load_chatbot_config(99)
    assert cfg.business_name == "our business"
    assert cfg.tone == "professional and helpful"


def test_sanitize_text_strips_control_chars():
    assert _sanitize_text("hello\x00world") == "helloworld"


def test_sanitize_patch_rejects_blocked_keys():
    patch, rejected = sanitize_chatbot_config_patch(
        {"tone": "friendly", "systemPrompt": "evil"}
    )
    assert "tone" in patch
    assert "systemPrompt" in rejected


def test_sanitize_patch_camel_case():
    patch, rejected = sanitize_chatbot_config_patch({"businessName": "Acme"})
    assert rejected == []
    assert patch["business_name"] == "Acme"
