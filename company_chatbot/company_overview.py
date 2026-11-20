"""Shared detectors for basic company / services overview questions."""

from __future__ import annotations

import re

_OVERVIEW_RE = re.compile(
    r"\b("
    r"what do you(?: all)? do|what (?:do )?y'?all do|"
    r"what do you offer|what (?:services|products|solutions) do you (?:offer|have|provide)|"
    r"what services|services do you offer|what products do you have|"
    r"what can you (?:do|help(?: with)?)|what (?:can|does) fikiri (?:do|offer|help)|"
    r"what does fikiri|what (?:is|are) fikiri|who is fikiri|who are you|"
    r"tell me about (?:fikiri|your (?:company|services|products|offerings?))|"
    r"about (?:a |your )?services?|tell me about (?:a |your )?service|"
    r"i just asked what services|just asked what (?:services|products)|"
    r"what (?:services|products) again"
    r")\b",
    re.I,
)

_META_COMPLAINT_RE = re.compile(
    r"\b("
    r"you don'?t understand|you dont understand|don'?t understand|"
    r"not understanding|confused|not helping|isn'?t helping|"
    r"can'?t tell me about|cant tell me about|"
    r"now you'?re responding|responding to anything|"
    r"back to this loop|same (?:thing|loop) again"
    r")\b",
    re.I,
)

OVERVIEW_CHUNK_IDS = (
    "company_three_capabilities",
    "company_about",
    "company_outcomes",
)


def is_company_overview_question(message: str) -> bool:
    return bool(_OVERVIEW_RE.search(message or ""))


def is_meta_conversation_complaint(message: str) -> bool:
    return bool(_META_COMPLAINT_RE.search(message or ""))
