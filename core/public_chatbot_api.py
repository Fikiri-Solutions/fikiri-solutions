"""
Public Chatbot API for External Clients
Provides embeddable chatbot endpoint with API key authentication, CORS, and tenant isolation
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from functools import wraps

from core.api_key_manager import api_key_manager
from core.chatbot_smart_faq_api import get_vector_search
from core.smart_faq_system import get_smart_faq
from core.knowledge_base_system import get_knowledge_base
from core.context_aware_responses import get_context_system
from core.api_validation import handle_api_errors, create_error_response
from core.ai.llm_router import LLMRouter
from core.database_optimization import db_optimizer
from core.feature_flags import get_feature_flags
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)

# Create Blueprint for public API
public_chatbot_bp = Blueprint('public_chatbot', __name__, url_prefix='/api/public/chatbot')

# Initialize systems
faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()
context_system = get_context_system()

CHATBOT_RESPONSE_SCHEMA_V1 = {
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
        month = datetime.utcnow().strftime("%Y-%m")
        db_optimizer.execute_query(
            "INSERT INTO billing_usage (user_id, month, usage_type, quantity) VALUES (?, ?, ?, ?)",
            (user_id, month, usage_type, quantity),
            fetch=False
        )
    except Exception as e:
        logger.warning("Failed to record billing usage: %s", e)


def _check_plan_access(user_id: Optional[int]) -> Dict[str, Any]:
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


def _build_context_snippets(sources: List[Dict[str, Any]]) -> str:
    snippets = []
    for source in sources:
        if source["type"] == "faq":
            snippets.append(f"FAQ: Q={source.get('question')} A={source.get('answer')}")
        elif source["type"] == "knowledge_base":
            snippets.append(f"KB: {source.get('title')}: {source.get('content')}")
        elif source["type"] == "vector":
            snippets.append(f"KB: {source.get('content')}")
    return "\n".join(snippets)


def _safe_fallback_response() -> str:
    return "I don't have enough verified information to answer that. If you share more details or contact info, I can connect you with our team."


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        # Extract from Bearer token format
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
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
        
        # Check required scope (chatbot vs AI analysis)
        allowed_scopes = set(key_info.get('scopes', []))
        endpoint = request.endpoint or ""
        if endpoint.startswith("ai_analysis."):
            required_scope = "ai:analyze"
            has_scope = required_scope in allowed_scopes
        else:
            required_scope = f"{endpoint.split('.')[-1]}:query" if endpoint else "chatbot:query"
            has_scope = required_scope in allowed_scopes or "chatbot:query" in allowed_scopes
        if not has_scope:
            return jsonify({
                "success": False,
                "error": f"Insufficient permissions. Required scope: {required_scope}",
                "error_code": "INSUFFICIENT_SCOPE"
            }), 403
        
        # Check rate limit
        rate_limit_result = api_key_manager.check_rate_limit(key_info['api_key_id'], 'minute')
        if not rate_limit_result['allowed']:
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": 60,
                "limit": rate_limit_result['limit'],
                "remaining": rate_limit_result['remaining']
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
    start_time = datetime.utcnow()
    
    try:
        data = request.json or {}
        query = data.get('query', '').strip()
        conversation_id = data.get('conversation_id')
        context = data.get('context', {})
        lead_payload = data.get("lead") or {}
        
        if not query:
            record_api_usage(response_status=400)
            return jsonify({
                "success": False,
                "error": "Query is required",
                "error_code": "MISSING_QUERY"
            }), 400
        
        # Get tenant isolation from API key
        tenant_id = g.api_key_info.get('tenant_id')
        user_id = g.api_key_info.get('user_id')
        
        # Use tenant-specific context if available
        if tenant_id:
            context['tenant_id'] = tenant_id
        
        # Search FAQs + knowledge base
        faq_results = faq_system.search_faqs(query, max_results=3)
        kb_results = knowledge_base.search(query, {}, limit=3)

        # Optional vector retrieval (feature flagged)
        vector_results = []
        flags = get_feature_flags()
        if flags.is_enabled("vector_search"):
            try:
                vector_results = get_vector_search().search_similar(query, top_k=3, threshold=0.6)
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
            return jsonify({
                "success": False,
                "error": "Plan limit exceeded",
                "error_code": "PLAN_LIMIT_EXCEEDED"
            }), 402

        answer = _safe_fallback_response()
        confidence = 0.2
        fallback_used = True
        llm_trace_id = None
        if allow_llm and not fallback_needed:
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
                context={"conversation_id": conversation_id, "tenant_id": tenant_id}
            )
            if llm_result.get("success") and llm_result.get("validated"):
                try:
                    parsed = json.loads(llm_result.get("content", "{}"))
                    answer = parsed.get("answer") or answer
                    confidence = parsed.get("confidence", confidence)
                    fallback_used = bool(parsed.get("fallback_used", False))
                except json.JSONDecodeError:
                    logger.warning("LLM response not JSON; using fallback")
            else:
                logger.warning("LLM response invalid: %s", llm_result.get("error"))
            llm_trace_id = llm_result.get("trace_id")

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
        
        # Calculate response time
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Record usage
        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        _record_billing_usage(user_id, "chatbot_queries", 1)
        
        return jsonify({
            "success": True,
            "query": query,
            "response": answer,
            "sources": sources,
            "confidence": confidence,
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "schema_version": "v1",
            "fallback_used": fallback_used,
            "plan": plan_info.get("plan"),
            "llm_trace_id": llm_trace_id,
            "lead_id": lead_id
        })
        
    except Exception as e:
        logger.error(f"❌ Public chatbot query failed: {e}", exc_info=True)
        record_api_usage(response_status=500)
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


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
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
