"""Request/response shapes for the Fikiri site bot."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HandoffMetadata:
    applicable: bool = False
    primary: Optional[str] = None
    secondary: Optional[str] = None
    handoff_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeadIntentMetadata:
    """Phase 1 schema only — persistence comes in a later phase."""

    capture_ready: bool = False
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeadAssessmentMetadata:
    score: int = 0
    tier: str = "casual"
    signals: List[str] = field(default_factory=list)
    synopsis: str = ""
    recommended_handoff: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MessageResult:
    mode: str
    response: str
    handoff: HandoffMetadata
    lead_intent: LeadIntentMetadata
    turn_count: int
    grounded: bool = False
    confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)
    intake: Dict[str, Any] = field(default_factory=dict)
    lead_assessment: LeadAssessmentMetadata = field(default_factory=LeadAssessmentMetadata)

    def to_dict(self, schema_version: str) -> Dict[str, Any]:
        payload = {
            "schema_version": schema_version,
            "mode": self.mode,
            "response": self.response,
            "handoff": self.handoff.to_dict(),
            "lead_intent": self.lead_intent.to_dict(),
            "lead_assessment": self.lead_assessment.to_dict(),
            "turn_count": self.turn_count,
            "grounded": self.grounded,
            "confidence": self.confidence,
            "sources": self.sources,
        }
        if self.intake:
            payload["intake"] = self.intake
        return payload


@dataclass
class SessionStartResult:
    session_id: str
    welcome: str

    def to_dict(self, schema_version: str) -> Dict[str, Any]:
        return {
            "schema_version": schema_version,
            "session_id": self.session_id,
            "welcome": self.welcome,
        }
