"""
Chatbot response generation for the public widget path.

LLM prompt construction, schema validation, confidence handling, and fallback behavior.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.ai.llm_router import LLMRouter
from core.ai.schemas import ChatbotResponseSchema
from core.chatbot_config import ChatbotConfig, load_chatbot_config
from core.chatbot_retrieval import retrieval_confidence

logger = logging.getLogger(__name__)

CHATBOT_RESPONSE_SCHEMA_V1 = ChatbotResponseSchema


@dataclass
class ChatbotAnswerResult:
    answer: str
    confidence: float
    llm_confidence: Optional[float]
    combined_confidence: float
    fallback_used: bool
    escalation_recommended: bool
    llm_trace_id: Optional[str]
    response_metadata: Dict[str, Any] = field(default_factory=dict)
    retrieval_confidence: float = 0.0


def _confidence_threshold() -> float:
    try:
        return float(os.getenv("CHATBOT_CONFIDENCE_THRESHOLD", "0.4"))
    except ValueError:
        return 0.4


def _combine_confidence(retrieval_conf: float, llm_conf: Optional[float], weight_retrieval: float = 0.5) -> float:
    if llm_conf is None:
        return round(retrieval_conf if retrieval_conf > 0 else 0.2, 4)
    combined = weight_retrieval * retrieval_conf + (1.0 - weight_retrieval) * llm_conf
    return round(min(1.0, max(0.0, combined)), 4)


def _resolve_config(
    chatbot_config: Optional[ChatbotConfig],
    user_id: Optional[int],
    tenant_id: Optional[str],
    billing_uid: Optional[int],
) -> ChatbotConfig:
    if chatbot_config is not None:
        return chatbot_config
    uid = billing_uid if billing_uid is not None else user_id
    if isinstance(uid, str) and uid.strip().isdigit():
        try:
            uid = int(uid.strip())
        except ValueError:
            uid = None
    if isinstance(uid, bool):
        uid = None
    return load_chatbot_config(uid if isinstance(uid, int) else None, tenant_id=tenant_id)


def build_chatbot_prompt(query: str, context_text: str, config: ChatbotConfig) -> str:
    """Assemble LLM prompt from retrieved context and safe tenant config fields."""
    role = (
        f"You are {config.chatbot_name}, a customer support chatbot for {config.business_name}."
    )
    lines = [
        role,
        f"Tone: {config.tone}.",
        f"Answer style: {config.answer_style}.",
        f"Keep answers under {config.max_answer_length} characters when possible.",
        "Use ONLY the provided context below.",
        "If the context does not support an answer, say you don't have enough verified information.",
        "Never invent details or make unsupported claims.",
    ]
    if config.allowed_topics:
        lines.append(
            "Prefer to help with topics such as: "
            + ", ".join(config.allowed_topics[:10])
            + "."
        )
    if config.restricted_topics:
        lines.append(
            "Do not provide advice on: "
            + ", ".join(config.restricted_topics[:10])
            + ". Politely decline and offer to connect the user with the team."
        )
    if config.disclosure_text:
        lines.append(f"When relevant, include: {config.disclosure_text}")
    lines.extend([
        "",
        f"Context:\n{context_text}",
        "",
        f"User question: {query}",
        "",
        "Return JSON with fields: answer, confidence (0-1), fallback_used (true/false), "
        "sources (list of source ids), follow_up (optional).",
    ])
    return "\n".join(lines)


def generate_chatbot_answer(
    query: str,
    context_text: str,
    sources: List[Dict[str, Any]],
    *,
    tenant_id: Optional[str],
    user_id: Optional[int],
    conversation_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    billing_uid: Optional[int] = None,
    fallback_needed: bool = False,
    allow_llm: bool = True,
    chatbot_config: Optional[ChatbotConfig] = None,
) -> ChatbotAnswerResult:
    """
    Generate a chatbot answer from retrieved context.

    When ``fallback_needed`` is true or ``allow_llm`` is false, skips the LLM and uses the safe fallback.
    """
    config = _resolve_config(chatbot_config, user_id, tenant_id, billing_uid)
    retrieval_conf = retrieval_confidence(sources)
    answer = config.fallback_message
    llm_confidence: Optional[float] = 0.2
    fallback_used = True
    llm_trace_id = None
    llm_attempted = False
    llm_result: Dict[str, Any] = {}

    if allow_llm and not fallback_needed:
        router = LLMRouter()
        prompt = build_chatbot_prompt(query, context_text, config)
        llm_user_id = billing_uid if billing_uid is not None else user_id
        llm_result = router.process(
            input_data=prompt,
            intent="chatbot_response",
            output_schema=CHATBOT_RESPONSE_SCHEMA_V1,
            context={
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "user_id": llm_user_id,
                "source": "public_chatbot",
                "correlation_id": correlation_id,
            },
        )
        llm_attempted = True
        if llm_result.get("success") and llm_result.get("validated"):
            try:
                parsed = json.loads(llm_result.get("content", "{}"))
                answer = parsed.get("answer") or answer
                llm_confidence = parsed.get("confidence")
                if llm_confidence is not None:
                    llm_confidence = max(0.0, min(1.0, float(llm_confidence)))
                fallback_used = bool(parsed.get("fallback_used", False))
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM response not JSON; using fallback")
                llm_confidence = 0.2
        else:
            logger.warning("LLM response invalid: %s", llm_result.get("error"))
            llm_confidence = 0.2
        llm_trace_id = llm_result.get("trace_id")
    else:
        llm_confidence = None

    combined = _combine_confidence(retrieval_conf, llm_confidence)
    threshold = _confidence_threshold()
    if combined < threshold:
        answer = config.low_confidence_message()
        fallback_used = True

    return ChatbotAnswerResult(
        answer=answer,
        confidence=combined,
        llm_confidence=llm_confidence,
        combined_confidence=combined,
        fallback_used=fallback_used,
        escalation_recommended=fallback_used or combined < threshold,
        llm_trace_id=llm_trace_id,
        retrieval_confidence=retrieval_conf,
        response_metadata={
            "llm_attempted": llm_attempted,
            "llm_success": bool(llm_result.get("success")),
            "llm_validated": bool(llm_result.get("validated")),
            "confidence_threshold": threshold,
            "chatbot_config_applied": True,
        },
    )
