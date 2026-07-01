"""Unit tests for company site bot mode detection."""

import os

import pytest

from company_chatbot.config import (
    MODE_ANSWER,
    MODE_CONSULTING,
    MODE_CONTACT,
    MODE_EXPLORE_FIT,
    MODE_FALLBACK,
    MODE_WORKFLOW_AUDIT,
    PRIMARY_MODES,
)
from company_chatbot.modes import detect_mode

os.environ.setdefault("FIKIRI_SITE_BOT_TEST_MODE", "1")


@pytest.mark.parametrize(
    "message,expected",
    [
        ("What is your pricing?", MODE_ANSWER),
        ("How much does Fikiri cost?", MODE_ANSWER),
        ("Is Fikiri right for my business?", MODE_EXPLORE_FIT),
        ("Is Fikiri a fit for my business?", MODE_EXPLORE_FIT),
        ("Good fit for our company?", MODE_EXPLORE_FIT),
        ("I need a workflow audit", MODE_WORKFLOW_AUDIT),
        ("Can you audit my business process?", MODE_WORKFLOW_AUDIT),
        ("Looking for consulting help", MODE_CONSULTING),
        ("Florida SMB implementation", MODE_CONSULTING),
        ("I want to talk to someone", MODE_CONTACT),
        ("I want to talk with your team", MODE_CONTACT),
        ("How do I contact you?", MODE_CONTACT),
        ("I need to find out about the email assisant", MODE_ANSWER),
        ("Im asking about one of the producsts, the AI email assistant", MODE_ANSWER),
        ("Tell me about the AI email assistant", MODE_ANSWER),
        ("email automation assistant", MODE_ANSWER),
        ("Does Fikiri work with Gmail?", MODE_ANSWER),
        ("what is fikiri", MODE_ANSWER),
        ("asdfghjkl qwerty", MODE_FALLBACK),
        ("", MODE_FALLBACK),
        ("   ", MODE_FALLBACK),
        (None, MODE_FALLBACK),
    ],
)
def test_detect_mode(message, expected):
    assert detect_mode(message) == expected


def test_primary_modes_cover_all_handlers():
    assert set(PRIMARY_MODES) == {
        MODE_ANSWER,
        MODE_EXPLORE_FIT,
        MODE_WORKFLOW_AUDIT,
        MODE_CONSULTING,
        MODE_CONTACT,
    }


def test_detect_mode_does_not_crash_on_weird_input():
    assert detect_mode("🚀" * 50) == MODE_FALLBACK
    assert detect_mode("a" * 5000) in set(PRIMARY_MODES) | {MODE_FALLBACK}


@pytest.mark.parametrize(
    "message",
    [
        "I don't know if we need a website or a CRM",
        "restaurant reservations and customer follow-up by email",
        "How can AI help my cleaning business with leads and email?",
        "I need something that follows up automatically",
        "dental clinic needs online booking and payment follow-up",
        "we already have a site we need CRM and intake forms",
        "automate just our quote request workflow nothing else",
        "website form intake CRM and payments",
    ],
)
def test_detect_mode_mixed_scope_business_needs(message):
    assert detect_mode(message) == MODE_ANSWER


def test_detect_mode_gmail_followup_with_context():
    assert (
        detect_mode("What about Gmail?", previous_query="Tell me about the AI email assistant")
        == MODE_ANSWER
    )
