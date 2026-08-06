"""Product analytics event registry — allowlists and rejection rules.

Kill switches default OFF. This module is pure data + validation helpers;
it does not write to the database.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

SCHEMA_VERSION = 1

EVENT_SOURCES = frozenset({"client", "server", "derived"})

# Secret-like or content keys: presence rejects the entire event.
PROHIBITED_PROPERTY_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "cookies",
        "secret",
        "code",
        "mfa_code",
        "recovery_code",
        "email_body",
        "body",
        "message",
        "notes",
        "card",
        "card_number",
        "clipboard",
        "prompt",
        "response",
        "content",
        "subject",
        "raw_user_agent",
        "ip",
        "ip_address",
        "full_ip",
    }
)

_SECRET_KEY_RE = re.compile(
    r"(?i)(password|passwd|token|secret|authorization|cookie|clipboard|"
    r"email_body|card_number|mfa|recovery_code|refresh_token|access_token)"
)

DURATION_BUCKETS = frozenset(
    {
        "under_30_seconds",
        "30_seconds_to_2_minutes",
        "2_to_5_minutes",
        "5_to_15_minutes",
        "15_to_30_minutes",
        "over_30_minutes",
    }
)

DEVICE_CLASSES = frozenset({"desktop", "mobile", "tablet", "unknown"})
BROWSER_FAMILIES = frozenset(
    {"chrome", "firefox", "safari", "edge", "opera", "other", "unknown"}
)
OS_FAMILIES = frozenset({"macos", "windows", "linux", "ios", "android", "other", "unknown"})
VIEWPORT_CATEGORIES = frozenset({"xs", "sm", "md", "lg", "xl", "unknown"})

COMMON_OPTIONAL_PROPS = frozenset(
    {
        "feature_key",
        "workflow_key",
        "step_id",
        "outcome",
        "duration_bucket",
        "device_class",
        "browser_family",
        "os_family",
        "viewport_category",
        "correlation_id",
        "error_category",
        "status_code_category",
        "retry_count",
        "completed",
        "session_id_hash",
    }
)

FEATURE_KEYS = frozenset(
    {
        "dashboard",
        "crm",
        "inbox",
        "automations",
        "integrations",
        "billing",
        "settings",
        "onboarding",
        "analytics",
        "appointments",
        "support",
        "other",
    }
)

WORKFLOW_KEYS = frozenset(
    {
        "onboarding",
        "gmail_connect",
        "outlook_connect",
        "lead_capture",
        "followup",
        "automation_run",
        "email_sync",
        "inbox_triage",
        "other",
    }
)

ERROR_CATEGORIES = frozenset(
    {
        "validation",
        "network",
        "auth",
        "rate_limit",
        "server",
        "timeout",
        "unknown",
    }
)


@dataclass(frozen=True)
class EventDefinition:
    name: str
    purpose: str
    allowed_properties: FrozenSet[str]
    retention_category: str  # raw_90d | aggregate_13m | security | support
    tenant_level: bool
    contributes_to_health: bool
    operator_visible: bool
    founder_aggregatable: bool
    allowed_sources: FrozenSet[str]
    # If True, unknown properties reject the whole event; else reject only those props
    # (we still never store unknown props). Plan: prefer reject event for this slice.
    reject_unknown_properties: bool = True


def _def(
    name: str,
    purpose: str,
    props: FrozenSet[str],
    *,
    health: bool = False,
    sources: Optional[FrozenSet[str]] = None,
) -> EventDefinition:
    return EventDefinition(
        name=name,
        purpose=purpose,
        allowed_properties=props | frozenset({"correlation_id", "session_id_hash"}),
        retention_category="raw_90d",
        tenant_level=True,
        contributes_to_health=health,
        operator_visible=True,
        founder_aggregatable=True,
        allowed_sources=sources or frozenset({"client", "server", "derived"}),
        reject_unknown_properties=True,
    )


EVENT_REGISTRY: Dict[str, EventDefinition] = {
    "session.started": _def(
        "session.started",
        "Coarse product session begin for adoption lookbacks",
        frozenset({"device_class", "browser_family", "os_family", "viewport_category"}),
        sources=frozenset({"client", "server"}),
    ),
    "feature.opened": _def(
        "feature.opened",
        "Major feature area opened (navigation)",
        frozenset({"feature_key", "device_class", "browser_family", "viewport_category"}),
        sources=frozenset({"client"}),
    ),
    "workflow.started": _def(
        "workflow.started",
        "Controlled workflow began",
        frozenset({"workflow_key", "feature_key", "step_id"}),
        sources=frozenset({"client", "server"}),
    ),
    "workflow.failed": _def(
        "workflow.failed",
        "Controlled workflow failed with category",
        frozenset({"workflow_key", "feature_key", "error_category", "status_code_category", "retry_count"}),
        health=True,
        sources=frozenset({"client", "server", "derived"}),
    ),
    "onboarding.step_completed": _def(
        "onboarding.step_completed",
        "Onboarding step advanced",
        frozenset({"step_id", "feature_key"}),
        health=True,
        sources=frozenset({"client", "server", "derived"}),
    ),
    "error.category": _def(
        "error.category",
        "Controlled product error category (no payload contents)",
        frozenset({"error_category", "feature_key", "workflow_key", "status_code_category"}),
        health=True,
        sources=frozenset({"client", "server"}),
    ),
    # Scaffolding only — accessibility kill switch must be on to accept these.
    "accessibility.reduced_motion_used": _def(
        "accessibility.reduced_motion_used",
        "Interface preference: prefers-reduced-motion",
        frozenset({"device_class", "viewport_category"}),
        sources=frozenset({"client"}),
    ),
    "accessibility.keyboard_navigation_detected": _def(
        "accessibility.keyboard_navigation_detected",
        "Interface pattern: keyboard-first navigation in session",
        frozenset({"device_class", "viewport_category"}),
        sources=frozenset({"client"}),
    ),
}

SOURCE_CATEGORIES = frozenset(
    {"manual", "website", "import", "email", "automation", "api", "other"}
)
CREATION_CHANNELS = frozenset(
    {"crm_ui", "api", "import", "automation", "webhook", "other"}
)
SYNC_PROVIDERS = frozenset({"gmail", "outlook", "imap", "other"})
SYNC_TYPES = frozenset({"initial", "incremental", "lookback", "retry", "other"})
RESULT_CATEGORIES = frozenset({"completed", "partial_completed", "other"})
PROCESSED_COUNT_BUCKETS = frozenset(
    {"0", "1_to_10", "11_to_50", "51_to_200", "201_to_1000", "over_1000"}
)

# Meaningful outcome categories (server/derived preferred)
MEANINGFUL_OUTCOME_EVENTS = frozenset(
    {
        "outcome.lead_captured",
        "outcome.sync_completed",
        "outcome.integration_connected",
        "outcome.onboarding_completed",
    }
)

# Override outcome defs with tighter allowlists (server/derived only).
EVENT_REGISTRY["outcome.lead_captured"] = _def(
    "outcome.lead_captured",
    "Lead durably created (server)",
    frozenset(
        {
            "feature_key",
            "workflow_key",
            "outcome",
            "completed",
            "source_category",
            "creation_channel",
            "schema_version",
        }
    ),
    health=True,
    sources=frozenset({"server", "derived"}),
)
EVENT_REGISTRY["outcome.sync_completed"] = _def(
    "outcome.sync_completed",
    "Email sync job reached successful completed state (server)",
    frozenset(
        {
            "feature_key",
            "workflow_key",
            "outcome",
            "completed",
            "provider",
            "sync_type",
            "result_category",
            "processed_count_bucket",
            "schema_version",
        }
    ),
    health=True,
    sources=frozenset({"server", "derived"}),
)
EVENT_REGISTRY["outcome.integration_connected"] = _def(
    "outcome.integration_connected",
    "Email integration connected (server/derived)",
    frozenset({"feature_key", "workflow_key", "outcome", "completed", "provider"}),
    health=True,
    sources=frozenset({"server", "derived"}),
)
EVENT_REGISTRY["outcome.onboarding_completed"] = _def(
    "outcome.onboarding_completed",
    "Onboarding marked complete (server/derived)",
    frozenset({"feature_key", "workflow_key", "outcome", "completed"}),
    health=True,
    sources=frozenset({"server", "derived"}),
)


def product_analytics_enabled() -> bool:
    return (os.getenv("PRODUCT_ANALYTICS_ENABLED") or "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def tenant_in_analytics_allowlist(tenant_id: int) -> bool:
    """Empty allowlist = all tenants when analytics enabled. Otherwise comma-separated IDs."""
    raw = (os.getenv("PRODUCT_ANALYTICS_TENANT_ALLOWLIST") or "").strip()
    if not raw:
        return True
    allowed: set = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            allowed.add(int(part))
    return int(tenant_id) in allowed


def accessibility_signals_enabled() -> bool:
    return (os.getenv("PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED") or "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def raw_retention_days() -> int:
    try:
        return max(1, min(int(os.getenv("PRODUCT_ANALYTICS_RAW_RETENTION_DAYS") or "90"), 730))
    except ValueError:
        return 90


def aggregate_retention_days() -> int:
    try:
        return max(1, min(int(os.getenv("PRODUCT_ANALYTICS_AGGREGATE_RETENTION_DAYS") or "395"), 2000))
    except ValueError:
        return 395


def is_accessibility_event(event_name: str) -> bool:
    return event_name.startswith("accessibility.")


def get_event_definition(event_name: str) -> Optional[EventDefinition]:
    return EVENT_REGISTRY.get(event_name)


def _is_prohibited_key(key: str) -> bool:
    k = (key or "").strip().lower()
    if k in PROHIBITED_PROPERTY_KEYS:
        return True
    if _SECRET_KEY_RE.search(k):
        return True
    return False


def validate_event_properties(
    event_name: str,
    properties: Optional[Dict[str, Any]],
    *,
    event_source: str = "client",
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validate properties against registry.

    Returns (ok, rejection_reason_code, sanitized_properties).
    On failure sanitized_properties is empty — never store partial events when prohibited.
    """
    definition = get_event_definition(event_name)
    if definition is None:
        return False, "UNKNOWN_EVENT", {}

    if event_source not in EVENT_SOURCES:
        return False, "INVALID_SOURCE", {}
    if event_source not in definition.allowed_sources:
        return False, "SOURCE_NOT_ALLOWED", {}

    if is_accessibility_event(event_name) and not accessibility_signals_enabled():
        return False, "ACCESSIBILITY_DISABLED", {}

    props = properties if isinstance(properties, dict) else {}
    if len(props) > 32:
        return False, "TOO_MANY_PROPERTIES", {}

    sanitized: Dict[str, Any] = {}
    for key, value in props.items():
        if not isinstance(key, str) or not key:
            return False, "INVALID_PROPERTY_KEY", {}
        if _is_prohibited_key(key):
            return False, "PROHIBITED_PROPERTY", {}
        if key in {"tenant_id", "user_id", "actor_user_id"}:
            # Client must never supply identity; reject to avoid confusion.
            return False, "IDENTITY_PROPERTY_FORBIDDEN", {}
        if key not in definition.allowed_properties:
            if definition.reject_unknown_properties:
                return False, "UNKNOWN_PROPERTY", {}
            continue
        ok, reason, coerced = _coerce_property(key, value)
        if not ok:
            return False, reason or "INVALID_PROPERTY_VALUE", {}
        if coerced is not None:
            sanitized[key] = coerced

    return True, None, sanitized


def _coerce_property(key: str, value: Any) -> Tuple[bool, Optional[str], Any]:
    if key in {"feature_key"}:
        text = str(value).strip().lower()
        if text not in FEATURE_KEYS:
            return False, "INVALID_FEATURE_KEY", None
        return True, None, text
    if key in {"workflow_key"}:
        text = str(value).strip().lower()
        if text not in WORKFLOW_KEYS:
            return False, "INVALID_WORKFLOW_KEY", None
        return True, None, text
    if key == "source_category":
        text = str(value).strip().lower()
        if text not in SOURCE_CATEGORIES:
            return False, "INVALID_SOURCE_CATEGORY", None
        return True, None, text
    if key == "creation_channel":
        text = str(value).strip().lower()
        if text not in CREATION_CHANNELS:
            return False, "INVALID_CREATION_CHANNEL", None
        return True, None, text
    if key == "provider":
        text = str(value).strip().lower()
        if text not in SYNC_PROVIDERS:
            return False, "INVALID_PROVIDER", None
        return True, None, text
    if key == "sync_type":
        text = str(value).strip().lower()
        if text not in SYNC_TYPES:
            return False, "INVALID_SYNC_TYPE", None
        return True, None, text
    if key == "result_category":
        text = str(value).strip().lower()
        if text not in RESULT_CATEGORIES:
            return False, "INVALID_RESULT_CATEGORY", None
        return True, None, text
    if key == "processed_count_bucket":
        text = str(value).strip().lower()
        if text not in PROCESSED_COUNT_BUCKETS:
            return False, "INVALID_PROCESSED_COUNT_BUCKET", None
        return True, None, text
    if key == "schema_version":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return False, "INVALID_SCHEMA_VERSION", None
        if n < 1 or n > 100:
            return False, "INVALID_SCHEMA_VERSION", None
        return True, None, n
    if key == "duration_bucket":
        text = str(value).strip()
        if text not in DURATION_BUCKETS:
            return False, "INVALID_DURATION_BUCKET", None
        return True, None, text
    if key == "device_class":
        text = str(value).strip().lower()
        if text not in DEVICE_CLASSES:
            return False, "INVALID_DEVICE_CLASS", None
        return True, None, text
    if key == "browser_family":
        text = str(value).strip().lower()
        if text not in BROWSER_FAMILIES:
            return False, "INVALID_BROWSER_FAMILY", None
        return True, None, text
    if key == "os_family":
        text = str(value).strip().lower()
        if text not in OS_FAMILIES:
            return False, "INVALID_OS_FAMILY", None
        return True, None, text
    if key == "viewport_category":
        text = str(value).strip().lower()
        if text not in VIEWPORT_CATEGORIES:
            return False, "INVALID_VIEWPORT_CATEGORY", None
        return True, None, text
    if key == "error_category":
        text = str(value).strip().lower()
        if text not in ERROR_CATEGORIES:
            return False, "INVALID_ERROR_CATEGORY", None
        return True, None, text
    if key == "completed":
        if isinstance(value, bool):
            return True, None, value
        return False, "INVALID_BOOLEAN", None
    if key == "retry_count":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return False, "INVALID_RETRY_COUNT", None
        if n < 0 or n > 100:
            return False, "INVALID_RETRY_COUNT", None
        return True, None, n
    if key in {"correlation_id", "session_id_hash", "step_id", "outcome", "status_code_category"}:
        if value is None:
            return True, None, None
        text = str(value).strip()
        if len(text) > 128:
            return False, "PROPERTY_TOO_LONG", None
        # Controlled codes prefer snake/upper; allow alnum + _.-:
        if not re.match(r"^[A-Za-z0-9_.:-]{1,128}$", text):
            return False, "INVALID_CONTROLLED_STRING", None
        return True, None, text
    # Default: bounded scalar only
    if isinstance(value, bool):
        return True, None, value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if abs(float(value)) > 1_000_000:
            return False, "NUMERIC_OUT_OF_RANGE", None
        return True, None, value
    if isinstance(value, str):
        if len(value) > 128:
            return False, "PROPERTY_TOO_LONG", None
        return True, None, value
    return False, "UNSUPPORTED_PROPERTY_TYPE", None


def list_registered_event_names() -> List[str]:
    return sorted(EVENT_REGISTRY.keys())
