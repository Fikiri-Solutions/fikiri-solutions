import json
import time
from pathlib import Path

import pytest
from flask import Flask

import routes.auth as auth_routes
from core.security import require_auth


@pytest.fixture
def auth_client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(auth_routes.auth_bp)

    state = {
        "reset_called": False,
        "metadata": {
            "reset_token": "valid-token",
            "reset_token_expires": int(time.time()) + 3600,
        },
        "active": True,
    }

    class FakeDb:
        def execute_query(self, query, params=(), fetch=True):
            if "json_extract(metadata, '$.reset_token')" in query:
                token = params[0]
                if not state["active"] or token != state["metadata"].get("reset_token"):
                    return []
                return [
                    {
                        "id": 123,
                        "email": "user@example.com",
                        "metadata": json.dumps(state["metadata"]),
                    }
                ]
            raise AssertionError(f"Unexpected query: {query}")

    class FakeUserAuthManager:
        def reset_user_password(self, user_id, new_password):
            assert user_id == 123
            assert new_password == "new-secure-password"
            state["reset_called"] = True
            state["metadata"].pop("reset_token", None)
            state["metadata"].pop("reset_token_expires", None)
            return {"success": True}

    monkeypatch.setattr(auth_routes, "db_optimizer", FakeDb())
    monkeypatch.setattr(auth_routes, "user_auth_manager", FakeUserAuthManager())
    monkeypatch.setattr(auth_routes, "log_security_event", lambda **kwargs: None)

    return app.test_client(), state


def reset_password(client, token="valid-token"):
    return client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "new-secure-password"},
    )


def test_password_reset_valid_token_works(auth_client):
    client, state = auth_client

    response = reset_password(client)

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert state["reset_called"] is True


def test_password_reset_expired_token_fails(auth_client):
    client, state = auth_client
    state["metadata"]["reset_token_expires"] = int(time.time()) - 1

    response = reset_password(client)

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "Invalid or expired reset token"
    assert state["reset_called"] is False


def test_password_reset_inactive_user_fails(auth_client):
    client, state = auth_client
    state["active"] = False

    response = reset_password(client)

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "Invalid or expired reset token"
    assert state["reset_called"] is False


def test_password_reset_token_cleared_after_use(auth_client):
    client, state = auth_client

    response = reset_password(client)

    assert response.status_code == 200
    assert "reset_token" not in state["metadata"]
    assert "reset_token_expires" not in state["metadata"]


def test_legacy_require_auth_hard_fails():
    def protected():
        return "ok"

    with pytest.raises(RuntimeError, match="jwt_required"):
        require_auth(protected)


def test_no_routes_use_legacy_require_auth():
    project_root = Path(__file__).resolve().parents[1]
    matches = []
    ignored_parts = {".git", ".venv", "venv_local", "archive", "__pycache__", "node_modules"}
    for path in project_root.rglob("*.py"):
        if any(part in ignored_parts for part in path.parts):
            continue
        if path == project_root / "core" / "security.py":
            continue
        if path == Path(__file__):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "require_auth" in text:
            matches.append(str(path.relative_to(project_root)))

    assert matches == []


def test_login_never_stores_plaintext_password():
    project_root = Path(__file__).resolve().parents[1]
    login_source = (project_root / "frontend" / "src" / "pages" / "Login.tsx").read_text(
        encoding="utf-8"
    )

    assert "setItem('fikiri-remember-password'" not in login_source
    assert 'setItem("fikiri-remember-password"' not in login_source
    assert "getItem('fikiri-remember-password'" not in login_source
    assert 'getItem("fikiri-remember-password"' not in login_source
