"""Transcript miss detection and human-approved alias proposal workflow (Phase 6d)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from company_chatbot import config
from company_chatbot.guards import _FRUSTRATION_RE, _GENERIC_FALLBACK_SNIPPET
from company_chatbot.retrieval import clear_kb_cache_for_tests, normalize_query_text, retrieve
from company_chatbot.service_families import chunk_service_families
from company_chatbot.transcript_store import ROLE_ASSISTANT, ROLE_USER, ensure_site_chat_transcript_tables
from core.database_optimization import db_optimizer

_MISS_ID_RE = re.compile(r"^[^:]+:\d+$")

_SIGNAL_PRIORITY: Dict[str, int] = {
    "hot_lead_ungrounded": 110,
    "warm_lead_ungrounded": 100,
    "user_frustration_followup": 90,
    "user_correction_followup": 85,
    "handoff_after_fallback": 80,
    "ungrounded": 70,
    "fallback_used": 60,
    "repeated_clarification": 55,
    "low_retrieval_score": 50,
    "low_confidence": 40,
}

_CORRECTION_RE = re.compile(
    r"\b(that'?s not what i meant|not what i (?:meant|asked)|wrong answer|"
    r"you misunderstood|didn'?t answer my question)\b",
    re.I,
)

_TRIVIAL_USER_RE = re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay)[\s!.?]*$", re.I)

_WARM_TIERS = frozenset({"warm", "hot"})


@dataclass
class TranscriptTurn:
    session_id: str
    turn_index: int
    user_message: str
    assistant_message: str
    mode: Optional[str] = None
    grounded: Optional[bool] = None
    confidence: Optional[float] = None
    sources: Optional[List[Dict[str, Any]]] = None
    handoff: Optional[Dict[str, Any]] = None
    lead_assessment: Optional[Dict[str, Any]] = None
    previous_user_message: str = ""
    next_user_message: str = ""
    created_at: Optional[str] = None


@dataclass
class MissSignals:
    signals: List[str] = field(default_factory=list)
    priority: str = "low"
    priority_score: int = 0
    retrieval_score: float = 0.0
    retrieval_top_chunk_id: Optional[str] = None

    @property
    def is_likely_miss(self) -> bool:
        return bool(self.signals)


@dataclass
class AliasProposal:
    miss_id: str
    session_id: str
    turn_index: int
    user_phrase: str
    miss_signals: List[str]
    priority: str
    suggested_alias: str
    suggested_service_families: List[str]
    suggested_chunk_ids: List[str]
    suggested_eval_case: Dict[str, Any]
    cursor_patch: str
    status: str = "proposal"
    requires_human_approval: bool = True
    notes: List[str] = field(default_factory=list)


def miss_id_for(session_id: str, turn_index: int) -> str:
    return f"{session_id}:{turn_index}"


def parse_miss_id(miss_id: str) -> Tuple[str, int]:
    raw = (miss_id or "").strip()
    if not _MISS_ID_RE.match(raw):
        raise ValueError("invalid_miss_id")
    session_id, turn_s = raw.rsplit(":", 1)
    return session_id, int(turn_s)


def _priority_label(score: int) -> str:
    if score >= 100:
        return "critical"
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def detect_miss_signals(turn: TranscriptTurn) -> MissSignals:
    signals: List[str] = []
    min_score = config.grounding_min_score()

    if turn.grounded is False:
        signals.append("ungrounded")
    if turn.confidence is not None and turn.confidence < min_score:
        signals.append("low_confidence")
    if turn.mode == config.MODE_FALLBACK:
        signals.append("fallback_used")

    handoff = turn.handoff or {}
    if turn.mode == config.MODE_FALLBACK and handoff.get("applicable"):
        signals.append("handoff_after_fallback")

    if turn.next_user_message:
        if _FRUSTRATION_RE.search(turn.next_user_message):
            signals.append("user_frustration_followup")
        if _CORRECTION_RE.search(turn.next_user_message):
            signals.append("user_correction_followup")

    assistant_norm = _norm(turn.assistant_message)
    if _GENERIC_FALLBACK_SNIPPET in assistant_norm:
        if turn.previous_user_message and _norm(turn.previous_user_message) == _norm(turn.user_message):
            signals.append("repeated_clarification")
        if turn.next_user_message and _norm(turn.next_user_message) == _norm(turn.user_message):
            signals.append("repeated_clarification")

    tier = str((turn.lead_assessment or {}).get("tier") or "").lower()
    if tier in _WARM_TIERS and turn.grounded is False:
        signals.append("warm_lead_ungrounded" if tier == "warm" else "hot_lead_ungrounded")

    retrieval = retrieve(
        turn.user_message,
        previous_query=turn.previous_user_message or None,
    )
    if retrieval.best_score < min_score:
        signals.append("low_retrieval_score")

    priority_score = max((_SIGNAL_PRIORITY.get(s, 10) for s in signals), default=0)
    return MissSignals(
        signals=sorted(set(signals)),
        priority=_priority_label(priority_score),
        priority_score=priority_score,
        retrieval_score=round(retrieval.best_score, 4),
        retrieval_top_chunk_id=retrieval.chunks[0].id if retrieval.chunks else None,
    )


def _slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_query_text(text).strip().lower()).strip("_")
    return (slug[:max_len] or "miss").strip("_")


def build_alias_proposal(turn: TranscriptTurn, miss: MissSignals) -> AliasProposal:
    retrieval = retrieve(
        turn.user_message,
        previous_query=turn.previous_user_message or None,
    )
    top_chunks = retrieval.chunks[:3]
    chunk_ids = [chunk.id for chunk in top_chunks]
    if not chunk_ids and turn.sources:
        chunk_ids = [str(src.get("id")) for src in turn.sources if src.get("id")]

    families: List[str] = []
    for chunk in top_chunks:
        families.extend(chunk_service_families(chunk))
    families = list(dict.fromkeys(families or retrieval.service_families))

    user_phrase = turn.user_message.strip()
    suggested_alias = normalize_query_text(user_phrase)
    primary_chunk = chunk_ids[0] if chunk_ids else "product_ai_email_assistant"
    eval_name = f"transcript_miss_{_slugify(turn.session_id)}_{turn.turn_index}"

    eval_case: Dict[str, Any] = {
        "name": eval_name,
        "query": user_phrase,
        "expected_ids": chunk_ids[:3] or [primary_chunk],
    }
    if families:
        eval_case["expected_families"] = families[:3]

    cursor_patch = _build_cursor_patch(
        miss_id=miss_id_for(turn.session_id, turn.turn_index),
        turn=turn,
        miss=miss,
        primary_chunk=primary_chunk,
        suggested_alias=suggested_alias,
        families=families,
        chunk_ids=chunk_ids,
        eval_case=eval_case,
    )

    return AliasProposal(
        miss_id=miss_id_for(turn.session_id, turn.turn_index),
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        user_phrase=user_phrase,
        miss_signals=miss.signals,
        priority=miss.priority,
        suggested_alias=suggested_alias,
        suggested_service_families=families,
        suggested_chunk_ids=chunk_ids,
        suggested_eval_case=eval_case,
        cursor_patch=cursor_patch,
        notes=[
            "Human approval required — do not auto-apply to production KB.",
            "Paste cursor_patch into Cursor, review, then run retrieval eval tests.",
        ],
    )


def _build_cursor_patch(
    *,
    miss_id: str,
    turn: TranscriptTurn,
    miss: MissSignals,
    primary_chunk: str,
    suggested_alias: str,
    families: Sequence[str],
    chunk_ids: Sequence[str],
    eval_case: Dict[str, Any],
) -> str:
    families_yaml = ", ".join(families) if families else "review manually"
    expected_ids_yaml = ", ".join(eval_case.get("expected_ids") or [])
    lines = [
        "# Phase 6d — Transcript miss proposal (HUMAN APPROVAL REQUIRED)",
        f"# Miss ID: {miss_id}",
        f"# Session: {turn.session_id} turn {turn.turn_index}",
        f"# Signals: {', '.join(miss.signals)}",
        f"# Priority: {miss.priority} (score {miss.priority_score})",
        f"# User phrase: {turn.user_message!r}",
        f"# Assistant mode: {turn.mode or 'n/a'} grounded={turn.grounded} confidence={turn.confidence}",
        "",
        "## Cursor task",
        "Review this proposal. If approved:",
        "1. Add the alias to the suggested KB chunk (or a better chunk if you disagree).",
        "2. Append the eval case to tests/company_chatbot_retrieval_eval.yaml.",
        "3. Run: FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest tests/test_company_chatbot_retrieval_eval.py -q",
        "4. Do NOT auto-apply in production without review.",
        "",
        "## Suggested eval case (tests/company_chatbot_retrieval_eval.yaml)",
        f"  - name: {eval_case['name']}",
        f"    query: {eval_case['query']}",
        f"    expected_ids: [{expected_ids_yaml}]",
    ]
    if eval_case.get("expected_families"):
        lines.append(f"    expected_families: [{families_yaml}]")
    lines.extend(
        [
            "",
            "## Suggested KB alias (data/company_chatbot/fikiri_kb_chunks.jsonl)",
            f"# Chunk ID: {primary_chunk}",
            f'# Add to "aliases": "{suggested_alias}"',
            f"# Optional service_families (if missing): [{families_yaml}]",
            "",
            "## Retrieval replay (debug)",
            f"# top_chunks: {list(chunk_ids)}",
            f"# retrieval_score: {miss.retrieval_score}",
            f"# retrieval_top: {miss.retrieval_top_chunk_id}",
        ]
    )
    return "\n".join(lines) + "\n"


def _parse_json_field(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def _row_get(row: Any, key: str, idx: int = 0) -> Any:
    return row[key] if hasattr(row, "keys") else row[idx]


def fetch_session_turns(session_id: str) -> List[TranscriptTurn]:
    ensure_site_chat_transcript_tables()
    rows = db_optimizer.execute_query(
        """
        SELECT role, content, mode, grounded, confidence, sources_json, handoff_json,
               lead_assessment_json, created_at
        FROM site_chat_messages
        WHERE session_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (session_id,),
    )
    messages = []
    for row in rows or []:
        grounded_raw = _row_get(row, "grounded", 3)
        messages.append(
            {
                "role": _row_get(row, "role", 0),
                "content": _row_get(row, "content", 1),
                "mode": _row_get(row, "mode", 2),
                "grounded": bool(grounded_raw) if grounded_raw is not None else None,
                "confidence": _row_get(row, "confidence", 4),
                "sources": _parse_json_field(_row_get(row, "sources_json", 5)),
                "handoff": _parse_json_field(_row_get(row, "handoff_json", 6)),
                "lead_assessment": _parse_json_field(_row_get(row, "lead_assessment_json", 7)),
                "created_at": _row_get(row, "created_at", 8),
            }
        )

    turns: List[TranscriptTurn] = []
    turn_index = 0
    last_user = ""
    pending_users: List[str] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg["role"] == ROLE_USER:
            pending_users.append(msg["content"])
            i += 1
            continue
        if msg["role"] != ROLE_ASSISTANT or not pending_users:
            i += 1
            continue

        user_message = pending_users[-1]
        previous_user = pending_users[-2] if len(pending_users) >= 2 else last_user
        next_user = ""
        j = i + 1
        while j < len(messages):
            if messages[j]["role"] == ROLE_USER:
                next_user = messages[j]["content"]
                break
            j += 1

        turn_index += 1
        turns.append(
            TranscriptTurn(
                session_id=session_id,
                turn_index=turn_index,
                user_message=user_message,
                assistant_message=msg["content"],
                mode=msg.get("mode"),
                grounded=msg.get("grounded"),
                confidence=msg.get("confidence"),
                sources=msg.get("sources"),
                handoff=msg.get("handoff"),
                lead_assessment=msg.get("lead_assessment"),
                previous_user_message=previous_user,
                next_user_message=next_user,
                created_at=msg.get("created_at"),
            )
        )
        last_user = user_message
        pending_users = []
        i += 1

    return turns


def list_likely_misses(
    *,
    limit: int = 20,
    offset: int = 0,
    min_priority: Optional[str] = None,
) -> Dict[str, Any]:
    """Scan recent transcript turns and return deterministic miss candidates."""
    ensure_site_chat_transcript_tables()
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    min_score = {"low": 0, "medium": 50, "high": 80, "critical": 100}.get(
        (min_priority or "").strip().lower(), 0
    )

    session_rows = db_optimizer.execute_query(
        """
        SELECT session_id FROM site_chat_sessions
        ORDER BY last_seen_at DESC
        LIMIT 500
        """
    )
    candidates: List[Dict[str, Any]] = []
    for row in session_rows or []:
        session_id = _row_get(row, "session_id", 0)
        for turn in fetch_session_turns(session_id):
            if _TRIVIAL_USER_RE.match(turn.user_message.strip()):
                continue
            miss = detect_miss_signals(turn)
            if not miss.is_likely_miss or miss.priority_score < min_score:
                continue
            candidates.append(
                {
                    "miss_id": miss_id_for(turn.session_id, turn.turn_index),
                    "session_id": turn.session_id,
                    "turn_index": turn.turn_index,
                    "user_message": turn.user_message,
                    "assistant_preview": (turn.assistant_message or "")[:160],
                    "mode": turn.mode,
                    "grounded": turn.grounded,
                    "confidence": turn.confidence,
                    "lead_tier": (turn.lead_assessment or {}).get("tier"),
                    "signals": miss.signals,
                    "priority": miss.priority,
                    "priority_score": miss.priority_score,
                    "retrieval_score": miss.retrieval_score,
                    "retrieval_top_chunk_id": miss.retrieval_top_chunk_id,
                    "created_at": turn.created_at,
                }
            )

    candidates.sort(key=lambda item: (-item["priority_score"], item.get("created_at") or ""))
    page = candidates[offset : offset + limit]
    return {
        "misses": page,
        "total": len(candidates),
        "limit": limit,
        "offset": offset,
        "min_priority": min_priority,
    }


def get_miss_proposal(session_id: str, turn_index: int) -> Optional[Dict[str, Any]]:
    turns = fetch_session_turns(session_id)
    turn = next((t for t in turns if t.turn_index == turn_index), None)
    if turn is None:
        return None
    miss = detect_miss_signals(turn)
    proposal = build_alias_proposal(turn, miss)
    return {
        "miss": {
            "miss_id": proposal.miss_id,
            "session_id": proposal.session_id,
            "turn_index": proposal.turn_index,
            "user_message": turn.user_message,
            "assistant_message": turn.assistant_message,
            "mode": turn.mode,
            "grounded": turn.grounded,
            "confidence": turn.confidence,
            "lead_assessment": turn.lead_assessment,
            "signals": miss.signals,
            "priority": miss.priority,
            "priority_score": miss.priority_score,
            "retrieval_score": miss.retrieval_score,
            "retrieval_top_chunk_id": miss.retrieval_top_chunk_id,
        },
        "proposal": {
            "status": proposal.status,
            "requires_human_approval": proposal.requires_human_approval,
            "user_phrase": proposal.user_phrase,
            "suggested_alias": proposal.suggested_alias,
            "suggested_service_families": proposal.suggested_service_families,
            "suggested_chunk_ids": proposal.suggested_chunk_ids,
            "suggested_eval_case": proposal.suggested_eval_case,
            "notes": proposal.notes,
        },
        "cursor_patch": proposal.cursor_patch,
    }


def export_miss_cursor_patch(session_id: str, turn_index: int) -> Optional[Dict[str, Any]]:
    payload = get_miss_proposal(session_id, turn_index)
    if not payload:
        return None
    return {
        "format": "cursor",
        "miss_id": payload["miss"]["miss_id"],
        "session_id": session_id,
        "turn_index": turn_index,
        "content": payload["cursor_patch"],
    }


def clear_miss_review_cache_for_tests() -> None:
    clear_kb_cache_for_tests()
