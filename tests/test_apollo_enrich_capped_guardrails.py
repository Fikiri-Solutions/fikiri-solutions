"""Regression: enrich_capped must not spend without confirm, and must hard-cap."""

from f.apollo.enrich_capped import HARD_MAX_PEOPLE, main


def test_enrich_refuses_without_confirm():
    result = main(api_key="your-test-key", people=[{"name": "Ada"}], confirm=False)
    assert result["skipped"] is True
    assert result["enriched"] == []
    assert result["credits_spent_estimate"] == 0


def test_hard_max_people_constant():
    assert HARD_MAX_PEOPLE == 5
