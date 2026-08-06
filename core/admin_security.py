"""Platform admin security controls (Phase 1.5 + 1.6).

Session-bound step-up, MFA, CSRF, rate limits, and privileged session windows.
Privileged state uses the shared admin security store (Redis in production).

Destructive admin capabilities remain gated by ADMIN_DESTRUCTIVE_ENABLED.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from functools import wraps
from typing import Any, Dict, FrozenSet, Optional, Tuple

from flask import g, jsonify, request

from core.secure_sessions import get_actor_user_id, get_current_user_id, is_impersonating

logger = logging.getLogger(__name__)

SENSITIVE_ADMIN_ACTIONS: FrozenSet[str] = frozenset(
    {
        "impersonate",
        "sync.retry",
        "billing.change",
        "account.suspend",
        "oauth.disconnect",
        "role.change",
        "export",
        "destructive",
    }
)

STEP_UP_HEADER = "X-Admin-Step-Up"
CSRF_HEADER = "X-CSRFToken"
STEP_UP_DEFAULT_TTL_SECONDS = 600  # 10 minutes (safe band 5–15)
IMPERSONATION_MAX_TTL_SECONDS = 3600
ADMIN_IDLE_DEFAULT = 1800
ADMIN_ABSOLUTE_DEFAULT = 28800

# Rate-limit audit dedupe (local throttle only; counters live in shared store).
_RATE_LIMIT_AUDIT_AT: Dict[str, float] = {}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_test_mode() -> bool:
    env = (os.getenv("FLASK_ENV") or "").strip().lower()
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or env == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def admin_lockdown_active() -> bool:
    return _env_flag("ADMIN_LOCKDOWN", default=False)


def impersonation_enabled() -> bool:
    return _env_flag("IMPERSONATION_ENABLED", default=False)


def impersonation_disabled() -> bool:
    return not impersonation_enabled()


def destructive_admin_enabled() -> bool:
    return _env_flag("ADMIN_DESTRUCTIVE_ENABLED", default=False)


def mfa_required_for_operators() -> bool:
    """Canonical MFA gate. Default false (transitional); set ADMIN_MFA_REQUIRED=true to enforce."""
    return _env_flag("ADMIN_MFA_REQUIRED", default=False)


def step_up_required() -> bool:
    if is_test_mode() and _env_flag("ADMIN_STEP_UP_BYPASS_FOR_TESTS", default=False):
        return False
    return not _env_flag("ADMIN_STEP_UP_DISABLED", default=False)


def step_up_ttl_seconds() -> int:
    raw = int(os.getenv("ADMIN_STEP_UP_TTL_SECONDS", str(STEP_UP_DEFAULT_TTL_SECONDS)))
    return max(300, min(raw, 900))  # 5–15 minutes


def admin_idle_timeout_seconds() -> int:
    return max(60, int(os.getenv("ADMIN_IDLE_TIMEOUT_SECONDS", str(ADMIN_IDLE_DEFAULT))))


def admin_absolute_session_seconds() -> int:
    return max(300, int(os.getenv("ADMIN_ABSOLUTE_SESSION_SECONDS", str(ADMIN_ABSOLUTE_DEFAULT))))


def get_request_correlation_id() -> str:
    existing = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    if existing and existing.strip():
        return existing.strip()[:128]
    return secrets.token_hex(8)


def get_admin_session_binding() -> Optional[str]:
    """Stable binding for the current authenticated session (cookie id or JWT jti).

    When the SPA sends ``Authorization: Bearer``, prefer the JWT ``jti`` even if a
    session cookie is also present. Cookie-first binding orphaned step-up after
    rotation: reauth rebound to ``jti:new`` (or left state on ``cookie:new`` the
    browser never received) while the next request still keyed off the other side.
    """
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.startswith("Bearer "):
        jti = getattr(g, "access_token_jti", None)
        if not jti:
            cu = getattr(request, "current_user", None)
            if isinstance(cu, dict):
                jti = cu.get("jti")
        if jti:
            return f"jti:{jti}"
        if len(auth) > 20:
            digest = hashlib.sha256(auth.encode("utf-8")).hexdigest()[:32]
            return f"bearer:{digest}"
    session_id = getattr(g, "session_id", None)
    if session_id:
        return f"cookie:{session_id}"
    jti = getattr(g, "access_token_jti", None)
    if jti:
        return f"jti:{jti}"
    return None


def _state_key(user_id: int, binding: str) -> str:
    return f"{int(user_id)}:{binding}"


def _audit(action: str, **kwargs) -> None:
    try:
        from core.admin_audit import record_admin_audit_from_request

        record_admin_audit_from_request(action=action, **kwargs)
    except Exception as exc:
        logger.warning("Admin security audit failed action=%s: %s", action, exc)


def mfa_verifier_enabled() -> bool:
    return _env_flag("ADMIN_MFA_VERIFIER_ENABLED", default=False)


def privileged_store_required() -> bool:
    """Privileged admin actions require a working shared store."""
    return True


def _store():
    from core.admin_security_store import get_admin_security_store

    return get_admin_security_store()


def _store_or_fail() -> Any:
    from core.admin_security_store import AdminSecurityStoreUnavailable

    store = _store()
    if not store.available:
        _audit(
            "admin.security_store.unavailable",
            actor_user_id=get_current_user_id() or 0,
            outcome="denied",
            metadata={"reason": "STORE_UNAVAILABLE"},
        )
        raise AdminSecurityStoreUnavailable("admin security store unavailable")
    return store


# --- MFA canonical helpers -------------------------------------------------


def operator_mfa_enrolled(actor_user_id: int) -> bool:
    """Canonical: operator has MFA enrollment completed (not merely a preference flag)."""
    try:
        from core.admin_mfa import operator_mfa_enrolled as _enrolled

        return _enrolled(int(actor_user_id))
    except Exception:
        return False


def step_up_completed_with_mfa(actor_user_id: int) -> bool:
    """Canonical: current valid step-up was completed with MFA (or recovery)."""
    state = get_admin_step_up_state(int(actor_user_id))
    if not state:
        return False
    return bool(state.get("mfa_completed")) and state.get("method") in ("mfa", "recovery")


def step_up_assurance_level(actor_user_id: Optional[int] = None, state: Optional[Dict[str, Any]] = None) -> str:
    """
    Compact assurance label for the current (or provided) step-up state.

    NONE | PASSWORD_BOOTSTRAP | MFA_VERIFIED
    """
    if state is None:
        if actor_user_id is None:
            return "NONE"
        state = get_admin_step_up_state(int(actor_user_id))
    if not state:
        return "NONE"
    if bool(state.get("mfa_completed")) and state.get("method") in ("mfa", "recovery"):
        return "MFA_VERIFIED"
    if state.get("method") == "password" and not state.get("mfa_completed"):
        return "PASSWORD_BOOTSTRAP"
    if state.get("mfa_completed"):
        return "MFA_VERIFIED"
    return "PASSWORD_BOOTSTRAP"

def verify_operator_mfa(actor_user_id: int, code: Optional[str], recovery_code: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    MFA verification for step-up.

    When ADMIN_MFA_REQUIRED is off, password-only step-up is allowed.
    When on, requires verifier + enrolled MFA + valid TOTP/recovery.
    """
    if not mfa_required_for_operators():
        return True, None
    if not mfa_verifier_enabled():
        return False, "MFA_VERIFIER_UNAVAILABLE"
    if not operator_mfa_enrolled(actor_user_id):
        return False, "MFA_ENROLLMENT_REQUIRED"
    try:
        from core.admin_mfa import verify_operator_mfa_code

        ok, err, _method = verify_operator_mfa_code(
            int(actor_user_id),
            totp_code=code,
            recovery_code=recovery_code,
        )
        return ok, err
    except Exception as exc:
        from core.admin_security_store import AdminSecurityStoreUnavailable

        if isinstance(exc, AdminSecurityStoreUnavailable):
            return False, "STORE_UNAVAILABLE"
        logger.warning("MFA verify failed: %s", exc)
        return False, "MFA_INVALID"


# --- Step-up state (shared store) ------------------------------------------


def get_admin_step_up_state(user_id: int) -> Optional[Dict[str, Any]]:
    binding = get_admin_session_binding()
    if not binding:
        return None
    try:
        store = _store_or_fail()
    except Exception:
        return None

    # Global user revocation epoch
    revoked = store.get_json(store.k("revoked", int(user_id)))
    key = store.k("stepup", int(user_id), binding)
    state = store.get_json(key)
    if not state:
        return None
    now = time.time()
    if revoked and float(state.get("iat", 0)) <= float(revoked.get("at", 0)):
        store.delete(key)
        return None
    if float(state.get("exp", 0)) <= now:
        _expire_step_up_key(store, key, user_id, reason="expired")
        return None
    idle_limit = admin_idle_timeout_seconds()
    if now - float(state.get("last_activity", state.get("iat", now))) > idle_limit:
        _expire_step_up_key(store, key, user_id, reason="idle_timeout")
        return None
    absolute = admin_absolute_session_seconds()
    if now - float(state.get("iat", now)) > absolute:
        _expire_step_up_key(store, key, user_id, reason="absolute_timeout")
        return None

    # Cross-session enroll: password bootstrap must die the moment MFA is active.
    if (
        mfa_required_for_operators()
        and not state.get("mfa_completed")
        and operator_mfa_enrolled(int(user_id))
    ):
        _expire_step_up_key(store, key, user_id, reason="stale_bootstrap_after_enroll")
        return None

    return state

def _expire_step_up_key(store, key: str, user_id: int, reason: str) -> None:
    store.delete(key)
    _audit(
        "admin.step_up.expired",
        actor_user_id=int(user_id),
        outcome="denied",
        metadata={"reason": reason},
    )


def establish_admin_step_up(
    *,
    actor_user_id: int,
    method: str = "password",
    mfa_completed: bool = False,
    ttl_seconds: Optional[int] = None,
    binding: Optional[str] = None,
) -> Dict[str, Any]:
    """Create short-lived server-side step-up state bound to the current session."""
    binding = binding or get_admin_session_binding()
    if not binding:
        raise ValueError("missing_session_binding")

    if mfa_required_for_operators() and not mfa_completed:
        # First-time enrollment bootstrap: password step-up is allowed only while
        # the operator has no MFA device. Privileged mutations still require
        # mfa_completed via require_admin_step_up / step_up_completed_with_mfa.
        if operator_mfa_enrolled(int(actor_user_id)):
            raise PermissionError("MFA_REQUIRED")

    # Never downgrade an existing MFA-verified step-up on this binding.
    try:
        store_probe = _store_or_fail()
        existing = store_probe.get_json(
            store_probe.k("stepup", int(actor_user_id), binding)
        )
        if (
            existing
            and existing.get("mfa_completed")
            and existing.get("method") in ("mfa", "recovery")
            and not mfa_completed
        ):
            raise PermissionError("STEP_UP_DOWNGRADE_FORBIDDEN")
    except PermissionError:
        raise
    except Exception:
        pass

    store = _store_or_fail()
    ttl = int(ttl_seconds if ttl_seconds is not None else step_up_ttl_seconds())
    ttl = max(300, min(ttl, 900))
    now = time.time()
    state = {
        "user_id": int(actor_user_id),
        "binding": binding,
        "method": method,
        "mfa_completed": bool(mfa_completed),
        "iat": now,
        "exp": now + ttl,
        "last_activity": now,
    }
    step_key = store.k("stepup", int(actor_user_id), binding)
    store.set_json(step_key, state, ttl)
    idx_key = store.k("stepup_idx", int(actor_user_id))
    store.sadd(idx_key, step_key)
    # Index TTL slightly longer than step-up
    try:
        store.set_json(store.k("stepup_idx_meta", int(actor_user_id)), {"updated": now}, ttl + 60)
    except Exception:
        pass

    receipt = secrets.token_urlsafe(24)
    receipt_hash = hashlib.sha256(receipt.encode("utf-8")).hexdigest()
    store.set_json(store.k("receipt", receipt_hash), {"state_key": step_key, "user_id": int(actor_user_id)}, ttl)

    return {
        "step_up_confirmed": True,
        "expires_in": ttl,
        "method": method,
        "mfa_completed": bool(mfa_completed),
        "authenticated_at": int(now),
        "step_up_token": receipt,
        "binding": binding,
    }


def touch_admin_activity(user_id: int) -> None:
    binding = get_admin_session_binding()
    if not binding:
        return
    try:
        store = _store_or_fail()
    except Exception:
        return
    key = store.k("stepup", int(user_id), binding)
    state = store.get_json(key)
    if not state:
        return
    state["last_activity"] = time.time()
    ttl = max(1, int(float(state.get("exp", time.time())) - time.time()))
    store.set_json(key, state, ttl)


def mark_admin_step_up_mfa_completed(user_id: int, *, method: str = "mfa") -> bool:
    """Upgrade current step-up after TOTP enrollment confirm (password bootstrap → MFA)."""
    binding = get_admin_session_binding()
    if not binding:
        return False
    try:
        store = _store_or_fail()
    except Exception:
        return False
    key = store.k("stepup", int(user_id), binding)
    state = store.get_json(key)
    if not state:
        return False
    state["mfa_completed"] = True
    state["method"] = method if method in ("mfa", "recovery") else "mfa"
    state["last_activity"] = time.time()
    ttl = max(1, int(float(state.get("exp", time.time())) - time.time()))
    store.set_json(key, state, ttl)
    return True


def invalidate_admin_step_up_for_user(user_id: int, *, reason: str = "revoked") -> None:
    try:
        store = _store_or_fail()
    except Exception:
        return
    idx_key = store.k("stepup_idx", int(user_id))
    for step_key in store.smembers(idx_key):
        store.delete(step_key)
        store.srem(idx_key, step_key)
    store.delete(idx_key)
    # Revocation epoch so stale copies cannot be reused
    store.set_json(store.k("revoked", int(user_id)), {"at": time.time(), "reason": reason}, ttl=admin_absolute_session_seconds())
    store.delete(store.k("mfa", "enroll", int(user_id)))
    _audit(
        "admin.session.revoked",
        actor_user_id=int(user_id),
        outcome="success",
        metadata={"reason": reason},
    )


def invalidate_admin_step_up_for_binding(user_id: int, binding: str, *, reason: str = "logout") -> None:
    try:
        store = _store_or_fail()
    except Exception:
        return
    step_key = store.k("stepup", int(user_id), binding)
    store.delete(step_key)
    store.srem(store.k("stepup_idx", int(user_id)), step_key)
    store.delete(store.k("csrf", int(user_id), binding))
    _audit(
        "admin.session.revoked",
        actor_user_id=int(user_id),
        outcome="success",
        metadata={"reason": reason},
    )


def clear_step_up_tokens_for_tests() -> None:
    from core.admin_security_store import clear_admin_security_store_for_tests

    clear_admin_security_store_for_tests()


def issue_step_up_token(
    *,
    actor_user_id: int,
    action: str,
    method: str = "password",
    ttl_seconds: Optional[int] = None,
    binding: Optional[str] = None,
) -> Dict[str, Any]:
    """Compat helper for tests: establish session-bound step-up and return receipt."""
    if action not in SENSITIVE_ADMIN_ACTIONS:
        raise ValueError(f"Unknown sensitive action: {action}")
    mfa_completed = method in ("mfa", "recovery")
    bundle = establish_admin_step_up(
        actor_user_id=actor_user_id,
        method=method,
        mfa_completed=mfa_completed,
        ttl_seconds=ttl_seconds,
        binding=binding or f"test:{actor_user_id}",
    )
    bundle["action"] = action
    return bundle


def verify_step_up_token(
    *,
    actor_user_id: int,
    action: str,
    token: Optional[str],
    consume: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Validate session-bound step-up; optional receipt header is secondary."""
    if not step_up_required():
        return True, None
    try:
        state = get_admin_step_up_state(int(actor_user_id))
    except Exception:
        return False, "STORE_UNAVAILABLE"
    if state:
        if mfa_required_for_operators() and not state.get("mfa_completed"):
            if not operator_mfa_enrolled(int(actor_user_id)):
                return False, "MFA_ENROLLMENT_REQUIRED"
            return False, "MFA_REQUIRED"
        return True, None
    if not token:
        return False, "STEP_UP_REQUIRED"
    try:
        store = _store_or_fail()
    except Exception:
        return False, "STORE_UNAVAILABLE"
    receipt_hash = hashlib.sha256(str(token).strip().encode("utf-8")).hexdigest()
    receipt = store.get_json(store.k("receipt", receipt_hash))
    if not receipt:
        return False, "STEP_UP_INVALID"
    if int(receipt.get("user_id", -1)) != int(actor_user_id):
        return False, "STEP_UP_ACTOR_MISMATCH"
    state = store.get_json(receipt.get("state_key") or "")
    if not state:
        return False, "STEP_UP_INVALID"
    if float(state.get("exp", 0)) <= time.time():
        return False, "STEP_UP_EXPIRED"
    if mfa_required_for_operators() and not state.get("mfa_completed"):
        if not operator_mfa_enrolled(int(actor_user_id)):
            return False, "MFA_ENROLLMENT_REQUIRED"
        return False, "MFA_REQUIRED"
    return True, None


# --- Password verification -------------------------------------------------


def verify_operator_password(actor_user_id: int, password: str) -> bool:
    """Re-authenticate operator via existing password verifier (no manual hash compare)."""
    if not password:
        return False
    try:
        from core.database_optimization import db_optimizer
        from core.user_auth import user_auth_manager
        import json

        active = db_optimizer.sql_cast_int_eq_one("is_active")
        rows = db_optimizer.execute_query(
            f"""
            SELECT password_hash, metadata, is_active
            FROM users WHERE id = ? AND {active}
            LIMIT 1
            """,
            (actor_user_id,),
        )
        if not rows:
            return False
        row = rows[0]
        password_hash = row.get("password_hash") if hasattr(row, "keys") else row[0]
        metadata_raw = row.get("metadata") if hasattr(row, "keys") else row[1]
        metadata = json.loads(metadata_raw or "{}") if metadata_raw else {}
        salt = metadata.get("salt", "")
        if not password_hash:
            return False
        if user_auth_manager._verify_password(password, password_hash, salt):
            return True
        return bool(user_auth_manager._verify_legacy_password(password, password_hash))
    except Exception as exc:
        logger.warning("Operator password step-up verify failed: %s", exc)
        return False


def operator_account_usable(actor_user_id: int) -> bool:
    try:
        from core.database_optimization import db_optimizer

        active = db_optimizer.sql_cast_int_eq_one("is_active")
        rows = db_optimizer.execute_query(
            f"SELECT id FROM users WHERE id = ? AND {active} LIMIT 1",
            (actor_user_id,),
        )
        return bool(rows)
    except Exception:
        return False


# --- CSRF (cookie-authenticated mutations) ---------------------------------


def admin_request_uses_cookie_auth() -> bool:
    auth = (request.headers.get("Authorization") or "").strip()
    has_bearer = auth.startswith("Bearer ") and len(auth.split(" ", 1)[-1].strip()) > 10
    has_cookie = bool(getattr(g, "session_id", None))
    return bool(has_cookie and not has_bearer)


def issue_admin_csrf_token(user_id: int) -> str:
    binding = get_admin_session_binding()
    if not binding:
        raise ValueError("missing_session_binding")
    store = _store_or_fail()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    store.set_json(
        store.k("csrf", int(user_id), binding),
        {"hash": token_hash},
        ttl=admin_absolute_session_seconds(),
    )
    return token


def verify_admin_csrf_token(user_id: int, token: Optional[str]) -> bool:
    binding = get_admin_session_binding()
    if not binding or not token:
        return False
    try:
        store = _store_or_fail()
    except Exception:
        return False
    expected = store.get_json(store.k("csrf", int(user_id), binding))
    if not expected or not expected.get("hash"):
        return False
    got = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    return secrets.compare_digest(got, expected["hash"])


def validate_browser_origin_for_cookie_auth() -> Optional[Tuple[Any, int]]:
    """Reject cross-origin cookie-authenticated mutations when Origin/Referer present."""
    if not admin_request_uses_cookie_auth():
        return None
    origin = (request.headers.get("Origin") or "").strip()
    referer = (request.headers.get("Referer") or "").strip()
    allowed = (os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_URL") or "").split(",")
    allowed = [o.strip().rstrip("/") for o in allowed if o.strip()]
    if not allowed:
        return None
    candidate = origin
    if not candidate and referer:
        # Scheme + host only
        try:
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                candidate = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            candidate = ""
    if candidate and candidate.rstrip("/") not in allowed:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "CSRF validation failed",
                    "error_code": "CSRF_ORIGIN_FAILED",
                }
            ),
            403,
        )
    return None


def require_admin_csrf_if_cookie_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return f(*args, **kwargs)
        if not admin_request_uses_cookie_auth():
            return f(*args, **kwargs)
        origin_fail = validate_browser_origin_for_cookie_auth()
        if origin_fail:
            return origin_fail
        actor_id = get_current_user_id()
        token = request.headers.get(CSRF_HEADER) or request.headers.get("X-CSRF-Token")
        if not actor_id or not verify_admin_csrf_token(int(actor_id), token):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "CSRF validation failed",
                        "error_code": "CSRF_FAILED",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return wrapped


# --- Rate limits -----------------------------------------------------------


def check_admin_rate_limit(
    *,
    bucket: str,
    actor_key: str,
    limit: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    try:
        store = _store_or_fail()
    except Exception:
        # Fail closed for privileged rate accounting when store is down.
        return False, 60
    key = store.k("ratelimit", bucket, actor_key)
    try:
        count = store.incr(key, window_seconds)
    except Exception:
        return False, 60
    if count > limit:
        retry_after = window_seconds
        now = time.time()
        audit_key = f"{bucket}:{actor_key}"
        last = _RATE_LIMIT_AUDIT_AT.get(audit_key, 0)
        if now - last > 60:
            _RATE_LIMIT_AUDIT_AT[audit_key] = now
            try:
                uid = int(str(actor_key).split(":")[0]) if str(actor_key)[:1].isdigit() else 0
            except Exception:
                uid = 0
            if uid:
                _audit(
                    "admin.rate_limit.triggered",
                    actor_user_id=uid,
                    outcome="denied",
                    metadata={"bucket": bucket, "retry_after": retry_after},
                )
        return False, retry_after
    return True, 0


def clear_admin_rate_limits_for_tests() -> None:
    _RATE_LIMIT_AUDIT_AT.clear()
    from core.admin_security_store import clear_admin_security_store_for_tests

    clear_admin_security_store_for_tests()


# --- Decorators ------------------------------------------------------------


def lockdown_response():
    return (
        jsonify(
            {
                "success": False,
                "error": "Admin portal is under emergency lockdown",
                "error_code": "ADMIN_LOCKDOWN",
            }
        ),
        503,
    )


def impersonation_disabled_response():
    return (
        jsonify(
            {
                "success": False,
                "error": "Impersonation is not available",
                "error_code": "IMPERSONATION_DISABLED",
            }
        ),
        403,
    )


def require_admin_not_locked_down(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if admin_lockdown_active():
            return lockdown_response()
        return f(*args, **kwargs)

    return wrapped


def require_impersonation_enabled(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if impersonation_disabled():
            actor_id = get_actor_user_id() or get_current_user_id()
            if actor_id:
                _audit(
                    "platform.impersonate.start",
                    actor_user_id=int(actor_id),
                    outcome="denied",
                    capability="platform.tenants.impersonate",
                    metadata={"reason": "IMPERSONATION_DISABLED"},
                )
            return impersonation_disabled_response()
        return f(*args, **kwargs)

    return wrapped


def require_no_nested_impersonation(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if is_impersonating():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Nested impersonation is not allowed",
                        "error_code": "NESTED_IMPERSONATION_FORBIDDEN",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return wrapped


def require_admin_step_up(action: Optional[str] = None):
    """Reusable guard: require valid server-side step-up for privileged admin actions."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if is_impersonating():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Forbidden",
                            "error_code": "FORBIDDEN_WHILE_IMPERSONATING",
                        }
                    ),
                    403,
                )
            actor_id = get_current_user_id()
            if not actor_id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Authentication required",
                            "error_code": "AUTHENTICATION_REQUIRED",
                        }
                    ),
                    401,
                )

            # Re-check account + operator status immediately before mutation.
            from core.platform_admin import is_platform_admin

            if not is_platform_admin(actor_id) or not operator_account_usable(int(actor_id)):
                _audit(
                    "admin.step_up.denied",
                    actor_user_id=int(actor_id),
                    outcome="denied",
                    metadata={"reason": "OPERATOR_UNUSABLE", "action": action},
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Forbidden",
                            "error_code": "FORBIDDEN",
                        }
                    ),
                    403,
                )

            if not step_up_required():
                return f(*args, **kwargs)
            try:
                _store_or_fail()
            except Exception:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Service temporarily unavailable",
                            "error_code": "STORE_UNAVAILABLE",
                        }
                    ),
                    503,
                )

            header_token = request.headers.get(STEP_UP_HEADER)
            ok, err = verify_step_up_token(
                actor_user_id=int(actor_id),
                action=action or "destructive",
                token=header_token,
                consume=False,
            )
            if not ok:
                if err == "STORE_UNAVAILABLE":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Service temporarily unavailable",
                                "error_code": "STORE_UNAVAILABLE",
                            }
                        ),
                        503,
                    )
                if err in ("MFA_REQUIRED", "MFA_ENROLLMENT_REQUIRED"):
                    _audit(
                        "admin.mfa.required",
                        actor_user_id=int(actor_id),
                        outcome="denied",
                        metadata={"reason": err, "action": action},
                    )
                else:
                    _audit(
                        "admin.step_up.denied",
                        actor_user_id=int(actor_id),
                        outcome="denied",
                        metadata={"reason": err or "STEP_UP_REQUIRED", "action": action},
                    )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Step-up authentication required",
                            "error_code": err or "STEP_UP_REQUIRED",
                        }
                    ),
                    403,
                )

            if mfa_required_for_operators() and not step_up_completed_with_mfa(int(actor_id)):
                mfa_err = (
                    "MFA_ENROLLMENT_REQUIRED"
                    if not operator_mfa_enrolled(int(actor_id))
                    else "MFA_REQUIRED"
                )
                _audit(
                    "admin.mfa.required",
                    actor_user_id=int(actor_id),
                    outcome="denied",
                    metadata={"reason": mfa_err, "action": action},
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Step-up authentication required",
                            "error_code": mfa_err,
                        }
                    ),
                    403,
                )

            touch_admin_activity(int(actor_id))
            return f(*args, **kwargs)

        return wrapped

    return decorator


# Alias used by older call sites.
def require_step_up(action: str):
    if action not in SENSITIVE_ADMIN_ACTIONS:
        raise ValueError(f"Unknown sensitive action for decorator: {action}")
    return require_admin_step_up(action)


def require_destructive_enabled(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not destructive_admin_enabled():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Destructive admin controls are disabled until security gate completes",
                        "error_code": "DESTRUCTIVE_DISABLED",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return wrapped


def impersonation_ttl_seconds() -> int:
    raw = int(os.getenv("IMPERSONATION_TOKEN_EXPIRY_SECONDS", "1800"))
    return max(300, min(raw, IMPERSONATION_MAX_TTL_SECONDS))


def rotate_session_after_step_up(actor_user_id: int) -> Dict[str, Any]:
    """Rotate cookie session id and/or bearer jti after successful step-up."""
    result: Dict[str, Any] = {"rotated": False, "new_bindings": []}
    old_binding = get_admin_session_binding()

    session_id = getattr(g, "session_id", None)
    if session_id:
        try:
            from core.secure_sessions import secure_session_manager
            from core.database_optimization import db_optimizer

            rows = db_optimizer.execute_query(
                "SELECT email, name, role FROM users WHERE id = ? LIMIT 1",
                (actor_user_id,),
            )
            user_data: Dict[str, Any] = {}
            if rows:
                row = rows[0]
                user_data = {
                    "email": row.get("email") if hasattr(row, "keys") else row[0],
                    "name": row.get("name") if hasattr(row, "keys") else row[1],
                    "role": row.get("role") if hasattr(row, "keys") else row[2],
                }
            secure_session_manager.revoke_session(session_id)
            new_sid, cookie_data = secure_session_manager.create_session(actor_user_id, user_data)
            g.session_id = new_sid
            result["rotated"] = True
            result["cookie"] = dict(cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookie_binding = f"cookie:{new_sid}"
            result["new_bindings"].append(cookie_binding)
            result["new_binding"] = cookie_binding
        except Exception as exc:
            logger.warning("Cookie session rotation after step-up failed: %s", exc)

    auth = (request.headers.get("Authorization") or "").strip()
    old_jti = getattr(g, "access_token_jti", None)
    if auth.startswith("Bearer ") and not old_jti:
        # Cookie-first before_request used to skip JWT parse; recover jti from the header.
        try:
            import jwt as pyjwt
            from core.jwt_auth import get_jwt_manager

            token = auth.split(" ", 1)[1].strip()
            mgr = get_jwt_manager()
            payload = mgr.verify_access_token(token)
            if isinstance(payload, dict) and "error" not in payload:
                old_jti = payload.get("jti")
            elif token:
                old_jti = pyjwt.decode(
                    token,
                    mgr.secret_key,
                    algorithms=[mgr.algorithm],
                    options={"verify_exp": False},
                ).get("jti")
            if old_jti:
                g.access_token_jti = old_jti
        except Exception as exc:
            logger.warning("Could not recover bearer jti for step-up rotation: %s", exc)

    if auth.startswith("Bearer ") and old_jti:
        try:
            import jwt as pyjwt
            from core.jwt_auth import get_jwt_manager
            from core.database_optimization import db_optimizer

            mgr = get_jwt_manager()
            mgr.blacklist_token(old_jti)
            rows = db_optimizer.execute_query(
                "SELECT email, name, role FROM users WHERE id = ? LIMIT 1",
                (actor_user_id,),
            )
            user_data = {"email": None, "name": None, "role": "user"}
            if rows:
                row = rows[0]
                user_data = {
                    "email": row.get("email") if hasattr(row, "keys") else row[0],
                    "name": row.get("name") if hasattr(row, "keys") else row[1],
                    "role": row.get("role") if hasattr(row, "keys") else row[2],
                }
            tokens = mgr.generate_tokens(actor_user_id, user_data)
            new_access = tokens.get("access_token")
            new_payload = pyjwt.decode(
                new_access,
                mgr.secret_key,
                algorithms=[mgr.algorithm],
                options={"verify_exp": False},
            )
            new_jti = new_payload.get("jti")
            result["rotated"] = True
            result["access_token"] = new_access
            result["refresh_token"] = tokens.get("refresh_token")
            result["expires_in"] = tokens.get("expires_in")
            if new_jti:
                g.access_token_jti = new_jti
                jti_binding = f"jti:{new_jti}"
                result["new_bindings"].append(jti_binding)
                # Bearer is the SPA auth path — prefer it as canonical new_binding.
                result["new_binding"] = jti_binding
        except Exception as exc:
            logger.warning("Bearer rotation after step-up failed: %s", exc)

    new_bindings = list(dict.fromkeys(result.get("new_bindings") or []))
    if result.get("new_binding") and result["new_binding"] not in new_bindings:
        new_bindings.append(result["new_binding"])
    result["new_bindings"] = new_bindings

    if result.get("rotated") and old_binding and new_bindings:
        preserved: Optional[Dict[str, Any]] = None
        try:
            store = _store_or_fail()
            old_key = store.k("stepup", int(actor_user_id), old_binding)
            state = store.get_json(old_key)
            preserved = dict(state) if state else None
            if state:
                ttl = max(1, int(float(state.get("exp", time.time())) - time.time()))
                store.delete(old_key)
                store.srem(store.k("stepup_idx", int(actor_user_id)), old_key)
                # Write to every post-rotation binding so cookie-only and bearer-only
                # follow-up requests both see step-up (SPA often has both headers).
                for binding in new_bindings:
                    bound = dict(state)
                    bound["binding"] = binding
                    new_key = store.k("stepup", int(actor_user_id), binding)
                    store.set_json(new_key, bound, ttl)
                    store.sadd(store.k("stepup_idx", int(actor_user_id)), new_key)
            _audit(
                "admin.session.rotated",
                actor_user_id=int(actor_user_id),
                outcome="success",
                metadata={"reason": "step_up", "bindings": new_bindings},
            )
        except Exception as exc:
            logger.warning("Step-up rebind after rotation failed: %s", exc)

        # Fail closed: never leave privileged step-up only on a binding the client cannot use.
        try:
            store = _store_or_fail()
            primary = result.get("new_binding") or (new_bindings[0] if new_bindings else None)
            primary_key = store.k("stepup", int(actor_user_id), primary) if primary else None
            if primary_key and not store.get_json(primary_key) and preserved:
                ttl = max(300, int(float(preserved.get("exp", time.time())) - time.time()))
                for binding in new_bindings:
                    establish_admin_step_up(
                        actor_user_id=int(actor_user_id),
                        method=str(preserved.get("method") or "password"),
                        mfa_completed=bool(preserved.get("mfa_completed")),
                        ttl_seconds=ttl,
                        binding=binding,
                    )
            if primary_key and not store.get_json(primary_key):
                if old_binding:
                    old_key = store.k("stepup", int(actor_user_id), old_binding)
                    store.delete(old_key)
                    store.srem(store.k("stepup_idx", int(actor_user_id)), old_key)
                result["step_up_orphaned"] = True
                logger.error(
                    "Step-up orphaned after rotation for user %s — privileged state cleared",
                    actor_user_id,
                )
        except Exception as exc:
            logger.warning("Step-up recovery after rotation failed: %s", exc)
            try:
                invalidate_admin_step_up_for_user(int(actor_user_id), reason="rotation_partial_failure")
                result["step_up_orphaned"] = True
            except Exception:
                pass

    return result



def validate_admin_security_config() -> None:
    """Startup validation for unsafe configuration combinations."""
    from core.admin_security_store import (
        configured_store_backend,
        get_admin_security_store,
        is_production,
    )

    errors = []
    if mfa_required_for_operators() and not mfa_verifier_enabled():
        if is_production():
            errors.append(
                "ADMIN_MFA_REQUIRED=true requires ADMIN_MFA_VERIFIER_ENABLED=true in production"
            )
        else:
            logger.warning(
                "ADMIN_MFA_REQUIRED without verifier — privileged step-up will fail closed"
            )

    if destructive_admin_enabled():
        if not mfa_required_for_operators():
            errors.append("ADMIN_DESTRUCTIVE_ENABLED requires ADMIN_MFA_REQUIRED=true")
        if not mfa_verifier_enabled():
            errors.append("ADMIN_DESTRUCTIVE_ENABLED requires ADMIN_MFA_VERIFIER_ENABLED=true")
        store = get_admin_security_store()
        if not store.available:
            errors.append("ADMIN_DESTRUCTIVE_ENABLED requires shared admin security store")
        if configured_store_backend() != "redis" and is_production():
            errors.append(
                "ADMIN_DESTRUCTIVE_ENABLED in production requires ADMIN_SECURITY_STORE=redis"
            )

    if is_production() and configured_store_backend() == "memory":
        if not _env_flag("ADMIN_SECURITY_ALLOW_MEMORY_IN_PRODUCTION", False):
            errors.append("ADMIN_SECURITY_STORE=memory is not allowed in production")

    if errors:
        msg = "; ".join(errors)
        logger.error("Admin security configuration invalid: %s", msg)
        raise RuntimeError(f"Admin security configuration invalid: {msg}")
