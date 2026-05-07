#!/usr/bin/env python3
"""Canonical launch-gate thresholds for inbound email triage evaluation."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class EmailTriageEvalThresholds:
    """Thresholds used to decide if the use case is launch-ready."""

    intent_macro_f1_min: float = 0.88
    urgency_macro_f1_min: float = 0.85
    schema_valid_rate_min: float = 0.99
    unsafe_recommendation_rate_max: float = 0.005
    p95_latency_ms_max: float = 5000.0
    cost_per_request_max: float = 0.02

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

