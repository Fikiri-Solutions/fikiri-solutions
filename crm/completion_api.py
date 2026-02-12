"""
CRM Completion API Endpoints for Fikiri Solutions
Handles automated follow-ups, reminders, alerts, and pipeline management
"""

import json
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from email_automation.followup_system import get_follow_up_system
from core.reminders_alerts_system import get_reminders_alerts_system
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Create blueprint
crm_bp = Blueprint('crm', __name__, url_prefix='/api/crm')

@crm_bp.route('/follow-ups/create', methods=['POST'])
def create_follow_up():
    """Create a follow-up task for a lead"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        required_fields = ['lead_id', 'user_id', 'stage']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        follow_up_system = get_follow_up_system()
        if not follow_up_system:
            return jsonify({"success": False, "error": "Follow-up system not available"}), 500
        
        result = follow_up_system.create_follow_up_task(
            lead_id=data['lead_id'],
            user_id=data['user_id'],
            stage=data['stage']
        )
        
        if result['success']:
            logger.info(f"✅ Follow-up created: {result.get('task_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to create follow-up: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Create follow-up error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/follow-ups/process', methods=['POST'])
def process_follow_ups():
    """Process all pending follow-up tasks"""
    try:
        follow_up_system = get_follow_up_system()
        if not follow_up_system:
            return jsonify({"success": False, "error": "Follow-up system not available"}), 500
        
        result = follow_up_system.process_pending_follow_ups()
        
        if result['success']:
            logger.info(f"✅ Processed {result.get('processed')} follow-ups")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to process follow-ups: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Process follow-ups error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/follow-ups/stats/<int:user_id>', methods=['GET'])
def get_follow_up_stats(user_id):
    """Get follow-up statistics for a user"""
    try:
        follow_up_system = get_follow_up_system()
        if not follow_up_system:
            return jsonify({"success": False, "error": "Follow-up system not available"}), 500
        
        result = follow_up_system.get_follow_up_stats(user_id)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"❌ Get follow-up stats error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/reminders/create', methods=['POST'])
def create_reminder():
    """Create a new reminder"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        required_fields = ['user_id', 'reminder_type', 'title', 'description', 'due_date']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Reminders system not available"}), 500
        
        # Parse due_date
        try:
            due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"success": False, "error": "Invalid due_date format"}), 400
        
        result = reminders_system.create_reminder(
            user_id=data['user_id'],
            reminder_type=data['reminder_type'],
            title=data['title'],
            description=data['description'],
            due_date=due_date,
            priority=data.get('priority', 'medium'),
            lead_id=data.get('lead_id')
        )
        
        if result['success']:
            logger.info(f"✅ Reminder created: {result.get('reminder_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to create reminder: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Create reminder error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/reminders/<int:user_id>', methods=['GET'])
def get_user_reminders(user_id):
    """Get user's reminders"""
    try:
        upcoming_days = request.args.get('upcoming_days', 7, type=int)
        
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Reminders system not available"}), 500
        
        result = reminders_system.get_user_reminders(user_id, upcoming_days)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"❌ Get reminders error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/reminders/<reminder_id>/cancel', methods=['POST'])
def cancel_reminder(reminder_id):
    """Cancel a reminder"""
    try:
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Reminders system not available"}), 500
        
        result = reminders_system.cancel_reminder(reminder_id)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"❌ Cancel reminder error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/alerts/create', methods=['POST'])
def create_alert():
    """Create a new alert"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        required_fields = ['user_id', 'alert_type', 'title', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Alerts system not available"}), 500
        
        result = reminders_system.create_alert(
            user_id=data['user_id'],
            alert_type=data['alert_type'],
            title=data['title'],
            message=data['message'],
            priority=data.get('priority', 'medium')
        )
        
        if result['success']:
            logger.info(f"✅ Alert created: {result.get('alert_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to create alert: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Create alert error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/alerts/<int:user_id>', methods=['GET'])
def get_user_alerts(user_id):
    """Get user's alerts"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Alerts system not available"}), 500
        
        result = reminders_system.get_user_alerts(user_id, limit)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"❌ Get alerts error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/alerts/<alert_id>/read', methods=['POST'])
def mark_alert_read(alert_id):
    """Mark an alert as read"""
    try:
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Alerts system not available"}), 500
        
        result = reminders_system.mark_alert_read(alert_id)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"❌ Mark alert read error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/pipeline/stages', methods=['GET'])
def get_pipeline_stages():
    """Get all pipeline stages"""
    try:
        # Rulepack compliance: specific columns, not SELECT *
        query = """
            SELECT id, name, description, order_index, is_active, created_at 
            FROM lead_pipeline_stages 
            WHERE is_active = 1 
            ORDER BY order_index ASC
        """
        
        stages = db_optimizer.execute_query(query)
        
        formatted_stages = []
        for stage in stages:
            formatted_stages.append({
                'id': stage['id'],
                'name': stage['name'],
                'description': stage['description'],
                'order_index': stage['order_index'],
                'is_active': stage['is_active']
            })
        
        return jsonify({"success": True, "stages": formatted_stages}), 200
        
    except Exception as e:
        logger.error(f"❌ Get pipeline stages error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/pipeline/stages', methods=['POST'])
def create_pipeline_stage():
    """Create a new pipeline stage"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        required_fields = ['name', 'description', 'order_index']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        query = """
            INSERT INTO lead_pipeline_stages (name, description, order_index, is_active)
            VALUES (?, ?, ?, ?)
        """
        
        values = (
            data['name'],
            data['description'],
            data['order_index'],
            data.get('is_active', True)
        )
        
        db_optimizer.execute_query(query, values, fetch=False)
        
        logger.info(f"✅ Pipeline stage created: {data['name']}")
        return jsonify({"success": True, "message": "Pipeline stage created"}), 200
        
    except Exception as e:
        logger.error(f"❌ Create pipeline stage error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/pipeline/leads/<int:user_id>', methods=['GET'])
def get_pipeline_leads(user_id):
    """Get leads organized by pipeline stage"""
    try:
        query = """
            SELECT l.*, 
                   COUNT(la.id) as activity_count,
                   MAX(la.timestamp) as last_activity
            FROM leads l
            LEFT JOIN lead_activities la ON l.id = la.lead_id
            WHERE l.user_id = ?
            GROUP BY l.id
            ORDER BY l.created_at DESC
        """
        
        leads = db_optimizer.execute_query(query, (user_id,))
        
        # Group leads by stage
        pipeline_data = {}
        for lead in leads:
            stage = lead['stage'] or 'new'
            if stage not in pipeline_data:
                pipeline_data[stage] = []
            
            pipeline_data[stage].append({
                'id': lead['id'],
                'name': lead['name'],
                'email': lead['email'],
                'company': lead['company'],
                'stage': lead['stage'],
                'score': lead['score'],
                'created_at': lead['created_at'],
                'last_contact': lead['last_contact'],
                'activity_count': lead['activity_count'],
                'last_activity': lead['last_activity']
            })
        
        return jsonify({"success": True, "pipeline": pipeline_data}), 200
        
    except Exception as e:
        logger.error(f"❌ Get pipeline leads error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/pipeline/leads/<lead_id>/stage', methods=['PUT'])
def update_lead_stage(lead_id):
    """Update a lead's pipeline stage"""
    try:
        data = request.get_json()
        if not data or 'stage' not in data:
            return jsonify({"success": False, "error": "Stage not provided"}), 400
        
        query = "UPDATE leads SET stage = ?, updated_at = ? WHERE id = ?"
        values = (data['stage'], datetime.now().isoformat(), lead_id)
        
        db_optimizer.execute_query(query, values, fetch=False)
        
        # Log the stage change activity
        activity_query = """
            INSERT INTO lead_activities (lead_id, activity_type, description, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
        """
        
        activity_values = (
            lead_id,
            'stage_changed',
            f"Lead moved to {data['stage']} stage",
            datetime.now().isoformat(),
            json.dumps({'old_stage': 'unknown', 'new_stage': data['stage']})
        )
        
        db_optimizer.execute_query(activity_query, activity_values, fetch=False)
        
        logger.info(f"✅ Lead {lead_id} moved to {data['stage']} stage")
        return jsonify({"success": True, "message": "Lead stage updated"}), 200
        
    except Exception as e:
        logger.error(f"❌ Update lead stage error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@crm_bp.route('/process/expired-reminders', methods=['POST'])
def process_expired_reminders():
    """Process expired reminders and create alerts"""
    try:
        reminders_system = get_reminders_alerts_system()
        if not reminders_system:
            return jsonify({"success": False, "error": "Reminders system not available"}), 500
        
        result = reminders_system.process_expired_reminders()
        
        if result['success']:
            logger.info(f"✅ Processed {result.get('processed')} expired reminders")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to process expired reminders: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Process expired reminders error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
