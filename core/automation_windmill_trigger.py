"""Flask → Windmill normalize-leads trigger (development pilot).

Auth, audit, and optional idempotency stay in Flask.
Windmill only executes f/normalize_leads/normalize_leads.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.admin_audit import record_admin_audit
from core.automation_event_ingress import (
    EVENT_ID_RE,
    CORRELATION_ID_RE,
    IngressPrincipal,
    IngressResult,
    STATUS_COMPLETED,
    _claim_receipt,
    _complete_receipt,
    _fail_receipt,
    receipts_table_ready,
)
from core.automation_normalize_leads import MAX_BATCH_SIZE
from core.trace_context import set_trace_id
from core.windmill_dev_client import (
    WindmillClientError,
    WindmillDevConfig,
    run_script,
    windmill_trigger_enabled,
)

logger = logging.getLogger(__name__)

TRIGGER_SOURCE = "flask-trigger-dev"
TRIGGER_EVENT_TYPE = "automation.normalize_leads.triggered"
TRIGGER_EVENT_VERSION = 1
RESULT_CODE_QUEUED = "normalize_leads_queued"
REQUIRED_SCOPE = "automation:ingress"

MAX_HTTP_BODY_BYTES = 32_768
MAX_RECORDS_JSON_BYTES = 24_576


def _records_request_hash(records: List[Any], *, wait: bool) -> str:
    material = {"records": records, "wait": bool(wait)}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_normalize_trigger_payload(
    raw: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not isinstance(raw, dict):
        return None, {
            "success": False,
            "error": "JSON object required",
            "error_code": "INVALID_JSON",
        }

    allowed = {"records", "trigger_id", "correlation_id", "wait", "tenant_id"}
    unknown = set(raw.keys()) - allowed
    if unknown:
        return None, {
            "success": False,
            "error": "Unknown top-level fields",
            "error_code": "UNKNOWN_FIELDS",
            "fields": sorted(unknown),
        }

    records = raw.get("records")
    if not isinstance(records, list):
        return None, {
            "success": False,
            "error": "records must be an array",
            "error_code": "INVALID_RECORDS",
        }
    if len(records) > MAX_BATCH_SIZE:
        return None, {
            "success": False,
            "error": f"records exceeds max batch size ({MAX_BATCH_SIZE})",
            "error_code": "BATCH_TOO_LARGE",
        }
    try:
        encoded = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError):
        return None, {
            "success": False,
            "error": "records must be JSON-serializable",
            "error_code": "INVALID_RECORDS",
        }
    if len(encoded.encode("utf-8")) > MAX_RECORDS_JSON_BYTES:
        return None, {
            "success": False,
            "error": "records payload too large",
            "error_code": "RECORDS_TOO_LARGE",
        }

    trigger_id = raw.get("trigger_id")
    if trigger_id is None or trigger_id == "":
        trigger_id = f"trig_{uuid.uuid4().hex}"
    elif not isinstance(trigger_id, str) or not EVENT_ID_RE.match(trigger_id):
        return None, {
            "success": False,
            "error": "trigger_id invalid",
            "error_code": "INVALID_TRIGGER_ID",
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

    wait = bool(raw.get("wait") is True)

    tenant_id = raw.get("tenant_id")
    if tenant_id is not None and not isinstance(tenant_id, (str, int)):
        return None, {
            "success": False,
            "error": "tenant_id malformed",
            "error_code": "INVALID_TENANT",
        }
    if isinstance(tenant_id, int):
        tenant_id = str(tenant_id)
    if isinstance(tenant_id, str):
        tenant_id = tenant_id.strip() or None

    return {
        "records": records,
        "trigger_id": trigger_id,
        "correlation_id": correlation_id,
        "wait": wait,
        "tenant_id": tenant_id,
    }, None


def handle_normalize_leads_trigger(
    payload: Dict[str, Any],
    *,
    principal: IngressPrincipal,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    config: Optional[WindmillDevConfig] = None,
) -> IngressResult:
    if not windmill_trigger_enabled():
        return IngressResult(
            http_status=503,
            body={
                "success": False,
                "error": "Windmill trigger disabled (set FIKIRI_WINDMILL_TRIGGER_ENABLED=1)",
                "error_code": "TRIGGER_DISABLED",
            },
        )

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
    request_hash = _records_request_hash(payload["records"], wait=payload["wait"])
    claim_payload = {
        "source": TRIGGER_SOURCE,
        "event_id": payload["trigger_id"],
        "event_type": TRIGGER_EVENT_TYPE,
        "event_version": TRIGGER_EVENT_VERSION,
        "tenant_id": payload.get("tenant_id"),
        "correlation_id": payload["correlation_id"],
    }
    receipt, dup = _claim_receipt(
        payload=claim_payload,
        request_hash=request_hash,
        principal=principal,
    )
    if dup is not None:
        return dup
    assert receipt is not None

    try:
        run = run_script(
            {"records": payload["records"]},
            config=config,
            wait=payload["wait"],
        )
    except WindmillClientError as exc:
        _fail_receipt(TRIGGER_SOURCE, payload["trigger_id"], error_code=exc.error_code)
        record_admin_audit(
            actor_user_id=principal.user_id,
            action="automation.windmill.trigger",
            target_type="windmill_script",
            target_id=(config or WindmillDevConfig.from_env()).script_path,
            metadata={
                "trigger_id": payload["trigger_id"],
                "api_key_id": principal.api_key_id,
                "key_prefix": principal.key_prefix,
                "wait": payload["wait"],
                "error_code": exc.error_code,
                "record_count": len(payload["records"]),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            outcome="error",
            capability=REQUIRED_SCOPE,
            correlation_id=payload["correlation_id"],
        )
        http_status = 502
        if exc.error_code == "WINDMILL_TOKEN_MISSING":
            http_status = 503
        elif exc.error_code == "TRIGGER_DISABLED":
            http_status = 503
        return IngressResult(
            http_status=http_status,
            body={
                "success": False,
                "error": "Windmill trigger failed",
                "error_code": exc.error_code,
                "trigger_id": payload["trigger_id"],
                "correlation_id": payload["correlation_id"],
            },
        )

    job_id = run.get("job_id")
    result_code = (
        f"wm_job:{job_id}" if job_id else ("wm_wait_ok" if run.get("result") is not None else RESULT_CODE_QUEUED)
    )
    _complete_receipt(TRIGGER_SOURCE, payload["trigger_id"], result_code=result_code[:240])

    after = {
        "trigger_id": payload["trigger_id"],
        "job_id": job_id,
        "wait": payload["wait"],
        "workspace": run.get("workspace"),
        "script_path": run.get("script_path"),
        "record_count": len(payload["records"]),
    }
    if payload["wait"]:
        # Do not persist full result in audit; only summarize keys.
        result = run.get("result") if isinstance(run.get("result"), dict) else {}
        after["result_summary"] = {
            "accepted": len(result.get("accepted") or []) if isinstance(result, dict) else None,
            "rejected": len(result.get("rejected") or []) if isinstance(result, dict) else None,
            "duplicate_count": result.get("duplicate_count") if isinstance(result, dict) else None,
        }

    record_admin_audit(
        actor_user_id=principal.user_id,
        action="automation.windmill.trigger",
        target_type="windmill_script",
        target_id=run.get("script_path"),
        after=after,
        metadata={
            "api_key_id": principal.api_key_id,
            "key_prefix": principal.key_prefix,
            "result_code": result_code,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        outcome="success",
        capability=REQUIRED_SCOPE,
        correlation_id=payload["correlation_id"],
    )

    body: Dict[str, Any] = {
        "success": True,
        "status": STATUS_COMPLETED,
        "duplicate": False,
        "trigger_id": payload["trigger_id"],
        "correlation_id": payload["correlation_id"],
        "workspace": run.get("workspace"),
        "script_path": run.get("script_path"),
        "wait": payload["wait"],
        "result_code": result_code,
    }
    if job_id:
        body["job_id"] = job_id
    if payload["wait"]:
        body["result"] = run.get("result")

    return IngressResult(http_status=202 if not payload["wait"] else 200, body=body)
