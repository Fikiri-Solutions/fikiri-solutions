#!/usr/bin/env python3
"""
Rate Limiter Unit Tests
Tests for core/rate_limiter.py (check_rate_limit, key generation, fail-open)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestEnhancedRateLimiter(unittest.TestCase):
    def setUp(self):
        with patch("core.rate_limiter.db_optimizer") as mock_db:
            mock_db.execute_query.return_value = None
            from core.rate_limiter import EnhancedRateLimiter, RateLimitResult

            self.limiter = EnhancedRateLimiter()
            self.limiter.redis_client = None  # force DB or in-memory path
            self.RateLimitResult = RateLimitResult

    def test_unknown_limit_name_allowed(self):
        result = self.limiter.check_rate_limit(
            "unknown_limit", "id1", ip_address="127.0.0.1", user_id=1
        )
        self.assertTrue(result.allowed)
        self.assertGreaterEqual(result.remaining, 999999)

    @patch("core.rate_limiter.db_optimizer")
    def test_check_rate_limit_login_attempts_returns_result(self, mock_db):
        mock_db.execute_query.return_value = []  # no existing count
        result = self.limiter.check_rate_limit(
            "login_attempts", "127.0.0.1", ip_address="127.0.0.1"
        )
        self.assertIsInstance(result.allowed, bool)
        self.assertIsInstance(result.remaining, int)
        self.assertIsInstance(result.limit, int)

    def test_default_limits_contain_expected_keys(self):
        self.assertIn("api_global", self.limiter.default_limits)
        self.assertIn("login_attempts", self.limiter.default_limits)
        self.assertIn("api_user", self.limiter.default_limits)

    def test_generate_rate_limit_key_ip_type(self):
        from core.rate_limiter import RateLimit, RateLimitType

        rl = self.limiter.default_limits["api_ip"]
        key = self.limiter._generate_rate_limit_key(
            rl, "id", ip_address="192.168.1.1", user_id=1
        )
        self.assertIn("ip:192.168.1.1", key)

    def test_generate_rate_limit_key_user_type(self):
        from core.rate_limiter import RateLimitType

        rl = self.limiter.default_limits["api_user"]
        key = self.limiter._generate_rate_limit_key(
            rl, "id", ip_address="127.0.0.1", user_id=42
        )
        self.assertIn("user:42", key)

    @patch("core.rate_limiter.db_optimizer")
    def test_database_fallback_tracks_requests_and_blocks(self, mock_db):
        from core.rate_limiter import RateLimit, RateLimitType

        state = {"count": 0}

        def _execute(query, params=None, fetch=True):
            q = " ".join(query.split())
            if "SELECT COUNT(*) as count FROM rate_limit_requests" in q:
                return [{"count": state["count"]}]
            if "INSERT INTO rate_limit_requests" in q:
                state["count"] += 1
                return None
            if "SELECT request_time FROM rate_limit_requests" in q:
                return [{"request_time": datetime.utcnow().isoformat()}]
            return []

        mock_db.execute_query.side_effect = _execute
        rate_limit = RateLimit("test_limit", RateLimitType.CUSTOM, 2, 60)

        first = self.limiter._check_database_rate_limit("rl:key:test", rate_limit)
        second = self.limiter._check_database_rate_limit("rl:key:test", rate_limit)
        third = self.limiter._check_database_rate_limit("rl:key:test", rate_limit)

        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertFalse(third.allowed)
        self.assertEqual(third.remaining, 0)


if __name__ == "__main__":
    unittest.main()
