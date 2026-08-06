"""Platform-level admin authorization for Fikiri operators (not tenant org admins)."""

from __future__ import annotations

import os
from functools import wraps
from typing import FrozenSet, Iterable, Optional, Set

from flask import jsonify

from core.secure_sessions import get_actor_user_id, get_current_user_id

PLATFORM_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        "platform.tenants.read",
        "platform.tenants.impersonate",
        "platform.audit.read",
        "platform.audit.export",
        "platform.ops.read",
        "platform.ops.retry_sync",
        "platform.ops.write",
        "platform.emergency",
    }
)

# platform.ops.write remains gated by ADMIN_DESTRUCTIVE_ENABLED.
# platform.ops.retry_sync is the first low-risk ops mutation (failed sync retry only).


def _admin_user_ids() -> Set[str]:
    raw = os.getenv("ADMIN_USER_IDS") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def is_platform_admin(user_id) -> bool:
    """True when user id is in ADMIN_USER_IDS (Fikiri staff / platform operators)."""
    if user_id is None:
        return False
    admin_ids = _admin_user_ids()
    if not admin_ids:
        return False
    return str(user_id) in admin_ids


def get_platform_capabilities(user_id) -> Set[str]:
    if is_platform_admin(user_id):
        return set(PLATFORM_CAPABILITIES)
    return set()


def has_platform_capability(user_id, capability: str) -> bool:
    return capability in get_platform_capabilities(user_id)


def require_platform_capability(capability: str):
    """Decorator: require platform operator with a specific capability (deny-by-default).

    Impersonation sessions cannot use operator capabilities even if actor_user_id
    would otherwise qualify — operator APIs require a non-impersonating session.
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from core.admin_security import admin_lockdown_active, lockdown_response
            from core.secure_sessions import is_impersonating

            if admin_lockdown_active():
                return lockdown_response()

            if is_impersonating():
                try:
                    from core.admin_audit import record_admin_audit_from_request

                    actor_id = get_actor_user_id() or get_current_user_id()
                    if actor_id:
                        record_admin_audit_from_request(
                            actor_user_id=int(actor_id),
                            action="platform.capability.denied",
                            target_type="capability",
                            target_id=capability,
                            outcome="denied",
                            capability=capability,
                            metadata={
                                "reason": "IMPERSONATION_ACTIVE",
                                "path": getattr(f, "__name__", "unknown"),
                            },
                        )
                except Exception:
                    pass
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

            # Capability is evaluated for the authenticated operator session only
            # (not the effective tenant user under impersonation).
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
            if not has_platform_capability(actor_id, capability):
                try:
                    from core.admin_audit import record_admin_audit_from_request

                    record_admin_audit_from_request(
                        actor_user_id=int(actor_id),
                        action="platform.capability.denied",
                        target_type="capability",
                        target_id=capability,
                        outcome="denied",
                        capability=capability,
                        metadata={"path": getattr(f, "__name__", "unknown")},
                    )
                except Exception:
                    pass
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
            if capability == "platform.ops.write":
                from core.admin_security import destructive_admin_enabled

                if not destructive_admin_enabled():
                    try:
                        from core.admin_audit import record_admin_audit_from_request

                        record_admin_audit_from_request(
                            actor_user_id=int(actor_id),
                            action="platform.destructive.blocked",
                            target_type="capability",
                            target_id=capability,
                            outcome="denied",
                            capability=capability,
                        )
                    except Exception:
                        pass
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

    return decorator


def summarize_capabilities(capabilities: Iterable[str]) -> list[str]:
    return sorted({str(item).strip() for item in capabilities if str(item).strip()})
