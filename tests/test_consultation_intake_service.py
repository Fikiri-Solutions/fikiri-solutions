"""Unit tests for short-form consultation intake parsing / notes."""

from core.consultation_intake_service import (
    build_intake_plain_notes,
    derive_lead_priority_band,
    parse_intake_body,
    parse_service_interests_list,
)


def test_parse_intake_body_accepts_service_interest_list():
    parsed = parse_intake_body(
        {
            "contact_name": "Sam",
            "email": "sam@example.com",
            "service_interests": [
                "website_design_development",
                "custom_software_systems",
            ],
            "service_detail": ["new_website", "ecommerce"],
            "preferred_next_step": "Book",
            "main_pain": "Need a new site",
            "project_clarity": "know_exactly",
            "timeline_readiness": "ready_now",
            "budget_readiness": "budget_ready",
            "lead_priority_band": "nurture",  # spoof — server recomputes
        }
    )
    assert parsed["business_name"] == ""
    assert parsed["preferred_next_step"] == "book"
    assert parsed["service_detail"] == "new_website,ecommerce"
    assert parsed["lead_priority_band"] == "priority"
    assert parse_service_interests_list(parsed["service_interests"]) == [
        "website_design_development",
        "custom_software_systems",
    ]


def test_derive_lead_priority_band():
    assert derive_lead_priority_band("know_exactly", "ready_now", "budget_ready") == "priority"
    assert derive_lead_priority_band("exploring", "researching", "not_sure") == "nurture"
    assert derive_lead_priority_band("strong_idea", "ready_now", "not_sure") == "warm"


def test_plain_notes_omit_empty_business_and_include_interests():
    notes = build_intake_plain_notes(
        {
            "business_name": "",
            "contact_name": "Sam",
            "email": "sam@example.com",
            "service_interests": "website_design_development",
            "preferred_next_step": "follow_up",
            "main_pain": "Leads drop",
            "project_clarity": "strong_idea",
            "budget_readiness": "budget_ready",
            "lead_priority_band": "warm",
        }
    )
    assert "Business:" not in notes
    assert "Contact: Sam" in notes
    assert "Service interests: website_design_development" in notes
    assert "Preferred next step: follow_up" in notes
    assert "Main pain: Leads drop" in notes
    assert "Lead priority: warm" in notes
    assert "Budget readiness: budget_ready" in notes
