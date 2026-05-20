"""Unit tests for inbox search query helpers."""

from core.email_inbox_search import (
    gmail_inbox_list_query,
    sanitize_inbox_search_query,
    synced_inbox_search_sql_and_params,
)


class TestSanitizeInboxSearchQuery:
    def test_strips_and_bounds(self):
        assert sanitize_inbox_search_query("  Florida Atlantic  ") == "Florida Atlantic"
        assert sanitize_inbox_search_query("a" * 300) is not None
        assert len(sanitize_inbox_search_query("a" * 300)) == 200

    def test_empty_returns_none(self):
        assert sanitize_inbox_search_query("") is None
        assert sanitize_inbox_search_query("   ") is None


class TestGmailInboxListQuery:
    def test_inbox_with_search(self):
        q = gmail_inbox_list_query("all", "Florida Atlantic University")
        assert q == "in:inbox Florida Atlantic University"

    def test_unread_with_search(self):
        q = gmail_inbox_list_query("unread", "fau.edu")
        assert q == "in:inbox is:unread fau.edu"

    def test_read_with_search(self):
        q = gmail_inbox_list_query("read", "Florida Atlantic University")
        assert q == "in:inbox is:read Florida Atlantic University"

    def test_fau_phrase_inbox_all(self):
        q = gmail_inbox_list_query("all", "Florida Atlantic University")
        assert q == "in:inbox Florida Atlantic University"


class TestSyncedInboxSearchSql:
    def test_no_search_returns_empty(self):
        sql, params = synced_inbox_search_sql_and_params(None)
        assert sql == ""
        assert params == ()

    def test_search_returns_like_clause(self):
        sql, params = synced_inbox_search_sql_and_params("FAU")
        assert "LIKE" in sql
        assert params == ("%FAU%", "%FAU%", "%FAU%", "%FAU%")
