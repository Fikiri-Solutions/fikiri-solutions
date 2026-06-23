import logging
from pathlib import Path

import pytest
from flask import Flask

import routes.auth as auth_routes


@pytest.fixture
def refresh_client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(auth_routes.auth_bp)

    state = {
        "received_tokens": [],
        "mode": "valid",
    }

    class FakeJwtManager:
        def refresh_access_token(self, refresh_token):
            state["received_tokens"].append(refresh_token)
            if state["mode"] == "raises":
                raise RuntimeError(f"boom: {refresh_token}")
            if state["mode"] != "valid" or refresh_token != "valid-refresh-token":
                return None
            return {
                "access_token": "new-access-token",
                "refresh_token": "rotated-refresh-token",
                "expires_in": 1800,
                "token_type": "Bearer",
            }

    monkeypatch.setattr(auth_routes, "get_jwt_manager", lambda: FakeJwtManager())

    return app.test_client(), state


def post_refresh(client, token="valid-refresh-token"):
    return client.post("/api/auth/refresh", json={"refresh_token": token})


def test_valid_refresh_token_returns_rotated_tokens(refresh_client):
    client, state = refresh_client

    response = post_refresh(client)

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["access_token"] == "new-access-token"
    assert body["data"]["refresh_token"] == "rotated-refresh-token"
    assert body["data"]["tokens"]["refresh_token"] == "rotated-refresh-token"
    assert state["received_tokens"] == ["valid-refresh-token"]


@pytest.mark.parametrize("mode", ["invalid", "expired", "reused"])
def test_invalid_expired_or_reused_refresh_token_rejected(refresh_client, mode):
    client, state = refresh_client
    state["mode"] = mode

    response = post_refresh(client)

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "Invalid or expired refresh token"


def test_refresh_token_can_be_sent_as_bearer_refresh_token(refresh_client):
    client, state = refresh_client

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": "Bearer valid-refresh-token"},
        json={},
    )

    assert response.status_code == 200
    assert state["received_tokens"] == ["valid-refresh-token"]


def test_refresh_endpoint_does_not_log_raw_tokens(refresh_client, caplog):
    client, state = refresh_client
    state["mode"] = "raises"
    caplog.set_level(logging.ERROR)

    response = post_refresh(client, "raw-refresh-token-secret")

    assert response.status_code == 500
    assert "raw-refresh-token-secret" not in caplog.text


def test_api_helper_attaches_current_access_token():
    project_root = Path(__file__).resolve().parents[1]
    api_source = (project_root / "frontend" / "src" / "lib" / "api.ts").read_text(
        encoding="utf-8"
    )

    assert "useAuth.getState().accessToken" in api_source
    assert "localStorage.getItem('fikiri-token')" in api_source
    assert "headers.set('Authorization', `Bearer ${accessToken}`)" in api_source


def test_refresh_helper_sends_refresh_token():
    project_root = Path(__file__).resolve().parents[1]
    api_source = (project_root / "frontend" / "src" / "lib" / "api.ts").read_text(
        encoding="utf-8"
    )
    refresh_source = (
        project_root / "frontend" / "src" / "lib" / "withRefresh.ts"
    ).read_text(encoding="utf-8")

    assert "refresh: (refreshToken: string)" in api_source
    assert "refresh_token: refreshToken" in api_source
    assert "authApi.refresh(refreshToken)" in refresh_source
    assert "setRefreshToken(nextRefreshToken)" in refresh_source


def test_password_is_still_not_stored():
    project_root = Path(__file__).resolve().parents[1]
    login_source = (project_root / "frontend" / "src" / "pages" / "Login.tsx").read_text(
        encoding="utf-8"
    )

    assert "setItem('fikiri-remember-password'" not in login_source
    assert 'setItem("fikiri-remember-password"' not in login_source
    assert "getItem('fikiri-remember-password'" not in login_source
    assert 'getItem("fikiri-remember-password"' not in login_source
