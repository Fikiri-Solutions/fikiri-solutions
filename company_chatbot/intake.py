"""Short deterministic intake flow for the Fikiri site bot."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from company_chatbot import config

INTAKE_MODES = frozenset(
    {
        config.MODE_EXPLORE_FIT,
        config.MODE_WORKFLOW_AUDIT,
        config.MODE_CONSULTING,
    }
)

CORE_SLOTS = ("industry", "main_pain", "timeline", "contact_email")
OPTIONAL_SLOTS = ("name", "business_name")

SLOT_QUESTIONS: Dict[str, str] = {
    "industry": "What industry is your business in?",
    "main_pain": "What's the main bottleneck you're trying to fix?",
    "timeline": "What's your timeline — urgent, this quarter, or flexible?",
    "contact_email": (
        "What's the best email to follow up? "
        "You can also continue at fikirisolutions.com/intake without sharing email here."
    ),
}

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_REFUSE_EMAIL_RE = re.compile(
    r"\b(no email|won'?t share|without email|skip email|prefer not to share)\b",
    re.I,
)
_TIMELINE_RE = re.compile(
    r"\b(asap|urgent|this week|this month|this quarter|next quarter|"
    r"soon|flexible|no rush|immediately|right away)\b",
    re.I,
)
_PAIN_RE = re.compile(
    r"\b(bottleneck|pain|problem|struggle|leak|manual|slow|missed leads?|"
    r"follow(?:ing)? up|follow-?up|leads?|quotes?|scheduling|marketing|"
    r"chaos|overwhelm|inefficient|waste time|inbox|email)\b",
    re.I,
)

_INDUSTRY_SKIP_RE = re.compile(
    r"\b(workflow audit|fit check|consulting|quote|automation help|explore fit)\b",
    re.I,
)

_INDUSTRY_HINTS = {
    "landscaping": "landscaping",
    "restaurant": "restaurant",
    "dental": "dental",
    "medical": "medical",
    "construction": "construction",
    "logistics": "logistics",
    "transportation": "transportation",
    "real estate": "real estate",
    "hvac": "hvac",
    "cleaning": "cleaning",
    "insurance": "insurance",
    "retail": "retail",
    "saas": "saas",
    "msp": "managed it",
}


@dataclass
class IntakeSlots:
    industry: str = ""
    main_pain: str = ""
    timeline: str = ""
    contact_email: str = ""
    name: str = ""
    business_name: str = ""
    email_declined: bool = False

    def to_dict(self) -> Dict[str, str]:
        data = {slot: getattr(self, slot) for slot in CORE_SLOTS + OPTIONAL_SLOTS}
        data["email_declined"] = self.email_declined
        return data


@dataclass
class IntakeTurnResult:
    response: str
    complete: bool
    next_slot: Optional[str] = None
    slots: IntakeSlots = field(default_factory=IntakeSlots)


def should_start_intake(mode: str) -> bool:
    return mode in INTAKE_MODES


def slot_satisfied(slots: IntakeSlots, slot: str) -> bool:
    if slot == "contact_email":
        return bool(slots.contact_email) or slots.email_declined
    return bool(getattr(slots, slot))


def filled_core_count(slots: IntakeSlots) -> int:
    return sum(1 for slot in CORE_SLOTS if slot_satisfied(slots, slot))


def is_intake_complete(slots: IntakeSlots) -> bool:
    return filled_core_count(slots) >= 3


def next_missing_slot(slots: IntakeSlots) -> Optional[str]:
    for slot in CORE_SLOTS:
        if not slot_satisfied(slots, slot):
            return slot
    return None


def _extract_industry(text: str) -> str:
    lowered = text.lower()
    for needle, label in _INDUSTRY_HINTS.items():
        if needle in lowered:
            return label
    match = re.search(r"\b(?:we(?:'re| are) a|i run a|our)\s+(.{3,40}?)(?:\s+business|\s+company|\.|,|$)", text, re.I)
    if match:
        return match.group(1).strip()
    return ""


def _extract_main_pain(text: str) -> str:
    if _PAIN_RE.search(text):
        return text.strip()[:300]
    if len(text.split()) >= 8:
        return text.strip()[:300]
    return ""


def _extract_timeline(text: str) -> str:
    match = _TIMELINE_RE.search(text)
    return match.group(0).strip() if match else ""


def _fill_direct_slot_answer(message: str, slots: IntakeSlots, slot: str) -> IntakeSlots:
    """Accept short direct answers for the slot we asked on this turn."""
    text = (message or "").strip()
    if not text or slot_satisfied(slots, slot):
        return slots

    if slot == "main_pain":
        pain = _extract_main_pain(text)
        if pain:
            slots.main_pain = pain
            return slots
        if _EMAIL_RE.search(text) or _REFUSE_EMAIL_RE.search(text):
            return slots
        if _TIMELINE_RE.search(text) and len(text.split()) <= 5 and not _PAIN_RE.search(text):
            return slots
        if 2 <= len(text) <= 300:
            slots.main_pain = text

    elif slot == "timeline":
        timeline = _extract_timeline(text)
        if timeline:
            slots.timeline = timeline
            return slots
        if _PAIN_RE.search(text) and not _TIMELINE_RE.search(text):
            slots.main_pain = text[:300]
            return slots
        if 2 <= len(text) <= 120:
            slots.timeline = text

    elif slot == "industry":
        industry = _extract_industry(text)
        if industry:
            slots.industry = industry
            return slots
        if _INDUSTRY_SKIP_RE.search(text):
            return slots
        words = text.split()
        if 1 <= len(words) <= 3 and len(text) <= 40:
            slots.industry = text.strip().lower()

    return slots


def extract_slots_from_message(message: str, slots: IntakeSlots) -> IntakeSlots:
    text = (message or "").strip()
    if not text:
        return slots

    if _REFUSE_EMAIL_RE.search(text):
        slots.email_declined = True

    email_match = _EMAIL_RE.search(text)
    if email_match:
        slots.contact_email = email_match.group(0)

    if not slots.industry:
        industry = _extract_industry(text)
        if industry:
            slots.industry = industry

    if not slots.main_pain:
        pain = _extract_main_pain(text)
        if pain:
            slots.main_pain = pain

    if not slots.timeline:
        timeline = _extract_timeline(text)
        if timeline:
            slots.timeline = timeline

    name_match = re.search(r"\b(?:i'?m|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if name_match and not slots.name:
        slots.name = name_match.group(1).strip()

    return slots


def build_intake_summary(slots: IntakeSlots) -> str:
    lines: List[str] = []
    if slots.industry:
        lines.append(f"Industry: {slots.industry}")
    if slots.main_pain:
        lines.append(f"Main pain: {slots.main_pain[:120]}")
    if slots.timeline:
        lines.append(f"Timeline: {slots.timeline}")
    if slots.contact_email:
        lines.append(f"Email: {slots.contact_email}")
    elif slots.email_declined:
        lines.append("Email: declined in chat")
    if slots.name:
        lines.append(f"Name: {slots.name}")
    summary = "; ".join(lines) if lines else "your notes"
    return (
        f"Thanks — here's what I captured: {summary}. "
        "Next step: complete our workflow intake at fikirisolutions.com/intake "
        "or email info@fikirisolutions.com."
    )


def process_intake_turn(message: str, slots: IntakeSlots, mode: str) -> IntakeTurnResult:
    asked_slot = next_missing_slot(slots)
    slots = extract_slots_from_message(message, slots)
    if asked_slot:
        slots = _fill_direct_slot_answer(message, slots, asked_slot)

    if is_intake_complete(slots):
        return IntakeTurnResult(
            response=build_intake_summary(slots),
            complete=True,
            slots=slots,
        )

    missing = next_missing_slot(slots)
    if missing is None:
        return IntakeTurnResult(
            response=build_intake_summary(slots),
            complete=True,
            slots=slots,
        )

    opener = {
        config.MODE_WORKFLOW_AUDIT: "A workflow audit reviews where time and leads leak in your operations.",
        config.MODE_CONSULTING: "Happy to learn about your consulting or implementation needs.",
        config.MODE_EXPLORE_FIT: "Let's see if Fikiri is a good fit for your business.",
    }.get(mode, "Let's capture a few quick details.")

    question = SLOT_QUESTIONS[missing]
    if filled_core_count(slots) == 0:
        response = f"{opener} {question}"
    else:
        response = question

    return IntakeTurnResult(
        response=response,
        complete=False,
        next_slot=missing,
        slots=slots,
    )


def intake_metadata(slots: IntakeSlots, *, active: bool, complete: bool, next_slot: Optional[str]) -> Dict:
    return {
        "active": active,
        "complete": complete,
        "next_slot": next_slot,
        "slots": slots.to_dict(),
        "filled_core_count": filled_core_count(slots),
    }
