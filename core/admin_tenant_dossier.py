"""Read-only platform-admin tenant support dossier.

Assembles sanitized account / access / integration / product / commercial /
support-activity summaries from existing tables. No privileged mutations.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_OAUTH_STATES = frozenset(
    {"connected", "expired", "revoked", "refresh_failed", "disconnected", "unknown"}
)

_SUPPORT_AUDIT_ACTIONS = frozenset(
    {
        "platform.impersonate.start",
        "platform.impersonate.stop",
        "platform.sync.retry",
        "platform.sync.retry.denied",
        "admin.step_up.succeeded",
        "admin.mfa.totp_succeeded",
        "admin.mfa.recovery_code_used",
        "admin.mfa.required",
        "admin.session.rotated",
    }
)

_PATH_RE = re.compile(r"(?:/Users/[^\s]+|/home/[^\s]+|[A-Za-z]:\\[^\s]+)")
_SECRETISH_RE = re.compile(
    r"(?i)(bearer\s+[a-z0-9\-._~+/]+=*|eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+|"
    r"sk-[a-zA-Z0-9]+|refresh_token|access_token)"
)


def _row_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {}


def _sanitize_message(raw: Any, *, limit: int = 240) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = _PATH_RE.sub("[path]", text)
    text = _SECRETISH_RE.sub("[redacted]", text)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _oauth_provider_state(user_id: int, provider: str, token_table: str) -> Dict[str, Any]:
    """Derive controlled OAuth state without reading token material."""
    from core.database_optimization import db_optimizer

    result: Dict[str, Any] = {
        "provider": provider,
        "connected": False,
        "state": "disconnected",
        "expires_at": None,
        "updated_at": None,
    }
    if not db_optimizer.table_exists(token_table):
        result["state"] = "unknown"
        return result

  # Never SELECT access_token / refresh_token / *_enc.
    try:
        available = set(db_optimizer.list_table_columns(token_table) or [])
    except Exception:
        available = set()
    preferred = ("id", "expires_at", "updated_at", "is_active", "expiry_timestamp")
    select_cols = [c for c in preferred if not available or c in available]
    if not select_cols:
        select_cols = ["id"]
    try:
        rows = db_optimizer.execute_query(
            f"SELECT {', '.join(select_cols)} FROM {token_table} WHERE user_id = ? LIMIT 1",
            (int(user_id),),
        )
    except Exception as exc:
        logger.warning("OAuth state query failed provider=%s: %s", provider, exc)
        result["state"] = "unknown"
        return result

    if not rows:
        return result

    row = _row_dict(rows[0])
    result["connected"] = True
    result["expires_at"] = row.get("expires_at")
    result["updated_at"] = row.get("updated_at")
    if "is_active" in row and row.get("is_active") is not None and not _boolish(row.get("is_active")):
        result["state"] = "disconnected"
        result["connected"] = False
        return result

    # Prefer explicit refresh-failure marker when present.
    if db_optimizer.table_exists("oauth_refresh_failures"):
        try:
            fail_rows = db_optimizer.execute_query(
                """
                SELECT failure_type
                FROM oauth_refresh_failures
                WHERE user_id = ? AND service = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (int(user_id), provider),
            )
            if fail_rows:
                failure_type = str(_row_dict(fail_rows[0]).get("failure_type") or "").lower()
                if failure_type in {"revoked", "token_revoked"}:
                    result["state"] = "revoked"
                    return result
                if failure_type in {"refresh_failed", "token_expired"}:
                    result["state"] = "refresh_failed" if failure_type == "refresh_failed" else "expired"
                    return result
        except Exception as exc:
            logger.debug("oauth_refresh_failures lookup skipped: %s", exc)

    expires = _parse_dt(row.get("expires_at"))
    if expires is None and row.get("expiry_timestamp") is not None:
        try:
            expires = datetime.fromtimestamp(int(row.get("expiry_timestamp")), tz=timezone.utc)
            result["expires_at"] = expires.isoformat()
        except Exception:
            expires = None
    if expires is not None and expires < datetime.now(timezone.utc):
        result["state"] = "expired"
        return result

    result["state"] = "connected"
    assert result["state"] in _OAUTH_STATES
    return result


def _access_summary(user_id: int) -> Dict[str, Any]:
    from core.database_optimization import db_optimizer

    access: Dict[str, Any] = {
        "active_session_count": None,
        "last_login_ip": None,
        "last_login_user_agent": None,
    }
    if not db_optimizer.table_exists("secure_sessions"):
        return access
    try:
        exp_ok = db_optimizer.sql_timestamp_gt_now("expires_at")
        count_rows = db_optimizer.execute_query(
            f"""
            SELECT COUNT(*) AS active_count
            FROM secure_sessions
            WHERE user_id = ? AND is_active = TRUE AND {exp_ok}
            """,
            (int(user_id),),
        )
        if count_rows:
            access["active_session_count"] = int(
                _row_dict(count_rows[0]).get("active_count")
                if hasattr(count_rows[0], "keys")
                else count_rows[0][0]
                or 0
            )
        latest = db_optimizer.execute_query(
            """
            SELECT ip_address, user_agent, last_accessed
            FROM secure_sessions
            WHERE user_id = ?
            ORDER BY last_accessed DESC
            LIMIT 1
            """,
            (int(user_id),),
        )
        if latest:
            row = _row_dict(latest[0])
            access["last_login_ip"] = row.get("ip_address") or None
            ua = row.get("user_agent")
            access["last_login_user_agent"] = (str(ua)[:200] if ua else None)
    except Exception as exc:
        logger.warning("Access summary failed for user %s: %s", user_id, exc)
    return access


def _job_counts(user_id: int) -> Dict[str, Any]:
    from core.database_optimization import db_optimizer

    counts = {
        "pending": 0,
        "processing": 0,
        "failed": 0,
        "completed": 0,
        "retrying": 0,
        "other": 0,
    }
    latest_error = None
    last_success_at = None
    last_failed_at = None
    any_retryable = False

    if not db_optimizer.table_exists("gmail_sync_jobs"):
        return {
            "job_counts": counts,
            "latest_sanitized_error": None,
            "last_successful_sync_at": None,
            "last_failed_sync_at": None,
            "has_retryable_failed_job": False,
        }

    try:
        rows = db_optimizer.execute_query(
            """
            SELECT status, COUNT(*) AS cnt
            FROM gmail_sync_jobs
            WHERE user_id = ?
            GROUP BY status
            """,
            (int(user_id),),
        )
        for row in rows or []:
            data = _row_dict(row)
            status = str(data.get("status") or "other").lower()
            cnt = int(data.get("cnt") if "cnt" in data else (data.get("count") or 0) or 0)
            if status in counts:
                counts[status] = cnt
            else:
                counts["other"] += cnt

        err_rows = db_optimizer.execute_query(
            """
            SELECT error_message, completed_at, created_at, status
            FROM gmail_sync_jobs
            WHERE user_id = ? AND status IN ('failed', 'retrying')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (int(user_id),),
        )
        if err_rows:
            er = _row_dict(err_rows[0])
            latest_error = _sanitize_message(er.get("error_message"))
            last_failed_at = er.get("completed_at") or er.get("created_at")

        ok_rows = db_optimizer.execute_query(
            """
            SELECT completed_at, created_at
            FROM gmail_sync_jobs
            WHERE user_id = ? AND status = 'completed'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (int(user_id),),
        )
        if ok_rows:
            ok = _row_dict(ok_rows[0])
            last_success_at = ok.get("completed_at") or ok.get("created_at")

        any_retryable = int(counts.get("failed") or 0) > 0 or int(counts.get("retrying") or 0) > 0
    except Exception as exc:
        logger.warning("Job count summary failed for user %s: %s", user_id, exc)

    return {
        "job_counts": counts,
        "latest_sanitized_error": latest_error,
        "last_successful_sync_at": last_success_at,
        "last_failed_sync_at": last_failed_at,
        "has_retryable_failed_job": any_retryable,
    }


def _integrations_section(user_id: int, infrastructure: Dict[str, Any]) -> Dict[str, Any]:
    gmail = _oauth_provider_state(user_id, "gmail", "gmail_tokens")
    outlook = _oauth_provider_state(user_id, "outlook", "outlook_tokens")
    jobs = _job_counts(user_id)
    sync = infrastructure.get("sync_status") if isinstance(infrastructure.get("sync_status"), dict) else {}
    return {
        "gmail": gmail,
        "outlook": outlook,
        "sync_status": sync.get("sync_status") if sync else None,
        "last_sync_at": sync.get("last_sync") if sync else None,
        "syncing": bool(sync.get("syncing")) if sync else False,
        "total_emails_indexed": sync.get("total_emails") if sync else None,
        "pending_job_count": int(jobs["job_counts"].get("pending") or 0),
        "processing_job_count": int(jobs["job_counts"].get("processing") or 0),
        "failed_job_count": int(jobs["job_counts"].get("failed") or 0)
        + int(jobs["job_counts"].get("retrying") or 0),
        "job_counts": jobs["job_counts"],
        "last_successful_sync_at": jobs["last_successful_sync_at"] or (sync.get("last_sync") if sync else None),
        "last_failed_sync_at": jobs["last_failed_sync_at"],
        "latest_sanitized_error": jobs["latest_sanitized_error"],
        "has_retryable_failed_job": jobs["has_retryable_failed_job"],
    }


def _product_health_section(user_row: Dict[str, Any], job_counts: Dict[str, int]) -> Dict[str, Any]:
    from core.database_optimization import db_optimizer

    user_id = int(user_row.get("id"))
    onboarding_complete = bool(user_row.get("onboarding_completed"))
    step = user_row.get("onboarding_step")
    blockers: List[str] = []
    if not onboarding_complete:
        blockers.append(f"onboarding_incomplete_step_{step if step is not None else 'unknown'}")
    if not bool(user_row.get("email_verified")):
        blockers.append("email_unverified")
    if not bool(user_row.get("is_active")):
        blockers.append("account_inactive")

    entitlements_enabled: List[str] = []
    entitlements_disabled: List[str] = []
    if db_optimizer.table_exists("user_feature_access"):
        try:
            rows = db_optimizer.execute_query(
                """
                SELECT feature_name, has_access
                FROM user_feature_access
                WHERE user_id = ?
                ORDER BY feature_name ASC
                LIMIT 50
                """,
                (user_id,),
            )
            for row in rows or []:
                data = _row_dict(row)
                name = str(data.get("feature_name") or "").strip()
                if not name:
                    continue
                if _boolish(data.get("has_access")):
                    entitlements_enabled.append(name)
                else:
                    entitlements_disabled.append(name)
        except Exception as exc:
            logger.debug("feature access summary skipped: %s", exc)

    ai_budget: Dict[str, Any] = {"status": "unknown"}
    try:
        from core.ai_budget_guardrails import ai_budget_guardrails

        decision = ai_budget_guardrails.snapshot(user_id)
        ai_budget = {
            "status": "ok" if decision.allowed else "blocked",
            "reason": str(getattr(decision, "reason", None) or "unknown")[:80],
            "tier": str(getattr(decision, "tier", None) or "unknown"),
            "month": str(getattr(decision, "month", None) or ""),
            "estimated_cost_usd": float(getattr(decision, "estimated_cost_usd", 0) or 0),
            "budget_cap_usd": float(getattr(decision, "budget_cap_usd", 0) or 0),
            "allowed": bool(decision.allowed),
        }
    except Exception as exc:
        logger.debug("AI budget summary skipped: %s", exc)
        ai_budget = {"status": "unknown"}

    return {
        "last_product_activity_at": user_row.get("last_login") or user_row.get("updated_at"),
        "onboarding_complete": onboarding_complete,
        "onboarding_step": step,
        "onboarding_blockers": blockers,
        "entitlements_enabled": entitlements_enabled,
        "entitlements_disabled": entitlements_disabled,
        "ai_budget": ai_budget,
        "background_jobs": job_counts,
    }


def _commercial_section(infrastructure: Dict[str, Any], product_health: Dict[str, Any]) -> Dict[str, Any]:
    sub = infrastructure.get("subscription") if isinstance(infrastructure.get("subscription"), dict) else None
    if not sub:
        return {
            "tier": None,
            "status": "unknown",
            "current_period_end": None,
            "past_due": None,
            "ai_budget": product_health.get("ai_budget") or {"status": "unknown"},
        }
    status = str(sub.get("status") or "unknown").lower()
    past_due = status in {"past_due", "unpaid"} if status != "unknown" else None
    return {
        "tier": sub.get("tier"),
        "status": status or "unknown",
        "current_period_end": sub.get("current_period_end"),
        "past_due": past_due,
        # Intentionally omit stripe_subscription_id from dossier commercial (kept on legacy infrastructure).
        "ai_budget": product_health.get("ai_budget") or {"status": "unknown"},
    }


def _support_activity(user_id: int, *, limit: int = 20) -> List[Dict[str, Any]]:
    from core.admin_audit import list_admin_audit

    limit = max(1, min(int(limit), 20))
    try:
        raw = list_admin_audit(limit=limit, offset=0, target_id=str(int(user_id)))
    except Exception as exc:
        logger.warning("Support activity audit list failed: %s", exc)
        return []

    items: List[Dict[str, Any]] = []
    for entry in raw.get("items") or []:
        action = str(entry.get("action") or "")
        # Prefer known support-relevant actions; still include other platform.* target hits (bounded).
        if action not in _SUPPORT_AUDIT_ACTIONS and not action.startswith("platform."):
            continue
        corr = entry.get("correlation_id")
        corr_short = None
        if corr:
            corr_short = str(corr)[:12]
        reason = None
        meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        if isinstance(meta, dict):
            reason = meta.get("reason") or meta.get("error_code") or meta.get("code")
            reason = _sanitize_message(reason, limit=80) if reason else None
        items.append(
            {
                "timestamp": str(entry.get("created_at")) if entry.get("created_at") is not None else None,
                "action": action,
                "outcome": entry.get("outcome") or "unknown",
                "reason_code": reason,
                "actor_user_id": entry.get("actor_user_id"),
                "target_type": entry.get("target_type"),
                "target_id": str(entry.get("target_id")) if entry.get("target_id") is not None else None,
                "correlation_id": corr_short,
            }
        )
        if len(items) >= limit:
            break
    return items


_CHECKLIST_STATUSES = frozenset(
    {"healthy", "attention", "blocked", "unknown", "not_applicable"}
)
_OAUTH_USABLE = frozenset({"connected"})
_OAUTH_AUTH_BLOCKED = frozenset({"expired", "refresh_failed", "revoked"})
_OAUTH_IDLE = frozenset({"disconnected"})


def _checklist_item(
    *,
    item_id: str,
    label: str,
    status: str,
    section: str,
    explanation: str,
) -> Dict[str, Any]:
    if status not in _CHECKLIST_STATUSES:
        status = "unknown"
    return {
        "id": item_id,
        "label": label,
        "status": status,
        "section": section,
        "explanation": explanation,
    }


def build_impersonation_eligibility(account: Dict[str, Any]) -> Dict[str, Any]:
    """Read-only target eligibility mirroring start_impersonation USER_INACTIVE rule.

    Operator step-up/MFA remain enforced at mutation time; this only surfaces
    target-side blockers so the UI can disable the action safely.
    """
    if not account.get("is_active"):
        return {
            "eligible": False,
            "reason_code": "USER_INACTIVE",
            "reason_label": "Account inactive",
        }
    return {
        "eligible": True,
        "reason_code": "AVAILABLE",
        "reason_label": "Available after operator step-up and MFA",
    }


def _provider_label(state: str, provider: str) -> str:
    mapping = {
        "expired": f"{provider} authorization expired",
        "refresh_failed": f"{provider} token refresh failed",
        "revoked": f"{provider} access revoked",
        "disconnected": f"{provider} disconnected",
        "connected": f"{provider} connected",
        "unknown": f"{provider} state unknown",
    }
    return mapping.get(state, f"{provider} {state}")


def _email_integration_checklist(integrations: Dict[str, Any]) -> Dict[str, Any]:
    gmail = integrations.get("gmail") or {}
    outlook = integrations.get("outlook") or {}
    g_state = str(gmail.get("state") or "unknown")
    o_state = str(outlook.get("state") or "unknown")
    if g_state not in _OAUTH_STATES:
        g_state = "unknown"
    if o_state not in _OAUTH_STATES:
        o_state = "unknown"

    states = [g_state, o_state]
    usable = [s for s in states if s in _OAUTH_USABLE]
    blocked = [s for s in states if s in _OAUTH_AUTH_BLOCKED]
    unknown = [s for s in states if s == "unknown"]
    idle = [s for s in states if s in _OAUTH_IDLE]

    if usable and blocked:
        reasons = []
        if g_state in _OAUTH_AUTH_BLOCKED:
            reasons.append(_provider_label(g_state, "Gmail"))
        if o_state in _OAUTH_AUTH_BLOCKED:
            reasons.append(_provider_label(o_state, "Outlook"))
        return _checklist_item(
            item_id="email_integration_usable",
            label="Email integration usable",
            status="attention",
            section="integration-health",
            explanation="; ".join(reasons) or "One provider unhealthy",
        )
    if usable:
        return _checklist_item(
            item_id="email_integration_usable",
            label="Email integration usable",
            status="healthy",
            section="integration-health",
            explanation="At least one email provider is connected",
        )
    if blocked and not usable:
        parts: List[str] = []
        if g_state in _OAUTH_AUTH_BLOCKED:
            parts.append(_provider_label(g_state, "Gmail"))
        if o_state in _OAUTH_AUTH_BLOCKED:
            parts.append(_provider_label(o_state, "Outlook"))
        return _checklist_item(
            item_id="email_integration_usable",
            label="Email integration usable",
            status="blocked",
            section="integration-health",
            explanation="; ".join(parts) or "Email authorization unusable",
        )
    if unknown and not usable and not blocked:
        return _checklist_item(
            item_id="email_integration_usable",
            label="Email integration usable",
            status="unknown",
            section="integration-health",
            explanation="Email integration state cannot be determined",
        )
    if idle and not usable and not blocked and not unknown:
        return _checklist_item(
            item_id="email_integration_usable",
            label="Email integration usable",
            status="not_applicable",
            section="integration-health",
            explanation="No email integration connected",
        )
    return _checklist_item(
        item_id="email_integration_usable",
        label="Email integration usable",
        status="unknown",
        section="integration-health",
        explanation="Email integration state cannot be determined",
    )


def _sync_job_health_checklist(integrations: Dict[str, Any]) -> Dict[str, Any]:
    """Job-queue health only — never overridden by historical successful sync."""
    failed = int(integrations.get("failed_job_count") or 0)
    pending = int(integrations.get("pending_job_count") or 0)
    processing = int(integrations.get("processing_job_count") or 0)
    g_state = str((integrations.get("gmail") or {}).get("state") or "unknown")
    o_state = str((integrations.get("outlook") or {}).get("state") or "unknown")
    auth_blocked = g_state in _OAUTH_AUTH_BLOCKED or o_state in _OAUTH_AUTH_BLOCKED

    if failed > 0:
        return _checklist_item(
            item_id="sync_job_health",
            label="Sync job health",
            status="blocked",
            section="sync-jobs",
            explanation=f"{failed} failed sync job(s)",
        )
    if auth_blocked and not (
        g_state in _OAUTH_USABLE or o_state in _OAUTH_USABLE
    ):
        # Auth failure blocks sync even with a clean job queue / historical success.
        explanation = (
            _provider_label(g_state, "Gmail")
            if g_state in _OAUTH_AUTH_BLOCKED
            else _provider_label(o_state, "Outlook")
        )
        return _checklist_item(
            item_id="sync_job_health",
            label="Sync job health",
            status="blocked",
            section="integration-health",
            explanation=f"Cannot authorize — {explanation}",
        )
    if pending + processing > 0:
        return _checklist_item(
            item_id="sync_job_health",
            label="Sync job health",
            status="attention",
            section="sync-jobs",
            explanation=f"{pending + processing} active sync job(s)",
        )
    if g_state in _OAUTH_IDLE and o_state in _OAUTH_IDLE:
        return _checklist_item(
            item_id="sync_job_health",
            label="Sync job health",
            status="not_applicable",
            section="sync-jobs",
            explanation="No email integration to sync",
        )
    return _checklist_item(
        item_id="sync_job_health",
        label="Sync job health",
        status="healthy",
        section="sync-jobs",
        explanation="No failed or active sync jobs",
    )


def build_support_checklist(dossier: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive a health-oriented checklist from dossier sections (no extra DB I/O).

    Canonical status: healthy | attention | blocked | unknown | not_applicable.
    Labels describe healthy conditions; green never means “a problem exists.”
    """
    account = dossier.get("account") or {}
    access = dossier.get("access") or {}
    integrations = dossier.get("integrations") or {}
    product = dossier.get("product_health") or {}
    commercial = dossier.get("commercial") or {}
    eligibility = dossier.get("impersonation_eligibility") or build_impersonation_eligibility(account)

    is_active = bool(account.get("is_active"))
    email_verified = bool(account.get("email_verified") or access.get("email_verified"))
    onboarding_done = bool(account.get("onboarding_completed") or product.get("onboarding_complete"))
    step = account.get("onboarding_step")
    if step is None:
        step = product.get("onboarding_step")

    if not is_active and not email_verified:
        account_item = _checklist_item(
            item_id="account_usable",
            label="Account usable",
            status="blocked",
            section="account-access",
            explanation="Inactive and email unverified",
        )
    elif not is_active:
        account_item = _checklist_item(
            item_id="account_usable",
            label="Account usable",
            status="blocked",
            section="account-access",
            explanation="Account inactive",
        )
    elif not email_verified:
        account_item = _checklist_item(
            item_id="account_usable",
            label="Account usable",
            status="attention",
            section="account-access",
            explanation="Email unverified",
        )
    else:
        account_item = _checklist_item(
            item_id="account_usable",
            label="Account usable",
            status="healthy",
            section="account-access",
            explanation="Account active and verified",
        )

    email_item = _checklist_item(
        item_id="email_verified",
        label="Email verified",
        status="healthy" if email_verified else "attention",
        section="account-access",
        explanation="Verified" if email_verified else "Account email is unverified",
    )

    if onboarding_done:
        onboarding_item = _checklist_item(
            item_id="onboarding_complete",
            label="Onboarding complete",
            status="healthy",
            section="product-health",
            explanation="Onboarding completed",
        )
    else:
        step_note = f" (step {step})" if step is not None else ""
        onboarding_item = _checklist_item(
            item_id="onboarding_complete",
            label="Onboarding complete",
            status="attention",
            section="product-health",
            explanation=f"Onboarding incomplete{step_note}",
        )

    failed = int(integrations.get("failed_job_count") or 0)
    has_retryable = bool(integrations.get("has_retryable_failed_job"))

    if failed > 0:
        recent_item = _checklist_item(
            item_id="no_recent_failures",
            label="No recent failures",
            status="attention" if failed < 3 else "blocked",
            section="integration-health",
            explanation=f"{failed} failed sync job(s)",
        )
    else:
        recent_item = _checklist_item(
            item_id="no_recent_failures",
            label="No recent failures",
            status="healthy",
            section="integration-health",
            explanation="No recent failed sync jobs",
        )

    if has_retryable:
        retry_item = _checklist_item(
            item_id="no_retryable_failed_jobs",
            label="No retryable failed jobs",
            status="attention",
            section="sync-jobs",
            explanation="Retryable failed jobs require attention",
        )
    elif failed == 0:
        retry_item = _checklist_item(
            item_id="no_retryable_failed_jobs",
            label="No retryable failed jobs",
            status="not_applicable",
            section="sync-jobs",
            explanation="No retryable failed jobs",
        )
    else:
        retry_item = _checklist_item(
            item_id="no_retryable_failed_jobs",
            label="No retryable failed jobs",
            status="healthy",
            section="sync-jobs",
            explanation="Failed jobs are not retryable from admin",
        )

    sub_status = str(commercial.get("status") or "unknown").lower()
    if sub_status in {"active", "trialing"}:
        sub_item = _checklist_item(
            item_id="subscription_active",
            label="Subscription active",
            status="healthy",
            section="commercial",
            explanation=f"Subscription {sub_status}",
        )
    elif sub_status in {"past_due", "unpaid"}:
        sub_item = _checklist_item(
            item_id="subscription_active",
            label="Subscription active",
            status="attention",
            section="commercial",
            explanation=f"Subscription {sub_status}",
        )
    elif sub_status in {"canceled", "cancelled", "incomplete_expired"}:
        sub_item = _checklist_item(
            item_id="subscription_active",
            label="Subscription active",
            status="blocked",
            section="commercial",
            explanation=f"Subscription {sub_status}",
        )
    else:
        sub_item = _checklist_item(
            item_id="subscription_active",
            label="Subscription active",
            status="unknown",
            section="commercial",
            explanation="Subscription status unavailable",
        )

    if eligibility.get("eligible"):
        impersonation_item = _checklist_item(
            item_id="impersonation_available",
            label="Impersonation available",
            status="healthy",
            section="support-actions",
            explanation=str(eligibility.get("reason_label") or "Available after operator step-up and MFA"),
        )
    else:
        reason = str(eligibility.get("reason_label") or "Impersonation unavailable")
        code = str(eligibility.get("reason_code") or "")
        status = "blocked" if code == "USER_INACTIVE" else "attention"
        impersonation_item = _checklist_item(
            item_id="impersonation_available",
            label="Impersonation available",
            status=status,
            section="support-actions",
            explanation=reason,
        )

    return [
        account_item,
        email_item,
        onboarding_item,
        _email_integration_checklist(integrations),
        _sync_job_health_checklist(integrations),
        recent_item,
        retry_item,
        sub_item,
        impersonation_item,
    ]


def build_tenant_dossier(
    user_row: Dict[str, Any],
    *,
    infrastructure: Dict[str, Any],
    support_activity_limit: int = 20,
) -> Dict[str, Any]:
    """Build sanitized dossier sections for a tenant user row."""
    user_id = int(user_row.get("id"))
    infra = infrastructure or {}

    account = {
        "id": user_row.get("id"),
        "name": user_row.get("name"),
        "email": user_row.get("email"),
        "business_name": user_row.get("business_name"),
        "industry": user_row.get("industry"),
        "role": user_row.get("role"),
        "is_active": bool(user_row.get("is_active")),
        "email_verified": bool(user_row.get("email_verified")),
        "created_at": user_row.get("created_at"),
        "updated_at": user_row.get("updated_at"),
        "last_login": user_row.get("last_login"),
        "onboarding_step": user_row.get("onboarding_step"),
        "onboarding_completed": bool(user_row.get("onboarding_completed")),
    }
    access = {
        "is_active": account["is_active"],
        "email_verified": account["email_verified"],
        "role": account["role"],
        "last_login": account["last_login"],
        **_access_summary(user_id),
    }
    integrations = _integrations_section(user_id, infra)
    product_health = _product_health_section(user_row, integrations.get("job_counts") or {})
    commercial = _commercial_section(infra, product_health)
    support_activity = _support_activity(user_id, limit=support_activity_limit)
    impersonation_eligibility = build_impersonation_eligibility(account)
    dossier = {
        "account": account,
        "access": access,
        "integrations": integrations,
        "product_health": product_health,
        "commercial": commercial,
        "support_activity": support_activity,
        "impersonation_eligibility": impersonation_eligibility,
    }
    dossier["support_checklist"] = build_support_checklist(dossier)
    # Optional customer-success analytics — failures must not break the dossier.
    try:
        from core.customer_success_analytics import build_customer_success_sections

        cs = build_customer_success_sections(user_id, dossier)
        dossier["analytics_state"] = cs.get("analytics_state")
        dossier["customer_health"] = cs.get("customer_health")
        dossier["usage_adoption"] = cs.get("usage_adoption")
        dossier["friction_experience"] = cs.get("friction_experience")
        dossier["customer_outcomes"] = cs.get("customer_outcomes")
    except Exception as exc:
        logger.warning(
            "customer success analytics compose failed",
            extra={"event": "dossier.cs_analytics_failed", "error_type": type(exc).__name__},
        )
    return dossier
