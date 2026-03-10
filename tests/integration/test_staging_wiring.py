"""Staging wiring integration tests (env-gated)."""

import os

import pytest
import requests


pytestmark = pytest.mark.integration


def _backend_url() -> str:
    return os.getenv("INTEGRATION_BACKEND_URL", "")


def _enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1" and bool(_backend_url())


@pytest.fixture(scope="session")
def backend_url():
    if not _enabled():
        pytest.skip("Integration tests disabled or INTEGRATION_BACKEND_URL not set")
    return _backend_url().rstrip("/")


def test_health_endpoint(backend_url):
    resp = requests.get(f"{backend_url}/api/health", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in {"healthy", "degraded"}


def test_health_old_endpoint(backend_url):
    resp = requests.get(f"{backend_url}/api/health-old", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert data.get("data", {}).get("status") in {"healthy", "degraded", "unhealthy"}
