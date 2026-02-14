"""
AI Chat API for Fikiri Solutions
Provides /api/ai/chat endpoint for frontend AI interactions
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import Blueprint, request, jsonify

from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.ai.llm_router import LLMRouter
from core.secure_sessions import get_current_user_id
from core.jwt_auth import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Create Blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

_llm_router: Optional[LLMRouter] = None

def _get_llm_router() -> Optional[LLMRouter]:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter(api_key=None)
    return _llm_router

def _generate_contextual_fallback(message: str, user_id: int) -> str:
    """Generate a context-aware fallback response based on user message"""
    message_lower = message.lower()
    
    # Lead analysis queries
    if any(word in message_lower for word in ['analyze', 'analyze my', 'leads', 'priorities', 'priority', 'suggest']):
        return """I can help you analyze your leads! Here's what I can do:

📊 **Lead Analysis:**
- Review your leads by stage (new, contacted, qualified, etc.)
- Identify high-priority leads based on engagement
- Suggest follow-up actions for each lead

🎯 **To get started:**
1. Go to the CRM page to see all your leads
2. Use the filters to view leads by stage or date
3. Check lead scores to identify hot prospects

Would you like me to show you your leads sorted by priority, or help you set up automated lead scoring?"""
    
    # Email writing queries
    elif any(word in message_lower for word in ['write', 'email', 'response', 'reply', 'draft', 'compose']):
        return """I can help you write professional email responses! Here's how:

✍️ **Email Writing Assistance:**
- Generate professional email drafts
- Create personalized responses to leads
- Suggest tone and content based on the recipient

📝 **To write an email:**
1. Go to the AI Assistant page
2. Select a lead from your CRM
3. Click "Generate Reply" to create a personalized response
4. Edit and customize the draft before sending

Would you like to write a response to a specific lead, or create a template email?"""
    
    # Automation/workflow queries
    elif any(word in message_lower for word in ['automation', 'workflow', 'automate', 'set up', 'create rule']):
        return """I can help you set up automated workflows! Here's what's available:

⚙️ **Automation Options:**
- **Email Automation**: Auto-reply to new leads, follow-ups, and more
- **CRM Automation**: Auto-create leads from emails, update stages
- **Lead Scoring**: Automatically score and prioritize leads
- **Slack Notifications**: Get alerts for important events

🔧 **To set up automations:**
1. Go to the Automations page
2. Browse pre-built automation presets
3. Toggle them ON to activate
4. Customize triggers and actions as needed

Would you like help setting up a specific automation, or would you prefer to see available presets?"""
    
    # General help
    else:
        return """I'm here to help with Fikiri Solutions! Here's what I can assist with:

📧 **Email Management:**
- Analyze your email activity
- Help write professional responses
- Set up email automation

👥 **Lead & CRM:**
- Analyze your leads and suggest priorities
- Track lead progress through your pipeline
- Generate reports and insights

⚙️ **Automation:**
- Set up automated workflows
- Create email automation rules
- Configure lead scoring

What would you like help with today?"""

def _get_suggested_actions(message: str) -> List[str]:
    """Get suggested actions based on user message"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['analyze', 'leads', 'priority']):
        return ['View CRM Dashboard', 'Check Lead Scores', 'Review Recent Leads']
    elif any(word in message_lower for word in ['write', 'email', 'response']):
        return ['Go to AI Assistant', 'Select a Lead', 'Generate Reply']
    elif any(word in message_lower for word in ['automation', 'workflow']):
        return ['View Automations Page', 'Browse Presets', 'Create Custom Rule']
    else:
        return ['Check Dashboard', 'View CRM', 'Explore Features']

def _generate_simple_fallback(message: str) -> str:
    """Generate a simple fallback response when all else fails"""
    return f"I received your message: '{message}'. I'm currently processing your request and will provide a more detailed response soon. In the meantime, you can explore the CRM, Automations, or Dashboard pages for more information."

@ai_bp.route('/chat', methods=['POST'])
@handle_api_errors
def ai_chat():
    """AI chat endpoint for frontend interactions"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
        
        message = data.get('message', '')
        context = data.get('context', {})
        
        if not message:
            return create_error_response("Message is required", 400, 'MISSING_MESSAGE')
        
        # Try to get user_id from JWT token first, then fall back to request body
        user_id = None
        user_data = None
        
        try:
            # Try JWT authentication (optional)
            user_data = get_current_user()
            if user_data:
                user_id = user_data.get('user_id')
        except Exception as auth_error:
            # JWT not available, continue to fallback
            logger.debug("JWT lookup failed, falling back to session auth: %s", auth_error)
        
        # Fallback to session-based auth
        if not user_id:
            user_id = get_current_user_id()
        
        # Final fallback to request body (for development/testing)
        if not user_id:
            user_id = data.get('user_id')
            if not user_id:
                return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Try real LLM first; fall back to contextual response on failure
        try:
            router = _get_llm_router()
            if router and router.client and router.client.is_enabled():
                llm_result = router.process(
                    input_data=message,
                    intent='general',
                    context={
                        'user_id': user_id,
                        'channel': 'ai_chat',
                        'suggested_actions': _get_suggested_actions(message),
                    }
                )
                if llm_result.get('success'):
                    response_data = {
                        'response': llm_result.get('content', ''),
                        'service_queries': [],
                        'suggested_actions': _get_suggested_actions(message),
                        'confidence': 0.75,
                        'success': True
                    }
                    return create_success_response(response_data, "AI response generated")
                logger.warning("LLM router failed, falling back: %s", llm_result.get('error'))
        except Exception as llm_error:
            logger.error("LLM chat failed, falling back: %s", llm_error)

        # Contextual fallback
        try:
            response = _generate_contextual_fallback(message, user_id)
            response_data = {
                'response': response,
                'service_queries': [],
                'suggested_actions': _get_suggested_actions(message),
                'confidence': 0.6,
                'success': True
            }
            return create_success_response(response_data, "AI response generated")
        except Exception as fallback_error:
            logger.error(f"Response generation failed: {fallback_error}")
            response_data = {
                'response': _generate_simple_fallback(message),
                'service_queries': [],
                'suggested_actions': _get_suggested_actions(message),
                'confidence': 0.4,
                'success': True
            }
            return create_success_response(response_data, "AI response generated (simple fallback)")
        
    except Exception as e:
        logger.error(f"AI chat endpoint error: {e}")
        return create_error_response("AI chat failed", 500, "AI_CHAT_ERROR")

@ai_bp.route('/status', methods=['GET'])
@handle_api_errors
def ai_status():
    """Get AI system status"""
    try:
        status_data = {
            'ai_available': True,
            'services': {
                'email_parser': True,
                'crm_service': True,
                'automation_engine': True,
                'analytics': True,
                'privacy_manager': True,
                'gmail_sync': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return create_success_response(status_data, "AI system status retrieved")
        
    except Exception as e:
        logger.error(f"AI status error: {e}")
        return create_error_response("Failed to get AI status", 500, "AI_STATUS_ERROR")
# Force deployment
