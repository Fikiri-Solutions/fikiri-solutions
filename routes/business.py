#!/usr/bin/env python3
"""
Business and CRM Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging
from datetime import datetime

# Import business logic modules
from core.enhanced_crm_service import enhanced_crm_service
from core.database_optimization import db_optimizer
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.automation_engine import automation_engine
from core.automation_safety import automation_safety_manager
from core.oauth_token_manager import oauth_token_manager
from core.secure_sessions import get_current_user_id
from core.user_auth import user_auth_manager

logger = logging.getLogger(__name__)

# Create business blueprint
business_bp = Blueprint("business", __name__, url_prefix="/api")

# CRM Routes
@business_bp.route('/crm/leads', methods=['GET'])
@handle_api_errors
def get_leads():
    """Get all leads for authenticated user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        leads = enhanced_crm_service.get_leads(user_id)
        return create_success_response({'leads': leads}, 'Leads retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get leads error: {e}")
        return create_error_response("Failed to retrieve leads", 500, 'CRM_ERROR')

@business_bp.route('/crm/leads', methods=['POST'])
@handle_api_errors
def create_lead():
    """Create a new lead"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Validate required fields
        required_fields = ['email', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')

        lead_data = {
            'name': data['name'],
            'email': data['email'],
            'company': data.get('company', ''),
            'phone': data.get('phone', ''),
            'source': data.get('source', 'website'),
            'status': data.get('status', 'new'),
            'notes': data.get('notes', '')
        }

        lead = enhanced_crm_service.create_lead(user_id, lead_data)
        
        if lead:
            return create_success_response({'lead': lead}, 'Lead created successfully')
        else:
            return create_error_response("Failed to create lead", 500, 'CRM_CREATE_ERROR')
            
    except Exception as e:
        logger.error(f"Create lead error: {e}")
        return create_error_response("Failed to create lead", 500, 'CRM_ERROR')

@business_bp.route('/crm/leads/<int:lead_id>', methods=['PUT'])
@handle_api_errors
def update_lead(lead_id):
    """Update an existing lead"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Check if lead belongs to user
        lead = enhanced_crm_service.get_lead(lead_id)
        if not lead or lead['user_id'] != user_id:
            return create_error_response("Lead not found", 404, 'LEAD_NOT_FOUND')

        updated_lead = enhanced_crm_service.update_lead(lead_id, data)
        
        if updated_lead:
            return create_success_response({'lead': updated_lead}, 'Lead updated successfully')
        else:
            return create_error_response("Failed to update lead", 500, 'CRM_UPDATE_ERROR')
            
    except Exception as e:
        logger.error(f"Update lead error: {e}")
        return create_error_response("Failed to update lead", 500, 'CRM_ERROR')

@business_bp.route('/crm/leads/<int:lead_id>/activities', methods=['POST'])
@handle_api_errors
def add_lead_activity(lead_id):
    """Add an activity to a lead"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        activity_data = {
            'type': data.get('type', 'note'),
            'description': data.get('description', ''),
            'due_date': data.get('due_date'),
            'completed': data.get('completed', False)
        }

        activity = enhanced_crm_service.add_lead_activity(lead_id, activity_data)
        
        if activity:
            return create_success_response({'activity': activity}, 'Activity added successfully')
        else:
            return create_error_response("Failed to add activity", 500, 'CRM_ACTIVITY_ERROR')
            
    except Exception as e:
        logger.error(f"Add lead activity error: {e}")
        return create_error_response("Failed to add activity", 500, 'CRM_ERROR')

@business_bp.route('/crm/leads/<int:lead_id>/activities', methods=['GET'])
@handle_api_errors
def get_lead_activities(lead_id):
    """Get all activities for a lead"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Check if lead belongs to user
        lead = enhanced_crm_service.get_lead(lead_id)
        if not lead or lead['user_id'] != user_id:
            return create_error_response("Lead not found", 404, 'LEAD_NOT_FOUND')

        activities = enhanced_crm_service.get_lead_activities(lead_id)
        
        return create_success_response({'activities': activities}, 'Activities retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get lead activities error: {e}")
        return create_error_response("Failed to retrieve activities", 500, 'CRM_ERROR')

@business_bp.route('/crm/pipeline', methods=['GET'])
@handle_api_errors
def get_pipeline():
    """Get CRM pipeline data"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        pipeline = enhanced_crm_service.get_pipeline(user_id)
        
        return create_success_response({'pipeline': pipeline}, 'Pipeline retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get pipeline error: {e}")
        return create_error_response("Failed to retrieve pipeline", 500, 'CRM_ERROR')

@business_bp.route('/crm/sync-gmail', methods=['POST'])
@handle_api_errors
def sync_gmail():
    """Sync Gmail contacts to CRM"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Check OAuth connection
        result = oauth_token_manager.get_token_status(user_id, "gmail")
        if not result['success']:
            return create_error_response("Gmail connection required", 403, 'OAUTH_REQUIRED')

        # Trigger Gmail sync
        sync_result = enhanced_crm_sync.sync_gmail_contacts(user_id)
        
        if sync_result['success']:
            return create_success_response(
                {'contacts_synced': sync_result['count']}, 
                'Gmail contacts synced successfully'
            )
        else:
            return create_error_response(sync_result['error'], 500, 'GMAIL_SYNC_ERROR')
            
    except Exception as e:
        logger.error(f"Gmail sync error: {e}")
        return create_error_response("Failed to sync Gmail contacts", 500, 'GMAIL_SYNC_ERROR')

# Automation Routes
@business_bp.route('/automation/rules', methods=['GET'])
@handle_api_errors
def get_automation_rules():
    """Get automation rules for authenticated user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        rules = automation_engine.get_user_rules(user_id)
        
        return create_success_response({'rules': rules}, 'Automation rules retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get automation rules error: {e}")
        return create_error_response("Failed to retrieve automation rules", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/rules', methods=['POST'])
@handle_api_errors
def create_automation_rule():
    """Create a new automation rule"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Validate required fields
        if 'trigger_type' not in data or 'action_type' not in data:
            return create_error_response("Trigger and action types are required", 400, 'MISSING_FIELDS')

        rule_data = {
            'name': data.get('name', 'Unnamed Rule'),
            'trigger_type': data['trigger_type'],
            'action_type': data['action_type'],
            'conditions': data.get('conditions', {}),
            'is_active': data.get('is_active', True)
        }

        rule = automation_engine.create_rule(user_id, rule_data)
        
        if rule:
            return create_success_response({'rule': rule}, 'Automation rule created successfully')
        else:
            return create_error_response("Failed to create automation rule", 500, 'AUTOMATION_CREATE_ERROR')
            
    except Exception as e:
        logger.error(f"Create automation rule error: {e}")
        return create_error_response("Failed to create automation rule", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/rules/<int:rule_id>', methods=['PUT'])
@handle_api_errors
def update_automation_rule(rule_id):
    """Update an existing automation rule"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Check if rule belongs to user
        rule = automation_engine.get_rule(rule_id)
        if not rule or rule['user_id'] != user_id:
            return create_error_response("Automation rule not found", 404, 'RULE_NOT_FOUND')

        updated_rule = automation_engine.update_rule(rule_id, data)
        
        if updated_rule:
            return create_success_response({'rule': updated_rule}, 'Automation rule updated successfully')
        else:
            return create_error_response("Failed to update automation rule", 500, 'AUTOMATION_UPDATE_ERROR')
            
    except Exception as e:
        logger.error(f"Update automation rule error: {e}")
        return create_error_response("Failed to update automation rule", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/suggestions', methods=['GET'])
@handle_api_errors
def get_automation_suggestions():
    """Get AI-powered automation suggestions"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        suggestions = automation_engine.get_suggestions(user_id)
        
        return create_success_response({'suggestions': suggestions}, 'Automation suggestions retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get automation suggestions error: {e}")
        return create_error_response("Failed to retrieve automation suggestions", 500, 'AUTOMATION_SUGGESTIONS_ERROR')

@business_bp.route('/automation/execute', methods=['POST'])
@handle_api_errors
def execute_automation():
    """Execute automation rules"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        if 'rule_ids' not in data:
            return create_error_response("Rule IDs are required", 400, 'MISSING_RULE_IDS')

        execution_result = automation_engine.execute_rules(user_id, data['rule_ids'])
        
        return create_success_response(
            {'execution_results': execution_result}, 
            'Automation rules executed successfully'
        )
        
    except Exception as e:
        logger.error(f"Execute automation error: {e}")
        return create_error_response("Failed to execute automation rules", 500, 'AUTOMATION_EXECUTION_ERROR')

@business_bp.route('/automation/kill-switch', methods=['POST'])
@handle_api_errors
def automation_kill_switch():
    """Emergency automation kill switch"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        safety_manager.disable_all_automations(user_id)
        
        return create_success_response(
            {'message': 'All automations have been disabled'}, 
            'Automation kill switch activated'
        )
        
    except Exception as e:
        logger.error(f"Automation kill switch error: {e}")
        return create_error_response("Failed to activate kill switch", 500, 'KILL_SWITCH_ERROR')

@business_bp.route('/automation/safety-status', methods=['GET'])
@handle_api_errors
def get_automation_safety_status():
    """Get automation safety status"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        safety_status = automation_safety_manager.get_safety_status(user_id)
        
        return create_success_response({'safety_status': safety_status}, 'Safety status retrieved successfully')
        
    except Exception as e:
        logger.error(f"Get safety status error: {e}")
        return create_error_response("Failed to retrieve safety status", 500, 'SAFETY_STATUS_ERROR')
