"""
Unit tests for core.minimal_config (Core 16 - minimal_config).
"""

import os
import pytest


class TestMinimalConfig:
    def test_defaults(self):
        from core.minimal_config import MinimalConfig
        cfg = MinimalConfig()
        assert isinstance(cfg.gmail_max_results, int)
        assert hasattr(cfg, "debug")
        assert hasattr(cfg, "dry_run")

    def test_is_debug_is_dry_run(self):
        from core.minimal_config import MinimalConfig
        cfg = MinimalConfig()
        assert isinstance(cfg.is_debug(), bool)
        assert isinstance(cfg.is_dry_run(), bool)

    def test_get_gmail_scopes_returns_list(self):
        from core.minimal_config import MinimalConfig
        cfg = MinimalConfig()
        scopes = cfg.get_gmail_scopes()
        assert isinstance(scopes, list)
        assert len(scopes) >= 1


class TestGetConfig:
    def test_returns_minimal_config(self):
        from core.minimal_config import get_config, MinimalConfig
        cfg = get_config()
        assert isinstance(cfg, MinimalConfig)

    def test_same_instance(self):
        from core.minimal_config import get_config
        assert get_config() is get_config()


class TestConstants:
    def test_default_templates_exist(self):
        from core.minimal_config import DEFAULT_REPLY_TEMPLATE, DEFAULT_SIGNATURE
        assert len(DEFAULT_REPLY_TEMPLATE) > 0
        assert "Fikiri" in DEFAULT_SIGNATURE
