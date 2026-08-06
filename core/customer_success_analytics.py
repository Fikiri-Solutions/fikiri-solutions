"""Customer-success analytics: aggregates, friction, multi-dimension health.

Read-only. Does not call ai_budget_guardrails.evaluate(). Prefer daily aggregates
and authoritative product tables — no raw 90-day event scans for dossier reads.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.product_analytics_registry import product_analytics_enabled
from core.product_analytics_store import (
    earliest_meaningful_outcome_at,
    latest_aggregate_timestamp,
    latest_event_timestamp,
    sum_daily_metrics,
    tables_available,
)

logger = logging.getLogger(__name__)

# Friction thresholds (constants — no ML)
ONBOARDING_STALL_DAYS = 7
NO_MEANINGFUL_ACTIVITY_DAYS = 21
FEATURE_OPEN_WITHOUT_COMPLETION_COUNT = 3
WORKFLOW_FAIL_ATTENTION = 3
STALE_AGGREGATE_MINUTES = 120
A11Y_MIN_SESSIONS = 5

FRICTION_SEVERITY = frozenset({"info", "attention", "blocked"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def build_analytics_state(
    tenant_id: int,
    *,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Completeness metadata — disabled ≠ zero usage."""
    on = product_analytics_enabled() if enabled is None else bool(enabled)
    if not on:
        return {
            "status": "disabled",
            "tracking_since": None,
            "last_event_at": None,
            "last_aggregated_at": None,
            "coverage": "none",
        }
    if not tables_available():
        return {
            "status": "unavailable",
            "tracking_since": None,
            "last_event_at": None,
            "last_aggregated_at": None,
            "coverage": "none",
        }
    last_event = latest_event_timestamp(tenant_id)
    last_agg = latest_aggregate_timestamp(tenant_id)
    if not last_event and not last_agg:
        return {
            "status": "collecting",
            "tracking_since": None,
            "last_event_at": None,
            "last_aggregated_at": None,
            "coverage": "none",
        }
    status = "available"
    coverage = "partial"
    if last_agg:
        agg_dt = _parse_dt(last_agg)
        if agg_dt and (_utc_now() - agg_dt) > timedelta(minutes=STALE_AGGREGATE_MINUTES):
            status = "stale"
    return {
        "status": status,
        "tracking_since": None,
        "last_event_at": last_event,
        "last_aggregated_at": last_agg,
        "coverage": coverage,
    }


def _authoritative_outcomes(tenant_id: int) -> Dict[str, Any]:
    """Derive meaningful outcomes from existing tables (counts only)."""
    from core.database_optimization import db_optimizer

    out = {
        "leads_captured": None,
        "contacts_captured": None,
        "sync_completed_jobs": None,
        "onboarding_completed": None,
    }
    try:
        if db_optimizer.table_exists("leads"):
            rows = db_optimizer.execute_query(
                "SELECT COUNT(*) AS c FROM leads WHERE user_id = ?",
                (int(tenant_id),),
            )
            if rows:
                out["leads_captured"] = int(rows[0]["c"] if hasattr(rows[0], "keys") else rows[0][0])
        if db_optimizer.table_exists("contacts"):
            rows = db_optimizer.execute_query(
                "SELECT COUNT(*) AS c FROM contacts WHERE user_id = ?",
                (int(tenant_id),),
            )
            if rows:
                out["contacts_captured"] = int(rows[0]["c"] if hasattr(rows[0], "keys") else rows[0][0])
        if db_optimizer.table_exists("gmail_sync_jobs"):
            rows = db_optimizer.execute_query(
                """
                SELECT COUNT(*) AS c FROM gmail_sync_jobs
                WHERE user_id = ? AND LOWER(COALESCE(status, '')) = 'completed'
                """,
                (int(tenant_id),),
            )
            if rows:
                out["sync_completed_jobs"] = int(
                    rows[0]["c"] if hasattr(rows[0], "keys") else rows[0][0]
                )
    except Exception as exc:
        logger.warning(
            "authoritative outcomes query failed",
            extra={"event": "cs_analytics.outcomes_failed", "error_type": type(exc).__name__},
        )
    return out


def build_usage_adoption(tenant_id: int, *, lookback_days: int = 30) -> Dict[str, Any]:
    lookback_days = max(1, min(int(lookback_days), 90))
    since = (_utc_now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    state = build_analytics_state(tenant_id)
    if state["status"] in {"disabled", "unavailable"}:
        return {
            "lookback_days": lookback_days,
            "active_days": None,
            "sessions": None,
            "meaningful_actions": None,
            "workflow_started": None,
            "workflow_failed": None,
            "workflow_completion_rate": None,
            "top_features": [],
            "analytics_state": state,
        }
    metrics = sum_daily_metrics(tenant_id, since_date=since)
    started = int(metrics.get("workflow_started") or 0)
    # Completions from server-derived meaningful + not client workflow.completed this slice
    completed = int(metrics.get("workflow_completed") or 0)
    rate = None
    if started > 0:
        rate = round(min(completed, started) / started, 3)
    feature_usage = metrics.get("feature_usage") or {}
    top = sorted(
        [{"feature_key": k, "opens": v} for k, v in feature_usage.items()],
        key=lambda x: x["opens"],
        reverse=True,
    )[:8]
    return {
        "lookback_days": lookback_days,
        "active_days": metrics.get("active_days"),
        "sessions": metrics.get("sessions"),
        "meaningful_actions": metrics.get("meaningful_actions"),
        "workflow_started": started,
        "workflow_failed": metrics.get("workflow_failed"),
        "workflow_completion_rate": rate,
        "top_features": top,
        "last_aggregated_at": state.get("last_aggregated_at"),
        "analytics_state": state,
    }


def build_friction_signals(
    tenant_id: int,
    *,
    dossier: Optional[Dict[str, Any]] = None,
    usage: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Deterministic friction — controlled codes only."""
    dossier = dossier or {}
    usage = usage or {}
    account = dossier.get("account") or {}
    integrations = dossier.get("integrations") or {}
    evaluated_at = _utc_now().isoformat()
    signals: List[Dict[str, Any]] = []

    onboarding_done = bool(account.get("onboarding_completed"))
    created = _parse_dt(account.get("created_at"))
    if not onboarding_done and created:
        if (_utc_now() - created).days >= ONBOARDING_STALL_DAYS:
            signals.append(
                {
                    "code": "ONBOARDING_STALLED",
                    "explanation": f"Onboarding incomplete for {ONBOARDING_STALL_DAYS}+ days",
                    "severity": "attention",
                    "feature_key": "onboarding",
                    "supporting_metric": {"days_since_create": (_utc_now() - created).days},
                    "evaluated_at": evaluated_at,
                }
            )

    gmail = (integrations.get("gmail") or {}).get("state")
    if gmail in {"expired", "refresh_failed", "revoked"}:
        signals.append(
            {
                "code": "INTEGRATION_AUTH_UNHEALTHY",
                "explanation": f"Gmail authorization state: {gmail}",
                "severity": "blocked",
                "feature_key": "integrations",
                "supporting_metric": {"gmail_state": gmail},
                "evaluated_at": evaluated_at,
            }
        )

    failed_jobs = int(integrations.get("failed_job_count") or 0)
    if failed_jobs >= WORKFLOW_FAIL_ATTENTION:
        signals.append(
            {
                "code": "REPEATED_SYNC_FAILURE",
                "explanation": f"{failed_jobs} failed sync jobs",
                "severity": "attention",
                "feature_key": "integrations",
                "supporting_metric": {"failed_job_count": failed_jobs},
                "evaluated_at": evaluated_at,
            }
        )

    state = (usage.get("analytics_state") or {})
    if state.get("status") not in {"disabled", "unavailable", "collecting"}:
        meaningful = usage.get("meaningful_actions")
        last_login = _parse_dt(account.get("last_login"))
        if meaningful == 0 and onboarding_done and last_login:
            if (_utc_now() - last_login).days >= NO_MEANINGFUL_ACTIVITY_DAYS:
                signals.append(
                    {
                        "code": "NO_MEANINGFUL_ACTIVITY",
                        "explanation": f"No meaningful analytics activity in {NO_MEANINGFUL_ACTIVITY_DAYS} days",
                        "severity": "attention",
                        "feature_key": None,
                        "supporting_metric": {"lookback_days": usage.get("lookback_days")},
                        "evaluated_at": evaluated_at,
                    }
                )

    return signals


def build_customer_health(
    dossier: Dict[str, Any],
    *,
    usage: Optional[Dict[str, Any]] = None,
    friction: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Multi-dimension health. Missing analytics → unknown, never healthy-from-empty."""
    account = dossier.get("account") or {}
    integrations = dossier.get("integrations") or {}
    commercial = dossier.get("commercial") or {}
    usage = usage or {}
    friction = friction or []
    outcomes = outcomes or {}
    evaluated_at = _utc_now().isoformat()

    dimensions: Dict[str, Dict[str, Any]] = {}

    # Account
    if not account.get("is_active"):
        dimensions["account"] = {
            "status": "blocked",
            "reasons": [{"code": "ACCOUNT_INACTIVE", "detail": "Account inactive"}],
        }
    elif not account.get("email_verified"):
        dimensions["account"] = {
            "status": "attention",
            "reasons": [{"code": "EMAIL_UNVERIFIED", "detail": "Email unverified"}],
        }
    else:
        dimensions["account"] = {
            "status": "healthy",
            "reasons": [{"code": "ACCOUNT_OK", "detail": "Account active and verified"}],
        }

    # Integration
    g_state = (integrations.get("gmail") or {}).get("state")
    o_state = (integrations.get("outlook") or {}).get("state")
    if g_state in {"expired", "refresh_failed", "revoked"} and o_state not in {"connected"}:
        dimensions["integration"] = {
            "status": "blocked",
            "reasons": [{"code": "GMAIL_AUTH_UNHEALTHY", "detail": f"Gmail {g_state}"}],
        }
    elif g_state == "connected" or o_state == "connected":
        dimensions["integration"] = {
            "status": "healthy",
            "reasons": [{"code": "INTEGRATION_CONNECTED", "detail": "At least one email provider connected"}],
        }
    elif g_state == "disconnected" and o_state in {None, "disconnected", "unknown"}:
        dimensions["integration"] = {
            "status": "not_applicable",
            "reasons": [{"code": "NO_INTEGRATION", "detail": "No email integration connected"}],
        }
    else:
        dimensions["integration"] = {
            "status": "unknown",
            "reasons": [{"code": "INTEGRATION_UNKNOWN", "detail": "Integration state incomplete"}],
        }

    # Reliability (sync jobs)
    failed = int(integrations.get("failed_job_count") or 0)
    if failed > 0:
        dimensions["reliability"] = {
            "status": "attention",
            "reasons": [{"code": "SYNC_FAILURES", "detail": f"{failed} failed sync job(s)"}],
        }
    elif g_state == "connected":
        dimensions["reliability"] = {
            "status": "healthy",
            "reasons": [{"code": "SYNC_OK", "detail": "No failed sync jobs"}],
        }
    else:
        dimensions["reliability"] = {
            "status": "not_applicable",
            "reasons": [{"code": "SYNC_N_A", "detail": "Sync not applicable"}],
        }

    # Product adoption
    state = usage.get("analytics_state") or {}
    if state.get("status") in {"disabled", "unavailable"}:
        dimensions["product_adoption"] = {
            "status": "unknown",
            "reasons": [{"code": "ANALYTICS_DISABLED_OR_UNAVAILABLE", "detail": "Product analytics not available"}],
        }
    elif state.get("status") in {"collecting"} and (usage.get("sessions") in (None, 0)):
        dimensions["product_adoption"] = {
            "status": "insufficient_data",
            "reasons": [{"code": "INSUFFICIENT_ANALYTICS", "detail": "Not enough analytics evidence yet"}],
        }
    elif any(s.get("code") == "NO_MEANINGFUL_ACTIVITY" for s in friction):
        dimensions["product_adoption"] = {
            "status": "at_risk",
            "reasons": [{"code": "NO_MEANINGFUL_ACTIVITY", "detail": "No recent meaningful activity"}],
        }
    elif (usage.get("sessions") or 0) > 0 or (outcomes.get("leads_captured") or 0) > 0:
        dimensions["product_adoption"] = {
            "status": "healthy",
            "reasons": [{"code": "ADOPTION_SIGNAL", "detail": "Recent sessions or CRM outcomes present"}],
        }
    else:
        dimensions["product_adoption"] = {
            "status": "unknown",
            "reasons": [{"code": "ADOPTION_UNKNOWN", "detail": "Adoption evidence incomplete"}],
        }

    # Commercial — missing subscription is N/A / unknown, not unhealthy
    sub = str(commercial.get("status") or "unknown").lower()
    if sub in {"active", "trialing"}:
        dimensions["commercial"] = {
            "status": "healthy",
            "reasons": [{"code": "SUBSCRIPTION_OK", "detail": f"Subscription {sub}"}],
        }
    elif sub in {"past_due", "unpaid"}:
        dimensions["commercial"] = {
            "status": "attention",
            "reasons": [{"code": "SUBSCRIPTION_PAST_DUE", "detail": f"Subscription {sub}"}],
        }
    elif sub in {"canceled", "cancelled"}:
        dimensions["commercial"] = {
            "status": "attention",
            "reasons": [{"code": "SUBSCRIPTION_CANCELED", "detail": f"Subscription {sub}"}],
        }
    else:
        dimensions["commercial"] = {
            "status": "not_applicable",
            "reasons": [
                {
                    "code": "SUBSCRIPTION_ABSENT",
                    "detail": "No paid subscription record (pilots/complimentary allowed)",
                }
            ],
        }

    # Support burden — from dossier support_activity length only
    activity = dossier.get("support_activity") or []
    if len(activity) >= 5:
        dimensions["support_burden"] = {
            "status": "attention",
            "reasons": [{"code": "ELEVATED_SUPPORT", "detail": "Elevated recent support activity"}],
        }
    else:
        dimensions["support_burden"] = {
            "status": "healthy",
            "reasons": [{"code": "SUPPORT_OK", "detail": "Support activity within normal bounds"}],
        }

    # Overall from documented priority
    overall = "healthy"
    reasons: List[Dict[str, str]] = []
    priority = [
        ("account", "blocked"),
        ("integration", "blocked"),
        ("account", "attention"),
        ("product_adoption", "at_risk"),
        ("reliability", "attention"),
        ("product_adoption", "insufficient_data"),
        ("product_adoption", "unknown"),
        ("integration", "unknown"),
    ]
    matched = False
    for dim, want in priority:
        st = (dimensions.get(dim) or {}).get("status")
        if st == want:
            overall = want if want != "insufficient_data" else "unknown"
            reasons.extend((dimensions[dim].get("reasons") or [])[:2])
            matched = True
            break
    if not matched:
        # Prefer unknown over healthy when adoption unknown
        if (dimensions.get("product_adoption") or {}).get("status") == "unknown":
            overall = "unknown"
            reasons.extend((dimensions["product_adoption"].get("reasons") or [])[:1])
        else:
            overall = "healthy"
            reasons.append({"code": "OVERALL_OK", "detail": "No blocking health signals"})

    # Accessibility never contributes
    focus = "Monitor adoption"
    if overall == "blocked":
        focus = "Restore account or integration access"
    elif overall == "at_risk":
        focus = "Re-engage on meaningful product outcomes"
    elif overall == "attention":
        focus = "Clear verification, sync, or billing attention items"
    elif overall == "unknown":
        focus = "Gather more product evidence before judging adoption"

    return {
        "status": overall,
        "reasons": reasons[:5],
        "dimensions": dimensions,
        "recommended_focus": focus,
        "evaluated_at": evaluated_at,
        "analytics_state": state,
    }


def build_customer_outcomes(tenant_id: int, dossier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Canonical sources (documented — do not double-count across these):

    - leads_captured / contacts_captured / syncs_completed: authoritative DB tables
    - meaningful activity rollups: tenant_daily_metrics from analytics emissions
    - time_to_first_value_at: earliest server product_events outcome (partial until tracking)

    Historical periods before analytics tracking remain partial coverage; no silent backfill.
    """
    dossier = dossier or {}
    auth = _authoritative_outcomes(tenant_id)
    account = dossier.get("account") or {}
    auth["onboarding_completed"] = bool(account.get("onboarding_completed"))
    first_outcome = earliest_meaningful_outcome_at(tenant_id)
    created = _parse_dt(account.get("created_at"))
    first_dt = _parse_dt(first_outcome)
    ttfv_days = None
    if created and first_dt:
        ttfv_days = max(0, int((first_dt - created).total_seconds() // 86400))
    return {
        "leads_captured": auth.get("leads_captured"),
        "contacts_captured": auth.get("contacts_captured"),
        "syncs_completed": auth.get("sync_completed_jobs"),
        "onboarding_completed": auth.get("onboarding_completed"),
        "last_meaningful_activity_at": latest_event_timestamp(tenant_id),
        "time_to_first_value_at": first_outcome,
        "time_to_first_value_days": ttfv_days,
        "estimated_time_saved": None,  # deferred
        "canonical_sources": {
            "leads_captured": "leads_table",
            "syncs_completed": "gmail_sync_jobs_table",
            "meaningful_actions": "tenant_daily_metrics",
            "time_to_first_value": "product_events_server_outcomes",
        },
        "notes": (
            "Lead/sync totals from authoritative tables. "
            "TTFV and meaningful-action rollups from server analytics when enabled; "
            "historical coverage remains partial (no silent backfill)."
        ),
    }


def build_customer_success_sections(
    tenant_id: int,
    dossier: Dict[str, Any],
) -> Dict[str, Any]:
    """Compose optional dossier analytics sections."""
    if not product_analytics_enabled():
        state = build_analytics_state(tenant_id, enabled=False)
        return {
            "analytics_state": state,
            "customer_health": {
                "status": "unknown",
                "reasons": [
                    {
                        "code": "ANALYTICS_DISABLED",
                        "detail": "Product analytics disabled — not zero usage",
                    }
                ],
                "dimensions": {},
                "recommended_focus": "Enable analytics to collect adoption evidence",
                "evaluated_at": _utc_now().isoformat(),
                "analytics_state": state,
            },
            "usage_adoption": {
                "lookback_days": 30,
                "active_days": None,
                "sessions": None,
                "analytics_state": state,
            },
            "friction_experience": {"signals": [], "accessibility_signals": None},
            "customer_outcomes": build_customer_outcomes(tenant_id, dossier),
        }

    usage = build_usage_adoption(tenant_id, lookback_days=30)
    usage_7 = build_usage_adoption(tenant_id, lookback_days=7)
    friction = build_friction_signals(tenant_id, dossier=dossier, usage=usage)
    outcomes = build_customer_outcomes(tenant_id, dossier)
    health = build_customer_health(dossier, usage=usage, friction=friction, outcomes=outcomes)
    return {
        "analytics_state": usage.get("analytics_state"),
        "customer_health": health,
        "usage_adoption": {
            **usage,
            "active_days_7": usage_7.get("active_days"),
            "sessions_7": usage_7.get("sessions"),
        },
        "friction_experience": {
            "signals": friction,
            # Accessibility suppressed until flag + sample thresholds
            "accessibility_signals": None,
        },
        "customer_outcomes": outcomes,
    }
