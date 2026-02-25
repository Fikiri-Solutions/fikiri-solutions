"""
Multi-channel Support System for Fikiri Solutions
Unified chatbot interface across web, API, and integration channels
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid
from abc import ABC, abstractmethod

from core.smart_faq_system import get_smart_faq
from core.knowledge_base_system import get_knowledge_base
from core.context_aware_responses import get_context_system
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class ChannelType(Enum):
    """Supported channel types"""
    WEB_CHAT = "web_chat"
    API = "api"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    WIDGET = "widget"

class MessageFormat(Enum):
    """Message format types"""
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    RICH_CARD = "rich_card"

class ResponseType(Enum):
    """Response types"""
    DIRECT_ANSWER = "direct_answer"
    FAQ_MATCH = "faq_match"
    KNOWLEDGE_SEARCH = "knowledge_search"
    CONTEXT_RESPONSE = "context_response"
    ESCALATION = "escalation"
    FALLBACK = "fallback"

@dataclass
class ChannelMessage:
    """Message from any channel"""
    id: str
    channel_type: ChannelType
    user_id: str
    content: str
    format: MessageFormat
    metadata: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

@dataclass
class ChannelResponse:
    """Response formatted for specific channel"""
    message_id: str
    channel_type: ChannelType
    content: str
    format: MessageFormat
    response_type: ResponseType
    confidence: float
    metadata: Dict[str, Any]
    suggested_actions: List[Dict[str, Any]]
    timestamp: datetime

@dataclass
class ChannelConfig:
    """Configuration for a specific channel"""
    channel_type: ChannelType
    enabled: bool
    settings: Dict[str, Any]
    authentication: Dict[str, Any]
    rate_limits: Dict[str, int]
    formatting_rules: Dict[str, Any]

class ChannelHandler(ABC):
    """Abstract base class for channel handlers"""
    
    def __init__(self, channel_type: ChannelType, config: ChannelConfig):
        self.channel_type = channel_type
        self.config = config
        self.is_enabled = config.enabled
    
    @abstractmethod
    def process_incoming_message(self, raw_message: Dict[str, Any]) -> ChannelMessage:
        """Process incoming message from channel"""
        raise NotImplementedError("process_incoming_message must be implemented by channel handlers")
    
    @abstractmethod
    def format_outgoing_response(self, response: ChannelResponse) -> Dict[str, Any]:
        """Format response for channel"""
        raise NotImplementedError("format_outgoing_response must be implemented by channel handlers")
    
    @abstractmethod
    def send_response(self, formatted_response: Dict[str, Any]) -> bool:
        """Send response through channel"""
        raise NotImplementedError("send_response must be implemented by channel handlers")
    
    def validate_message(self, message: ChannelMessage) -> bool:
        """Validate incoming message"""
        return bool(message.content and message.user_id)
    
    def apply_rate_limiting(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        # Simplified rate limiting - in production, use Redis or similar
        return True

class WebChatHandler(ChannelHandler):
    """Handler for web chat widget"""
    
    def process_incoming_message(self, raw_message: Dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            id=str(uuid.uuid4()),
            channel_type=ChannelType.WEB_CHAT,
            user_id=raw_message.get('user_id', 'anonymous'),
            content=raw_message.get('message', ''),
            format=MessageFormat.TEXT,
            metadata={
                'user_agent': raw_message.get('user_agent', ''),
                'ip_address': raw_message.get('ip_address', ''),
                'page_url': raw_message.get('page_url', ''),
                'session_data': raw_message.get('session_data', {})
            },
            timestamp=datetime.now(),
            session_id=raw_message.get('session_id'),
            conversation_id=raw_message.get('conversation_id')
        )
    
    def format_outgoing_response(self, response: ChannelResponse) -> Dict[str, Any]:
        formatted = {
            'type': 'message',
            'content': response.content,
            'format': response.format.value,
            'confidence': response.confidence,
            'response_type': response.response_type.value,
            'timestamp': response.timestamp.isoformat(),
            'suggested_actions': []
        }
        
        # Format suggested actions for web chat
        for action in response.suggested_actions:
            formatted['suggested_actions'].append({
                'type': 'button',
                'label': action.get('label', ''),
                'action': action.get('action', 'message'),
                'payload': action.get('payload', '')
            })
        
        # Add rich formatting if supported
        if response.format == MessageFormat.RICH_CARD:
            formatted['rich_content'] = response.metadata.get('rich_content', {})
        
        return formatted
    
    def send_response(self, formatted_response: Dict[str, Any]) -> bool:
        # In a real implementation, this would send via WebSocket or HTTP
        logger.info(f"📱 Sending web chat response: {formatted_response['content'][:50]}...")
        return True

class APIHandler(ChannelHandler):
    """Handler for REST API interactions"""
    
    def process_incoming_message(self, raw_message: Dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            id=str(uuid.uuid4()),
            channel_type=ChannelType.API,
            user_id=raw_message.get('user_id', 'api_user'),
            content=raw_message.get('query', ''),
            format=MessageFormat.JSON,
            metadata={
                'api_key': raw_message.get('api_key', ''),
                'endpoint': raw_message.get('endpoint', ''),
                'request_id': raw_message.get('request_id', ''),
                'client_info': raw_message.get('client_info', {})
            },
            timestamp=datetime.now(),
            session_id=raw_message.get('session_id')
        )
    
    def format_outgoing_response(self, response: ChannelResponse) -> Dict[str, Any]:
        return {
            'success': True,
            'response': response.content,
            'response_type': response.response_type.value,
            'confidence': response.confidence,
            'metadata': {
                'processing_time': response.metadata.get('processing_time', 0),
                'sources_used': response.metadata.get('sources_used', []),
                'context_applied': response.metadata.get('context_applied', False)
            },
            'suggested_actions': [
                {
                    'action': action.get('action', ''),
                    'parameters': action.get('payload', {})
                } for action in response.suggested_actions
            ],
            'timestamp': response.timestamp.isoformat()
        }
    
    def send_response(self, formatted_response: Dict[str, Any]) -> bool:
        # API responses are returned directly, not sent
        logger.info(f"🔌 API response prepared: {formatted_response.get('response_type', '')}")
        return True

class SlackHandler(ChannelHandler):
    """Handler for Slack integration"""
    
    def process_incoming_message(self, raw_message: Dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            id=str(uuid.uuid4()),
            channel_type=ChannelType.SLACK,
            user_id=raw_message.get('user', {}).get('id', 'slack_user'),
            content=raw_message.get('text', ''),
            format=MessageFormat.TEXT,
            metadata={
                'channel': raw_message.get('channel', ''),
                'team': raw_message.get('team', ''),
                'thread_ts': raw_message.get('thread_ts', ''),
                'user_name': raw_message.get('user', {}).get('name', '')
            },
            timestamp=datetime.now(),
            session_id=raw_message.get('channel', '')
        )
    
    def format_outgoing_response(self, response: ChannelResponse) -> Dict[str, Any]:
        formatted = {
            'text': response.content,
            'response_type': 'in_channel' if response.confidence > 0.8 else 'ephemeral'
        }
        
        # Add Slack-specific formatting
        if response.suggested_actions:
            blocks = [
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': response.content}
                }
            ]
            
            # Add action buttons
            if len(response.suggested_actions) > 0:
                actions = []
                for action in response.suggested_actions[:5]:  # Slack limit
                    actions.append({
                        'type': 'button',
                        'text': {'type': 'plain_text', 'text': action.get('label', '')},
                        'action_id': action.get('action', ''),
                        'value': json.dumps(action.get('payload', {}))
                    })
                
                blocks.append({
                    'type': 'actions',
                    'elements': actions
                })
            
            formatted['blocks'] = blocks
        
        return formatted
    
    def send_response(self, formatted_response: Dict[str, Any]) -> bool:
        # In real implementation, would use Slack Web API
        logger.info(f"💬 Sending Slack response: {formatted_response['text'][:50]}...")
        return True

class EmailHandler(ChannelHandler):
    """Handler for email-based interactions"""
    
    def process_incoming_message(self, raw_message: Dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            id=str(uuid.uuid4()),
            channel_type=ChannelType.EMAIL,
            user_id=raw_message.get('from_email', 'email_user'),
            content=raw_message.get('body', ''),
            format=MessageFormat.HTML if raw_message.get('html_body') else MessageFormat.TEXT,
            metadata={
                'subject': raw_message.get('subject', ''),
                'from_name': raw_message.get('from_name', ''),
                'to_email': raw_message.get('to_email', ''),
                'message_id': raw_message.get('message_id', ''),
                'thread_id': raw_message.get('thread_id', '')
            },
            timestamp=datetime.now(),
            session_id=raw_message.get('thread_id', '')
        )
    
    def format_outgoing_response(self, response: ChannelResponse) -> Dict[str, Any]:
        return {
            'subject': f"Re: {response.metadata.get('original_subject', 'Your Inquiry')}",
            'body_text': response.content,
            'body_html': self._convert_to_html(response.content),
            'reply_to': response.metadata.get('reply_to', 'support@fikirisolutions.com'),
            'in_reply_to': response.metadata.get('original_message_id', ''),
            'references': response.metadata.get('thread_references', [])
        }
    
    def _convert_to_html(self, text_content: str) -> str:
        """Convert text to HTML format"""
        html = text_content.replace('\n\n', '</p><p>')
        html = html.replace('\n', '<br>')
        return f"<p>{html}</p>"
    
    def send_response(self, formatted_response: Dict[str, Any]) -> bool:
        # In real implementation, would use SMTP or email service API
        logger.info(f"📧 Sending email response: {formatted_response['subject']}")
        return True

class MultiChannelSupportSystem:
    """Unified multi-channel chatbot system"""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize AI systems
        self.faq_system = get_smart_faq()
        self.knowledge_base = get_knowledge_base()
        self.context_system = get_context_system()
        
        # Initialize channel handlers
        self.channel_handlers = self._initialize_channel_handlers()
        
        # Message routing and processing
        self.message_processors = []
        self.response_enhancers = []
        
        # Statistics tracking
        self.channel_stats = {}
        
        logger.info("🌐 Multi-channel support system initialized")
    
    def _initialize_channel_handlers(self) -> Dict[ChannelType, ChannelHandler]:
        """Initialize all channel handlers"""
        handlers = {}
        
        # Web Chat Handler
        web_config = ChannelConfig(
            channel_type=ChannelType.WEB_CHAT,
            enabled=True,
            settings={'widget_theme': 'light', 'show_typing_indicator': True},
            authentication={'require_session': False},
            rate_limits={'messages_per_minute': 10, 'messages_per_hour': 100},
            formatting_rules={'max_length': 2000, 'allow_html': False}
        )
        handlers[ChannelType.WEB_CHAT] = WebChatHandler(ChannelType.WEB_CHAT, web_config)
        
        # API Handler
        api_config = ChannelConfig(
            channel_type=ChannelType.API,
            enabled=True,
            settings={'version': 'v1', 'format': 'json'},
            authentication={'require_api_key': True},
            rate_limits={'requests_per_minute': 60, 'requests_per_hour': 1000},
            formatting_rules={'max_length': 5000, 'include_metadata': True}
        )
        handlers[ChannelType.API] = APIHandler(ChannelType.API, api_config)
        
        # Slack Handler
        slack_config = ChannelConfig(
            channel_type=ChannelType.SLACK,
            enabled=getattr(self.config, 'slack_enabled', False),
            settings={'bot_token': getattr(self.config, 'slack_bot_token', '')},
            authentication={'verify_signature': True},
            rate_limits={'messages_per_minute': 20},
            formatting_rules={'use_blocks': True, 'max_buttons': 5}
        )
        handlers[ChannelType.SLACK] = SlackHandler(ChannelType.SLACK, slack_config)
        
        # Email Handler
        email_config = ChannelConfig(
            channel_type=ChannelType.EMAIL,
            enabled=True,
            settings={'smtp_server': getattr(self.config, 'smtp_server', '')},
            authentication={'smtp_auth': True},
            rate_limits={'emails_per_hour': 50},
            formatting_rules={'include_signature': True, 'auto_html': True}
        )
        handlers[ChannelType.EMAIL] = EmailHandler(ChannelType.EMAIL, email_config)
        
        return handlers
    
    def process_message(self, channel_type: ChannelType, raw_message: Dict[str, Any]) -> ChannelResponse:
        """Process message from any channel"""
        try:
            # Get channel handler
            handler = self.channel_handlers.get(channel_type)
            if not handler or not handler.is_enabled:
                raise ValueError(f"Channel not supported or disabled: {channel_type.value}")
            
            # Process incoming message
            message = handler.process_incoming_message(raw_message)
            
            # Validate message
            if not handler.validate_message(message):
                raise ValueError("Invalid message format")
            
            # Check rate limits
            if not handler.apply_rate_limiting(message.user_id):
                return self._create_rate_limit_response(message, channel_type)
            
            # Track message
            self._track_channel_message(channel_type, message)
            
            # Generate intelligent response
            response = self._generate_intelligent_response(message)
            
            # Format response for channel
            formatted_response = handler.format_outgoing_response(response)
            
            # Send response (if applicable for channel)
            if channel_type != ChannelType.API:  # API responses are returned, not sent
                handler.send_response(formatted_response)
            
            logger.info(f"✅ Processed {channel_type.value} message: {message.content[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to process {channel_type.value} message: {e}")
            return self._create_error_response(channel_type, str(e))
    
    def _generate_intelligent_response(self, message: ChannelMessage) -> ChannelResponse:
        """Generate intelligent response using all AI systems"""
        try:
            start_time = datetime.now()
            
            # Try different response strategies in order of preference
            
            # 1. Context-aware response (if conversation exists)
            if message.conversation_id:
                try:
                    context_response = self.context_system.generate_contextual_response(
                        message.conversation_id, message.content
                    )
                    
                    if context_response.confidence > 0.6:
                        return self._create_channel_response(
                            message, context_response.response, ResponseType.CONTEXT_RESPONSE,
                            context_response.confidence, {
                                'context_used': context_response.context_used,
                                'reasoning': context_response.reasoning,
                                'processing_time': (datetime.now() - start_time).total_seconds()
                            },
                            self._convert_to_channel_actions(context_response.suggested_actions)
                        )
                except Exception as e:
                    logger.warning(f"Context response failed: {e}")
            
            # 2. FAQ System
            try:
                faq_response = self.faq_system.search_faqs(message.content, max_results=3)
                
                if faq_response.success and faq_response.best_match and faq_response.best_match.confidence > 0.7:
                    best_match = faq_response.best_match
                    
                    # Record FAQ usage
                    self.faq_system.record_faq_usage(best_match.faq_entry.id, helpful=True)
                    
                    return self._create_channel_response(
                        message, best_match.faq_entry.answer, ResponseType.FAQ_MATCH,
                        best_match.confidence, {
                            'faq_id': best_match.faq_entry.id,
                            'match_type': best_match.match_type,
                            'processing_time': faq_response.processing_time
                        },
                        self._convert_suggested_questions_to_actions(faq_response.suggested_questions)
                    )
            except Exception as e:
                logger.warning(f"FAQ search failed: {e}")
            
            # 3. Knowledge Base Search
            try:
                kb_response = self.knowledge_base.search(message.content, limit=3)
                
                if kb_response.success and kb_response.results and kb_response.results[0].relevance_score > 0.5:
                    best_result = kb_response.results[0]
                    
                    return self._create_channel_response(
                        message, best_result.highlighted_content, ResponseType.KNOWLEDGE_SEARCH,
                        best_result.relevance_score / 10.0, {  # Normalize to 0-1
                            'document_id': best_result.document.id,
                            'document_title': best_result.document.title,
                            'match_explanation': best_result.match_explanation,
                            'processing_time': kb_response.search_time
                        },
                        self._convert_kb_suggestions_to_actions(kb_response.suggestions)
                    )
            except Exception as e:
                logger.warning(f"Knowledge base search failed: {e}")
            
            # 4. Fallback Response
            return self._create_fallback_response(message)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate intelligent response: {e}")
            return self._create_error_response(message.channel_type, str(e))
    
    def _create_channel_response(self, message: ChannelMessage, content: str,
                               response_type: ResponseType, confidence: float,
                               metadata: Dict[str, Any], suggested_actions: List[Dict[str, Any]]) -> ChannelResponse:
        """Create channel response"""
        
        # Adjust content format based on channel
        if message.channel_type == ChannelType.EMAIL:
            format_type = MessageFormat.HTML
        elif message.channel_type == ChannelType.SLACK:
            format_type = MessageFormat.MARKDOWN
        elif message.channel_type == ChannelType.API:
            format_type = MessageFormat.JSON
        else:
            format_type = MessageFormat.TEXT
        
        return ChannelResponse(
            message_id=str(uuid.uuid4()),
            channel_type=message.channel_type,
            content=content,
            format=format_type,
            response_type=response_type,
            confidence=confidence,
            metadata=metadata,
            suggested_actions=suggested_actions,
            timestamp=datetime.now()
        )
    
    def _create_fallback_response(self, message: ChannelMessage) -> ChannelResponse:
        """Create fallback response when no good matches found"""
        fallback_content = (
            "I don't have a specific answer for that question, but I'd be happy to help! "
            "You can try rephrasing your question, browse our help documentation, or contact our support team."
        )
        
        fallback_actions = [
            {'label': 'Browse Help Docs', 'action': 'browse_docs', 'payload': {}},
            {'label': 'Contact Support', 'action': 'contact_support', 'payload': {}},
            {'label': 'View FAQ', 'action': 'view_faq', 'payload': {}}
        ]
        
        return self._create_channel_response(
            message, fallback_content, ResponseType.FALLBACK, 0.3,
            {'fallback_reason': 'no_good_matches'}, fallback_actions
        )
    
    def _create_error_response(self, channel_type: ChannelType, error: str) -> ChannelResponse:
        """Create error response"""
        error_content = (
            "I apologize, but I encountered a technical issue while processing your request. "
            "Please try again in a moment, or contact our support team if the problem persists."
        )
        
        return ChannelResponse(
            message_id=str(uuid.uuid4()),
            channel_type=channel_type,
            content=error_content,
            format=MessageFormat.TEXT,
            response_type=ResponseType.FALLBACK,
            confidence=0.1,
            metadata={'error': error, 'requires_escalation': True},
            suggested_actions=[
                {'label': 'Contact Support', 'action': 'contact_support', 'payload': {'error': error}}
            ],
            timestamp=datetime.now()
        )
    
    def _create_rate_limit_response(self, message: ChannelMessage, channel_type: ChannelType) -> ChannelResponse:
        """Create rate limit response"""
        rate_limit_content = (
            "You've reached the message limit for this time period. "
            "Please wait a moment before sending another message, or contact our support team for immediate assistance."
        )
        
        return self._create_channel_response(
            message, rate_limit_content, ResponseType.FALLBACK, 0.9,
            {'rate_limited': True}, [
                {'label': 'Contact Support', 'action': 'contact_support', 'payload': {}}
            ]
        )
    
    def _convert_to_channel_actions(self, suggested_actions: List[str]) -> List[Dict[str, Any]]:
        """Convert suggested actions to channel-specific format"""
        actions = []
        
        for action in suggested_actions:
            actions.append({
                'label': action,
                'action': 'message',
                'payload': {'message': action}
            })
        
        return actions
    
    def _convert_suggested_questions_to_actions(self, questions: List[str]) -> List[Dict[str, Any]]:
        """Convert suggested questions to actions"""
        actions = []
        
        for question in questions[:3]:  # Limit to 3
            actions.append({
                'label': question,
                'action': 'ask_question',
                'payload': {'question': question}
            })
        
        return actions
    
    def _convert_kb_suggestions_to_actions(self, suggestions: List[str]) -> List[Dict[str, Any]]:
        """Convert knowledge base suggestions to actions"""
        actions = []
        
        for suggestion in suggestions[:3]:  # Limit to 3
            actions.append({
                'label': f"Search: {suggestion}",
                'action': 'search',
                'payload': {'query': suggestion}
            })
        
        return actions
    
    def _track_channel_message(self, channel_type: ChannelType, message: ChannelMessage):
        """Track channel usage statistics"""
        try:
            channel_key = channel_type.value
            
            if channel_key not in self.channel_stats:
                self.channel_stats[channel_key] = {
                    'message_count': 0,
                    'unique_users': set(),
                    'first_message': datetime.now(),
                    'last_message': datetime.now()
                }
            
            stats = self.channel_stats[channel_key]
            stats['message_count'] += 1
            stats['unique_users'].add(message.user_id)
            stats['last_message'] = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Failed to track channel message: {e}")
    
    def get_supported_channels(self) -> List[Dict[str, Any]]:
        """Get list of supported channels"""
        channels = []
        
        for channel_type, handler in self.channel_handlers.items():
            channels.append({
                'channel_type': channel_type.value,
                'enabled': handler.is_enabled,
                'settings': handler.config.settings,
                'rate_limits': handler.config.rate_limits
            })
        
        return channels
    
    def enable_channel(self, channel_type: ChannelType, config: Dict[str, Any] = None) -> bool:
        """Enable a specific channel"""
        try:
            if channel_type in self.channel_handlers:
                handler = self.channel_handlers[channel_type]
                handler.is_enabled = True
                
                if config:
                    handler.config.settings.update(config)
                
                logger.info(f"✅ Enabled channel: {channel_type.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to enable channel {channel_type.value}: {e}")
            return False
    
    def disable_channel(self, channel_type: ChannelType) -> bool:
        """Disable a specific channel"""
        try:
            if channel_type in self.channel_handlers:
                self.channel_handlers[channel_type].is_enabled = False
                logger.info(f"🚫 Disabled channel: {channel_type.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to disable channel {channel_type.value}: {e}")
            return False
    
    def get_channel_statistics(self) -> Dict[str, Any]:
        """Get channel usage statistics"""
        try:
            stats = {}
            
            for channel_key, channel_stats in self.channel_stats.items():
                stats[channel_key] = {
                    'message_count': channel_stats['message_count'],
                    'unique_users': len(channel_stats['unique_users']),
                    'first_message': channel_stats['first_message'].isoformat(),
                    'last_message': channel_stats['last_message'].isoformat(),
                    'enabled': channel_key in [h.channel_type.value for h in self.channel_handlers.values() if h.is_enabled]
                }
            
            # Overall statistics
            total_messages = sum(s['message_count'] for s in stats.values())
            total_users = len(set().union(*[s['unique_users'] for s in self.channel_stats.values()]))
            
            return {
                'channel_stats': stats,
                'total_messages': total_messages,
                'total_unique_users': total_users,
                'active_channels': len([h for h in self.channel_handlers.values() if h.is_enabled]),
                'total_channels': len(self.channel_handlers)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get channel statistics: {e}")
            return {}
    
    def test_channel(self, channel_type: ChannelType, test_message: str = "Hello, this is a test message") -> Dict[str, Any]:
        """Test a specific channel"""
        try:
            # Create test message
            test_raw_message = {
                'user_id': 'test_user',
                'message': test_message,
                'session_id': 'test_session'
            }
            
            # Process message
            response = self.process_message(channel_type, test_raw_message)
            
            return {
                'success': True,
                'channel_type': channel_type.value,
                'test_message': test_message,
                'response': response.content,
                'confidence': response.confidence,
                'response_type': response.response_type.value,
                'processing_time': (datetime.now() - response.timestamp).total_seconds()
            }
            
        except Exception as e:
            return {
                'success': False,
                'channel_type': channel_type.value,
                'error': str(e)
            }

# Global instance
multi_channel_system = MultiChannelSupportSystem()

def get_multi_channel_system() -> MultiChannelSupportSystem:
    """Get the global multi-channel support system instance"""
    return multi_channel_system
