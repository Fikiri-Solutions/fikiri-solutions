"""Site bot orchestrator — dispatch map, intake state, and persisted sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from company_chatbot import config
from company_chatbot.guards import (
    GuardContext,
    MAX_IDENTICAL_RESPONSES,
    build_guard_handoff_message,
    evaluate_guards,
    would_repeat_too_many_times,
)
from company_chatbot.intake import (
    IntakeSlots,
    build_intake_summary,
    intake_metadata,
    process_intake_turn,
    should_start_intake,
)
from company_chatbot.lead_scoring import assess_lead
from company_chatbot.modes import detect_mode
from company_chatbot.schemas import (
    HandoffMetadata,
    LeadAssessmentMetadata,
    LeadIntentMetadata,
    MessageResult,
    SessionStartResult,
)
from company_chatbot.session_store import (
    clear_sessions_for_tests as _reset_session_store,
    load_session,
    save_session,
)

_WELCOME = (
    "Hi — I'm the Fikiri assistant. Ask about our product, explore fit, "
    "or say if you'd like a workflow audit or to talk with our team."
)

@dataclass
class SessionState:
    session_id: str
    turn_count: int = 0
    last_mode: str = config.MODE_FALLBACK
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    intake_active: bool = False
    intake_mode: str = config.MODE_EXPLORE_FIT
    intake_slots: IntakeSlots = field(default_factory=IntakeSlots)
    response_history: List[str] = field(default_factory=list)
    last_user_message: str = ""


def clear_sessions_for_tests() -> None:
    """Reset session store (tests only)."""
    _reset_session_store()


def start_session() -> SessionStartResult:
    session_id = f"site_{uuid.uuid4().hex}"
    state = SessionState(session_id=session_id)
    save_session(state)
    return SessionStartResult(session_id=session_id, welcome=_WELCOME)


def get_session(session_id: str) -> Optional[SessionState]:
    return load_session(session_id)


def handle_message(session_id: str, message: str) -> MessageResult:
    session = load_session(session_id)
    if session is None:
        raise KeyError("session_not_found")

    text = (message or "").strip()
    session.turn_count += 1
    previous_user_message = session.last_user_message
    session.last_user_message = text

    guard = evaluate_guards(
        GuardContext(
            turn_count=session.turn_count,
            message=text,
            intake_active=session.intake_active,
            response_history=session.response_history,
        )
    )
    if guard.suggest_handoff:
        result = _guard_handoff_result(session, guard.reason or "guard", previous_user_message)
        save_session(session)
        return result

    if session.intake_active:
        interrupt_mode = detect_mode(text)
        if interrupt_mode in (config.MODE_ANSWER, config.MODE_CONTACT):
            session.intake_active = False
            result = _dispatch_mode(interrupt_mode, text, session, previous_user_message)
            save_session(session)
            return result
        result = _run_intake_turn(session, text, session.intake_mode, previous_user_message)
        save_session(session)
        return result

    mode = detect_mode(text)
    session.last_mode = mode

    if should_start_intake(mode):
        session.intake_active = True
        session.intake_mode = mode
        result = _run_intake_turn(session, text, mode, previous_user_message)
        save_session(session)
        return result

    result = _dispatch_mode(mode, text, session, previous_user_message)
    save_session(session)
    return result


def _dispatch_mode(
    mode: str, message: str, session: SessionState, previous_user_message: str = ""
) -> MessageResult:
    if mode == config.MODE_ANSWER:
        result = _handle_answer(
            message=message,
            session=session,
            previous_user_message=previous_user_message,
        )
    elif mode == config.MODE_FALLBACK:
        result = _handle_fallback(message, session, previous_user_message=previous_user_message)
    else:
        handler = _HANDLERS.get(mode, _handle_fallback)
        result = handler(message=message, session=session)
    return _finalize_response(session, result, previous_user_message)


def _run_intake_turn(
    session: SessionState, message: str, mode: str, previous_user_message: str = ""
) -> MessageResult:
    turn = process_intake_turn(message, session.intake_slots, mode)
    session.intake_slots = turn.slots

    if turn.complete:
        session.intake_active = False
        response = turn.response
        handoff_type = "intake"
    else:
        response = turn.response
        handoff_type = None

    result = _base_result(
        mode,
        response,
        session,
        HandoffMetadata(
            applicable=turn.complete,
            primary=config.HANDOFF_PRIMARY_WIDGET,
            secondary=config.HANDOFF_SECONDARY_INTAKE,
            handoff_type=handoff_type,
        ),
        LeadIntentMetadata(
            signals=[mode, "intake"],
            capture_ready=turn.complete and bool(session.intake_slots.contact_email),
        ),
        intake=intake_metadata(
            turn.slots,
            active=not turn.complete,
            complete=turn.complete,
            next_slot=turn.next_slot,
        ),
    )
    return _finalize_response(session, result, previous_user_message)


def _guard_handoff_result(session: SessionState, reason: str, previous_user_message: str = "") -> MessageResult:
    session.intake_active = False
    summary = ""
    if session.intake_slots and any(
        getattr(session.intake_slots, slot) for slot in ("industry", "main_pain", "timeline")
    ):
        summary = build_intake_summary(session.intake_slots).replace(
            "Thanks — here's what I captured:", "What I have so far:"
        )
    mode = session.last_mode or config.MODE_FALLBACK
    result = _base_result(
        mode,
        build_guard_handoff_message(reason, summary),
        session,
        HandoffMetadata(
            applicable=True,
            primary=config.HANDOFF_PRIMARY_WIDGET,
            secondary=config.HANDOFF_SECONDARY_INTAKE,
            handoff_type="intake",
        ),
        LeadIntentMetadata(signals=["guard_handoff", reason or "guard"]),
        intake=intake_metadata(
            session.intake_slots,
            active=False,
            complete=True,
            next_slot=None,
        ),
    )
    return _finalize_response(session, result, previous_user_message)


def _finalize_response(
    session: SessionState, result: MessageResult, previous_user_message: str = ""
) -> MessageResult:
    if would_repeat_too_many_times(
        session.response_history,
        result.response,
        last_user_message=previous_user_message,
        current_user_message=session.last_user_message,
    ):
        return _guard_handoff_result(session, "repeat_response", previous_user_message)

    intake_complete = bool(result.intake.get("complete"))
    assessment = assess_lead(
        message=session.last_user_message,
        mode=result.mode,
        slots=session.intake_slots,
        handoff=result.handoff,
        grounded=result.grounded,
        turn_count=session.turn_count,
        intake_complete=intake_complete,
        previous_message=previous_user_message,
    )
    result.lead_assessment = LeadAssessmentMetadata(
        score=assessment.score,
        tier=assessment.tier,
        signals=assessment.signals,
        synopsis=assessment.synopsis,
        recommended_handoff=assessment.recommended_handoff,
    )

    session.response_history.append(result.response)
    if len(session.response_history) > MAX_IDENTICAL_RESPONSES + 2:
        session.response_history = session.response_history[-(MAX_IDENTICAL_RESPONSES + 2) :]
    session.last_mode = result.mode
    return result


def _base_result(
    mode: str,
    response: str,
    session: SessionState,
    handoff: HandoffMetadata,
    lead_intent: Optional[LeadIntentMetadata] = None,
    *,
    grounded: bool = False,
    confidence: float = 0.0,
    sources: Optional[list] = None,
    intake: Optional[dict] = None,
) -> MessageResult:
    return MessageResult(
        mode=mode,
        response=response,
        handoff=handoff,
        lead_intent=lead_intent or LeadIntentMetadata(),
        turn_count=session.turn_count,
        grounded=grounded,
        confidence=confidence,
        sources=sources or [],
        intake=intake or {},
    )


def _handle_answer(
    message: str,
    session: SessionState,
    previous_user_message: str = "",
) -> MessageResult:
    from company_chatbot.grounding import apply_grounding
    from company_chatbot.retrieval import effective_query_for_retrieval, retrieve

    effective = effective_query_for_retrieval(message, previous_user_message)
    grounded = apply_grounding(message, retrieval=retrieve(effective))
    handoff = HandoffMetadata(
        applicable=True,
        primary=config.HANDOFF_PRIMARY_WIDGET,
        secondary=config.HANDOFF_SECONDARY_CONTACT,
        handoff_type="contact" if not grounded.success else None,
    )
    return _base_result(
        config.MODE_ANSWER,
        grounded.response,
        session,
        handoff,
        LeadIntentMetadata(signals=["product_interest"]),
        grounded=grounded.success,
        confidence=grounded.confidence,
        sources=grounded.sources,
    )


def _handle_contact(message: str, session: SessionState) -> MessageResult:
    _ = message
    return _base_result(
        config.MODE_CONTACT,
        "You can reach us at info@fikirisolutions.com or use our contact page. "
        "An in-widget form will be available in a later release.",
        session,
        HandoffMetadata(
            applicable=True,
            primary=config.HANDOFF_PRIMARY_WIDGET,
            secondary=config.HANDOFF_SECONDARY_CONTACT,
            handoff_type="contact",
        ),
        LeadIntentMetadata(signals=["contact_request"], capture_ready=False),
    )


def _handle_fallback(
    message: str,
    session: SessionState,
    previous_user_message: str = "",
) -> MessageResult:
    from company_chatbot.capabilities import compose_capability_bridge, detect_needs
    from company_chatbot.conversational import conversational_reply
    from company_chatbot.retrieval import effective_query_for_retrieval, retrieve

    casual = conversational_reply(message)
    if casual:
        return _base_result(
            config.MODE_FALLBACK,
            casual,
            session,
            HandoffMetadata(applicable=False),
        )

    effective = effective_query_for_retrieval(message, previous_user_message or None)
    needs = detect_needs(message, previous_query=previous_user_message or None, effective_query=effective)
    if needs.detected_families and needs.confidence >= 0.35:
        retrieval = retrieve(effective, previous_query=previous_user_message or None)
        response = compose_capability_bridge(needs, retrieval.chunks[:2])
        return _base_result(
            config.MODE_ANSWER,
            response,
            session,
            HandoffMetadata(
                applicable=True,
                primary=config.HANDOFF_PRIMARY_WIDGET,
                secondary=config.HANDOFF_SECONDARY_INTAKE,
                handoff_type="intake",
            ),
            LeadIntentMetadata(signals=["needs_rescue", "product_interest"]),
            grounded=True,
            confidence=needs.confidence,
            sources=[{"chunk_id": c.id, "topic": c.topic} for c in retrieval.chunks[:2]],
        )

    response = (
        "I'm not sure I understood. You can ask about Fikiri's product, explore whether we're a fit, "
        "request a workflow audit, or ask to contact our team."
    )
    return _base_result(
        config.MODE_FALLBACK,
        response,
        session,
        HandoffMetadata(
            applicable=True,
            primary=config.HANDOFF_PRIMARY_WIDGET,
            secondary=config.HANDOFF_SECONDARY_INTAKE,
            handoff_type="intake",
        ),
        LeadIntentMetadata(signals=["fallback_clarify"]),
    )


_HANDLERS = {
    config.MODE_ANSWER: _handle_answer,
    config.MODE_CONTACT: _handle_contact,
    config.MODE_FALLBACK: _handle_fallback,
}
