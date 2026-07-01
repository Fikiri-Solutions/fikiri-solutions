"""Conversation guards — turn cap, repeat detection, frustration, low-info input."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

MAX_TURN_CAP = 12
MAX_IDENTICAL_RESPONSES = 2

_FRUSTRATION_RE = re.compile(
    r"\b(already told you|i said that|stop asking|this is frustrating|"
    r"you already asked|asked me that|enough questions|you already said that|"
    r"stuck in a loop|you'?re stuck|youre stuck|in a loop|keep saying the same|"
    r"same thing again|not helping|isn'?t helping|useless|you keep repeating|"
    r"repeating yourself|going in circles)\b",
    re.I,
)
_LOW_INFO_RE = re.compile(r"^[\s.?!(,:;-]*$")
_HELP_ME_RE = re.compile(r"^help me[\s!.?]*$", re.I)
_GENERIC_FALLBACK_SNIPPET = "i'm not sure i understood"
_STUCK_EXIT_SNIPPET = "i got stuck there"


@dataclass
class GuardContext:
    turn_count: int = 0
    message: str = ""
    intake_active: bool = False
    response_history: List[str] = field(default_factory=list)


@dataclass
class GuardResult:
    triggered: bool = False
    reason: Optional[str] = None
    suggest_handoff: bool = False


def evaluate_guards(ctx: GuardContext) -> GuardResult:
    checks = (
        _check_turn_cap,
        _check_frustration,
        _check_help_after_stuck,
        _check_low_information,
    )
    for check in checks:
        result = check(ctx)
        if result.triggered:
            return result
    return GuardResult()


def would_repeat_too_many_times(
    response_history: List[str],
    new_response: str,
    *,
    last_user_message: str = "",
    current_user_message: str = "",
) -> bool:
    """Hand off when the bot would repeat the same reply too many times."""
    if not response_history:
        return False

    n = _norm(new_response)
    trailing_identical = 0
    for prior in reversed(response_history):
        if _norm(prior) == n:
            trailing_identical += 1
        else:
            break
    if trailing_identical >= MAX_IDENTICAL_RESPONSES:
        return True

    if _norm(response_history[-1]) != n:
        return False
    if not _norm(last_user_message):
        return False
    return _norm(last_user_message) == _norm(current_user_message)


def _norm(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _is_generic_fallback_response(text: str) -> bool:
    return _GENERIC_FALLBACK_SNIPPET in _norm(text)


def _check_turn_cap(ctx: GuardContext) -> GuardResult:
    if ctx.turn_count >= MAX_TURN_CAP:
        return GuardResult(
            triggered=True,
            reason="turn_cap",
            suggest_handoff=True,
        )
    return GuardResult()


def _check_frustration(ctx: GuardContext) -> GuardResult:
    if _FRUSTRATION_RE.search(ctx.message or ""):
        return GuardResult(
            triggered=True,
            reason="frustration",
            suggest_handoff=True,
        )
    return GuardResult()


def _check_help_after_stuck(ctx: GuardContext) -> GuardResult:
    if not _HELP_ME_RE.match((ctx.message or "").strip()):
        return GuardResult()
    history = ctx.response_history or []
    if any(_is_generic_fallback_response(reply) for reply in history):
        return GuardResult(
            triggered=True,
            reason="help_after_stuck",
            suggest_handoff=True,
        )
    if any(_STUCK_EXIT_SNIPPET in _norm(reply) for reply in history):
        return GuardResult(
            triggered=True,
            reason="help_after_stuck",
            suggest_handoff=True,
        )
    if ctx.turn_count >= 4:
        return GuardResult(
            triggered=True,
            reason="help_after_stuck",
            suggest_handoff=True,
        )
    return GuardResult()


def _check_low_information(ctx: GuardContext) -> GuardResult:
    if not ctx.intake_active:
        return GuardResult()
    text = (ctx.message or "").strip()
    if not text or _LOW_INFO_RE.match(text) or len(text) < 2:
        return GuardResult(
            triggered=True,
            reason="low_information",
            suggest_handoff=False,
        )
    return GuardResult()


def build_guard_handoff_message(reason: str, summary: str = "") -> str:
    if reason in ("frustration", "help_after_stuck", "repeat_response"):
        prefix = (
            "You're right — I got stuck there. The best next step is to send this to the "
            "Fikiri team or continue through the workflow audit so we can answer properly."
        )
    elif reason == "turn_cap":
        prefix = "We've covered a lot in this chat — let's hand this to the team with context."
    else:
        prefix = "Let's move this forward with the right next step."
    known = f" {summary}" if summary else ""
    return (
        f"{prefix}{known} "
        "Please continue at fikirisolutions.com/intake or email info@fikirisolutions.com."
    )
