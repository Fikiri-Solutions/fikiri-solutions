"""
Canonical email classification contract and legacy compatibility helpers.

All entry points should return analysis via ``finalize_email_analysis``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.ai.email_intent_taxonomy import legacy_intent_for_compat

logger = logging.getLogger(__name__)

# Classification provenance (logged + returned on analysis payload)
SOURCE_V2_AI = "v2_ai"
SOURCE_V2_FALLBACK = "v2_fallback"
SOURCE_LEGACY_WRAPPER = "legacy_wrapper"
SOURCE_MANUAL_API = "manual_api"
SOURCE_MAILBOX_SYNC = "mailbox_sync"

V2_ANALYSIS_KEYS = (
    "intent",
    "legacy_intent",
    "secondary_intents",
    "confidence_score",
    "lead_score",
    "urgency_score",
    "business_value_score",
    "sender",
    "extracted_details",
    "recommended_action_detail",
    "reply_guidance",
    "reasoning_summary",
    "schema_version",
    "summary",
    "recommended_action",
    "tone",
    "crm_updates",
    "suggested_reply",
    "should_auto_send",
    "needs_human_review",
    "classification_source",
)


def merge_legacy_compat_fields(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure legacy keys exist alongside v2 fields without removing canonical intent.

    Legacy consumers often read: intent (legacy), confidence, urgency, suggested_action.
    V2 consumers read: intent (canonical), legacy_intent, confidence_score, ...
    """
    if not isinstance(analysis, dict):
        return {}

    out = dict(analysis)
    canonical = str(out.get("intent") or "unknown_business_relevant")
    out["intent"] = canonical
    out["legacy_intent"] = out.get("legacy_intent") or legacy_intent_for_compat(canonical)

    conf = out.get("confidence_score", out.get("confidence"))
    try:
        out["confidence_score"] = float(conf if conf is not None else 0.0)
    except (TypeError, ValueError):
        out["confidence_score"] = 0.0
    out["confidence"] = out["confidence_score"]

    out["urgency"] = str(out.get("urgency") or "medium").lower()
    out["business_value"] = str(out.get("business_value") or "medium").lower()

    rad = out.get("recommended_action_detail")
    next_action = out.get("recommended_action")
    if isinstance(rad, dict) and rad.get("next_best_action"):
        next_action = next_action or rad.get("next_best_action")
    out["recommended_action"] = str(next_action or "draft_reply")
    out["suggested_action"] = out.get("suggested_action") or out["recommended_action"]

    out.setdefault("secondary_intents", [])
    out.setdefault("lead_score", 0)
    out.setdefault("urgency_score", 50)
    out.setdefault("business_value_score", 50)
    out.setdefault("sender", {})
    out.setdefault("extracted_details", {})
    out.setdefault("recommended_action_detail", {})
    out.setdefault("reply_guidance", {})
    out.setdefault("reason_for_recommendation", out.get("reasoning_summary") or "")
    out.setdefault("reasoning_summary", out.get("reason_for_recommendation") or "")

    return out


def finalize_email_analysis(
    analysis: Dict[str, Any],
    *,
    classification_source: str,
) -> Dict[str, Any]:
    """Attach source, legacy aliases, and log routing metadata."""
    out = merge_legacy_compat_fields(analysis)
    out["classification_source"] = classification_source
    try:
        logger.info(
            "email.classification.finalized",
            extra={
                "event": "email.classification.finalized",
                "service": "email",
                "severity": "INFO",
                "metadata": {
                    "classification_source": classification_source,
                    "intent": out.get("intent"),
                    "legacy_intent": out.get("legacy_intent"),
                    "confidence_score": out.get("confidence_score"),
                    "lead_score": out.get("lead_score"),
                },
            },
        )
    except Exception:
        pass
    return out


def slim_legacy_classification_view(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Narrow view matching the old classify_email_intent response shape.

    Includes full v2 payload under ``analysis`` for callers that want depth.
    """
    full = merge_legacy_compat_fields(analysis)
    return {
        "intent": full.get("legacy_intent"),
        "canonical_intent": full.get("intent"),
        "legacy_intent": full.get("legacy_intent"),
        "confidence": full.get("confidence"),
        "confidence_score": full.get("confidence_score"),
        "urgency": full.get("urgency"),
        "suggested_action": full.get("suggested_action"),
        "classification_source": full.get("classification_source"),
        "analysis": full,
    }
