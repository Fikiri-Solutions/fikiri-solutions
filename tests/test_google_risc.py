"""Unit tests for Google Cross-Account Protection (RISC) handling."""

import json
from unittest.mock import patch


def test_double_sha512_b64_stable():
    from core.google_risc import _double_sha512_b64

    a = _double_sha512_b64("refresh-token-example")
    b = _double_sha512_b64("refresh-token-example")
    assert a == b
    assert len(a) > 0


def test_resolve_user_id_from_google_sub():
    from core import google_risc as gr

    fake_rows = [
        {"id": 7, "metadata": json.dumps({"google_sub": "sub-abc"})},
        {"id": 8, "metadata": json.dumps({"google_sub": "other"})},
    ]
    with patch.object(gr.db_optimizer, "execute_query", return_value=fake_rows):
        assert gr.resolve_user_id_from_google_sub("sub-abc") == 7
        assert gr.resolve_user_id_from_google_sub("missing") is None


def test_handle_events_verification_logs():
    from core import google_risc as gr

    decoded = {
        "jti": "evt-1",
        "events": {
            gr.EVENT_VERIFICATION: {"state": "ping"},
        },
    }
    with patch.object(gr, "_jti_first_seen", return_value=True):
        gr._handle_events_payload(decoded)


def test_webhook_disabled_returns_404():
    from flask import Flask

    from routes.google_risc import google_risc_bp

    app = Flask(__name__)
    app.register_blueprint(google_risc_bp)
    app.config["TESTING"] = True

    with patch("routes.google_risc.is_risc_enabled", return_value=False):
        c = app.test_client()
        rv = c.post("/api/webhooks/google/risc", data="token")
        assert rv.status_code == 404


def test_webhook_enabled_accepts_valid_token():
    from flask import Flask

    from routes.google_risc import google_risc_bp

    app = Flask(__name__)
    app.register_blueprint(google_risc_bp)

    with patch("routes.google_risc.is_risc_enabled", return_value=True):
        with patch(
            "routes.google_risc.process_security_event_token_string",
            return_value=(True, None),
        ) as proc:
            c = app.test_client()
            rv = c.post("/api/webhooks/google/risc", data="jwt-here")
            assert rv.status_code == 202
            proc.assert_called_once()


def test_webhook_400_on_invalid_token():
    from flask import Flask

    from routes.google_risc import google_risc_bp

    app = Flask(__name__)
    app.register_blueprint(google_risc_bp)

    with patch("routes.google_risc.is_risc_enabled", return_value=True):
        with patch(
            "routes.google_risc.process_security_event_token_string",
            return_value=(False, "invalid token"),
        ):
            c = app.test_client()
            rv = c.post("/api/webhooks/google/risc", data="bad")
            assert rv.status_code == 400
            body = rv.get_json()
            assert body.get("error") == "invalid token"


def test_process_token_skips_side_effects_on_duplicate_jti():
    from core import google_risc as gr

    payload = {"jti": "dup", "events": {}}
    with patch.object(gr, "validate_security_event_token", return_value=payload):
        with patch.object(gr, "_jti_first_seen", return_value=False):
            with patch.object(gr, "_handle_events_payload") as h:
                ok, err = gr.process_security_event_token_string("x.y.z")
                assert ok is True
                assert err is None
                h.assert_not_called()
