"""Unit tests for CORS_ORIGINS env merge (app.py)."""

import pytest

from app import _merge_cors_origins_from_env


def test_merge_cors_origins_empty_env_returns_copy_of_base(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    base = ["https://a.example"]
    merged = _merge_cors_origins_from_env(base)
    assert merged == ["https://a.example"]
    merged.append("https://b.example")
    assert base == ["https://a.example"]


def test_merge_cors_origins_appends_and_dedupes(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://b.example ,https://c.example, https://a.example ")
    base = ["https://a.example", "https://b.example"]
    merged = _merge_cors_origins_from_env(base)
    assert merged == [
        "https://a.example",
        "https://b.example",
        "https://c.example",
    ]
