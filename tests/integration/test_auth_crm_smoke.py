"""Auth + CRM smoke integration tests (env-gated)."""

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


def test_login_and_list_leads(backend_url):
    email = os.getenv("INTEGRATION_LOGIN_EMAIL")
    password = os.getenv("INTEGRATION_LOGIN_PASSWORD")
    if not (email and password):
        pytest.skip("INTEGRATION_LOGIN_EMAIL/PASSWORD not set")

    login_resp = requests.post(
        f"{backend_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    token = login_data.get("data", {}).get("access_token") or login_data.get("data", {}).get("tokens", {}).get("access_token")
    assert token

    headers = {"Authorization": f"Bearer {token}"}
    leads_resp = requests.get(f"{backend_url}/api/crm/leads", headers=headers, timeout=15)
    assert leads_resp.status_code in {200, 403, 401}
    if leads_resp.status_code == 200:
        data = leads_resp.json()
        assert data.get("success") is True
        assert "leads" in data.get("data", {})
