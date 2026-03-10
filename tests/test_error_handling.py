"""
Unit tests for core.error_handling (Core 16 — error_handling).
FikiriError and subclasses; no Flask/sentry required.
"""

import pytest


class TestFikiriError:
    """FikiriError base."""

    def test_attributes(self):
        from core.error_handling import FikiriError
        e = FikiriError("msg", error_code="ERR", status_code=400)
        assert e.message == "msg"
        assert e.error_code == "ERR"
        assert e.status_code == 400
        assert e.user_message == "msg"
        assert e.error_id
        assert e.timestamp

    def test_user_message_override(self):
        from core.error_handling import FikiriError
        e = FikiriError("internal", user_message="Something went wrong")
        assert e.user_message == "Something went wrong"


class TestValidationError:
    """ValidationError subclass."""

    def test_defaults(self):
        from core.error_handling import ValidationError
        e = ValidationError("invalid email", field="email")
        assert e.error_code == "VALIDATION_ERROR"
        assert e.status_code == 400
        assert e.field == "email"
        assert "input" in e.user_message.lower() or "check" in e.user_message.lower()


class TestAuthenticationError:
    """AuthenticationError subclass."""

    def test_defaults(self):
        from core.error_handling import AuthenticationError
        e = AuthenticationError()
        assert e.error_code == "AUTHENTICATION_ERROR"
        assert e.status_code == 401
        assert "log in" in e.user_message.lower() or "login" in e.user_message.lower()


class TestNotFoundError:
    """NotFoundError subclass."""

    def test_message_includes_resource(self):
        from core.error_handling import NotFoundError
        e = NotFoundError(resource="Lead")
        assert "Lead" in e.message
        assert e.error_code == "NOT_FOUND"
        assert e.status_code == 404


class TestRateLimitError:
    """RateLimitError subclass."""

    def test_defaults(self):
        from core.error_handling import RateLimitError
        e = RateLimitError()
        assert e.status_code == 429
        assert "rate limit" in e.error_code.lower() or "rate" in str(e).lower()


class TestExternalServiceError:
    """ExternalServiceError subclass."""

    def test_message_includes_service(self):
        from core.error_handling import ExternalServiceError
        e = ExternalServiceError("Stripe", "timeout")
        assert "Stripe" in e.message
        assert e.status_code == 502
