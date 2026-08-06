"""Platform admin API: tenant directory, impersonation, audit trail."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from flask import Blueprint, g, request

from core.admin_audit import list_admin_audit, record_admin_audit_from_request
from core.admin_security import (
    check_admin_rate_limit,
    destructive_admin_enabled,
    establish_admin_step_up,
    get_admin_step_up_state,
    get_request_correlation_id,
    impersonation_disabled,
    issue_admin_csrf_token,
    mfa_required_for_operators,
    mfa_verifier_enabled,
    operator_account_usable,
    operator_mfa_enrolled,
    require_admin_csrf_if_cookie_auth,
    require_admin_step_up,
    require_impersonation_enabled,
    require_no_nested_impersonation,
    rotate_session_after_step_up,
    step_up_completed_with_mfa,
    validate_browser_origin_for_cookie_auth,
    verify_operator_mfa,
    verify_operator_password,
)
from core.admin_mfa import (
    cancel_totp_enrollment,
    confirm_totp_enrollment,
    disable_operator_mfa,
    get_mfa_status,
    regenerate_recovery_codes,
    start_totp_enrollment,
    verify_operator_mfa_code,
)
from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.database_optimization import db_optimizer
from core.jwt_auth import get_jwt_manager, jwt_required
from core.platform_admin import (
    get_platform_capabilities,
    is_platform_admin,
    require_platform_capability,
    summarize_capabilities,
)
from core.secure_sessions import get_actor_user_id, get_current_user_id, is_impersonating
from core.admin_security_store import AdminSecurityStoreUnavailable

logger = logging.getLogger(__name__)

admin_platform_bp = Blueprint("admin_platform", __name__, url_prefix="/api/admin/platform")


@admin_platform_bp.after_request
def _admin_no_store(response):
    """Sensitive admin API responses must not be cached."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    return response


@admin_platform_bp.before_request
def _block_platform_apis_while_impersonating():
    """Operator console APIs are unavailable during view-as-user; stop remains allowed."""
    if request.method == "OPTIONS":
        return None
    path = (request.path or "").rstrip("/")
    if path.endswith("/impersonate/stop"):
        return None
    if not is_impersonating():
        return None
    actor_id = get_actor_user_id() or get_current_user_id()
    if actor_id:
        try:
            record_admin_audit_from_request(
                actor_user_id=int(actor_id),
                action="platform.api.denied",
                target_type="path",
                target_id=path,
                outcome="denied",
                metadata={"reason": "IMPERSONATION_ACTIVE"},
            )
        except Exception:
            pass
    return create_error_response("Forbidden", 403, "FORBIDDEN_WHILE_IMPERSONATING")


def _row_value(row: Any, key: str, index: int):
    if hasattr(row, "keys"):
        return row.get(key)
    return row[index]


def _fetch_user_row(user_id: int) -> Optional[Dict[str, Any]]:
    active = db_optimizer.sql_cast_int_eq_one("is_active")
    rows = db_optimizer.execute_query(
        f"""
        SELECT id, email, name, role, business_name, business_email, industry, team_size,
               is_active, email_verified, created_at, updated_at, last_login,
               onboarding_completed, onboarding_step, metadata
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (user_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return dict(row) if hasattr(row, "keys") else {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "business_name": row[4],
        "business_email": row[5],
        "industry": row[6],
        "team_size": row[7],
        "is_active": row[8],
        "email_verified": row[9],
        "created_at": row[10],
        "updated_at": row[11],
        "last_login": row[12],
        "onboarding_completed": row[13],
        "onboarding_step": row[14],
        "metadata": row[15],
    }


def _integration_summary(user_id: int) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "gmail_connected": False,
        "outlook_connected": False,
        "sync_status": None,
        "subscription": None,
        "pending_gmail_jobs": 0,
    }

    if db_optimizer.table_exists("gmail_tokens"):
        gmail_rows = db_optimizer.execute_query(
            "SELECT id FROM gmail_tokens WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        summary["gmail_connected"] = bool(gmail_rows)

    if db_optimizer.table_exists("outlook_tokens"):
        outlook_rows = db_optimizer.execute_query(
            "SELECT id FROM outlook_tokens WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        summary["outlook_connected"] = bool(outlook_rows)

    if db_optimizer.table_exists("user_sync_status"):
        sync_rows = db_optimizer.execute_query(
            """
            SELECT last_sync, sync_status, syncing, total_emails, updated_at
            FROM user_sync_status
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        )
        if sync_rows:
            row = sync_rows[0]
            summary["sync_status"] = dict(row) if hasattr(row, "keys") else {
                "last_sync": row[0],
                "sync_status": row[1],
                "syncing": row[2],
                "total_emails": row[3],
                "updated_at": row[4],
            }

    if db_optimizer.table_exists("subscriptions"):
        sub_rows = db_optimizer.execute_query(
            """
            SELECT tier, status, current_period_end, stripe_subscription_id
            FROM subscriptions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        if sub_rows:
            row = sub_rows[0]
            summary["subscription"] = dict(row) if hasattr(row, "keys") else {
                "tier": row[0],
                "status": row[1],
                "current_period_end": row[2],
                "stripe_subscription_id": row[3],
            }

    if db_optimizer.table_exists("gmail_sync_jobs"):
        job_rows = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS pending_count
            FROM gmail_sync_jobs
            WHERE user_id = ? AND status IN ('pending', 'processing')
            """,
            (user_id,),
        )
        if job_rows:
            summary["pending_gmail_jobs"] = int(
                _row_value(job_rows[0], "pending_count", 0) or 0
            )

    return summary


def _serialize_tenant(user_row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user_row.get("id"),
        "email": user_row.get("email"),
        "name": user_row.get("name"),
        "role": user_row.get("role"),
        "business_name": user_row.get("business_name"),
        "industry": user_row.get("industry"),
        "is_active": bool(user_row.get("is_active")),
        "email_verified": bool(user_row.get("email_verified")),
        "onboarding_completed": bool(user_row.get("onboarding_completed")),
        "onboarding_step": user_row.get("onboarding_step"),
        "created_at": user_row.get("created_at"),
        "last_login": user_row.get("last_login"),
    }


@admin_platform_bp.route("/me", methods=["GET"])
@handle_api_errors
@jwt_required
def platform_admin_me():
    from core.admin_security import admin_lockdown_active, destructive_admin_enabled

    if admin_lockdown_active():
        from core.admin_security import lockdown_response

        return lockdown_response()

    actor_id = get_actor_user_id() or get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    capabilities = summarize_capabilities(get_platform_capabilities(actor_id))
    return create_success_response(
        {
            "is_platform_admin": is_platform_admin(actor_id),
            "capabilities": capabilities,
            "impersonating": is_impersonating(),
            "actor_user_id": actor_id,
            "effective_user_id": get_current_user_id(),
            "security": {
                "mfa_required": mfa_required_for_operators(),
                "mfa_enrolled": operator_mfa_enrolled(int(actor_id)),
                "step_up_active": bool(get_admin_step_up_state(int(actor_id))),
                "step_up_mfa_completed": step_up_completed_with_mfa(int(actor_id)),
                "destructive_enabled": destructive_admin_enabled(),
                "impersonation_disabled": impersonation_disabled(),
                "lockdown": admin_lockdown_active(),
            },
        },
        "Platform admin context retrieved",
    )


@admin_platform_bp.route("/status", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.tenants.read")
def platform_admin_status():
    """Read-only Overview contract: operator posture, gates, audit/sync/analytics signals."""
    from core.admin_security import admin_lockdown_active, lockdown_response
    from core.platform_admin_status import build_platform_status

    if admin_lockdown_active():
        return lockdown_response()

    actor_id = get_actor_user_id() or get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    capabilities = summarize_capabilities(get_platform_capabilities(actor_id))
    payload = build_platform_status(actor_user_id=int(actor_id), capabilities=capabilities)
    return create_success_response(payload, "Platform status retrieved")


@admin_platform_bp.route("/sync-jobs", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.ops.read")
def list_platform_sync_jobs():
    """Cross-tenant failed/retrying sync inbox (read-only, bounded)."""
    from core.admin_sync_ops import list_actionable_sync_jobs

    raw_status = (request.args.get("status") or "failed,retrying").strip()
    statuses = [part.strip() for part in raw_status.split(",") if part.strip()]
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    result = list_actionable_sync_jobs(statuses=statuses, limit=limit, offset=offset)
    return create_success_response(result, "Actionable sync jobs retrieved")


@admin_platform_bp.route("/security/csrf", methods=["GET"])
@handle_api_errors
@jwt_required
def admin_csrf_token():
    """Issue CSRF token for cookie-authenticated admin mutations."""
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()
    actor_id = get_current_user_id()
    if not actor_id or not is_platform_admin(actor_id) or is_impersonating():
        return create_error_response("Forbidden", 403, "FORBIDDEN")
    try:
        token = issue_admin_csrf_token(int(actor_id))
    except ValueError:
        return create_error_response("Session binding required", 400, "SESSION_REQUIRED")
    return create_success_response({"csrf_token": token}, "CSRF token issued")


@admin_platform_bp.route("/security/reauthenticate", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
def admin_reauthenticate():
    """Password reauthentication establishing short-lived server-side step-up state."""
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()

    actor_id = get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    # Generic denial for non-operators / impersonation / inactive (no enumeration).
    if is_impersonating() or not is_platform_admin(actor_id) or not operator_account_usable(int(actor_id)):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="admin.step_up.denied",
            outcome="denied",
            metadata={"reason": "UNAUTHORIZED"},
        )
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")

    ip_key = (request.remote_addr or "unknown")
    allowed, _retry = check_admin_rate_limit(
        bucket="admin_reauth",
        actor_key=f"{actor_id}:{ip_key}",
        limit=5,
        window_seconds=300,
    )
    if not allowed:
        return create_error_response("Too many attempts", 429, "RATE_LIMITED")

    payload = request.get_json(silent=True) or {}
    password = payload.get("password") or ""
    mfa_code = payload.get("mfa_code") or payload.get("totp_code")
    recovery_code = payload.get("recovery_code")

    if not verify_operator_password(int(actor_id), password):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="admin.step_up.denied",
            outcome="denied",
            metadata={"reason": "AUTH_FAILED"},
        )
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")

    mfa_method = None
    mfa_completed = False
    if mfa_required_for_operators():
        mfa_ok, mfa_err = verify_operator_mfa(
            int(actor_id), mfa_code, recovery_code=recovery_code
        )
        if not mfa_ok:
            # Unenrolled operators may complete password-only step-up so they can
            # enroll MFA. Other privileged actions still require mfa_completed.
            if mfa_err == "MFA_ENROLLMENT_REQUIRED":
                record_admin_audit_from_request(
                    actor_user_id=int(actor_id),
                    action="admin.step_up.enrollment_bootstrap",
                    outcome="success",
                    metadata={"reason": mfa_err},
                )
            else:
                action = "admin.mfa.required"
                if mfa_err == "MFA_REPLAY":
                    action = "admin.mfa.totp_replay_denied"
                elif recovery_code:
                    action = "admin.mfa.recovery_code_denied"
                elif mfa_code:
                    action = "admin.mfa.totp_denied"
                record_admin_audit_from_request(
                    actor_user_id=int(actor_id),
                    action=action,
                    outcome="denied",
                    metadata={"reason": mfa_err},
                )
                return create_error_response("Authentication failed", 403, "REAUTH_FAILED")
        else:
            mfa_completed = True
            mfa_method = "recovery" if recovery_code else "mfa"
            record_admin_audit_from_request(
                actor_user_id=int(actor_id),
                action="admin.mfa.recovery_code_used" if mfa_method == "recovery" else "admin.mfa.totp_succeeded",
                outcome="success",
                metadata={"method": mfa_method},
            )
    method = mfa_method or "password"

    try:
        bundle = establish_admin_step_up(
            actor_user_id=int(actor_id),
            method=method,
            mfa_completed=mfa_completed,
        )
    except PermissionError as exc:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="admin.mfa.required",
            outcome="denied",
            metadata={"reason": str(exc)},
        )
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")
    except AdminSecurityStoreUnavailable:
        return create_error_response("Service temporarily unavailable", 503, "STORE_UNAVAILABLE")
    except ValueError:
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")

    rotation = rotate_session_after_step_up(int(actor_id))
    if rotation.get("step_up_orphaned"):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="admin.step_up.succeeded",
            outcome="denied",
            metadata={
                "method": method,
                "mfa_completed": mfa_completed,
                "reason": "step_up_orphaned_after_rotation",
            },
        )
        return create_error_response(
            "Step-up could not be bound to the new session; please reauthenticate",
            503,
            "STEP_UP_ORPHANED",
        )

    record_admin_audit_from_request(
        actor_user_id=int(actor_id),
        action="admin.step_up.succeeded",
        outcome="success",
        metadata={
            "method": method,
            "mfa_completed": mfa_completed,
            "expires_in": bundle.get("expires_in"),
            "rotated": bool(rotation.get("rotated")),
        },
    )
    response_data = {
        "step_up_confirmed": True,
        "expires_in": bundle.get("expires_in"),
        "method": method,
        "mfa_completed": mfa_completed,
        "authenticated_at": bundle.get("authenticated_at"),
        "session_rotated": bool(rotation.get("rotated")),
    }
    if rotation.get("access_token"):
        response_data["access_token"] = rotation["access_token"]
        response_data["expires_in_token"] = rotation.get("expires_in")
        if rotation.get("refresh_token"):
            response_data["refresh_token"] = rotation["refresh_token"]
    response = create_success_response(response_data, "Reauthentication succeeded")
    # Rotation revokes the prior cookie; attach the replacement so the browser
    # does not keep sending a dead session id on the next admin call.
    if rotation.get("cookie"):
        try:
            from routes.auth import _attach_session_cookie

            resp_obj = response[0] if isinstance(response, tuple) else response
            _attach_session_cookie(resp_obj, dict(rotation["cookie"]))
        except Exception:
            pass
    return response


def _require_operator_not_impersonating():
    actor_id = get_current_user_id()
    if not actor_id:
        return None, create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    if is_impersonating() or not is_platform_admin(actor_id) or not operator_account_usable(int(actor_id)):
        return None, create_error_response("Forbidden", 403, "FORBIDDEN")
    return int(actor_id), None


@admin_platform_bp.route("/security/mfa/status", methods=["GET"])
@handle_api_errors
@jwt_required
def admin_mfa_status():
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()
    actor_id, err = _require_operator_not_impersonating()
    if err:
        return err
    return create_success_response(get_mfa_status(actor_id), "MFA status")


@admin_platform_bp.route("/security/mfa/totp/enroll", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
def admin_mfa_totp_enroll():
    """Start TOTP enrollment (requires recent password step-up). Does not activate MFA."""
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()
    actor_id, err = _require_operator_not_impersonating()
    if err:
        return err
    state = get_admin_step_up_state(actor_id)
    if not state:
        return create_error_response("Step-up authentication required", 403, "STEP_UP_REQUIRED")
    # Replacing an enrolled device requires MFA-completed step-up.
    if operator_mfa_enrolled(actor_id) and mfa_required_for_operators() and not state.get("mfa_completed"):
        return create_error_response("Step-up authentication required", 403, "MFA_REQUIRED")
    allowed, _ = check_admin_rate_limit(
        bucket="admin_mfa_enroll",
        actor_key=f"{actor_id}:{request.remote_addr or 'unknown'}",
        limit=5,
        window_seconds=600,
    )
    if not allowed:
        return create_error_response("Too many attempts", 429, "RATE_LIMITED")
    try:
        result = start_totp_enrollment(actor_id)
    except AdminSecurityStoreUnavailable:
        return create_error_response("Service temporarily unavailable", 503, "STORE_UNAVAILABLE")
    except Exception:
        record_admin_audit_from_request(
            actor_user_id=actor_id,
            action="admin.mfa.enrollment_failed",
            outcome="denied",
            metadata={"reason": "ENROLL_START_FAILED"},
        )
        return create_error_response("Enrollment failed", 500, "ENROLL_FAILED")
    record_admin_audit_from_request(
        actor_user_id=actor_id,
        action="admin.mfa.enrollment_started",
        outcome="success",
        metadata={"expires_in": result.get("expires_in")},
    )
    return create_success_response(result, "MFA enrollment started")


@admin_platform_bp.route("/security/mfa/totp/confirm", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
def admin_mfa_totp_confirm():
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()
    actor_id, err = _require_operator_not_impersonating()
    if err:
        return err
    state = get_admin_step_up_state(actor_id)
    if not state:
        return create_error_response("Step-up authentication required", 403, "STEP_UP_REQUIRED")
    allowed, _ = check_admin_rate_limit(
        bucket="admin_mfa_confirm",
        actor_key=f"{actor_id}:{request.remote_addr or 'unknown'}",
        limit=10,
        window_seconds=600,
    )
    if not allowed:
        return create_error_response("Too many attempts", 429, "RATE_LIMITED")
    payload = request.get_json(silent=True) or {}
    code = payload.get("totp_code") or payload.get("mfa_code") or ""
    ok, mfa_err, result = confirm_totp_enrollment(actor_id, code)
    if not ok:
        record_admin_audit_from_request(
            actor_user_id=actor_id,
            action="admin.mfa.enrollment_failed",
            outcome="denied",
            metadata={"reason": mfa_err},
        )
        return create_error_response("Enrollment confirmation failed", 403, "ENROLL_CONFIRM_FAILED")
    # Enrollment TOTP proof upgrades password-bootstrap step-up so privileged
    # actions don't require an immediate second reauth dance.
    from core.admin_security import mark_admin_step_up_mfa_completed

    mark_admin_step_up_mfa_completed(actor_id, method="mfa")
    already = bool(result and result.get("already_completed"))
    action = (
        "admin.mfa.enrollment_already_completed"
        if already
        else (
            "admin.mfa.device_replaced"
            if result and result.get("replaced_device")
            else "admin.mfa.enrollment_confirmed"
        )
    )
    record_admin_audit_from_request(
        actor_user_id=actor_id,
        action=action,
        outcome="success",
        metadata={"activated": True, "already_completed": already},
    )
    if not already:
        record_admin_audit_from_request(
            actor_user_id=actor_id,
            action="admin.mfa.recovery_codes_generated",
            outcome="success",
            metadata={"count": len((result or {}).get("recovery_codes") or [])},
        )
    return create_success_response(result, "MFA activated")

@admin_platform_bp.route("/security/mfa/recovery-codes/regenerate", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_admin_step_up("destructive")
def admin_mfa_regenerate_recovery():
    from core.admin_security import admin_lockdown_active, lockdown_response

    if admin_lockdown_active():
        return lockdown_response()
    actor_id, err = _require_operator_not_impersonating()
    if err:
        return err
    ok, mfa_err, codes = regenerate_recovery_codes(actor_id)
    if not ok:
        return create_error_response("Unable to regenerate codes", 403, mfa_err or "FAILED")
    record_admin_audit_from_request(
        actor_user_id=actor_id,
        action="admin.mfa.recovery_codes_regenerated",
        outcome="success",
        metadata={"count": len(codes or [])},
    )
    return create_success_response({"recovery_codes": codes}, "Recovery codes regenerated")


@admin_platform_bp.route("/security/mfa/disable", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_admin_step_up("destructive")
def admin_mfa_disable():
    from core.admin_security import admin_lockdown_active, lockdown_response
    from core.admin_security import invalidate_admin_step_up_for_user

    if admin_lockdown_active():
        return lockdown_response()
    actor_id, err = _require_operator_not_impersonating()
    if err:
        return err
    if mfa_required_for_operators():
        return create_error_response(
            "MFA cannot be disabled while ADMIN_MFA_REQUIRED is enabled",
            403,
            "MFA_REQUIRED_POLICY",
        )
    payload = request.get_json(silent=True) or {}
    password = payload.get("password") or ""
    mfa_code = payload.get("mfa_code") or payload.get("totp_code")
    recovery_code = payload.get("recovery_code")
    if not verify_operator_password(actor_id, password):
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")
    ok, mfa_err, _method = verify_operator_mfa_code(
        actor_id, totp_code=mfa_code, recovery_code=recovery_code
    )
    # Allow disable with password+TOTP only when verifier on; if not enrolled skip
    if operator_mfa_enrolled(actor_id) and mfa_verifier_enabled() and not ok:
        return create_error_response("Authentication failed", 403, "REAUTH_FAILED")
    disable_operator_mfa(actor_id)
    invalidate_admin_step_up_for_user(actor_id, reason="mfa_disabled")
    record_admin_audit_from_request(
        actor_user_id=actor_id,
        action="admin.mfa.disabled",
        outcome="success",
        metadata={},
    )
    return create_success_response({"disabled": True}, "MFA disabled")


@admin_platform_bp.route("/step-up", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
def create_step_up():
    """Legacy alias: password step-up for a named action (uses same server-side state)."""
    return admin_reauthenticate()


@admin_platform_bp.route("/tenants", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.tenants.read")
def list_tenants():
    actor_id = get_actor_user_id() or get_current_user_id()
    allowed, retry_after = check_admin_rate_limit(
        bucket="tenant_search",
        actor_key=str(actor_id or "anon"),
        limit=60,
        window_seconds=60,
    )
    if not allowed:
        return create_error_response("Too many search requests", 429, "RATE_LIMITED")

    try:
        limit = int(request.args.get("limit", 25))
    except ValueError:
        limit = 25
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    search = (request.args.get("search") or "").strip()

    clauses = ["1=1"]
    params: list[Any] = []
    if search:
        like = f"%{search.lower()}%"
        clauses.append(
            "(LOWER(email) LIKE ? OR LOWER(name) LIKE ? OR LOWER(COALESCE(business_name, '')) LIKE ?)"
        )
        params.extend([like, like, like])

    where_sql = " AND ".join(clauses)
    rows = db_optimizer.execute_query(
        f"""
        SELECT id, email, name, role, business_name, industry, is_active, email_verified,
               onboarding_completed, onboarding_step, created_at, last_login
        FROM users
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, offset]),
    )
    count_rows = db_optimizer.execute_query(
        f"SELECT COUNT(*) AS total FROM users WHERE {where_sql}",
        tuple(params),
    )
    total = int(_row_value(count_rows[0], "total", 0) or 0) if count_rows else 0

    tenants = []
    for row in rows or []:
        user_row = dict(row) if hasattr(row, "keys") else {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "role": row[3],
            "business_name": row[4],
            "industry": row[5],
            "is_active": row[6],
            "email_verified": row[7],
            "onboarding_completed": row[8],
            "onboarding_step": row[9],
            "created_at": row[10],
            "last_login": row[11],
        }
        tenants.append(_serialize_tenant(user_row))

    return create_success_response(
        {"items": tenants, "total": total, "limit": limit, "offset": offset},
        "Tenants retrieved",
    )


@admin_platform_bp.route("/tenants/<int:tenant_id>", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.tenants.read")
def get_tenant(tenant_id: int):
    from core.admin_tenant_dossier import build_tenant_dossier

    user_row = _fetch_user_row(tenant_id)
    if not user_row:
        return create_error_response("Tenant not found", 404, "TENANT_NOT_FOUND")

    infrastructure = _integration_summary(tenant_id)
    dossier = build_tenant_dossier(user_row, infrastructure=infrastructure)
    # Backward-compatible keys + expanded read-only support dossier sections.
    return create_success_response(
        {
            "tenant": _serialize_tenant(user_row),
            "infrastructure": infrastructure,
            "account": dossier["account"],
            "access": dossier["access"],
            "integrations": dossier["integrations"],
            "product_health": dossier["product_health"],
            "commercial": dossier["commercial"],
            "support_activity": dossier["support_activity"],
            "support_checklist": dossier.get("support_checklist") or [],
            "impersonation_eligibility": dossier.get("impersonation_eligibility")
            or {
                "eligible": bool((dossier.get("account") or {}).get("is_active")),
                "reason_code": "AVAILABLE"
                if (dossier.get("account") or {}).get("is_active")
                else "USER_INACTIVE",
                "reason_label": "Available after operator step-up and MFA"
                if (dossier.get("account") or {}).get("is_active")
                else "Account inactive",
            },
            # Optional CS analytics (absent-safe for older clients)
            "analytics_state": dossier.get("analytics_state"),
            "customer_health": dossier.get("customer_health"),
            "usage_adoption": dossier.get("usage_adoption"),
            "friction_experience": dossier.get("friction_experience"),
            "customer_outcomes": dossier.get("customer_outcomes"),
        },
        "Tenant retrieved",
    )


@admin_platform_bp.route("/tenants/<int:tenant_id>/sync-jobs", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.ops.read")
def list_tenant_sync_jobs(tenant_id: int):
    """List recent Gmail sync jobs for a tenant (read-only ops diagnostic)."""
    from core.admin_sync_ops import list_tenant_sync_jobs as _list_jobs

    user_row = _fetch_user_row(tenant_id)
    if not user_row:
        return create_error_response("Tenant not found", 404, "TENANT_NOT_FOUND")
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    items = _list_jobs(tenant_id, limit=limit)
    return create_success_response(
        {"items": items, "tenant_id": tenant_id, "limit": max(1, min(limit, 50))},
        "Sync jobs retrieved",
    )


@admin_platform_bp.route("/tenants/<int:tenant_id>/analytics-ops", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.tenants.read")
def get_tenant_analytics_ops(tenant_id: int):
    """Read-only analytics operational check + optional reconciliation report.

    Manual GET only. No mutations, no backfill. lookback_days=7|30.
    """
    from core.product_analytics_ops import build_analytics_ops_report, normalize_lookback_days

    user_row = _fetch_user_row(tenant_id)
    if not user_row:
        return create_error_response("Tenant not found", 404, "TENANT_NOT_FOUND")

    lookback = normalize_lookback_days(request.args.get("lookback_days", 7))
    include_recon = str(request.args.get("reconcile", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    report = build_analytics_ops_report(
        tenant_id,
        lookback_days=lookback,
        include_reconciliation=include_recon,
    )
    return create_success_response(report, "Analytics ops report")


@admin_platform_bp.route(
    "/tenants/<int:tenant_id>/sync-jobs/<string:job_id>/retry",
    methods=["POST"],
)
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_platform_capability("platform.ops.retry_sync")
@require_admin_step_up("sync.retry")
def retry_tenant_sync_job(tenant_id: int, job_id: str):
    """
    Low-risk first ops mutation: retry a failed Gmail sync for one tenant/job.

    Does NOT require ADMIN_DESTRUCTIVE_ENABLED. Still requires step-up (+ MFA when enforced).
    """
    from core.admin_sync_ops import retry_failed_gmail_sync

    actor_id = get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    allowed, _ = check_admin_rate_limit(
        bucket="admin_sync_retry",
        actor_key=f"{actor_id}:{request.remote_addr or 'unknown'}",
        limit=10,
        window_seconds=300,
    )
    if not allowed:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.sync.retry",
            target_type="gmail_sync_job",
            target_id=str(job_id),
            outcome="denied",
            capability="platform.ops.retry_sync",
            metadata={"reason": "RATE_LIMITED", "tenant_id": tenant_id},
        )
        return create_error_response("Too many attempts", 429, "RATE_LIMITED")

    user_row = _fetch_user_row(tenant_id)
    if not user_row:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.sync.retry",
            target_type="gmail_sync_job",
            target_id=str(job_id),
            outcome="denied",
            capability="platform.ops.retry_sync",
            metadata={"reason": "TENANT_NOT_FOUND", "tenant_id": tenant_id},
        )
        return create_error_response("Tenant not found", 404, "TENANT_NOT_FOUND")

    payload = request.get_json(silent=True) or {}
    # Body tenant_id must match path when provided (prevents confused-deputy swaps).
    if "tenant_id" in payload and int(payload.get("tenant_id") or -1) != int(tenant_id):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.sync.retry",
            target_type="gmail_sync_job",
            target_id=str(job_id),
            outcome="denied",
            capability="platform.ops.retry_sync",
            metadata={"reason": "TENANT_MISMATCH"},
        )
        return create_error_response("Invalid request", 400, "TENANT_MISMATCH")

    idem = (
        request.headers.get("Idempotency-Key")
        or request.headers.get("X-Idempotency-Key")
        or payload.get("idempotency_key")
        or ""
    )
    result, err = retry_failed_gmail_sync(
        actor_id=int(actor_id),
        tenant_id=int(tenant_id),
        job_id=str(job_id),
        idempotency_key=str(idem),
        confirm=str(payload.get("confirm") or ""),
    )
    step_state = get_admin_step_up_state(int(actor_id))
    step_method = (step_state or {}).get("method")
    idem_hash = None
    try:
        from core.admin_sync_ops import _idem_key_hash

        idem_hash = _idem_key_hash(str(idem)) if idem else None
    except Exception:
        idem_hash = None

    if err:
        status = {
            "CONFIRMATION_REQUIRED": 400,
            "IDEMPOTENCY_REQUIRED": 400,
            "INVALID_JOB_ID": 400,
            "TENANT_MISMATCH": 400,
            "JOB_NOT_FOUND": 404,
            "JOB_NOT_RETRYABLE": 409,
            "SYNC_ALREADY_ACTIVE": 409,
            "ALREADY_CLAIMED": 409,
            "RETRY_RACE_LOST": 409,
            "RETRY_IN_PROGRESS": 409,
            "IDEMPOTENCY_CONFLICT": 409,
            "STEP_UP_REQUIRED": 403,
            "STEP_UP_EXPIRED": 403,
            "STORE_UNAVAILABLE": 503,
            "QUEUE_UNAVAILABLE": 503,
            "QUEUE_FAILED": 503,
            "RETRY_FAILED": 500,
        }.get(err, 400)
        # Map internal codes to controlled audit reason vocabulary.
        audit_reason = {
            "RETRY_RACE_LOST": "ALREADY_CLAIMED",
            "RETRY_IN_PROGRESS": "IDEMPOTENCY_CONFLICT",
            "QUEUE_FAILED": "QUEUE_UNAVAILABLE",
            "RETRY_FAILED": "QUEUE_UNAVAILABLE",
            "SYNC_ALREADY_ACTIVE": "JOB_NOT_RETRYABLE",
            # STORE_UNAVAILABLE is preserved as-is (distinct from QUEUE_UNAVAILABLE).
        }.get(err, err)
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.sync.retry",
            target_type="gmail_sync_job",
            target_id=str(job_id),
            outcome="denied",
            capability="platform.ops.retry_sync",
            metadata={
                "reason": audit_reason,
                "tenant_id": tenant_id,
                "idempotency_key_hash": idem_hash,
                "step_up_method": step_method,
                "correlation_id": get_request_correlation_id(),
            },
        )
        return create_error_response("Sync retry failed", status, err)

    record_admin_audit_from_request(
        actor_user_id=int(actor_id),
        action="platform.sync.retry",
        target_type="gmail_sync_job",
        target_id=str(job_id),
        outcome="success",
        capability="platform.ops.retry_sync",
        before={"status": result.get("previous_status"), "job_id": job_id},
        after={
            "status": result.get("resulting_status"),
            "original_job_id": result.get("original_job_id"),
            "new_job_id": result.get("new_job_id"),
            "tenant_id": tenant_id,
            "enqueue_mode": result.get("enqueue_mode"),
            "replayed": bool(result.get("replayed")),
        },
        metadata={
            "correlation_id": result.get("correlation_id") or get_request_correlation_id(),
            "idempotency_key_hash": result.get("idempotency_key_hash") or idem_hash,
            "step_up_method": step_method,
            "tenant_id": tenant_id,
        },
    )
    return create_success_response(result, "Sync job retry queued")


@admin_platform_bp.route("/impersonate", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_platform_capability("platform.tenants.impersonate")
@require_no_nested_impersonation
@require_impersonation_enabled
@require_admin_step_up("impersonate")
def start_impersonation():
    actor_id = get_actor_user_id() or get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    allowed, retry_after = check_admin_rate_limit(
        bucket="impersonate",
        actor_key=str(actor_id),
        limit=10,
        window_seconds=600,
    )
    if not allowed:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.start",
            outcome="denied",
            capability="platform.tenants.impersonate",
            metadata={"reason": "RATE_LIMITED", "retry_after": retry_after},
        )
        return create_error_response("Too many impersonation attempts", 429, "RATE_LIMITED")

    payload = request.get_json(silent=True) or {}
    # Ignore any client-supplied actor_user_id (AT-AUTHZ-05 / AT-API-10).
    payload.pop("actor_user_id", None)

    target_user_id = payload.get("target_user_id")
    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.start",
            outcome="denied",
            capability="platform.tenants.impersonate",
            metadata={"reason": "VALIDATION_ERROR"},
        )
        return create_error_response("target_user_id is required", 400, "VALIDATION_ERROR")

    if target_user_id == actor_id:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.start",
            target_type="user",
            target_id=str(target_user_id),
            outcome="denied",
            capability="platform.tenants.impersonate",
            metadata={"reason": "IMPERSONATION_SELF_FORBIDDEN"},
        )
        return create_error_response(
            "Cannot impersonate yourself",
            400,
            "IMPERSONATION_SELF_FORBIDDEN",
        )

    target_row = _fetch_user_row(target_user_id)
    if not target_row:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.start",
            target_type="user",
            target_id=str(target_user_id),
            outcome="denied",
            capability="platform.tenants.impersonate",
            metadata={"reason": "TENANT_NOT_FOUND"},
        )
        return create_error_response("Target user not found", 404, "TENANT_NOT_FOUND")

    if not bool(target_row.get("is_active")):
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.start",
            target_type="user",
            target_id=str(target_user_id),
            outcome="denied",
            capability="platform.tenants.impersonate",
            metadata={"reason": "USER_INACTIVE"},
        )
        return create_error_response("Target user is inactive", 400, "USER_INACTIVE")

    token_bundle = get_jwt_manager().generate_impersonation_access_token(
        actor_user_id=actor_id,
        target_user_id=target_user_id,
        target_user_data={
            "email": target_row.get("email"),
            "role": target_row.get("role", "user"),
        },
    )

    record_admin_audit_from_request(
        actor_user_id=actor_id,
        action="platform.impersonate.start",
        target_type="user",
        target_id=str(target_user_id),
        after={
            "target_email": target_row.get("email"),
            "expires_in": token_bundle.get("expires_in"),
            "correlation_id": get_request_correlation_id(),
        },
        outcome="success",
        capability="platform.tenants.impersonate",
    )

    # Never return a refresh token for impersonation sessions.
    return create_success_response(
        {
            "tokens": {
                "access_token": token_bundle.get("access_token"),
                "expires_in": token_bundle.get("expires_in"),
                "token_type": token_bundle.get("token_type", "Bearer"),
                "impersonating": True,
                "actor_user_id": actor_id,
                "target_user_id": target_user_id,
            },
            "target_user": _serialize_tenant(target_row),
        },
        "Impersonation started",
    )


@admin_platform_bp.route("/impersonate/stop", methods=["POST"])
@handle_api_errors
@jwt_required
def stop_impersonation():
    """
    Narrow escape hatch: terminate only the caller's current impersonation session.
    Accepts no target user/tenant/redirect. Works without step-up / when start is disabled.
    """
    # Ignore any client-supplied identity fields entirely.
    payload = request.get_json(silent=True) or {}
    for forbidden in ("target_user_id", "user_id", "tenant_id", "actor_user_id", "redirect", "redirect_url"):
        if forbidden in payload:
            record_admin_audit_from_request(
                actor_user_id=get_actor_user_id() or get_current_user_id() or 0,
                action="platform.impersonate.stop",
                outcome="denied",
                metadata={"reason": "FORBIDDEN_FIELDS"},
            )
            return create_error_response("Invalid request", 400, "INVALID_REQUEST")

    origin_fail = validate_browser_origin_for_cookie_auth()
    if origin_fail:
        return origin_fail

    if not is_impersonating():
        # Idempotent: already stopped.
        return create_success_response(
            {"stopped": True, "already_stopped": True},
            "Not impersonating",
        )

    actor_id = get_actor_user_id()
    effective_user_id = get_current_user_id()
    if not actor_id:
        record_admin_audit_from_request(
            actor_user_id=0,
            action="platform.impersonate.stop",
            outcome="denied",
            metadata={"reason": "MISSING_ACTOR"},
        )
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    # Blacklist current impersonation jti
    try:
        jti = getattr(g, "access_token_jti", None)
        if jti:
            get_jwt_manager().blacklist_token(jti)
    except Exception as exc:
        logger.warning("Failed to blacklist impersonation token on stop: %s", exc)

    actor_usable = operator_account_usable(int(actor_id)) and is_platform_admin(int(actor_id))
    response_data: Dict[str, Any] = {
        "stopped": True,
        "actor_user_id": int(actor_id),
    }

    if not actor_usable:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="platform.impersonate.stop",
            target_type="user",
            target_id=str(effective_user_id) if effective_user_id else None,
            outcome="success",
            capability="platform.tenants.impersonate",
            metadata={"reason": "ACTOR_UNAUTHORIZED", "admin_access_revoked": True},
        )
        response_data["admin_access_revoked"] = True
        response_data["require_relogin"] = True
        return create_success_response(response_data, "Impersonation stopped")

    # Restore rotated actor token (no elevated step-up granted).
    try:
        from core.database_optimization import db_optimizer

        rows = db_optimizer.execute_query(
            "SELECT email, name, role FROM users WHERE id = ? LIMIT 1",
            (actor_id,),
        )
        user_data = {"email": None, "name": None, "role": "user"}
        if rows:
            row = rows[0]
            user_data = {
                "email": row.get("email") if hasattr(row, "keys") else row[0],
                "name": row.get("name") if hasattr(row, "keys") else row[1],
                "role": row.get("role") if hasattr(row, "keys") else row[2],
            }
        tokens = get_jwt_manager().generate_tokens(int(actor_id), user_data)
        response_data["tokens"] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
            "token_type": "Bearer",
        }
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action="admin.session.rotated",
            outcome="success",
            metadata={"reason": "impersonation_stop"},
        )
    except Exception as exc:
        logger.warning("Actor token restore on impersonation stop failed: %s", exc)
        response_data["require_relogin"] = True

    record_admin_audit_from_request(
        actor_user_id=int(actor_id),
        action="platform.impersonate.stop",
        target_type="user",
        target_id=str(effective_user_id) if effective_user_id else None,
        outcome="success",
        capability="platform.tenants.impersonate",
    )

    return create_success_response(response_data, "Impersonation stopped")


@admin_platform_bp.route("/audit", methods=["GET"])
@handle_api_errors
@jwt_required
@require_platform_capability("platform.audit.read")
def get_audit_log():
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    actor_user_id = request.args.get("actor_user_id")
    parsed_actor = None
    if actor_user_id not in (None, ""):
        try:
            parsed_actor = int(actor_user_id)
        except (TypeError, ValueError):
            # Malformed actor filter: ignore rather than erroring with SQL details.
            parsed_actor = None

    outcome_raw = (request.args.get("outcome") or "").strip().lower()
    outcome = outcome_raw if outcome_raw in ("success", "denied", "error") else None

    target_type = (request.args.get("target_type") or "").strip() or None
    if target_type and len(target_type) > 64:
        target_type = None

    target_id = (request.args.get("target_id") or "").strip() or None
    if target_id and len(target_id) > 128:
        target_id = None

    result = list_admin_audit(
        limit=limit,
        offset=offset,
        actor_user_id=parsed_actor,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
    )
    return create_success_response(result, "Admin audit log retrieved")


@admin_platform_bp.route("/audit/export", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_platform_capability("platform.audit.export")
@require_admin_step_up("export")
def export_audit_log():
    """Bounded allowlisted export of the current filtered audit page (no raw metadata)."""
    from core.admin_audit_export import EXPORT_MAX_ROWS, build_audit_export_payload

    actor_id = get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    payload = request.get_json(silent=True) or {}
    fmt = str(payload.get("format") or "json").strip().lower()
    try:
        limit = int(payload.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, EXPORT_MAX_ROWS))
    try:
        offset = int(payload.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)

    parsed_actor = None
    if payload.get("actor_user_id") not in (None, ""):
        try:
            parsed_actor = int(payload.get("actor_user_id"))
        except (TypeError, ValueError):
            parsed_actor = None

    outcome_raw = str(payload.get("outcome") or "").strip().lower()
    outcome = outcome_raw if outcome_raw in ("success", "denied", "error") else None
    target_type = str(payload.get("target_type") or "").strip() or None
    if target_type and len(target_type) > 64:
        target_type = None
    target_id = str(payload.get("target_id") or "").strip() or None
    if target_id and len(target_id) > 128:
        target_id = None

    result = list_admin_audit(
        limit=limit,
        offset=offset,
        actor_user_id=parsed_actor,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
    )
    export = build_audit_export_payload(result.get("items") or [], fmt=fmt)

    record_admin_audit_from_request(
        actor_user_id=int(actor_id),
        action="platform.audit.export",
        target_type="audit_export",
        target_id=export["format"],
        outcome="success",
        capability="platform.audit.export",
        metadata={
            "reason": "EXPORT_OK",
            "code": "EXPORT_OK",
            "row_count": export["count"],
            "limit": limit,
            "offset": offset,
            "outcome_filter": outcome or "",
        },
        after={"count": export["count"], "format": export["format"]},
    )

    return create_success_response(
        {
            "format": export["format"],
            "count": export["count"],
            "limit": limit,
            "offset": offset,
            "total_matching": result.get("total"),
            "content_type": export["content_type"],
            "body": export["body"],
            "items": export.get("items"),
        },
        "Audit export ready",
    )


@admin_platform_bp.route("/tenants/<int:tenant_id>/suspend", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_platform_capability("platform.ops.write")
@require_admin_step_up("account.suspend")
def suspend_tenant(tenant_id: int):
    """Pause a tenant account (is_active=false). Gated by ADMIN_DESTRUCTIVE_ENABLED."""
    return _set_tenant_lifecycle(tenant_id, active=False, confirm_word="suspend")


@admin_platform_bp.route("/tenants/<int:tenant_id>/resume", methods=["POST"])
@handle_api_errors
@jwt_required
@require_admin_csrf_if_cookie_auth
@require_platform_capability("platform.ops.write")
@require_admin_step_up("account.suspend")
def resume_tenant(tenant_id: int):
    """Resume a paused tenant account (is_active=true). Gated by ADMIN_DESTRUCTIVE_ENABLED."""
    return _set_tenant_lifecycle(tenant_id, active=True, confirm_word="resume")


def _set_tenant_lifecycle(tenant_id: int, *, active: bool, confirm_word: str):
    from core.admin_tenant_lifecycle import set_tenant_active

    actor_id = get_current_user_id()
    if not actor_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    action = "platform.tenant.resume" if active else "platform.tenant.suspend"
    payload = request.get_json(silent=True) or {}
    confirm = str(payload.get("confirm") or "").strip().lower()
    if confirm != confirm_word:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action=action,
            target_type="tenant",
            target_id=str(tenant_id),
            outcome="denied",
            capability="platform.ops.write",
            metadata={"reason": "CONFIRM_REQUIRED"},
        )
        return create_error_response(
            f'Confirmation required: set confirm="{confirm_word}"',
            400,
            "CONFIRM_REQUIRED",
        )

    ok, reason, summary = set_tenant_active(tenant_id, active=active)
    if not ok and reason == "TENANT_NOT_FOUND":
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action=action,
            target_type="tenant",
            target_id=str(tenant_id),
            outcome="denied",
            capability="platform.ops.write",
            metadata={"reason": reason},
        )
        return create_error_response("Tenant not found", 404, "TENANT_NOT_FOUND")
    if not ok:
        record_admin_audit_from_request(
            actor_user_id=int(actor_id),
            action=action,
            target_type="tenant",
            target_id=str(tenant_id),
            outcome="error",
            capability="platform.ops.write",
            metadata={"reason": reason},
            before=(summary or {}).get("before"),
            after=(summary or {}).get("after"),
        )
        return create_error_response("Lifecycle update failed", 500, reason)

    record_admin_audit_from_request(
        actor_user_id=int(actor_id),
        action=action,
        target_type="tenant",
        target_id=str(tenant_id),
        outcome="success",
        capability="platform.ops.write",
        metadata={"reason": reason, "code": reason},
        before=(summary or {}).get("before"),
        after=(summary or {}).get("after"),
    )
    return create_success_response(
        {
            "tenant_id": tenant_id,
            "is_active": active,
            "unchanged": bool((summary or {}).get("unchanged")),
            "reason": reason,
        },
        "Tenant resumed" if active else "Tenant suspended",
    )
