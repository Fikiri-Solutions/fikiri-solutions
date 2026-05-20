"""Authenticated service test endpoint."""

from unittest.mock import patch

import pytest


@pytest.fixture
def client(app):
    return app.test_client()


def test_service_test_unknown_id(client):
    with patch("routes.business.get_current_user_id", return_value=1):
        res = client.post("/api/services/unknown-service/test", json={})
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("success") is False
    assert body.get("error_code") == "UNKNOWN_SERVICE"


def test_service_test_crm(client):
    with patch("routes.business.get_current_user_id", return_value=1), patch(
        "crm.service.enhanced_crm_service.get_leads_summary",
        return_value={"success": True, "data": {"leads": [{"id": 1}], "analytics": {}}},
    ):
        res = client.post("/api/services/crm/test", json={})
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("success") is True
    assert body.get("data", {}).get("leads_count") == 1
