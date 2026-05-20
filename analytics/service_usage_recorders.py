"""
Best-effort service usage recorders for triage, Command Center, and CRM.

Never raises to callers; strips PII from metadata before persist.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from analytics.service_usage_analytics import build_idempotency_key, record_service_usage_event
from analytics.service_usage_constants import (
    EVENT_CATEGORY_USAGE,
    EVENT_CC_APPLY,
    EVENT_CC_ARCHIVE,
    EVENT_CC_CLASSIFY_SYNCED,
    EVENT_CC_RECLASSIFY,
    EVENT_CC_SYNC,
    EVENT_CRM_ACTIVITY_ADDED,
    EVENT_CRM_LEAD_CONVERTED,
    EVENT_CRM_LEAD_CREATED,
    EVENT_CRM_LEAD_STAGE_CHANGED,
    EVENT_CRM_LEAD_UPDATED,
    EVENT_TRIAGE_BULK_ACTION,
    EVENT_TRIAGE_CLASSIFIED,
    EVENT_TRIAGE_CLASSIFY_UNCLASSIFIED,
    EVENT_TRIAGE_RECLASSIFIED,
    METRIC_CC_ACTION,
    METRIC_CRM_ACTIVITY,
    METRIC_CRM_LEAD,
    METRIC_TRIAGE_BULK,
    METRIC_TRIAGE_CLASSIFIED,
    METRIC_TRIAGE_RECLASSIFIED,
    SERVICE_COMMAND_CENTER,
    SERVICE_CRM,
)

logger = logging.getLogger(__name__)

_PII_KEYS = frozenset(
    {
        "body",
        "email_body",
        "subject",
        "prompt",
        "response",
        "content",
        "message",
        "query",
        "email",
        "name",
        "phone",
        "sender",
        "recipient",
        "description",
        "notes",
    }
)


def _safe_metadata(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not data:
        return None
    safe: Dict[str, Any] = {}
    for key, value in data.items():
        if key in _PII_KEYS:
            continue
        if isinstance(value, str) and len(value) > 200:
            safe[key] = value[:200]
        elif isinstance(value, (bool, int, float)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)) and all(
            isinstance(x, (bool, int, float, str)) for x in value
        ):
            safe[key] = list(value)[:20]
        elif isinstance(value, dict):
            nested = _safe_metadata(value)
            if nested:
                safe[key] = nested
        elif isinstance(value, str):
            if "@" in value and "." in value:
                continue
            safe[key] = value[:120]
    return safe or None


def _record(
    *,
    user_id: int,
    service_id: str,
    event_type: str,
    metric_name: str,
    quantity: float = 1.0,
    status: str = "success",
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> None:
    if not user_id:
        return
    try:
        record_service_usage_event(
            user_id=user_id,
            service_id=service_id,
            event_type=event_type,
            event_category=EVENT_CATEGORY_USAGE,
            metric_name=metric_name,
            quantity=quantity,
            status=status,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=_safe_metadata(metadata),
            source=source,
        )
    except Exception as exc:
        logger.debug("service_usage_recorder skipped: %s", exc)


def record_triage_classified(
    user_id: int,
    *,
    external_id: str,
    category: Optional[str] = None,
    source: str = "sync",
    workflow_status: Optional[str] = None,
    provider: str = "gmail",
) -> None:
    key = build_idempotency_key("triage_classified", user_id, provider, external_id, source)
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_TRIAGE_CLASSIFIED,
        metric_name=METRIC_TRIAGE_CLASSIFIED,
        idempotency_key=key,
        correlation_id=external_id,
        resource_type="synced_email",
        resource_id=external_id,
        metadata={
            "category": category,
            "source": source,
            "workflow_status": workflow_status,
            "provider": provider,
        },
        source="email_triage_service",
    )


def record_triage_reclassified(
    user_id: int,
    *,
    external_id: str,
    category: Optional[str] = None,
    force: bool = True,
    workflow_status: Optional[str] = None,
    provider: str = "gmail",
) -> None:
    key = build_idempotency_key("triage_reclassified", user_id, provider, external_id, "force")
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_TRIAGE_RECLASSIFIED,
        metric_name=METRIC_TRIAGE_RECLASSIFIED,
        idempotency_key=key,
        correlation_id=external_id,
        resource_type="synced_email",
        resource_id=external_id,
        metadata={
            "category": category,
            "force": force,
            "source": "command_center",
            "workflow_status": workflow_status,
            "provider": provider,
        },
        source="email_triage_service",
    )


def record_triage_classify_unclassified_completed(
    user_id: int,
    *,
    scanned: int,
    classified_count: int,
    skipped_existing: int,
    failed: int,
) -> None:
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_TRIAGE_CLASSIFY_UNCLASSIFIED,
        metric_name=METRIC_TRIAGE_CLASSIFIED,
        quantity=float(classified_count),
        idempotency_key=build_idempotency_key(
            "triage_unclassified_batch",
            user_id,
            scanned,
            classified_count,
            failed,
        ),
        metadata={
            "scanned": scanned,
            "classified_count": classified_count,
            "skipped_existing": skipped_existing,
            "failed": failed,
            "source": "command_center",
        },
        source="email_triage_service",
    )
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_CC_CLASSIFY_SYNCED,
        metric_name=METRIC_CC_ACTION,
        quantity=float(classified_count),
        metadata={
            "scanned": scanned,
            "classified_count": classified_count,
            "failed": failed,
            "source": "command_center",
        },
        source="email_triage_service",
    )


def record_triage_bulk_action(
    user_id: int,
    *,
    action: str,
    processed: int,
    failed: int = 0,
    leads_created: int = 0,
) -> None:
    status = "success" if processed > 0 else "error"
    cc_event = EVENT_CC_ARCHIVE if action == "archive" else EVENT_CC_APPLY
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=cc_event,
        metric_name=METRIC_CC_ACTION,
        quantity=float(processed),
        status=status,
        metadata={
            "action": action,
            "processed_count": processed,
            "failed_count": failed,
            "leads_created": leads_created,
            "source": "command_center",
        },
        source="email_triage_service",
    )
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_TRIAGE_BULK_ACTION,
        metric_name=METRIC_TRIAGE_BULK,
        quantity=float(processed),
        status=status,
        metadata={
            "action": action,
            "processed_count": processed,
            "failed_count": failed,
            "leads_created": leads_created,
            "source": "command_center",
        },
        source="email_triage_service",
    )


def record_command_center_reclassify_batch(
    user_id: int,
    *,
    email_count: int,
    classified_count: int,
) -> None:
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_CC_RECLASSIFY,
        metric_name=METRIC_CC_ACTION,
        quantity=float(classified_count),
        metadata={
            "email_count": email_count,
            "classified_count": classified_count,
            "source": "command_center",
        },
        source="email_triage_service",
    )


def record_command_center_sync_clicked(
    user_id: int,
    *,
    job_id: Optional[str] = None,
    sync_job_queued: bool = False,
    surface: str = "command_center",
) -> None:
    key = build_idempotency_key("cc_sync", user_id, job_id or surface)
    _record(
        user_id=user_id,
        service_id=SERVICE_COMMAND_CENTER,
        event_type=EVENT_CC_SYNC,
        metric_name=METRIC_CC_ACTION,
        idempotency_key=key,
        correlation_id=job_id,
        metadata={
            "sync_job_queued": sync_job_queued,
            "surface": surface,
            "has_job_id": bool(job_id),
        },
        source="sync_gmail",
    )


def record_crm_lead_created(
    user_id: int,
    *,
    lead_id: int,
    source: Optional[str] = None,
    created: bool = True,
    has_email: bool = False,
    has_phone: bool = False,
    correlation_id: Optional[str] = None,
) -> None:
    key = build_idempotency_key("crm_lead_created", user_id, lead_id)
    _record(
        user_id=user_id,
        service_id=SERVICE_CRM,
        event_type=EVENT_CRM_LEAD_CREATED,
        metric_name=METRIC_CRM_LEAD,
        idempotency_key=key,
        correlation_id=correlation_id,
        resource_type="lead",
        resource_id=str(lead_id),
        metadata={
            "lead_id": lead_id,
            "source": source or "manual",
            "created": created,
            "has_email": has_email,
            "has_phone": has_phone,
        },
        source="crm_service",
    )


def record_crm_lead_updated(
    user_id: int,
    *,
    lead_id: int,
    fields_changed: Optional[list] = None,
    source: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    _record(
        user_id=user_id,
        service_id=SERVICE_CRM,
        event_type=EVENT_CRM_LEAD_UPDATED,
        metric_name=METRIC_CRM_LEAD,
        correlation_id=correlation_id,
        resource_type="lead",
        resource_id=str(lead_id),
        metadata={
            "lead_id": lead_id,
            "fields_changed": fields_changed or [],
            "source": source or "manual",
        },
        source="crm_service",
    )


def record_crm_lead_stage_changed(
    user_id: int,
    *,
    lead_id: int,
    previous_stage: str,
    new_stage: str,
    correlation_id: Optional[str] = None,
) -> None:
    key = build_idempotency_key(
        "crm_stage", user_id, lead_id, previous_stage, new_stage, correlation_id or ""
    )
    _record(
        user_id=user_id,
        service_id=SERVICE_CRM,
        event_type=EVENT_CRM_LEAD_STAGE_CHANGED,
        metric_name=METRIC_CRM_LEAD,
        idempotency_key=key,
        correlation_id=correlation_id,
        resource_type="lead",
        resource_id=str(lead_id),
        metadata={
            "lead_id": lead_id,
            "previous_stage": previous_stage,
            "new_stage": new_stage,
        },
        source="crm_service",
    )
    if new_stage == "qualified" and previous_stage != "qualified":
        _record(
            user_id=user_id,
            service_id=SERVICE_CRM,
            event_type=EVENT_CRM_LEAD_CONVERTED,
            metric_name=METRIC_CRM_LEAD,
            idempotency_key=build_idempotency_key("crm_converted", user_id, lead_id, new_stage),
            resource_type="lead",
            resource_id=str(lead_id),
            metadata={
                "lead_id": lead_id,
                "previous_stage": previous_stage,
                "new_stage": new_stage,
            },
            source="crm_service",
        )


def record_crm_activity_added(
    user_id: int,
    *,
    lead_id: int,
    activity_id: Optional[int],
    activity_type: str,
    correlation_id: Optional[str] = None,
) -> None:
    _record(
        user_id=user_id,
        service_id=SERVICE_CRM,
        event_type=EVENT_CRM_ACTIVITY_ADDED,
        metric_name=METRIC_CRM_ACTIVITY,
        correlation_id=correlation_id,
        resource_type="lead",
        resource_id=str(lead_id),
        metadata={
            "lead_id": lead_id,
            "activity_id": activity_id,
            "activity_type": activity_type,
        },
        source="crm_service",
    )
