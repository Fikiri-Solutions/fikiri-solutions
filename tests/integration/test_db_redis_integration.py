"""DB/Redis integration checks via health endpoints (env-gated)."""

import os

import pytest
import requests


pytestmark = pytest.mark.integration


def _backend_url() -> str:
    return os.getenv("INTEGRATION_BACKEND_URL", "").rstrip("/")


def _enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1" and bool(_backend_url())


@pytest.fixture(scope="session")
def backend_url():
    if not _enabled():
        pytest.skip("Integration tests disabled or INTEGRATION_BACKEND_URL not set")
    return _backend_url()


def test_health_old_db_redis_status(backend_url):
    resp = requests.get(f"{backend_url}/api/health-old", timeout=10)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    checks = data.get("checks", {})

    assert "database" in checks
    assert "redis" in checks

    db_status = checks["database"].get("status")
    redis_status = checks["redis"].get("status")

    assert db_status in {"healthy", "degraded", "unhealthy"}
    assert redis_status in {"healthy", "degraded", "unhealthy"}

    if os.getenv("INTEGRATION_REQUIRE_HEALTHY") == "1":
        assert db_status == "healthy"
        assert redis_status == "healthy"
