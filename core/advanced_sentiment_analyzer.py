"""
Sentiment Analysis System for Fikiri Solutions
Advanced client mood and urgency detection using AI
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    sentiment: str  # positive, negative, neutral, mixed
    confidence: float
    urgency: str  # low, medium, high, critical
    emotions: List[str]
    mood_score: float  # -1.0 to 1.0
    business_impact: str  # low, medium, high
    suggested_action: str
    response_tone: str  # professional, empathetic, urgent, casual

class AdvancedSentimentAnalyzer:
    """Advanced sentiment analysis with business context"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
        
        # Sentiment patterns for fallback analysis
        self.sentiment_patterns = {
            "positive": [
                "excellent", "great", "amazing", "wonderful", "fantastic", "love", "perfect",
                "satisfied", "happy", "pleased", "impressed", "recommend", "thank you"
            ],
            "negative": [
                "terrible", "awful", "horrible", "disappointed", "angry", "frustrated",
                "upset", "dissatisfied", "complaint", "problem", "issue", "wrong",
                "broken", "failed", "unacceptable", "poor", "bad"
            ],
            "urgent": [
                "urgent", "asap", "immediately", "emergency", "critical", "rush",
                "deadline", "today", "now", "quickly", "fast", "priority"
            ],
            "business_critical": [
                "cancel", "terminate", "refund", "legal", "sue", "lawyer",
                "manager", "supervisor", "ceo", "complaint", "formal"
            ]
        }
        
        # Industry-specific sentiment contexts
        self.industry_contexts = {
            "landscaping": {
                "positive_triggers": ["beautiful", "maintained", "professional", "quality work"],
                "negative_triggers": ["overgrown", "messy", "poor quality", "damaged"],
                "urgency_indicators": ["deadline", "event", "season", "weather"]
            },
            "real_estate": {
                "positive_triggers": ["perfect", "ideal", "dream home", "investment"],
                "negative_triggers": ["overpriced", "issues", "problems", "concerns"],
                "urgency_indicators": ["market", "competition", "timing", "financing"]
            },
            "healthcare": {
                "positive_triggers": ["feeling better", "recovery", "treatment", "care"],
                "negative_triggers": ["pain", "symptoms", "worse", "concerned"],
                "urgency_indicators": ["emergency", "urgent", "immediate", "critical"]
            }
        }
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            config = get_config()
            api_key = getattr(config, 'openai_api_key', '')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized for sentiment analysis")
            else:
                logger.warning("⚠️ OpenAI API key not configured for sentiment analysis")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI: {e}")
    
    def analyze_sentiment(self, text: str, industry: str = "general", context: Dict[str, Any] = None) -> SentimentResult:
        """Analyze sentiment with business context"""
        if not self.openai_client:
            return self._fallback_sentiment_analysis(text, industry)
        
        try:
            # Prepare context information
            context_info = context or {}
            industry_context = self.industry_contexts.get(industry, {})
            
            prompt = f"""
            Analyze the sentiment and business impact of this customer communication:
            
            Text: "{text}"
            Industry: {industry}
            Context: {json.dumps(context_info)}
            
            Provide a comprehensive analysis in JSON format:
            {{
                "sentiment": "positive|negative|neutral|mixed",
                "confidence": 0.0-1.0,
                "urgency": "low|medium|high|critical",
                "emotions": ["emotion1", "emotion2"],
                "mood_score": -1.0 to 1.0,
                "business_impact": "low|medium|high",
                "suggested_action": "specific action to take",
                "response_tone": "professional|empathetic|urgent|casual"
            }}
            
            Consider:
            - Customer satisfaction level
            - Urgency of their request
            - Potential business impact
            - Appropriate response tone
            - Industry-specific context
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            result_data = json.loads(response.choices[0].message.content)
            
            return SentimentResult(
                sentiment=result_data.get("sentiment", "neutral"),
                confidence=result_data.get("confidence", 0.5),
                urgency=result_data.get("urgency", "low"),
                emotions=result_data.get("emotions", []),
                mood_score=result_data.get("mood_score", 0.0),
                business_impact=result_data.get("business_impact", "low"),
                suggested_action=result_data.get("suggested_action", "standard_response"),
                response_tone=result_data.get("response_tone", "professional")
            )
            
        except Exception as e:
            logger.error(f"❌ AI sentiment analysis failed: {e}")
            return self._fallback_sentiment_analysis(text, industry)
    
    def _fallback_sentiment_analysis(self, text: str, industry: str) -> SentimentResult:
        """Fallback sentiment analysis without AI"""
        text_lower = text.lower()
        
        # Analyze sentiment
        positive_count = sum(1 for word in self.sentiment_patterns["positive"] if word in text_lower)
        negative_count = sum(1 for word in self.sentiment_patterns["negative"] if word in text_lower)
        urgent_count = sum(1 for word in self.sentiment_patterns["urgent"] if word in text_lower)
        critical_count = sum(1 for word in self.sentiment_patterns["business_critical"] if word in text_lower)
        
        # Determine sentiment
        if negative_count > positive_count:
            sentiment = "negative"
            mood_score = -0.5
        elif positive_count > negative_count:
            sentiment = "positive"
            mood_score = 0.5
        else:
            sentiment = "neutral"
            mood_score = 0.0
        
        # Determine urgency
        if critical_count > 0:
            urgency = "critical"
        elif urgent_count > 2:
            urgency = "high"
        elif urgent_count > 0:
            urgency = "medium"
        else:
            urgency = "low"
        
        # Determine business impact
        if critical_count > 0 or (negative_count > 2 and urgency == "high"):
            business_impact = "high"
        elif negative_count > 0 or urgency == "medium":
            business_impact = "medium"
        else:
            business_impact = "low"
        
        # Determine response tone
        if sentiment == "negative" and urgency == "high":
            response_tone = "empathetic"
        elif urgency == "critical":
            response_tone = "urgent"
        elif sentiment == "positive":
            response_tone = "casual"
        else:
            response_tone = "professional"
        
        # Determine suggested action
        if business_impact == "high":
            suggested_action = "escalate_to_manager"
        elif urgency == "high":
            suggested_action = "immediate_response"
        elif sentiment == "negative":
            suggested_action = "apologize_and_resolve"
        else:
            suggested_action = "standard_response"
        
        return SentimentResult(
            sentiment=sentiment,
            confidence=0.7,  # Fallback confidence
            urgency=urgency,
            emotions=self._extract_emotions(text_lower),
            mood_score=mood_score,
            business_impact=business_impact,
            suggested_action=suggested_action,
            response_tone=response_tone
        )
    
    def _extract_emotions(self, text: str) -> List[str]:
        """Extract emotions from text"""
        emotions = []
        
        emotion_patterns = {
            "frustrated": ["frustrated", "annoyed", "irritated"],
            "angry": ["angry", "mad", "furious", "outraged"],
            "happy": ["happy", "pleased", "delighted", "excited"],
            "worried": ["worried", "concerned", "anxious", "nervous"],
            "satisfied": ["satisfied", "content", "pleased"],
            "disappointed": ["disappointed", "let down", "displeased"]
        }
        
        for emotion, patterns in emotion_patterns.items():
            if any(pattern in text for pattern in patterns):
                emotions.append(emotion)
        
        return emotions
    
    def analyze_email_thread(self, emails: List[Dict[str, Any]], industry: str = "general") -> Dict[str, Any]:
        """Analyze sentiment across an email thread"""
        if not emails:
            return {"error": "No emails provided"}
        
        try:
            # Analyze each email
            sentiment_results = []
            for email in emails:
                text = f"{email.get('subject', '')} {email.get('content', '')}"
                result = self.analyze_sentiment(text, industry)
                sentiment_results.append({
                    "email_id": email.get('id'),
                    "sentiment": result.sentiment,
                    "urgency": result.urgency,
                    "mood_score": result.mood_score,
                    "business_impact": result.business_impact
                })
            
            # Calculate thread-level metrics
            avg_mood_score = sum(r["mood_score"] for r in sentiment_results) / len(sentiment_results)
            
            # Determine overall thread sentiment
            sentiment_counts = {}
            for result in sentiment_results:
                sentiment = result["sentiment"]
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            
            # Determine highest urgency
            urgency_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            max_urgency = max(sentiment_results, key=lambda x: urgency_levels[x["urgency"]])["urgency"]
            
            # Determine highest business impact
            impact_levels = {"low": 1, "medium": 2, "high": 3}
            max_impact = max(sentiment_results, key=lambda x: impact_levels[x["business_impact"]])["business_impact"]
            
            return {
                "thread_sentiment": overall_sentiment,
                "avg_mood_score": avg_mood_score,
                "max_urgency": max_urgency,
                "max_business_impact": max_impact,
                "email_count": len(emails),
                "sentiment_trend": sentiment_results,
                "recommended_action": self._get_thread_action(max_impact, max_urgency, overall_sentiment)
            }
            
        except Exception as e:
            logger.error(f"❌ Thread sentiment analysis failed: {e}")
            return {"error": "Thread analysis failed"}
    
    def _get_thread_action(self, business_impact: str, urgency: str, sentiment: str) -> str:
        """Get recommended action for email thread"""
        if business_impact == "high" and urgency == "critical":
            return "immediate_manager_escalation"
        elif business_impact == "high" or urgency == "critical":
            return "priority_handling"
        elif sentiment == "negative" and urgency == "high":
            return "apologize_and_resolve"
        elif sentiment == "negative":
            return "customer_service_follow_up"
        elif urgency == "high":
            return "quick_response"
        else:
            return "standard_response"
    
    def get_sentiment_insights(self, sentiment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from sentiment data"""
        if not sentiment_data:
            return {"error": "No sentiment data provided"}
        
        try:
            # Calculate overall metrics
            total_emails = len(sentiment_data)
            positive_count = sum(1 for s in sentiment_data if s.get("sentiment") == "positive")
            negative_count = sum(1 for s in sentiment_data if s.get("sentiment") == "negative")
            neutral_count = sum(1 for s in sentiment_data if s.get("sentiment") == "neutral")
            
            avg_mood_score = sum(s.get("mood_score", 0) for s in sentiment_data) / total_emails
            
            # Urgency distribution
            urgency_counts = {}
            for s in sentiment_data:
                urgency = s.get("urgency", "low")
                urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
            
            # Business impact distribution
            impact_counts = {}
            for s in sentiment_data:
                impact = s.get("business_impact", "low")
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
            
            return {
                "total_emails": total_emails,
                "sentiment_distribution": {
                    "positive": positive_count,
                    "negative": negative_count,
                    "neutral": neutral_count
                },
                "avg_mood_score": avg_mood_score,
                "urgency_distribution": urgency_counts,
                "business_impact_distribution": impact_counts,
                "customer_satisfaction_score": (positive_count / total_emails) * 100,
                "recommendations": self._generate_recommendations(sentiment_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Sentiment insights generation failed: {e}")
            return {"error": "Insights generation failed"}
    
    def _generate_recommendations(self, sentiment_data: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on sentiment data"""
        recommendations = []
        
        # Analyze patterns
        negative_count = sum(1 for s in sentiment_data if s.get("sentiment") == "negative")
        high_urgency_count = sum(1 for s in sentiment_data if s.get("urgency") == "high")
        high_impact_count = sum(1 for s in sentiment_data if s.get("business_impact") == "high")
        
        if negative_count > len(sentiment_data) * 0.3:
            recommendations.append("Consider implementing customer satisfaction surveys")
        
        if high_urgency_count > len(sentiment_data) * 0.2:
            recommendations.append("Review response time processes for urgent requests")
        
        if high_impact_count > len(sentiment_data) * 0.1:
            recommendations.append("Implement escalation procedures for high-impact issues")
        
        if not recommendations:
            recommendations.append("Continue current customer service practices")
        
        return recommendations

# Global instance
sentiment_analyzer = None

def get_sentiment_analyzer() -> Optional[AdvancedSentimentAnalyzer]:
    """Get the global sentiment analyzer instance"""
    global sentiment_analyzer
    
    if sentiment_analyzer is None:
        sentiment_analyzer = AdvancedSentimentAnalyzer()
    
    return sentiment_analyzer
