#!/usr/bin/env python3
"""
Fikiri Solutions - LLM Router
Routes LLM requests through the proper pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.ai.llm_client import LLMClient
from core.ai.model_policy import (
    FALLBACK_LLM_MODEL,
    INTENT_MODEL_CONFIG,
    KNOWN_INTENTS,
    PREMIUM_LLM_MODEL,
)
from core.ai.validators import SchemaValidator
from core.ai.ai_event_log import (
    build_router_envelope_base,
    coerce_user_id,
    record_ai_event,
    sha256_hex,
    text_summary,
)

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce to float; None or invalid values become default."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce to int; None or invalid values become default."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_latency_ms(value: Any) -> float:
    """Coerce LLM client latency to float; missing or invalid values become 0.0."""
    return _safe_float(value, 0.0)


def _extract_first_json_object(text: str) -> str:
    """
    If the model wraps JSON in prose, take the first balanced {...} substring.
    Falls back to the original string when no object is found or braces are unbalanced.
    """
    if not text or not isinstance(text, str):
        return text
    s = text.strip()
    start = s.find("{")
    if start == -1:
        return text
    depth = 0
    for i in range(start, len(s)):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return text


def _coerce_llm_json_for_schema(text: str, output_schema: Optional[Dict[str, Any]]) -> str:
    """
    Normalize common LLM quirks before schema validation:
    - Fill required classification fields with safe defaults when missing
    - Coerce confidence (bool / str) to number
    - Coerce string-typed fields from int/float (e.g. phone numbers)
    """
    if not output_schema or not text:
        return text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(data, dict):
        return text

    required = list(output_schema.get("required") or [])
    properties = output_schema.get("properties") or {}

    # Email classification: ensure required keys exist
    if required and set(required) <= {"intent", "confidence", "urgency", "suggested_action"}:
        defaults = {
            "intent": "general_info",
            "confidence": 0.5,
            "urgency": "medium",
            "suggested_action": "Review and respond",
        }
        for key in required:
            val = data.get(key)
            if key not in data or val is None or val == "":
                if key in defaults:
                    data[key] = defaults[key]

    if "confidence" in data:
        c = data["confidence"]
        if isinstance(c, bool):
            data["confidence"] = 1.0 if c else 0.0
        elif isinstance(c, str):
            try:
                data["confidence"] = float(c.strip())
            except ValueError:
                data["confidence"] = 0.5
        elif isinstance(c, int) and not isinstance(c, bool):
            data["confidence"] = float(c)

    for key in ("intent", "urgency", "suggested_action"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            data[key] = str(data[key])

    for key, spec in properties.items():
        if spec.get("type") == "string" and key in data:
            v = data[key]
            if v is None:
                continue
            if isinstance(v, bool):
                data[key] = "true" if v else "false"
            elif isinstance(v, (int, float)):
                data[key] = str(v)

    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return text


class LLMRouter:
    """
    Central router for all LLM operations.
    Implements the required pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM router with client and validator."""
        self.client = LLMClient(api_key)
        self.validator = SchemaValidator()
        self.trace_id = None
    
    def process(
        self,
        input_data: str,
        intent: Optional[str] = None,
        cost_budget: Optional[float] = None,
        latency_requirement: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process input through the complete AI pipeline.
        
        Pipeline:
        1. preprocess(input)
        2. detect_intent(input) [if not provided]
        3. choose_model(intent, cost_budget, latency_requirement)
        4. call_llm(model, prompt, params)
        5. postprocess(output)
        6. validate_schema(output)
        7. log cost + latency
        8. return structured result
        
        Args:
            input_data: Input text/prompt
            intent: Optional pre-detected intent (skips detection step)
            cost_budget: Optional cost budget in USD
            latency_requirement: Optional latency requirement ('low', 'medium', 'high')
            output_schema: Optional schema for validation
            context: Optional context dictionary
        
        Returns:
            Dict with:
                - success: bool
                - content: str
                - intent: str
                - model: str
                - tokens_used: int
                - cost_usd: float
                - latency_ms: float
                - trace_id: str
                - correlation_id: str (also set on context when missing)
                - validated: bool
                - error: Optional[str]
        """
        self.trace_id = str(uuid.uuid4())
        start_time = datetime.now()
        if context is None:
            context = {}
        _cid = context.get("correlation_id")
        if _cid is None or (isinstance(_cid, str) and not _cid.strip()):
            context["correlation_id"] = str(uuid.uuid4())
        else:
            context["correlation_id"] = str(_cid).strip()
        correlation_id = context["correlation_id"]
        user_row_id = coerce_user_id(context.get("user_id"))
        source = str(context.get("source") or "unknown")
        entity_type = str(context.get("ai_entity_type") or "ai")
        entity_id = coerce_user_id(context.get("ai_entity_id"))

        preprocessed = ""
        resolved_intent = intent
        model = "unknown"
        max_tokens = 0
        temperature = 0.0
        requested_row_id = None

        try:
            # Step 1: Preprocess
            preprocessed = self.preprocess(input_data, context)

            # Step 2: Detect intent (if not provided)
            if not resolved_intent:
                resolved_intent = self.detect_intent(preprocessed)

            # Step 3: Choose model
            model_config = self.choose_model(resolved_intent, cost_budget, latency_requirement)
            model = model_config["model"]
            max_tokens = model_config["max_tokens"]
            temperature = model_config["temperature"]

            base_envelope = build_router_envelope_base(
                correlation_id=correlation_id,
                router_trace_id=self.trace_id,
                intent=resolved_intent,
                source=source,
                context=context,
                preprocessed_prompt=preprocessed,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if output_schema is not None:
                base_envelope["request"]["has_output_schema"] = True

            requested_row_id = record_ai_event(
                "ai.requested",
                user_id=user_row_id,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                status="completed",
                source=source,
                payload=base_envelope,
            )

            # Step 4: Call LLM
            llm_result = self.client.call_llm(
                model=model,
                prompt=preprocessed,
                max_tokens=max_tokens,
                temperature=temperature,
                trace_id=self.trace_id,
            )
            if not isinstance(llm_result, dict):
                llm_result = {
                    "success": False,
                    "error": "Invalid LLM client response",
                    "content": "",
                    "latency_ms": 0.0,
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                }

            if not llm_result.get("success"):
                fail_payload = dict(base_envelope)
                fail_payload["model"]["tokens_used"] = _safe_int(llm_result.get("tokens_used"))
                fail_payload["model"]["cost_usd"] = _safe_float(llm_result.get("cost_usd"))
                fail_payload["model"]["latency_ms"] = _safe_latency_ms(llm_result.get("latency_ms"))
                fail_payload["error"] = {
                    "code": "llm_call_failed",
                    "message": llm_result.get("error", "LLM call failed"),
                }
                record_ai_event(
                    "ai.response.failed",
                    user_id=user_row_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    correlation_id=correlation_id,
                    status="failed",
                    error_message=llm_result.get("error", "LLM call failed"),
                    source=source,
                    payload=fail_payload,
                )
                return {
                    "success": False,
                    "content": "",
                    "intent": resolved_intent,
                    "model": model,
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                    "latency_ms": _safe_latency_ms(llm_result.get("latency_ms")),
                    "trace_id": self.trace_id,
                    "correlation_id": correlation_id,
                    "validated": False,
                    "error": llm_result.get("error", "LLM call failed"),
                }

            # Step 5: Postprocess
            postprocessed = self.postprocess(
                llm_result.get("content") or "",
                resolved_intent,
                context,
            )

            # Step 5b: Structured JSON cleanup (prose wrappers, LLM type quirks) before validation
            if output_schema:
                postprocessed = _extract_first_json_object(postprocessed)
                postprocessed = _coerce_llm_json_for_schema(postprocessed, output_schema)

            # Step 6: Validate schema (if provided)
            validated = False
            if output_schema:
                validated = self.validator.validate_schema(postprocessed, output_schema)
                if not validated:
                    warn_extra = {
                        "event": "schema_validation_failed",
                        "service": "ai",
                        "severity": "WARN",
                        "trace_id": self.trace_id,
                    }
                    if context.get("source") is not None:
                        warn_extra["source"] = context["source"]
                    if context.get("tenant_id") is not None:
                        warn_extra["tenant_id"] = context["tenant_id"]
                    if context.get("user_id") is not None:
                        warn_extra["user_id"] = context["user_id"]
                    logger.warning("Schema validation failed for trace_id %s", self.trace_id, extra=warn_extra)
            else:
                validated = True  # No schema to validate against

            # Step 7: Log cost + latency and context (source, tenant_id, user_id when present)
            total_latency = (datetime.now() - start_time).total_seconds() * 1000
            _tu = _safe_int(llm_result.get("tokens_used"))
            _cost = _safe_float(llm_result.get("cost_usd"))
            log_extra = {
                "event": "ai_pipeline_complete",
                "service": "ai",
                "severity": "INFO",
                "trace_id": self.trace_id,
                "intent": resolved_intent,
                "model": model,
                "tokens_used": _tu,
                "cost_usd": _cost,
                "latency_ms": total_latency,
                "validated": validated,
                "metadata": {"cost_budget": cost_budget, "latency_requirement": latency_requirement},
            }
            if context.get("source") is not None:
                log_extra["source"] = context["source"]
            if context.get("tenant_id") is not None:
                log_extra["tenant_id"] = context["tenant_id"]
            if context.get("user_id") is not None:
                log_extra["user_id"] = context["user_id"]
            logger.info("✅ AI pipeline completed", extra=log_extra)

            gen_payload = dict(base_envelope)
            gen_payload["model"]["tokens_used"] = _tu
            gen_payload["model"]["cost_usd"] = _cost
            gen_payload["model"]["latency_ms"] = total_latency
            gen_payload["output"] = {
                "summary": text_summary(postprocessed, 200),
                "content_sha256": sha256_hex(postprocessed),
                "validated": validated,
                "raw_byte_length": len(postprocessed.encode("utf-8", errors="ignore")),
            }
            gen_payload["requested_event_id"] = requested_row_id

            record_ai_event(
                "ai.response.generated",
                user_id=user_row_id,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                status="completed",
                source=source,
                payload=gen_payload,
            )

            # Step 8: Return structured result
            return {
                "success": True,
                "content": postprocessed,
                "intent": resolved_intent,
                "model": model,
                "tokens_used": _tu,
                "cost_usd": _cost,
                "latency_ms": total_latency,
                "trace_id": self.trace_id,
                "correlation_id": correlation_id,
                "validated": validated,
                "error": None,
            }

        except Exception as e:
            error_msg = str(e)
            err_extra = {
                "event": "ai_pipeline_error",
                "service": "ai",
                "severity": "ERROR",
                "trace_id": self.trace_id,
                "error": error_msg,
            }
            if context.get("source") is not None:
                err_extra["source"] = context["source"]
            if context.get("tenant_id") is not None:
                err_extra["tenant_id"] = context["tenant_id"]
            if context.get("user_id") is not None:
                err_extra["user_id"] = context["user_id"]
            logger.error("❌ AI pipeline failed: %s", error_msg, extra=err_extra)
            try:
                _cfg = INTENT_MODEL_CONFIG["general"]
                _mt = max_tokens if max_tokens > 0 else _cfg["max_tokens"]
                _tp = temperature if model != "unknown" else _cfg["temperature"]
                fail_env = build_router_envelope_base(
                    correlation_id=correlation_id,
                    router_trace_id=self.trace_id,
                    intent=resolved_intent or "unknown",
                    source=source,
                    context=context,
                    preprocessed_prompt=preprocessed or "",
                    model=model,
                    max_tokens=_mt,
                    temperature=_tp,
                )
                fail_env["error"] = {"code": "pipeline_exception", "message": error_msg}
                record_ai_event(
                    "ai.response.failed",
                    user_id=user_row_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    correlation_id=correlation_id,
                    status="failed",
                    error_message=error_msg,
                    source=source,
                    payload=fail_env,
                )
            except Exception:
                logger.debug("AI failure event logging skipped", exc_info=True)
            return {
                "success": False,
                "content": "",
                "intent": resolved_intent or "unknown",
                "model": model,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "latency_ms": 0.0,
                "trace_id": self.trace_id,
                "correlation_id": correlation_id,
                "validated": False,
                "error": error_msg,
            }
    
    def preprocess(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Preprocess input: sanitize, truncate if needed, add context.
        
        Args:
            input_data: Raw input text
            context: Optional context dictionary
        
        Returns:
            Preprocessed prompt string
        """
        # Sanitize: remove excessive whitespace, basic cleanup
        preprocessed = ' '.join(input_data.split())
        
        # Add context if provided (standard key: context_text or context)
        if context:
            context_str = context.get('context_text') or context.get('context') or ''
            if context_str:
                preprocessed = preprocessed + f"\n\nContext: {context_str}"
        
        # Truncate if too long (prevent token overflow)
        max_length = 8000  # Reasonable limit for most models
        if len(preprocessed) > max_length:
            preprocessed = preprocessed[:max_length] + "... [truncated]"
            logger.warning(f"Input truncated to {max_length} characters")
        
        return preprocessed
    
    def detect_intent(self, input_data: str) -> str:
        """
        Detect intent from input using simple keyword matching.
        Can be enhanced with ML model later.
        
        Args:
            input_data: Preprocessed input
        
        Returns:
            Intent string (e.g., 'email_reply', 'classification', 'extraction', 'general')
        """
        input_lower = input_data.lower()
        
        # Simple keyword-based intent detection
        if any(word in input_lower for word in ['reply', 'respond', 'answer', 'email']):
            return 'email_reply'
        elif any(word in input_lower for word in ['classify', 'categorize', 'type', 'category']):
            return 'classification'
        elif any(word in input_lower for word in ['extract', 'parse', 'find', 'get']):
            return 'extraction'
        elif any(word in input_lower for word in ['summarize', 'summary', 'summarise']):
            return 'summarization'
        else:
            return 'general'
    
    def choose_model(
        self,
        intent: str,
        cost_budget: Optional[float] = None,
        latency_requirement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Choose appropriate model based on intent, cost budget, and latency requirements.
        
        Args:
            intent: Detected intent
            cost_budget: Optional cost budget in USD
            latency_requirement: Optional latency requirement ('low', 'medium', 'high')
        
        Returns:
            Dict with model, max_tokens, temperature
        """
        config = INTENT_MODEL_CONFIG.get(intent, INTENT_MODEL_CONFIG["general"]).copy()
        
        # Adjust based on cost budget (premium model only when explicitly high budget).
        if cost_budget is not None:
            if cost_budget < 0.01:
                config["model"] = FALLBACK_LLM_MODEL
                config["max_tokens"] = min(config["max_tokens"], 200)
            elif cost_budget > 0.10:
                config["model"] = PREMIUM_LLM_MODEL
                config["max_tokens"] = min(config["max_tokens"] * 2, 2000)

        if latency_requirement == "low":
            config["model"] = FALLBACK_LLM_MODEL
        elif latency_requirement == "high":
            config["model"] = PREMIUM_LLM_MODEL

        return config
    
    def postprocess(
        self,
        output: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Postprocess LLM output: clean, format, validate basic structure.
        
        Args:
            output: Raw LLM output
            intent: Intent used for generation
            context: Optional context
        
        Returns:
            Postprocessed output string
        """
        # Basic cleanup
        postprocessed = output.strip()

        # Strip ```json ... ``` wrappers so validate_schema can parse JSON
        if postprocessed.startswith('```'):
            postprocessed = re.sub(r'^```(?:json)?\s*', '', postprocessed, flags=re.IGNORECASE)
            postprocessed = re.sub(r'\s*```$', '', postprocessed)
            postprocessed = postprocessed.strip()
        
        # Remove common LLM artifacts
        if postprocessed.startswith('"') and postprocessed.endswith('"'):
            postprocessed = postprocessed[1:-1]
        
        # Intent-specific postprocessing
        if intent == 'email_reply':
            # Ensure it doesn't start with "Subject:" or similar
            if postprocessed.lower().startswith('subject:'):
                lines = postprocessed.split('\n', 1)
                if len(lines) > 1:
                    postprocessed = lines[1].strip()
        
        return postprocessed

