"""
Public Chatbot API for External Clients
Provides embeddable chatbot endpoint with API key authentication, CORS, and tenant isolation
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from functools import wraps

from core.api_key_manager import api_key_manager
from core.context_aware_responses import get_context_system
from core.api_validation import handle_api_errors, create_error_response
from core.database_optimization import db_optimizer
from core.expert_escalation import get_escalation_engine
from core.chatbot_feedback import get_feedback_system
from core.chatbot_content_events import (
    content_fingerprint_from_sources,
    record_chatbot_response_generated,
)
from core.request_correlation import get_or_create_correlation_id
from core.user_feedback_router import get_user_feedback_router
from core.chatbot_config import ChatbotConfig, load_chatbot_config
from core.chatbot_lead_capture import capture_chatbot_lead
from core.chatbot_retrieval import retrieve_chatbot_context, retrieval_metadata
from core.chatbot_response_service import generate_chatbot_answer
from core.chatbot_usage_tracking import (
    check_chatbot_usage_allowed,
    record_chatbot_ai_usage_if_needed,
    record_chatbot_billing_usage,
    record_chatbot_request_usage,
)

logger = logging.getLogger(__name__)

# Create Blueprint for public API
public_chatbot_bp = Blueprint('public_chatbot', __name__, url_prefix='/api/public/chatbot')

context_system = get_context_system()


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


def _is_production_env() -> bool:
    return (os.getenv("FLASK_ENV") or "").strip().lower() == "production"


def _public_error_payload(message: str, error_code: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": False, "error": message}
    payload.update(extra)
    if not _is_production_env() and error_code:
        payload["error_code"] = error_code
    return payload


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

        g.api_key_info = key_info
        g.api_key_id = key_info['api_key_id']
        g.api_key = api_key

        return f(*args, **kwargs)

    return decorated_function


def record_api_usage(response_status: int = None, response_time_ms: int = None):
    """Record API usage after request"""
    key_info = getattr(g, "api_key_info", None) or {}
    record_chatbot_request_usage(
        api_key_id=getattr(g, "api_key_id", None),
        endpoint=request.endpoint or request.path,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        response_status=response_status,
        response_time_ms=response_time_ms,
        user_id=key_info.get("user_id"),
        tenant_id=key_info.get("tenant_id"),
    )


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

        tenant_id = g.api_key_info.get('tenant_id')
        user_id = g.api_key_info.get('user_id')

        if tenant_id:
            context['tenant_id'] = tenant_id

        tenant_scope_uid = _api_key_user_id_as_int(user_id)
        billing_uid = tenant_scope_uid
        if billing_uid is None and isinstance(user_id, int) and not isinstance(user_id, bool):
            billing_uid = user_id

        if not conversation_id:
            conversation = context_system.start_conversation(
                user_id=user_id,
                initial_message=query,
                session_id=context.get("session_id"),
                channel='api',
                user_context={"tenant_id": tenant_id, **context}
            )
            conversation_id = conversation.conversation_id

        retrieval = retrieve_chatbot_context(
            query,
            tenant_id,
            tenant_scope_uid,
            correlation_id=correlation_id,
        )

        try:
            chatbot_config = load_chatbot_config(billing_uid, tenant_id=tenant_id)
        except Exception as config_exc:
            logger.warning(
                "chatbot_config load failed; using defaults: %s",
                config_exc,
                extra={
                    "event": "chatbot_config_load_warning",
                    "user_id": billing_uid,
                    "tenant_id": tenant_id,
                },
            )
            chatbot_config = ChatbotConfig()

        usage_gate = check_chatbot_usage_allowed(
            user_id=user_id,
            billing_uid=billing_uid,
            fallback_needed=retrieval.fallback_needed,
            tenant_id=tenant_id,
        )
        if not usage_gate.allowed:
            record_api_usage(response_status=usage_gate.http_status)
            return jsonify(
                _public_error_payload(
                    usage_gate.error_message or "Plan limit exceeded",
                    usage_gate.error_code,
                    **usage_gate.error_extra,
                )
            ), usage_gate.http_status

        plan_info = usage_gate.plan_info
        allow_llm = usage_gate.allow_llm

        llm_result_meta: Dict[str, Any] = {}
        answer_result = generate_chatbot_answer(
            query,
            retrieval.context_text,
            retrieval.sources,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            billing_uid=billing_uid,
            fallback_needed=retrieval.fallback_needed,
            allow_llm=allow_llm,
            chatbot_config=chatbot_config,
        )

        answer = answer_result.answer
        confidence = answer_result.confidence
        llm_confidence = answer_result.llm_confidence
        fallback_used = answer_result.fallback_used
        llm_trace_id = answer_result.llm_trace_id
        retrieval_conf = answer_result.retrieval_confidence
        threshold = answer_result.response_metadata.get("confidence_threshold", 0.4)
        llm_attempted = answer_result.response_metadata.get("llm_attempted", False)
        llm_result_meta = answer_result.response_metadata

        lead_id = capture_chatbot_lead(
            user_id=user_id,
            query=query,
            lead_payload=lead_payload,
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            chatbot_config=chatbot_config,
        )

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
                answer = f"{answer}\n\n{chatbot_config.escalation_message}"

        message_id = str(uuid.uuid4())
        log_metadata = {
            "retrieval_confidence": retrieval_conf,
            "llm_confidence": llm_confidence,
            "confidence_threshold": threshold,
        }
        sources = retrieval.sources
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

        response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        if billing_uid is not None:
            record_chatbot_billing_usage(
                billing_uid,
                "chatbot_queries",
                1,
                tenant_id=str(tenant_id) if tenant_id is not None else None,
            )
        ai_usage_recorded = record_chatbot_ai_usage_if_needed(
            billing_uid=billing_uid,
            llm_attempted=llm_attempted,
            llm_result_meta=llm_result_meta,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
        )

        retrieved_doc_ids, retrieval_scores = retrieval_metadata(sources)

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
            "ai_usage_recorded": ai_usage_recorded,
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
    origin = request.headers.get('Origin')

    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'

    return response
