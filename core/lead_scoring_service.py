#!/usr/bin/env python3
"""
Lead Scoring Service
Computes lead_score (0-100) and lead_quality (A/B/C/D) with configurable weights.

Technique (Scoring V1.1): deterministic weighted components in [0, 100] with explainable
breakdown fields. This is intentionally rule-based (not ML) so results are stable and
auditable in production.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SCORING_VERSION = "v1.1-deterministic"
LIFECYCLE_MAX_MULTIPLIER_DELTA = 0.10  # lifecycle applies up to +/-10%

DEFAULT_WEIGHTS = {
    "identity": 0.20,
    "intent": 0.30,
    "icp_match": 0.20,
    "engagement": 0.20,
    "lifecycle_modifier": 0.10,
}

LEGACY_WEIGHT_KEY_MAP = {
    "source": "identity",
    "attributes": "intent",
    "recency": "icp_match",
    "engagement": "engagement",
    "stage": "lifecycle_modifier",
}

DEFAULT_SOURCE_SCORES = {
    "referral": 100,
    "partner": 90,
    "gmail": 75,
    "outlook": 70,
    "website": 65,
    "tally": 60,
    "typeform": 60,
    "jotform": 55,
    "manual": 40,
    "webhook": 50,
}

DEFAULT_LIFECYCLE_SCORES = {
    "new": 40,
    "contacted": 55,
    "replied": 65,
    "qualified": 80,
    # CRM pipeline uses "booked" for won deals (see frontend pipeline boards).
    "booked": 95,
    "closed": 95,
}


@dataclass
class LeadScoreResult:
    score: int
    quality: str
    breakdown: Dict[str, Any]


class LeadScoringService:
    def __init__(self):
        self.weights = DEFAULT_WEIGHTS.copy()
        self.source_scores = DEFAULT_SOURCE_SCORES.copy()
        self.lifecycle_scores = DEFAULT_LIFECYCLE_SCORES.copy()
        self._load_config()

    def _normalize_weights(self) -> None:
        """Keep weights as a convex combination so score stays in [0, 100] when all components are."""
        total = sum(self.weights.values())
        if total <= 0:
            logger.warning("LEAD_SCORING_WEIGHTS sum invalid; resetting to defaults")
            self.weights = DEFAULT_WEIGHTS.copy()
            return
        if abs(total - 1.0) > 1e-6:
            for k in self.weights:
                self.weights[k] /= total

    def _load_config(self):
        """Load optional config from env JSON."""
        raw = os.getenv("LEAD_SCORING_WEIGHTS")
        if not raw:
            self._normalize_weights()
            return
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                for k, v in data.items():
                    key = k if k in self.weights else LEGACY_WEIGHT_KEY_MAP.get(k)
                    if key in self.weights:
                        self.weights[key] = float(v)
        except Exception as e:
            logger.warning("Failed to parse LEAD_SCORING_WEIGHTS: %s", e)
        self._normalize_weights()

    def _domain_score(self, email: str) -> int:
        if "@" not in email:
            return 35
        domain = email.split("@", 1)[1].strip().lower()
        if not domain:
            return 35
        if domain in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}:
            return 45
        if domain.endswith(".edu"):
            return 55
        if domain.endswith(".org"):
            return 65
        return 80

    def _collect_text_for_intent(self, lead_data: Dict[str, Any]) -> str:
        metadata = lead_data.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        pieces = [
            str(lead_data.get("notes") or ""),
            str(lead_data.get("subject") or ""),
            str(metadata.get("subject") or ""),
            str(metadata.get("last_email_subject") or ""),
            str(metadata.get("message") or ""),
            str(metadata.get("body") or ""),
            str(metadata.get("last_email_body") or ""),
        ]
        return " ".join(pieces).lower().strip()

    def _intent_score(self, lead_data: Dict[str, Any]) -> int:
        text = self._collect_text_for_intent(lead_data)
        if not text:
            return 35
        score = 40
        high_intent = {
            "demo": 18,
            "proposal": 20,
            "pricing": 16,
            "quote": 14,
            "contract": 20,
            "meeting": 14,
            "budget": 16,
            "timeline": 12,
            "implementation": 12,
            "asap": 8,
            "urgent": 10,
        }
        negative = {
            "unsubscribe": -30,
            "not interested": -24,
            "spam": -20,
            "wrong person": -16,
            "student project": -12,
        }
        for kw, pts in high_intent.items():
            if kw in text:
                score += pts
        for kw, pts in negative.items():
            if kw in text:
                score += pts
        return int(max(0, min(100, score)))

    def _icp_match_score(self, lead_data: Dict[str, Any]) -> int:
        text = self._collect_text_for_intent(lead_data)
        score = 30
        if lead_data.get("company"):
            score += 15
        source = str(lead_data.get("source") or "").lower()
        if source in {"referral", "partner", "website", "typeform", "tally"}:
            score += 10
        configured = os.getenv("LEAD_SCORING_ICP_KEYWORDS", "").strip()
        if configured:
            terms = [t.strip().lower() for t in configured.split(",") if t.strip()]
        else:
            terms = ["automation", "crm", "ai", "workflow", "integration", "inbox", "sales"]
        score += sum(8 for t in terms if t in text)
        return int(max(0, min(100, score)))

    def _engagement_score(
        self,
        lead_data: Dict[str, Any],
        activity_count: int,
        last_activity: Optional[datetime],
        now: datetime,
    ) -> int:
        score = min(activity_count * 10, 60)
        if last_activity:
            delta_days = max((now - last_activity).days, 0)
            score += max(0, 40 - min(delta_days, 30) * 1.3)
        created_at = lead_data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = None
        if created_at:
            age_days = max((now - created_at).days, 0)
            score += max(0, 20 - min(age_days, 40) * 0.5)
        return int(max(0, min(100, score)))

    def score_lead(
        self,
        lead_data: Dict[str, Any],
        activity_count: int = 0,
        last_activity: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> LeadScoreResult:
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        source = (lead_data.get("source") or "").lower()
        source_score = self.source_scores.get(source, 50)
        identity_score = int(round((source_score * 0.55) + (self._domain_score(str(lead_data.get("email") or "")) * 0.45), 0))
        intent_score = self._intent_score(lead_data)
        icp_match_score = self._icp_match_score(lead_data)
        engagement_score = self._engagement_score(lead_data, activity_count, last_activity, now)
        stage = (lead_data.get("stage") or "new").lower()
        lifecycle_score = self.lifecycle_scores.get(stage, 40)

        base_weighted = (
            identity_score * self.weights["identity"]
            + intent_score * self.weights["intent"]
            + icp_match_score * self.weights["icp_match"]
            + engagement_score * self.weights["engagement"]
        )
        lifecycle_centered = (lifecycle_score - 50) / 50.0
        lifecycle_factor = 1.0 + (self.weights["lifecycle_modifier"] * LIFECYCLE_MAX_MULTIPLIER_DELTA * lifecycle_centered)
        weighted = base_weighted * lifecycle_factor

        score = int(round(max(0.0, min(100.0, weighted)), 0))
        quality = self._quality_from_score(score)

        breakdown = {
            "version": SCORING_VERSION,
            "identity": identity_score,
            "intent": intent_score,
            "icp_match": icp_match_score,
            "engagement": engagement_score,
            "lifecycle_modifier": lifecycle_score,
            "weights": self.weights,
            "lifecycle_factor": round(lifecycle_factor, 4),
            "base_weighted_score": round(base_weighted, 2),
        }

        return LeadScoreResult(score=score, quality=quality, breakdown=breakdown)

    def _quality_from_score(self, score: int) -> str:
        if score >= 80:
            return "A"
        if score >= 60:
            return "B"
        if score >= 40:
            return "C"
        return "D"

    def quality_from_score(self, score: int) -> str:
        return self._quality_from_score(score)


lead_scoring_service = LeadScoringService()


def get_lead_scoring_service() -> LeadScoringService:
    return lead_scoring_service
