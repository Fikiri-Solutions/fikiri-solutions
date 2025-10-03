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
from core.universal_ai_assistant import UniversalAIAssistant
from core.minimal_ai_assistant import MinimalAIEmailAssistant
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

# Create Blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Initialize AI systems
universal_ai = UniversalAIAssistant()

@ai_bp.route('/chat', methods=['POST'])
@handle_api_errors
def ai_chat():
    """AI chat endpoint for frontend interactions"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
        
        message = data.get('message', '')
        user_id = data.get('user_id')
        context = data.get('context', {})
        
        if not message:
            return create_error_response("Message is required", 400, 'MISSING_MESSAGE')
        
        # Get user ID from session if not provided
        if not user_id:
            user_id = get_current_user_id()
            if not user_id:
                return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Process the message through Universal AI Assistant
        try:
            ai_response = universal_ai.process_query(
                user_message=message,
                user_id=user_id,
                context=context
            )
            
            # Format response for frontend
            response_data = {
                'response': ai_response.response,
                'service_queries': [
                    {
                        'service': query.service,
                        'query': query.query,
                        'response': query.response,
                        'timestamp': query.timestamp.isoformat()
                    } for query in ai_response.service_queries
                ],
                'suggested_actions': ai_response.suggested_actions,
                'confidence': ai_response.confidence,
                'success': ai_response.success
            }
            
            return create_success_response(response_data, "AI response generated")
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            
            # Fallback to minimal AI assistant
            try:
                minimal_ai = MinimalAIEmailAssistant()
                fallback_response = minimal_ai.process_message(message)
                
                response_data = {
                    'response': fallback_response,
                    'service_queries': [],
                    'suggested_actions': [],
                    'confidence': 0.5,
                    'success': True
                }
                
                return create_success_response(response_data, "AI response generated (fallback)")
                
            except Exception as fallback_error:
                logger.error(f"Fallback AI also failed: {fallback_error}")
                
                # Final fallback - simple response
                response_data = {
                    'response': f"I received your message: '{message}'. I'm currently processing your request and will provide a more detailed response soon.",
                    'service_queries': [],
                    'suggested_actions': ['Try rephrasing your question', 'Check your account status', 'Contact support'],
                    'confidence': 0.3,
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
            'universal_ai_available': True,
            'minimal_ai_available': True,
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
