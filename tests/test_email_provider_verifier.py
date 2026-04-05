"""DNS MX helper must not raise when dnspython is installed (regression: NameError on dns_resolver)."""

import pytest

from core.email_provider_verifier import check_email_domain_has_mx


def test_check_email_domain_has_mx_returns_dict_without_raising():
    r = check_email_domain_has_mx("gmail.com")
    assert isinstance(r, dict)
    assert "has_mx" in r
    assert r.get("domain") == "gmail.com"
