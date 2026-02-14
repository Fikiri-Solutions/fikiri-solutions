#!/usr/bin/env python3
"""
Idempotency Manager Unit Tests
Tests for core/idempotency_manager.py (generate_key, check_key, store_key, update_key_result)
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestIdempotencyManager(unittest.TestCase):
    def setUp(self):
        with patch("core.idempotency_manager.db_optimizer") as mock_db:
            mock_db.execute_query.return_value = None
            from core.idempotency_manager import IdempotencyManager

            self.manager = IdempotencyManager()
            self.manager.redis_client = None

    def test_generate_key_returns_hex_hash(self):
        key = self.manager.generate_key("test_op", user_id=1, request_data={"a": 1})
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in key))

    def test_generate_key_different_inputs_different_keys(self):
        k1 = self.manager.generate_key("op", user_id=1)
        k2 = self.manager.generate_key("op", user_id=2)
        self.assertNotEqual(k1, k2)

    def test_check_key_missing_returns_none(self):
        with patch("core.idempotency_manager.db_optimizer") as mock_db:
            mock_db.execute_query.return_value = []
            result = self.manager.check_key("nonexistent_key_hash")
        self.assertIsNone(result)

    @patch("core.idempotency_manager.db_optimizer")
    def test_store_key_returns_true(self, mock_db):
        mock_db.execute_query.return_value = None
        ok = self.manager.store_key(
            "keyhash123", "create_lead", user_id=1, request_data={"email": "a@b.com"}
        )
        self.assertTrue(ok)

    @patch("core.idempotency_manager.db_optimizer")
    def test_update_key_result_returns_true(self, mock_db):
        mock_db.execute_query.return_value = None
        ok = self.manager.update_key_result(
            "keyhash123", "completed", response_data={"id": 1}
        )
        self.assertTrue(ok)

    @patch("core.idempotency_manager.db_optimizer")
    def test_check_key_returns_cached_result_from_db(self, mock_db):
        mock_db.execute_query.return_value = [
            {
                "id": 1,
                "key_hash": "abc",
                "operation_type": "create_lead",
                "user_id": 1,
                "request_data": "{}",
                "response_data": json.dumps({"id": 1}),
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "expires_at": "2025-01-01T00:00:00",
                "metadata": "{}",
            }
        ]
        result = self.manager.check_key("abc")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["response_data"], {"id": 1})


if __name__ == "__main__":
    unittest.main()
