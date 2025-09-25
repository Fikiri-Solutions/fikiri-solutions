"""
Context-Aware Response System for Fikiri Solutions
Maintains conversation context and memory for intelligent responses
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid

from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Conversation state types"""
    NEW = "new"
    ACTIVE = "active"
    WAITING_RESPONSE = "waiting_response"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"

class MessageType(Enum):
    """Message types in conversation"""
    USER_QUESTION = "user_question"
    BOT_RESPONSE = "bot_response"
    SYSTEM_MESSAGE = "system_message"
    ESCALATION = "escalation"
    FEEDBACK = "feedback"

class ContextType(Enum):
    """Types of context information"""
    USER_PROFILE = "user_profile"
    CONVERSATION_HISTORY = "conversation_history"
    BUSINESS_DATA = "business_data"
    EXTERNAL_DATA = "external_data"
    SYSTEM_STATE = "system_state"

@dataclass
class ConversationMessage:
    """Single message in conversation"""
    id: str
    conversation_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    confidence: Optional[float] = None

@dataclass
class ConversationContext:
    """Conversation context and memory"""
    conversation_id: str
    user_id: str
    state: ConversationState
    messages: List[ConversationMessage]
    context_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    session_id: Optional[str] = None
    channel: str = "web"
    resolved_issues: List[str] = None
    escalation_count: int = 0

@dataclass
class ContextualResponse:
    """Context-aware response with reasoning"""
    response: str
    confidence: float
    context_used: List[str]
    reasoning: str
    suggested_actions: List[str]
    requires_escalation: bool = False
    follow_up_questions: List[str] = None

class ContextAwareResponseSystem:
    """System for maintaining conversation context and generating context-aware responses"""
    
    def __init__(self):
        self.config = get_config()
        self.conversations = {}  # In-memory storage for demo
        self.context_memory = {}  # Context data storage
        self.response_patterns = self._load_response_patterns()
        
        # Context retention settings
        self.max_conversation_age = timedelta(days=30)
        self.max_context_items = 100
        self.context_relevance_threshold = 0.3
        
        logger.info("🧠 Context-aware response system initialized")
    
    def _load_response_patterns(self) -> Dict[str, Any]:
        """Load response patterns and context rules"""
        return {
            "greeting_patterns": [
                "hello", "hi", "hey", "good morning", "good afternoon", "good evening"
            ],
            "question_patterns": [
                "how", "what", "when", "where", "why", "can you", "do you", "is it"
            ],
            "problem_patterns": [
                "problem", "issue", "error", "not working", "broken", "failed", "trouble"
            ],
            "appreciation_patterns": [
                "thank you", "thanks", "appreciate", "helpful", "great", "perfect"
            ],
            "frustration_patterns": [
                "frustrated", "annoying", "terrible", "awful", "hate", "stupid", "useless"
            ],
            "escalation_triggers": [
                "speak to human", "real person", "manager", "supervisor", "not helpful", "terrible"
            ]
        }
    
    def start_conversation(self, user_id: str, initial_message: str,
                         session_id: Optional[str] = None, channel: str = "web",
                         user_context: Dict[str, Any] = None) -> ConversationContext:
        """Start a new conversation with context"""
        try:
            conversation_id = str(uuid.uuid4())
            
            # Create initial message
            initial_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                message_type=MessageType.USER_QUESTION,
                content=initial_message,
                metadata={"channel": channel, "session_id": session_id},
                timestamp=datetime.now(),
                user_id=user_id
            )
            
            # Initialize context data
            context_data = {
                "user_profile": user_context or {},
                "conversation_summary": "",
                "key_topics": [],
                "user_intent": self._analyze_intent(initial_message),
                "emotional_state": self._analyze_emotion(initial_message),
                "technical_level": "unknown",
                "preferred_communication_style": "formal"
            }
            
            # Create conversation context
            conversation = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                state=ConversationState.NEW,
                messages=[initial_msg],
                context_data=context_data,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_activity=datetime.now(),
                session_id=session_id,
                channel=channel,
                resolved_issues=[]
            )
            
            # Store conversation
            self.conversations[conversation_id] = conversation
            
            # Initialize user context memory
            if user_id not in self.context_memory:
                self.context_memory[user_id] = {
                    "profile": user_context or {},
                    "conversation_history": [],
                    "preferences": {},
                    "resolved_issues": [],
                    "escalation_history": []
                }
            
            logger.info(f"🆕 Started conversation: {conversation_id} for user: {user_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"❌ Failed to start conversation: {e}")
            raise
    
    def add_message(self, conversation_id: str, content: str, 
                   message_type: MessageType, metadata: Dict[str, Any] = None) -> ConversationMessage:
        """Add message to conversation"""
        try:
            if conversation_id not in self.conversations:
                raise ValueError(f"Conversation not found: {conversation_id}")
            
            conversation = self.conversations[conversation_id]
            
            # Create message
            message = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                message_type=message_type,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now(),
                user_id=conversation.user_id
            )
            
            # Add to conversation
            conversation.messages.append(message)
            conversation.updated_at = datetime.now()
            conversation.last_activity = datetime.now()
            
            # Update context based on message
            self._update_context_from_message(conversation, message)
            
            logger.debug(f"📝 Added message to conversation: {conversation_id}")
            return message
            
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            raise
    
    def generate_contextual_response(self, conversation_id: str, 
                                   user_message: str) -> ContextualResponse:
        """Generate context-aware response"""
        try:
            if conversation_id not in self.conversations:
                raise ValueError(f"Conversation not found: {conversation_id}")
            
            conversation = self.conversations[conversation_id]
            
            # Add user message to conversation
            user_msg = self.add_message(
                conversation_id, 
                user_message, 
                MessageType.USER_QUESTION
            )
            
            # Analyze current context
            context_analysis = self._analyze_conversation_context(conversation)
            
            # Generate response based on context
            response = self._generate_response_with_context(
                conversation, 
                user_message, 
                context_analysis
            )
            
            # Add bot response to conversation
            bot_msg = self.add_message(
                conversation_id,
                response.response,
                MessageType.BOT_RESPONSE,
                {
                    "confidence": response.confidence,
                    "context_used": response.context_used,
                    "reasoning": response.reasoning
                }
            )
            
            # Update conversation state
            self._update_conversation_state(conversation, response)
            
            logger.info(f"🤖 Generated contextual response for: {conversation_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to generate contextual response: {e}")
            # Return fallback response
            return ContextualResponse(
                response="I apologize, but I encountered an issue. Could you please rephrase your question?",
                confidence=0.1,
                context_used=[],
                reasoning="Error fallback",
                suggested_actions=["Try rephrasing your question", "Contact support"],
                requires_escalation=True
            )
    
    def _analyze_intent(self, message: str) -> str:
        """Analyze user intent from message"""
        message_lower = message.lower()
        
        # Check for common intents
        if any(pattern in message_lower for pattern in self.response_patterns["greeting_patterns"]):
            return "greeting"
        elif any(pattern in message_lower for pattern in self.response_patterns["question_patterns"]):
            return "question"
        elif any(pattern in message_lower for pattern in self.response_patterns["problem_patterns"]):
            return "problem_report"
        elif any(pattern in message_lower for pattern in self.response_patterns["appreciation_patterns"]):
            return "appreciation"
        elif "price" in message_lower or "cost" in message_lower:
            return "pricing_inquiry"
        elif "help" in message_lower or "support" in message_lower:
            return "help_request"
        else:
            return "general_inquiry"
    
    def _analyze_emotion(self, message: str) -> str:
        """Analyze emotional tone of message"""
        message_lower = message.lower()
        
        if any(pattern in message_lower for pattern in self.response_patterns["frustration_patterns"]):
            return "frustrated"
        elif any(pattern in message_lower for pattern in self.response_patterns["appreciation_patterns"]):
            return "positive"
        elif "urgent" in message_lower or "asap" in message_lower or "!" in message:
            return "urgent"
        elif "?" in message:
            return "curious"
        else:
            return "neutral"
    
    def _update_context_from_message(self, conversation: ConversationContext, 
                                   message: ConversationMessage):
        """Update conversation context based on new message"""
        try:
            context = conversation.context_data
            
            # Update user intent and emotion
            if message.message_type == MessageType.USER_QUESTION:
                context["user_intent"] = self._analyze_intent(message.content)
                context["emotional_state"] = self._analyze_emotion(message.content)
                
                # Extract key topics
                topics = self._extract_topics(message.content)
                context["key_topics"] = list(set(context.get("key_topics", []) + topics))
                
                # Detect technical level
                if self._is_technical_message(message.content):
                    context["technical_level"] = "technical"
                elif context.get("technical_level") == "unknown":
                    context["technical_level"] = "basic"
            
            # Update conversation summary
            self._update_conversation_summary(conversation)
            
        except Exception as e:
            logger.error(f"❌ Failed to update context: {e}")
    
    def _extract_topics(self, message: str) -> List[str]:
        """Extract key topics from message"""
        topics = []
        message_lower = message.lower()
        
        # Business topics
        topic_keywords = {
            "email": ["email", "gmail", "outlook", "mail"],
            "crm": ["crm", "lead", "contact", "customer"],
            "automation": ["automation", "automate", "workflow", "rule"],
            "integration": ["integration", "connect", "sync", "api"],
            "pricing": ["price", "cost", "plan", "subscription"],
            "support": ["help", "support", "issue", "problem"],
            "features": ["feature", "functionality", "capability"],
            "setup": ["setup", "configure", "install", "getting started"],
            "landscaping": ["landscaping", "lawn", "garden", "outdoor"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _is_technical_message(self, message: str) -> bool:
        """Determine if message contains technical content"""
        technical_terms = [
            "api", "webhook", "integration", "database", "server", "error code",
            "configuration", "authentication", "ssl", "json", "xml", "oauth"
        ]
        
        message_lower = message.lower()
        return any(term in message_lower for term in technical_terms)
    
    def _update_conversation_summary(self, conversation: ConversationContext):
        """Update conversation summary based on messages"""
        try:
            messages = conversation.messages[-5:]  # Last 5 messages
            
            # Extract key points
            key_points = []
            for msg in messages:
                if msg.message_type == MessageType.USER_QUESTION:
                    intent = self._analyze_intent(msg.content)
                    key_points.append(f"User {intent}")
                elif msg.message_type == MessageType.BOT_RESPONSE:
                    key_points.append("Bot responded")
            
            # Update summary
            conversation.context_data["conversation_summary"] = " → ".join(key_points)
            
        except Exception as e:
            logger.error(f"❌ Failed to update conversation summary: {e}")
    
    def _analyze_conversation_context(self, conversation: ConversationContext) -> Dict[str, Any]:
        """Analyze current conversation context"""
        try:
            context = conversation.context_data
            messages = conversation.messages
            
            analysis = {
                "conversation_length": len(messages),
                "user_messages": len([m for m in messages if m.message_type == MessageType.USER_QUESTION]),
                "bot_messages": len([m for m in messages if m.message_type == MessageType.BOT_RESPONSE]),
                "current_intent": context.get("user_intent", "unknown"),
                "emotional_state": context.get("emotional_state", "neutral"),
                "key_topics": context.get("key_topics", []),
                "technical_level": context.get("technical_level", "unknown"),
                "conversation_age": (datetime.now() - conversation.created_at).total_seconds() / 60,  # minutes
                "needs_escalation": self._check_escalation_needed(conversation),
                "user_satisfaction": self._estimate_user_satisfaction(conversation)
            }
            
            # Check for patterns
            analysis["repeated_questions"] = self._detect_repeated_questions(messages)
            analysis["escalation_signals"] = self._detect_escalation_signals(messages)
            analysis["resolution_indicators"] = self._detect_resolution_indicators(messages)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze conversation context: {e}")
            return {}
    
    def _check_escalation_needed(self, conversation: ConversationContext) -> bool:
        """Check if conversation needs human escalation"""
        recent_messages = conversation.messages[-3:]  # Last 3 messages
        
        for message in recent_messages:
            if message.message_type == MessageType.USER_QUESTION:
                message_lower = message.content.lower()
                if any(trigger in message_lower for trigger in self.response_patterns["escalation_triggers"]):
                    return True
        
        # Check for repeated issues
        if conversation.escalation_count > 2:
            return True
        
        # Check conversation length without resolution
        if len(conversation.messages) > 20 and conversation.state != ConversationState.RESOLVED:
            return True
        
        return False
    
    def _estimate_user_satisfaction(self, conversation: ConversationContext) -> str:
        """Estimate user satisfaction based on conversation"""
        recent_messages = conversation.messages[-3:]
        
        positive_indicators = 0
        negative_indicators = 0
        
        for message in recent_messages:
            if message.message_type == MessageType.USER_QUESTION:
                message_lower = message.content.lower()
                
                if any(pattern in message_lower for pattern in self.response_patterns["appreciation_patterns"]):
                    positive_indicators += 1
                elif any(pattern in message_lower for pattern in self.response_patterns["frustration_patterns"]):
                    negative_indicators += 1
        
        if positive_indicators > negative_indicators:
            return "satisfied"
        elif negative_indicators > positive_indicators:
            return "dissatisfied"
        else:
            return "neutral"
    
    def _detect_repeated_questions(self, messages: List[ConversationMessage]) -> bool:
        """Detect if user is asking similar questions repeatedly"""
        user_messages = [m.content.lower() for m in messages if m.message_type == MessageType.USER_QUESTION]
        
        if len(user_messages) < 2:
            return False
        
        # Simple similarity check
        for i, msg1 in enumerate(user_messages):
            for msg2 in user_messages[i+1:]:
                if self._calculate_similarity(msg1, msg2) > 0.7:
                    return True
        
        return False
    
    def _detect_escalation_signals(self, messages: List[ConversationMessage]) -> bool:
        """Detect signals that user wants escalation"""
        recent_user_messages = [
            m.content.lower() for m in messages[-3:] 
            if m.message_type == MessageType.USER_QUESTION
        ]
        
        for message in recent_user_messages:
            if any(trigger in message for trigger in self.response_patterns["escalation_triggers"]):
                return True
        
        return False
    
    def _detect_resolution_indicators(self, messages: List[ConversationMessage]) -> bool:
        """Detect if conversation seems resolved"""
        if not messages:
            return False
        
        last_message = messages[-1]
        if last_message.message_type == MessageType.USER_QUESTION:
            message_lower = last_message.content.lower()
            return any(pattern in message_lower for pattern in self.response_patterns["appreciation_patterns"])
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_response_with_context(self, conversation: ConversationContext,
                                      user_message: str, context_analysis: Dict[str, Any]) -> ContextualResponse:
        """Generate response using conversation context"""
        try:
            context_used = []
            reasoning_parts = []
            confidence = 0.7  # Base confidence
            
            # Adjust response based on emotional state
            emotional_state = context_analysis.get("emotional_state", "neutral")
            if emotional_state == "frustrated":
                response_prefix = "I understand your frustration. "
                confidence += 0.1
                context_used.append("emotional_state")
                reasoning_parts.append("Detected user frustration, using empathetic tone")
            elif emotional_state == "positive":
                response_prefix = "I'm glad to help! "
                confidence += 0.1
                context_used.append("emotional_state")
                reasoning_parts.append("Detected positive mood, using enthusiastic tone")
            else:
                response_prefix = ""
            
            # Adjust for technical level
            technical_level = context_analysis.get("technical_level", "basic")
            if technical_level == "technical":
                context_used.append("technical_level")
                reasoning_parts.append("Using technical language for experienced user")
            
            # Check for repeated questions
            if context_analysis.get("repeated_questions", False):
                response_prefix += "I notice you've asked about this before. Let me provide more detailed information. "
                context_used.append("conversation_history")
                reasoning_parts.append("Detected repeated question, providing more detail")
            
            # Generate base response based on intent
            intent = context_analysis.get("current_intent", "general_inquiry")
            base_response = self._generate_base_response(user_message, intent, technical_level)
            
            # Combine response parts
            full_response = response_prefix + base_response
            
            # Determine if escalation needed
            requires_escalation = context_analysis.get("needs_escalation", False)
            if requires_escalation:
                full_response += "\n\nWould you like me to connect you with a human specialist for more personalized assistance?"
                context_used.append("escalation_detection")
                reasoning_parts.append("Escalation recommended based on conversation pattern")
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(intent, context_analysis)
            
            # Generate follow-up questions
            follow_up_questions = self._generate_follow_up_questions(intent, conversation.context_data)
            
            return ContextualResponse(
                response=full_response,
                confidence=min(confidence, 1.0),
                context_used=context_used,
                reasoning=" | ".join(reasoning_parts) if reasoning_parts else "Standard response",
                suggested_actions=suggested_actions,
                requires_escalation=requires_escalation,
                follow_up_questions=follow_up_questions
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to generate contextual response: {e}")
            return ContextualResponse(
                response="I apologize, but I'm having trouble understanding your request. Could you please provide more details?",
                confidence=0.3,
                context_used=[],
                reasoning="Error fallback response",
                suggested_actions=["Rephrase your question", "Contact support"],
                requires_escalation=True
            )
    
    def _generate_base_response(self, user_message: str, intent: str, technical_level: str) -> str:
        """Generate base response based on intent and technical level"""
        
        # Intent-based responses
        if intent == "greeting":
            return "Hello! I'm here to help you with any questions about Fikiri Solutions. What can I assist you with today?"
        
        elif intent == "pricing_inquiry":
            if technical_level == "technical":
                return "Our pricing is based on usage tiers with API rate limits and feature access. We offer Starter ($29), Growth ($79), Business ($199), and Enterprise (custom) plans. Each includes different limits for emails, AI responses, and integrations."
            else:
                return "We have flexible pricing plans starting at $29/month for our Starter plan. Each plan includes different features and limits. Would you like me to help you find the right plan for your needs?"
        
        elif intent == "problem_report":
            return "I'm sorry to hear you're experiencing an issue. Let me help you troubleshoot this. Can you provide more details about what specific problem you're encountering?"
        
        elif intent == "help_request":
            return "I'm here to help! You can ask me about our features, pricing, setup process, integrations, or any other questions about Fikiri Solutions. What would you like to know more about?"
        
        elif intent == "appreciation":
            return "You're very welcome! I'm glad I could help. Is there anything else you'd like to know about Fikiri Solutions?"
        
        else:  # general_inquiry
            return "I'd be happy to help with your question about Fikiri Solutions. Could you provide a bit more detail about what you're looking for?"
    
    def _generate_suggested_actions(self, intent: str, context_analysis: Dict[str, Any]) -> List[str]:
        """Generate suggested actions based on context"""
        actions = []
        
        if intent == "pricing_inquiry":
            actions = ["View detailed pricing", "Start free trial", "Contact sales"]
        elif intent == "problem_report":
            actions = ["Check troubleshooting guide", "Contact support", "Search knowledge base"]
        elif intent == "help_request":
            actions = ["Browse help documentation", "Watch tutorial videos", "Schedule demo"]
        else:
            actions = ["Explore features", "Start free trial", "Contact support"]
        
        # Add escalation if needed
        if context_analysis.get("needs_escalation", False):
            actions.append("Speak with human specialist")
        
        return actions
    
    def _generate_follow_up_questions(self, intent: str, context_data: Dict[str, Any]) -> List[str]:
        """Generate relevant follow-up questions"""
        questions = []
        
        key_topics = context_data.get("key_topics", [])
        
        if intent == "pricing_inquiry":
            questions = [
                "What's your typical email volume per month?",
                "Do you need specific integrations?",
                "Would you like to schedule a demo?"
            ]
        elif intent == "problem_report":
            questions = [
                "When did this issue first occur?",
                "Are you seeing any error messages?",
                "Have you tried any troubleshooting steps?"
            ]
        elif "email" in key_topics:
            questions = [
                "Which email provider are you using?",
                "What type of email automation interests you most?",
                "Do you currently use any email management tools?"
            ]
        elif "crm" in key_topics:
            questions = [
                "What CRM system do you currently use?",
                "How many leads do you typically handle?",
                "What's your biggest CRM challenge?"
            ]
        else:
            questions = [
                "What's your primary business goal?",
                "Which features interest you most?",
                "What's your current biggest time-waster?"
            ]
        
        return questions[:3]  # Limit to 3 questions
    
    def _update_conversation_state(self, conversation: ConversationContext, 
                                 response: ContextualResponse):
        """Update conversation state based on response"""
        try:
            if response.requires_escalation:
                conversation.state = ConversationState.ESCALATED
                conversation.escalation_count += 1
            elif "thank" in conversation.messages[-1].content.lower():
                conversation.state = ConversationState.RESOLVED
            else:
                conversation.state = ConversationState.ACTIVE
            
            conversation.updated_at = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Failed to update conversation state: {e}")
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[ConversationContext]:
        """Get conversations for a user"""
        user_conversations = [
            conv for conv in self.conversations.values() 
            if conv.user_id == user_id
        ]
        
        # Sort by last activity
        user_conversations.sort(key=lambda c: c.last_activity, reverse=True)
        
        return user_conversations[:limit]
    
    def close_conversation(self, conversation_id: str, reason: str = "completed"):
        """Close a conversation"""
        try:
            if conversation_id in self.conversations:
                conversation = self.conversations[conversation_id]
                conversation.state = ConversationState.CLOSED
                conversation.updated_at = datetime.now()
                
                # Add to user's conversation history
                user_id = conversation.user_id
                if user_id in self.context_memory:
                    self.context_memory[user_id]["conversation_history"].append({
                        "conversation_id": conversation_id,
                        "summary": conversation.context_data.get("conversation_summary", ""),
                        "topics": conversation.context_data.get("key_topics", []),
                        "closed_at": datetime.now(),
                        "reason": reason
                    })
                
                logger.info(f"🔒 Closed conversation: {conversation_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to close conversation: {e}")
    
    def cleanup_old_conversations(self):
        """Clean up old conversations to free memory"""
        try:
            cutoff_time = datetime.now() - self.max_conversation_age
            
            old_conversations = [
                conv_id for conv_id, conv in self.conversations.items()
                if conv.last_activity < cutoff_time
            ]
            
            for conv_id in old_conversations:
                # Archive to user history before deleting
                conversation = self.conversations[conv_id]
                user_id = conversation.user_id
                
                if user_id in self.context_memory:
                    self.context_memory[user_id]["conversation_history"].append({
                        "conversation_id": conv_id,
                        "summary": conversation.context_data.get("conversation_summary", ""),
                        "topics": conversation.context_data.get("key_topics", []),
                        "archived_at": datetime.now(),
                        "reason": "auto_cleanup"
                    })
                
                del self.conversations[conv_id]
            
            logger.info(f"🧹 Cleaned up {len(old_conversations)} old conversations")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup conversations: {e}")
    
    def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        try:
            total_conversations = len(self.conversations)
            
            # Count by state
            state_counts = {}
            for conv in self.conversations.values():
                state = conv.state.value
                state_counts[state] = state_counts.get(state, 0) + 1
            
            # Count by channel
            channel_counts = {}
            for conv in self.conversations.values():
                channel = conv.channel
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
            
            # Average conversation length
            total_messages = sum(len(conv.messages) for conv in self.conversations.values())
            avg_length = total_messages / total_conversations if total_conversations > 0 else 0
            
            # Escalation rate
            escalated_conversations = len([c for c in self.conversations.values() if c.state == ConversationState.ESCALATED])
            escalation_rate = (escalated_conversations / total_conversations) * 100 if total_conversations > 0 else 0
            
            return {
                "total_conversations": total_conversations,
                "state_distribution": state_counts,
                "channel_distribution": channel_counts,
                "average_conversation_length": round(avg_length, 2),
                "escalation_rate": round(escalation_rate, 2),
                "active_users": len(set(conv.user_id for conv in self.conversations.values())),
                "context_memory_size": len(self.context_memory)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation statistics: {e}")
            return {}

# Global instance
context_system = ContextAwareResponseSystem()

def get_context_system() -> ContextAwareResponseSystem:
    """Get the global context-aware response system instance"""
    return context_system
