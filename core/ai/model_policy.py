"""
LLM model selection — Fikiri standard pair: **gpt-4o-mini** + **gpt-4o**.

- **gpt-4o-mini**: default for every intent, API error fallback, and low-budget /
  low-latency paths from LLMRouter.choose_model().
- **gpt-4o**: premium when choose_model() sees high cost_budget or
  latency_requirement == 'high'.

Optional env overrides (same IDs or snapshots your org allows):
FIKIRI_LLM_MODEL_DEFAULT, FIKIRI_LLM_PREMIUM_MODEL, FIKIRI_LLM_FALLBACK_MODEL,
FIKIRI_LLM_MODEL_CHATBOT, FIKIRI_LLM_MODEL_EMAIL_REPLY, etc.

Pricing: https://openai.com/api/pricing/
"""

from __future__ import annotations

import os
from typing import Any, Dict

# Broadly available, cheap; used when primary model errors or budget is tight.
FALLBACK_LLM_MODEL = (os.getenv("FIKIRI_LLM_FALLBACK_MODEL") or "gpt-4o-mini").strip()

# Stronger default when router requests high quality / high budget cap.
PREMIUM_LLM_MODEL = (os.getenv("FIKIRI_LLM_PREMIUM_MODEL") or "gpt-4o").strip()


def _env_model(key: str, default: str) -> str:
    v = (os.getenv(key) or "").strip()
    return v if v else default


# Single “cheap default” for any intent without a specific override.
_DEFAULT_CHEAP = _env_model("FIKIRI_LLM_MODEL_DEFAULT", "gpt-4o-mini")


def _cfg(model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
    return {"model": model, "max_tokens": max_tokens, "temperature": temperature}


# Intent → model: keep temperatures aligned with task risk (lower for structured).
INTENT_MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "email_reply": _cfg(
        _env_model("FIKIRI_LLM_MODEL_EMAIL_REPLY", _DEFAULT_CHEAP),
        300,
        0.7,
    ),
    "classification": _cfg(
        _env_model("FIKIRI_LLM_MODEL_CLASSIFICATION", _DEFAULT_CHEAP),
        100,
        0.3,
    ),
    "extraction": _cfg(
        _env_model("FIKIRI_LLM_MODEL_EXTRACTION", _DEFAULT_CHEAP),
        200,
        0.1,
    ),
    "summarization": _cfg(
        _env_model("FIKIRI_LLM_MODEL_SUMMARIZATION", _DEFAULT_CHEAP),
        500,
        0.5,
    ),
    "chatbot_response": _cfg(
        _env_model("FIKIRI_LLM_MODEL_CHATBOT", _DEFAULT_CHEAP),
        500,
        0.4,
    ),
    "general": _cfg(
        _env_model("FIKIRI_LLM_MODEL_GENERAL", _DEFAULT_CHEAP),
        500,
        0.7,
    ),
}

KNOWN_INTENTS = tuple(INTENT_MODEL_CONFIG.keys())
