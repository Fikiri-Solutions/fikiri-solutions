"""
Durable email workflow state: classification lifecycle + Command Center queue visibility.

Stable identity: (user_id, external_id, provider).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

CLASSIFICATION_STATUSES = frozenset(
    {"unclassified", "classified", "reclassified", "failed"}
)
WORKFLOW_STATUSES = frozenset(
    {
        "active",
        "done",
        "archived",
        "dismissed",
        "spam",
        "converted_to_lead",
        "replied",
    }
)
HANDLED_WORKFLOW_STATUSES = frozenset(
    {"archived", "dismissed", "done", "spam", "converted_to_lead", "replied"}
)
CLASSIFIED_STATUSES = frozenset({"classified", "reclassified"})


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_email_workflow_state_table() -> None:
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS email_workflow_state (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            external_id TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'gmail',
            synced_email_id INTEGER,
            classification_id INTEGER,
            provider_thread_id TEXT,
            classification_status TEXT NOT NULL DEFAULT 'unclassified',
            workflow_status TEXT NOT NULL DEFAULT 'active',
            user_override_category TEXT,
            user_override_reason TEXT,
            last_action TEXT,
            last_action_source TEXT,
            last_action_at TEXT,
            last_classified_at TEXT,
            handled_at TEXT,
            classification_version INTEGER NOT NULL DEFAULT 0,
            hidden_from_command_center INTEGER NOT NULL DEFAULT 0,
            hidden_from_live_mail INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(user_id, external_id, provider)
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_email_workflow_user_status
        ON email_workflow_state (user_id, workflow_status)
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_email_workflow_user_class_status
        ON email_workflow_state (user_id, classification_status)
        """,
        fetch=False,
    )


def get_email_identity(
    *,
    user_id: int,
    external_id: str,
    provider: str = "gmail",
    provider_thread_id: Optional[str] = None,
    synced_email_id: Optional[int] = None,
) -> Dict[str, Any]:
    ext = str(external_id or "").strip()
    prov = (provider or "gmail").strip().lower() or "gmail"
    return {
        "user_id": int(user_id),
        "external_id": ext,
        "provider": prov,
        "provider_thread_id": provider_thread_id,
        "synced_email_id": synced_email_id,
    }


def _normalize_provider(provider: str) -> str:
    return (provider or "gmail").strip().lower() or "gmail"


def _fetch_workflow_row(
    user_id: int, external_id: str, provider: str
) -> Optional[Dict[str, Any]]:
    ensure_email_workflow_state_table()
    rows = db_optimizer.execute_query(
        """
        SELECT *
        FROM email_workflow_state
        WHERE user_id = ? AND external_id = ? AND provider = ?
        LIMIT 1
        """,
        (user_id, external_id, _normalize_provider(provider)),
    )
    return rows[0] if rows else None


def _classification_row_exists(user_id: int, external_id: str, provider: str) -> bool:
    from core.email_triage_store import ensure_email_classifications_table

    ensure_email_classifications_table()
    rows = db_optimizer.execute_query(
        """
        SELECT id, updated_at
        FROM email_classifications
        WHERE user_id = ? AND external_id = ? AND provider = ?
        LIMIT 1
        """,
        (user_id, external_id, _normalize_provider(provider)),
    )
    return bool(rows)


def _backfill_from_classification(
    user_id: int,
    external_id: str,
    provider: str,
    *,
    synced_email_id: Optional[int] = None,
    provider_thread_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create workflow row when classification exists but workflow does not."""
    if not _classification_row_exists(user_id, external_id, provider):
        return None
    rows = db_optimizer.execute_query(
        """
        SELECT id, updated_at
        FROM email_classifications
        WHERE user_id = ? AND external_id = ? AND provider = ?
        LIMIT 1
        """,
        (user_id, external_id, _normalize_provider(provider)),
    )
    if not rows:
        return None
    now = _utcnow_iso()
    last_cls = rows[0].get("updated_at") or now
    cid = int(rows[0]["id"]) if rows[0].get("id") is not None else None
    db_optimizer.execute_query(
        """
        INSERT INTO email_workflow_state (
            user_id, external_id, provider, synced_email_id, classification_id,
            provider_thread_id, classification_status, workflow_status,
            last_classified_at, classification_version, hidden_from_command_center,
            hidden_from_live_mail, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'classified', 'active', ?, 0, 0, 0, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO NOTHING
        """,
        (
            user_id,
            external_id,
            _normalize_provider(provider),
            synced_email_id,
            cid,
            provider_thread_id,
            last_cls,
            now,
            now,
        ),
        fetch=False,
    )
    return _fetch_workflow_row(user_id, external_id, provider)


def get_or_create_workflow_state(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    provider_thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    ext = str(external_id or "").strip()
    if not ext:
        raise ValueError("external_id required")
    prov = _normalize_provider(provider)
    existing = _fetch_workflow_row(user_id, ext, prov)
    if existing:
        return existing

    backfilled = _backfill_from_classification(
        user_id,
        ext,
        prov,
        synced_email_id=synced_email_id,
        provider_thread_id=provider_thread_id,
    )
    if backfilled:
        return backfilled

    now = _utcnow_iso()
    db_optimizer.execute_query(
        """
        INSERT INTO email_workflow_state (
            user_id, external_id, provider, synced_email_id, provider_thread_id,
            classification_status, workflow_status, classification_version,
            hidden_from_command_center, hidden_from_live_mail, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'unclassified', 'active', 0, 0, 0, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO NOTHING
        """,
        (user_id, ext, prov, synced_email_id, provider_thread_id, now, now),
        fetch=False,
    )
    row = _fetch_workflow_row(user_id, ext, prov)
    if row:
        return row
    raise RuntimeError("failed to create email_workflow_state row")


def should_classify_email(
    user_id: int,
    external_id: str,
    provider: str = "gmail",
    *,
    force: bool = False,
) -> bool:
    if force:
        return True
    ext = str(external_id or "").strip()
    if not ext:
        return False
    prov = _normalize_provider(provider)
    row = _fetch_workflow_row(user_id, ext, prov)
    if not row:
        if _classification_row_exists(user_id, ext, prov):
            _backfill_from_classification(user_id, ext, prov)
            return False
        return True
    status = str(row.get("classification_status") or "unclassified")
    if status in CLASSIFIED_STATUSES:
        return False
    if status == "failed":
        return True
    return status == "unclassified"


def workflow_status_is_handled(workflow_status: Optional[str]) -> bool:
    return str(workflow_status or "").strip().lower() in HANDLED_WORKFLOW_STATUSES


def should_show_in_command_center(
    workflow_row: Optional[Dict[str, Any]],
    *,
    include_handled: bool = False,
) -> bool:
    if include_handled:
        return True
    if not workflow_row:
        return True
    if int(workflow_row.get("hidden_from_command_center") or 0):
        return False
    status = str(workflow_row.get("workflow_status") or "active")
    return not workflow_status_is_handled(status)


def command_center_workflow_sql(
    *,
    include_handled: bool = False,
    table_alias: str = "w",
) -> Tuple[str, List[Any]]:
    """SQL fragment + params for active Command Center queue (LEFT JOIN workflow)."""
    if include_handled:
        return "", []
    a = table_alias
    sql = f"""
        AND (
            {a}.id IS NULL
            OR (
                COALESCE({a}.workflow_status, 'active') = 'active'
                AND COALESCE({a}.hidden_from_command_center, 0) = 0
            )
        )
    """
    return sql, []


def mark_classified(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    classification_id: Optional[int] = None,
    provider_thread_id: Optional[str] = None,
    source: str = "sync",
) -> None:
    ensure_email_workflow_state_table()
    ext = str(external_id or "").strip()
    prov = _normalize_provider(provider)
    now = _utcnow_iso()
    get_or_create_workflow_state(
        user_id,
        ext,
        provider=prov,
        synced_email_id=synced_email_id,
        provider_thread_id=provider_thread_id,
    )
    db_optimizer.execute_query(
        """
        INSERT INTO email_workflow_state (
            user_id, external_id, provider, synced_email_id, classification_id,
            provider_thread_id, classification_status, workflow_status,
            last_classified_at, last_action, last_action_source, last_action_at,
            classification_version, hidden_from_command_center, hidden_from_live_mail,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'classified', 'active', ?, 'classify', ?, ?, 0, 0, 0, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO UPDATE SET
            synced_email_id = COALESCE(excluded.synced_email_id, email_workflow_state.synced_email_id),
            classification_id = COALESCE(excluded.classification_id, email_workflow_state.classification_id),
            provider_thread_id = COALESCE(excluded.provider_thread_id, email_workflow_state.provider_thread_id),
            classification_status = CASE
                WHEN email_workflow_state.classification_status = 'reclassified' THEN 'reclassified'
                ELSE 'classified'
            END,
            workflow_status = CASE
                WHEN email_workflow_state.workflow_status IN (
                    'archived', 'dismissed', 'done', 'spam', 'converted_to_lead', 'replied'
                )
                THEN email_workflow_state.workflow_status
                ELSE 'active'
            END,
            last_classified_at = excluded.last_classified_at,
            last_action = excluded.last_action,
            last_action_source = excluded.last_action_source,
            last_action_at = excluded.last_action_at,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            ext,
            prov,
            synced_email_id,
            classification_id,
            provider_thread_id,
            now,
            source,
            now,
            now,
            now,
        ),
        fetch=False,
    )


def mark_reclassified(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    classification_id: Optional[int] = None,
    provider_thread_id: Optional[str] = None,
) -> None:
    ensure_email_workflow_state_table()
    ext = str(external_id or "").strip()
    prov = _normalize_provider(provider)
    now = _utcnow_iso()
    get_or_create_workflow_state(
        user_id,
        ext,
        provider=prov,
        synced_email_id=synced_email_id,
        provider_thread_id=provider_thread_id,
    )
    db_optimizer.execute_query(
        """
        INSERT INTO email_workflow_state (
            user_id, external_id, provider, synced_email_id, classification_id,
            provider_thread_id, classification_status, workflow_status,
            last_classified_at, last_action, last_action_source, last_action_at,
            classification_version, hidden_from_command_center, hidden_from_live_mail,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'reclassified', 'active', ?, 'reclassify', 'command_center', ?, 1, 0, 0, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO UPDATE SET
            synced_email_id = COALESCE(excluded.synced_email_id, email_workflow_state.synced_email_id),
            classification_id = COALESCE(excluded.classification_id, email_workflow_state.classification_id),
            provider_thread_id = COALESCE(excluded.provider_thread_id, email_workflow_state.provider_thread_id),
            classification_status = 'reclassified',
            workflow_status = CASE
                WHEN email_workflow_state.workflow_status IN (
                    'archived', 'dismissed', 'done', 'spam', 'converted_to_lead', 'replied'
                )
                THEN email_workflow_state.workflow_status
                ELSE 'active'
            END,
            last_classified_at = excluded.last_classified_at,
            last_action = excluded.last_action,
            last_action_source = excluded.last_action_source,
            last_action_at = excluded.last_action_at,
            classification_version = email_workflow_state.classification_version + 1,
            hidden_from_command_center = 0,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            ext,
            prov,
            synced_email_id,
            classification_id,
            provider_thread_id,
            now,
            now,
            now,
            now,
        ),
        fetch=False,
    )


def mark_classification_failed(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    source: str = "sync",
) -> None:
    ensure_email_workflow_state_table()
    ext = str(external_id or "").strip()
    prov = _normalize_provider(provider)
    now = _utcnow_iso()
    get_or_create_workflow_state(
        user_id,
        ext,
        provider=prov,
        synced_email_id=synced_email_id,
    )
    db_optimizer.execute_query(
        """
        INSERT INTO email_workflow_state (
            user_id, external_id, provider, synced_email_id,
            classification_status, workflow_status, last_action, last_action_source,
            last_action_at, classification_version, hidden_from_command_center,
            hidden_from_live_mail, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'failed', 'active', 'classify_failed', ?, ?, 0, 0, 0, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO UPDATE SET
            classification_status = 'failed',
            last_action = excluded.last_action,
            last_action_source = excluded.last_action_source,
            last_action_at = excluded.last_action_at,
            updated_at = excluded.updated_at
        """,
        (user_id, ext, prov, synced_email_id, source, now, now, now),
        fetch=False,
    )


def workflow_action_spec(action: str) -> Dict[str, Any]:
    """Map bulk/UI action id to workflow transition (no Gmail side effects)."""
    key = str(action or "").strip().lower()
    specs: Dict[str, Dict[str, Any]] = {
        "archive": {
            "workflow_status": "archived",
            "hide_from_command_center": True,
            "requires_gmail": True,
            "gmail_modify": {"removeLabelIds": ["INBOX"]},
        },
        "spam_candidate": {
            "workflow_status": "spam",
            "hide_from_command_center": True,
            "requires_gmail": True,
            "gmail_modify": {"addLabelIds": ["SPAM"], "removeLabelIds": ["INBOX"]},
        },
        "spam": {
            "workflow_status": "spam",
            "hide_from_command_center": True,
            "requires_gmail": False,
        },
        "dismiss": {
            "workflow_status": "dismissed",
            "hide_from_command_center": True,
            "requires_gmail": False,
        },
        "not_a_lead": {
            "workflow_status": "dismissed",
            "hide_from_command_center": True,
            "requires_gmail": False,
            "user_override_category": "personal_non_business",
        },
        "done": {
            "workflow_status": "done",
            "hide_from_command_center": True,
            "requires_gmail": False,
        },
        "create_leads": {
            "workflow_status": "converted_to_lead",
            "hide_from_command_center": False,
            "requires_gmail": False,
        },
        "delete_candidate": {
            "workflow_status": "archived",
            "hide_from_command_center": True,
            "requires_gmail": True,
            "gmail_trash": True,
        },
        "mark_read": {
            "workflow_status": None,
            "hide_from_command_center": False,
            "requires_gmail": True,
            "gmail_modify": {"removeLabelIds": ["UNREAD"]},
            "touch_only": True,
        },
        "mark_unread": {
            "workflow_status": None,
            "hide_from_command_center": False,
            "requires_gmail": True,
            "gmail_modify": {"addLabelIds": ["UNREAD"]},
            "touch_only": True,
        },
        "label": {
            "workflow_status": None,
            "hide_from_command_center": False,
            "requires_gmail": True,
        },
        "reply_sent": {
            "workflow_status": "replied",
            "hide_from_command_center": False,
            "requires_gmail": False,
        },
        "restore_to_queue": {
            "workflow_status": "active",
            "hide_from_command_center": False,
            "requires_gmail": False,
            "clear_handled_at": True,
        },
    }
    return specs.get(key, {"workflow_status": None, "hide_from_command_center": False, "requires_gmail": False})


def workflow_already_at_target(
    user_id: int,
    external_id: str,
    action: str,
    *,
    provider: str = "gmail",
) -> bool:
    """True when re-applying the same handled transition is a no-op."""
    spec = workflow_action_spec(action)
    if spec.get("touch_only"):
        return False
    target = spec.get("workflow_status")
    if not target:
        return False
    row = _fetch_workflow_row(user_id, external_id, provider)
    if not row:
        return False
    if str(row.get("workflow_status") or "") != target:
        return False
    if spec.get("hide_from_command_center") and not int(row.get("hidden_from_command_center") or 0):
        return False
    return True


def synced_email_remove_inbox_label(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
) -> bool:
    """Remove INBOX from synced_emails.labels when row exists (best-effort)."""
    rows = db_optimizer.execute_query(
        """
        SELECT labels FROM synced_emails
        WHERE user_id = ? AND provider = ?
          AND (external_id = ? OR gmail_id = ?)
        LIMIT 1
        """,
        (user_id, _normalize_provider(provider), external_id, external_id),
    )
    if not rows:
        return False
    labels = _parse_labels(rows[0].get("labels"))
    if "INBOX" not in labels:
        return False
    labels = [x for x in labels if x != "INBOX"]
    db_optimizer.execute_query(
        """
        UPDATE synced_emails
        SET labels = ?
        WHERE user_id = ? AND provider = ?
          AND (external_id = ? OR gmail_id = ?)
        """,
        (
            json.dumps(labels),
            user_id,
            _normalize_provider(provider),
            external_id,
            external_id,
        ),
        fetch=False,
    )
    return True


def synced_email_mark_read_local(
    user_id: int,
    external_id: str,
    *,
    provider: str = "gmail",
) -> bool:
    """Mark synced row read locally (remove UNREAD label, is_read=true)."""
    rows = db_optimizer.execute_query(
        """
        SELECT labels FROM synced_emails
        WHERE user_id = ? AND provider = ?
          AND (external_id = ? OR gmail_id = ?)
        LIMIT 1
        """,
        (user_id, _normalize_provider(provider), external_id, external_id),
    )
    if not rows:
        return False
    labels = [x for x in _parse_labels(rows[0].get("labels")) if x != "UNREAD"]
    db_optimizer.execute_query(
        """
        UPDATE synced_emails
        SET labels = ?, is_read = """ + db_optimizer.sql_true_literal() + """
        WHERE user_id = ? AND provider = ?
          AND (external_id = ? OR gmail_id = ?)
        """,
        (
            json.dumps(labels),
            user_id,
            _normalize_provider(provider),
            external_id,
            external_id,
        ),
        fetch=False,
    )
    return True


def _parse_labels(raw: Any) -> List[str]:
    if not raw:
        return []
    try:
        labels = json.loads(raw) if isinstance(raw, str) else list(raw)
    except (json.JSONDecodeError, TypeError):
        labels = []
    return labels if isinstance(labels, list) else []


def mark_action_applied(
    user_id: int,
    external_id: str,
    *,
    action: str,
    provider: str = "gmail",
    source: str = "command_center",
    workflow_status: Optional[str] = None,
    user_override_category: Optional[str] = None,
    user_override_reason: Optional[str] = None,
    hide_from_command_center: Optional[bool] = None,
) -> str:
    """
    Idempotent workflow transition for user actions.
    Returns ``updated`` or ``skipped``.
    """
    ensure_email_workflow_state_table()
    ext = str(external_id or "").strip()
    if not ext:
        return "skipped"
    prov = _normalize_provider(provider)
    action_key = str(action or "").strip().lower()
    now = _utcnow_iso()
    spec = workflow_action_spec(action_key)

    if spec.get("touch_only"):
        get_or_create_workflow_state(user_id, ext, provider=prov)
        row = _fetch_workflow_row(user_id, ext, prov) or {}
        if (
            str(row.get("last_action") or "") == action_key
            and str(row.get("last_action_source") or "") == source
        ):
            return "skipped"
        db_optimizer.execute_query(
            """
            UPDATE email_workflow_state
            SET last_action = ?,
                last_action_source = ?,
                last_action_at = ?,
                updated_at = ?
            WHERE user_id = ? AND external_id = ? AND provider = ?
            """,
            (action_key, source, now, now, user_id, ext, prov),
            fetch=False,
        )
        return "updated"

    new_status = workflow_status or spec.get("workflow_status") or "active"
    if new_status not in WORKFLOW_STATUSES:
        new_status = "active"

    override_cat = user_override_category or spec.get("user_override_category")

    row = get_or_create_workflow_state(user_id, ext, provider=prov)
    if workflow_already_at_target(user_id, ext, action_key, provider=prov):
        if (
            override_cat
            and str(row.get("user_override_category") or "") == override_cat
        ):
            return "skipped"
        if not override_cat:
            return "skipped"

    if hide_from_command_center is True:
        hide_cc = 1
    elif hide_from_command_center is False:
        hide_cc = 0
    elif "hide_from_command_center" in spec:
        hide_cc = 1 if spec.get("hide_from_command_center") else 0
    else:
        hide_cc = int(row.get("hidden_from_command_center") or 0)
    if spec.get("clear_handled_at"):
        handled_at = None
    elif workflow_status_is_handled(new_status):
        handled_at = now
    else:
        handled_at = row.get("handled_at")

    db_optimizer.execute_query(
        """
        UPDATE email_workflow_state
        SET workflow_status = ?,
            user_override_category = COALESCE(?, user_override_category),
            user_override_reason = COALESCE(?, user_override_reason),
            last_action = ?,
            last_action_source = ?,
            last_action_at = ?,
            handled_at = ?,
            hidden_from_command_center = ?,
            updated_at = ?
        WHERE user_id = ? AND external_id = ? AND provider = ?
        """,
        (
            new_status,
            override_cat,
            user_override_reason,
            action_key,
            source,
            now,
            handled_at,
            hide_cc,
            now,
            user_id,
            ext,
            prov,
        ),
        fetch=False,
    )
    return "updated"


def persist_workflow_after_user_action(
    user_id: int,
    external_id: str,
    action: str,
    *,
    provider: str = "gmail",
    source: str = "command_center",
    user_override_category: Optional[str] = None,
) -> str:
    """Workflow row + synced_emails mirror for a successful user action."""
    result = mark_action_applied(
        user_id,
        external_id,
        action=action,
        provider=provider,
        source=source,
        user_override_category=user_override_category,
    )
    spec = workflow_action_spec(action)
    try:
        if action in ("archive", "spam_candidate", "delete_candidate"):
            synced_email_remove_inbox_label(user_id, external_id, provider=provider)
        elif action in ("mark_read",):
            synced_email_mark_read_local(user_id, external_id, provider=provider)
    except Exception as exc:
        logger.warning(
            "synced_emails mirror skipped user=%s id=%s action=%s: %s",
            user_id,
            external_id,
            action,
            exc,
        )
    return result


def persist_live_mail_archive(user_id: int, email_id: str) -> None:
    """Best-effort after Gmail archive succeeds (Live Mail)."""
    try:
        persist_workflow_after_user_action(
            user_id, email_id, "archive", provider="gmail", source="live_mail"
        )
    except Exception as exc:
        logger.warning("persist_live_mail_archive workflow skipped: %s", exc)


def persist_live_mail_mark_read(user_id: int, email_id: str) -> None:
    """Best-effort after Gmail mark-read succeeds; keeps workflow active."""
    try:
        synced_email_mark_read_local(user_id, email_id, provider="gmail")
        mark_action_applied(
            user_id, email_id, action="mark_read", provider="gmail", source="live_mail"
        )
    except Exception as exc:
        logger.warning("persist_live_mail_mark_read skipped: %s", exc)


def fetch_workflow_by_external_ids(
    user_id: int,
    external_ids: List[str],
    *,
    provider: str = "gmail",
) -> Dict[str, Dict[str, Any]]:
    if not external_ids:
        return {}
    ensure_email_workflow_state_table()
    prov = _normalize_provider(provider)
    placeholders = ",".join("?" for _ in external_ids)
    rows = db_optimizer.execute_query(
        f"""
        SELECT * FROM email_workflow_state
        WHERE user_id = ? AND provider = ? AND external_id IN ({placeholders})
        """,
        tuple([user_id, prov, *external_ids]),
    )
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        out[str(row.get("external_id"))] = row
    return out
