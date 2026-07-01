"""Mode constants and lightweight deterministic detector."""

import re
from typing import Dict, List, Pattern, Tuple

from company_chatbot.config import (
    MODE_ANSWER,
    MODE_CONSULTING,
    MODE_CONTACT,
    MODE_EXPLORE_FIT,
    MODE_FALLBACK,
    MODE_WORKFLOW_AUDIT,
)
from company_chatbot.retrieval import normalize_query_text

ModeRule = Tuple[str, Pattern[str]]

_EMAIL_ASSISTANT_RE = re.compile(
    r"\b(?:ai )?email (?:automation )?assistant\b|"
    r"\b(?:find out|learn|asking) about (?:the |one of the )?(?:ai )?email\b|"
    r"\b(?:products?|product).{0,48}(?:ai )?email assistant\b|"
    r"\bemail automation assistant\b",
    re.I,
)

_MIXED_SCOPE_ANSWER_RE = re.compile(
    r"i need a website but also|can customers book|book and pay online|"
    r"(?:emails|email).{0,32}(?:follow|lead)|follow-?ups connected|"
    r"chatbot that answers|captures leads|"
    r"only need one small workflow|"
    r"(?:we have )?forms but nobody|people fill out the form|"
    r"leads in one place|emails and leads|"
    r"intake form.{0,32}(?:crm|email)|website.{0,32}(?:track|quote)|"
    r"request quotes.{0,40}tracked|"
    r"chatbot.{0,24}(?:knowledge|answer)|booking flow|"
    r"automate my appointment|quote requests keep|"
    r"crm and email|small team needs crm|"
    r"payments?.{0,24}(?:customer|reminder)|"
    r"keep track of clients|track leads|"
    r"one quote workflow|email assistant plus|"
    r"don'?t know if we need|website or (?:a )?crm|"
    r"restaurant reservations|cleaning business|"
    r"follows? up automatically|follow-?up automatically|"
    r"dental clinic|online booking and payment|"
    r"already have a site.{0,24}(?:crm|intake)|"
    r"quote request workflow|website form intake",
    re.I,
)

_VAGUE_OFFICE_RE = re.compile(
    r"i don'?t know what i need|office is messy|my office is a mess|"
    r"office is a mess with leads",
    re.I,
)

_MODE_RULES: List[ModeRule] = [
    (
        MODE_CONTACT,
        re.compile(
            r"\b(talk (?:to|with) (?:someone|a human|sales|support|your team|the team)|"
            r"contact(?:\s+us)?|speak with|call me|email me|get in touch|human agent)\b",
            re.I,
        ),
    ),
    (
        MODE_WORKFLOW_AUDIT,
        re.compile(
            r"\b(workflow audit|process audit|operations audit|"
            r"audit (?:my|our) (?:business|workflow|process)|"
            r"can you audit|audit our workflow|free audit|"
            r"i(?:'d| would) like a workflow audit|i want a workflow audit)\b",
            re.I,
        ),
    ),
    (
        MODE_CONSULTING,
        re.compile(
            r"\b(consulting|implementation help|custom (build|project)|"
            r"florida smb|done[- ]for[- ]you|professional services|"
            r"need a quote|help automate)\b",
            re.I,
        ),
    ),
    (
        MODE_EXPLORE_FIT,
        re.compile(
            r"\b(is fikiri (?:right|good|a fit)|"
            r"(?:a )?good fit|fit for (?:my|our) (?:business|company|team)|"
            r"right for (?:my|our) (?:business|company)|"
            r"should we use fikiri|fit for us|explore fit|fit check|"
            r"i need help with my business|talk about my process)\b",
            re.I,
        ),
    ),
    (
        MODE_ANSWER,
        re.compile(
            r"\b(hipaa|soc\s*2|case stud(?:y|ies)|certified|compliance|guarantee)\b",
            re.I,
        ),
    ),
    (
        MODE_ANSWER,
        re.compile(
            r"\b(pricing|price|cost|how much|free trial|features?|"
            r"what do you (do|offer)|what does fikiri|what (?:is|are) fikiri|who is fikiri|"
            r"tell me about fikiri|integrations?|faq|hours|"
            r"gmail|outlook|google workspace|microsoft 365|"
            r"email automation|how does email|automation|"
            r"i(?:'m| am) drowning in emails|too many emails|automate my inbox|"
            r"do y'?all do gmail|gmail stuff|reply to emails|"
            r"can (?:this|you).{0,24}(?:help|track|automate)|"
            r"i need (?:help|something).{0,24}(?:follow|email|customer|lead|inbox)|"
            r"(?:help|need).{0,16}(?:managing|track) customers|"
            r"something like a crm|incoming leads system|"
            r"tell me about (?:crm|the ai email)|"
            r"slipping through the cracks|stop missing leads|nobody follows up)\b",
            re.I,
        ),
    ),
    (MODE_ANSWER, _MIXED_SCOPE_ANSWER_RE),
    (MODE_ANSWER, _VAGUE_OFFICE_RE),
    (MODE_ANSWER, _EMAIL_ASSISTANT_RE),
]


def _normalize_mode_text(text: str) -> str:
    return normalize_query_text(text)


_BUSINESS_NEED_RE = re.compile(
    r"\b(i need|we need|we already|how can|don'?t know|not sure|can customers|"
    r"restaurant reservations|dental clinic|website form|intake crm|"
    r"quote request workflow|cleaning business|something that follows|"
    r"automate just|website or|need a site|need a form|"
    r"can you make|books appointments|stop losing|book and remind)\b",
    re.I,
)

_MIN_NEEDS_CONFIDENCE_FOR_ANSWER = 0.35


def _needs_imply_answer(message: str, previous_query: str | None = None) -> bool:
    """Mixed-scope business needs: let capability map route to answer, not fallback."""
    if not _BUSINESS_NEED_RE.search(message):
        return False
    from company_chatbot.capabilities import detect_needs

    needs = detect_needs(message, previous_query=previous_query)
    return bool(needs.detected_families) and needs.confidence >= _MIN_NEEDS_CONFIDENCE_FOR_ANSWER


def detect_mode(message: str, previous_query: str | None = None) -> str:
    """Return the first matching primary mode, else fallback."""
    text = (message or "").strip()
    if not text:
        return MODE_FALLBACK

    for candidate in (text, _normalize_mode_text(text)):
        for mode, pattern in _MODE_RULES:
            if pattern.search(candidate):
                return mode

    if _needs_imply_answer(text, previous_query):
        return MODE_ANSWER
    return MODE_FALLBACK


def mode_labels() -> Dict[str, str]:
    return {
        MODE_ANSWER: "answer",
        MODE_EXPLORE_FIT: "explore_fit",
        MODE_WORKFLOW_AUDIT: "workflow_audit",
        MODE_CONSULTING: "consulting",
        MODE_CONTACT: "contact",
        MODE_FALLBACK: "fallback",
    }
