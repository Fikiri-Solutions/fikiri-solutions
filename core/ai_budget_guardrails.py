"""
AI budget guardrails for tenant-level cost control.

Implements:
- monthly estimated AI spend checks per user/tenant
- alert thresholds (80/90/100%) with dedupe per month
- enterprise soft-stop near cap that can be overridden via approval
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


@dataclass
class AIBudgetDecision:
    allowed: bool
    reason: str
    tier: str
    month: str
    estimated_cost_usd: float
    projected_cost_usd: float
    budget_cap_usd: float
    threshold_ratio: float
    requires_approval: bool = False


class AIBudgetGuardrails:
    ALERT_LEVELS = (0.8, 0.9, 1.0)

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        try:
            false_lit = db_optimizer.sql_false_literal()
            db_optimizer.execute_query(
                """
                CREATE TABLE IF NOT EXISTS ai_budget_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    alert_level REAL NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    budget_cap_usd REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, month, alert_level)
                )
                """,
                fetch=False,
            )
            db_optimizer.execute_query(
                f"""
                CREATE TABLE IF NOT EXISTS ai_budget_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    approved BOOLEAN NOT NULL DEFAULT {false_lit},
                    approved_by TEXT,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, month)
                )
                """,
                fetch=False,
            )
        except Exception as e:
            logger.warning("AI budget guardrail tables init failed: %s", e)

    def _month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _subscription_tier(self, user_id: int) -> str:
        try:
            if not db_optimizer.table_exists("subscriptions"):
                return "starter"
            rows = db_optimizer.execute_query(
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
            return tier if status in {"active", "trialing"} else "free"
        except Exception:
            return "starter"

    def _budget_cap_usd(self, tier: str) -> float:
        env_map = {
            "free": "AI_BUDGET_FREE_USD",
            "starter": "AI_BUDGET_STARTER_USD",
            "growth": "AI_BUDGET_GROWTH_USD",
            "business": "AI_BUDGET_BUSINESS_USD",
            "enterprise": "AI_BUDGET_ENTERPRISE_USD",
        }
        defaults = {
            "free": 2.0,
            "starter": 10.0,
            "growth": 35.0,
            "business": 150.0,
            "enterprise": 400.0,
        }
        key = env_map.get(tier, "AI_BUDGET_STARTER_USD")
        default = defaults.get(tier, 10.0)
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _estimated_cost_per_response(self) -> float:
        try:
            return float(os.getenv("AI_ESTIMATED_COST_PER_RESPONSE_USD", "0.0015"))
        except ValueError:
            return 0.0015

    def _enterprise_soft_stop_threshold(self) -> float:
        try:
            return float(os.getenv("AI_ENTERPRISE_SOFT_STOP_THRESHOLD", "0.95"))
        except ValueError:
            return 0.95

    def _monthly_usage_count(self, user_id: int, month: str) -> int:
        try:
            rows = db_optimizer.execute_query(
                """
                SELECT COALESCE(SUM(quantity), 0) as total
                FROM billing_usage
                WHERE user_id = ? AND month = ? AND usage_type = 'ai_responses'
                """,
                (user_id, month),
            )
            return int(rows[0].get("total") or 0) if rows else 0
        except Exception:
            return 0

    def _has_approval(self, user_id: int, month: str) -> bool:
        try:
            rows = db_optimizer.execute_query(
                """
                SELECT approved
                FROM ai_budget_approvals
                WHERE user_id = ? AND month = ?
                LIMIT 1
                """,
                (user_id, month),
            )
            return bool(rows and rows[0].get("approved"))
        except Exception:
            return False

    def _emit_alerts(self, user_id: int, month: str, ratio: float, est: float, cap: float):
        for level in self.ALERT_LEVELS:
            if ratio < level:
                continue
            try:
                db_optimizer.execute_query(
                    """
                    INSERT INTO ai_budget_alerts
                    (user_id, month, alert_level, estimated_cost_usd, budget_cap_usd)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (user_id, month, alert_level) DO NOTHING
                    """,
                    (user_id, month, level, est, cap),
                    fetch=False,
                )
                logger.warning(
                    "AI budget alert user=%s month=%s level=%.0f%% est=$%.2f cap=$%.2f",
                    user_id,
                    month,
                    level * 100,
                    est,
                    cap,
                )
            except Exception:
                # Alerts should never break request flow.
                pass

    def evaluate(self, user_id: Optional[int], projected_increment: int = 1) -> AIBudgetDecision:
        if not user_id:
            return AIBudgetDecision(
                allowed=True,
                reason="no_user",
                tier="unknown",
                month=self._month(),
                estimated_cost_usd=0.0,
                projected_cost_usd=0.0,
                budget_cap_usd=0.0,
                threshold_ratio=0.0,
            )

        month = self._month()
        tier = self._subscription_tier(user_id)
        cap = self._budget_cap_usd(tier)
        per_response = self._estimated_cost_per_response()
        used = self._monthly_usage_count(user_id, month)
        est = round(used * per_response, 4)
        projected = round((used + max(0, projected_increment)) * per_response, 4)
        ratio = (projected / cap) if cap > 0 else 0.0

        self._emit_alerts(user_id, month, ratio, projected, cap)

        # Hard stop for non-enterprise tiers at 100% of monthly budget cap
        if tier in ("free", "starter", "growth", "business"):
            if ratio >= 1.0:
                return AIBudgetDecision(
                    allowed=False,
                    reason="monthly_budget_cap_reached",
                    tier=tier,
                    month=month,
                    estimated_cost_usd=est,
                    projected_cost_usd=projected,
                    budget_cap_usd=cap,
                    threshold_ratio=ratio,
                )

        if tier == "enterprise":
            soft_stop = self._enterprise_soft_stop_threshold()
            if ratio >= soft_stop and not self._has_approval(user_id, month):
                return AIBudgetDecision(
                    allowed=False,
                    reason="enterprise_soft_stop_requires_approval",
                    tier=tier,
                    month=month,
                    estimated_cost_usd=est,
                    projected_cost_usd=projected,
                    budget_cap_usd=cap,
                    threshold_ratio=ratio,
                    requires_approval=True,
                )

        return AIBudgetDecision(
            allowed=True,
            reason="ok",
            tier=tier,
            month=month,
            estimated_cost_usd=est,
            projected_cost_usd=projected,
            budget_cap_usd=cap,
            threshold_ratio=ratio,
        )

    def record_ai_usage(self, user_id: Optional[int], quantity: int = 1):
        if not user_id or quantity <= 0:
            return
        try:
            month = self._month()
            db_optimizer.execute_query(
                """
                INSERT INTO billing_usage (user_id, month, usage_type, quantity)
                VALUES (?, ?, 'ai_responses', ?)
                """,
                (user_id, month, quantity),
                fetch=False,
            )
        except Exception as e:
            logger.warning("Failed to record ai_responses usage: %s", e)


ai_budget_guardrails = AIBudgetGuardrails()
