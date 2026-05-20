"""
Per-tenant chatbot configuration (read path only).

Merges safe global defaults, optional ``data/business_profile.json``, ``users``
row fields, ``users.metadata.chatbot`` (whitelisted keys), and
``user_services`` settings for service_id ``chatbot`` (then ``ai-assistant`` tone).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK = (
    "I don't have enough verified information to answer that. "
    "If you share more details or contact info, I can connect you with our team."
)
_DEFAULT_LOW_CONFIDENCE = (
    "I may be missing some context for that. Could you rephrase or add a few more details? "
    "If you'd like, I can connect you with our team for more help."
)
_DEFAULT_ESCALATION_SUFFIX = (
    "I've also shared your question with our expert team. "
    "If you'd like to speak with someone directly, they'll be in touch soon."
)

# Whitelisted keys only — never merge raw metadata into prompts.
_CHATBOT_CONFIG_KEYS = frozenset({
    "business_name",
    "chatbot_name",
    "tone",
    "fallback_message",
    "escalation_message",
    "allowed_topics",
    "restricted_topics",
    "lead_capture_enabled",
    "lead_capture_prompt",
    "collect_email",
    "collect_phone",
    "answer_style",
    "max_answer_length",
    "disclosure_text",
})

_BLOCKED_CONFIG_KEYS = frozenset({
    "system_prompt",
    "developer_prompt",
    "systemPrompt",
    "developerPrompt",
    "prompt",
    "instructions",
    "raw_metadata",
    "api_key",
    "apiKey",
    "secret",
    "password",
    "token",
})

_CAMEL_TO_SNAKE = {
    "businessName": "business_name",
    "chatbotName": "chatbot_name",
    "responseTone": "tone",
    "fallbackMessage": "fallback_message",
    "escalationMessage": "escalation_message",
    "allowedTopics": "allowed_topics",
    "restrictedTopics": "restricted_topics",
    "leadCaptureEnabled": "lead_capture_enabled",
    "leadCapturePrompt": "lead_capture_prompt",
    "collectEmail": "collect_email",
    "collectPhone": "collect_phone",
    "answerStyle": "answer_style",
    "maxAnswerLength": "max_answer_length",
    "disclosureText": "disclosure_text",
}


@dataclass
class ChatbotConfig:
    business_name: str = "our business"
    chatbot_name: str = "Assistant"
    tone: str = "professional and helpful"
    fallback_message: str = _DEFAULT_FALLBACK
    escalation_message: str = _DEFAULT_ESCALATION_SUFFIX
    allowed_topics: List[str] = field(default_factory=list)
    restricted_topics: List[str] = field(default_factory=list)
    lead_capture_enabled: bool = True
    lead_capture_prompt: str = ""
    collect_email: bool = True
    collect_phone: bool = False
    answer_style: str = "concise"
    max_answer_length: int = 500
    disclosure_text: str = ""

    def low_confidence_message(self) -> str:
        """Clarifying message when combined confidence is below threshold."""
        msg = (self.fallback_message or "").strip()
        if msg and msg != _DEFAULT_FALLBACK:
            return msg
        return _DEFAULT_LOW_CONFIDENCE


def _sanitize_text(value: Any, max_len: int = 500) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text


def _sanitize_topic_list(value: Any, *, max_items: int = 20, max_item_len: int = 80) -> List[str]:
    items: List[str] = []
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            raw = parsed if isinstance(parsed, list) else [s.strip() for s in value.split(",")]
        except json.JSONDecodeError:
            raw = [s.strip() for s in value.split(",")]
    else:
        return []
    for item in raw[:max_items]:
        cleaned = _sanitize_text(item, max_item_len)
        if cleaned:
            items.append(cleaned)
    return items


def _sanitize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _sanitize_max_answer_length(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 500
    return max(50, min(2000, n))


def _normalize_partial(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map camelCase keys to snake_case and keep only whitelisted fields."""
    out: Dict[str, Any] = {}
    for key, val in raw.items():
        snake = _CAMEL_TO_SNAKE.get(key, key if key in _CHATBOT_CONFIG_KEYS else None)
        if snake and snake in _CHATBOT_CONFIG_KEYS:
            out[snake] = val
    return out


def _apply_partial(config: ChatbotConfig, partial: Dict[str, Any]) -> None:
    if not partial:
        return
    normalized = _normalize_partial(partial)
    if "business_name" in normalized:
        config.business_name = _sanitize_text(normalized["business_name"], 120) or config.business_name
    if "chatbot_name" in normalized:
        config.chatbot_name = _sanitize_text(normalized["chatbot_name"], 80) or config.chatbot_name
    if "tone" in normalized:
        config.tone = _sanitize_text(normalized["tone"], 200) or config.tone
    if "fallback_message" in normalized:
        config.fallback_message = _sanitize_text(normalized["fallback_message"], 800) or config.fallback_message
    if "escalation_message" in normalized:
        config.escalation_message = _sanitize_text(normalized["escalation_message"], 800) or config.escalation_message
    if "allowed_topics" in normalized:
        config.allowed_topics = _sanitize_topic_list(normalized["allowed_topics"])
    if "restricted_topics" in normalized:
        config.restricted_topics = _sanitize_topic_list(normalized["restricted_topics"])
    if "lead_capture_enabled" in normalized:
        config.lead_capture_enabled = _sanitize_bool(normalized["lead_capture_enabled"], config.lead_capture_enabled)
    if "lead_capture_prompt" in normalized:
        config.lead_capture_prompt = _sanitize_text(normalized["lead_capture_prompt"], 400)
    if "collect_email" in normalized:
        config.collect_email = _sanitize_bool(normalized["collect_email"], config.collect_email)
    if "collect_phone" in normalized:
        config.collect_phone = _sanitize_bool(normalized["collect_phone"], config.collect_phone)
    if "answer_style" in normalized:
        config.answer_style = _sanitize_text(normalized["answer_style"], 120) or config.answer_style
    if "max_answer_length" in normalized:
        config.max_answer_length = _sanitize_max_answer_length(normalized["max_answer_length"])
    if "disclosure_text" in normalized:
        config.disclosure_text = _sanitize_text(normalized["disclosure_text"], 500)


def _load_file_defaults() -> Dict[str, Any]:
    try:
        path = Path("data/business_profile.json")
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}
        chatbot = data.get("chatbot")
        if isinstance(chatbot, dict):
            return chatbot
        return {}
    except Exception as exc:
        logger.debug("business_profile.json chatbot section not loaded: %s", exc)
        return {}


def load_chatbot_config(
    user_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> ChatbotConfig:
    """
    Load merged chatbot config. Never raises; returns defaults on any failure.
    ``tenant_id`` is reserved for future tenant-scoped stores; not used in this increment.
    """
    _ = tenant_id
    config = ChatbotConfig()
    try:
        _apply_partial(config, _load_file_defaults())
    except Exception as exc:
        logger.warning(
            "chatbot_config file defaults failed",
            extra={"event": "chatbot_config_load_warning", "reason": str(exc)},
        )

    if not user_id:
        return config

    try:
        from core.database_optimization import db_optimizer

        rows = db_optimizer.execute_query(
            """
            SELECT business_name, metadata
            FROM users WHERE id = ? LIMIT 1
            """,
            (user_id,),
        )
        if rows:
            row = rows[0] if isinstance(rows[0], dict) else {}
            if row.get("business_name"):
                config.business_name = _sanitize_text(row["business_name"], 120) or config.business_name
            meta = row.get("metadata")
            if isinstance(meta, str) and meta.strip():
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}
            if isinstance(meta, dict):
                chatbot_meta = meta.get("chatbot")
                if isinstance(chatbot_meta, dict):
                    _apply_partial(config, chatbot_meta)

        from core.user_services import get_service_settings

        chatbot_svc = get_service_settings(user_id, "chatbot")
        if chatbot_svc:
            _apply_partial(config, chatbot_svc)

        ai_svc = get_service_settings(user_id, "ai-assistant")
        has_chatbot_tone = bool(
            chatbot_svc and (chatbot_svc.get("tone") or chatbot_svc.get("responseTone"))
        )
        if ai_svc and ai_svc.get("responseTone") and not has_chatbot_tone:
            _apply_partial(config, {"tone": ai_svc.get("responseTone")})
    except Exception as exc:
        logger.warning(
            "chatbot_config load failed for user %s: %s",
            user_id,
            exc,
            extra={"event": "chatbot_config_load_warning", "user_id": user_id},
        )

    return config


def config_to_dict(config: ChatbotConfig) -> Dict[str, Any]:
    """Public API shape for effective chatbot settings (snake_case)."""
    return {
        "business_name": config.business_name,
        "chatbot_name": config.chatbot_name,
        "tone": config.tone,
        "fallback_message": config.fallback_message,
        "escalation_message": config.escalation_message,
        "allowed_topics": list(config.allowed_topics),
        "restricted_topics": list(config.restricted_topics),
        "lead_capture_enabled": config.lead_capture_enabled,
        "lead_capture_prompt": config.lead_capture_prompt,
        "collect_email": config.collect_email,
        "collect_phone": config.collect_phone,
        "answer_style": config.answer_style,
        "max_answer_length": config.max_answer_length,
        "disclosure_text": config.disclosure_text,
    }


def _load_user_metadata_dict(user_id: int) -> Dict[str, Any]:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        "SELECT metadata FROM users WHERE id = ? LIMIT 1",
        (user_id,),
    )
    if not rows:
        return {}
    row = rows[0] if isinstance(rows[0], dict) else {}
    meta = row.get("metadata")
    if isinstance(meta, str) and meta.strip():
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(meta, dict):
        return dict(meta)
    return {}


def load_stored_chatbot_config(user_id: int) -> Dict[str, Any]:
    """Persisted overrides in ``users.metadata.chatbot`` only (snake_case)."""
    meta = _load_user_metadata_dict(user_id)
    chatbot = meta.get("chatbot")
    if not isinstance(chatbot, dict):
        return {}
    return {k: chatbot[k] for k in chatbot if k in _CHATBOT_CONFIG_KEYS}


def _collect_rejected_keys(raw: Dict[str, Any]) -> List[str]:
    rejected: List[str] = []
    for key in raw:
        snake = _CAMEL_TO_SNAKE.get(key, key)
        if key in _BLOCKED_CONFIG_KEYS or snake in _BLOCKED_CONFIG_KEYS:
            rejected.append(key)
        elif snake not in _CHATBOT_CONFIG_KEYS and key not in _CHATBOT_CONFIG_KEYS and key not in _CAMEL_TO_SNAKE:
            rejected.append(key)
    return rejected


def sanitize_chatbot_config_patch(raw: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    """
    Validate and sanitize a partial config update.
    Returns (snake_case patch dict, rejected field names).
    """
    if not isinstance(raw, dict):
        return {}, ["body"]
    rejected = _collect_rejected_keys(raw)
    normalized = _normalize_partial(raw)
    if not normalized:
        return {}, rejected
    cfg = ChatbotConfig()
    _apply_partial(cfg, normalized)
    patch: Dict[str, Any] = {}
    for key in normalized:
        patch[key] = getattr(cfg, key)
    return patch, rejected


def save_chatbot_config(
    user_id: int,
    patch: Dict[str, Any],
    *,
    source: str,
    correlation_id: Optional[str] = None,
) -> ChatbotConfig:
    """
    Merge ``patch`` into ``users.metadata.chatbot`` and return effective config.
    """
    from core.database_optimization import db_optimizer
    from core.chatbot_content_events import record_chatbot_config_updated

    snapshot_before = load_stored_chatbot_config(user_id)
    meta = _load_user_metadata_dict(user_id)
    chatbot = dict(meta.get("chatbot") or {}) if isinstance(meta.get("chatbot"), dict) else {}
    chatbot.update(patch)
    meta["chatbot"] = chatbot

    db_optimizer.execute_query(
        "UPDATE users SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(meta), user_id),
        fetch=False,
    )

    if "business_name" in patch and patch["business_name"]:
        db_optimizer.execute_query(
            "UPDATE users SET business_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (patch["business_name"], user_id),
            fetch=False,
        )

    snapshot_after = load_stored_chatbot_config(user_id)
    record_chatbot_config_updated(
        user_id=user_id,
        source=source,
        correlation_id=correlation_id,
        config_key=str(user_id),
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
    )

    return load_chatbot_config(user_id)
