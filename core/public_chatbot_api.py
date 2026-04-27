"""
Public Chatbot API for External Clients
Provides embeddable chatbot endpoint with API key authentication, CORS, and tenant isolation
"""

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from functools import wraps

from core.api_key_manager import api_key_manager
from core.ai_budget_guardrails import ai_budget_guardrails
from core.minimal_vector_search import get_vector_search
from core.smart_faq_system import get_smart_faq
from core.knowledge_base_system import get_knowledge_base
from core.context_aware_responses import get_context_system
from core.api_validation import handle_api_errors, create_error_response
from core.ai.llm_router import LLMRouter
from core.database_optimization import db_optimizer
from core.feature_flags import get_feature_flags
from core.expert_escalation import get_escalation_engine
from core.chatbot_feedback import get_feedback_system
from crm.service import enhanced_crm_service
from core.chatbot_content_events import (
    content_fingerprint_from_sources,
    record_chatbot_response_generated,
)
from core.request_correlation import get_or_create_correlation_id
from core.user_feedback_router import get_user_feedback_router

logger = logging.getLogger(__name__)

# Create Blueprint for public API
public_chatbot_bp = Blueprint('public_chatbot', __name__, url_prefix='/api/public/chatbot')

# Initialize systems
faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()
context_system = get_context_system()

# Phase 1: canonical LLM output schema from core.ai.schemas
from core.ai.schemas import ChatbotResponseSchema
CHATBOT_RESPONSE_SCHEMA_V1 = ChatbotResponseSchema  # backward compat

# Phase 2b: canonical KnowledgeSnippet and context string from domain
from core.domain.schemas import knowledge_snippet, snippets_to_context_string


def _extract_lead_info(query: str, lead_payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    email = (lead_payload.get("email") or "").strip()
    phone = (lead_payload.get("phone") or "").strip()
    name = (lead_payload.get("name") or "").strip()

    if not email:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", query)
        email = match.group(0) if match else ""
    if not phone:
        match = re.search(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", query)
        phone = match.group(0) if match else ""
    if not name and email:
        name = email.split("@")[0].replace(".", " ").title()

    return {
        "email": email or None,
        "phone": phone or None,
        "name": name or "Chatbot Lead"
    }


def _record_billing_usage(user_id: Optional[int], usage_type: str, quantity: int = 1):
    if not user_id:
        return
    if os.getenv("FLASK_ENV") == "test" or os.getenv("PYTEST_CURRENT_TEST"):
        return
    if not db_optimizer.table_exists("billing_usage"):
        return
    try:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        db_optimizer.execute_query(
            "INSERT INTO billing_usage (user_id, month, usage_type, quantity) VALUES (?, ?, ?, ?)",
            (user_id, month, usage_type, quantity),
            fetch=False
        )
    except Exception as e:
        logger.warning("Failed to record billing usage: %s", e)


def _check_plan_access(user_id: Optional[int]) -> Dict[str, Any]:
    if os.getenv("FLASK_ENV") == "test" or os.getenv("PYTEST_CURRENT_TEST"):
        return {"plan": "test", "allow_llm": True}
    if not user_id or not db_optimizer.table_exists("subscriptions"):
        return {"plan": "unknown", "allow_llm": True}
    try:
        sub = db_optimizer.execute_query(
            "SELECT status, tier FROM subscriptions WHERE user_id = ? ORDER BY current_period_end DESC LIMIT 1",
            (user_id,)
        )
        if sub:
            status = (sub[0].get("status") or "").lower()
            tier = (sub[0].get("tier") or "starter").lower()
            is_paid = status in {"active", "trialing"}
            return {"plan": tier if is_paid else "free", "allow_llm": is_paid}
        return {"plan": "free", "allow_llm": False}
    except Exception as e:
        logger.warning("Plan check failed: %s", e)
        return {"plan": "unknown", "allow_llm": True}


def _build_sources(faq_results, kb_results, vector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources = []
    if faq_results and getattr(faq_results, "success", False) and getattr(faq_results, "matches", None):
        for match in faq_results.matches[:3]:
            sources.append({
                "type": "faq",
                "id": match.faq_entry.id,
                "question": match.faq_entry.question,
                "answer": match.faq_entry.answer,
                "confidence": match.confidence
            })
    if kb_results and getattr(kb_results, "success", False) and getattr(kb_results, "results", None):
        for result in kb_results.results[:3]:
            sources.append({
                "type": "knowledge_base",
                "id": result.document.id,
                "title": result.document.title,
                "content": result.document.content[:200] + "..." if len(result.document.content) > 200 else result.document.content,
                "relevance": result.relevance_score
            })
    for item in vector_results[:3]:
        sources.append({
            "type": "vector",
            "id": item.get("id") or item.get("metadata", {}).get("id") or item.get("metadata", {}).get("doc_id"),
            "content": (item.get("document") or "")[:200],
            "relevance": item.get("similarity")
        })
    return sources


def _retrieval_metadata(sources: List[Dict[str, Any]]) -> tuple:
    """Return (retrieved_doc_ids, retrieval_scores) from sources. Empty arrays if no retrieval."""
    if not sources:
        return [], []
    doc_ids: List[str] = []
    scores: List[float] = []
    for s in sources:
        doc_id = s.get("id") or (s.get("metadata") or {}).get("document_id") or (s.get("metadata") or {}).get("doc_id")
        doc_ids.append(str(doc_id) if doc_id is not None else "")
        sc = s.get("confidence") or s.get("relevance")
        scores.append(round(float(sc), 4) if sc is not None else 0.0)
    return doc_ids, scores


def _retrieval_confidence(sources: List[Dict[str, Any]]) -> float:
    """Average top-k similarity from retriever (FAQ confidence, KB relevance, vector similarity). 0 if no sources."""
    _, scores = _retrieval_metadata(sources)
    if not scores:
        return 0.0
    # Normalize KB relevance if it's on 0-10 scale (knowledge_base_system uses 0-10)
    normalized = []
    for s in scores:
        if s <= 1.0:
            normalized.append(s)
        else:
            normalized.append(min(1.0, s / 10.0))
    return round(sum(normalized) / len(normalized), 4)


def _combine_confidence(retrieval_conf: float, llm_conf: Optional[float], weight_retrieval: float = 0.5) -> float:
    """Combine retriever and LLM confidence. If llm_conf is None, use retrieval only (or low default)."""
    if llm_conf is None:
        return round(retrieval_conf if retrieval_conf > 0 else 0.2, 4)
    combined = weight_retrieval * retrieval_conf + (1.0 - weight_retrieval) * llm_conf
    return round(min(1.0, max(0.0, combined)), 4)


def _api_key_user_id_as_int(user_id: Optional[Any]) -> Optional[int]:
    if user_id is None or isinstance(user_id, bool):
        return None
    if isinstance(user_id, int):
        return user_id
    if isinstance(user_id, str):
        s = user_id.strip()
        if s.isdigit():
            try:
                return int(s)
            except ValueError:
                return None
    return None


def _low_confidence_message() -> str:
    """Response when combined confidence is below threshold."""
    return (
        "I may be missing some context for that. Could you rephrase or add a few more details? "
        "If you'd like, I can connect you with our team for more help."
    )


def _is_production_env() -> bool:
    return (os.getenv("FLASK_ENV") or "").strip().lower() == "production"


def _public_error_payload(message: str, error_code: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": False, "error": message}
    payload.update(extra)
    if not _is_production_env() and error_code:
        payload["error_code"] = error_code
    return payload


def _confidence_threshold() -> float:
    """Minimum combined confidence to show the model answer; below this we show clarifying message."""
    try:
        return float(os.getenv("CHATBOT_CONFIDENCE_THRESHOLD", "0.4"))
    except ValueError:
        return 0.4


def _sources_to_snippets(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert _build_sources output to canonical KnowledgeSnippet shape."""
    snippets = []
    for s in sources:
        t = s.get("type", "")
        sid = s.get("id")
        source_id = str(sid) if sid is not None else None
        if t == "faq":
            q, a = s.get("question") or "", s.get("answer") or ""
            content = a or q
            snippets.append(knowledge_snippet("faq", content, question=q, answer=a, source_id=source_id, confidence=s.get("confidence")))
        elif t == "knowledge_base":
            content = s.get("content") or ""
            snippets.append(knowledge_snippet("knowledge_base", content, title=s.get("title"), source_id=source_id, relevance=s.get("relevance")))
        elif t == "vector":
            content = s.get("content") or ""
            snippets.append(knowledge_snippet("vector", content, source_id=source_id, relevance=s.get("relevance")))
        else:
            snippets.append(knowledge_snippet(t, s.get("content", ""), source_id=source_id))
    return snippets


def _build_context_snippets(sources: List[Dict[str, Any]]) -> str:
    """Build prompt context string from retrieval sources (canonical KnowledgeSnippet → string)."""
    return snippets_to_context_string(_sources_to_snippets(sources))


def _safe_fallback_response() -> str:
    return "I don't have enough verified information to answer that. If you share more details or contact info, I can connect you with our team."


def _parse_request_api_key() -> Optional[str]:
    """Read API key from X-API-Key or Authorization: Bearer."""
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key[7:]
    if not api_key or not str(api_key).strip():
        return None
    return str(api_key).strip()


def _scopes_allow_for_endpoint(key_info: Dict[str, Any], endpoint: str) -> bool:
    """Whether key scopes satisfy the route (matches prior require_api_key rules)."""
    allowed_scopes = set(key_info.get("scopes", []))
    if not endpoint:
        return "chatbot:query" in allowed_scopes
    if endpoint.startswith("ai_analysis."):
        return "ai:analyze" in allowed_scopes
    required_scope = f"{endpoint.split('.')[-1]}:query"
    return required_scope in allowed_scopes or "chatbot:query" in allowed_scopes


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = _parse_request_api_key()

        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required",
                "error_code": "MISSING_API_KEY"
            }), 401

        # Validate API key
        key_info = api_key_manager.validate_api_key(api_key)
        if not key_info:
            return jsonify({
                "success": False,
                "error": "Invalid or expired API key",
                "error_code": "INVALID_API_KEY"
            }), 401

        endpoint = request.endpoint or ""
        if not _scopes_allow_for_endpoint(key_info, endpoint):
            required_scope = (
                "ai:analyze"
                if endpoint.startswith("ai_analysis.")
                else f"{endpoint.split('.')[-1]}:query" if endpoint else "chatbot:query"
            )
            return jsonify({
                "success": False,
                "error": f"Insufficient permissions. Required scope: {required_scope}",
                "error_code": "INSUFFICIENT_SCOPE"
            }), 403
        
        # Check both short burst and sustained usage rate limits.
        minute_limit_result = api_key_manager.check_rate_limit(key_info['api_key_id'], 'minute')
        hour_limit_result = api_key_manager.check_rate_limit(key_info['api_key_id'], 'hour')
        if not minute_limit_result['allowed'] or not hour_limit_result['allowed']:
            active_limit = minute_limit_result if not minute_limit_result['allowed'] else hour_limit_result
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": 60 if not minute_limit_result['allowed'] else 3600,
                "limit": active_limit['limit'],
                "remaining": active_limit['remaining']
            }), 429
        
        # Store key info in Flask g for use in route handlers
        g.api_key_info = key_info
        g.api_key_id = key_info['api_key_id']
        g.api_key = api_key  # Store for usage tracking
        
        return f(*args, **kwargs)
    
    return decorated_function


def record_api_usage(response_status: int = None, response_time_ms: int = None):
    """Record API usage after request"""
    try:
        if hasattr(g, 'api_key_id'):
            api_key_manager.record_usage(
                api_key_id=g.api_key_id,
                endpoint=request.endpoint or request.path,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                response_status=response_status,
                response_time_ms=response_time_ms
            )
    except Exception as e:
        logger.error(f"Failed to record API usage: {e}")


@public_chatbot_bp.route("/key-status", methods=["GET", "OPTIONS"])
@handle_api_errors
def public_chatbot_key_status():
    """
    Lightweight key check for embeds. Always returns HTTP 200 with JSON so clients
    can validate keys without 401 noise in the browser network tab.
    """
    if request.method == "OPTIONS":
        return "", 204

    raw = _parse_request_api_key()
    if not raw:
        payload = {
            "success": True,
            "valid": False,
            "message": "Send header X-API-Key with your Fikiri API key.",
        }
        if not _is_production_env():
            payload["error_code"] = "MISSING_API_KEY"
        return (
            jsonify(payload),
            200,
        )

    key_info = api_key_manager.validate_api_key(raw)
    if not key_info:
        payload = {
            "success": True,
            "valid": False,
            "message": "This API key is not valid or was revoked.",
        }
        if not _is_production_env():
            payload["error_code"] = "INVALID_API_KEY"
        return (
            jsonify(payload),
            200,
        )

    query_endpoint = "public_chatbot.public_chatbot_query"
    if not _scopes_allow_for_endpoint(key_info, query_endpoint):
        payload = {
            "success": True,
            "valid": False,
            "message": "This API key does not include chatbot query access.",
        }
        if not _is_production_env():
            payload["error_code"] = "INSUFFICIENT_SCOPE"
        return (
            jsonify(payload),
            200,
        )

    return jsonify({"success": True, "valid": True}), 200


@public_chatbot_bp.route('/query', methods=['POST', 'OPTIONS'])
@handle_api_errors
@require_api_key
def public_chatbot_query():
    """
    Public chatbot query endpoint for external clients
    
    Request:
        POST /api/public/chatbot/query
        Headers:
            X-API-Key: fik_...
        Body:
            {
                "query": "What are your business hours?",
                "conversation_id": "optional-conversation-id",
                "context": {"user_id": "optional", "session_id": "optional"}
            }
    
    Response:
        {
            "success": true,
            "query": "What are your business hours?",
            "response": "We're open Monday-Friday 9am-5pm EST.",
            "sources": [...],
            "confidence": 0.95,
            "conversation_id": "generated-or-provided-id"
        }
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        data = request.json or {}
        query = data.get('query', '').strip()
        conversation_id = data.get('conversation_id')
        context = data.get('context', {})
        lead_payload = data.get("lead") or {}
        
        if not query:
            record_api_usage(response_status=400)
            return jsonify(_public_error_payload("Query is required", "MISSING_QUERY")), 400

        correlation_id = get_or_create_correlation_id(request, data)
        
        # Get tenant isolation from API key
        tenant_id = g.api_key_info.get('tenant_id')
        user_id = g.api_key_info.get('user_id')
        
        # Use tenant-specific context if available
        if tenant_id:
            context['tenant_id'] = tenant_id
        
        # Search FAQs + knowledge base (tenant-scoped FAQs when numeric user_id on API key)
        tenant_scope_uid = _api_key_user_id_as_int(user_id)
        faq_results = faq_system.search_faqs(
            query, max_results=3, user_id=tenant_scope_uid
        )
        # Pass tenant_id filter for multi-tenant isolation
        kb_filters = {}
        if tenant_id:
            kb_filters['tenant_id'] = tenant_id
        kb_results = knowledge_base.search(query, filters=kb_filters, limit=3)

        # Optional vector retrieval (feature flagged)
        vector_results = []
        flags = get_feature_flags()
        if flags.is_enabled("vector_search"):
            try:
                # Pass tenant_id for multi-tenant isolation
                vector_results = get_vector_search().search_similar(
                    query, 
                    top_k=3, 
                    threshold=0.6,
                    tenant_id=tenant_id
                )
            except Exception as vector_error:
                logger.warning("Vector search failed: %s", vector_error)
        
        # Get or create conversation context
        if not conversation_id:
            conversation = context_system.start_conversation(
                user_id=user_id,
                initial_message=query,
                session_id=context.get("session_id"),
                channel='api',
                user_context={"tenant_id": tenant_id, **context}
            )
            conversation_id = conversation.conversation_id

        sources = _build_sources(faq_results, kb_results, vector_results)
        context_snippets = _build_context_snippets(sources)
        fallback_needed = not bool(context_snippets.strip())

        plan_info = _check_plan_access(user_id)
        allow_llm = plan_info.get("allow_llm", True)
        if not allow_llm:
            record_api_usage(response_status=402)
            return jsonify(_public_error_payload("Plan limit exceeded", "PLAN_LIMIT_EXCEEDED")), 402

        answer = _safe_fallback_response()
        llm_confidence: Optional[float] = 0.2
        fallback_used = True
        llm_trace_id = None
        llm_attempted = False
        if allow_llm and not fallback_needed:
            budget_decision = ai_budget_guardrails.evaluate(user_id, projected_increment=1)
            if not budget_decision.allowed:
                record_api_usage(response_status=402)
                return jsonify(
                    _public_error_payload(
                        "AI monthly budget cap reached. Upgrade or wait until next billing period."
                        if budget_decision.reason == "monthly_budget_cap_reached"
                        else "AI monthly budget approval required.",
                        "AI_BUDGET_SOFT_STOP",
                        tier=budget_decision.tier,
                        month=budget_decision.month,
                        budget_cap_usd=budget_decision.budget_cap_usd,
                        estimated_cost_usd=budget_decision.estimated_cost_usd,
                        projected_cost_usd=budget_decision.projected_cost_usd,
                        requires_approval=budget_decision.requires_approval,
                    )
                ), 402

            router = LLMRouter()
            prompt = (
                "You are a customer support chatbot. Use ONLY the provided context.\n"
                "If the context does not support an answer, say you don't have enough verified information.\n"
                "Never invent details or make unsupported claims.\n\n"
                f"Context:\n{context_snippets}\n\n"
                f"User question: {query}\n\n"
                "Return JSON with fields: answer, confidence (0-1), fallback_used (true/false), sources (list of source ids), follow_up (optional).\n"
            )
            llm_result = router.process(
                input_data=prompt,
                intent="chatbot_response",
                output_schema=CHATBOT_RESPONSE_SCHEMA_V1,
                context={
                    "conversation_id": conversation_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
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

        # Combine retriever similarity and LLM self-check; apply low-confidence override
        retrieval_conf = _retrieval_confidence(sources)
        confidence = _combine_confidence(retrieval_conf, llm_confidence)
        threshold = _confidence_threshold()
        if confidence < threshold:
            answer = _low_confidence_message()
            fallback_used = True

        # Lead capture (optional)
        lead_info = _extract_lead_info(query, lead_payload)
        lead_id = None
        if user_id and (lead_info.get("email") or lead_info.get("phone")):
            try:
                if lead_info.get("email"):
                    existing = db_optimizer.execute_query(
                        "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                        (user_id, lead_info["email"])
                    )
                    if existing:
                        lead_id = existing[0]["id"]
                    else:
                        created = enhanced_crm_service.create_lead(
                            user_id,
                            {
                                "email": lead_info["email"],
                                "name": lead_info.get("name") or "Chatbot Lead",
                                "phone": lead_info.get("phone"),
                                "source": "chatbot_widget",
                                "metadata": {
                                    "conversation_id": conversation_id,
                                    "tenant_id": tenant_id
                                }
                            }
                        )
                        lead_id = created.get("data", {}).get("lead_id") if created.get("success") else None
                if lead_id:
                    enhanced_crm_service.add_lead_activity(
                        lead_id,
                        user_id,
                        "note_added",
                        "Chatbot conversation captured lead info",
                        metadata={"conversation_id": conversation_id, "query": query}
                    )
            except Exception as lead_error:
                logger.warning("Lead capture failed: %s", lead_error)
        
        # Check if escalation is needed
        escalation_engine = get_escalation_engine()
        should_escalate = escalation_engine.should_escalate(confidence, fallback_used)
        escalated_question_id = None
        
        if should_escalate:
            escalation_result = escalation_engine.escalate_question(
                conversation_id=conversation_id,
                tenant_id=tenant_id or str(user_id or 'anonymous'),
                question=query,
                original_answer=answer,
                confidence=confidence,
                user_id=str(user_id) if user_id else None
            )
            if escalation_result.get('success'):
                escalated_question_id = escalation_result.get('escalated_question_id')
                # Update answer to include escalation option
                answer = (
                    f"{answer}\n\n"
                    f"I've also shared your question with our expert team. "
                    f"If you'd like to speak with someone directly, they'll be in touch soon."
                )
        
        # Log query/response and confidence breakdown for feedback evaluation
        message_id = str(uuid.uuid4())
        log_metadata = {
            "retrieval_confidence": retrieval_conf,
            "llm_confidence": llm_confidence,
            "confidence_threshold": threshold,
        }
        content_fp = content_fingerprint_from_sources(sources)
        try:
            if db_optimizer.table_exists("chatbot_query_log"):
                meta_json = json.dumps(log_metadata)[:10000]
                base_params = (
                    conversation_id,
                    message_id,
                    query[:10000] if query else "",
                    answer[:50000] if answer else "",
                    confidence,
                    fallback_used,
                    json.dumps(sources)[:50000] if sources else "[]",
                    str(tenant_id) if tenant_id is not None else None,
                    str(user_id) if user_id is not None else None,
                    llm_trace_id,
                )
                try:
                    db_optimizer.execute_query(
                        """INSERT INTO chatbot_query_log
                           (conversation_id, message_id, query, response, confidence, fallback_used, sources_json, tenant_id, user_id, llm_trace_id, metadata, correlation_id, content_fingerprint)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        base_params + (meta_json, correlation_id, content_fp or None),
                        fetch=False,
                    )
                except Exception:
                    try:
                        db_optimizer.execute_query(
                            """INSERT INTO chatbot_query_log
                               (conversation_id, message_id, query, response, confidence, fallback_used, sources_json, tenant_id, user_id, llm_trace_id, metadata, correlation_id)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            base_params + (meta_json, correlation_id),
                            fetch=False,
                        )
                    except Exception:
                        try:
                            db_optimizer.execute_query(
                                """INSERT INTO chatbot_query_log
                                   (conversation_id, message_id, query, response, confidence, fallback_used, sources_json, tenant_id, user_id, llm_trace_id, metadata)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                base_params + (meta_json,),
                                fetch=False,
                            )
                        except Exception:
                            db_optimizer.execute_query(
                                """INSERT INTO chatbot_query_log
                                   (conversation_id, message_id, query, response, confidence, fallback_used, sources_json, tenant_id, user_id, llm_trace_id)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                base_params,
                                fetch=False,
                            )
        except Exception as log_err:
            logger.warning("Chatbot query log insert failed: %s", log_err)

        record_chatbot_response_generated(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=tenant_scope_uid,
            correlation_id=correlation_id,
            query_excerpt=query,
            response_excerpt=answer,
            sources=sources,
            content_fingerprint=content_fp,
            llm_trace_id=llm_trace_id,
            confidence=confidence,
            fallback_used=fallback_used,
        )

        
        # Calculate response time
        response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Record usage
        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        _record_billing_usage(user_id, "chatbot_queries", 1)
        if llm_attempted and llm_result.get("success"):
            ai_budget_guardrails.record_ai_usage(user_id, 1)
        
        retrieved_doc_ids, retrieval_scores = _retrieval_metadata(sources)
        
        response = {
            "success": True,
            "query": query,
            "response": answer,
            "sources": sources,
            "retrieved_doc_ids": retrieved_doc_ids,
            "retrieval_scores": retrieval_scores,
            "confidence": confidence,
            "retrieval_confidence": retrieval_conf,
            "llm_confidence": llm_confidence,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "tenant_id": tenant_id,
            "schema_version": "v1",
            "fallback_used": fallback_used,
            "plan": plan_info.get("plan"),
            "lead_id": lead_id,
            "escalated": should_escalate,
            "escalated_question_id": escalated_question_id,
            "ai_usage_recorded": bool(llm_attempted)
        }
        if not _is_production_env():
            response["correlation_id"] = correlation_id
            response["llm_trace_id"] = llm_trace_id
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Public chatbot query failed: {e}", exc_info=True)
        record_api_usage(response_status=500)
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


@public_chatbot_bp.route('/feedback', methods=['POST', 'OPTIONS'])
@handle_api_errors
@require_api_key
def submit_feedback():
    """Submit feedback on a chatbot answer"""
    try:
        data = request.json or {}
        conversation_id = data.get('conversation_id', '').strip()
        helpful = data.get('helpful', True)
        feedback_text = data.get('feedback_text', '').strip()
        message_id = data.get('message_id')
        confidence = data.get('confidence')
        metadata = data.get('metadata')
        if isinstance(metadata, dict):
            if confidence is not None:
                metadata = {**metadata, "confidence_score": confidence}
        elif confidence is not None:
            metadata = {"confidence_score": confidence}
        else:
            metadata = None

        if not conversation_id:
            response = {
                "success": False,
                "error": "Please include the conversation id for this feedback.",
            }
            if not _is_production_env():
                response["error_code"] = "MISSING_FIELD"
            return jsonify(response), 400

        tenant_id = g.api_key_info.get('tenant_id')
        user_id = g.api_key_info.get('user_id')
        correlation_id = get_or_create_correlation_id(request, data)

        feedback_system = get_feedback_system()
        result = feedback_system.record_feedback(
            conversation_id=conversation_id,
            helpful=helpful,
            feedback_text=feedback_text,
            message_id=message_id,
            user_id=str(user_id) if user_id else None,
            metadata=metadata,
        )
        feedback_router = get_user_feedback_router()
        feedback_router.record_feedback_event(
            source="api.public_chatbot.feedback",
            user_id=str(user_id) if user_id is not None else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            category="chatbot",
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            payload={
                "helpful": bool(helpful),
                "feedback_text": feedback_text,
                "confidence": confidence,
                "metadata": metadata if isinstance(metadata, dict) else {},
            },
            idempotency_key=data.get("idempotency_key"),
        )
        
        if not result.get('success'):
            logger.error("Public feedback persistence failed: %s", result)
            response = {
                "success": False,
                "error": "We couldn't save your feedback right now. Please try again.",
            }
            if not _is_production_env():
                response["error_code"] = result.get('error_code', 'FEEDBACK_ERROR')
            return jsonify(response), 500
        
        return jsonify({
            "success": True,
            "feedback_id": result.get('feedback_id'),
            "message": "Thanks for your feedback."
        })
        
    except Exception as e:
        logger.error(f"❌ Feedback submission failed: {e}", exc_info=True)
        if _is_production_env():
            return jsonify({
                "success": False,
                "error": "We couldn't save your feedback right now. Please try again.",
            }), 500
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


@public_chatbot_bp.route('/evaluation', methods=['GET', 'OPTIONS'])
@handle_api_errors
@require_api_key
def get_evaluation():
    """Get chatbot evaluation stats (query log + feedback joined). Scoped to tenant from API key."""
    try:
        tenant_id = g.api_key_info.get('tenant_id')
        since = request.args.get('since')
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                pass
        feedback_system = get_feedback_system()
        stats = feedback_system.get_evaluation_stats(tenant_id=tenant_id, since=since_dt)
        return jsonify({"success": True, "evaluation": stats})
    except Exception as e:
        logger.error("Evaluation endpoint failed: %s", e)
        return create_error_response("Evaluation failed", 500, 'EVALUATION_ERROR')


@public_chatbot_bp.route('/health', methods=['GET', 'OPTIONS'])
def public_chatbot_health():
    """
    Health check endpoint (no auth required)
    
    Response:
        {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "service": "public-chatbot-api"
    })


@public_chatbot_bp.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    # Allow all origins for public API (can be restricted per tenant if needed)
    origin = request.headers.get('Origin')
    
    # In production, validate origin against allowed list
    # For now, allow all origins for public API
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    
    return response
