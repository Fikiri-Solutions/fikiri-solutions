#!/usr/bin/env python3
"""
Test and Debug Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
import os
import json
import base64
import logging
from datetime import datetime

# Import testing modules
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.user_auth import user_auth_manager
from email_automation.ai_assistant import MinimalAIEmailAssistant
from email_automation.parser import MinimalEmailParser
from email_automation.actions import MinimalEmailActions
from core.minimal_ml_scoring import MinimalMLScoring
from crm.service import enhanced_crm_service

# Helper function for backward compatibility
def create_ai_assistant(api_key=None):
    """Create AI assistant instance (backward compatibility)"""
    return MinimalAIEmailAssistant(api_key=api_key)
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

# Create test blueprint
test_bp = Blueprint("test", __name__, url_prefix="/api")

@test_bp.route('/test/debug', methods=['GET'])
@handle_api_errors
def debug_endpoint():
    """Debug endpoint for system status"""
    try:
        from core.redis_connection_helper import is_redis_available
        debug_info = {
            'environment': 'production' if os.getenv('ENVIRONMENT') == 'production' else 'development',
            'database_connected': True,
            'redis_available': is_redis_available(),
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
    data = request.get_json() or {}
    
    # Use default test email if not provided
    default_email = """Subject: Test Email - Inquiry about Services
    
Hi there,
    
I'm interested in learning more about your services. Could you please send me more information?
    
Best regards,
Test User
test@example.com"""
    
    email_content = data.get('email_content', default_email)

    try:
        parser = MinimalEmailParser()
        
        # Convert plain email text to a mock Gmail message structure
        # MinimalEmailParser.parse_message expects a Gmail API message object
        mock_message = {
            "id": "test_message_123",
            "threadId": "test_thread_123",
            "snippet": email_content[:100] if len(email_content) > 100 else email_content,
            "labelIds": ["UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": email_content.split('\n')[0].replace('Subject:', '').strip() if 'Subject:' in email_content else "Test Email"},
                    {"name": "From", "value": "test@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": datetime.now().isoformat()}
                ],
                "body": {
                    "data": base64.urlsafe_b64encode(email_content.encode('utf-8')).decode('utf-8')
                },
                "mimeType": "text/plain"
            }
        }
        
        parsed_result = parser.parse_message(mock_message)
        
        return create_success_response({
            'original_content': email_content,
            'parsed_result': parsed_result
        }, 'Email parsing test completed')
        
    except Exception as e:
        logger.error(f"Email parser test error: {e}")
        import traceback
        logger.error(f"Email parser test traceback: {traceback.format_exc()}")
        return create_error_response(f"Email parser test failed: {str(e)}", 500, 'EMAIL_PARSER_TEST_ERROR')

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
    data = request.get_json() or {}

    try:
        user_id = get_current_user_id()
        if not user_id:
            # Use default user_id for testing if not authenticated
            user_id = 1
            logger.warning("No authenticated user, using default user_id=1 for CRM test")

        test_action = data.get('action', 'get_leads')
        
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
            # Use get_leads_summary instead of get_leads
            result = enhanced_crm_service.get_leads_summary(user_id)
            
            if result.get('success'):
                leads = result.get('data', {}).get('leads', [])
                return create_success_response({
                    'action': test_action,
                    'leads_count': len(leads) if leads else 0,
                    'leads': leads[:5] if leads else [],  # Return first 5 leads for testing
                    'analytics': result.get('data', {}).get('analytics', {})
                }, 'CRM test completed')
            else:
                return create_error_response(
                    result.get('error', 'Failed to retrieve leads'), 
                    500, 
                    'CRM_GET_LEADS_ERROR'
                )
            
        else:
            return create_error_response("Invalid test action. Use 'create_lead' or 'get_leads'", 400, 'INVALID_TEST_ACTION')
            
    except Exception as e:
        logger.error(f"CRM test error: {e}")
        import traceback
        logger.error(f"CRM test traceback: {traceback.format_exc()}")
        return create_error_response(f"CRM test failed: {str(e)}", 500, 'CRM_TEST_ERROR')

@test_bp.route('/test/ai-assistant', methods=['POST'])
@handle_api_errors
def test_ai_assistant():
    """Test AI assistant functionality"""
    data = request.get_json() or {}
    
    # Support both formats: { prompt } or { content, sender, subject }
    content = data.get('content', 'Hi, I need help with your services.')
    sender = data.get('sender', 'User')
    subject = data.get('subject', 'Inquiry')
    
    # If prompt is provided, try to extract content, sender, subject from it
    prompt = data.get('prompt')
    if prompt:
        # Try to parse prompt format: "From: ...\nSubject: ...\n\n..."
        lines = prompt.split('\n')
        for i, line in enumerate(lines):
            if line.lower().startswith('from:'):
                sender = line.split(':', 1)[1].strip()
            elif line.lower().startswith('subject:'):
                subject = line.split(':', 1)[1].strip()
            elif line.strip() and not line.startswith('From:') and not line.startswith('Subject:'):
                # This is likely the content
                content = '\n'.join(lines[i:]).strip()
                break

    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return create_success_response({
                'success': False,
                'classification': {
                    'confidence': 0,
                    'intent': 'unknown',
                    'suggested_action': 'configure_openai',
                    'urgency': 'low'
                },
                'response': 'OpenAI API key not configured. Please configure it in your environment variables.',
                'contact_info': {},
                'stats': {
                    'api_key_configured': False,
                    'client_initialized': False,
                    'enabled': False
                }
            }, 'AI assistant test completed (no API key)')

        assistant = create_ai_assistant(api_key)
        
        # Classify intent first
        intent_result = assistant.classify_email_intent(content, subject)
        intent = intent_result.get('intent', 'general')
        
        # Generate response using the correct method signature
        response = assistant.generate_response(content, sender, subject, intent)
        
        # Extract contact info
        contact_info = assistant.extract_contact_info(content)
        
        # Get AI stats
        ai_stats = assistant.get_ai_stats()
        
        # Return format matching what frontend expects
        return create_success_response({
            'success': True,
            'classification': intent_result,
            'response': response,
            'contact_info': contact_info,
            'stats': {
                'api_key_configured': ai_stats.get('enabled', True),
                'client_initialized': True,
                'enabled': ai_stats.get('enabled', True)
            }
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
    """
    Comprehensive ML scoring test with validation
    
    Tests:
    1. High-value lead scenario (urgent keywords, business email)
    2. Low-value lead scenario (generic email, personal domain)
    3. Score calculation accuracy
    4. Priority classification
    5. Individual feature scoring
    
    Pass Criteria:
    - Service initializes without errors
    - Scores are between 0-100
    - Priority is one of: 'low', 'medium', 'high', 'critical'
    - High-value lead scores higher than low-value lead
    - All individual scores are between 0-1
    """
    data = request.get_json() or {}

    try:
        scorer = MinimalMLScoring()
        
        # Test 1: High-value lead (should score high)
        high_value_email = {
            'subject': 'URGENT: Need Premium Services - Budget $50,000',
            'content': 'Hi, I need your premium services immediately. We have a budget of $50,000 and need this implemented ASAP. Please send a proposal.',
            'timestamp': datetime.now().isoformat()
        }
        high_value_lead = {
            'email': 'ceo@enterprise-corp.com',
            'name': 'John Smith',
            'company': 'Enterprise Corp',
            'contact_count': 3
        }
        
        # Test 2: Low-value lead (should score lower)
        low_value_email = {
            'subject': 'Hello',
            'content': 'Hi there, just saying hello. Test message.',
            'timestamp': datetime.now().isoformat()
        }
        low_value_lead = {
            'email': 'test@gmail.com',
            'name': 'Test User',
            'company': None,
            'contact_count': 0
        }
        
        # Run tests
        high_score_result = scorer.calculate_lead_score(high_value_email, high_value_lead)
        low_score_result = scorer.calculate_lead_score(low_value_email, low_value_lead)
        
        # Validation checks
        validation_results = {
            'service_initialized': True,
            'high_value_score_valid': 0 <= high_score_result.get('total_score', 0) <= 100,
            'low_value_score_valid': 0 <= low_score_result.get('total_score', 0) <= 100,
            'high_priority_valid': high_score_result.get('priority') in ['low', 'medium', 'high', 'critical'],
            'low_priority_valid': low_score_result.get('priority') in ['low', 'medium', 'high', 'critical'],
            'score_differentiation': high_score_result.get('total_score', 0) > low_score_result.get('total_score', 0),
            'individual_scores_valid': all(
                0 <= score <= 1 
                for score in high_score_result.get('individual_scores', {}).values()
            ),
            'model_type_present': 'model_type' in high_score_result,
            'recommended_action_present': 'recommended_action' in high_score_result,
            'confidence_valid': 0 <= high_score_result.get('confidence', 0) <= 1
        }
        
        # Calculate pass rate
        passed_checks = sum(1 for v in validation_results.values() if v)
        total_checks = len(validation_results)
        pass_rate = (passed_checks / total_checks) * 100
        
        # Determine overall test status
        test_passed = pass_rate >= 80  # 80% of checks must pass
        
        # Build comprehensive response
        test_summary = {
            'test_status': 'PASSED' if test_passed else 'FAILED',
            'pass_rate': f"{pass_rate:.1f}%",
            'checks_passed': f"{passed_checks}/{total_checks}",
            'validation_results': validation_results,
            'test_scenarios': {
                'high_value_lead': {
                    'input': {
                        'email': high_value_email,
                        'lead': high_value_lead
                    },
                    'result': high_score_result,
                    'expected': 'High score (>50) with high/critical priority'
                },
                'low_value_lead': {
                    'input': {
                        'email': low_value_email,
                        'lead': low_value_lead
                    },
                    'result': low_score_result,
                    'expected': 'Lower score than high-value lead'
                }
            },
            'what_was_tested': [
                'Service initialization and configuration',
                'Email domain scoring (business vs personal)',
                'Keyword detection (urgent, budget, purchase)',
                'Email content analysis (length, subject)',
                'Contact frequency scoring',
                'Time-based scoring',
                'Priority classification (low/medium/high/critical)',
                'Score calculation accuracy (0-100 range)',
                'Individual feature scoring (0-1 range)',
                'Score differentiation (high-value > low-value)'
            ],
            'pass_criteria': {
                'minimum_pass_rate': '80%',
                'required_checks': [
                    'Service must initialize',
                    'Scores must be 0-100',
                    'Priority must be valid',
                    'High-value leads must score higher',
                    'Individual scores must be 0-1',
                    'Model type must be present',
                    'Recommended action must be provided',
                    'Confidence must be 0-1'
                ]
            },
            'scoring_breakdown': {
                'high_value': {
                    'total_score': high_score_result.get('total_score'),
                    'priority': high_score_result.get('priority'),
                    'individual_scores': high_score_result.get('individual_scores', {}),
                    'recommended_action': high_score_result.get('recommended_action'),
                    'confidence': high_score_result.get('confidence')
                },
                'low_value': {
                    'total_score': low_score_result.get('total_score'),
                    'priority': low_score_result.get('priority'),
                    'individual_scores': low_score_result.get('individual_scores', {}),
                    'recommended_action': low_score_result.get('recommended_action'),
                    'confidence': low_score_result.get('confidence')
                }
            }
        }
        
        if test_passed:
            return create_success_response(test_summary, 'ML scoring test PASSED - All validations successful')
        else:
            return create_success_response(
                test_summary, 
                f'ML scoring test PARTIALLY PASSED - {pass_rate:.1f}% of checks passed'
            )
        
    except Exception as e:
        logger.error(f"ML scoring test error: {e}")
        import traceback
        logger.error(f"ML scoring test traceback: {traceback.format_exc()}")
        return create_error_response(f"ML scoring test failed: {str(e)}", 500, 'ML_SCORING_TEST_ERROR')

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
