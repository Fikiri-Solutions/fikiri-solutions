"""
Unit tests for core.feature_flags (Core 16 — feature_flags).
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

# Skip slow heavy dependency checks in tests
os.environ["SKIP_HEAVY_DEP_CHECKS"] = "true"


class TestFeatureLevel:
    """FeatureLevel enum."""

    def test_levels_exist(self):
        from core.feature_flags import FeatureLevel
        assert FeatureLevel.LIGHTWEIGHT.value == "lightweight"
        assert FeatureLevel.ENHANCED.value == "enhanced"
        assert FeatureLevel.ADVANCED.value == "advanced"
        assert FeatureLevel.FULL_AI.value == "full_ai"


class TestFeatureFlags:
    """FeatureFlags default flags and is_enabled."""

    def test_default_flags_loaded(self):
        from core.feature_flags import FeatureFlags
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nonexistent.json"
            flags = FeatureFlags(config_path=str(path))
            assert "gmail_integration" in flags.flags
            assert "crm_basic" in flags.flags
            assert "vector_search" in flags.flags

    def test_is_enabled_defaults(self):
        from core.feature_flags import FeatureFlags
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "flags.json"
            flags = FeatureFlags(config_path=str(path))
            assert flags.is_enabled("gmail_integration") is True
            assert flags.is_enabled("crm_basic") is True
            assert flags.is_enabled("advanced_nlp") is False
            assert flags.is_enabled("nonexistent_flag") is False

    def test_get_level(self):
        from core.feature_flags import FeatureFlags, FeatureLevel
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "flags.json"
            flags = FeatureFlags(config_path=str(path))
            assert flags.get_level("gmail_integration") == FeatureLevel.LIGHTWEIGHT
            # With SKIP_HEAVY_CHECKS, ai_email_responses is downgraded to LIGHTWEIGHT
            assert flags.get_level("ai_email_responses") in (
                FeatureLevel.LIGHTWEIGHT,
                FeatureLevel.ENHANCED,
            )
            assert flags.get_level("nonexistent") == FeatureLevel.LIGHTWEIGHT

    def test_load_config_overrides(self):
        from core.feature_flags import FeatureFlags
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "flags.json"
            path.write_text(json.dumps({"gmail_integration": {"enabled": False}}))
            flags = FeatureFlags(config_path=str(path))
            assert flags.is_enabled("gmail_integration") is False
