#!/usr/bin/env python3
"""
LLM output schemas and context builder (Phase 1).
Single source of truth for router output_schema and context shape.
Domain models (Lead, KnowledgeSnippet, ExtractedContact) live in core/domain/schemas.py.
See docs/SCHEMA_STRATEGY_LLM_DATA.md.
"""

from typing import Dict, Any, Optional

# ---------------------------------------------------------------------------
# LLM output schemas (for SchemaValidator / router.process output_schema)
# ---------------------------------------------------------------------------

ChatbotResponseSchema = {
    "type": "object",
    "required": ["answer", "confidence", "fallback_used", "sources"],
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number"},
        "fallback_used": {"type": "boolean"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "follow_up": {"type": "string"},
    },
}

# Backward compat alias
CHATBOT_RESPONSE_SCHEMA = ChatbotResponseSchema

EmailClassificationSchema = {
    "type": "object",
    "required": ["intent", "confidence", "urgency", "suggested_action"],
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number"},
        "urgency": {"type": "string"},
        "suggested_action": {"type": "string"},
    },
}

LeadAnalysisSchema = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "conversion_probability": {"type": "number"},
        "priority": {"type": "string"},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "insights": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
        "estimated_value": {"type": "integer"},
    },
}

# ---------------------------------------------------------------------------
# LLM context builder (standard shape for LLMRouter.process(..., context=...))
# ---------------------------------------------------------------------------


def build_llm_context(
    context_text: str = "",
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    intent: Optional[str] = None,
    source: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build standard context dict for LLMRouter.process(). Router uses context_text or context for prompt appendix."""
    out: Dict[str, Any] = {}
    if context_text:
        out["context"] = context_text
        out["context_text"] = context_text
    if tenant_id is not None:
        out["tenant_id"] = tenant_id
    if user_id is not None:
        out["user_id"] = user_id
    if intent is not None:
        out["intent"] = intent
    if source is not None:
        out["source"] = source
    out.update(extra)
    return out
