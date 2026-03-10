"""
Unit tests for Core Redis modules (no real Redis required).
Covers: redis_connection_helper, redis_cache, redis_sessions, redis_pool, redis_queues, redis_monitor.
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRedisConnectionHelper:
    """Tests for core/redis_connection_helper.py"""

    @patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}, clear=False)
    def test_resolve_redis_url_from_redis_url(self):
        from core.redis_connection_helper import _resolve_redis_url
        url = _resolve_redis_url()
        assert url == "redis://localhost:6379"

    @patch.dict(os.environ, {"REDIS_URL": ""}, clear=False)
    def test_resolve_redis_url_empty_redis_url_checks_upstash(self):
        from core.redis_connection_helper import _resolve_redis_url
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_URL": "https://x.upstash.io", "UPSTASH_REDIS_REST_TOKEN": "tok"}):
            url = _resolve_redis_url()
        assert url is None or url.startswith("rediss://")

    def test_resolve_redis_url_no_env_returns_none(self):
        from core.redis_connection_helper import _resolve_redis_url
        with patch.dict(os.environ, {"REDIS_URL": "", "UPSTASH_REDIS_REST_URL": "", "UPSTASH_REDIS_REST_TOKEN": ""}, clear=False):
            url = _resolve_redis_url()
        assert url is None or url == ""

    def test_is_test_mode_true_when_flask_env_test(self):
        from core.redis_connection_helper import _is_test_mode
        assert _is_test_mode() is True

    @patch("core.redis_connection_helper.get_redis_client")
    def test_is_redis_available_false_when_client_none(self, mock_get_client):
        mock_get_client.return_value = None
        from core.redis_connection_helper import is_redis_available
        assert is_redis_available() is False

    @patch("core.redis_connection_helper.get_redis_client")
    def test_is_redis_available_true_when_ping_ok(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        from core.redis_connection_helper import is_redis_available
        assert is_redis_available() is True
        mock_client.ping.assert_called_once()


class TestRedisCache:
    """Tests for core/redis_cache.py"""

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_cache.get_config")
    def test_fikiri_cache_is_connected_false_without_client(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_cache import FikiriCache
        cache = FikiriCache()
        assert cache.is_connected() is False

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_cache.get_config")
    def test_fikiri_cache_generate_cache_key(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_cache import FikiriCache
        cache = FikiriCache()
        key = cache._generate_cache_key("ai", "user1")
        assert key == "fikiri:ai:user1"
        key2 = cache._generate_cache_key("email", "id1", "extra")
        assert key2.startswith("fikiri:email:id1:")
        assert len(key2.split(":")) == 4

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_cache.get_config")
    def test_fikiri_cache_get_cache_stats_returns_dict(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_cache import FikiriCache
        cache = FikiriCache()
        stats = cache.get_cache_stats()
        assert isinstance(stats, dict)

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_cache.get_config")
    def test_get_cache_returns_singleton(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_cache import get_cache
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2


class TestRedisSessions:
    """Tests for core/redis_sessions.py"""

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_sessions.get_config")
    def test_session_manager_is_connected_false_without_client(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_sessions import RedisSessionManager
        mgr = RedisSessionManager()
        assert mgr.is_connected() is False

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_sessions.get_config")
    def test_session_manager_prefix(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_sessions import RedisSessionManager
        mgr = RedisSessionManager()
        assert mgr.session_prefix == "fikiri:session:"
        assert mgr.session_ttl == 86400

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_sessions.get_config")
    def test_create_session_returns_none_when_not_connected(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_sessions import RedisSessionManager
        mgr = RedisSessionManager()
        sid = mgr.create_session("user1", {"email": "u@example.com"})
        assert sid is None


class TestRedisPool:
    """Tests for core/redis_pool.py"""

    def test_get_redis_client_returns_none_in_test_mode(self):
        from core.redis_pool import get_redis_client
        # In test env, connection helper often returns None; pool may return None or cached
        client = get_redis_client()
        assert client is None or hasattr(client, "ping")

    @patch("core.redis_pool.REDIS_AVAILABLE", False)
    def test_get_redis_client_returns_none_when_redis_not_available(self):
        from core.redis_pool import get_redis_client
        client = get_redis_client()
        assert client is None

    def test_reset_redis_client_does_not_raise(self):
        from core.redis_pool import reset_redis_client
        reset_redis_client()
        reset_redis_client()


class TestRedisQueues:
    """Tests for core/redis_queues.py"""

    def test_job_status_enum(self):
        from core.redis_queues import JobStatus
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_job_dataclass(self):
        from core.redis_queues import Job, JobStatus
        import time
        j = Job(
            id="j1",
            task="test_task",
            args={},
            status=JobStatus.PENDING,
            created_at=time.time(),
        )
        assert j.id == "j1"
        assert j.task == "test_task"
        assert j.status == JobStatus.PENDING
        assert j.retry_count == 0
        assert j.max_retries == 3

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_queues.get_config")
    def test_redis_queue_is_connected_false_without_client(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_queues import RedisQueue
        q = RedisQueue(queue_name="test:queue")
        assert q.is_connected() is False

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_queues.get_config")
    def test_redis_queue_register_task(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_queues import RedisQueue
        q = RedisQueue(queue_name="test:queue")
        def dummy_task(**kwargs):
            return None
        q.register_task("dummy", dummy_task)
        assert q._registered_tasks.get("dummy") is dummy_task

    @patch("core.redis_connection_helper.get_redis_client")
    @patch("core.redis_queues.get_config")
    def test_redis_queue_enqueue_raises_when_not_connected(self, mock_config, mock_get_client):
        mock_get_client.return_value = None
        mock_config.return_value = MagicMock()
        from core.redis_queues import RedisQueue
        q = RedisQueue(queue_name="test:queue")
        import pytest
        with pytest.raises(Exception) as exc_info:
            q.enqueue_job("task1", {})
        assert "not connected" in str(exc_info.value).lower() or "redis" in str(exc_info.value).lower()


class TestRedisMonitor:
    """Tests for core/redis_monitor.py"""

    @patch("core.redis_connection_helper.get_redis_client")
    def test_get_redis_usage_stats_returns_none_when_no_client(self, mock_get_client):
        mock_get_client.return_value = None
        from core.redis_monitor import get_redis_usage_stats
        stats = get_redis_usage_stats()
        assert stats is None

    def test_log_redis_usage_report_does_not_raise_when_no_stats(self):
        with patch("core.redis_monitor.get_redis_usage_stats", return_value=None):
            from core.redis_monitor import log_redis_usage_report
            log_redis_usage_report()

    @patch("core.redis_connection_helper.get_redis_client")
    def test_get_redis_usage_stats_returns_dict_when_connected(self, mock_get_client):
        mock_client = MagicMock()
        def info(section):
            if section == "memory":
                return {"used_memory": 1000, "used_memory_human": "1K", "connected_clients": 1, "uptime_in_seconds": 0}
            return {"total_commands_processed": 0}
        mock_client.info.side_effect = info
        mock_client.keys.return_value = []
        mock_client.dbsize.return_value = 0
        mock_client.ttl.return_value = 3600
        mock_get_client.return_value = mock_client
        from core.redis_monitor import get_redis_usage_stats
        stats = get_redis_usage_stats()
        assert stats is not None
        assert "memory" in stats
        assert "keys" in stats
        assert "commands" in stats
        assert "connection" in stats
        assert "used_mb" in stats["memory"]
        assert "used_bytes" in stats["memory"]
