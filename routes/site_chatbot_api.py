"""HTTP routes for the first-party Fikiri marketing site chatbot."""

import logging

from flask import Blueprint, request

from company_chatbot import config
from company_chatbot.orchestrator import handle_message, start_session
from company_chatbot.rate_limit import check_message_limits, check_session_start_limits
from core.api_validation import create_error_response, create_success_response, handle_api_errors

logger = logging.getLogger(__name__)

site_chatbot_bp = Blueprint("site_chatbot", __name__, url_prefix="/api/site/chat")

_SITE_BOT_DISABLED_MESSAGE = (
    "The Fikiri site assistant is temporarily unavailable. "
    "Please use our contact page or email info@fikirisolutions.com."
)
_RATE_LIMIT_MESSAGE = (
    "You're sending messages a bit too quickly. Please wait a moment and try again."
)

config.log_site_bot_config_warnings(logger)


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.remote_addr or "unknown").strip()


def _disabled_response():
    return create_error_response(
        _SITE_BOT_DISABLED_MESSAGE,
        503,
        "SITE_BOT_DISABLED",
    )


def _rate_limit_response(retry_after: int):
    response, status = create_error_response(
        _RATE_LIMIT_MESSAGE,
        429,
        "RATE_LIMIT_EXCEEDED",
    )
    response.headers["Retry-After"] = str(max(1, retry_after))
    return response, status


@site_chatbot_bp.route("/session/start", methods=["POST", "OPTIONS"])
@handle_api_errors
def site_chat_session_start():
    if request.method == "OPTIONS":
        return "", 204

    if not config.site_bot_enabled():
        return _disabled_response()

    limit = check_session_start_limits(_client_ip())
    if not limit.allowed:
        return _rate_limit_response(limit.retry_after_seconds)

    result = start_session()
    return create_success_response(
        result.to_dict(config.SCHEMA_VERSION),
        "Site chat session started",
    )


@site_chatbot_bp.route("/message", methods=["POST", "OPTIONS"])
@handle_api_errors
def site_chat_message():
    if request.method == "OPTIONS":
        return "", 204

    if not config.site_bot_enabled():
        return _disabled_response()

    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    message = (data.get("message") or "").strip()

    if not session_id:
        return create_error_response("session_id is required", 400, "MISSING_SESSION_ID")
    if not message:
        return create_error_response("message is required", 400, "MISSING_MESSAGE")

    limit = check_message_limits(_client_ip(), session_id)
    if not limit.allowed:
        return _rate_limit_response(limit.retry_after_seconds)

    try:
        result = handle_message(session_id, message)
    except KeyError:
        return create_error_response("Invalid or expired session", 404, "SESSION_NOT_FOUND")

    from company_chatbot.transcript_store import persist_message_turn

    persist_message_turn(
        session_id=session_id,
        user_message=message,
        result=result,
        source_page=(request.headers.get("Referer") or data.get("source_page") or "").strip() or None,
        client_ip=_client_ip(),
        user_agent=(request.headers.get("User-Agent") or "").strip() or None,
    )

    return create_success_response(
        {**result.to_dict(config.SCHEMA_VERSION), "session_id": session_id},
        "Site chat message processed",
    )
