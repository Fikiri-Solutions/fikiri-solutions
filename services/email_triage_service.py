"""
Inbox Command Center: triage persistence and user-approved bulk Gmail actions.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.ai.email_triage_taxonomy import (
    CLEANUP_ACTION_SET,
    DESTRUCTIVE_CLEANUP_ACTIONS,
    INBOX_COMMAND_CENTER_TABS,
    normalize_cleanup_action,
)
from core.email_triage_store import (
    count_classifications_by_category,
    count_unclassified_synced,
    list_classified_emails,
    list_unclassified_synced,
    upsert_classification,
)
from email_automation.email_triage_engine import classify_email_triage
from email_automation.email_workflow_state import (
    mark_classification_failed,
    mark_classified,
    mark_reclassified,
    persist_workflow_after_user_action,
    should_classify_email,
    workflow_action_spec,
    workflow_already_at_target,
)
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)


def _lookup_workflow_status(
    user_id: int, external_id: str, provider: str = "gmail"
) -> Optional[str]:
    try:
        from email_automation.email_workflow_state import ensure_email_workflow_state_table
        from core.database_optimization import db_optimizer

        ensure_email_workflow_state_table()
        rows = db_optimizer.execute_query(
            """
            SELECT workflow_status FROM email_workflow_state
            WHERE user_id = ? AND external_id = ? AND provider = ?
            LIMIT 1
            """,
            (user_id, external_id, provider),
        )
        if rows:
            return str(rows[0].get("workflow_status") or "")
    except Exception:
        pass
    return None


BULK_ACTIONS = frozenset(
    {
        "archive",
        "mark_read",
        "mark_unread",
        "label",
        "delete_candidate",
        "spam_candidate",
        "create_leads",
        "not_a_lead",
        "dismiss",
        "done",
    }
)

WORKFLOW_ONLY_BULK_ACTIONS = frozenset({"not_a_lead", "dismiss", "done"})


def triage_and_store_synced_message(
    user_id: int,
    *,
    external_id: str,
    subject: str,
    body: str,
    sender_email: str = "",
    sender_name: str = "",
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    headers: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    triage = classify_email_triage(
        subject=subject,
        body=body,
        sender_email=sender_email,
        sender_name=sender_name,
        headers=headers,
        user_id=user_id,
        analysis=analysis,
        allow_ai=analysis is None,
    )
    upsert_classification(
        user_id,
        external_id=external_id,
        provider=provider,
        synced_email_id=synced_email_id,
        triage=triage,
    )
    try:
        mark_classified(
            user_id,
            external_id,
            provider=provider,
            synced_email_id=synced_email_id,
            source="sync" if analysis is None else "mailbox_pipeline",
        )
    except Exception as wf_exc:
        logger.warning(
            "workflow mark_classified skipped user=%s external_id=%s: %s",
            user_id,
            external_id,
            wf_exc,
        )
    try:
        from analytics.service_usage_recorders import record_triage_classified

        record_triage_classified(
            user_id,
            external_id=external_id,
            category=(triage or {}).get("category"),
            source="sync" if analysis is None else "mailbox_pipeline",
            workflow_status=_lookup_workflow_status(user_id, external_id, provider),
            provider=provider,
        )
    except Exception:
        pass
    return triage


def list_triage_inbox(
    user_id: int,
    *,
    category: Optional[str] = None,
    cleanup_action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_handled: bool = False,
) -> Dict[str, Any]:
    data = list_classified_emails(
        user_id,
        category=category,
        cleanup_action=cleanup_action,
        limit=limit,
        offset=offset,
        include_handled=include_handled,
    )
    data["tabs"] = list(INBOX_COMMAND_CENTER_TABS)
    data["category_counts"] = count_classifications_by_category(
        user_id, include_handled=include_handled
    )
    data["unclassified_synced_count"] = count_unclassified_synced(user_id)
    return data


def classify_unclassified_synced(user_id: int, *, limit: int = 50) -> Dict[str, Any]:
    """Classify synced rows missing email_classifications (e.g. after failed sync triage)."""
    rows = list_unclassified_synced(user_id, limit=limit)
    classified: List[Dict[str, Any]] = []
    scanned = 0
    skipped_existing = 0
    failed = 0
    for row in rows:
        scanned += 1
        sender = row.get("sender") or ""
        email_addr = sender
        if "<" in sender and ">" in sender:
            email_addr = sender.split("<")[1].split(">")[0].strip()
        eid = str(row.get("external_id") or "")
        prov = row.get("provider") or "gmail"
        if not eid:
            failed += 1
            continue
        if not should_classify_email(user_id, eid, prov, force=False):
            skipped_existing += 1
            continue
        try:
            triage = triage_and_store_synced_message(
                user_id,
                external_id=eid,
                subject=row.get("subject") or "",
                body=row.get("body") or "",
                sender_email=email_addr,
                sender_name=sender.split("<")[0].strip() if "<" in sender else sender,
                provider=prov,
                synced_email_id=int(row["id"]) if row.get("id") is not None else None,
            )
            classified.append({"email_id": eid, "triage": triage})
        except Exception as exc:
            failed += 1
            logger.warning("classify_unclassified failed user=%s id=%s: %s", user_id, eid, exc)
            try:
                mark_classification_failed(
                    user_id, eid, provider=prov, source="classify_unclassified"
                )
            except Exception as wf_exc:
                logger.debug("mark_classification_failed skipped: %s", wf_exc)
    count = len(classified)
    result = {
        "classified": classified,
        "count": count,
        "scanned": scanned,
        "classified_count": count,
        "skipped_existing": skipped_existing,
        "failed": failed,
    }
    try:
        from analytics.service_usage_recorders import record_triage_classify_unclassified_completed

        record_triage_classify_unclassified_completed(
            user_id,
            scanned=scanned,
            classified_count=count,
            skipped_existing=skipped_existing,
            failed=failed,
        )
    except Exception:
        pass
    logger.info(
        "email triage classify batch finished",
        extra={
            "event": "email_triage.classify_batch.completed",
            "service": "email",
            "severity": "INFO",
            "user_id": user_id,
            "classified_count": count,
            "scanned": scanned,
            "failed": failed,
        },
    )
    return result


def reclassify_synced_messages(
    user_id: int,
    email_ids: List[str],
) -> Dict[str, Any]:
    """Force re-triage for selected synced messages (Command Center Re-classify)."""
    from core.database_optimization import db_optimizer

    classified: List[Dict[str, Any]] = []
    for eid in email_ids[:50]:
        rows = db_optimizer.execute_query(
            """
            SELECT id, subject, sender, body, COALESCE(external_id, gmail_id) AS external_id, provider
            FROM synced_emails
            WHERE user_id = ? AND (external_id = ? OR gmail_id = ?)
            LIMIT 1
            """,
            (user_id, str(eid), str(eid)),
        )
        if not rows:
            continue
        row = rows[0]
        sender = row.get("sender") or ""
        email_addr = sender
        if "<" in sender and ">" in sender:
            email_addr = sender.split("<")[1].split(">")[0].strip()
        external_id = str(row.get("external_id") or eid)
        prov = row.get("provider") or "gmail"
        triage = classify_email_triage(
            subject=row.get("subject") or "",
            body=row.get("body") or "",
            sender_email=email_addr,
            sender_name=sender.split("<")[0].strip() if "<" in sender else sender,
            user_id=user_id,
            allow_ai=False,
        )
        upsert_classification(
            user_id,
            external_id=external_id,
            provider=prov,
            synced_email_id=int(row["id"]) if row.get("id") is not None else None,
            triage=triage,
        )
        try:
            mark_reclassified(
                user_id,
                external_id,
                provider=prov,
                synced_email_id=int(row["id"]) if row.get("id") is not None else None,
            )
        except Exception as wf_exc:
            logger.warning("mark_reclassified skipped: %s", wf_exc)
        try:
            from analytics.service_usage_recorders import record_triage_reclassified

            record_triage_reclassified(
                user_id,
                external_id=external_id,
                category=(triage or {}).get("category"),
                force=True,
                workflow_status=_lookup_workflow_status(user_id, external_id, prov),
                provider=prov,
            )
        except Exception:
            pass
        classified.append({"email_id": eid, "triage": triage})
    out = {"classified": classified, "count": len(classified)}
    try:
        from analytics.service_usage_recorders import record_command_center_reclassify_batch

        record_command_center_reclassify_batch(
            user_id,
            email_count=len(email_ids),
            classified_count=len(classified),
        )
    except Exception:
        pass
    return out


def _should_persist_bulk_workflow(action: str) -> bool:
    spec = workflow_action_spec(action)
    return bool(spec.get("workflow_status")) or bool(spec.get("touch_only"))


def _execute_bulk_gmail_item(
    gmail_service: Any,
    action: str,
    email_id: str,
    *,
    label_names: Optional[List[str]] = None,
) -> None:
    spec = workflow_action_spec(action)
    if spec.get("gmail_trash"):
        gmail_service.users().messages().trash(userId="me", id=email_id).execute()
        return
    if action == "label":
        if not label_names:
            raise ValueError("label_names required")
        for name in label_names[:5]:
            label_id = _ensure_label_id(gmail_service, name)
            if label_id:
                gmail_service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"addLabelIds": [label_id]},
                ).execute()
        return
    body = spec.get("gmail_modify")
    if body:
        gmail_service.users().messages().modify(
            userId="me", id=email_id, body=body
        ).execute()


def _record_bulk_workflow(
    user_id: int,
    email_id: str,
    action: str,
    *,
    counters: Dict[str, int],
) -> None:
    if not _should_persist_bulk_workflow(action):
        return
    try:
        outcome = persist_workflow_after_user_action(
            user_id,
            email_id,
            action,
            provider="gmail",
            source="command_center",
        )
        if outcome == "updated":
            counters["workflow_updated"] += 1
        else:
            counters["workflow_skipped"] += 1
    except Exception as exc:
        logger.warning(
            "bulk workflow persist skipped user=%s id=%s action=%s: %s",
            user_id,
            email_id,
            action,
            exc,
        )


def execute_bulk_action(
    user_id: int,
    *,
    action: str,
    email_ids: List[str],
    confirm_destructive: bool = False,
    label_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if action not in BULK_ACTIONS:
        return {"success": False, "error": f"Unknown action: {action}", "processed": 0}

    if action in DESTRUCTIVE_CLEANUP_ACTIONS and not confirm_destructive:
        return {
            "success": False,
            "error": "confirm_destructive=true required for delete/spam candidates",
            "code": "CONFIRMATION_REQUIRED",
            "processed": 0,
        }

    if not email_ids:
        return {"success": False, "error": "email_ids required", "processed": 0}

    spec = workflow_action_spec(action)
    gmail_service = None
    if spec.get("requires_gmail") or action == "label":
        from integrations.gmail.gmail_client import gmail_client

        try:
            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
        except Exception as exc:
            return {"success": False, "error": str(exc), "processed": 0}

    processed = 0
    errors: List[Dict[str, str]] = []
    leads_created = 0
    wf_counters = {"workflow_updated": 0, "workflow_skipped": 0}

    for email_id in email_ids[:100]:
        try:
            if action in WORKFLOW_ONLY_BULK_ACTIONS:
                _record_bulk_workflow(user_id, email_id, action, counters=wf_counters)
                processed += 1
                continue

            if action == "create_leads":
                lead_ok = _create_lead_from_classified_email(user_id, email_id)
                if not lead_ok:
                    errors.append({"email_id": email_id, "error": "lead_not_created"})
                    continue
                leads_created += 1
                _record_bulk_workflow(user_id, email_id, action, counters=wf_counters)
                processed += 1
                continue

            if action == "label":
                if not label_names:
                    errors.append({"email_id": email_id, "error": "skipped"})
                    continue
                _execute_bulk_gmail_item(
                    gmail_service, action, email_id, label_names=label_names
                )
                processed += 1
                continue

            if spec.get("requires_gmail"):
                if workflow_already_at_target(user_id, email_id, action):
                    _record_bulk_workflow(user_id, email_id, action, counters=wf_counters)
                    processed += 1
                    continue
                _execute_bulk_gmail_item(gmail_service, action, email_id)
            _record_bulk_workflow(user_id, email_id, action, counters=wf_counters)
            processed += 1
        except Exception as exc:
            errors.append({"email_id": email_id, "error": str(exc)[:200]})

    result = {
        "success": processed > 0 and not errors,
        "action": action,
        "processed": processed,
        "leads_created": leads_created,
        "errors": errors,
        "requires_confirmation": action in DESTRUCTIVE_CLEANUP_ACTIONS,
        "workflow_updated": wf_counters["workflow_updated"],
        "workflow_skipped": wf_counters["workflow_skipped"],
    }
    try:
        from analytics.service_usage_recorders import record_triage_bulk_action

        record_triage_bulk_action(
            user_id,
            action=action,
            processed=processed,
            failed=len(errors),
            leads_created=leads_created,
        )
    except Exception:
        pass
    logger.info(
        "inbox workflow bulk action finished",
        extra={
            "event": "inbox.workflow.bulk_action.completed",
            "service": "email",
            "severity": "INFO",
            "user_id": user_id,
            "action": action,
            "processed": processed,
            "failed": len(errors),
            "leads_created": leads_created,
            "workflow_updated": wf_counters["workflow_updated"],
            "workflow_skipped": wf_counters["workflow_skipped"],
        },
    )
    return result


def _ensure_label_id(gmail_service: Any, label_name: str) -> Optional[str]:
    try:
        labels = gmail_service.users().labels().list(userId="me").execute().get("labels", [])
        for lab in labels:
            if lab.get("name") == label_name:
                return lab.get("id")
        created = (
            gmail_service.users()
            .labels()
            .create(userId="me", body={"name": label_name, "labelListVisibility": "labelShow"})
            .execute()
        )
        return created.get("id")
    except Exception as exc:
        logger.warning("Gmail label ensure failed for %s: %s", label_name, exc)
        return None


def _create_lead_from_classified_email(user_id: int, email_id: str) -> bool:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        """
        SELECT c.lead_score, c.category, s.sender, s.subject, s.body
        FROM email_classifications c
        LEFT JOIN synced_emails s
          ON s.user_id = c.user_id AND (s.external_id = c.external_id OR s.gmail_id = c.external_id)
        WHERE c.user_id = ? AND c.external_id = ?
        LIMIT 1
        """,
        (user_id, email_id),
    )
    if not rows:
        return False
    row = rows[0]
    if row.get("category") != "business_lead" and int(row.get("lead_score") or 0) < 40:
        return False
    sender = row.get("sender") or ""
    email_addr = sender
    if "<" in sender and ">" in sender:
        email_addr = sender.split("<")[1].split(">")[0].strip()
    if not email_addr or "@" not in email_addr:
        return False
    name = sender.split("<")[0].strip().replace('"', "") if "<" in sender else sender
    payload = {
        "email": email_addr.lower(),
        "name": name or email_addr,
        "source": "email_triage",
        "stage": "new",
        "score": int(row.get("lead_score") or 50),
        "notes": (row.get("subject") or "")[:500],
    }
    result = enhanced_crm_service.create_lead(user_id, payload)
    return bool(isinstance(result, dict) and result.get("success"))
