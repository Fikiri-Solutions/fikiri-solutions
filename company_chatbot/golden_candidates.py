"""Production miss → golden candidate (never auto-promoted)."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any, Dict, List, Optional, Sequence


CANDIDATE_STATUSES = (
    "OBSERVED",
    "TRIAGED",
    "LABELED",
    "FIXED",
    "VERIFIED",
    "PROMOTED_TO_GOLDEN",
)

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_URL_RE = re.compile(r"https?://\S+", re.I)


def redact_query_for_export(text: str, *, keep_length: int = 120) -> str:
    """Strip common PII before candidate exports are shared or committed."""
    raw = (text or "").strip()
    if not raw:
        return ""
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", raw)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = _URL_RE.sub("[REDACTED_URL]", redacted)
    if len(redacted) > keep_length:
        redacted = redacted[: keep_length - 1].rstrip() + "…"
    return redacted


def query_fingerprint(text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return digest[:12]


def build_golden_candidate(
    *,
    miss_id: str,
    query: str,
    previous_query: Optional[str] = None,
    retrieved_ids: Sequence[str] = (),
    expected_ids: Sequence[str] = (),
    forbidden_ids: Sequence[str] = (),
    expected_mode: Optional[str] = None,
    forbidden_modes: Sequence[str] = (),
    topic: Optional[str] = None,
    context_dependency: Optional[str] = None,
    failure_labels: Sequence[str] = (),
    tags: Sequence[str] = (),
    notes: str = "",
    redact: bool = True,
) -> Dict[str, Any]:
    """
    Build a rich golden-case candidate for human review.

    Lifecycle starts at OBSERVED. Automation may create candidates only;
    promotion into tests/company_chatbot_retrieval_eval.yaml requires humans.
    """
    name = f"prod_miss_{miss_id}"
    retrieval: Dict[str, List[str]] = {
        "required": list(expected_ids),
        "acceptable": [],
        "forbidden": list(forbidden_ids),
    }
    if not forbidden_ids and retrieved_ids and expected_ids:
        retrieval["forbidden"] = [
            chunk_id for chunk_id in retrieved_ids if chunk_id not in set(expected_ids)
        ]

    export_query = redact_query_for_export(query) if redact else query
    export_previous = (
        redact_query_for_export(previous_query) if (redact and previous_query) else previous_query
    )

    candidate: Dict[str, Any] = {
        "id": name,
        "name": name,
        "query": export_query,
        "status": "OBSERVED",
        "expected": {
            "context_dependency": context_dependency,
            "mode": expected_mode,
            "topic": topic,
            "ids": retrieval,
            "forbidden_modes": list(forbidden_modes),
        },
        "tags": list(dict.fromkeys([*(tags or []), "production_miss", "needs_review"])),
        "provenance": {
            "source": "production_miss",
            "miss_id": miss_id,
            "first_seen": date.today().isoformat(),
            "regression": True,
            "failure_labels": list(failure_labels),
            "retrieved_at_miss": list(retrieved_ids),
            "notes": notes,
            "auto_promote": False,
            "redacted": bool(redact),
            "query_fingerprint": query_fingerprint(query),
        },
    }
    if export_previous:
        candidate["previous_query"] = export_previous
    return candidate


def candidate_to_yaml_fragment(candidate: Dict[str, Any]) -> str:
    """Render a reviewable YAML fragment (not applied automatically)."""
    expected = candidate.get("expected") or {}
    ids = expected.get("ids") or {}
    prov = candidate.get("provenance") or {}
    lines = [
        f"  # CANDIDATE — status={candidate.get('status')} auto_promote=false "
        f"redacted={str(bool(prov.get('redacted', True))).lower()}",
        f"  # miss_id={prov.get('miss_id')} fingerprint={prov.get('query_fingerprint')}",
        f"  - name: {candidate.get('name')}",
        f"    query: {candidate.get('query')!r}",
    ]
    if candidate.get("previous_query"):
        lines.append(f"    previous_query: {candidate['previous_query']!r}")
    if expected.get("topic"):
        lines.append(f"    topic: {expected['topic']}")
    if expected.get("context_dependency"):
        lines.append(f"    context_dependency: {expected['context_dependency']}")
    lines.append("    retrieval:")
    lines.append(f"      required: {list(ids.get('required') or [])}")
    if ids.get("acceptable"):
        lines.append(f"      acceptable: {list(ids.get('acceptable') or [])}")
    if ids.get("forbidden"):
        lines.append(f"      forbidden: {list(ids.get('forbidden') or [])}")
    if expected.get("mode"):
        lines.append(f"    expected_mode: {expected['mode']}")
    if expected.get("forbidden_modes"):
        lines.append(f"    forbidden_modes: {list(expected['forbidden_modes'])}")
    tags = candidate.get("tags") or []
    if tags:
        lines.append(f"    tags: {list(tags)}")
    lines.append("    provenance:")
    lines.append(f"      source: {prov.get('source', 'production_miss')}")
    lines.append(f"      miss_id: {prov.get('miss_id')}")
    lines.append(f"      first_seen: {prov.get('first_seen')}")
    lines.append("      regression: true")
    lines.append("      auto_promote: false")
    lines.append(f"      redacted: {str(bool(prov.get('redacted', True))).lower()}")
    return "\n".join(lines) + "\n"


def advance_candidate_status(candidate: Dict[str, Any], new_status: str) -> Dict[str, Any]:
    if new_status not in CANDIDATE_STATUSES:
        raise ValueError(f"invalid status: {new_status}")
    current = candidate.get("status") or "OBSERVED"
    try:
        cur_i = CANDIDATE_STATUSES.index(current)
        new_i = CANDIDATE_STATUSES.index(new_status)
    except ValueError as exc:
        raise ValueError(f"unknown status transition {current} → {new_status}") from exc
    if new_i < cur_i:
        raise ValueError(f"cannot regress status {current} → {new_status}")
    updated = dict(candidate)
    updated["status"] = new_status
    return updated
