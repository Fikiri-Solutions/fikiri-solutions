"""Environment flags and constants for the Fikiri site bot."""

import os
from pathlib import Path

SCHEMA_VERSION = "v1"

MODE_ANSWER = "answer"
MODE_EXPLORE_FIT = "explore_fit"
MODE_WORKFLOW_AUDIT = "workflow_audit"
MODE_CONSULTING = "consulting"
MODE_CONTACT = "contact"
MODE_FALLBACK = "fallback"

PRIMARY_MODES = (
    MODE_ANSWER,
    MODE_EXPLORE_FIT,
    MODE_WORKFLOW_AUDIT,
    MODE_CONSULTING,
    MODE_CONTACT,
)

HANDOFF_PRIMARY_WIDGET = "in_widget_form"
HANDOFF_SECONDARY_INTAKE = "/intake"
HANDOFF_SECONDARY_CONTACT = "/contact"

DEFAULT_GROUNDING_MIN_SCORE = 0.25
DEFAULT_RETRIEVAL_TOP_K = 3


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def kb_data_dir() -> Path:
    override = os.getenv("FIKIRI_SITE_BOT_KB_DIR", "").strip()
    if override:
        return Path(override)
    return project_root() / "data" / "company_chatbot"


def grounding_min_score() -> float:
    raw = os.getenv("FIKIRI_SITE_BOT_GROUNDING_MIN_SCORE", "").strip()
    if not raw:
        return DEFAULT_GROUNDING_MIN_SCORE
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_GROUNDING_MIN_SCORE


def retrieval_top_k() -> int:
    raw = os.getenv("FIKIRI_SITE_BOT_RETRIEVAL_TOP_K", "").strip()
    if not raw:
        return DEFAULT_RETRIEVAL_TOP_K
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_RETRIEVAL_TOP_K


def is_test_mode() -> bool:
    """When true, no OpenAI/model calls (Phase 1 is deterministic regardless)."""
    return os.getenv("FIKIRI_SITE_BOT_TEST_MODE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def is_llm_polish_enabled() -> bool:
    """LLM polish is off until scenario tests pass (Phase 2+)."""
    if is_test_mode():
        return False
    return os.getenv("FIKIRI_SITE_BOT_LLM_POLISH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def site_bot_enabled() -> bool:
    """Kill switch for site bot HTTP routes (default on)."""
    raw = os.getenv("FIKIRI_SITE_BOT_ENABLED", "true").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def session_ttl_seconds() -> int:
    raw = os.getenv("FIKIRI_SITE_BOT_SESSION_TTL_SECONDS", "86400").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 86400


def rate_limit_per_minute() -> int:
    raw = os.getenv("FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE", "20").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 20


def rate_limit_burst() -> int:
    raw = os.getenv("FIKIRI_SITE_BOT_RATE_LIMIT_BURST", "40").strip()
    try:
        return max(rate_limit_per_minute(), int(raw))
    except ValueError:
        return 40


def _is_production_runtime() -> bool:
    return os.getenv("FLASK_ENV", "").strip().lower() == "production"


def validate_site_bot_runtime_config() -> list[str]:
    """Return non-fatal configuration warnings for production smoke checks."""
    warnings: list[str] = []
    if not site_bot_enabled():
        return warnings

    if is_test_mode():
        return warnings

    redis_url = os.getenv("REDIS_URL", "").strip()
    upstash = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    if _is_production_runtime() and not redis_url and not upstash:
        warnings.append(
            "REDIS_URL (or Upstash Redis env) is not set; site bot sessions and rate limits "
            "fall back to per-process memory."
        )

    cors_origins = os.getenv("CORS_ORIGINS", "").strip()
    if _is_production_runtime() and not cors_origins:
        warnings.append(
            "CORS_ORIGINS is empty; confirm marketing-site origins are allowed for /api/site/chat."
        )

    if _is_production_runtime() and persist_transcripts_enabled():
        salt = os.getenv("FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT", "").strip()
        if not salt or salt == "fikiri-site-chat":
            warnings.append(
                "FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS is on but "
                "FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT is missing or still the dev default; "
                "set a strong random salt in production."
            )

    return warnings


def log_site_bot_config_warnings(logger) -> None:
    for message in validate_site_bot_runtime_config():
        logger.warning("Site bot config: %s", message)


def persist_transcripts_enabled() -> bool:
    """When true, append site chat turns to Postgres (Phase 5b). Default off."""
    if is_test_mode():
        raw = os.getenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "").strip().lower()
        if raw in ("0", "false", "no", "off"):
            return False
        return raw in ("1", "true", "yes", "on")
    return os.getenv("FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def transcript_retention_days() -> int:
    raw = os.getenv("FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS", "90").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 90
