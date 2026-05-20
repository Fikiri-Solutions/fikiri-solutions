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
from core.email_triage_store import list_classified_emails, upsert_classification
from email_automation.email_triage_engine import classify_email_triage
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)

BULK_ACTIONS = frozenset(
    {
        "archive",
        "mark_read",
        "mark_unread",
        "label",
        "delete_candidate",
        "spam_candidate",
        "create_leads",
    }
)


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
    return triage


def list_triage_inbox(
    user_id: int,
    *,
    category: Optional[str] = None,
    cleanup_action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    data = list_classified_emails(
        user_id,
        category=category,
        cleanup_action=cleanup_action,
        limit=limit,
        offset=offset,
    )
    data["tabs"] = list(INBOX_COMMAND_CENTER_TABS)
    return data


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

    from integrations.gmail.gmail_client import gmail_client

    try:
        gmail_service = gmail_client.get_gmail_service_for_user(user_id)
    except Exception as exc:
        return {"success": False, "error": str(exc), "processed": 0}

    processed = 0
    errors: List[Dict[str, str]] = []
    leads_created = 0

    for email_id in email_ids[:100]:
        try:
            if action == "archive":
                gmail_service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"removeLabelIds": ["INBOX"]},
                ).execute()
            elif action == "mark_read":
                gmail_service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
            elif action == "mark_unread":
                gmail_service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"addLabelIds": ["UNREAD"]},
                ).execute()
            elif action == "spam_candidate":
                gmail_service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"addLabelIds": ["SPAM"], "removeLabelIds": ["INBOX"]},
                ).execute()
            elif action == "delete_candidate":
                gmail_service.users().messages().trash(userId="me", id=email_id).execute()
            elif action == "label" and label_names:
                for name in label_names[:5]:
                    label_id = _ensure_label_id(gmail_service, name)
                    if label_id:
                        gmail_service.users().messages().modify(
                            userId="me",
                            id=email_id,
                            body={"addLabelIds": [label_id]},
                        ).execute()
            elif action == "create_leads":
                lead_ok = _create_lead_from_classified_email(user_id, email_id)
                if lead_ok:
                    leads_created += 1
            else:
                errors.append({"email_id": email_id, "error": "skipped"})
                continue
            processed += 1
        except Exception as exc:
            errors.append({"email_id": email_id, "error": str(exc)[:200]})

    return {
        "success": processed > 0 and not errors,
        "action": action,
        "processed": processed,
        "leads_created": leads_created,
        "errors": errors,
        "requires_confirmation": action in DESTRUCTIVE_CLEANUP_ACTIONS,
    }


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
