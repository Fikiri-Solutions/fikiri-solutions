"""
Single IF-group trigger conditions (match: all = AND across conditions).

Stored under trigger_conditions["if"]:
  { "match": "all", "conditions": [ { "field", "op", "value?" }, ... ] }

When "conditions" is non-empty, only this group is evaluated (legacy flat rules are skipped).
When the "if" key is absent or conditions is empty, legacy per-trigger checks apply in AutomationEngine.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

IF_MATCH_ALL = "all"

# Maximum regex pattern length to limit ReDoS / accidental huge patterns.
_MAX_REGEX_PATTERN_LEN = 512

# Fields allowed per trigger_type (values must match TriggerType enum .value).
ALLOWED_FIELDS_BY_TRIGGER: Dict[str, frozenset] = {
    "email_received": frozenset({"sender_email", "subject", "text", "email_id"}),
    "email_sent": frozenset({"sender_email", "subject", "text", "email_id"}),
    "lead_created": frozenset({"lead_id", "source", "score", "email", "name"}),
    "lead_stage_changed": frozenset({"lead_id", "old_stage", "new_stage", "email"}),
    "time_based": frozenset({"frequency", "scheduled_run"}),
    "keyword_detected": frozenset({"text", "sender_email", "subject"}),
}

STRING_OPS = frozenset(
    {
        "equals",
        "not_equals",
        "contains",
        "not_contains",
        "starts_with",
        "ends_with",
        "regex",
        "is_empty",
        "is_not_empty",
    }
)
NUMERIC_OPS = frozenset({"gt", "gte", "lt", "lte"})

ALL_OPS = STRING_OPS | NUMERIC_OPS

# Fields that only support equality / emptiness (no substring / regex).
BOOLEANISH_FIELDS = frozenset({"scheduled_run"})
NUMERIC_ONLY_FIELDS = frozenset({"lead_id", "score"})

# For these fields, string comparisons use case-folding (lower()).
_CASEFOLD_STRING_FIELDS = frozenset(
    {
        "sender_email",
        "email",
        "subject",
        "text",
        "source",
        "name",
        "old_stage",
        "new_stage",
        "frequency",
        "email_id",
    }
)


def validate_if_group_structure(
    trigger_type: str, if_block: Any
) -> Tuple[bool, Optional[str]]:
    """Validate shape of trigger_conditions['if']. Returns (ok, error_message)."""
    if if_block is None:
        return True, None
    if not isinstance(if_block, dict):
        return False, "trigger_conditions.if must be an object"
    match = if_block.get("match")
    if match is not None and match != IF_MATCH_ALL:
        return False, f'trigger_conditions.if.match must be "{IF_MATCH_ALL}"'
    conds = if_block.get("conditions")
    if conds is None:
        return True, None
    if not isinstance(conds, list):
        return False, "trigger_conditions.if.conditions must be a list"
    allowed = ALLOWED_FIELDS_BY_TRIGGER.get(trigger_type)
    if not allowed:
        return False, f"Unknown trigger_type for IF group: {trigger_type}"
    for i, c in enumerate(conds):
        if not isinstance(c, dict):
            return False, f"trigger_conditions.if.conditions[{i}] must be an object"
        field = c.get("field")
        op = c.get("op")
        if not field or not isinstance(field, str):
            return False, f"trigger_conditions.if.conditions[{i}].field is required"
        if field not in allowed:
            return False, (
                f"Field {field!r} is not allowed for trigger {trigger_type}; "
                f"allowed: {sorted(allowed)}"
            )
        if not op or not isinstance(op, str):
            return False, f"trigger_conditions.if.conditions[{i}].op is required"
        if op not in ALL_OPS:
            return False, f"Unsupported operator {op!r} in conditions[{i}]"
        if op in NUMERIC_OPS and field not in NUMERIC_ONLY_FIELDS:
            return False, f"Operator {op} is only valid for numeric fields (lead_id, score)"
        if field in NUMERIC_ONLY_FIELDS and op not in (
            NUMERIC_OPS | {"equals", "not_equals", "is_empty", "is_not_empty"}
        ):
            return (
                False,
                f"Operator {op} is not valid for numeric field {field}",
            )
        if field in BOOLEANISH_FIELDS and op not in frozenset(
            {"equals", "not_equals", "is_empty", "is_not_empty"}
        ):
            return (
                False,
                f"Operator {op} is not valid for field {field}; "
                "use equals, not_equals, is_empty, or is_not_empty",
            )
        if op in {"is_empty", "is_not_empty"}:
            continue
        if op in NUMERIC_OPS:
            if c.get("value") is None or c.get("value") == "":
                return False, f"conditions[{i}].value is required for operator {op}"
        else:
            if c.get("value") is None:
                return False, f"conditions[{i}].value is required for operator {op}"
    return True, None


def _coerce_number(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def _resolve_value(trigger_data: Mapping[str, Any], field: str) -> Any:
    if field not in trigger_data:
        return None
    return trigger_data.get(field)


def _normalize_string(field: str, value: Any) -> str:
    if value is None:
        return ""
    s = value if isinstance(value, str) else str(value)
    if field in _CASEFOLD_STRING_FIELDS:
        return s.casefold()
    return s


def _truthy_config_value(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    if isinstance(raw, (int, float)):
        return raw != 0
    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return bool(raw)


def _condition_applies(
    trigger_type: str,
    trigger_data: Mapping[str, Any],
    cond: Mapping[str, Any],
) -> bool:
    field = cond.get("field")
    op = cond.get("op")
    raw_val = cond.get("value")

    allowed = ALLOWED_FIELDS_BY_TRIGGER.get(trigger_type, frozenset())
    if field not in allowed or op not in ALL_OPS:
        return False

    actual = _resolve_value(trigger_data, field)

    if field == "scheduled_run":
        if op == "equals":
            return _truthy_config_value(actual) == _truthy_config_value(raw_val)
        if op == "not_equals":
            return _truthy_config_value(actual) != _truthy_config_value(raw_val)
        if op == "is_empty":
            return actual is None
        if op == "is_not_empty":
            return actual is not None
        return False

    if op in {"is_empty", "is_not_empty"}:
        if actual is None:
            is_empty = True
        elif isinstance(actual, str):
            is_empty = actual.strip() == ""
        elif isinstance(actual, (int, float)):
            is_empty = False
        elif isinstance(actual, bool):
            is_empty = False
        else:
            is_empty = str(actual).strip() == ""
        return is_empty if op == "is_empty" else not is_empty

    if op in NUMERIC_OPS:
        left = _coerce_number(actual)
        right = _coerce_number(raw_val)
        if left is None or right is None:
            return False
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        if op == "lte":
            return left <= right
        return False

    if field in ("lead_id", "score") and op in ("equals", "not_equals"):
        ln = _coerce_number(actual)
        rn = _coerce_number(raw_val)
        if ln is not None and rn is not None:
            eq = ln == rn
            return eq if op == "equals" else not eq

    left_s = _normalize_string(field, actual)
    right_s = _normalize_string(field, raw_val)

    if op == "equals":
        return left_s == right_s
    if op == "not_equals":
        return left_s != right_s
    if op == "contains":
        return right_s in left_s
    if op == "not_contains":
        return right_s not in left_s
    if op == "starts_with":
        return left_s.startswith(right_s)
    if op == "ends_with":
        return left_s.endswith(right_s)
    if op == "regex":
        pattern = raw_val if isinstance(raw_val, str) else str(raw_val)
        if len(pattern) > _MAX_REGEX_PATTERN_LEN:
            logger.warning("regex pattern too long; condition fails")
            return False
        try:
            cre = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        except re.error as e:
            logger.warning("invalid regex in trigger condition: %s", e)
            return False
        haystack = actual if isinstance(actual, str) else ("" if actual is None else str(actual))
        return cre.search(haystack) is not None

    return False


def evaluate_if_group(
    trigger_type: str,
    trigger_data: Mapping[str, Any],
    if_block: Mapping[str, Any],
) -> bool:
    """
    Evaluate AND across all conditions in if_block.
    Precondition: validate_if_group_structure passed for this block.
    """
    match = if_block.get("match") or IF_MATCH_ALL
    if match != IF_MATCH_ALL:
        return False
    conds: Sequence[Mapping[str, Any]] = if_block.get("conditions") or []
    if not conds:
        return True
    td = dict(trigger_data or {})
    # Normalise scheduled_run for time_based (JSON/clients may send "true"/"false" strings).
    if trigger_type == "time_based" and "scheduled_run" in td:
        v = td["scheduled_run"]
        if not isinstance(v, bool):
            td["scheduled_run"] = _truthy_config_value(v)

    for cond in conds:
        if not _condition_applies(trigger_type, td, cond):
            return False
    return True


def trigger_condition_metadata() -> Dict[str, Any]:
    """Public schema for Automation Studio UI and API consumers."""
    field_labels: Dict[str, str] = {
        "sender_email": "Sender email",
        "subject": "Subject",
        "text": "Body / text",
        "email_id": "Email ID",
        "lead_id": "Lead ID",
        "source": "Source",
        "score": "Score",
        "email": "Lead email",
        "name": "Lead name",
        "old_stage": "Previous stage",
        "new_stage": "New stage",
        "frequency": "Frequency",
        "scheduled_run": "Scheduled run",
    }
    op_labels = {
        "equals": "equals",
        "not_equals": "does not equal",
        "contains": "contains",
        "not_contains": "does not contain",
        "starts_with": "starts with",
        "ends_with": "ends with",
        "regex": "matches regex",
        "is_empty": "is empty",
        "is_not_empty": "is not empty",
        "gt": "greater than",
        "gte": "greater or equal",
        "lt": "less than",
        "lte": "less or equal",
    }
    triggers_out = {}
    for tt, fields in ALLOWED_FIELDS_BY_TRIGGER.items():
        triggers_out[tt] = {
            "fields": [
                {"value": f, "label": field_labels.get(f, f.replace("_", " ").title())}
                for f in sorted(fields)
            ],
            "string_operators": sorted(STRING_OPS),
            "numeric_operators": sorted(NUMERIC_OPS),
            "numeric_fields": ["lead_id", "score"],
        }
    return {
        "if_match_values": [IF_MATCH_ALL],
        "operator_labels": op_labels,
        "triggers": triggers_out,
    }
