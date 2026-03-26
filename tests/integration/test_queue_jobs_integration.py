"""Queue/job wiring integration checks (env-gated)."""

import os

import pytest
import requests


pytestmark = pytest.mark.integration


def _backend_url() -> str:
    return os.getenv("INTEGRATION_BACKEND_URL", "http://localhost:5000").rstrip("/")


def _enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1" and bool(_backend_url())


def _login_headers(backend_url: str):
    email = os.getenv("INTEGRATION_LOGIN_EMAIL", "test@example.com")
    password = os.getenv("INTEGRATION_LOGIN_PASSWORD", "TestPassword123!")
    resp = requests.post(
        f"{backend_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        return {}
    payload = resp.json()
    token = payload.get("data", {}).get("access_token") or payload.get("data", {}).get("tokens", {}).get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _headers(backend_url: str):
    token = os.getenv("INTEGRATION_AUTH_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return _login_headers(backend_url)


@pytest.fixture(scope="session")
def backend_url():
    if not _enabled():
        pytest.skip("Integration tests disabled or INTEGRATION_BACKEND_URL not set")
    return _backend_url()


def test_gmail_sync_job_queue_flow(backend_url):
    user_id = os.getenv("INTEGRATION_GMAIL_SYNC_USER_ID")
    expected = os.getenv("INTEGRATION_GMAIL_SYNC_EXPECT", "oauth_required")
    payload = {"user_id": int(user_id)} if user_id else {}
    headers = _headers(backend_url)
    if not headers:
        pytest.skip("Could not obtain integration auth token from env or login")

    resp = requests.post(
        f"{backend_url}/api/crm/sync-gmail",
        json=payload,
        headers=headers,
        timeout=15,
    )

    if expected == "queued":
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("data", {}).get("sync_job_queued") is True
    elif expected == "oauth_required":
        assert resp.status_code == 403
        data = resp.json()
        assert data.get("code") in {"OAUTH_REQUIRED", "GMAIL_NOT_CONNECTED"}
    else:
        pytest.fail("INTEGRATION_GMAIL_SYNC_EXPECT must be 'queued' or 'oauth_required'")
