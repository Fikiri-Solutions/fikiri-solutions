"""
Shared pytest fixtures for Fikiri test suite.
Use these to keep new test files fast and non-flaky (zero setup pain).

Layers:
  - Pure unit tests: use mock_* fixtures only, no app/client.
  - Route tests: use app + client for HTTP contract + auth.
  - Integration: use only for wiring; never call external APIs.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Project root on path and test env before any imports that read FLASK_ENV
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("FLASK_ENV", "test")


class FakeRedis:
    """In-memory Redis stub for unit tests. No real Redis required."""

    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ex=None, px=None):
        self._store[key] = value
        return True

    def setex(self, key, ttl_seconds, value):
        self._store[key] = value
        return True

    def delete(self, key):
        if key in self._store:
            del self._store[key]
        return 1

    def exists(self, key):
        return key in self._store

    def incr(self, key, amount=1):
        self._store[key] = self._store.get(key, 0) + amount
        return self._store[key]


@pytest.fixture
def fake_redis():
    """In-memory Redis stub."""
    return FakeRedis()


@pytest.fixture
def mock_gmail_client():
    """Mock Gmail client for email_automation tests."""
    m = MagicMock()
    m.get_message = MagicMock(return_value=None)
    m.modify_message = MagicMock(return_value=True)
    m.send_message = MagicMock(return_value={"id": "sent_1"})
    m.get_thread = MagicMock(return_value=None)
    return m


@pytest.fixture
def mock_crm_service():
    """Mock CRM service for webhook/lead and route tests."""
    m = MagicMock()
    m.create_lead = MagicMock(return_value={"id": 1, "email": "test@example.com"})
    m.get_lead = MagicMock(return_value=None)
    m.get_leads_summary = MagicMock(return_value={"success": True, "data": {"leads": [], "total_count": 0}})
    m.get_pipeline = MagicMock(return_value={"stages": []})
    return m


@pytest.fixture
def mock_llm_router():
    """Mock LLM router for AI/assistant tests."""
    m = MagicMock()
    m.route = MagicMock(return_value={"reply": "Test reply", "confidence": 0.9})
    m.analyze = MagicMock(return_value={"intent": "inquiry", "summary": ""})
    return m


@pytest.fixture(scope="session")
def _app():
    """Flask app (session-scoped to avoid repeated heavy init)."""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def app(_app):
    """Flask app for route tests."""
    return _app


@pytest.fixture
def client(app):
    """Flask test client for route/contract tests."""
    return app.test_client()


# caplog is built-in in pytest — use it in tests for log assertions, e.g.:
#   def test_foo(caplog): ...
#   with caplog.at_level("ERROR"): ...
