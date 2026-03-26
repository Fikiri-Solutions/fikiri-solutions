"""Launch-focused automation integration checks (env-gated)."""

import os
from typing import Dict
from uuid import uuid4

import pytest
import requests


pytestmark = pytest.mark.integration


def _backend_url() -> str:
    return os.getenv("INTEGRATION_BACKEND_URL", "http://localhost:5000").rstrip("/")


def _enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1" and bool(_backend_url())


def _login(backend_url: str) -> Dict[str, str]:
    email = os.getenv("INTEGRATION_LOGIN_EMAIL", "test@example.com")
    password = os.getenv("INTEGRATION_LOGIN_PASSWORD", "TestPassword123!")

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


def test_automation_email_sheets_webhook_execution(backend_url: str, auth_headers: Dict[str, str]):
    webhook_url = os.getenv("INTEGRATION_WEBHOOK_URL")
    if not webhook_url:
        pytest.skip("INTEGRATION_WEBHOOK_URL not set")

    slug = "email_sheets"
    rule_name = f"int-email-sheets-{uuid4().hex[:10]}"
    create_response = requests.post(
        f"{backend_url}/api/automation/rules",
        headers=auth_headers,
        json={
            "name": rule_name,
            "description": "Integration webhook execution check",
            "trigger_type": "email_received",
            "trigger_conditions": {"slug": slug},
            "action_type": "trigger_webhook",
            "action_parameters": {
                "slug": slug,
                "webhook_url": webhook_url,
                "payload": {"source": "integration_test"},
            },
            "status": "active",
        },
        timeout=20,
    )
    assert create_response.status_code == 200, create_response.text
    created_payload = create_response.json()
    assert created_payload.get("success") is True
    created_rule = created_payload.get("data", {}).get("rule", {})
    created_rule_id = created_rule.get("id")
    assert created_rule_id, "Created rule id missing"

    execute_response = requests.post(
        f"{backend_url}/api/automation/test/preset",
        headers=auth_headers,
        json={"preset_id": slug},
        timeout=30,
    )
    assert execute_response.status_code == 200, execute_response.text
    execute_payload = execute_response.json()
    assert execute_payload.get("success") is True
    execute_data = execute_payload.get("data", {})
    assert execute_data.get("total_executed", 0) >= 1
    assert execute_data.get("total_failed", 0) == 0

    logs_response = requests.get(
        f"{backend_url}/api/automation/logs",
        headers=auth_headers,
        params={"slug": slug, "limit": 20},
        timeout=20,
    )
    assert logs_response.status_code == 200, logs_response.text
    logs_payload = logs_response.json()
    assert logs_payload.get("success") is True
    logs = logs_payload.get("data", {}).get("logs", [])
    assert any(
        log.get("rule_id") == created_rule_id and log.get("status") == "success"
        for log in logs
    ), f"No successful log found for rule {created_rule_id}"
