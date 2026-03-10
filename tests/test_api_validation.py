"""
Unit tests for core.api_validation (request validation helpers).
Core 16 domain/features - api_validation.
"""

import pytest


class TestValidateEmail:
    def test_valid_emails(self):
        from core.api_validation import validate_email
        assert validate_email("a@b.co") is True
        assert validate_email("user+tag@example.com") is True

    def test_invalid_emails(self):
        from core.api_validation import validate_email
        assert validate_email("") is False
        assert validate_email("no-at") is False
        assert validate_email("a@b") is False


class TestValidatePhone:
    def test_valid_phones(self):
        from core.api_validation import validate_phone
        assert validate_phone("1234567") is True
        assert validate_phone("+1 (555) 123-4567") is True

    def test_invalid_phones(self):
        from core.api_validation import validate_phone
        assert validate_phone("123456") is False


class TestValidatePassword:
    def test_weak_password(self):
        from core.api_validation import validate_password
        out = validate_password("short")
        assert out["valid"] is False

    def test_strong_password(self):
        from core.api_validation import validate_password
        out = validate_password("SecureP@ss1")
        assert out["valid"] is True
        assert out["errors"] == []


class TestValidateRequiredFields:
    def test_all_present(self):
        from core.api_validation import validate_required_fields
        validate_required_fields({"a": 1, "b": "x"}, ["a", "b"])

    def test_missing_raises(self):
        from core.api_validation import validate_required_fields, ValidationError
        with pytest.raises(ValidationError):
            validate_required_fields({"a": 1}, ["a", "b"])


class TestExceptions:
    def test_validation_error(self):
        from core.api_validation import ValidationError
        e = ValidationError("bad input", field="email", code="INVALID")
        assert e.message == "bad input"
        assert e.field == "email"

    def test_api_error(self):
        from core.api_validation import APIError
        e = APIError("forbidden", status_code=403, error_code="FORBIDDEN")
        assert e.message == "forbidden"
        assert e.status_code == 403
