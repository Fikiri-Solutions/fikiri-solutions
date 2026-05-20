"""
Canonical service IDs, event categories, and billing→service mappings
for the unified service usage analytics layer.
"""

from __future__ import annotations

# Mirrors core/user_services.py aliases for consistent rollups.
SERVICE_ID_ALIASES = {
    "ai_email_assistant": "ai-assistant",
    "email_parser": "email-parser",
    "ml_lead_scoring": "ml-scoring",
}

KNOWN_SERVICE_IDS = frozenset(
    {
        "ai-assistant",
        "chatbot",
        "crm",
        "gmail",
        "outlook",
        "email-parser",
        "ml-scoring",
        "automations",
        "command-center",
    }
)

EVENT_CATEGORY_USAGE = "usage"
EVENT_CATEGORY_HEALTH = "health"
EVENT_CATEGORY_ADOPTION = "adoption"
EVENT_CATEGORY_BILLING_MIRROR = "billing_mirror"

# Operational event types (persisted in service_usage_events).
EVENT_AI_CALL = "ai_call"
EVENT_AUTOMATION_RUN = "automation_run"
EVENT_EMAIL_SYNC = "email_sync"
EVENT_EMAIL_TRIAGE = "email_triage"
EVENT_CHATBOT_QUERY = "chatbot_query"
EVENT_SERVICE_ENABLED = "service_enabled"

# Email triage / Command Center (operational; not billing).
EVENT_TRIAGE_CLASSIFIED = "email_triage.classified"
EVENT_TRIAGE_RECLASSIFIED = "email_triage.reclassified"
EVENT_TRIAGE_CLASSIFY_UNCLASSIFIED = "email_triage.classify_unclassified_completed"
EVENT_TRIAGE_BULK_ACTION = "email_triage.bulk_action_applied"
EVENT_CC_SYNC = "command_center.sync_clicked"
EVENT_CC_ARCHIVE = "command_center.archive"
EVENT_CC_APPLY = "command_center.apply"
EVENT_CC_RECLASSIFY = "command_center.reclassify"
EVENT_CC_CLASSIFY_SYNCED = "command_center.classify_synced"

# CRM mutations (operational).
EVENT_CRM_LEAD_CREATED = "crm.lead_created"
EVENT_CRM_LEAD_UPDATED = "crm.lead_updated"
EVENT_CRM_LEAD_STAGE_CHANGED = "crm.lead_stage_changed"
EVENT_CRM_ACTIVITY_ADDED = "crm.activity_added"
EVENT_CRM_LEAD_CONVERTED = "crm.lead_converted"

SERVICE_COMMAND_CENTER = "command-center"
SERVICE_CRM = "crm"

METRIC_AI_RESPONSES = "ai_responses"
METRIC_AUTOMATION_EXECUTIONS = "automation_executions"
METRIC_EMAIL_SYNCED = "emails_synced"
METRIC_CHATBOT_QUERIES = "chatbot_queries"
METRIC_BILLING_QUANTITY = "billing_quantity"
METRIC_TRIAGE_CLASSIFIED = "triage_classified"
METRIC_TRIAGE_RECLASSIFIED = "triage_reclassified"
METRIC_TRIAGE_BULK = "triage_bulk_action"
METRIC_CC_ACTION = "command_center_action"
METRIC_CRM_LEAD = "crm_lead_mutation"
METRIC_CRM_ACTIVITY = "crm_activity"

WINDOW_CURRENT_MONTH = "current_month"
WINDOW_LAST_7D = "last_7d"
WINDOW_LAST_30D = "last_30d"
WINDOW_ALL_TIME = "all_time"

# billing_usage.usage_type → default service_id for mirror rollups (not double-written).
BILLING_USAGE_TYPE_TO_SERVICE = {
    "ai_responses": "ai-assistant",
    "chatbot_queries": "chatbot",
    "email_processing": "ai-assistant",
    "lead_storage": "crm",
}


def normalize_service_id(service_id: str) -> str:
    sid = (service_id or "").strip()
    return SERVICE_ID_ALIASES.get(sid, sid)


def service_id_for_billing_usage(usage_type: str) -> str:
    return BILLING_USAGE_TYPE_TO_SERVICE.get((usage_type or "").strip(), "platform")
