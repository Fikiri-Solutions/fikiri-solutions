"""Gmail contract tests (sandbox creds required)."""

import os
import time

import pytest

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None


def _client_id():
    return os.getenv("GMAIL_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")


def _client_secret():
    return os.getenv("GMAIL_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")


def _refresh_token():
    return os.getenv("GMAIL_REFRESH_TOKEN") or os.getenv("GOOGLE_REFRESH_TOKEN")


def _skip_if_missing_env():
    if os.getenv("GMAIL_CONTRACT_ACCESS_TOKEN"):
        return False
    if _client_id() and _client_secret() and _refresh_token():
        return False
    return True


def _missing_creds_reason():
    """One-line reason for skip (no secret values)."""
    if os.getenv("GMAIL_CONTRACT_ACCESS_TOKEN"):
        return None
    missing = []
    if not _client_id():
        missing.append("client_id (GMAIL_OAUTH_CLIENT_ID or GOOGLE_CLIENT_ID)")
    if not _client_secret():
        missing.append("client_secret (GMAIL_OAUTH_CLIENT_SECRET or GOOGLE_CLIENT_SECRET)")
    if not _refresh_token():
        missing.append("refresh_token (GMAIL_REFRESH_TOKEN or GOOGLE_REFRESH_TOKEN)")
    return "missing: " + ", ".join(missing) if missing else None


def _get_access_token():
    token = os.getenv("GMAIL_CONTRACT_ACCESS_TOKEN")
    if token:
        return token
    client_id = _client_id()
    client_secret = _client_secret()
    refresh_token = _refresh_token()
    if not (client_id and client_secret and refresh_token):
        return None
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("access_token")


@pytest.mark.contract
def test_gmail_token_refresh_or_access():
    if requests is None or _skip_if_missing_env():
        reason = _missing_creds_reason() or "requests not installed"
        pytest.skip(f"Gmail contract creds not configured ({reason})")

    token = _get_access_token()
    assert token, "Expected access token from refresh or env"


@pytest.mark.contract
def test_gmail_list_messages_and_basic_modify():
    if requests is None or _skip_if_missing_env():
        reason = _missing_creds_reason() or "requests not installed"
        pytest.skip(f"Gmail contract creds not configured ({reason})")

    token = _get_access_token()
    assert token

    headers = {"Authorization": f"Bearer {token}"}
    query = os.getenv("GMAIL_CONTRACT_QUERY", "")
    params = {"maxResults": 1}
    if query:
        params["q"] = query

    resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers,
        params=params,
        timeout=15,
    )
    assert resp.status_code == 200
    data = resp.json()
    messages = data.get("messages") or []

    if not messages:
        pytest.skip("No messages found for contract account")

    msg_id = os.getenv("GMAIL_CONTRACT_MESSAGE_ID") or messages[0].get("id")
    if not msg_id:
        pytest.skip("No message id available for modify test")

    # Add and then remove STARRED label to validate modify works.
    modify_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify"
    add_payload = {"addLabelIds": ["STARRED"], "removeLabelIds": []}
    add_resp = requests.post(modify_url, headers=headers, json=add_payload, timeout=15)
    assert add_resp.status_code == 200

    # Small delay to avoid immediate rate limits
    time.sleep(0.2)

    remove_payload = {"addLabelIds": [], "removeLabelIds": ["STARRED"]}
    remove_resp = requests.post(modify_url, headers=headers, json=remove_payload, timeout=15)
    assert remove_resp.status_code == 200


@pytest.mark.contract
def test_gmail_invalid_token_returns_401():
    if requests is None:
        pytest.skip("requests not available")

    headers = {"Authorization": "Bearer invalid"}
    resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers,
        params={"maxResults": 1},
        timeout=10,
    )
    assert resp.status_code in (401, 403)
