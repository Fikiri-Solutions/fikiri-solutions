"""
Tier-based monthly usage caps for cost-sensitive endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Tuple

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# `-1` means unlimited.
TIER_USAGE_LIMITS: Dict[str, Dict[str, int]] = {
    "free": {"ai_responses": 50, "email_processing": 100},
    "starter": {"ai_responses": 200, "email_processing": 500},
    "growth": {"ai_responses": 800, "email_processing": 2000},
    "business": {"ai_responses": 4000, "email_processing": 10000},
    "enterprise": {"ai_responses": -1, "email_processing": -1},
}


def resolve_subscription_tier(user_id: int, db=None) -> str:
    """Return active/trialing subscription tier; default to starter when unknown."""
    db = db or db_optimizer
    try:
        if not db.table_exists("subscriptions"):
            return "starter"
        rows = db.execute_query(
            """
            SELECT status, tier
            FROM subscriptions
            WHERE user_id = ?
            ORDER BY current_period_end DESC, updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        if not rows:
            return "starter"
        status = (rows[0].get("status") or "").lower()
        tier = (rows[0].get("tier") or "starter").lower()
        if status in {"active", "trialing"} and tier in TIER_USAGE_LIMITS:
            return tier
        return "free"
    except Exception as e:
        logger.warning("Tier lookup failed for user %s: %s", user_id, e)
        return "starter"


def get_monthly_usage(user_id: int, usage_type: str, month: str, db=None) -> int:
    db = db or db_optimizer
    try:
        if not db.table_exists("billing_usage"):
            return 0
        rows = db.execute_query(
            """
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM billing_usage
            WHERE user_id = ? AND month = ? AND usage_type = ?
            """,
            (user_id, month, usage_type),
        )
        return int(rows[0].get("total") or 0) if rows else 0
    except Exception as e:
        logger.warning("Usage lookup failed user=%s usage_type=%s: %s", user_id, usage_type, e)
        return 0


def record_monthly_usage(user_id: int, usage_type: str, quantity: int = 1, db=None) -> None:
    db = db or db_optimizer
    if not user_id or quantity <= 0:
        return
    try:
        if not db.table_exists("billing_usage"):
            return
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        db.execute_query(
            """
            INSERT INTO billing_usage (user_id, month, usage_type, quantity)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, month, usage_type, quantity),
            fetch=False,
        )
    except Exception as e:
        logger.warning("Failed to record usage user=%s usage_type=%s: %s", user_id, usage_type, e)


def check_tier_usage_cap(
    user_id: int, usage_type: str, projected_increment: int = 1, db=None
) -> Tuple[bool, str, str]:
    """
    Return (allowed, error_message, error_code) for projected usage.
    Error fields are empty when allowed.
    """
    try:
        db = db or db_optimizer
        tier = resolve_subscription_tier(user_id, db=db)
        tier_caps = TIER_USAGE_LIMITS.get(tier, TIER_USAGE_LIMITS["starter"])
        cap = int(tier_caps.get(usage_type, -1))
        if cap < 0:
            return True, "", ""

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        used = get_monthly_usage(user_id, usage_type, month, db=db)
        projected = used + max(0, int(projected_increment))
        if projected > cap:
            return (
                False,
                f"Plan limit exceeded for {usage_type}. {tier.title()} allows {cap} per month.",
                "PLAN_LIMIT_EXCEEDED",
            )
    except Exception as e:
        # Fail-open by design to avoid blocking on usage accounting issues.
        logger.warning("Tier cap check failed user=%s usage_type=%s: %s", user_id, usage_type, e)
    return True, "", ""
