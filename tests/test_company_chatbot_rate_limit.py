"""Unit tests for company site bot rate limiting."""

import os

import pytest

from company_chatbot import config
from company_chatbot.rate_limit import (
    check_message_limits,
    check_session_start_limits,
    clear_rate_limits_for_tests,
)

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.fixture(autouse=True)
def _reset_limits():
    clear_rate_limits_for_tests()
    yield
    clear_rate_limits_for_tests()


def test_rate_limit_defaults():
    assert config.rate_limit_per_minute() == 20
    assert config.rate_limit_burst() == 40


def test_rate_limit_allows_requests_under_limit():
    for _ in range(5):
        result = check_session_start_limits("203.0.113.10")
        assert result.allowed is True


def test_rate_limit_blocks_requests_over_limit(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_BURST", "2")

    assert check_message_limits("203.0.113.11", "site_burst").allowed is True
    assert check_message_limits("203.0.113.11", "site_burst").allowed is True
    blocked = check_message_limits("203.0.113.11", "site_burst")
    assert blocked.allowed is False
    assert blocked.retry_after_seconds >= 1


def test_session_start_limit_is_independent_from_message_limit(monkeypatch):
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("FIKIRI_SITE_BOT_RATE_LIMIT_BURST", "1")

    assert check_session_start_limits("203.0.113.20").allowed is True
    assert check_session_start_limits("203.0.113.20").allowed is False

    clear_rate_limits_for_tests()
    assert check_message_limits("203.0.113.21", "site_scope_a").allowed is True
    assert check_message_limits("203.0.113.22", "site_scope_b").allowed is True
