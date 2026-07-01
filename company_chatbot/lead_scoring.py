"""Deterministic lead assessment for the Fikiri site bot (no LLM, no CRM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from company_chatbot import config
from company_chatbot.intake import INTAKE_MODES, IntakeSlots, filled_core_count, slot_satisfied
from company_chatbot.schemas import HandoffMetadata

SIGNAL_WEIGHTS: Dict[str, int] = {
    "business_context": 2,
    "workflow_pain": 2,
    "pricing_interest": 1,
    "timeline": 1,
    "contact_email": 3,
    "automation_keyword": 1,
    "crm_keyword": 1,
    "website_keyword": 1,
    "payments_keyword": 1,
    "urgent_language": 2,
    "needs_detected": 2,
    "bundle_suggested": 1,
}

_KEYWORD_SIGNALS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("automation_keyword", re.compile(r"\b(automat(e|ion|ing)|workflow)\b", re.I)),
    ("crm_keyword", re.compile(r"\b(crm|pipeline|leads?)\b", re.I)),
    ("website_keyword", re.compile(r"\b(website|web\s*site|landing\s*page)\b", re.I)),
    ("payments_keyword", re.compile(r"\b(payment|stripe|invoice|billing)\b", re.I)),
    ("urgent_language", re.compile(r"\b(urgent|asap|immediately|right away|this week)\b", re.I)),
    ("workflow_pain", re.compile(r"\b(bottleneck|missed leads?|manual|slow|overwhelm)\b", re.I)),
    ("pricing_interest", re.compile(r"\b(pricing|price|cost|how much)\b", re.I)),
)

_MODE_SIGNALS: Dict[str, List[str]] = {
    config.MODE_EXPLORE_FIT: ["business_context"],
    config.MODE_WORKFLOW_AUDIT: ["workflow_pain"],
    config.MODE_CONSULTING: ["business_context", "workflow_pain"],
    config.MODE_CONTACT: ["business_context"],
    config.MODE_ANSWER: [],
}


@dataclass
class LeadAssessment:
    score: int = 0
    tier: str = "casual"
    signals: List[str] = field(default_factory=list)
    synopsis: str = ""
    recommended_handoff: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "score": self.score,
            "tier": self.tier,
            "signals": list(self.signals),
            "synopsis": self.synopsis,
            "recommended_handoff": self.recommended_handoff,
        }


def score_to_tier(score: int) -> str:
    if score >= 9:
        return "hot"
    if score >= 6:
        return "warm"
    if score >= 3:
        return "possible"
    return "casual"


def _unique_signals(signals: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for signal in signals:
        if signal not in seen:
            seen.add(signal)
            ordered.append(signal)
    return ordered


def detect_message_signals(message: str) -> List[str]:
    text = (message or "").strip()
    if not text:
        return []
    found: List[str] = []
    for name, pattern in _KEYWORD_SIGNALS:
        if pattern.search(text):
            found.append(name)
    return found


def detect_slot_signals(slots: IntakeSlots) -> List[str]:
    found: List[str] = []
    if slots.industry or slots.business_name:
        found.append("business_context")
    if slots.main_pain:
        found.append("workflow_pain")
    if slots.timeline:
        found.append("timeline")
    if slots.contact_email:
        found.append("contact_email")
    return found


def compute_score(signals: List[str]) -> int:
    return sum(SIGNAL_WEIGHTS.get(signal, 0) for signal in signals)


def recommend_handoff(
    *,
    tier: str,
    mode: str,
    handoff: HandoffMetadata,
    intake_complete: bool,
) -> Optional[str]:
    if mode == config.MODE_CONTACT:
        return config.HANDOFF_SECONDARY_CONTACT
    if handoff.handoff_type == "contact" and handoff.secondary:
        return handoff.secondary
    if mode in INTAKE_MODES and not intake_complete:
        return config.HANDOFF_SECONDARY_INTAKE
    if intake_complete and handoff.secondary:
        return handoff.secondary
    if tier in ("warm", "hot"):
        return config.HANDOFF_SECONDARY_INTAKE
    if handoff.applicable and handoff.secondary:
        return handoff.secondary
    return None


def build_qualification_synopsis(
    needs: Optional["NeedsDetectionResult"],
    message: str,
    signals: List[str],
) -> str:
    """Sales-ready synopsis from capability needs, keyword signals, and the visitor quote."""
    from company_chatbot.capabilities import _cached_map

    parts: List[str] = []
    if needs and needs.detected_families:
        cmap = _cached_map()
        labels = [
            cmap.families[fid].label
            for fid in needs.detected_families[:4]
            if fid in cmap.families
        ]
        if labels:
            parts.append(f"Interested in {', '.join(labels)}")
        if needs.suggested_bundle_label:
            parts.append(f"closest fit: {needs.suggested_bundle_label}")
        if needs.detected_capabilities:
            parts.append(f"likely needs: {', '.join(needs.detected_capabilities[:4])}")

    if not parts:
        signal_labels: List[str] = []
        if "crm_keyword" in signals:
            signal_labels.append("CRM or lead tracking")
        if "website_keyword" in signals:
            signal_labels.append("website or web presence")
        if "payments_keyword" in signals:
            signal_labels.append("payments or billing")
        if "automation_keyword" in signals:
            signal_labels.append("automation or workflows")
        if "workflow_pain" in signals:
            signal_labels.append("workflow or follow-up pain")
        if "pricing_interest" in signals:
            signal_labels.append("pricing")
        if signal_labels:
            parts.append(f"Visitor mentioned {', '.join(signal_labels)}")

    excerpt = (message or "").strip()[:140]
    if excerpt and (parts or len(excerpt) > 12):
        parts.append(f'Quoted: "{excerpt}"')

    if not parts:
        return ""

    return ". ".join(parts) + ("." if not parts[-1].endswith(".") else "")


def build_synopsis(
    slots: IntakeSlots,
    signals: List[str],
    tier: str,
    *,
    message: str = "",
    needs_synopsis: str = "",
) -> str:
    if needs_synopsis:
        slot_part = _build_slot_synopsis(slots, signals, tier)
        if slot_part and "not provided enough" not in slot_part.lower():
            return f"{needs_synopsis} {slot_part}"[:320]
        return needs_synopsis[:320]

    return _build_slot_synopsis(slots, signals, tier)


def _build_slot_synopsis(slots: IntakeSlots, signals: List[str], tier: str) -> str:
    if tier == "casual" and not any(
        slot_satisfied(slots, s) for s in ("industry", "main_pain", "timeline", "contact_email")
    ):
        if not signals or signals == ["pricing_interest"]:
            return "Visitor has not provided enough business context yet."

    parts: List[str] = []
    if slots.industry:
        parts.append(f"{slots.industry} business")
    elif "business_context" in signals:
        parts.append("Business context mentioned")

    if slots.main_pain:
        pain = slots.main_pain[:80].rstrip(".")
        parts.append(f"looking to address {pain.lower()}")
    elif "workflow_pain" in signals:
        parts.append("workflow or lead-handling pain mentioned")

    if slots.timeline:
        parts.append(f"timeline noted as {slots.timeline}")
    elif "urgent_language" in signals or "timeline" in signals:
        parts.append("timeline appears soon")

    if slots.contact_email:
        parts.append("contact email provided")

    if not parts:
        if "pricing_interest" in signals:
            return "Visitor asked about pricing; business context not yet captured."
        return "Visitor has not provided enough business context yet."

    sentence = parts[0].capitalize() if parts else ""
    if len(parts) > 1:
        sentence = f"{sentence} {', '.join(parts[1:])}."
    elif not sentence.endswith("."):
        sentence = f"{sentence}."
    return sentence[:320]


def assess_lead(
    *,
    message: str,
    mode: str,
    slots: IntakeSlots,
    handoff: HandoffMetadata,
    grounded: bool = False,
    turn_count: int = 0,
    intake_complete: bool = False,
    previous_message: str = "",
) -> LeadAssessment:
    from company_chatbot.capabilities import detect_needs

    needs = detect_needs(message, previous_query=previous_message or None)
    signals = _unique_signals(
        detect_message_signals(message)
        + detect_slot_signals(slots)
        + _MODE_SIGNALS.get(mode, [])
    )
    if needs.detected_families:
        signals.append("needs_detected")
    if needs.suggested_bundle:
        signals.append("bundle_suggested")

    needs_synopsis = build_qualification_synopsis(needs, message, signals)

    score = compute_score(signals)
    if needs.detected_families:
        score += 1
    if needs.suggested_bundle:
        score += 1
    if mode in INTAKE_MODES and not intake_complete:
        score += 1
    if intake_complete:
        score += 2
    if filled_core_count(slots) >= 2:
        score += 1
    if grounded:
        score += 0  # visible in response metadata; no score inflation

    tier = score_to_tier(score)
    synopsis = build_synopsis(
        slots,
        signals,
        tier,
        message=message,
        needs_synopsis=needs_synopsis,
    )
    recommended = recommend_handoff(
        tier=tier,
        mode=mode,
        handoff=handoff,
        intake_complete=intake_complete,
    )

    return LeadAssessment(
        score=score,
        tier=tier,
        signals=signals,
        synopsis=synopsis,
        recommended_handoff=recommended,
    )
