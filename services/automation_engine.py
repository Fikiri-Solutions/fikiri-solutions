"""
Automation Engine with Rule-based Workflows
Handles automated email responses, lead management, and workflow automation
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from core.database_optimization import db_optimizer
from core.automation_run_events import (
    enter_automation_run_if_missing,
    get_automation_run_id,
    record_automation_run_event,
    record_automation_skipped_rule,
    record_automation_step_finished,
    record_automation_step_started,
)
from core.workflow_followups import schedule_follow_up as workflow_schedule_follow_up
from core.automation_trigger_conditions import (
    evaluate_if_group,
    trigger_condition_metadata,
    validate_if_group_structure,
)
from email_automation.parser import MinimalEmailParser
from services.automation_actions.crm_action import (
    CrmActionHandler,
    INBOUND_CRM_SYNC_SLUG,
    is_inbound_crm_sync_slug,
)
from services.automation_actions.email_action import EmailActionHandler
from services.automation_actions.sms_action import SmsActionHandler
from services.automation_actions.webhook_action import WebhookActionHandler

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


class ActionCapability(Enum):
    """Whether an action type is fully implemented, partial, or stub (not implemented)."""
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    STUB = "stub"


# Per-action capability: do not fake success for STUB; return 501 from API.
ACTION_CAPABILITIES: Dict[ActionType, ActionCapability] = {
    ActionType.SEND_EMAIL: ActionCapability.IMPLEMENTED,
    ActionType.UPDATE_LEAD_STAGE: ActionCapability.IMPLEMENTED,
    ActionType.ADD_LEAD_ACTIVITY: ActionCapability.IMPLEMENTED,
    ActionType.APPLY_LABEL: ActionCapability.STUB,
    ActionType.ARCHIVE_EMAIL: ActionCapability.STUB,
    ActionType.CREATE_TASK: ActionCapability.STUB,
    ActionType.SEND_NOTIFICATION: ActionCapability.PARTIAL,
    ActionType.SCHEDULE_FOLLOW_UP: ActionCapability.IMPLEMENTED,
    ActionType.CREATE_CALENDAR_EVENT: ActionCapability.IMPLEMENTED,
    ActionType.UPDATE_CRM_FIELD: ActionCapability.IMPLEMENTED,
    ActionType.TRIGGER_WEBHOOK: ActionCapability.IMPLEMENTED,
    ActionType.GENERATE_DOCUMENT: ActionCapability.PARTIAL,
    ActionType.SEND_SMS: ActionCapability.PARTIAL,
    ActionType.CREATE_INVOICE: ActionCapability.IMPLEMENTED,
    ActionType.ASSIGN_TEAM_MEMBER: ActionCapability.IMPLEMENTED,
}

def _is_inbound_crm_sync_slug(slug: Any) -> bool:
    """Backward-compatible shim for tests/callers."""
    return is_inbound_crm_sync_slug(slug)


_ACTION_CAPABILITY_DESCRIPTIONS: Dict[ActionType, str] = {
    ActionType.SEND_EMAIL:
        "Sends outbound email via Gmail OAuth when connected; "
        "otherwise SendGrid/SMTP (FROM_EMAIL) when configured.",
    ActionType.APPLY_LABEL: "Gmail label API not integrated.",
    ActionType.ARCHIVE_EMAIL: "Gmail archive API not integrated.",
    ActionType.CREATE_TASK: "Task system not integrated.",
    ActionType.SEND_NOTIFICATION: "Works when Slack webhook URL is configured (action param or SLACK_WEBHOOK_URL).",
    ActionType.TRIGGER_WEBHOOK: "Real HTTP POST with timeout and retries; optional HMAC signature.",
    ActionType.GENERATE_DOCUMENT: "Depends on document templates.",
    ActionType.SEND_SMS: "Works when Twilio is configured.",
}

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
        self.crm_action_handler = CrmActionHandler(logger)
        self.email_action_handler = EmailActionHandler(logger)
        self.sms_action_handler = SmsActionHandler(logger)
        self.webhook_action_handler = WebhookActionHandler(logger)
        self.trigger_handlers = {
            TriggerType.EMAIL_RECEIVED: self._handle_email_received_trigger,
            TriggerType.EMAIL_SENT: self._handle_email_sent_trigger,
            TriggerType.LEAD_CREATED: self._handle_lead_created_trigger,
            TriggerType.LEAD_STAGE_CHANGED: self._handle_lead_stage_changed_trigger,
            TriggerType.TIME_BASED: self._handle_time_based_trigger,
            TriggerType.KEYWORD_DETECTED: self._handle_keyword_detected_trigger
        }
        
        self.action_handlers = {
            ActionType.SEND_EMAIL: self.email_action_handler.execute_send_email,
            ActionType.UPDATE_LEAD_STAGE: self.crm_action_handler.execute_update_lead_stage,
            ActionType.ADD_LEAD_ACTIVITY: self.crm_action_handler.execute_add_lead_activity,
            ActionType.APPLY_LABEL: self._execute_apply_label,
            ActionType.ARCHIVE_EMAIL: self._execute_archive_email,
            ActionType.CREATE_TASK: self._execute_create_task,
            ActionType.SEND_NOTIFICATION: self._execute_send_notification,
            # Advanced workflow action handlers
            ActionType.SCHEDULE_FOLLOW_UP: self._execute_schedule_follow_up,
            ActionType.CREATE_CALENDAR_EVENT: self._execute_create_calendar_event,
            ActionType.UPDATE_CRM_FIELD: self.crm_action_handler.execute_update_crm_field,
            ActionType.TRIGGER_WEBHOOK: self.webhook_action_handler.execute_trigger_webhook,
            ActionType.GENERATE_DOCUMENT: self._execute_generate_document,
            ActionType.SEND_SMS: self.sms_action_handler.execute_send_sms,
            ActionType.CREATE_INVOICE: self._execute_create_invoice,
            ActionType.ASSIGN_TEAM_MEMBER: self._execute_assign_team_member
        }
    
    def get_trigger_condition_metadata(self) -> Dict[str, Any]:
        """Schema for trigger IF-groups (fields and operators per trigger type)."""
        return {"success": True, "data": trigger_condition_metadata()}

    def _validate_trigger_conditions_shape(
        self, trigger_type: str, trigger_conditions: Any
    ) -> Optional[str]:
        if trigger_conditions is None:
            return None
        if not isinstance(trigger_conditions, dict):
            return "trigger_conditions must be a JSON object"
        if "if" not in trigger_conditions:
            return None
        ok, err = validate_if_group_structure(trigger_type, trigger_conditions.get("if"))
        if not ok:
            return err
        return None

    def get_action_capabilities(self) -> Dict[str, Any]:
        """Return per-action capability flags for UI/API. implemented | partial | stub."""
        capabilities = []
        for action_type, cap in ACTION_CAPABILITIES.items():
            capabilities.append({
                "action_type": action_type.value,
                "capability": cap.value,
                "description": _ACTION_CAPABILITY_DESCRIPTIONS.get(action_type, ""),
            })
        return {"success": True, "data": {"capabilities": capabilities}}

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

            tc_err = self._validate_trigger_conditions_shape(
                rule_data["trigger_type"],
                rule_data.get("trigger_conditions"),
            )
            if tc_err:
                return {
                    "success": False,
                    "error": tc_err,
                    "error_code": "INVALID_TRIGGER_CONDITIONS",
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

            if "trigger_conditions" in updates:
                tc_err = self._validate_trigger_conditions_shape(
                    rule_data[0]["trigger_type"],
                    updates["trigger_conditions"],
                )
                if tc_err:
                    return {
                        "success": False,
                        "error": tc_err,
                        "error_code": "INVALID_TRIGGER_CONDITIONS",
                    }

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

    def run_single_rule(self, rule: AutomationRule, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single automation rule (used by scheduler time-based execution)."""
        trigger_data = trigger_data or {}
        with enter_automation_run_if_missing(trigger_data, "scheduler") as created_ctx:
            if created_ctx:
                record_automation_run_event(
                    rule.user_id,
                    "automation.triggered",
                    payload={
                        "trigger_type": TriggerType.TIME_BASED.value,
                        "rule_id": rule.id,
                        "scheduled_run": True,
                    },
                )
            result = self._execute_rule(rule, trigger_data)
            if get_automation_run_id() and created_ctx:
                record_automation_run_event(
                    rule.user_id,
                    "automation.completed",
                    status="ok" if result.get("success") else "failed",
                    payload={"rule_id": rule.id, "mode": "scheduler"},
                )
            return result

    def get_due_time_based_rules(self) -> List[tuple]:
        """Return list of (rule, trigger_data) for due time-based rules in UTC."""
        try:
            now_utc = datetime.utcnow()
            default_hour = 9
            rows = db_optimizer.execute_query(
                """SELECT * FROM automation_rules
                   WHERE trigger_type = ? AND status = ?""",
                (TriggerType.TIME_BASED.value, AutomationStatus.ACTIVE.value)
            )
            due = []
            for rule_data in rows:
                params = rule_data.get('action_parameters')
                if isinstance(params, str):
                    try:
                        params = json.loads(params) if params else {}
                    except json.JSONDecodeError:
                        params = {}
                frequency = (params.get('frequency') or 'daily').lower()
                hour = params.get('run_at_hour', default_hour)
                try:
                    hour = int(hour)
                except (TypeError, ValueError):
                    hour = default_hour

                if now_utc.hour != hour:
                    continue

                last_executed = rule_data.get('last_executed')
                if last_executed and isinstance(last_executed, str):
                    try:
                        last_executed = datetime.fromisoformat(last_executed.replace('Z', '+00:00'))
                    except Exception:
                        last_executed = None
                if last_executed and last_executed.tzinfo:
                    last_executed = last_executed.replace(tzinfo=None)

                last_date = last_executed.date() if last_executed else None
                today = now_utc.date()
                if frequency == 'daily':
                    if last_date is not None and last_date >= today:
                        continue
                elif frequency == 'weekly':
                    start_of_week = today - timedelta(days=now_utc.weekday())
                    if last_date is not None and last_date >= start_of_week:
                        continue
                else:
                    continue

                rule = self._format_rule(rule_data)
                due.append((rule, {'scheduled_run': True, 'frequency': frequency}))
            return due
        except Exception as e:
            logger.error("get_due_time_based_rules error: %s", e)
            return []
    
    def execute_automation_rules(
        self,
        trigger_type: TriggerType,
        trigger_data: Dict[str, Any],
        user_id: int,
        *,
        automation_source: str = "engine",
    ) -> Dict[str, Any]:
        """Execute automation rules based on trigger"""
        trigger_data = trigger_data or {}
        with enter_automation_run_if_missing(trigger_data, automation_source) as created_ctx:
            if created_ctx:
                record_automation_run_event(
                    user_id,
                    "automation.triggered",
                    payload={"trigger_type": trigger_type.value, "user_id": user_id},
                )
            try:
                # Get active rules for trigger type (rulepack compliance: specific columns)
                rules_data = db_optimizer.execute_query(
                    """SELECT id, user_id, name, description, trigger_type, trigger_conditions,
                       action_type, action_parameters, status, created_at, updated_at,
                       last_executed, execution_count, success_count, error_count
                       FROM automation_rules
                       WHERE user_id = ? AND trigger_type = ? AND status = ?
                       ORDER BY created_at ASC, id ASC""",
                    (user_id, trigger_type.value, AutomationStatus.ACTIVE.value),
                )

                executed_rules = []
                failed_rules = []

                for rule_data in rules_data:
                    rule = self._format_rule(rule_data)

                    if not self._check_trigger_conditions(rule, trigger_data):
                        record_automation_skipped_rule(
                            user_id, rule, trigger_data, "trigger_conditions_not_met"
                        )
                        continue

                    execution_result = self._execute_rule(rule, trigger_data)

                    if execution_result["success"]:
                        self._merge_lead_id_into_trigger(trigger_data, execution_result)
                        executed_rules.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "result": execution_result.get("data"),
                            }
                        )
                    else:
                        failed_rules.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "error": execution_result.get("error"),
                                "error_code": execution_result.get("error_code"),
                            }
                        )

                if get_automation_run_id() and created_ctx:
                    st = "ok" if not failed_rules else "partial"
                    record_automation_run_event(
                        user_id,
                        "automation.completed",
                        status=st,
                        payload={
                            "total_executed": len(executed_rules),
                            "total_failed": len(failed_rules),
                            "trigger_type": trigger_type.value,
                        },
                    )

                return {
                    "success": True,
                    "data": {
                        "executed_rules": executed_rules,
                        "failed_rules": failed_rules,
                        "total_executed": len(executed_rules),
                        "total_failed": len(failed_rules),
                    },
                }

            except Exception as e:
                logger.error(f"Error executing automation rules: {e}")
                if get_automation_run_id() and created_ctx:
                    record_automation_run_event(
                        user_id,
                        "automation.run_failed",
                        status="failed",
                        error_message=str(e)[:2000],
                        payload={"trigger_type": trigger_type.value},
                    )
                return {
                    "success": False,
                    "error": str(e),
                    "data": None,
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

    def execute_rules(self, user_id: int, rule_ids: List[int]) -> List[Dict[str, Any]]:
        """Execute specific rules by ID (used by /automation/execute). Runs synchronously."""
        with enter_automation_run_if_missing(None, "api_manual") as created_ctx:
            if created_ctx:
                record_automation_run_event(
                    user_id,
                    "automation.triggered",
                    payload={"payload_type": "rule_ids", "rule_ids": list(rule_ids)},
                )
            results = []
            for rule_id in rule_ids:
                rule_data = db_optimizer.execute_query(
                    """SELECT id, user_id, name, description, trigger_type, trigger_conditions,
                       action_type, action_parameters, status, created_at, updated_at,
                       last_executed, execution_count, success_count, error_count
                       FROM automation_rules WHERE id = ? AND user_id = ? AND status = ?""",
                    (rule_id, user_id, AutomationStatus.ACTIVE.value),
                )
                if not rule_data:
                    results.append({"rule_id": rule_id, "success": False, "error": "Rule not found or inactive"})
                    continue
                rule = self._format_rule(rule_data[0])
                trigger_data = self._synthetic_trigger_data_for_rule(rule)
                execution_result = self._execute_rule(rule, trigger_data)
                results.append(
                    {
                        "rule_id": rule_id,
                        "rule_name": rule.name,
                        "success": execution_result.get("success", False),
                        "error": execution_result.get("error"),
                        "error_code": execution_result.get("error_code"),
                        "data": execution_result.get("data"),
                    }
                )
            if get_automation_run_id() and created_ctx:
                any_fail = any(not r.get("success") for r in results)
                record_automation_run_event(
                    user_id,
                    "automation.completed",
                    status="ok" if not any_fail else "partial",
                    payload={"results_count": len(results), "any_failure": any_fail},
                )
            return results

    def _synthetic_trigger_data_for_rule(self, rule: AutomationRule) -> Dict[str, Any]:
        """Build minimal trigger data for a rule when running by ID (e.g. test)."""
        if rule.trigger_type == TriggerType.EMAIL_RECEIVED:
            return {"sender_email": "test@example.com", "subject": "Test", "text": "Test run"}
        if rule.trigger_type == TriggerType.LEAD_CREATED:
            return {"lead_id": 0, "source": "manual"}
        if rule.trigger_type == TriggerType.LEAD_STAGE_CHANGED:
            return {"lead_id": 0, "old_stage": "new", "new_stage": "contacted"}
        if rule.trigger_type == TriggerType.TIME_BASED:
            return {"timestamp": datetime.now().isoformat()}
        if rule.trigger_type == TriggerType.KEYWORD_DETECTED:
            return {"text": "test keyword", "sender_email": "test@example.com"}
        return {"trigger": rule.trigger_type.value}

    def test_rule(self, rule_id: int, test_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Test a single rule with provided trigger data (used by /automation/test)."""
        rule_data = db_optimizer.execute_query(
            """SELECT id, user_id, name, description, trigger_type, trigger_conditions,
               action_type, action_parameters, status, created_at, updated_at,
               last_executed, execution_count, success_count, error_count
               FROM automation_rules WHERE id = ? AND user_id = ?""",
            (rule_id, user_id)
        )
        if not rule_data:
            return {"success": False, "error": "Rule not found", "error_code": "RULE_NOT_FOUND"}
        rule = self._format_rule(rule_data[0])
        trigger_data = test_data if test_data else self._synthetic_trigger_data_for_rule(rule)
        with enter_automation_run_if_missing(trigger_data, "test") as created_ctx:
            if created_ctx:
                record_automation_run_event(
                    user_id,
                    "automation.triggered",
                    payload={"mode": "test", "rule_id": rule_id},
                )
            result = self._execute_rule(rule, trigger_data)
            if get_automation_run_id() and created_ctx:
                record_automation_run_event(
                    user_id,
                    "automation.completed",
                    status="ok" if result.get("success") else "failed",
                    payload={"mode": "test", "rule_id": rule_id},
                )
        result["rule_id"] = rule_id
        return result

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

        def _to_dt(value):
            # psycopg2 returns datetime objects natively; sqlite returns ISO strings.
            # Accept either to keep this hot path working on both backends.
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(value)

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
            created_at=_to_dt(rule_data['created_at']),
            updated_at=_to_dt(rule_data['updated_at']),
            last_executed=_to_dt(rule_data.get('last_executed')),
            execution_count=rule_data['execution_count'],
            success_count=rule_data['success_count'],
            error_count=rule_data['error_count']
        )
    
    def _check_trigger_conditions(self, rule: AutomationRule, trigger_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        conditions = rule.trigger_conditions
        if isinstance(conditions, dict):
            if_block = conditions.get("if")
            if isinstance(if_block, dict):
                cond_list = if_block.get("conditions")
                if isinstance(cond_list, list) and len(cond_list) > 0:
                    return evaluate_if_group(
                        rule.trigger_type.value,
                        trigger_data or {},
                        if_block,
                    )

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
        user_id = rule.user_id
        try:
            action_handler = self.action_handlers.get(rule.action_type)
            if not action_handler:
                res = {"success": False, "error": f"No handler for action type: {rule.action_type}"}
                if get_automation_run_id():
                    record_automation_step_finished(user_id, rule, trigger_data, res)
                return res

            if get_automation_run_id():
                record_automation_step_started(user_id, rule, trigger_data)
            try:
                handler_trigger = dict(trigger_data or {})
                handler_trigger["_automation_rule_id"] = rule.id
                result = action_handler(rule.action_parameters, handler_trigger, user_id)
                self._update_rule_stats(rule.id, result["success"])
                self._log_execution(rule.id, user_id, trigger_data, result)
                if get_automation_run_id():
                    record_automation_step_finished(user_id, rule, trigger_data, result)
                return result
            except Exception as handler_err:
                logger.error(f"Error executing rule {rule.id}: {handler_err}")
                err_res = {"success": False, "error": str(handler_err)}
                if get_automation_run_id():
                    record_automation_step_finished(user_id, rule, trigger_data, err_res)
                return err_res

        except Exception as e:
            logger.error(f"Error executing rule {rule.id}: {e}")
            err_res = {"success": False, "error": str(e)}
            if get_automation_run_id():
                record_automation_step_finished(user_id, rule, trigger_data, err_res)
            return err_res
    
    def _merge_lead_id_into_trigger(
        self, trigger_data: Dict[str, Any], execution_result: Dict[str, Any]
    ) -> None:
        """Allow later rules in the same run (e.g. SCHEDULE_FOLLOW_UP) to see lead_id from CRM actions."""
        lead_id = self._lead_id_from_action_result(execution_result)
        if lead_id is None:
            return
        trigger_data["lead_id"] = lead_id

    def _lead_id_from_action_result(self, execution_result: Dict[str, Any]) -> Optional[int]:
        if not execution_result.get("success"):
            return None
        data = execution_result.get("data")
        if not isinstance(data, dict):
            return None
        lid = data.get("lead_id")
        if lid is None:
            lead_obj = data.get("lead")
            if isinstance(lead_obj, dict):
                lid = lead_obj.get("id")
        if lid is None:
            return None
        try:
            return int(lid)
        except (TypeError, ValueError):
            return None

    def _parse_email_address(self, raw: Optional[str]) -> str:
        """Backward-compatible wrapper for tests/callers."""
        return self.email_action_handler.parse_email_address(raw)

    def _sanitize_email_subject(self, subject: str) -> str:
        """Backward-compatible wrapper for tests/callers."""
        return self.email_action_handler.sanitize_email_subject(subject)

    def _send_email_idempotency_key(
        self,
        user_id: int,
        rule_id: int,
        to_email: str,
        subject: str,
        body: str,
        trigger_data: Dict[str, Any],
    ) -> str:
        """Backward-compatible wrapper for tests/callers."""
        return self.email_action_handler.send_email_idempotency_key(
            user_id=user_id,
            rule_id=rule_id,
            to_email=to_email,
            subject=subject,
            body=body,
            trigger_data=trigger_data,
        )

    def _execute_send_email(
        self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.email_action_handler.execute_send_email(
            parameters=parameters,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_update_lead_stage(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.crm_action_handler.execute_update_lead_stage(
            parameters=parameters,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_add_lead_activity(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.crm_action_handler.execute_add_lead_activity(
            parameters=parameters,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_apply_label(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute apply label action. Stub: Gmail label API not integrated."""
        if ACTION_CAPABILITIES.get(ActionType.APPLY_LABEL) == ActionCapability.STUB:
            return {
                "success": False,
                "error": "Apply label is not yet implemented; Gmail label API not integrated.",
                "error_code": "NOT_IMPLEMENTED",
            }
        try:
            label = parameters.get('label')
            email_id = trigger_data.get('email_id')
            if not label or not email_id:
                return {'success': False, 'error': 'Missing label or email_id parameter'}
            logger.info(f"Applying label {label} to email {email_id}")
            return {
                'success': True,
                'data': {'action': 'label_applied', 'label': label, 'email_id': email_id}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_archive_email(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute archive email action. Stub: Gmail archive API not integrated."""
        if ACTION_CAPABILITIES.get(ActionType.ARCHIVE_EMAIL) == ActionCapability.STUB:
            return {
                "success": False,
                "error": "Archive email is not yet implemented; Gmail archive API not integrated.",
                "error_code": "NOT_IMPLEMENTED",
            }
        try:
            email_id = trigger_data.get('email_id')
            if not email_id:
                return {'success': False, 'error': 'Missing email_id parameter'}
            logger.info(f"Archiving email {email_id}")
            return {'success': True, 'data': {'action': 'email_archived', 'email_id': email_id}}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_create_task(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute create task action. Stub: task management not integrated."""
        if ACTION_CAPABILITIES.get(ActionType.CREATE_TASK) == ActionCapability.STUB:
            return {
                "success": False,
                "error": "Create task is not yet implemented; task management system not integrated.",
                "error_code": "NOT_IMPLEMENTED",
            }
        try:
            task_type = parameters.get('task_type', 'general')
            priority = parameters.get('priority', 'medium')
            description = parameters.get('description', 'Automated task')
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
            return {'success': False, 'error': str(e)}
    
    def _execute_send_notification(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Execute send notification. When slack_webhook_url (or SLACK_WEBHOOK_URL) is set, POST to Slack; else NOT_IMPLEMENTED."""
        webhook_url = (parameters.get('slack_webhook_url') or parameters.get('webhook_url') or os.getenv('SLACK_WEBHOOK_URL') or '').strip()
        if not webhook_url:
            return {
                "success": False,
                "error": "Send notification requires slack_webhook_url in action parameters or SLACK_WEBHOOK_URL env.",
                "error_code": "NOT_IMPLEMENTED",
            }
        message = parameters.get('message', 'Automation executed')
        notification_type = parameters.get('type', 'info')
        channel = parameters.get('channel')
        # Build Slack payload (Incoming Webhooks)
        payload = {"text": f"[{notification_type}] {message}"}
        if channel:
            payload["channel"] = channel
        try:
            import requests
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Slack notification sent to webhook")
            return {
                'success': True,
                'data': {
                    'action': 'notification_sent',
                    'message': message,
                    'type': notification_type,
                }
            }
        except Exception as e:
            logger.warning("Slack webhook failed: %s", e)
            return {'success': False, 'error': str(e), 'error_code': 'NOTIFICATION_DELIVERY_FAILED'}
    
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
                slug_expr = db_optimizer.json_field_expr("ar.action_parameters", "$.slug")
                query += f" AND {slug_expr} = ?"
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
                f"""SELECT la.activity_type, COUNT(*) as count
                   FROM lead_activities la
                   JOIN leads l ON la.lead_id = l.id
                   WHERE l.user_id = ? AND {db_optimizer.sql_column_newer_than_n_days_ago('la.timestamp', 30)}
                   GROUP BY la.activity_type""",
                (user_id,),
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
    def _execute_schedule_follow_up(self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Schedule a follow-up. For calendar_followups: lead_id and follow_up_date from trigger + delay_hours."""
        try:
            lead_id = action_data.get('lead_id') or trigger_data.get('lead_id')
            follow_up_date = action_data.get('follow_up_date')
            follow_up_type = action_data.get('follow_up_type', 'email')
            message = action_data.get('message', 'Follow-up reminder')
            delay_hours = action_data.get('delay_hours')
            if follow_up_date is None and delay_hours is not None:
                try:
                    follow_up_date = (datetime.utcnow() + timedelta(hours=int(delay_hours))).isoformat()
                except (TypeError, ValueError):
                    pass
            if not follow_up_date or lead_id is None:
                return {'success': False, 'error': 'lead_id and follow_up_date or delay_hours required'}
            result = workflow_schedule_follow_up(user_id, lead_id, follow_up_date, follow_up_type, message)
            if not result.get('success'):
                return result
            return {'success': True, 'follow_up_id': result.get('follow_up_id'), 'data': result}
        except Exception as e:
            logger.error("Error scheduling follow-up: %s", e)
            return {'success': False, 'error': str(e)}
    
    def _execute_create_calendar_event(self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create a calendar event. lead_id and date can come from trigger_data."""
        try:
            event_title = action_data.get('title', 'Meeting')
            event_date = action_data.get('date') or trigger_data.get('event_date')
            event_duration = action_data.get('duration', 60)
            event_description = action_data.get('description', '')
            lead_id = action_data.get('lead_id') or trigger_data.get('lead_id')
            if not event_date:
                return {'success': False, 'error': 'event date required'}
            event_id = db_optimizer.execute_query(
                """INSERT INTO calendar_events 
                   (user_id, lead_id, title, event_date, duration, description, status, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, lead_id, event_title, event_date, event_duration, event_description, 'scheduled', datetime.now().isoformat()),
                fetch=False
            )
            logger.info("Created calendar event %s", event_id)
            return {'success': True, 'event_id': event_id}
        except Exception as e:
            logger.error("Error creating calendar event: %s", e)
            return {'success': False, 'error': str(e)}
    
    def _execute_update_crm_field(self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.crm_action_handler.execute_update_crm_field(
            action_data=action_data,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_trigger_webhook(self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.webhook_action_handler.execute_trigger_webhook(
            parameters=parameters,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_generate_document(
        self,
        action_data: Dict[str, Any],
        trigger_data: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        """Generate a document"""
        try:
            template_id = action_data.get('template_id')
            lead_id = action_data.get('lead_id') or trigger_data.get('lead_id')
            variables = action_data.get('variables', {})
            
            # Import document templates system
            from core.document_templates_system import get_document_templates
            
            doc_templates = get_document_templates()
            document = doc_templates.generate_document(template_id, variables, user_id)
            
            logger.info(f"Generated document {document.id} for lead {lead_id}")
            return {
                'success': True,
                'document_id': document.id,
                'data': {'document_id': document.id, 'lead_id': lead_id},
            }
            
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_send_sms(
        self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper for tests/callers."""
        return self.sms_action_handler.execute_send_sms(
            action_data=action_data,
            trigger_data=trigger_data,
            user_id=user_id,
        )
    
    def _execute_create_invoice(
        self,
        action_data: Dict[str, Any],
        trigger_data: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        """Create an invoice"""
        try:
            lead_id = action_data.get('lead_id') or trigger_data.get('lead_id')
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
            return {
                'success': True,
                'invoice_id': invoice_id,
                'data': {'invoice_id': invoice_id, 'lead_id': lead_id},
            }
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_assign_team_member(
        self,
        action_data: Dict[str, Any],
        trigger_data: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        """Assign team member to lead"""
        try:
            lead_id = action_data.get('lead_id') or trigger_data.get('lead_id')
            team_member_id = action_data.get('team_member_id')
            assignment_type = action_data.get('assignment_type', 'owner')
            
            # Update lead assignment
            db_optimizer.execute_query(
                """UPDATE leads SET assigned_to = ?, assignment_type = ? WHERE id = ? AND user_id = ?""",
                (team_member_id, assignment_type, lead_id, user_id),
                fetch=False
            )
            
            logger.info(f"Assigned team member {team_member_id} to lead {lead_id}")
            return {'success': True, 'data': {'lead_id': lead_id}}
            
        except Exception as e:
            logger.error(f"Error assigning team member: {e}")
            return {'success': False, 'error': str(e)}

# Global automation engine instance
automation_engine = AutomationEngine()

def run_due_time_based_automations() -> Dict[str, Any]:
    """Run all due time-based automation rules (daily/weekly). Called from scheduler."""
    try:
        due = automation_engine.get_due_time_based_rules()
        executed = 0
        failed = 0
        for rule, trigger_data in due:
            result = automation_engine.run_single_rule(rule, trigger_data)
            if result.get('success'):
                executed += 1
            else:
                failed += 1
        return {'executed': executed, 'failed': failed, 'due_count': len(due)}
    except Exception as e:
        logger.error("run_due_time_based_automations error: %s", e)
        return {'executed': 0, 'failed': 0, 'due_count': 0, 'error': str(e)}

# Export the automation engine
__all__ = ['AutomationEngine', 'automation_engine', 'AutomationRule', 'AutomationExecution', 'TriggerType', 'ActionType', 'AutomationStatus', 'run_due_time_based_automations']
