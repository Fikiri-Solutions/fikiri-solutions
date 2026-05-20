"""Persist email triage classifications (synced_emails → email_classifications)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.ai.email_triage_taxonomy import normalize_cleanup_action, normalize_triage_category
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def ensure_email_classifications_table() -> None:
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS email_classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            synced_email_id INTEGER,
            external_id TEXT,
            provider TEXT DEFAULT 'gmail',
            category TEXT NOT NULL,
            lead_score INTEGER DEFAULT 0,
            business_relevance_score INTEGER DEFAULT 0,
            urgency_score INTEGER DEFAULT 0,
            cleanup_action TEXT NOT NULL DEFAULT 'keep',
            confidence REAL NOT NULL DEFAULT 0.5,
            reason TEXT,
            suggested_labels TEXT DEFAULT '[]',
            classification_source TEXT DEFAULT 'rules',
            intent_canonical TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(user_id, external_id, provider)
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_email_classifications_user_category
        ON email_classifications (user_id, category)
        """,
        fetch=False,
    )


def upsert_classification(
    user_id: int,
    *,
    external_id: str,
    provider: str = "gmail",
    synced_email_id: Optional[int] = None,
    triage: Dict[str, Any],
) -> None:
    ensure_email_classifications_table()
    now = datetime.now(timezone.utc).isoformat()
    labels_json = json.dumps(triage.get("suggested_labels") or [])
    db_optimizer.execute_query(
        """
        INSERT INTO email_classifications (
            user_id, synced_email_id, external_id, provider,
            category, lead_score, business_relevance_score, urgency_score,
            cleanup_action, confidence, reason, suggested_labels,
            classification_source, intent_canonical, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, external_id, provider) DO UPDATE SET
            synced_email_id = COALESCE(excluded.synced_email_id, synced_email_id),
            category = excluded.category,
            lead_score = excluded.lead_score,
            business_relevance_score = excluded.business_relevance_score,
            urgency_score = excluded.urgency_score,
            cleanup_action = excluded.cleanup_action,
            confidence = excluded.confidence,
            reason = excluded.reason,
            suggested_labels = excluded.suggested_labels,
            classification_source = excluded.classification_source,
            intent_canonical = excluded.intent_canonical,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            synced_email_id,
            external_id,
            provider,
            normalize_triage_category(triage.get("category")),
            int(triage.get("lead_score") or 0),
            int(triage.get("business_relevance_score") or 0),
            int(triage.get("urgency_score") or 0),
            normalize_cleanup_action(triage.get("cleanup_action")),
            float(triage.get("confidence") or 0.5),
            (triage.get("reason") or "")[:1000],
            labels_json,
            triage.get("classification_source") or "rules",
            triage.get("intent_canonical"),
            now,
            now,
        ),
        fetch=False,
    )


def list_classified_emails(
    user_id: int,
    *,
    category: Optional[str] = None,
    cleanup_action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    ensure_email_classifications_table()
    limit = max(1, min(500, limit))
    offset = max(0, offset)
    where = ["c.user_id = ?"]
    params: List[Any] = [user_id]
    if category:
        where.append("c.category = ?")
        params.append(normalize_triage_category(category))
    if cleanup_action:
        where.append("c.cleanup_action = ?")
        params.append(normalize_cleanup_action(cleanup_action))

    where_sql = " AND ".join(where)
    rows = db_optimizer.execute_query(
        f"""
        SELECT
            c.id AS classification_id,
            c.category, c.lead_score, c.business_relevance_score, c.urgency_score,
            c.cleanup_action, c.confidence, c.reason, c.suggested_labels,
            c.classification_source, c.intent_canonical, c.external_id, c.provider,
            s.subject, s.sender, s.date, s.is_read, s.labels
        FROM email_classifications c
        LEFT JOIN synced_emails s
          ON s.user_id = c.user_id
         AND (s.external_id = c.external_id OR s.gmail_id = c.external_id)
         AND COALESCE(s.provider, 'gmail') = c.provider
        WHERE {where_sql}
        ORDER BY c.lead_score DESC, s.date DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params) + (limit, offset),
    )
    count_row = db_optimizer.execute_query(
        f"SELECT COUNT(*) AS total FROM email_classifications c WHERE {where_sql}",
        tuple(params),
    )
    total = int(count_row[0]["total"]) if count_row else 0
    emails = []
    for row in rows or []:
        try:
            suggested = json.loads(row.get("suggested_labels") or "[]")
        except (json.JSONDecodeError, TypeError):
            suggested = []
        emails.append(
            {
                "id": row.get("external_id"),
                "classification_id": row.get("classification_id"),
                "provider": row.get("provider") or "gmail",
                "subject": row.get("subject") or "",
                "from": row.get("sender") or "",
                "date": row.get("date") or "",
                "unread": not bool(row.get("is_read")),
                "category": row.get("category"),
                "lead_score": row.get("lead_score"),
                "business_relevance_score": row.get("business_relevance_score"),
                "urgency_score": row.get("urgency_score"),
                "cleanup_action": row.get("cleanup_action"),
                "confidence": row.get("confidence"),
                "reason": row.get("reason"),
                "suggested_labels": suggested,
                "classification_source": row.get("classification_source"),
                "intent_canonical": row.get("intent_canonical"),
            }
        )
    return {
        "emails": emails,
        "pagination": {
            "total_count": total,
            "returned_count": len(emails),
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(emails)) < total,
        },
    }
