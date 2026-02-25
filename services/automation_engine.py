"""
Automation Engine with Rule-based Workflows
Handles automated email responses, lead management, and workflow automation
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from core.database_optimization import db_optimizer
from crm.service import enhanced_crm_service
from email_automation.parser import MinimalEmailParser

logger = logging.getLogger(__name__)

class TriggerType(Enum):
    """Automation trigger types"""
    EMAIL_RECEIVED = "email_received"
    EMAIL_SENT = "email_sent"
    LEAD_CREATED = "lead_created"
    LEAD_STAGE_CHANGED = "lead_stage_changed"
    TIME_BASED = "time_based"
    KEYWORD_DETECTED = "keyword_detected"

class ActionType(Enum):
    """Automation action types"""
    SEND_EMAIL = "send_email"
    UPDATE_LEAD_STAGE = "update_lead_stage"
    ADD_LEAD_ACTIVITY = "add_lead_activity"
    APPLY_LABEL = "apply_label"
    ARCHIVE_EMAIL = "archive_email"
    CREATE_TASK = "create_task"
    SEND_NOTIFICATION = "send_notification"
    # Advanced workflow actions
    SCHEDULE_FOLLOW_UP = "schedule_follow_up"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    UPDATE_CRM_FIELD = "update_crm_field"
    TRIGGER_WEBHOOK = "trigger_webhook"
    GENERATE_DOCUMENT = "generate_document"
    SEND_SMS = "send_sms"
    CREATE_INVOICE = "create_invoice"
    ASSIGN_TEAM_MEMBER = "assign_team_member"

class AutomationStatus(Enum):
    """Automation status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class AutomationRule:
    """Automation rule data structure"""
    id: int
    user_id: int
    name: str
    description: str
    trigger_type: TriggerType
    trigger_conditions: Dict[str, Any]
    action_type: ActionType
    action_parameters: Dict[str, Any]
    status: AutomationStatus
    created_at: datetime
    updated_at: datetime
    last_executed: Optional[datetime]
    execution_count: int
    success_count: int
    error_count: int

@dataclass
class AutomationExecution:
    """Automation execution data structure"""
    id: int
    rule_id: int
    user_id: int
    trigger_data: Dict[str, Any]
    action_result: Dict[str, Any]
    status: str
    executed_at: datetime
    error_message: Optional[str]

class AutomationEngine:
    """Automation engine for rule-based workflows"""
    
    def __init__(self):
        self.trigger_handlers = {
            TriggerType.EMAIL_RECEIVED: self._handle_email_received_trigger,
            TriggerType.EMAIL_SENT: self._handle_email_sent_trigger,
            TriggerType.LEAD_CREATED: self._handle_lead_created_trigger,
            TriggerType.LEAD_STAGE_CHANGED: self._handle_lead_stage_changed_trigger,
            TriggerType.TIME_BASED: self._handle_time_based_trigger,
            TriggerType.KEYWORD_DETECTED: self._handle_keyword_detected_trigger
        }
        
        self.action_handlers = {
            ActionType.SEND_EMAIL: self._execute_send_email,
            ActionType.UPDATE_LEAD_STAGE: self._execute_update_lead_stage,
            ActionType.ADD_LEAD_ACTIVITY: self._execute_add_lead_activity,
            ActionType.APPLY_LABEL: self._execute_apply_label,
            ActionType.ARCHIVE_EMAIL: self._execute_archive_email,
            ActionType.CREATE_TASK: self._execute_create_task,
            ActionType.SEND_NOTIFICATION: self._execute_send_notification,
            # Advanced workflow action handlers
            ActionType.SCHEDULE_FOLLOW_UP: self._execute_schedule_follow_up,
            ActionType.CREATE_CALENDAR_EVENT: self._execute_create_calendar_event,
            ActionType.UPDATE_CRM_FIELD: self._execute_update_crm_field,
            ActionType.TRIGGER_WEBHOOK: self._execute_trigger_webhook,
            ActionType.GENERATE_DOCUMENT: self._execute_generate_document,
            ActionType.SEND_SMS: self._execute_send_sms,
            ActionType.CREATE_INVOICE: self._execute_create_invoice,
            ActionType.ASSIGN_TEAM_MEMBER: self._execute_assign_team_member
        }
    
    def create_automation_rule(self, user_id: int, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new automation rule"""
        try:
            # Validate rule data
            validation_result = self._validate_rule_data(rule_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'error_code': 'INVALID_RULE_DATA'
                }
            
            # Create rule
            rule_id = db_optimizer.execute_query(
                """INSERT INTO automation_rules 
                   (user_id, name, description, trigger_type, trigger_conditions, 
                    action_type, action_parameters, status, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, rule_data['name'], rule_data['description'],
                 rule_data['trigger_type'], json.dumps(rule_data['trigger_conditions']),
                 rule_data['action_type'], json.dumps(rule_data['action_parameters']),
                 AutomationStatus.ACTIVE.value, datetime.now().isoformat(), datetime.now().isoformat()),
                fetch=False
            )
            
            logger.info(f"Automation rule created: {rule_data['name']} for user {user_id}")
            
            return {
                'success': True,
                'data': {
                    'rule_id': rule_id,
                    'message': 'Automation rule created successfully'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating automation rule: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_automation_rules(self, user_id: int, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get automation rules for user with pagination"""
        try:
            # Rulepack compliance: specific columns, not SELECT *
            query = """SELECT id, user_id, name, description, trigger_type, trigger_conditions, 
                      action_type, action_parameters, status, created_at, updated_at, 
                      last_executed, execution_count, success_count, error_count 
                      FROM automation_rules WHERE user_id = ?"""
            params = [user_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            # Add pagination (rulepack compliance: all list endpoints must be paginated)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rules_data = db_optimizer.execute_query(query, tuple(params))
            
            # Get total count for pagination metadata
            count_query = "SELECT COUNT(*) as total FROM automation_rules WHERE user_id = ?"
            count_params = [user_id]
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
            total_count_result = db_optimizer.execute_query(count_query, tuple(count_params))
            total_count = total_count_result[0]['total'] if total_count_result else 0
            
            rules = []
            for rule_data in rules_data:
                rules.append(self._format_rule(rule_data))
            
            return {
                'success': True,
                'data': {
                    'rules': rules,
                    'count': len(rules),
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + len(rules)) < total_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting automation rules: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def update_automation_rule(self, rule_id: int, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update automation rule"""
        try:
            # Verify rule ownership (rulepack compliance: specific columns)
            rule_data = db_optimizer.execute_query(
                "SELECT id, user_id, name, description, trigger_type, trigger_conditions, action_type, action_parameters, status, created_at, updated_at, last_executed, execution_count, success_count, error_count FROM automation_rules WHERE id = ? AND user_id = ?",
                (rule_id, user_id)
            )
            
            if not rule_data:
                return {
                    'success': False,
                    'error': 'Automation rule not found',
                    'error_code': 'RULE_NOT_FOUND'
                }
            
            # Build update query
            update_fields = []
            update_values = []
            
            allowed_fields = ['name', 'description', 'trigger_conditions', 'action_parameters', 'status']
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field in ['trigger_conditions', 'action_parameters']:
                        update_fields.append(f"{field} = ?")
                        update_values.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update',
                    'error_code': 'NO_UPDATES'
                }
            
            update_values.extend([rule_id, user_id])
            
            query = f"UPDATE automation_rules SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?"
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Get updated rule (rulepack compliance: specific columns)
            updated_rule = db_optimizer.execute_query(
                "SELECT id, user_id, name, description, trigger_type, trigger_conditions, action_type, action_parameters, status, created_at, updated_at, last_executed, execution_count, success_count, error_count FROM automation_rules WHERE id = ? AND user_id = ?",
                (rule_id, user_id)
            )[0]
            
            return {
                'success': True,
                'data': {
                    'rule': self._format_rule(updated_rule),
                    'message': 'Automation rule updated successfully'
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating automation rule: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def execute_automation_rules(self, trigger_type: TriggerType, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute automation rules based on trigger"""
        try:
            # Get active rules for trigger type (rulepack compliance: specific columns)
            rules_data = db_optimizer.execute_query(
                """SELECT id, user_id, name, description, trigger_type, trigger_conditions, 
                   action_type, action_parameters, status, created_at, updated_at, 
                   last_executed, execution_count, success_count, error_count 
                   FROM automation_rules 
                   WHERE user_id = ? AND trigger_type = ? AND status = ?""",
                (user_id, trigger_type.value, AutomationStatus.ACTIVE.value)
            )
            
            executed_rules = []
            failed_rules = []
            
            for rule_data in rules_data:
                rule = self._format_rule(rule_data)
                
                # Check if trigger conditions are met
                if self._check_trigger_conditions(rule, trigger_data):
                    # Execute rule
                    execution_result = self._execute_rule(rule, trigger_data)
                    
                    if execution_result['success']:
                        executed_rules.append({
                            'rule_id': rule.id,
                            'rule_name': rule.name,
                            'result': execution_result['data']
                        })
                    else:
                        failed_rules.append({
                            'rule_id': rule.id,
                            'rule_name': rule.name,
                            'error': execution_result['error']
                        })
            
            return {
                'success': True,
                'data': {
                    'executed_rules': executed_rules,
                    'failed_rules': failed_rules,
                    'total_executed': len(executed_rules),
                    'total_failed': len(failed_rules)
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing automation rules: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_automation_suggestions(self, user_id: int) -> Dict[str, Any]:
        """Get automation suggestions based on user's email patterns"""
        try:
            # Analyze user's email patterns
            email_patterns = self._analyze_email_patterns(user_id)
            
            # Generate suggestions based on patterns
            suggestions = []
            
            # Quote request automation
            if email_patterns.get('quote_requests', 0) > 0:
                suggestions.append({
                    'name': 'Auto-reply to Quote Requests',
                    'description': 'Automatically send a quote request acknowledgment',
                    'trigger': {
                        'type': TriggerType.KEYWORD_DETECTED.value,
                        'conditions': {
                            'keywords': ['quote', 'pricing', 'cost', 'estimate'],
                            'subject_contains': True
                        }
                    },
                    'action': {
                        'type': ActionType.SEND_EMAIL.value,
                        'parameters': {
                            'template': 'quote_request_acknowledgment',
                            'delay_minutes': 0
                        }
                    },
                    'priority': 'high'
                })
            
            # New lead automation
            if email_patterns.get('new_leads', 0) > 0:
                suggestions.append({
                    'name': 'Welcome New Leads',
                    'description': 'Send welcome email to new leads',
                    'trigger': {
                        'type': TriggerType.LEAD_CREATED.value,
                        'conditions': {
                            'source': 'gmail'
                        }
                    },
                    'action': {
                        'type': ActionType.SEND_EMAIL.value,
                        'parameters': {
                            'template': 'welcome_new_lead',
                            'delay_minutes': 5
                        }
                    },
                    'priority': 'medium'
                })
            
            # Follow-up automation
            if email_patterns.get('follow_ups_needed', 0) > 0:
                suggestions.append({
                    'name': 'Follow-up Reminder',
                    'description': 'Send follow-up reminders for leads',
                    'trigger': {
                        'type': TriggerType.TIME_BASED.value,
                        'conditions': {
                            'schedule': 'daily',
                            'time': '09:00'
                        }
                    },
                    'action': {
                        'type': ActionType.CREATE_TASK.value,
                        'parameters': {
                            'task_type': 'follow_up',
                            'priority': 'medium'
                        }
                    },
                    'priority': 'low'
                })
            
            return {
                'success': True,
                'data': {
                    'suggestions': suggestions,
                    'email_patterns': email_patterns
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting automation suggestions: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _validate_rule_data(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate automation rule data"""
        required_fields = ['name', 'trigger_type', 'action_type']
        
        for field in required_fields:
            if not rule_data.get(field):
                return {
                    'valid': False,
                    'error': f'Missing required field: {field}'
                }
        
        # Validate trigger type
        try:
            TriggerType(rule_data['trigger_type'])
        except ValueError:
            return {
                'valid': False,
                'error': 'Invalid trigger type'
            }
        
        # Validate action type
        try:
            ActionType(rule_data['action_type'])
        except ValueError:
            return {
                'valid': False,
                'error': 'Invalid action type'
            }
        
        return {'valid': True}
    
    def _format_rule(self, rule_data: Dict[str, Any]) -> AutomationRule:
        """Format rule data into AutomationRule object"""
        return AutomationRule(
            id=rule_data['id'],
            user_id=rule_data['user_id'],
            name=rule_data['name'],
            description=rule_data['description'],
            trigger_type=TriggerType(rule_data['trigger_type']),
            trigger_conditions=json.loads(rule_data['trigger_conditions']),
            action_type=ActionType(rule_data['action_type']),
            action_parameters=json.loads(rule_data['action_parameters']),
            status=AutomationStatus(rule_data['status']),
            created_at=datetime.fromisoformat(rule_data['created_at']),
            updated_at=datetime.fromisoformat(rule_data['updated_at']),
            last_executed=datetime.fromisoformat(rule_data['last_executed']) if rule_data.get('last_executed') else None,
            execution_count=rule_data['execution_count'],
            success_count=rule_data['success_count'],
            error_count=rule_data['error_count']
        )
    
    def _check_trigger_conditions(self, rule: AutomationRule, trigger_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        conditions = rule.trigger_conditions
        
        if rule.trigger_type == TriggerType.KEYWORD_DETECTED:
            keywords = conditions.get('keywords', [])
            text = trigger_data.get('text', '').lower()
            return any(keyword.lower() in text for keyword in keywords)
        
        elif rule.trigger_type == TriggerType.EMAIL_RECEIVED:
            sender_email = trigger_data.get('sender_email', '')
            if conditions.get('sender_domain'):
                return sender_email.endswith(conditions['sender_domain'])
            return True
        
        elif rule.trigger_type == TriggerType.LEAD_CREATED:
            source = trigger_data.get('source', '')
            if conditions.get('source'):
                return source == conditions['source']
            return True
        
        return True  # Default to true for other trigger types
    
    def _execute_rule(self, rule: AutomationRule, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automation rule"""
        try:
            # Get action handler
            action_handler = self.action_handlers.get(rule.action_type)
            if not action_handler:
                return {
                    'success': False,
                    'error': f'No handler for action type: {rule.action_type}'
                }
            
            # Execute action
            result = action_handler(rule.action_parameters, trigger_data, rule.user_id)
            
            # Update rule execution stats
            self._update_rule_stats(rule.id, result['success'])
            
            # Log execution
            self._log_execution(rule.id, rule.user_id, trigger_data, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing rule {rule.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_send_email(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute send email action"""
        try:
            # This would integrate with Gmail API to send emails
            # For now, we'll simulate the action
            
            template = parameters.get('template', 'default')
            delay_minutes = parameters.get('delay_minutes', 0)
            
            # Simulate email sending
            logger.info(f"Sending email using template: {template}")
            
            return {
                'success': True,
                'data': {
                    'action': 'email_sent',
                    'template': template,
                    'delay_minutes': delay_minutes,
                    'recipient': trigger_data.get('sender_email', 'unknown')
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_update_lead_stage(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute update lead stage action"""
        try:
            new_stage = parameters.get('stage')
            lead_id = trigger_data.get('lead_id')
            
            if not lead_id or not new_stage:
                return {
                    'success': False,
                    'error': 'Missing lead_id or stage parameter'
                }
            
            # Update lead stage using CRM service
            result = enhanced_crm_service.update_lead(lead_id, user_id, {'stage': new_stage})
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_add_lead_activity(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute add lead activity action"""
        try:
            activity_type = parameters.get('activity_type', 'note_added')
            description = parameters.get('description', 'Automated activity')
            lead_id = trigger_data.get('lead_id')
            
            if not lead_id:
                return {
                    'success': False,
                    'error': 'Missing lead_id parameter'
                }
            
            # Add activity using CRM service
            result = enhanced_crm_service.add_lead_activity(lead_id, user_id, activity_type, description)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_apply_label(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute apply label action"""
        try:
            label = parameters.get('label')
            email_id = trigger_data.get('email_id')
            
            if not label or not email_id:
                return {
                    'success': False,
                    'error': 'Missing label or email_id parameter'
                }
            
            # This would integrate with Gmail API to apply labels
            logger.info(f"Applying label {label} to email {email_id}")
            
            return {
                'success': True,
                'data': {
                    'action': 'label_applied',
                    'label': label,
                    'email_id': email_id
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_archive_email(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute archive email action"""
        try:
            email_id = trigger_data.get('email_id')
            
            if not email_id:
                return {
                    'success': False,
                    'error': 'Missing email_id parameter'
                }
            
            # This would integrate with Gmail API to archive emails
            logger.info(f"Archiving email {email_id}")
            
            return {
                'success': True,
                'data': {
                    'action': 'email_archived',
                    'email_id': email_id
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_create_task(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute create task action"""
        try:
            task_type = parameters.get('task_type', 'general')
            priority = parameters.get('priority', 'medium')
            description = parameters.get('description', 'Automated task')
            
            # This would integrate with a task management system
            logger.info(f"Creating {priority} priority {task_type} task: {description}")
            
            return {
                'success': True,
                'data': {
                    'action': 'task_created',
                    'task_type': task_type,
                    'priority': priority,
                    'description': description
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_send_notification(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute send notification action"""
        try:
            message = parameters.get('message', 'Automation executed')
            notification_type = parameters.get('type', 'info')
            
            # This would integrate with notification system
            logger.info(f"Sending {notification_type} notification: {message}")
            
            return {
                'success': True,
                'data': {
                    'action': 'notification_sent',
                    'message': message,
                    'type': notification_type
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_rule_stats(self, rule_id: int, success: bool):
        """Update rule execution statistics"""
        try:
            if success:
                db_optimizer.execute_query(
                    "UPDATE automation_rules SET execution_count = execution_count + 1, success_count = success_count + 1, last_executed = CURRENT_TIMESTAMP WHERE id = ?",
                    (rule_id,),
                    fetch=False
                )
            else:
                db_optimizer.execute_query(
                    "UPDATE automation_rules SET execution_count = execution_count + 1, error_count = error_count + 1, last_executed = CURRENT_TIMESTAMP WHERE id = ?",
                    (rule_id,),
                    fetch=False
                )
        except Exception as e:
            logger.error(f"Error updating rule stats: {e}")
    
    def _log_execution(self, rule_id: int, user_id: int, trigger_data: Dict[str, Any], result: Dict[str, Any]):
        """Log automation execution"""
        try:
            db_optimizer.execute_query(
                """INSERT INTO automation_executions 
                   (rule_id, user_id, trigger_data, action_result, status, executed_at, error_message) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (rule_id, user_id, json.dumps(trigger_data), json.dumps(result),
                 'success' if result['success'] else 'error', datetime.now().isoformat(),
                 result.get('error')),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Error logging execution: {e}")

    def get_execution_logs(self, user_id: int, rule_id: Optional[int] = None,
                           slug: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Get execution logs for a user's automations"""
        try:
            query = """
                SELECT ae.*, ar.name as rule_name, ar.action_parameters
                FROM automation_executions ae
                JOIN automation_rules ar ON ae.rule_id = ar.id
                WHERE ae.user_id = ?
            """
            params = [user_id]
            
            if rule_id:
                query += " AND ae.rule_id = ?"
                params.append(rule_id)
            
            if slug:
                query += " AND json_extract(ar.action_parameters, '$.slug') = ?"
                params.append(slug)
            
            query += " ORDER BY ae.executed_at DESC LIMIT ?"
            params.append(limit)
            
            rows = db_optimizer.execute_query(query, tuple(params))
            
            logs = []
            for row in rows:
                action_params = json.loads(row['action_parameters']) if row.get('action_parameters') else {}
                logs.append({
                    'execution_id': row['id'],
                    'rule_id': row['rule_id'],
                    'rule_name': row['rule_name'],
                    'slug': action_params.get('slug'),
                    'status': row['status'],
                    'trigger_data': json.loads(row['trigger_data']) if row.get('trigger_data') else {},
                    'action_result': json.loads(row['action_result']) if row.get('action_result') else {},
                    'executed_at': row['executed_at'],
                    'error_message': row['error_message']
                })
            
            return {
                'success': True,
                'data': {
                    'logs': logs,
                    'count': len(logs)
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching automation logs: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _analyze_email_patterns(self, user_id: int) -> Dict[str, Any]:
        """Analyze user's email patterns for automation suggestions"""
        try:
            # Get recent email activities
            activities_data = db_optimizer.execute_query(
                """SELECT la.activity_type, COUNT(*) as count
                   FROM lead_activities la
                   JOIN leads l ON la.lead_id = l.id
                   WHERE l.user_id = ? AND la.timestamp >= datetime('now', '-30 days')
                   GROUP BY la.activity_type""",
                (user_id,)
            )
            
            patterns = {}
            for activity in activities_data:
                patterns[activity['activity_type']] = activity['count']
            
            # Analyze for specific patterns
            patterns['quote_requests'] = patterns.get('email_received', 0)  # Simplified
            patterns['new_leads'] = patterns.get('email_received', 0)  # Simplified
            patterns['follow_ups_needed'] = patterns.get('email_received', 0)  # Simplified
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing email patterns: {e}")
            return {}
    
    def _handle_email_received_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle email received trigger"""
        return self.execute_automation_rules(TriggerType.EMAIL_RECEIVED, trigger_data, user_id)
    
    def _handle_email_sent_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle email sent trigger"""
        return self.execute_automation_rules(TriggerType.EMAIL_SENT, trigger_data, user_id)
    
    def _handle_lead_created_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle lead created trigger"""
        return self.execute_automation_rules(TriggerType.LEAD_CREATED, trigger_data, user_id)
    
    def _handle_lead_stage_changed_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle lead stage changed trigger"""
        return self.execute_automation_rules(TriggerType.LEAD_STAGE_CHANGED, trigger_data, user_id)
    
    def _handle_time_based_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle time-based trigger"""
        return self.execute_automation_rules(TriggerType.TIME_BASED, trigger_data, user_id)
    
    def _handle_keyword_detected_trigger(self, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle keyword detected trigger"""
        return self.execute_automation_rules(TriggerType.KEYWORD_DETECTED, trigger_data, user_id)
    
    # Advanced workflow action implementations
    def _execute_schedule_follow_up(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Schedule a follow-up action"""
        try:
            lead_id = action_data.get('lead_id')
            follow_up_date = action_data.get('follow_up_date')
            follow_up_type = action_data.get('follow_up_type', 'email')
            message = action_data.get('message', '')
            
            # Store follow-up in database
            follow_up_id = db_optimizer.execute_query(
                """INSERT INTO scheduled_follow_ups 
                   (user_id, lead_id, follow_up_date, follow_up_type, message, status, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, lead_id, follow_up_date, follow_up_type, message, 'scheduled', datetime.now().isoformat()),
                fetch=False
            )
            
            logger.info(f"Scheduled follow-up {follow_up_id} for lead {lead_id}")
            return {'success': True, 'follow_up_id': follow_up_id}
            
        except Exception as e:
            logger.error(f"Error scheduling follow-up: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_create_calendar_event(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            event_title = action_data.get('title', 'Meeting')
            event_date = action_data.get('date')
            event_duration = action_data.get('duration', 60)
            event_description = action_data.get('description', '')
            lead_id = action_data.get('lead_id')
            
            # Store calendar event in database
            event_id = db_optimizer.execute_query(
                """INSERT INTO calendar_events 
                   (user_id, lead_id, title, event_date, duration, description, status, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, lead_id, event_title, event_date, event_duration, event_description, 'scheduled', datetime.now().isoformat()),
                fetch=False
            )
            
            logger.info(f"Created calendar event {event_id}")
            return {'success': True, 'event_id': event_id}
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_update_crm_field(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Update a CRM field"""
        try:
            lead_id = action_data.get('lead_id')
            field_name = action_data.get('field_name')
            field_value = action_data.get('field_value')
            
            # Update lead field
            db_optimizer.execute_query(
                """UPDATE leads SET {} = ? WHERE id = ? AND user_id = ?""".format(field_name),
                (field_value, lead_id, user_id),
                fetch=False
            )
            
            logger.info(f"Updated CRM field {field_name} for lead {lead_id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error updating CRM field: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_trigger_webhook(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Trigger a webhook"""
        try:
            webhook_url = action_data.get('webhook_url')
            payload = action_data.get('payload', {})
            
            # Add user context to payload
            payload['user_id'] = user_id
            payload['timestamp'] = datetime.now().isoformat()
            
            # In a real implementation, you would make an HTTP request here
            # For now, we'll log the webhook trigger
            logger.info(f"Triggered webhook to {webhook_url} with payload: {payload}")
            
            return {'success': True, 'webhook_url': webhook_url}
            
        except Exception as e:
            logger.error(f"Error triggering webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_generate_document(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Generate a document"""
        try:
            template_id = action_data.get('template_id')
            lead_id = action_data.get('lead_id')
            variables = action_data.get('variables', {})
            
            # Import document templates system
            from core.document_templates_system import get_document_templates
            
            doc_templates = get_document_templates()
            document = doc_templates.generate_document(template_id, variables, user_id)
            
            logger.info(f"Generated document {document.id} for lead {lead_id}")
            return {'success': True, 'document_id': document.id}
            
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_send_sms(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Send SMS via Twilio when configured; otherwise log only."""
        try:
            phone_number = action_data.get('phone_number')
            message = action_data.get('message', '')
            lead_id = action_data.get('lead_id')
            if not phone_number or not message:
                return {'success': False, 'error': 'phone_number and message required'}
            to = str(phone_number).strip()
            if not to.startswith('+'):
                digits = ''.join(c for c in to if c.isdigit())
                to = ('+' + digits) if len(digits) == 11 and digits.startswith('1') else ('+1' + digits) if len(digits) == 10 else ('+' + digits)
            status = 'sent'
            error_msg = None
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            messaging_sid = os.getenv('TWILIO_MESSAGING_SERVICE_SID')
            if account_sid and auth_token and messaging_sid:
                try:
                    from twilio.rest import Client
                    client = Client(account_sid, auth_token)
                    msg = client.messages.create(
                        messaging_service_sid=messaging_sid,
                        body=message,
                        to=to,
                    )
                    logger.info("Twilio SMS sent to %s sid=%s", to, msg.sid)
                except Exception as e:
                    status = 'failed'
                    error_msg = str(e)
                    logger.exception("Twilio SMS error to %s", to)
            else:
                logger.info("SMS (no Twilio): to=%s body=%s", to, message[:50])
            try:
                db_optimizer.execute_query(
                    """INSERT INTO sms_messages (user_id, lead_id, phone_number, message, status, sent_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, lead_id, to, message, status, datetime.now().isoformat()),
                    fetch=False,
                )
            except Exception:
                pass
            return {'success': status == 'sent', 'error': error_msg} if error_msg else {'success': True}
        except Exception as e:
            logger.error("Error sending SMS: %s", e)
            return {'success': False, 'error': str(e)}
    
    def _execute_create_invoice(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create an invoice"""
        try:
            lead_id = action_data.get('lead_id')
            amount = action_data.get('amount', 0)
            description = action_data.get('description', '')
            due_date = action_data.get('due_date')
            
            # Create invoice record
            invoice_id = db_optimizer.execute_query(
                """INSERT INTO invoices 
                   (user_id, lead_id, amount, description, due_date, status, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, lead_id, amount, description, due_date, 'pending', datetime.now().isoformat()),
                fetch=False
            )
            
            logger.info(f"Created invoice {invoice_id} for lead {lead_id}")
            return {'success': True, 'invoice_id': invoice_id}
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_assign_team_member(self, action_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Assign team member to lead"""
        try:
            lead_id = action_data.get('lead_id')
            team_member_id = action_data.get('team_member_id')
            assignment_type = action_data.get('assignment_type', 'owner')
            
            # Update lead assignment
            db_optimizer.execute_query(
                """UPDATE leads SET assigned_to = ?, assignment_type = ? WHERE id = ? AND user_id = ?""",
                (team_member_id, assignment_type, lead_id, user_id),
                fetch=False
            )
            
            logger.info(f"Assigned team member {team_member_id} to lead {lead_id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error assigning team member: {e}")
            return {'success': False, 'error': str(e)}

# Global automation engine instance
automation_engine = AutomationEngine()

# Export the automation engine
__all__ = ['AutomationEngine', 'automation_engine', 'AutomationRule', 'AutomationExecution', 'TriggerType', 'ActionType', 'AutomationStatus']
