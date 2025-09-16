#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal ML Scoring Service
Lightweight ML scoring for CRM lead prioritization.
"""

import json
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class MinimalMLScoring:
    """Minimal ML scoring service - lightweight version."""
    
    def __init__(self):
        """Initialize ML scoring service."""
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
    
    def calculate_lead_score(self, email_data: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive lead score."""
        try:
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
            
            # Calculate weighted total score
            total_score = sum(score * self.feature_weights[feature] for feature, score in scores.items())
            
            # Determine priority level
            priority = self._determine_priority(total_score)
            
            result = {
                "total_score": round(total_score, 2),
                "priority": priority,
                "individual_scores": scores,
                "recommended_action": self._get_recommended_action(priority, scores),
                "confidence": self._calculate_confidence(scores)
            }
            
            # Debug output removed
            return result
            
        except Exception as e:
            print(f"❌ Scoring failed: {e}")
            return self._default_score()
    
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
            now = datetime.now()
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
            "confidence": 0.0
        }
    
    def batch_score_leads(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score multiple leads in batch."""
        scored_leads = []
        
        for lead_data in leads_data:
            email_data = lead_data.get("last_email", {})
            score_result = self.calculate_lead_score(email_data, lead_data)
            
            scored_lead = {
                **lead_data,
                "ml_score": score_result["total_score"],
                "priority": score_result["priority"],
                "recommended_action": score_result["recommended_action"],
                "confidence": score_result["confidence"]
            }
            
            scored_leads.append(scored_lead)
        
        # Sort by score (highest first)
        scored_leads.sort(key=lambda x: x["ml_score"], reverse=True)
        
        print(f"✅ Batch scored {len(scored_leads)} leads")
        return scored_leads
    
    def get_scoring_stats(self) -> Dict[str, Any]:
        """Get scoring statistics."""
        return {
            "feature_weights": self.feature_weights,
            "keywords": self.keywords,
            "model_loaded": self.scoring_model is not None
        }

def create_ml_scorer() -> MinimalMLScoring:
    """Create and return an ML scoring instance."""
    return MinimalMLScoring()

if __name__ == "__main__":
    # Test the ML scoring service
    print("🧪 Testing Minimal ML Scoring Service")
    print("=" * 50)
    
    scorer = MinimalMLScoring()
    
    # Test with sample data
    sample_email = {
        "content": "Hi, I'm urgently looking for your premium services. I have a budget of $10,000 and need this implemented ASAP.",
        "subject": "Urgent: Premium Service Quote Needed",
        "timestamp": datetime.now().isoformat()
    }
    
    sample_lead = {
        "email": "john.doe@company.com",
        "contact_count": 1,
        "name": "John Doe"
    }
    
    # Test scoring
    print("Testing lead scoring...")
    score_result = scorer.calculate_lead_score(sample_email, sample_lead)
    # Debug output removed to prevent metadata display
    
    # Test batch scoring
    print("\nTesting batch scoring...")
    leads = [
        {"email": "test1@example.com", "contact_count": 0, "last_email": sample_email},
        {"email": "test2@example.com", "contact_count": 2, "last_email": sample_email}
    ]
    
    batch_results = scorer.batch_score_leads(leads)
    print(f"✅ Batch scored {len(batch_results)} leads")
    
    # Test stats
    print("\nTesting stats...")
    stats = scorer.get_scoring_stats()
    print(f"✅ Feature weights: {len(stats['feature_weights'])}")
    
    print("\n🎉 All ML scoring tests completed!")

