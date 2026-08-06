"""Automation event ingress domain logic (Windmill CE pilot).

Flask routes stay thin in routes/internal_automation_api.py.
This module owns schema validation, insert-first receipt ownership,
deterministic handling, and authoritative Fikiri audit coordination.

Windmill job/worker logs are NOT the audit trail.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.admin_audit import record_admin_audit
from core.database_optimization import db_optimizer
from core.trace_context import set_trace_id

logger = logging.getLogger(__name__)

SUPPORTED_EVENT_TYPE = "automation.test.received"
SUPPORTED_EVENT_VERSION = 1
SUPPORTED_SOURCE = "windmill-dev"
REQUIRED_SCOPE = "automation:ingress"
RESULT_CODE_ACCEPTED = "automation_test_received"

MAX_HTTP_BODY_BYTES = 32_768
MAX_DATA_JSON_BYTES = 8_192
MAX_EVENT_ID_LEN = 128
MAX_CORRELATION_ID_LEN = 128
MAX_SOURCE_LEN = 64
MAX_TENANT_ID_LEN = 64
MAX_NESTING_DEPTH = 4
MAX_DATA_KEYS = 32

EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

ALLOWED_TOP_LEVEL = frozenset(
    {
        "event_id",
        "event_type",
        "event_version",
        "source",
        "tenant_id",
        "correlation_id",
        "occurred_at",
        "data",
    }
)

STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Rate-limit permanent audits for authenticated insufficient-scope denials.
_SCOPE_DENY_AUDIT_WINDOW_S = 60.0
_SCOPE_DENY_AUDIT_MAX = 3
_scope_deny_audit_hits: Dict[str, List[float]] = {}


@dataclass
class IngressPrincipal:
    user_id: int
    api_key_id: int
    key_prefix: str
    scopes: List[str]


@dataclass
class IngressResult:
    http_status: int
    body: Dict[str, Any]


def apply_automation_event_receipts_migration_for_tests() -> None:
    """Apply 008 DDL via db_optimizer (translates BIGSERIAL for SQLite)."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "migrations" / "008_automation_event_receipts.sql"
    sql = path.read_text(encoding="utf-8")
    statements: List[str] = []
    buf: List[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        buf.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buf).strip().rstrip(";"))
            buf = []
    if buf:
        statements.append("\n".join(buf).strip().rstrip(";"))
    for stmt in statements:
        if stmt:
            db_optimizer.execute_query(stmt, fetch=False)


def receipts_table_ready() -> bool:
    try:
        return bool(db_optimizer.table_exists("automation_event_receipts"))
    except Exception:
        return False


def clear_automation_receipts_for_tests() -> None:
    if not receipts_table_ready():
        return
    try:
        db_optimizer.execute_query("DELETE FROM automation_event_receipts", fetch=False)
    except Exception:
        pass
    _scope_deny_audit_hits.clear()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_size(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _nesting_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, dict):
        if not value:
            return depth
        return max(_nesting_depth(v, depth + 1) for v in value.values())
    if isinstance(value, list):
        if not value:
            return depth
        return max(_nesting_depth(v, depth + 1) for v in value)
    return depth


def _canonical_request_hash(payload: Dict[str, Any]) -> str:
    material = {
        "event_type": payload["event_type"],
        "event_version": payload["event_version"],
        "tenant_id": payload.get("tenant_id"),
        "data": payload.get("data") or {},
        "occurred_at": payload.get("occurred_at"),
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_event_payload(raw: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (normalized_payload, error_body)."""
    if not isinstance(raw, dict):
        return None, {"success": False, "error": "JSON object required", "error_code": "INVALID_JSON"}

    unknown = set(raw.keys()) - ALLOWED_TOP_LEVEL
    if unknown:
        return None, {
            "success": False,
            "error": "Unknown top-level fields",
            "error_code": "UNKNOWN_FIELDS",
            "fields": sorted(unknown),
        }

    event_id = raw.get("event_id")
    if not isinstance(event_id, str) or not EVENT_ID_RE.match(event_id):
        return None, {
            "success": False,
            "error": "event_id invalid or too long",
            "error_code": "INVALID_EVENT_ID",
        }

    event_type = raw.get("event_type")
    if event_type != SUPPORTED_EVENT_TYPE:
        return None, {
            "success": False,
            "error": "Unsupported event_type",
            "error_code": "UNSUPPORTED_EVENT_TYPE",
        }

    event_version = raw.get("event_version")
    if event_version != SUPPORTED_EVENT_VERSION:
        return None, {
            "success": False,
            "error": "Unsupported event_version",
            "error_code": "UNSUPPORTED_EVENT_VERSION",
        }

    source = raw.get("source")
    if not isinstance(source, str) or len(source) > MAX_SOURCE_LEN or source != SUPPORTED_SOURCE:
        return None, {
            "success": False,
            "error": "Unsupported source",
            "error_code": "UNSUPPORTED_SOURCE",
        }

    tenant_id = raw.get("tenant_id", None)
    if tenant_id is not None:
        if isinstance(tenant_id, int):
            if tenant_id <= 0:
                return None, {
                    "success": False,
                    "error": "tenant_id malformed",
                    "error_code": "INVALID_TENANT",
                }
            tenant_id = str(tenant_id)
        elif isinstance(tenant_id, str):
            tenant_id = tenant_id.strip()
            if not tenant_id or len(tenant_id) > MAX_TENANT_ID_LEN or not tenant_id.isdigit():
                return None, {
                    "success": False,
                    "error": "tenant_id malformed",
                    "error_code": "INVALID_TENANT",
                }
        else:
            return None, {
                "success": False,
                "error": "tenant_id malformed",
                "error_code": "INVALID_TENANT",
            }

    correlation_id = raw.get("correlation_id")
    if correlation_id is None or correlation_id == "":
        correlation_id = f"corr_{uuid.uuid4().hex}"
    elif not isinstance(correlation_id, str) or not CORRELATION_ID_RE.match(correlation_id):
        return None, {
            "success": False,
            "error": "correlation_id invalid",
            "error_code": "INVALID_CORRELATION_ID",
        }

    occurred_at = raw.get("occurred_at")
    if occurred_at is not None and not isinstance(occurred_at, str):
        return None, {
            "success": False,
            "error": "occurred_at must be a string",
            "error_code": "INVALID_OCCURRED_AT",
        }
    if isinstance(occurred_at, str) and len(occurred_at) > 64:
        return None, {
            "success": False,
            "error": "occurred_at too long",
            "error_code": "INVALID_OCCURRED_AT",
        }

    data = raw.get("data", {})
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, {
            "success": False,
            "error": "data must be an object",
            "error_code": "INVALID_DATA",
        }
    if len(data) > MAX_DATA_KEYS:
        return None, {
            "success": False,
            "error": "data has too many keys",
            "error_code": "DATA_TOO_LARGE",
        }
    if _json_size(data) > MAX_DATA_JSON_BYTES:
        return None, {
            "success": False,
            "error": "data payload too large",
            "error_code": "DATA_TOO_LARGE",
        }
    if _nesting_depth(data) > MAX_NESTING_DEPTH:
        return None, {
            "success": False,
            "error": "data nesting too deep",
            "error_code": "DATA_TOO_DEEP",
        }

    normalized = {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": event_version,
        "source": source,
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "occurred_at": occurred_at or _utcnow_iso(),
        "data": data,
    }
    return normalized, None


def principal_has_ingress_scope(scopes: Any) -> bool:
    """Scopes are a JSON list of exact strings (see api_key_manager / webhook_api)."""
    if not isinstance(scopes, list):
        return False
    return REQUIRED_SCOPE in scopes


def log_unauthenticated_failure(*, reason: str, ip_address: Optional[str] = None) -> None:
    """Structured security log only — do not write permanent admin_audit rows."""
    logger.warning(
        "automation_ingress_auth_failed reason=%s ip=%s",
        reason,
        ip_address or "-",
        extra={
            "event": "automation.ingress.auth_failed",
            "service": "automation",
            "reason": reason,
            "ip_address": ip_address,
        },
    )


def _allow_scope_deny_audit(api_key_id: int) -> bool:
    key = str(api_key_id)
    now = time.time()
    hits = [t for t in _scope_deny_audit_hits.get(key, []) if now - t < _SCOPE_DENY_AUDIT_WINDOW_S]
    if len(hits) >= _SCOPE_DENY_AUDIT_MAX:
        _scope_deny_audit_hits[key] = hits
        return False
    hits.append(now)
    _scope_deny_audit_hits[key] = hits
    return True


def audit_insufficient_scope(
    principal: IngressPrincipal,
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    logger.warning(
        "automation_ingress_insufficient_scope api_key_id=%s user_id=%s",
        principal.api_key_id,
        principal.user_id,
    )
    if not _allow_scope_deny_audit(principal.api_key_id):
        logger.info(
            "automation_ingress_insufficient_scope_audit_sampled api_key_id=%s",
            principal.api_key_id,
        )
        return
    record_admin_audit(
        actor_user_id=principal.user_id,
        action="automation.ingress.denied",
        target_type="capability",
        target_id=REQUIRED_SCOPE,
        metadata={
            "api_key_id": principal.api_key_id,
            "key_prefix": principal.key_prefix,
            "reason": "insufficient_scope",
        },
        ip_address=ip_address,
        user_agent=user_agent,
        outcome="denied",
        capability=REQUIRED_SCOPE,
        correlation_id=correlation_id,
    )


def _select_receipt(source: str, event_id: str) -> Optional[Dict[str, Any]]:
    rows = db_optimizer.execute_query(
        """
        SELECT id, source, event_id, event_type, event_version, tenant_id, correlation_id,
               api_key_id, actor_user_id, request_hash, status, result_code, error_code,
               received_at, completed_at
        FROM automation_event_receipts
        WHERE source = ? AND event_id = ?
        LIMIT 1
        """,
        (source, event_id),
    )
    if not rows:
        return None
    return rows[0]


def _is_unique_violation(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "unique" in msg or "duplicate" in msg or "constraint" in msg


def _duplicate_response(receipt: Dict[str, Any], request_hash: str) -> IngressResult:
    if receipt.get("request_hash") != request_hash:
        return IngressResult(
            http_status=409,
            body={
                "success": False,
                "error": "Idempotency key reused with different payload",
                "error_code": "IDEMPOTENCY_PAYLOAD_CONFLICT",
                "event_id": receipt.get("event_id"),
                "source": receipt.get("source"),
                "correlation_id": receipt.get("correlation_id"),
                "duplicate": True,
            },
        )

    status = receipt.get("status")
    if status == STATUS_PROCESSING:
        return IngressResult(
            http_status=202,
            body={
                "success": True,
                "status": STATUS_PROCESSING,
                "duplicate": True,
                "event_id": receipt.get("event_id"),
                "source": receipt.get("source"),
                "correlation_id": receipt.get("correlation_id"),
                "message": "Event already processing",
            },
        )
    if status == STATUS_COMPLETED:
        return IngressResult(
            http_status=200,
            body={
                "success": True,
                "status": STATUS_COMPLETED,
                "duplicate": True,
                "event_id": receipt.get("event_id"),
                "source": receipt.get("source"),
                "correlation_id": receipt.get("correlation_id"),
                "result_code": receipt.get("result_code") or RESULT_CODE_ACCEPTED,
            },
        )
    return IngressResult(
        http_status=200,
        body={
            "success": False,
            "status": STATUS_FAILED,
            "duplicate": True,
            "event_id": receipt.get("event_id"),
            "source": receipt.get("source"),
            "correlation_id": receipt.get("correlation_id"),
            "error_code": receipt.get("error_code") or "PREVIOUSLY_FAILED",
        },
    )


def _claim_receipt(
    *,
    payload: Dict[str, Any],
    request_hash: str,
    principal: IngressPrincipal,
) -> Tuple[Optional[Dict[str, Any]], Optional[IngressResult]]:
    """Insert processing row. Returns (receipt, None) on ownership, or (None, dup_result)."""
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO automation_event_receipts (
                source, event_id, event_type, event_version, tenant_id, correlation_id,
                api_key_id, actor_user_id, request_hash, status, result_code, error_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                payload["source"],
                payload["event_id"],
                payload["event_type"],
                payload["event_version"],
                payload.get("tenant_id"),
                payload["correlation_id"],
                principal.api_key_id,
                principal.user_id,
                request_hash,
                STATUS_PROCESSING,
            ),
            fetch=False,
        )
    except Exception as exc:
        if not _is_unique_violation(exc):
            logger.error("automation_ingress_claim_failed: %s", exc)
            return None, IngressResult(
                http_status=500,
                body={
                    "success": False,
                    "error": "Failed to claim event",
                    "error_code": "CLAIM_FAILED",
                    "correlation_id": payload["correlation_id"],
                },
            )
        existing = _select_receipt(payload["source"], payload["event_id"])
        if not existing:
            return None, IngressResult(
                http_status=409,
                body={
                    "success": False,
                    "error": "Idempotency conflict",
                    "error_code": "IDEMPOTENCY_CONFLICT",
                    "correlation_id": payload["correlation_id"],
                },
            )
        return None, _duplicate_response(existing, request_hash)

    receipt = _select_receipt(payload["source"], payload["event_id"])
    return receipt, None


def _complete_receipt(source: str, event_id: str, *, result_code: str) -> None:
    db_optimizer.execute_query(
        """
        UPDATE automation_event_receipts
        SET status = ?, result_code = ?, completed_at = CURRENT_TIMESTAMP, error_code = NULL
        WHERE source = ? AND event_id = ? AND status = ?
        """,
        (STATUS_COMPLETED, result_code, source, event_id, STATUS_PROCESSING),
        fetch=False,
    )


def _fail_receipt(source: str, event_id: str, *, error_code: str) -> None:
    db_optimizer.execute_query(
        """
        UPDATE automation_event_receipts
        SET status = ?, error_code = ?, completed_at = CURRENT_TIMESTAMP
        WHERE source = ? AND event_id = ? AND status = ?
        """,
        (STATUS_FAILED, error_code, source, event_id, STATUS_PROCESSING),
        fetch=False,
    )


def handle_automation_test_event(
    payload: Dict[str, Any],
    *,
    principal: IngressPrincipal,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IngressResult:
    """Process only automation.test.received after ownership is established."""
    if not receipts_table_ready():
        return IngressResult(
            http_status=503,
            body={
                "success": False,
                "error": "automation_event_receipts table not applied",
                "error_code": "SCHEMA_NOT_READY",
            },
        )

    set_trace_id(payload["correlation_id"])
    request_hash = _canonical_request_hash(payload)

    receipt, early = _claim_receipt(payload=payload, request_hash=request_hash, principal=principal)
    if early is not None:
        return early
    assert receipt is not None

    # Ownership established — only now handle + permanent accepted audit.
    try:
        if payload["event_type"] != SUPPORTED_EVENT_TYPE:
            _fail_receipt(payload["source"], payload["event_id"], error_code="UNSUPPORTED_EVENT_TYPE")
            return IngressResult(
                http_status=400,
                body={
                    "success": False,
                    "error": "Unsupported event_type",
                    "error_code": "UNSUPPORTED_EVENT_TYPE",
                    "correlation_id": payload["correlation_id"],
                },
            )

        result_code = RESULT_CODE_ACCEPTED
        _complete_receipt(payload["source"], payload["event_id"], result_code=result_code)

        record_admin_audit(
            actor_user_id=principal.user_id,
            action="automation.ingress.accepted",
            target_type="automation_event",
            target_id=payload["event_id"],
            metadata={
                "api_key_id": principal.api_key_id,
                "key_prefix": principal.key_prefix,
                "source": payload["source"],
                "event_type": payload["event_type"],
                "event_version": payload["event_version"],
                "tenant_id": payload.get("tenant_id"),
                "result_code": result_code,
                "duplicate": False,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            outcome="success",
            capability=REQUIRED_SCOPE,
            correlation_id=payload["correlation_id"],
        )

        logger.info(
            "automation_ingress_accepted event_id=%s source=%s correlation_id=%s "
            "api_key_id=%s tenant_id=%s duplicate=false outcome=success",
            payload["event_id"],
            payload["source"],
            payload["correlation_id"],
            principal.api_key_id,
            payload.get("tenant_id"),
        )

        return IngressResult(
            http_status=200,
            body={
                "success": True,
                "status": STATUS_COMPLETED,
                "duplicate": False,
                "event_id": payload["event_id"],
                "source": payload["source"],
                "event_type": payload["event_type"],
                "correlation_id": payload["correlation_id"],
                "result_code": result_code,
            },
        )
    except Exception as exc:
        logger.error("automation_ingress_handler_failed: %s", exc)
        try:
            _fail_receipt(payload["source"], payload["event_id"], error_code="HANDLER_ERROR")
        except Exception:
            pass
        return IngressResult(
            http_status=500,
            body={
                "success": False,
                "error": "Handler failed",
                "error_code": "HANDLER_ERROR",
                "correlation_id": payload["correlation_id"],
            },
        )
