"""Launch-focused automation integration checks (env-gated)."""

import os
from typing import Dict

import pytest
import requests


pytestmark = pytest.mark.integration


def _backend_url() -> str:
    return os.getenv("INTEGRATION_BACKEND_URL", "").rstrip("/")


def _enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1" and bool(_backend_url())


def _login(backend_url: str) -> Dict[str, str]:
    email = os.getenv("INTEGRATION_LOGIN_EMAIL")
    password = os.getenv("INTEGRATION_LOGIN_PASSWORD")
    if not (email and password):
        pytest.skip("INTEGRATION_LOGIN_EMAIL/PASSWORD not set")

    response = requests.post(
        f"{backend_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert response.status_code == 200
    payload = response.json()
    token = (
        payload.get("data", {}).get("access_token")
        or payload.get("data", {}).get("tokens", {}).get("access_token")
    )
    assert token, "No access token in login response"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def backend_url() -> str:
    if not _enabled():
        pytest.skip("Integration tests disabled or INTEGRATION_BACKEND_URL not set")
    return _backend_url()


@pytest.fixture(scope="session")
def auth_headers(backend_url: str) -> Dict[str, str]:
    return _login(backend_url)


def test_automation_capabilities_schema(backend_url: str, auth_headers: Dict[str, str]):
    response = requests.get(f"{backend_url}/api/automation/capabilities", headers=auth_headers, timeout=15)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True

    capabilities = data.get("data", {}).get("capabilities", [])
    assert isinstance(capabilities, list)
    assert len(capabilities) >= 5

    action_types = {item.get("action_type") for item in capabilities}
    assert "trigger_webhook" in action_types
    assert "send_notification" in action_types


def test_automation_read_endpoints(backend_url: str, auth_headers: Dict[str, str]):
    endpoints = [
        "/api/automation/rules",
        "/api/automation/safety-status",
        "/api/automation/metrics?hours=24",
        "/api/automation/logs?limit=10",
        "/api/automation/queue-stats",
        "/api/automation/suggestions",
    ]

    for endpoint in endpoints:
        response = requests.get(f"{backend_url}{endpoint}", headers=auth_headers, timeout=15)
        assert response.status_code == 200, f"{endpoint} failed: {response.status_code}"
        payload = response.json()
        assert payload.get("success") is True


def test_automation_preset_validation_paths(backend_url: str, auth_headers: Dict[str, str]):
    missing = requests.post(
        f"{backend_url}/api/automation/test/preset",
        json={},
        headers=auth_headers,
        timeout=15,
    )
    assert missing.status_code == 400

    unknown = requests.post(
        f"{backend_url}/api/automation/test/preset",
        json={"preset_id": "unknown_preset"},
        headers=auth_headers,
        timeout=15,
    )
    assert unknown.status_code == 400


def test_automation_execute_guardrails(backend_url: str, auth_headers: Dict[str, str]):
    """
    Route can fail as:
    - 402 when billing plan guardrail blocks execution
    - 400 when request validation runs first (missing rule_ids)
    """
    response = requests.post(
        f"{backend_url}/api/automation/execute",
        json={},
        headers=auth_headers,
        timeout=15,
    )
    assert response.status_code in {400, 402}
