#!/usr/bin/env python3
"""
Expert API Endpoints
Endpoints for expert teams, escalated questions, and Q&A management
"""

import json
import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from core.expert_escalation import get_escalation_engine, EscalationStatus
from core.expert_manager import get_expert_manager
from core.chatbot_feedback import get_feedback_system
from core.chatbot_smart_faq_api import chatbot_bp
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.smart_faq_system import get_smart_faq
from core.knowledge_base_system import get_knowledge_base, DocumentType

logger = logging.getLogger(__name__)

# Create blueprint
expert_bp = Blueprint('expert', __name__, url_prefix='/api/expert')

# Initialize systems
escalation_engine = get_escalation_engine()
expert_manager = get_expert_manager()
feedback_system = get_feedback_system()
faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()

# Expert Teams Endpoints

@expert_bp.route('/teams', methods=['GET'])
@handle_api_errors
def get_expert_teams():
    """Get all expert teams for current tenant"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    # Get tenant_id from user (simplified - in production, get from user's organization)
    tenant_id = str(user_id)
    
    teams = expert_manager.get_expert_teams(tenant_id)
    
    return create_success_response({
        'teams': teams
    }, 'Expert teams retrieved successfully')

@expert_bp.route('/teams', methods=['POST'])
@handle_api_errors
def create_expert_team():
    """Create a new expert team"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return create_error_response("Team name is required", 400, 'MISSING_FIELD')
    
    tenant_id = str(user_id)  # Simplified - use user_id as tenant_id
    
    result = expert_manager.create_expert_team(tenant_id, name, description)
    
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Failed to create team'),
            500,
            result.get('error_code', 'TEAM_CREATE_ERROR')
        )
    
    return create_success_response(result, 'Expert team created successfully')

@expert_bp.route('/teams/<int:team_id>/members', methods=['GET'])
@handle_api_errors
def get_team_members(team_id):
    """Get all members of an expert team"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    members = expert_manager.get_team_members(team_id)
    
    return create_success_response({
        'team_id': team_id,
        'members': members
    }, 'Team members retrieved successfully')

@expert_bp.route('/teams/<int:team_id>/members', methods=['POST'])
@handle_api_errors
def add_team_member(team_id):
    """Add a member to an expert team"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    data = request.get_json() or {}
    member_user_id = data.get('user_id')
    role = data.get('role', 'expert')
    
    if not member_user_id:
        return create_error_response("user_id is required", 400, 'MISSING_FIELD')
    
    result = expert_manager.add_team_member(team_id, member_user_id, role)
    
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Failed to add member'),
            500,
            result.get('error_code', 'MEMBER_ADD_ERROR')
        )
    
    return create_success_response(result, 'Team member added successfully')

# Escalated Questions Endpoints

@expert_bp.route('/questions', methods=['GET'])
@handle_api_errors
def get_escalated_questions():
    """Get escalated questions for current expert"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    status = request.args.get('status', 'pending')
    limit = min(max(request.args.get('limit', type=int, default=50), 1), 100)
    offset = max(request.args.get('offset', type=int, default=0), 0)
    
    from core.database_optimization import db_optimizer
    
    # Get questions assigned to this expert
    questions = db_optimizer.execute_query(
        """SELECT id, conversation_id, tenant_id, user_id, question, original_answer, 
           confidence, assigned_to, team_id, status, resolution, created_at, assigned_at, resolved_at
           FROM escalated_questions 
           WHERE assigned_to = ? AND status = ?
           ORDER BY created_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, status, limit, offset)
    )
    
    return create_success_response({
        'questions': questions,
        'count': len(questions),
        'status': status
    }, 'Escalated questions retrieved successfully')

@expert_bp.route('/questions/<int:question_id>/assign', methods=['POST'])
@handle_api_errors
def assign_question(question_id):
    """Assign an escalated question to current expert"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    from core.database_optimization import db_optimizer
    
    # Update assignment
    db_optimizer.execute_query(
        """UPDATE escalated_questions 
           SET assigned_to = ?, status = ?, assigned_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        (user_id, EscalationStatus.ASSIGNED.value, question_id),
        fetch=False
    )
    
    return create_success_response({
        'question_id': question_id,
        'assigned_to': user_id
    }, 'Question assigned successfully')

@expert_bp.route('/questions/<int:question_id>/respond', methods=['POST'])
@handle_api_errors
def respond_to_question(question_id):
    """Expert responds to an escalated question"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    data = request.get_json() or {}
    response_text = data.get('response', '').strip()
    add_to_kb = data.get('add_to_kb', False)
    
    if not response_text:
        return create_error_response("Response text is required", 400, 'MISSING_FIELD')
    
    from core.database_optimization import db_optimizer
    
    # Get escalated question
    escalated = escalation_engine.get_escalated_question(question_id)
    if not escalated:
        return create_error_response("Question not found", 404, 'QUESTION_NOT_FOUND')
    
    # Create expert response
    response_id = db_optimizer.execute_query(
        """INSERT INTO expert_responses 
           (escalated_question_id, expert_user_id, response_text, added_to_kb)
           VALUES (?, ?, ?, ?)""",
        (question_id, user_id, response_text, add_to_kb),
        fetch=False
    )
    
    # Update escalation status
    escalation_engine.update_status(
        question_id,
        EscalationStatus.RESOLVED,
        resolution=response_text
    )
    
    # Add to KB if requested
    tenant_id = str(user_id)
    faq_id = None
    kb_document_id = None
    if add_to_kb:
        # Add as FAQ
        faq_id = faq_system.add_faq(
            question=escalated.question,
            answer=response_text,
            category='general',
            keywords=[],
            variations=[],
            priority=1
        )
        
        # Update response with FAQ ID
        db_optimizer.execute_query(
            "UPDATE expert_responses SET faq_id = ? WHERE id = ?",
            (faq_id, response_id),
            fetch=False
        )
    
    return create_success_response({
        'response_id': response_id,
        'question_id': question_id,
        'faq_id': faq_id,
        'kb_document_id': kb_document_id
    }, 'Response submitted successfully')

@expert_bp.route('/questions/<int:question_id>/add-to-kb', methods=['POST'])
@handle_api_errors
def add_question_to_kb(question_id):
    """Add escalated question/answer pair to knowledge base"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    data = request.get_json() or {}
    answer = data.get('answer', '').strip()
    as_faq = data.get('as_faq', True)
    
    if not answer:
        return create_error_response("Answer is required", 400, 'MISSING_FIELD')
    
    escalated = escalation_engine.get_escalated_question(question_id)
    if not escalated:
        return create_error_response("Question not found", 404, 'QUESTION_NOT_FOUND')
    
    faq_id = None
    kb_document_id = None
    
    if as_faq:
        # Add as FAQ
        faq_id = faq_system.add_faq(
            question=escalated.question,
            answer=answer,
            category='general',
            keywords=[],
            variations=[],
            priority=1
        )
    else:
        # Add as KB document
        kb_document_id = knowledge_base.add_document(
            title=escalated.question,
            content=answer,
            summary=answer[:200],
            document_type=DocumentType.ARTICLE,
            tags=[],
            keywords=[],
            category='general',
            author='expert',
            metadata={'escalated_question_id': question_id, 'tenant_id': tenant_id}
        )
    
    # Update expert response
    from core.database_optimization import db_optimizer
    db_optimizer.execute_query(
        """UPDATE expert_responses 
           SET added_to_kb = 1, faq_id = ?, kb_document_id = ? 
           WHERE escalated_question_id = ? AND expert_user_id = ?""",
        (faq_id, kb_document_id, question_id, user_id),
        fetch=False
    )
    
    return create_success_response({
        'question_id': question_id,
        'faq_id': faq_id,
        'kb_document_id': kb_document_id
    }, 'Question added to knowledge base successfully')

@expert_bp.route('/stats', methods=['GET'])
@handle_api_errors
def get_expert_stats():
    """Get expert performance statistics"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    stats = expert_manager.get_expert_stats(user_id)
    
    return create_success_response(stats, 'Expert statistics retrieved successfully')

# Feedback Endpoints

@expert_bp.route('/feedback', methods=['POST'])
@handle_api_errors
def record_feedback():
    """Record feedback on a chatbot answer"""
    data = request.get_json() or {}
    conversation_id = data.get('conversation_id', '').strip()
    helpful = data.get('helpful', True)
    feedback_text = data.get('feedback_text', '').strip()
    message_id = data.get('message_id')
    user_id = data.get('user_id')
    
    if not conversation_id:
        return create_error_response("conversation_id is required", 400, 'MISSING_FIELD')
    
    result = feedback_system.record_feedback(
        conversation_id=conversation_id,
        helpful=helpful,
        feedback_text=feedback_text,
        message_id=message_id,
        user_id=user_id
    )
    
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Failed to record feedback'),
            500,
            result.get('error_code', 'FEEDBACK_ERROR')
        )
    
    return create_success_response(result, 'Feedback recorded successfully')

@expert_bp.route('/feedback/<conversation_id>', methods=['GET'])
@handle_api_errors
def get_conversation_feedback(conversation_id):
    """Get feedback for a conversation"""
    feedbacks = feedback_system.get_conversation_feedback(conversation_id)
    stats = feedback_system.get_feedback_stats(conversation_id)
    
    return create_success_response({
        'feedbacks': feedbacks,
        'stats': stats
    }, 'Feedback retrieved successfully')
