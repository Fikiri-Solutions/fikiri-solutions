"""Rules-based context dependency: STANDALONE | FOLLOWUP | AMBIGUOUS."""

from __future__ import annotations

import re
from enum import Enum

from company_chatbot.retrieval import (
    _primary_router_topic,
    _retrieval_tokens,
    is_standalone_topic_query,
    normalize_query_text,
)


class ContextDependency(str, Enum):
    STANDALONE = "standalone"
    FOLLOWUP = "followup"
    AMBIGUOUS = "ambiguous"


_FOLLOWUP_CUE_RE = re.compile(
    r"^(what about|how about|and |also |same for|does that|is that|what if|"
    r"how much (is|does|for) (that|it|this)|what about that|"
    r"can (it|that)|does it)\b",
    re.I,
)


def detect_context_dependency(
    query: str,
    previous_query: str | None = None,
) -> ContextDependency:
    current = (query or "").strip()
    previous = (previous_query or "").strip()
    if not current:
        return ContextDependency.AMBIGUOUS
    if not previous:
        return ContextDependency.STANDALONE

    normalized = normalize_query_text(current)
    # Explicit follow-up cues win over topic-switch heuristics ("What about Gmail?").
    if _FOLLOWUP_CUE_RE.search(normalized):
        return ContextDependency.FOLLOWUP

    if is_standalone_topic_query(current):
        return ContextDependency.STANDALONE

    current_topic = _primary_router_topic(current)
    previous_topic = _primary_router_topic(previous)
    if current_topic and previous_topic and current_topic != previous_topic:
        return ContextDependency.STANDALONE

    tokens = _retrieval_tokens(current)
    if len(tokens) <= 3 and not current_topic:
        return ContextDependency.FOLLOWUP

    if current_topic:
        return ContextDependency.STANDALONE

    return ContextDependency.AMBIGUOUS


def should_use_previous_query(query: str, previous_query: str | None = None) -> bool:
    return detect_context_dependency(query, previous_query) == ContextDependency.FOLLOWUP
