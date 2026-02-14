#!/usr/bin/env python3
"""
Lead Scoring Service
Computes lead_score (0-100) and lead_quality label with configurable weights.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "source": 0.25,
    "recency": 0.20,
    "stage": 0.20,
    "engagement": 0.20,
    "attributes": 0.15,
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

DEFAULT_STAGE_SCORES = {
    "new": 40,
    "contacted": 55,
    "replied": 65,
    "qualified": 80,
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
        self.stage_scores = DEFAULT_STAGE_SCORES.copy()
        self._load_config()

    def _load_config(self):
        """Load optional config from env JSON."""
        raw = os.getenv("LEAD_SCORING_WEIGHTS")
        if not raw:
            return
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                self.weights.update({k: float(v) for k, v in data.items() if k in self.weights})
        except Exception as e:
            logger.warning("Failed to parse LEAD_SCORING_WEIGHTS: %s", e)

    def score_lead(
        self,
        lead_data: Dict[str, Any],
        activity_count: int = 0,
        last_activity: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> LeadScoreResult:
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)

        # Source score
        source = (lead_data.get("source") or "").lower()
        source_score = self.source_scores.get(source, 50)

        # Recency score (newer is better)
        created_at = lead_data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = None
        if created_at:
            age_days = max((now - created_at).days, 0)
        else:
            age_days = 30
        recency_score = max(0, 100 - min(age_days, 60) * 1.5)

        # Stage score
        stage = (lead_data.get("stage") or "new").lower()
        stage_score = self.stage_scores.get(stage, 40)

        # Engagement score (activity count + recency of last activity)
        engagement_score = min(activity_count * 10, 60)
        if last_activity:
            delta_days = max((now - last_activity).days, 0)
            engagement_score += max(0, 40 - min(delta_days, 30) * 1.3)
        engagement_score = min(engagement_score, 100)

        # Attribute score
        attributes_score = 0
        if lead_data.get("company"):
            attributes_score += 30
        if lead_data.get("phone"):
            attributes_score += 25
        if lead_data.get("email") and "@" in lead_data.get("email"):
            attributes_score += 25
        if lead_data.get("name"):
            attributes_score += 20
        attributes_score = min(attributes_score, 100)

        weighted = (
            source_score * self.weights["source"]
            + recency_score * self.weights["recency"]
            + stage_score * self.weights["stage"]
            + engagement_score * self.weights["engagement"]
            + attributes_score * self.weights["attributes"]
        )

        score = int(round(max(0, min(100, weighted)), 0))
        quality = self._quality_from_score(score)

        breakdown = {
            "source": source_score,
            "recency": recency_score,
            "stage": stage_score,
            "engagement": engagement_score,
            "attributes": attributes_score,
            "weights": self.weights,
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
