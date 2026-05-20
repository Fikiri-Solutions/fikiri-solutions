"""Eval case definitions and JSON loading for chatbot dev harness."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ChatbotEvalCase:
    """Single chatbot eval scenario (dev/local only)."""

    case_id: str
    tenant_id: str
    query: str
    expected_keywords: Tuple[str, ...] = ()
    forbidden_keywords: Tuple[str, ...] = ()
    expected_source_ids: Optional[Tuple[str, ...]] = None
    expected_fallback: Optional[bool] = None
    notes: str = ""
    user_id: Optional[int] = None

    def resolved_user_id(self) -> Optional[int]:
        if self.user_id is not None:
            return self.user_id
        tid = str(self.tenant_id or "").strip()
        if tid.isdigit():
            return int(tid)
        return None


def _normalize_str_list(raw: Any) -> Tuple[str, ...]:
    if not raw:
        return ()
    if isinstance(raw, str):
        return (raw.strip(),) if raw.strip() else ()
    out: List[str] = []
    for item in raw:
        s = str(item or "").strip()
        if s:
            out.append(s)
    return tuple(out)


def case_from_dict(data: Dict[str, Any]) -> ChatbotEvalCase:
    case_id = str(data.get("case_id") or data.get("id") or "").strip()
    if not case_id:
        raise ValueError("eval case requires case_id")
    tenant_id = str(data.get("tenant_id") or "").strip()
    if not tenant_id:
        raise ValueError(f"eval case {case_id!r} requires tenant_id")
    query = str(data.get("query") or "").strip()
    if not query:
        raise ValueError(f"eval case {case_id!r} requires query")

    expected_source_ids = data.get("expected_source_ids")
    source_tuple: Optional[Tuple[str, ...]] = None
    if expected_source_ids is not None:
        source_tuple = _normalize_str_list(expected_source_ids)
        if not source_tuple:
            source_tuple = None

    expected_fallback = data.get("expected_fallback")
    if expected_fallback is not None:
        expected_fallback = bool(expected_fallback)

    user_id_raw = data.get("user_id")
    user_id: Optional[int] = None
    if user_id_raw is not None:
        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"eval case {case_id!r} user_id must be int") from exc

    return ChatbotEvalCase(
        case_id=case_id,
        tenant_id=tenant_id,
        query=query,
        expected_keywords=_normalize_str_list(data.get("expected_keywords")),
        forbidden_keywords=_normalize_str_list(data.get("forbidden_keywords")),
        expected_source_ids=source_tuple,
        expected_fallback=expected_fallback,
        notes=str(data.get("notes") or "").strip(),
        user_id=user_id,
    )


def load_eval_cases(path: str | Path) -> List[ChatbotEvalCase]:
    """Load cases from a JSON file ({\"cases\": [...]} or a bare list)."""
    p = Path(path)
    raw_text = p.read_text(encoding="utf-8")
    payload = json.loads(raw_text)
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("cases") or payload.get("eval_cases") or []
    else:
        raise ValueError(f"unsupported eval cases format in {p}")
    return [case_from_dict(item) for item in items]


def builtin_sample_cases() -> List[ChatbotEvalCase]:
    """Minimal in-repo cases for smoke runs without external fixtures."""
    return [
        ChatbotEvalCase(
            case_id="sample_empty_fallback",
            tenant_id="1",
            query="What is the classified launch code for Mars?",
            expected_keywords=("information",),
            forbidden_keywords=("mars launch code", "classified"),
            expected_fallback=True,
            notes="Expect retrieval fallback when no FAQ/KB/vector hits.",
        ),
        ChatbotEvalCase(
            case_id="sample_hours_grounded",
            tenant_id="eval-tenant",
            user_id=42,
            query="What are your hours?",
            expected_keywords=("9", "5"),
            forbidden_keywords=("24/7", "midnight"),
            expected_source_ids=("faq_1",),
            expected_fallback=False,
            notes="Grounded FAQ/KB answer; used with mocks in unit tests.",
        ),
    ]
