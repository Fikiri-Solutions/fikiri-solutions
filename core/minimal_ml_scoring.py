#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal ML Scoring Service
Lightweight ML scoring for CRM lead prioritization with production enhancements.
"""

import json
import math
import logging
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

class MinimalMLScoring:
    """Minimal ML scoring service with production enhancements."""
    
    def __init__(self, services: Dict[str, Any] = None):
        """Initialize ML scoring service with enhanced features."""
        self.services = services or {}
        self.scoring_model = None
        self.feature_weights = {
            "email_domain_score": 0.2,
            "response_time_score": 0.15,
            "email_length_score": 0.1,
            "keyword_score": 0.25,
            "contact_frequency_score": 0.15,
            "time_of_day_score": 0.1,
            "subject_score": 0.05
        }
        self.keywords = {
            "high_value": ["urgent", "immediately", "asap", "budget", "purchase", "buy", "contract", "proposal"],
            "medium_value": ["interested", "information", "quote", "price", "service", "help"],
            "low_value": ["unsubscribe", "spam", "test", "hello", "hi"]
        }
        
        # Redis client for caching
        self.redis_client = None
        self._initialize_redis()
        
        # Database optimizer for historical tracking
        self.db_optimizer = None
        self._initialize_database()
        
        # Vector search for hybrid ranking
        self.vector_search = None
        self._initialize_vector_search()
        
        # Initialize ML models
        self._initialize_ml_models()
        
        # Historical calibration data
        self.calibration_data = []
        self._load_calibration_data()
    
    def _initialize_redis(self):
        """Initialize Redis client for caching."""
        try:
            from core.redis_connection_helper import get_redis_client
            self.redis_client = get_redis_client(decode_responses=True, db=int(os.getenv('REDIS_DB', 0)))
            if self.redis_client:
                logger.info("✅ Redis initialized for ML scoring cache")
            else:
                logger.info("ℹ️ Redis not available for ML scoring cache (using database fallback)")
        except Exception as e:
            logger.info(f"ℹ️ Redis not available for ML scoring cache: {e}")
            self.redis_client = None
    
    def _initialize_database(self):
        """Initialize database for historical tracking."""
        try:
            from core.database_optimization import db_optimizer
            self.db_optimizer = db_optimizer
            logger.info("✅ Database initialized for ML scoring tracking")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    def _initialize_vector_search(self):
        """Initialize vector search for hybrid ranking."""
        try:
            if 'vector_search' in self.services:
                self.vector_search = self.services['vector_search']
                logger.info("✅ Vector search initialized for hybrid ranking")
            else:
                logger.info("ℹ️ Vector search not available for hybrid ranking")
        except Exception as e:
            logger.warning(f"Vector search initialization failed: {e}")
    
    def _initialize_ml_models(self):
        """Initialize real ML models if available."""
        try:
            # Try scikit-learn first
            from sklearn.linear_model import LogisticRegression
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            
            self.scoring_model = LogisticRegression(random_state=42)
            self.scaler = StandardScaler()
            self.model_type = "logistic_regression"
            logger.info("✅ Scikit-learn ML model initialized")
            
        except ImportError:
            try:
                # Try XGBoost
                import xgboost as xgb
                self.scoring_model = xgb.XGBClassifier(random_state=42)
                self.model_type = "xgboost"
                logger.info("✅ XGBoost ML model initialized")
            except ImportError:
                logger.info("ℹ️ No ML libraries available, using rule-based scoring")
                self.model_type = "rule_based"
        except Exception as e:
            logger.warning(f"ML model initialization failed: {e}")
            self.model_type = "rule_based"
    
    def _load_calibration_data(self):
        """Load historical calibration data."""
        try:
            calibration_file = Path("data/ml_calibration.json")
            if calibration_file.exists():
                with open(calibration_file, 'r') as f:
                    self.calibration_data = json.load(f)
                logger.info(f"✅ Loaded {len(self.calibration_data)} calibration records")
        except Exception as e:
            logger.warning(f"Failed to load calibration data: {e}")
            self.calibration_data = []
    
    def _save_calibration_data(self):
        """Save historical calibration data."""
        try:
            calibration_file = Path("data/ml_calibration.json")
            calibration_file.parent.mkdir(exist_ok=True)
            
            with open(calibration_file, 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save calibration data: {e}")
    
    def calculate_lead_score(self, email_data: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive lead score with enhanced features."""
        try:
            # Check cache first
            cache_key = f"ml_score:{hash(str(email_data) + str(lead_data))}"
            if self.redis_client:
                try:
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        logger.info("✅ Retrieved score from cache")
                        return json.loads(cached_result)
                except Exception as e:
                    logger.warning(f"Cache retrieval failed: {e}")
            
            scores = {}
            
            # Email domain scoring
            scores["email_domain_score"] = self._score_email_domain(lead_data.get("email", ""))
            
            # Response time scoring
            scores["response_time_score"] = self._score_response_time(email_data.get("timestamp"))
            
            # Email content scoring
            email_content = email_data.get("content", "") + " " + email_data.get("subject", "")
            scores["email_length_score"] = self._score_email_length(email_content)
            scores["keyword_score"] = self._score_keywords(email_content)
            scores["subject_score"] = self._score_subject(email_data.get("subject", ""))
            
            # Contact frequency scoring
            scores["contact_frequency_score"] = self._score_contact_frequency(lead_data.get("contact_count", 0))
            
            # Time of day scoring
            scores["time_of_day_score"] = self._score_time_of_day(email_data.get("timestamp"))
            
            # Vector search similarity (if available)
            if self.vector_search:
                scores["semantic_similarity_score"] = self._score_semantic_similarity(email_content)
            
            # Calculate weighted total score
            if self.model_type != "rule_based" and self.scoring_model:
                total_score = self._predict_with_ml_model(scores)
            else:
                total_score = sum(score * self.feature_weights.get(feature, 0) for feature, score in scores.items())
            
            # Determine priority level
            priority = self._determine_priority(total_score)
            
            result = {
                "total_score": round(total_score, 2),
                "priority": priority,
                "individual_scores": scores,
                "recommended_action": self._get_recommended_action(priority, scores),
                "confidence": self._calculate_confidence(scores),
                "model_type": self.model_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache the result
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, 3600, json.dumps(result))  # 1 hour cache
                except Exception as e:
                    logger.warning(f"Cache storage failed: {e}")
            
            # Track for historical calibration
            self._track_scoring_result(result, email_data, lead_data)
            
            logger.info(f"✅ Calculated lead score: {total_score:.2f} ({priority})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Scoring failed: {e}")
            return self._default_score()
    
    def _predict_with_ml_model(self, scores: Dict[str, float]) -> float:
        """Predict score using trained ML model."""
        try:
            # Convert scores to feature vector
            feature_vector = [scores.get(feature, 0) for feature in self.feature_weights.keys()]
            
            if hasattr(self.scoring_model, 'predict_proba'):
                # For classification models
                probabilities = self.scoring_model.predict_proba([feature_vector])[0]
                # Convert probabilities to score (assuming binary classification)
                return probabilities[1] if len(probabilities) > 1 else probabilities[0]
            else:
                # For regression models
                return self.scoring_model.predict([feature_vector])[0]
                
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}, using rule-based scoring")
            return sum(score * self.feature_weights.get(feature, 0) for feature, score in scores.items())
    
    def _score_semantic_similarity(self, content: str) -> float:
        """Score based on semantic similarity to high-value leads."""
        try:
            if not self.vector_search:
                return 0.5
            
            # Search for similar high-value content
            results = self.vector_search.search_similar(content, top_k=3, threshold=0.6)
            
            if not results:
                return 0.5
            
            # Calculate average similarity
            avg_similarity = sum(result['similarity'] for result in results) / len(results)
            
            # Boost score if similar to high-value leads
            high_value_boost = 0.0
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('lead_value') == 'high':
                    high_value_boost += 0.2
            
            return min(1.0, avg_similarity + high_value_boost)
            
        except Exception as e:
            logger.warning(f"Semantic similarity scoring failed: {e}")
            return 0.5
    
    def _track_scoring_result(self, result: Dict[str, Any], email_data: Dict[str, Any], lead_data: Dict[str, Any]):
        """Track scoring result for historical calibration."""
        try:
            tracking_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email_content": email_data.get("content", "")[:200],  # Truncate for storage
                "email_subject": email_data.get("subject", ""),
                "lead_email": lead_data.get("email", ""),
                "predicted_score": result["total_score"],
                "predicted_priority": result["priority"],
                "individual_scores": result["individual_scores"],
                "model_type": result["model_type"]
            }
            
            # Store in memory
            self.calibration_data.append(tracking_data)
            
            # Keep only last 1000 records
            if len(self.calibration_data) > 1000:
                self.calibration_data = self.calibration_data[-1000:]
            
            # Store in database if available
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
                        tracking_data["model_type"]
                    ), fetch=False)
                except Exception as e:
                    logger.warning(f"Failed to store scoring log: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to track scoring result: {e}")
    
    def update_model_from_feedback(self, lead_id: str, actual_outcome: str, predicted_score: float):
        """Update model based on actual outcomes (online learning)."""
        try:
            feedback_data = {
                "lead_id": lead_id,
                "actual_outcome": actual_outcome,  # "won", "lost", "qualified", "unqualified"
                "predicted_score": predicted_score,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Store feedback
            if self.db_optimizer:
                self.db_optimizer.execute_query("""
                    INSERT INTO ml_feedback_log 
                    (lead_id, actual_outcome, predicted_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    feedback_data["lead_id"],
                    feedback_data["actual_outcome"],
                    feedback_data["predicted_score"],
                    feedback_data["timestamp"]
                ), fetch=False)
            
            # Update calibration data
            self.calibration_data.append(feedback_data)
            
            # Retrain model if we have enough data
            if len(self.calibration_data) >= 100:
                self._retrain_model()
            
            logger.info(f"✅ Updated model with feedback: {actual_outcome}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update model from feedback: {e}")
    
    def _retrain_model(self):
        """Retrain ML model with historical data."""
        try:
            if self.model_type == "rule_based" or not self.scoring_model:
                return
            
            # Prepare training data
            X = []
            y = []
            
            for record in self.calibration_data[-500:]:  # Use last 500 records
                if "individual_scores" in record:
                    feature_vector = [record["individual_scores"].get(feature, 0) for feature in self.feature_weights.keys()]
                    X.append(feature_vector)
                    
                    # Convert outcome to binary (1 for positive outcomes)
                    outcome = record.get("actual_outcome", "")
                    y.append(1 if outcome in ["won", "qualified"] else 0)
            
            if len(X) < 10:  # Need minimum data
                return
            
            # Retrain model
            if hasattr(self.scoring_model, 'fit'):
                self.scoring_model.fit(X, y)
                logger.info(f"✅ Retrained {self.model_type} model with {len(X)} samples")
            
        except Exception as e:
            logger.warning(f"Model retraining failed: {e}")
    
    def _score_email_domain(self, email: str) -> float:
        """Score email domain quality."""
        if not email or "@" not in email:
            return 0.0
        
        domain = email.split("@")[1].lower()
        
        # High-value domains
        if any(high_domain in domain for high_domain in ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]):
            return 0.8
        elif domain.endswith(".edu"):
            return 0.9
        elif domain.endswith(".gov"):
            return 0.95
        elif domain.endswith(".org"):
            return 0.7
        elif domain.endswith(".com"):
            return 0.6
        else:
            return 0.4
    
    def _score_response_time(self, timestamp: str) -> float:
        """Score based on response time."""
        if not timestamp:
            return 0.5
        
        try:
            email_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_diff = (now - email_time).total_seconds() / 3600  # hours
            
            # Faster response = higher score
            if time_diff < 1:
                return 1.0
            elif time_diff < 4:
                return 0.8
            elif time_diff < 24:
                return 0.6
            elif time_diff < 72:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5
    
    def _score_email_length(self, content: str) -> float:
        """Score based on email length."""
        length = len(content)
        
        # Optimal length range
        if 50 <= length <= 500:
            return 1.0
        elif 20 <= length < 50:
            return 0.7
        elif 500 < length <= 1000:
            return 0.8
        elif length > 1000:
            return 0.6
        else:
            return 0.3
    
    def _score_keywords(self, content: str) -> float:
        """Score based on keyword presence."""
        content_lower = content.lower()
        
        high_score = sum(1 for keyword in self.keywords["high_value"] if keyword in content_lower)
        medium_score = sum(1 for keyword in self.keywords["medium_value"] if keyword in content_lower)
        low_score = sum(1 for keyword in self.keywords["low_value"] if keyword in content_lower)
        
        # Calculate weighted score
        total_score = (high_score * 1.0) + (medium_score * 0.6) + (low_score * -0.3)
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, total_score / 3.0 + 0.5))
    
    def _score_subject(self, subject: str) -> float:
        """Score based on subject line quality."""
        if not subject:
            return 0.3
        
        subject_lower = subject.lower()
        
        # Positive indicators
        if any(word in subject_lower for word in ["urgent", "important", "asap", "help"]):
            return 0.9
        elif any(word in subject_lower for word in ["question", "inquiry", "information"]):
            return 0.7
        elif len(subject) > 10 and not subject_lower.startswith("re:"):
            return 0.6
        else:
            return 0.4
    
    def _score_contact_frequency(self, contact_count: int) -> float:
        """Score based on contact frequency."""
        if contact_count == 0:
            return 0.5  # New contact
        elif contact_count == 1:
            return 0.8  # First follow-up
        elif 2 <= contact_count <= 3:
            return 0.6  # Regular contact
        elif contact_count > 3:
            return 0.3  # Too frequent
        else:
            return 0.5
    
    def _score_time_of_day(self, timestamp: str) -> float:
        """Score based on time of day."""
        if not timestamp:
            return 0.5
        
        try:
            email_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = email_time.hour
            
            # Business hours get higher scores
            if 9 <= hour <= 17:
                return 1.0
            elif 8 <= hour <= 18:
                return 0.8
            elif 7 <= hour <= 19:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _determine_priority(self, total_score: float) -> str:
        """Determine priority level based on total score."""
        if total_score >= 0.8:
            return "high"
        elif total_score >= 0.6:
            return "medium"
        elif total_score >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def _get_recommended_action(self, priority: str, scores: Dict[str, float]) -> str:
        """Get recommended action based on priority and scores."""
        if priority == "high":
            return "immediate_response"
        elif priority == "medium":
            return "respond_within_4_hours"
        elif priority == "low":
            return "respond_within_24_hours"
        else:
            return "respond_when_convenient"
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate confidence in the scoring."""
        # Higher confidence when scores are more extreme (not all 0.5)
        variance = sum((score - 0.5) ** 2 for score in scores.values()) / len(scores)
        confidence = min(1.0, variance * 4)  # Scale to 0-1
        return round(confidence, 2)
    
    def _default_score(self) -> Dict[str, Any]:
        """Return default score when scoring fails."""
        return {
            "total_score": 0.5,
            "priority": "medium",
            "individual_scores": {},
            "recommended_action": "respond_within_24_hours",
            "confidence": 0.0,
            "model_type": self.model_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def batch_score_leads(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score multiple leads in batch with enhanced features."""
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
                "scored_at": score_result["timestamp"]
            }
            
            scored_leads.append(scored_lead)
        
        # Sort by score (highest first)
        scored_leads.sort(key=lambda x: x["ml_score"], reverse=True)
        
        logger.info(f"✅ Batch scored {len(scored_leads)} leads")
        return scored_leads
    
    async def batch_score_leads_async(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Async version of batch_score_leads for FastAPI compatibility."""
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch_score_leads, leads_data)
    
    def get_scoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive scoring statistics."""
        stats = {
            "feature_weights": self.feature_weights,
            "keywords": self.keywords,
            "model_loaded": self.scoring_model is not None,
            "model_type": self.model_type,
            "redis_available": self.redis_client is not None,
            "vector_search_available": self.vector_search is not None,
            "calibration_records": len(self.calibration_data),
            "database_available": self.db_optimizer is not None
        }
        
        # Add model-specific stats
        if self.scoring_model:
            stats["model_trained"] = hasattr(self.scoring_model, 'fit')
        
        return stats
    
    def get_calibration_accuracy(self) -> Dict[str, Any]:
        """Get calibration accuracy metrics."""
        try:
            if len(self.calibration_data) < 10:
                return {"error": "Insufficient calibration data"}
            
            # Calculate accuracy metrics
            total_predictions = len(self.calibration_data)
            correct_predictions = 0
            
            for record in self.calibration_data:
                predicted_score = record.get("predicted_score", 0)
                actual_outcome = record.get("actual_outcome", "")
                
                # Simple accuracy: high score + positive outcome = correct
                if predicted_score >= 0.7 and actual_outcome in ["won", "qualified"]:
                    correct_predictions += 1
                elif predicted_score < 0.7 and actual_outcome in ["lost", "unqualified"]:
                    correct_predictions += 1
            
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            
            return {
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "accuracy": round(accuracy, 3),
                "model_type": self.model_type
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate calibration accuracy: {e}")
            return {"error": str(e)}

def create_ml_scorer(services: Dict[str, Any] = None) -> MinimalMLScoring:
    """Create and return an ML scoring instance."""
    return MinimalMLScoring(services)

if __name__ == "__main__":
    # Test the ML scoring service
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    logger.info("🧪 Testing Enhanced Minimal ML Scoring Service")
    logger.info("=" * 60)
    
    # Test with mock services
    mock_services = {
        'vector_search': type('MockVectorSearch', (), {
            'search_similar': lambda self, content, top_k=3, threshold=0.6: [
                {'similarity': 0.8, 'metadata': {'lead_value': 'high'}},
                {'similarity': 0.7, 'metadata': {'lead_value': 'medium'}}
            ]
        })()
    }
    
    scorer = MinimalMLScoring(mock_services)
    
    # Test with sample data
    sample_email = {
        "content": "Hi, I'm urgently looking for your premium services. I have a budget of $10,000 and need this implemented ASAP.",
        "subject": "Urgent: Premium Service Quote Needed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    sample_lead = {
        "email": "john.doe@company.com",
        "contact_count": 1,
        "name": "John Doe"
    }
    
    # Test scoring
    logger.info("Testing lead scoring...")
    score_result = scorer.calculate_lead_score(sample_email, sample_lead)
    logger.info(f"✅ Score: {score_result['total_score']} ({score_result['priority']})")
    
    # Test batch scoring
    logger.info("Testing batch scoring...")
    leads = [
        {"email": "test1@example.com", "contact_count": 0, "last_email": sample_email},
        {"email": "test2@example.com", "contact_count": 2, "last_email": sample_email}
    ]
    
    batch_results = scorer.batch_score_leads(leads)
    logger.info(f"✅ Batch scored {len(batch_results)} leads")
    
    # Test feedback
    logger.info("Testing feedback update...")
    scorer.update_model_from_feedback("lead123", "won", 0.85)
    
    # Test stats
    logger.info("Testing stats...")
    stats = scorer.get_scoring_stats()
    logger.info(f"✅ Stats: {stats}")
    
    # Test calibration accuracy
    logger.info("Testing calibration accuracy...")
    accuracy = scorer.get_calibration_accuracy()
    logger.info(f"✅ Calibration accuracy: {accuracy}")
    
    logger.info("🎉 All enhanced ML scoring tests completed!")