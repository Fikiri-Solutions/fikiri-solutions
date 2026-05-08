"""
Google Cross-Account Protection (RISC) — validate security event tokens and react safely.

Uses https://accounts.google.com/.well-known/risc-configuration for issuer/JWKS.
Signals are for security / session management only (Google RISC Terms).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import jwt
import requests

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

RISC_CONFIGURATION_URL = "https://accounts.google.com/.well-known/risc-configuration"

EVENT_SESSIONS_REVOKED = "https://schemas.openid.net/secevent/risc/event-type/sessions-revoked"
EVENT_OAUTH_TOKENS_REVOKED = "https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked"
EVENT_OAUTH_TOKEN_REVOKED = "https://schemas.openid.net/secevent/oauth/event-type/token-revoked"
EVENT_ACCOUNT_DISABLED = "https://schemas.openid.net/secevent/risc/event-type/account-disabled"
EVENT_ACCOUNT_ENABLED = "https://schemas.openid.net/secevent/risc/event-type/account-enabled"
EVENT_CREDENTIAL_CHANGE = (
    "https://schemas.openid.net/secevent/risc/event-type/account-credential-change-required"
)
EVENT_VERIFICATION = "https://schemas.openid.net/secevent/risc/event-type/verification"

_risc_config_cache: Dict[str, Any] = {"fetched_at": 0.0, "issuer": None, "jwks_uri": None}
_jwks_client = None
_jwks_client_uri: Optional[str] = None


def is_risc_enabled() -> bool:
    return os.getenv("GOOGLE_RISC_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _allowed_audiences() -> List[str]:
    raw = os.getenv("GOOGLE_RISC_AUDIENCE", "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    ids: List[str] = []
    for key in ("GOOGLE_CLIENT_ID", "GMAIL_OAUTH_CLIENT_ID"):
        v = os.getenv(key, "").strip()
        if v:
            ids.append(v)
    return ids


def _ensure_tables() -> None:
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS google_risc_jti (
            jti TEXT PRIMARY KEY,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        fetch=False,
    )


def _get_risc_config() -> Tuple[str, str]:
    now = time.time()
    if (
        now - float(_risc_config_cache["fetched_at"]) < 3600
        and _risc_config_cache.get("issuer")
        and _risc_config_cache.get("jwks_uri")
    ):
        return _risc_config_cache["issuer"], _risc_config_cache["jwks_uri"]

    resp = requests.get(RISC_CONFIGURATION_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    issuer = data.get("issuer")
    jwks_uri = data.get("jwks_uri")
    if not issuer or not jwks_uri:
        raise ValueError("RISC configuration missing issuer or jwks_uri")
    _risc_config_cache["issuer"] = issuer
    _risc_config_cache["jwks_uri"] = jwks_uri
    _risc_config_cache["fetched_at"] = now
    return issuer, jwks_uri


def _get_jwks_client(jwks_uri: str) -> jwt.PyJWKClient:
    global _jwks_client, _jwks_client_uri
    if _jwks_client_uri != jwks_uri:
        _jwks_client = jwt.PyJWKClient(jwks_uri, cache_keys=True)
        _jwks_client_uri = jwks_uri
    return _jwks_client


def validate_security_event_token(token: str) -> Dict[str, Any]:
    """Verify signature and claims; does not enforce exp (historical events)."""
    audiences = _allowed_audiences()
    if not audiences:
        raise ValueError("No OAuth client IDs configured for RISC audience validation")

    issuer, jwks_uri = _get_risc_config()
    jwks_client = _get_jwks_client(jwks_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audiences,
        issuer=issuer,
        options={"verify_exp": False},
    )
    return payload


def _jti_first_seen(jti: str) -> bool:
    """Return True if this is the first time we see jti (insert succeeded)."""
    _ensure_tables()
    try:
        db_optimizer.execute_query(
            "INSERT INTO google_risc_jti (jti) VALUES (?)",
            (jti,),
            fetch=False,
        )
        return True
    except Exception as e:
        # Portable duplicate-key handling (SQLite + Postgres) without backend-specific imports.
        message = str(e).lower()
        if "unique" in message or "duplicate key" in message:
            return False
        raise


def resolve_user_id_from_google_sub(sub: str) -> Optional[int]:
    """Match users.metadata.google_sub (set on Gmail OAuth success)."""
    if not sub:
        return None
    try:
        active_user_pred = db_optimizer.sql_cast_int_eq_one("is_active")
        rows = db_optimizer.execute_query(
            "SELECT id, metadata FROM users WHERE " + active_user_pred + " AND metadata IS NOT NULL"
        )
    except Exception as e:
        logger.warning("google_risc user lookup failed: %s", e)
        return None

    for row in rows or []:
        if isinstance(row, dict):
            uid = row.get("id")
            raw = row.get("metadata")
        else:
            uid = row[0] if row else None
            raw = row[1] if len(row) > 1 else None
        if uid is None:
            continue
        meta: Dict[str, Any] = {}
        if isinstance(raw, str) and raw.strip():
            try:
                meta = json.loads(raw)
            except json.JSONDecodeError:
                continue
        if meta.get("google_sub") == sub:
            return int(uid)
    return None


def _double_sha512_b64(token: str) -> str:
    h1 = hashlib.sha512(token.encode("utf-8")).digest()
    h2 = hashlib.sha512(h1).digest()
    return base64.b64encode(h2).decode("ascii")


def _find_users_matching_refresh_hint(
    identifier_alg: Optional[str], token_hint: Optional[str]
) -> List[int]:
    """Match stored Gmail refresh tokens to RISC token identifier (prefix or double-hash)."""
    if not token_hint or not identifier_alg:
        return []

    from core.app_oauth import decrypt as oauth_decrypt

    user_ids: List[int] = []
    try:
        active_token_pred = db_optimizer.sql_cast_int_eq_one("is_active")
        rows = db_optimizer.execute_query(
            """
            SELECT user_id, refresh_token_enc, refresh_token
            FROM gmail_tokens
            WHERE """
            + active_token_pred +
            """ AND (refresh_token_enc IS NOT NULL OR refresh_token IS NOT NULL)
            """
        )
    except Exception as e:
        logger.debug("gmail_tokens scan for RISC: %s", e)
        rows = []

    seen = set()
    for row in rows or []:
        if isinstance(row, dict):
            uid = row.get("user_id")
            enc = row.get("refresh_token_enc")
            plain = row.get("refresh_token")
        else:
            uid = row[0]
            enc = row[1] if len(row) > 1 else None
            plain = row[2] if len(row) > 2 else None

        if uid is None:
            continue
        rt = None
        try:
            if enc and str(enc) not in ("", "[encrypted]"):
                rt = oauth_decrypt(str(enc))
            elif plain and str(plain) not in ("", "[encrypted]"):
                rt = str(plain)
        except Exception:
            continue
        if not rt:
            continue

        if identifier_alg == "prefix" and token_hint == rt[:16]:
            user_ids.append(int(uid))
            seen.add(int(uid))
        elif identifier_alg == "hash_base64_sha512_sha512" and token_hint == _double_sha512_b64(rt):
            user_ids.append(int(uid))
            seen.add(int(uid))

    # oauth_tokens (gmail / google_calendar)
    try:
        active_oauth_pred = db_optimizer.sql_cast_int_eq_one("is_active")
        orows = db_optimizer.execute_query(
            """
            SELECT user_id, refresh_token_encrypted
            FROM oauth_tokens
            WHERE """
            + active_oauth_pred +
            """ AND service IN ('gmail', 'google_calendar')
              AND refresh_token_encrypted IS NOT NULL
            """
        )
    except Exception as e:
        logger.debug("oauth_tokens scan for RISC: %s", e)
        orows = []

    try:
        from core.oauth_token_manager import oauth_token_manager
    except Exception:
        oauth_token_manager = None

    for row in orows or []:
        if isinstance(row, dict):
            uid = row.get("user_id")
            enc = row.get("refresh_token_encrypted")
        else:
            uid = row[0]
            enc = row[1] if len(row) > 1 else None
        if uid is None or not enc or oauth_token_manager is None:
            continue
        try:
            rt = oauth_token_manager.decrypt_token(str(enc))
        except Exception:
            continue
        if not rt:
            continue
        uid_int = int(uid)
        if identifier_alg == "prefix" and token_hint == rt[:16] and uid_int not in seen:
            user_ids.append(uid_int)
            seen.add(uid_int)
        elif (
            identifier_alg == "hash_base64_sha512_sha512"
            and token_hint == _double_sha512_b64(rt)
            and uid_int not in seen
        ):
            user_ids.append(uid_int)
            seen.add(uid_int)

    return user_ids


def deactivate_google_connections_for_user(user_id: int) -> None:
    """Mark Google-backed tokens inactive; best-effort remote revoke for Gmail access token."""
    try:
        gmail_token_check = db_optimizer.execute_query(
            """
            SELECT access_token, access_token_enc
            FROM gmail_tokens
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        if gmail_token_check and len(gmail_token_check) > 0:
            token_row = gmail_token_check[0]
            access_token = token_row.get("access_token") if isinstance(token_row, dict) else token_row[0]
            if access_token and access_token != "[encrypted]":
                try:
                    requests.post(
                        f"https://oauth2.googleapis.com/revoke?token={access_token}",
                        timeout=10,
                    )
                except Exception as e:
                    logger.warning("Google revoke HTTP failed for user %s: %s", user_id, e)
            db_optimizer.execute_query(
                """
                UPDATE gmail_tokens
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_active = TRUE
                """,
                (user_id,),
                fetch=False,
            )
    except Exception as e:
        logger.warning("gmail_tokens deactivate for RISC user %s: %s", user_id, e)

    try:
        db_optimizer.execute_query(
            """
            UPDATE oauth_tokens
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND service IN ('gmail', 'google_calendar')
            """,
            (user_id,),
            fetch=False,
        )
    except Exception as e:
        logger.warning("oauth_tokens deactivate for RISC user %s: %s", user_id, e)


def _extract_iss_sub(event_payload: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    subj = event_payload.get("subject") or {}
    if subj.get("subject_type") == "iss-sub" and subj.get("sub"):
        iss = subj.get("iss") or "https://accounts.google.com/"
        return iss, str(subj["sub"])
    return None


def _handle_events_payload(decoded: Dict[str, Any]) -> None:
    events = decoded.get("events") or {}
    if not isinstance(events, dict):
        return

    for event_uri, payload in events.items():
        if not isinstance(payload, dict):
            continue

        if event_uri == EVENT_VERIFICATION:
            state = payload.get("state")
            logger.info(
                "google_risc verification event",
                extra={"event": "google_risc_verification", "metadata": {"state": state}},
            )
            continue

        google_sub = None
        pair = _extract_iss_sub(payload)
        if pair:
            google_sub = pair[1]

        user_id = resolve_user_id_from_google_sub(google_sub) if google_sub else None

        if event_uri == EVENT_OAUTH_TOKEN_REVOKED:
            subj = payload.get("subject") or {}
            token_type = subj.get("token_type")
            alg = subj.get("token_identifier_alg")
            token_hint = subj.get("token")
            if token_type == "refresh_token" and alg and token_hint:
                for uid in _find_users_matching_refresh_hint(alg, str(token_hint)):
                    deactivate_google_connections_for_user(uid)
            elif user_id:
                deactivate_google_connections_for_user(user_id)
            continue

        if user_id is None:
            logger.info(
                "google_risc event without mapped user",
                extra={
                    "event": "google_risc_unmapped",
                    "metadata": {"event_uri": event_uri, "has_sub": bool(google_sub)},
                },
            )
            continue

        if event_uri in (
            EVENT_SESSIONS_REVOKED,
            EVENT_OAUTH_TOKENS_REVOKED,
            EVENT_ACCOUNT_DISABLED,
        ):
            try:
                from core.secure_sessions import secure_session_manager

                secure_session_manager.revoke_all_user_sessions(user_id)
            except Exception as e:
                logger.error("RISC session revoke failed user %s: %s", user_id, e)
            if event_uri in (EVENT_OAUTH_TOKENS_REVOKED, EVENT_ACCOUNT_DISABLED):
                deactivate_google_connections_for_user(user_id)
            if event_uri == EVENT_ACCOUNT_DISABLED:
                reason = payload.get("reason")
                logger.warning(
                    "google_risc account-disabled",
                    extra={
                        "event": "google_risc_account_disabled",
                        "metadata": {"user_id": user_id, "reason": reason},
                    },
                )
            continue

        if event_uri == EVENT_ACCOUNT_ENABLED:
            logger.info(
                "google_risc account-enabled (no automatic action)",
                extra={"event": "google_risc_account_enabled", "metadata": {"user_id": user_id}},
            )
            continue

        if event_uri == EVENT_CREDENTIAL_CHANGE:
            logger.warning(
                "google_risc credential-change-required",
                extra={"event": "google_risc_cred_change", "metadata": {"user_id": user_id}},
            )
            continue


def process_security_event_token_string(body: str) -> Tuple[bool, Optional[str]]:
    """
    Validate token, dedupe by jti, apply handlers.
    Returns (success, error_message). On success error_message is None.
    """
    token = (body or "").strip()
    if not token:
        return False, "empty token"

    try:
        decoded = validate_security_event_token(token)
    except jwt.exceptions.PyJWTError as e:
        logger.info("google_risc JWT validation failed: %s", e)
        return False, "invalid token"
    except Exception as e:
        logger.warning("google_risc validation error: %s", e)
        return False, "invalid token"

    jti = decoded.get("jti")
    if jti:
        if not _jti_first_seen(str(jti)):
            return True, None

    try:
        _handle_events_payload(decoded)
    except Exception as e:
        logger.error("google_risc handler error: %s", e, exc_info=True)
        return False, "handler error"

    return True, None
