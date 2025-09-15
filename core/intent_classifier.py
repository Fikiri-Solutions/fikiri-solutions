#!/usr/bin/env python3
"""
Fikiri Solutions - Intent Classification System
Advanced NLU for chat interface with specific intent recognition.
"""

import re
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

class IntentClassifier:
    """Advanced intent classification for chat interface."""
    
    def __init__(self):
        """Initialize intent classifier with training data."""
        self.intents = {
            "email_last_received": {
                "keywords": ["last email", "recent email", "who emailed", "latest message", "most recent"],
                "patterns": [r"who.*email.*last", r"show.*recent.*email", r"latest.*message"],
                "examples": [
                    "Who emailed me last?",
                    "Show me my most recent email",
                    "What's the latest message I received?",
                    "Who sent me the last email?"
                ]
            },
            "email_search": {
                "keywords": ["find email", "search email", "look for", "email from", "message from"],
                "patterns": [r"find.*email.*from", r"search.*message", r"email.*from.*"],
                "examples": [
                    "Find emails from John",
                    "Search for messages about project",
                    "Look for emails from last week"
                ]
            },
            "email_count": {
                "keywords": ["how many emails", "email count", "number of messages", "total emails"],
                "patterns": [r"how many.*email", r"count.*message", r"total.*email"],
                "examples": [
                    "How many emails do I have?",
                    "What's my email count?",
                    "Total number of messages"
                ]
            },
            "crm_new_lead": {
                "keywords": ["add lead", "new customer", "create contact", "add prospect"],
                "patterns": [r"add.*lead", r"new.*customer", r"create.*contact"],
                "examples": [
                    "Add a new lead",
                    "Create a customer record",
                    "Add this prospect to CRM"
                ]
            },
            "crm_lead_count": {
                "keywords": ["how many leads", "lead count", "number of customers", "total leads"],
                "patterns": [r"how many.*lead", r"count.*customer", r"total.*lead"],
                "examples": [
                    "How many leads do I have?",
                    "What's my customer count?",
                    "Total number of prospects"
                ]
            },
            "automation_setup": {
                "keywords": ["setup automation", "automate emails", "auto reply", "email automation"],
                "patterns": [r"setup.*automation", r"automate.*email", r"auto.*reply"],
                "examples": [
                    "Set up email automation",
                    "Automate my replies",
                    "Configure auto responses"
                ]
            },
            "service_status": {
                "keywords": ["service status", "is working", "system down", "check services"],
                "patterns": [r"service.*status", r"is.*working", r"system.*down"],
                "examples": [
                    "Is the service working?",
                    "Check system status",
                    "Are services down?"
                ]
            },
            "help_support": {
                "keywords": ["help", "support", "how to", "assistance", "guide"],
                "patterns": [r"how.*to", r"help.*with", r"guide.*me"],
                "examples": [
                    "How do I use this?",
                    "I need help",
                    "Can you guide me?"
                ]
            },
            "greeting": {
                "keywords": ["hello", "hi", "hey", "good morning", "good afternoon"],
                "patterns": [r"^(hello|hi|hey)", r"good (morning|afternoon|evening)"],
                "examples": [
                    "Hello",
                    "Hi there",
                    "Good morning"
                ]
            }
        }
    
    def classify_intent(self, user_message: str) -> Dict[str, Any]:
        """Classify user intent with confidence scoring."""
        message_lower = user_message.lower().strip()
        
        # Calculate scores for each intent
        intent_scores = {}
        
        for intent_name, intent_data in self.intents.items():
            score = 0.0
            
            # Keyword matching (weight: 0.3)
            keyword_matches = sum(1 for keyword in intent_data["keywords"] 
                                if keyword in message_lower)
            if keyword_matches > 0:
                score += min(keyword_matches * 0.3, 0.9)
            
            # Pattern matching (weight: 0.4)
            pattern_matches = sum(1 for pattern in intent_data["patterns"] 
                                if re.search(pattern, message_lower))
            if pattern_matches > 0:
                score += min(pattern_matches * 0.4, 0.9)
            
            # Exact example matching (weight: 0.5)
            for example in intent_data["examples"]:
                if example.lower() in message_lower or message_lower in example.lower():
                    score += 0.5
                    break
            
            intent_scores[intent_name] = score
        
        # Find best intent
        if not intent_scores or max(intent_scores.values()) < 0.3:
            best_intent = "general_inquiry"
            confidence = 0.6
        else:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best_intent], 0.95)
        
        # Determine urgency
        urgency = self._determine_urgency(message_lower, best_intent)
        
        return {
            "intent": best_intent,
            "confidence": round(confidence, 2),
            "urgency": urgency,
            "scores": intent_scores
        }
    
    def _determine_urgency(self, message: str, intent: str) -> str:
        """Determine urgency level based on message content and intent."""
        urgent_keywords = ["urgent", "asap", "immediately", "emergency", "critical", "help"]
        
        if any(keyword in message for keyword in urgent_keywords):
            return "high"
        
        if intent in ["service_status", "automation_setup"]:
            return "medium"
        
        if intent in ["greeting", "help_support"]:
            return "low"
        
        return "normal"
    
    def get_suggested_action(self, intent: str) -> str:
        """Get suggested action based on intent."""
        action_map = {
            "email_last_received": "fetch_last_email",
            "email_search": "search_emails",
            "email_count": "get_email_count",
            "crm_new_lead": "create_lead",
            "crm_lead_count": "get_lead_count",
            "automation_setup": "setup_automation",
            "service_status": "check_services",
            "help_support": "provide_help",
            "greeting": "greet_user",
            "general_inquiry": "provide_information"
        }
        
        return action_map.get(intent, "provide_information")

def create_intent_classifier() -> IntentClassifier:
    """Create and return an intent classifier instance."""
    return IntentClassifier()

if __name__ == "__main__":
    # Test the intent classifier
    print("🧪 Testing Intent Classifier")
    print("=" * 50)
    
    classifier = IntentClassifier()
    
    test_messages = [
        "Who emailed me last?",
        "How many leads do I have?",
        "Set up email automation",
        "Is the service working?",
        "Hello there",
        "I need help with my emails",
        "Find emails from John",
        "What's my email count?"
    ]
    
    for message in test_messages:
        result = classifier.classify_intent(message)
        action = classifier.get_suggested_action(result["intent"])
        
        print(f"Message: '{message}'")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']})")
        print(f"Urgency: {result['urgency']}")
        print(f"Action: {action}")
        print("-" * 30)
    
    print("🎉 Intent classification tests completed!")
