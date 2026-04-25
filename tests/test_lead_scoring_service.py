"""Tests for rule-based CRM lead scoring (weighted average of 0–100 components)."""

import os
import unittest
from unittest.mock import patch

from core.lead_scoring_service import LeadScoringService, DEFAULT_WEIGHTS


class TestLeadScoringService(unittest.TestCase):
    def test_weights_sum_to_one_after_env_override(self):
        raw = '{"identity": 2, "intent": 2, "icp_match": 2, "engagement": 2, "lifecycle_modifier": 2}'
        with patch.dict(os.environ, {"LEAD_SCORING_WEIGHTS": raw}):
            svc = LeadScoringService()
        s = sum(svc.weights.values())
        self.assertAlmostEqual(s, 1.0, places=6)

    def test_score_stays_within_0_100(self):
        svc = LeadScoringService()
        lead = {
            "source": "referral",
            "stage": "qualified",
            "email": "a@b.co",
            "name": "A",
            "company": "C",
            "phone": "1",
            "created_at": "2099-01-01T00:00:00",
        }
        r = svc.score_lead(lead, activity_count=10, last_activity=None)
        self.assertGreaterEqual(r.score, 0)
        self.assertLessEqual(r.score, 100)

    def test_booked_stage_high_score_component(self):
        svc = LeadScoringService()
        base = {
            "source": "manual",
            "email": "x@y.z",
            "name": "N",
            "created_at": "2099-01-01T00:00:00",
            "metadata": {"subject": "intro"},
        }
        new_r = svc.score_lead({**base, "stage": "new"}, 0, None)
        booked_r = svc.score_lead({**base, "stage": "booked"}, 0, None)
        self.assertGreater(
            booked_r.breakdown.get("lifecycle_modifier", 0),
            new_r.breakdown.get("lifecycle_modifier", 0),
        )
        self.assertGreaterEqual(booked_r.score, new_r.score)

    def test_intent_keywords_raise_score(self):
        svc = LeadScoringService()
        base = {
            "source": "gmail",
            "email": "contact@acme.com",
            "name": "Buyer",
            "company": "Acme",
            "created_at": "2099-01-01T00:00:00",
        }
        low = svc.score_lead({**base, "metadata": {"subject": "hello"}}, 0, None)
        high = svc.score_lead(
            {**base, "metadata": {"subject": "demo proposal pricing contract meeting this week"}},
            0,
            None,
        )
        self.assertGreater(high.score, low.score)

    def test_default_weights_unchanged_sum(self):
        svc = LeadScoringService()
        self.assertAlmostEqual(sum(svc.weights.values()), 1.0, places=6)
        self.assertEqual(svc.weights, DEFAULT_WEIGHTS)


if __name__ == "__main__":
    unittest.main()
