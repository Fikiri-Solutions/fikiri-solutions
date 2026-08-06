"""Platform operator MFA: TOTP enrollment, verification, recovery codes (Phase 1.6)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RECOVERY_CODE_COUNT = 10
TOTP_VALID_WINDOW = 1  # ±1 step (~30s skew)
METADATA_KEY = "admin_mfa"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def mfa_verifier_enabled() -> bool:
    return _env_flag("ADMIN_MFA_VERIFIER_ENABLED", default=False)


def mfa_challenge_ttl_seconds() -> int:
    return max(60, min(int(os.getenv("ADMIN_MFA_CHALLENGE_TTL_SECONDS", "300")), 600))


def totp_enrollment_ttl_seconds() -> int:
    return max(60, min(int(os.getenv("ADMIN_TOTP_ENROLLMENT_TTL_SECONDS", "600")), 1800))


def _fernet():
    from cryptography.fernet import Fernet

    key = (os.getenv("FERNET_KEY") or os.getenv("ENCRYPTION_KEY") or "").strip()
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    from core.database_optimization import db_optimizer

    if getattr(db_optimizer, "cipher", None):
        return db_optimizer.cipher
    raise RuntimeError("encryption_unavailable")


def _encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def _load_user_metadata(user_id: int) -> Dict[str, Any]:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        "SELECT metadata FROM users WHERE id = ? LIMIT 1",
        (user_id,),
    )
    if not rows:
        return {}
    raw = rows[0].get("metadata") if hasattr(rows[0], "keys") else rows[0][0]
    try:
        return json.loads(raw or "{}") if raw else {}
    except Exception:
        return {}


def _save_user_metadata(user_id: int, metadata: Dict[str, Any]) -> None:
    from core.database_optimization import db_optimizer

    db_optimizer.execute_query(
        "UPDATE users SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(metadata), user_id),
        fetch=False,
    )


def get_operator_mfa_record(user_id: int) -> Dict[str, Any]:
    meta = _load_user_metadata(user_id)
    mfa = meta.get(METADATA_KEY) or {}
    return mfa if isinstance(mfa, dict) else {}


def operator_mfa_enrolled(actor_user_id: int) -> bool:
    """Canonical: MFA active only after confirmed enrollment (verified_at + secret)."""
    mfa = get_operator_mfa_record(int(actor_user_id))
    return bool(mfa.get("verified_at")) and bool(mfa.get("secret_enc")) and bool(
        mfa.get("totp_enabled") or mfa.get("enrolled")
    )


def get_mfa_status(user_id: int) -> Dict[str, Any]:
    mfa = get_operator_mfa_record(user_id)
    codes = mfa.get("recovery_codes") or []
    unused = sum(1 for c in codes if isinstance(c, dict) and not c.get("used_at"))
    return {
        "enrolled": operator_mfa_enrolled(user_id),
        "totp_enabled": bool(mfa.get("totp_enabled")),
        "verified_at": mfa.get("verified_at"),
        "recovery_codes_remaining": unused if operator_mfa_enrolled(user_id) else 0,
        "verifier_enabled": mfa_verifier_enabled(),
    }


def _issuer_name() -> str:
    return (os.getenv("ADMIN_MFA_ISSUER") or "Fikiri Admin").strip() or "Fikiri Admin"


def _operator_label(user_id: int) -> str:
    from core.database_optimization import db_optimizer

    rows = db_optimizer.execute_query(
        "SELECT email FROM users WHERE id = ? LIMIT 1",
        (user_id,),
    )
    if not rows:
        return f"operator-{user_id}"
    email = rows[0].get("email") if hasattr(rows[0], "keys") else rows[0][0]
    return str(email or f"operator-{user_id}")


def start_totp_enrollment(user_id: int) -> Dict[str, Any]:
    """Begin enrollment: generate secret, store pending (encrypted) with TTL. Not active yet."""
    import pyotp

    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    store.require_available()

    secret = pyotp.random_base32()
    secret_enc = _encrypt(secret)
    enroll_key = store.k("mfa", "enroll", int(user_id))
    # Replace any previous unconfirmed enrollment.
    store.delete(enroll_key)
    ttl = totp_enrollment_ttl_seconds()
    store.set_json(
        enroll_key,
        {"secret_enc": secret_enc, "created_at": time.time(), "user_id": int(user_id)},
        ttl,
    )

    totp = pyotp.TOTP(secret)
    label = _operator_label(user_id)
    provisioning_uri = totp.provisioning_uri(name=label, issuer_name=_issuer_name())
    return {
        "enrollment_started": True,
        "expires_in": ttl,
        "secret": secret,  # once during enrollment only
        "provisioning_uri": provisioning_uri,
    }


def cancel_totp_enrollment(user_id: int) -> None:
    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    store.require_available()
    store.delete(store.k("mfa", "enroll", int(user_id)))


def _hash_recovery_code(code: str, salt: str) -> str:
    normalized = "".join(str(code).upper().split())
    return hashlib.sha256(f"{salt}:{normalized}".encode("utf-8")).hexdigest()


def _generate_recovery_codes() -> Tuple[List[str], List[Dict[str, Any]]]:
    plaintext: List[str] = []
    stored: List[Dict[str, Any]] = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = secrets.token_hex(5)  # 10 hex chars
        code = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}".upper()
        salt = secrets.token_hex(16)
        plaintext.append(code)
        stored.append({"salt": salt, "hash": _hash_recovery_code(code, salt), "used_at": None})
    return plaintext, stored


def confirm_totp_enrollment(user_id: int, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Confirm pending enrollment with a valid TOTP; activate MFA and issue recovery codes once.

    Idempotent retry: if pending is gone and MFA is already enrolled, return
    already_completed without minting a second recovery-code set.
    """
    import pyotp

    from core.admin_security_store import get_admin_security_store

    if not code or not str(code).strip():
        return False, "MFA_INVALID", None

    store = get_admin_security_store()
    store.require_available()
    enroll_key = store.k("mfa", "enroll", int(user_id))
    pending = store.get_json(enroll_key)

    if not pending or not pending.get("secret_enc"):
        # Durable activation already happened; do not regenerate secrets/codes.
        if operator_mfa_enrolled(user_id):
            return (
                True,
                None,
                {
                    "activated": True,
                    "already_completed": True,
                    "replaced_device": False,
                    "recovery_codes": [],
                },
            )
        return False, "ENROLLMENT_EXPIRED", None

    try:
        secret = _decrypt(pending["secret_enc"])
    except Exception:
        return False, "ENROLLMENT_INVALID", None

    totp = pyotp.TOTP(secret)
    if not totp.verify(str(code).strip(), valid_window=TOTP_VALID_WINDOW):
        return False, "MFA_INVALID", None

    # Claim confirmation so concurrent workers cannot mint two recovery sets.
    claim_key = store.k("mfa", "enroll_confirm", int(user_id), pending.get("secret_enc", "")[:16])
    if not store.set_nx(claim_key, {"at": time.time()}, ttl=120):
        if operator_mfa_enrolled(user_id):
            return (
                True,
                None,
                {
                    "activated": True,
                    "already_completed": True,
                    "replaced_device": False,
                    "recovery_codes": [],
                },
            )
        return False, "ENROLL_IN_PROGRESS", None

    replacing = operator_mfa_enrolled(user_id)
    plaintext_codes, stored_codes = _generate_recovery_codes()
    generation = secrets.token_hex(8)
    meta = _load_user_metadata(user_id)
    meta[METADATA_KEY] = {
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totp_enabled": True,
        "enrolled": True,
        "secret_enc": pending["secret_enc"],
        "recovery_codes": stored_codes,
        "recovery_generation": generation,
        "last_totp_step": None,
    }
    try:
        _save_user_metadata(user_id, meta)
    except Exception:
        store.delete(claim_key)
        raise

    store.delete(enroll_key)

    return (
        True,
        None,
        {
            "activated": True,
            "replaced_device": replacing,
            "already_completed": False,
            "recovery_codes": plaintext_codes,
        },
    )

def regenerate_recovery_codes(user_id: int) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    if not operator_mfa_enrolled(user_id):
        return False, "MFA_NOT_ENROLLED", None
    plaintext, stored = _generate_recovery_codes()
    meta = _load_user_metadata(user_id)
    mfa = meta.get(METADATA_KEY) or {}
    # New generation invalidates prior code claims / ambiguous old plaintext.
    mfa["recovery_generation"] = secrets.token_hex(8)
    mfa["recovery_codes"] = stored
    meta[METADATA_KEY] = mfa
    _save_user_metadata(user_id, meta)
    return True, None, plaintext


def disable_operator_mfa(user_id: int) -> None:
    meta = _load_user_metadata(user_id)
    meta.pop(METADATA_KEY, None)
    _save_user_metadata(user_id, meta)
    try:
        cancel_totp_enrollment(user_id)
    except Exception:
        pass


def _mark_totp_step_used(user_id: int, step: int) -> bool:
    """Replay protection: reject reuse of the same TOTP time step."""
    from core.admin_security_store import get_admin_security_store

    store = get_admin_security_store()
    store.require_available()
    key = store.k("mfa", "totp_step", int(user_id), int(step))
    # TTL slightly over 2 windows
    return store.set_nx(key, {"used": True}, ttl=90)


def verify_totp_code(user_id: int, code: str) -> Tuple[bool, Optional[str]]:
    import pyotp

    if not operator_mfa_enrolled(user_id):
        return False, "MFA_ENROLLMENT_REQUIRED"
    if not code or not str(code).strip():
        return False, "MFA_REQUIRED"

    mfa = get_operator_mfa_record(user_id)
    try:
        secret = _decrypt(mfa["secret_enc"])
    except Exception:
        return False, "MFA_INVALID"

    totp = pyotp.TOTP(secret)
    stripped = str(code).strip().replace(" ", "")
    # Reject recovery-code shaped input here
    if "-" in stripped and len(stripped) > 8:
        return False, "MFA_INVALID"

    if not totp.verify(stripped, valid_window=TOTP_VALID_WINDOW):
        return False, "MFA_INVALID"

    step = int(time.time()) // 30
    if not _mark_totp_step_used(user_id, step):
        return False, "MFA_REPLAY"

    # Persist last step for diagnostics (non-secret)
    meta = _load_user_metadata(user_id)
    mfa_rec = meta.get(METADATA_KEY) or {}
    mfa_rec["last_totp_step"] = step
    meta[METADATA_KEY] = mfa_rec
    try:
        _save_user_metadata(user_id, meta)
    except Exception:
        pass
    return True, None


def consume_recovery_code(user_id: int, code: str) -> Tuple[bool, Optional[str]]:
    """Atomically consume a single recovery code (hash compare + shared-store claim)."""
    if not operator_mfa_enrolled(user_id):
        return False, "MFA_ENROLLMENT_REQUIRED"
    if not code or not str(code).strip():
        return False, "MFA_REQUIRED"

    from core.admin_security_store import get_admin_security_store

    meta = _load_user_metadata(user_id)
    mfa = meta.get(METADATA_KEY) or {}
    codes = list(mfa.get("recovery_codes") or [])
    generation = str(mfa.get("recovery_generation") or "0")
    normalized = "".join(str(code).upper().split())
    matched_idx = None
    matched_hash = None
    for idx, entry in enumerate(codes):
        if not isinstance(entry, dict) or entry.get("used_at"):
            continue
        salt = entry.get("salt") or ""
        digest = _hash_recovery_code(normalized, salt)
        if secrets.compare_digest(entry.get("hash") or "", digest):
            matched_idx = idx
            matched_hash = digest
            break
    if matched_idx is None or not matched_hash:
        return False, "MFA_INVALID"

    store = get_admin_security_store()
    store.require_available()
    claim_key = store.k("mfa", "recovery_claim", int(user_id), generation, matched_hash[:24])
    if not store.set_nx(claim_key, {"used": True}, ttl=86400 * 400):
        return False, "MFA_INVALID"

    # Re-read and update only if still unused (second line of defense).
    meta = _load_user_metadata(user_id)
    mfa = meta.get(METADATA_KEY) or {}
    if str(mfa.get("recovery_generation") or "0") != generation:
        return False, "MFA_INVALID"
    codes = list(mfa.get("recovery_codes") or [])
    if matched_idx >= len(codes):
        return False, "MFA_INVALID"
    entry = codes[matched_idx]
    if not isinstance(entry, dict) or entry.get("used_at"):
        return False, "MFA_INVALID"
    if not secrets.compare_digest(entry.get("hash") or "", matched_hash):
        return False, "MFA_INVALID"

    codes[matched_idx] = {
        **entry,
        "used_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    mfa["recovery_codes"] = codes
    meta[METADATA_KEY] = mfa
    _save_user_metadata(user_id, meta)
    return True, None

def verify_operator_mfa_code(
    user_id: int,
    *,
    totp_code: Optional[str] = None,
    recovery_code: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify MFA for step-up.
    Returns (ok, error_code, method) where method is 'mfa' or 'recovery'.
    """
    if not mfa_verifier_enabled():
        return False, "MFA_VERIFIER_UNAVAILABLE", None
    if not operator_mfa_enrolled(user_id):
        return False, "MFA_ENROLLMENT_REQUIRED", None

    if recovery_code:
        ok, err = consume_recovery_code(user_id, recovery_code)
        if ok:
            return True, None, "recovery"
        return False, err or "MFA_INVALID", None

    if totp_code:
        ok, err = verify_totp_code(user_id, totp_code)
        if ok:
            return True, None, "mfa"
        return False, err or "MFA_INVALID", None

    return False, "MFA_REQUIRED", None
