#!/usr/bin/env python3
"""
Fikiri Solutions - ML Scoring Service (Canonical)
Lightweight ML scoring for CRM lead prioritization with production enhancements.
"""

import asyncio
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MinimalMLScoring:
    """Minimal ML scoring service with production enhancements."""

    def __init__(self, services: Dict[str, Any] = None):
        self.services = services or {}
        self.scoring_model = None
        self.feature_weights = {
            "email_domain_score": 0.2,
            "response_time_score": 0.15,
            "email_length_score": 0.1,
            "keyword_score": 0.25,
            "contact_frequency_score": 0.15,
            "time_of_day_score": 0.1,
            "subject_score": 0.05,
        }
        self.keywords = {
            "high_value": ["urgent", "immediately", "asap", "budget", "purchase", "buy", "contract", "proposal"],
            "medium_value": ["interested", "information", "quote", "price", "service", "help"],
            "low_value": ["unsubscribe", "spam", "test", "hello", "hi"],
        }
        self.redis_client = None
        self._initialize_redis()
        self.db_optimizer = None
        self._initialize_database()
        self.vector_search = None
        self._initialize_vector_search()
        self._ml_models_initialized = False
        self.scoring_model = None
        self.scaler = None
        self.model_type = "rule_based"
        self.calibration_data = []
        self._load_calibration_data()

    def _initialize_redis(self):
        try:
            from core.redis_connection_helper import get_redis_client
            self.redis_client = get_redis_client(decode_responses=True, db=int(os.getenv('REDIS_DB', 0)))
        except Exception:
            self.redis_client = None

    def _initialize_database(self):
        try:
            from core.database_optimization import db_optimizer
            self.db_optimizer = db_optimizer
        except Exception:
            self.db_optimizer = None

    def _initialize_vector_search(self):
        try:
            if 'vector_search' in self.services:
                self.vector_search = self.services['vector_search']
        except Exception:
            self.vector_search = None

    def _ensure_ml_models_initialized(self):
        if self._ml_models_initialized:
            return
        self._ml_models_initialized = True
        try:
            self._initialize_ml_models()
        except Exception:
            self.scoring_model = None
            self.scaler = None
            self.model_type = "rule_based"

    def _initialize_ml_models(self):
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            self.scoring_model = LogisticRegression(random_state=42)
            self.scaler = StandardScaler()
            self.model_type = "logistic_regression"
        except ImportError:
            try:
                import xgboost as xgb
                self.scoring_model = xgb.XGBClassifier(random_state=42)
                self.model_type = "xgboost"
            except ImportError:
                self.model_type = "rule_based"
        except Exception:
            self.model_type = "rule_based"

    def _load_calibration_data(self):
        try:
            calibration_file = Path("data/ml_calibration.json")
            if calibration_file.exists():
                with open(calibration_file, 'r') as f:
                    self.calibration_data = json.load(f)
        except Exception:
            self.calibration_data = []

    def _save_calibration_data(self):
        try:
            calibration_file = Path("data/ml_calibration.json")
            calibration_file.parent.mkdir(exist_ok=True)
            with open(calibration_file, 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
        except Exception:
            pass

    def calculate_lead_score(self, email_data: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cache_key = f"ml_score:{hash(str(email_data) + str(lead_data))}"
            if self.redis_client:
                try:
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        return json.loads(cached_result)
                except Exception:
                    pass

            scores = {
                "email_domain_score": self._score_email_domain(lead_data.get("email", "")),
                "response_time_score": self._score_response_time(email_data.get("timestamp")),
            }
            email_content = email_data.get("content", "") + " " + email_data.get("subject", "")
            scores["email_length_score"] = self._score_email_length(email_content)
            scores["keyword_score"] = self._score_keywords(email_content)
            scores["subject_score"] = self._score_subject(email_data.get("subject", ""))
            scores["contact_frequency_score"] = self._score_contact_frequency(lead_data.get("contact_count", 0))
            scores["time_of_day_score"] = self._score_time_of_day(email_data.get("timestamp"))
            if self.vector_search:
                scores["semantic_similarity_score"] = self._score_semantic_similarity(email_content)

            self._ensure_ml_models_initialized()
            if self.model_type != "rule_based" and self.scoring_model:
                total_score = self._predict_with_ml_model(scores)
            else:
                total_score = sum(score * self.feature_weights.get(feature, 0) for feature, score in scores.items())
            priority = self._determine_priority(total_score)
            result = {
                "total_score": round(total_score, 2),
                "priority": priority,
                "individual_scores": scores,
                "recommended_action": self._get_recommended_action(priority),
                "confidence": self._calculate_confidence(scores),
                "model_type": self.model_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, 3600, json.dumps(result))
                except Exception:
                    pass
            self._track_scoring_result(result, email_data, lead_data)
            return result
        except Exception:
            return self._default_score()

    def _predict_with_ml_model(self, scores: Dict[str, float]) -> float:
        try:
            feature_vector = [scores.get(feature, 0) for feature in self.feature_weights.keys()]
            if hasattr(self.scoring_model, 'predict_proba'):
                probabilities = self.scoring_model.predict_proba([feature_vector])[0]
                return probabilities[1] if len(probabilities) > 1 else probabilities[0]
            return self.scoring_model.predict([feature_vector])[0]
        except Exception:
            return sum(score * self.feature_weights.get(feature, 0) for feature, score in scores.items())

    def _score_semantic_similarity(self, content: str) -> float:
        try:
            if not self.vector_search:
                return 0.5
            results = self.vector_search.search_similar(content, top_k=3, threshold=0.6)
            if not results:
                return 0.5
            avg_similarity = sum(result['similarity'] for result in results) / len(results)
            high_value_boost = 0.0
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('lead_value') == 'high':
                    high_value_boost += 0.2
            return min(1.0, avg_similarity + high_value_boost)
        except Exception:
            return 0.5

    def _track_scoring_result(self, result: Dict[str, Any], email_data: Dict[str, Any], lead_data: Dict[str, Any]):
        try:
            tracking_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email_content": email_data.get("content", "")[:200],
                "email_subject": email_data.get("subject", ""),
                "lead_email": lead_data.get("email", ""),
                "predicted_score": result["total_score"],
                "predicted_priority": result["priority"],
                "individual_scores": result["individual_scores"],
                "model_type": result["model_type"],
            }
            self.calibration_data.append(tracking_data)
            if len(self.calibration_data) > 1000:
                self.calibration_data = self.calibration_data[-1000:]
            if self.db_optimizer:
                try:
                    self.db_optimizer.execute_query("""
                        INSERT INTO ml_scoring_log
                        (timestamp, email_content, email_subject, lead_email, predicted_score,
                         predicted_priority, individual_scores, model_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tracking_data["timestamp"],
                        tracking_data["email_content"],
                        tracking_data["email_subject"],
                        tracking_data["lead_email"],
                        tracking_data["predicted_score"],
                        tracking_data["predicted_priority"],
                        json.dumps(tracking_data["individual_scores"]),
                        tracking_data["model_type"],
                    ), fetch=False)
                except Exception:
                    pass
        except Exception:
            pass

    def update_model_from_feedback(self, lead_id: str, actual_outcome: str, predicted_score: float):
        try:
            feedback_data = {
                "lead_id": lead_id,
                "actual_outcome": actual_outcome,
                "predicted_score": predicted_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if self.db_optimizer:
                self.db_optimizer.execute_query("""
                    INSERT INTO ml_feedback_log
                    (lead_id, actual_outcome, predicted_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    feedback_data["lead_id"],
                    feedback_data["actual_outcome"],
                    feedback_data["predicted_score"],
                    feedback_data["timestamp"],
                ), fetch=False)
            self.calibration_data.append(feedback_data)
            if len(self.calibration_data) >= 100:
                self._retrain_model()
        except Exception:
            pass

    def _retrain_model(self):
        try:
            if self.model_type == "rule_based" or not self.scoring_model:
                return
            x_train: List[List[float]] = []
            y_train: List[int] = []
            for record in self.calibration_data[-500:]:
                if "individual_scores" in record:
                    feature_vector = [record["individual_scores"].get(feature, 0) for feature in self.feature_weights.keys()]
                    x_train.append(feature_vector)
                    outcome = record.get("actual_outcome", "")
                    y_train.append(1 if outcome in ["won", "qualified"] else 0)
            if len(x_train) < 10:
                return
            if hasattr(self.scoring_model, 'fit'):
                self.scoring_model.fit(x_train, y_train)
        except Exception:
            pass

    def _score_email_domain(self, email: str) -> float:
        if not email or "@" not in email:
            return 0.0
        domain = email.split("@")[1].lower()
        if any(high_domain in domain for high_domain in ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]):
            return 0.8
        if domain.endswith(".edu"):
            return 0.9
        if domain.endswith(".gov"):
            return 0.95
        if domain.endswith(".org"):
            return 0.7
        if domain.endswith(".com"):
            return 0.6
        return 0.4

    def _score_response_time(self, timestamp: str) -> float:
        if not timestamp:
            return 0.5
        try:
            email_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_diff = (now - email_time).total_seconds() / 3600
            if time_diff < 1:
                return 1.0
            if time_diff < 4:
                return 0.8
            if time_diff < 24:
                return 0.6
            if time_diff < 72:
                return 0.4
            return 0.2
        except Exception:
            return 0.5

    def _score_email_length(self, content: str) -> float:
        length = len(content)
        if 50 <= length <= 500:
            return 1.0
        if 20 <= length < 50:
            return 0.7
        if 500 < length <= 1000:
            return 0.8
        if length > 1000:
            return 0.6
        return 0.3

    def _score_keywords(self, content: str) -> float:
        content_lower = content.lower()
        high_score = sum(1 for keyword in self.keywords["high_value"] if keyword in content_lower)
        medium_score = sum(1 for keyword in self.keywords["medium_value"] if keyword in content_lower)
        low_score = sum(1 for keyword in self.keywords["low_value"] if keyword in content_lower)
        total_score = (high_score * 1.0) + (medium_score * 0.6) + (low_score * -0.3)
        return max(0.0, min(1.0, total_score / 3.0 + 0.5))

    def _score_subject(self, subject: str) -> float:
        if not subject:
            return 0.3
        subject_lower = subject.lower()
        if any(word in subject_lower for word in ["urgent", "important", "asap", "help"]):
            return 0.9
        if any(word in subject_lower for word in ["question", "inquiry", "information"]):
            return 0.7
        if len(subject) > 10 and not subject_lower.startswith("re:"):
            return 0.6
        return 0.4

    def _score_contact_frequency(self, contact_count: int) -> float:
        if contact_count == 0:
            return 0.5
        if contact_count == 1:
            return 0.8
        if 2 <= contact_count <= 3:
            return 0.6
        if contact_count > 3:
            return 0.3
        return 0.5

    def _score_time_of_day(self, timestamp: str) -> float:
        if not timestamp:
            return 0.5
        try:
            email_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = email_time.hour
            if 9 <= hour <= 17:
                return 1.0
            if 8 <= hour <= 18:
                return 0.8
            if 7 <= hour <= 19:
                return 0.6
            return 0.4
        except Exception:
            return 0.5

    def _determine_priority(self, total_score: float) -> str:
        if total_score >= 0.8:
            return "high"
        if total_score >= 0.6:
            return "medium"
        if total_score >= 0.4:
            return "low"
        return "very_low"

    def _get_recommended_action(self, priority: str) -> str:
        if priority == "high":
            return "immediate_response"
        if priority == "medium":
            return "respond_within_4_hours"
        if priority == "low":
            return "respond_within_24_hours"
        return "respond_when_convenient"

    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        variance = sum((score - 0.5) ** 2 for score in scores.values()) / len(scores)
        confidence = min(1.0, variance * 4)
        return round(confidence, 2)

    def _default_score(self) -> Dict[str, Any]:
        return {
            "total_score": 0.5,
            "priority": "medium",
            "individual_scores": {},
            "recommended_action": "respond_within_24_hours",
            "confidence": 0.0,
            "model_type": self.model_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def batch_score_leads(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored_leads = []
        for lead_data in leads_data:
            email_data = lead_data.get("last_email", {})
            score_result = self.calculate_lead_score(email_data, lead_data)
            scored_lead = {
                **lead_data,
                "ml_score": score_result["total_score"],
                "priority": score_result["priority"],
                "recommended_action": score_result["recommended_action"],
                "confidence": score_result["confidence"],
                "model_type": score_result["model_type"],
                "scored_at": score_result["timestamp"],
            }
            scored_leads.append(scored_lead)
        scored_leads.sort(key=lambda x: x["ml_score"], reverse=True)
        return scored_leads

    async def batch_score_leads_async(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch_score_leads, leads_data)

    def get_scoring_stats(self) -> Dict[str, Any]:
        stats = {
            "feature_weights": self.feature_weights,
            "keywords": self.keywords,
            "model_loaded": self.scoring_model is not None,
            "model_type": self.model_type,
            "redis_available": self.redis_client is not None,
            "vector_search_available": self.vector_search is not None,
            "calibration_records": len(self.calibration_data),
            "database_available": self.db_optimizer is not None,
        }
        if self.scoring_model:
            stats["model_trained"] = hasattr(self.scoring_model, 'fit')
        return stats

    def get_calibration_accuracy(self) -> Dict[str, Any]:
        try:
            if len(self.calibration_data) < 10:
                return {"error": "Insufficient calibration data"}
            total_predictions = len(self.calibration_data)
            correct_predictions = 0
            for record in self.calibration_data:
                predicted_score = record.get("predicted_score", 0)
                actual_outcome = record.get("actual_outcome", "")
                if predicted_score >= 0.7 and actual_outcome in ["won", "qualified"]:
                    correct_predictions += 1
                elif predicted_score < 0.7 and actual_outcome in ["lost", "unqualified"]:
                    correct_predictions += 1
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            return {
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "accuracy": round(accuracy, 3),
                "model_type": self.model_type,
            }
        except Exception as e:
            return {"error": str(e)}


def create_ml_scorer(services: Dict[str, Any] = None) -> MinimalMLScoring:
    return MinimalMLScoring(services)

