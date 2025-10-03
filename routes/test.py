#!/usr/bin/env python3
"""
Test and Debug Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
import os
import json
import logging
from datetime import datetime

# Import testing modules
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.user_auth import user_auth_manager
from core.minimal_ai_assistant import create_ai_assistant
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_ml_scoring import MinimalMLScoring
from core.enhanced_crm_service import enhanced_crm_service
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

# Create test blueprint
test_bp = Blueprint("test", __name__, url_prefix="/api")

@test_bp.route('/test/debug', methods=['GET'])
@handle_api_errors
def debug_endpoint():
    """Debug endpoint for system status"""
    try:
        debug_info = {
            'environment': 'production' if os.getenv('ENVIRONMENT') == 'production' else 'development',
            'database_connected': True,  # Assume connected if we get here
            'redis_available': bool(os.getenv('REDIS_URL')),
            'openai_available': bool(os.getenv('OPENAI_API_KEY')),
            'timestamp': datetime.now().isoformat()
        }
        
        return create_success_response(debug_info, 'Debug information retrieved')
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return create_error_response("Debug endpoint failed", 500, 'DEBUG_ERROR')

@test_bp.route('/test/signup-step', methods=['POST'])
@handle_api_errors
def test_signup_step():
    """Test specific signup steps for debugging"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    step = data.get('step', 1)
    email = data.get('email', f'test_{step}@example.com')
    
    try:
        if step == 1:
            # Test user creation
            result = user_auth_manager.create_user(
                email=email,
                password='testpass123',
                name='Test User'
            )
            return create_success_response({'step': step, 'result': result}, 'Signup step 1 completed')
            
        elif step == 2:
            # Test email sending (mock)
            return create_success_response({'step': step, 'message': 'Email sent'}, 'Signup step 2 completed')
            
        elif step == 3:
            # Test onboarding completion
            return create_success_response({'step': step, 'onboarding_completed': True}, 'Signup step 3 completed')
            
        else:
            return create_error_response("Invalid step number", 400, 'INVALID_STEP')
            
    except Exception as e:
        logger.error(f"Test signup step error: {e}")
        return create_error_response("Test signup step failed", 500, 'TEST_SIGNUP_ERROR')

@test_bp.route('/test/email-parser', methods=['POST'])
@handle_api_errors
def test_email_parser():
    """Test email parsing functionality"""
    data = request.get_json()
    if not data or 'email_content' not in data:
        return create_error_response("Email content is required", 400, 'MISSING_EMAIL_CONTENT')

    try:
        parser = MinimalEmailParser()
        
        email_content = data['email_content']
        parsed_result = parser.parse_email(email_content)
        
        return create_success_response({
            'original_content': email_content,
            'parsed_result': parsed_result
        }, 'Email parsing test completed')
        
    except Exception as e:
        logger.error(f"Email parser test error: {e}")
        return create_error_response("Email parser test failed", 500, 'EMAIL_PARSER_TEST_ERROR')

@test_bp.route('/test/email-actions', methods=['POST'])
@handle_api_errors
def test_email_actions():
    """Test email action functionality"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    try:
        actions = MinimalEmailActions()
        
        action_type = data.get('action_type', 'mark_read')
        email_id = data.get('email_id', 'test_email_id')
        
        action_result = actions.execute_action(action_type, email_id, data.get('params', {}))
        
        return create_success_response({
            'action_type': action_type,
            'email_id': email_id,
            'action_result': action_result
        }, 'Email action test completed')
        
    except Exception as e:
        logger.error(f"Email actions test error: {e}")
        return create_error_response("Email actions test failed", 500, 'EMAIL_ACTIONS_TEST_ERROR')

@test_bp.route('/test/crm', methods=['POST'])
@handle_api_errors
def test_crm():
    """Test CRM functionality"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        test_action = data.get('action', 'create_lead')
        
        if test_action == 'create_lead':
            lead_data = {
                'name': data.get('name', 'Test Lead'),
                'email': data.get('email', 'test@example.com'),
                'company': data.get('company', 'Test Company')
            }
            
            lead = enhanced_crm_service.create_lead(user_id, lead_data)
            
            return create_success_response({
                'action': test_action,
                'result': lead
            }, 'CRM test completed')
            
        elif test_action == 'get_leads':
            leads = enhanced_crm_service.get_leads(user_id)
            
            return create_success_response({
                'action': test_action,
                'leads_count': len(leads) if leads else 0
            }, 'CRM test completed')
            
        else:
            return create_error_response("Invalid test action", 400, 'INVALID_TEST_ACTION')
            
    except Exception as e:
        logger.error(f"CRM test error: {e}")
        return create_error_response("CRM test failed", 500, 'CRM_TEST_ERROR')

@test_bp.route('/test/ai-assistant', methods=['POST'])
@handle_api_errors
def test_ai_assistant():
    """Test AI assistant functionality"""
    data = request.get_json()
    if not data or 'prompt' not in data:
        return create_error_response("Prompt is required", 400, 'MISSING_PROMPT')

    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return create_error_response("OpenAI API key not configured", 500, 'OPENAI_NOT_CONFIGURED')

        assistant = create_ai_assistant(api_key)
        
        prompt = data['prompt']
        context = data.get('context', {})
        
        response = assistant.generate_response(prompt, context)
        
        return create_success_response({
            'prompt': prompt,
            'context': context,
            'response': response
        }, 'AI assistant test completed')
        
    except Exception as e:
        logger.error(f"AI assistant test error: {e}")
        return create_error_response("AI assistant test failed", 500, 'AI_ASSISTANT_TEST_ERROR')

@test_bp.route('/test/openai-key', methods=['GET'])
@handle_api_errors
def test_openai_key():
    """Test OpenAI API key configuration"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key:
            # Test API connectivity (optional)
            return create_success_response({
                'openai_configured': True,
                'key_length': len(api_key),
                'key_prefix': api_key[:8] + '...'
            }, 'OpenAI API key is configured')
        else:
            return create_error_response("OpenAI API key not found", 404, 'OPENAI_NOT_CONFIGURED')
            
    except Exception as e:
        logger.error(f"OpenAI key test error: {e}")
        return create_error_response("OpenAI key test failed", 500, 'OPENAI_KEY_TEST_ERROR')

@test_bp.route('/test/ml-scoring', methods=['POST'])
@handle_api_errors
def test_ml_scoring():
    """Test ML scoring functionality"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    try:
        scorer = MinimalMLScoring()
        
        input_data = data.get('data', {})
        score_type = data.get('score_type', 'email_priority')
        
        score = scorer.calculate_score(input_data, score_type)
        
        return create_success_response({
            'input_data': input_data,
            'score_type': score_type,
            'score': score
        }, 'ML scoring test completed')
        
    except Exception as e:
        logger.error(f"ML scoring test error: {e}")
        return create_error_response("ML scoring test failed", 500, 'ML_SCORING_TEST_ERROR')

@test_bp.route('/ai/test', methods=['POST'])
@handle_api_errors
def ai_test():
    """Comprehensive AI functionality test"""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return create_error_response("OpenAI API key not configured", 500, 'OPENAI_NOT_CONFIGURED')

        assistant = create_ai_assistant(api_key)
        
        test_type = data.get('test_type', 'response_generation')
        test_prompt = data.get('prompt', 'Test prompt')
        
        result = assistant.test_functionality(test_type, test_prompt)
        
        return create_success_response({
            'test_type': test_type,
            'test_prompt': test_prompt,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, 'AI test completed successfully')
        
    except Exception as e:
        logger.error(f"AI test error: {e}")
        return create_error_response("AI test failed", 500, 'AI_TEST_ERROR')
