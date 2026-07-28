"""Inline routing trace for the Fikiri site bot (observability only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

ROUTING_TRACE_SCHEMA_VERSION = "v1"


@dataclass
class GuardTrace:
    attempted: bool = False
    triggered: bool = False
    reason: Optional[str] = None


@dataclass
class ModeTrace:
    attempted: bool = False
    detected: Optional[str] = None
    matched_rule: Optional[str] = None
    previous_query_used: bool = False


@dataclass
class OutcomeTrace:
    mode: Optional[str] = None
    grounded: Optional[bool] = None
    confidence: Optional[float] = None


@dataclass
class RoutingTrace:
    schema_version: str = ROUTING_TRACE_SCHEMA_VERSION
    path: List[str] = field(default_factory=list)
    guard: GuardTrace = field(default_factory=GuardTrace)
    mode: ModeTrace = field(default_factory=ModeTrace)
    outcome: OutcomeTrace = field(default_factory=OutcomeTrace)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "path": list(self.path),
            "guard": asdict(self.guard),
            "mode": asdict(self.mode),
            "outcome": asdict(self.outcome),
        }


def record_guard(trace: RoutingTrace, *, triggered: bool, reason: Optional[str]) -> None:
    trace.path.append("guard")
    trace.guard = GuardTrace(attempted=True, triggered=triggered, reason=reason)


def record_mode(
    trace: RoutingTrace,
    *,
    detected: str,
    matched_rule: Optional[str],
    previous_query_used: bool,
) -> None:
    trace.path.append("mode")
    trace.mode = ModeTrace(
        attempted=True,
        detected=detected,
        matched_rule=matched_rule,
        previous_query_used=previous_query_used,
    )


def record_outcome(
    trace: RoutingTrace,
    *,
    mode: str,
    grounded: bool,
    confidence: float,
) -> None:
    trace.path.append("outcome")
    trace.outcome = OutcomeTrace(mode=mode, grounded=grounded, confidence=confidence)
