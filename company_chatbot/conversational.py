"""Short conversational replies for greetings and casual openers."""

from __future__ import annotations

import re
from typing import Optional

_GREETING_RE = re.compile(
    r"^(hi|hello|hey|howdy|good (morning|afternoon|evening))[\s!.?]*$",
    re.I,
)
_ACK_RE = re.compile(
    r"^(ok|okay|cool|thanks|thank you|got it|wow|nice|great)[\s!.?]*$",
    re.I,
)
_WHY_RE = re.compile(r"^why[\s!.?]*$", re.I)
_HOW_RE = re.compile(r"^how[\s!.?]*$", re.I)
_WHAT_RE = re.compile(r"^what[\s!.?]*$", re.I)
_HUH_RE = re.compile(r"^(huh|\?+)[\s!.?]*$", re.I)
_HELP_ME_RE = re.compile(r"^help me[\s!.?]*$", re.I)
_CONFUSED_RE = re.compile(
    r"^(i don'?t understand|don'?t understand|confused|not helping|this isn'?t helping)[\s!.?]*$",
    re.I,
)

_GREETING_REPLY = (
    "Hi! I can help with Fikiri pricing, the AI email assistant, fit checks, workflow audits, "
    "or connecting you with our team. What would you like to explore?"
)

_ACK_REPLY = (
    "Happy to help when you're ready. Ask about pricing, the AI email assistant, whether Fikiri "
    "fits your business, or say workflow audit for a process review."
)

_WHY_REPLY = (
    "Fikiri connects your email, CRM, and calendar so you respond to leads faster and "
    "don't drop follow-ups. To see if it's a fit, tell me your industry or say workflow audit."
)

_HOW_REPLY = (
    "Ask about pricing, the AI email assistant, whether Fikiri fits your business, or request a "
    "workflow audit — I'll ask a few short questions or point you to the right next step."
)

_WHAT_REPLY = (
    "I answer product and pricing questions, run a quick fit check, or start a workflow audit. "
    "Try one of the buttons below or ask about email automation, CRM, or our services."
)

_HUH_REPLY = (
    "No worries — pick Pricing, Fit check, or Workflow audit below, or ask about a specific "
    "product like the AI email assistant."
)

_HELP_ME_REPLY = (
    "Happy to help. Ask about pricing, the AI email assistant, whether Fikiri fits your business, "
    "or say workflow audit for a short process review. You can also continue at "
    "fikirisolutions.com/intake or fikirisolutions.com/contact."
)

_CONFUSED_REPLY = (
    "Sorry that wasn't clear. Try asking about pricing, the AI email assistant, fit for your "
    "business, or say workflow audit — or continue at fikirisolutions.com/intake."
)


def conversational_reply(message: str) -> Optional[str]:
    """Return a friendly reply for greetings/acks, else None (use normal routing)."""
    text = (message or "").strip()
    if not text:
        return None
    if _GREETING_RE.match(text):
        return _GREETING_REPLY
    if _ACK_RE.match(text):
        return _ACK_REPLY
    if _HELP_ME_RE.match(text):
        return _HELP_ME_REPLY
    if _CONFUSED_RE.match(text):
        return _CONFUSED_REPLY
    if _WHY_RE.match(text):
        return _WHY_REPLY
    if _HOW_RE.match(text):
        return _HOW_REPLY
    if _WHAT_RE.match(text):
        return _WHAT_REPLY
    if _HUH_RE.match(text):
        return _HUH_REPLY
    return None
