"""
Enhanced CRM Service with Real-time Gmail Sync
Manages leads, contacts, and activities with automatic Gmail integration
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from core.database_optimization import db_optimizer
from crm.event_log import record_crm_event
from core.lead_scoring_service import get_lead_scoring_service
# Gmail OAuth functionality - disabled pending OAuth refactor
# from core.gmail_oauth import gmail_oauth_manager, gmail_sync_manager
gmail_oauth_manager = None
gmail_sync_manager = None

logger = logging.getLogger(__name__)

_ACTIVE_LEADS_SQL = " (withdrawn_at IS NULL) "


def _crm_tags_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw]
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, list):
            return [str(t) for t in parsed]
    except (TypeError, json.JSONDecodeError):
        pass
    return []


def _crm_meta_dict(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        if isinstance(raw, str):
            return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return {}


def lead_row_to_public_dict(lead_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not lead_row:
        return {}
    row = dict(lead_row)
    row["tags"] = _crm_tags_list(row.get("tags"))
    row["metadata"] = _crm_meta_dict(row.get("metadata"))
    for key in ("created_at", "updated_at", "last_contact"):
        val = row.get(key)
        if val is not None and hasattr(val, "isoformat"):
            row[key] = val.isoformat()
    return row


def lead_dataclass_to_public_dict(lead: Any) -> Dict[str, Any]:
    if lead is None:
        return {}
    if is_dataclass(lead):
        d = asdict(lead)
        for k, v in list(d.items()):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        return d
    return dict(lead) if isinstance(lead, dict) else {}


@dataclass
class Lead:
    """Lead data structure"""
    id: int
    user_id: int
    email: str
    name: str
    phone: Optional[str]
    company: Optional[str]
    source: str
    stage: str
    score: int
    created_at: datetime
    updated_at: datetime
    last_contact: Optional[datetime]
    notes: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class LeadActivity:
    """Lead activity data structure"""
    id: int
    lead_id: int
    activity_type: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any]

class EnhancedCRMService:
    """Enhanced CRM service with real-time Gmail sync"""
    
    def __init__(self):
        self.lead_stages = ['new', 'contacted', 'replied', 'qualified', 'closed']
        self.activity_types = [
            'email_received', 'email_sent', 'call_made', 'meeting_scheduled',
            'proposal_sent', 'contract_signed', 'follow_up', 'note_added'
        ]

    def get_lead(self, lead_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Return raw lead row as dict, or None if not owned by user."""
        rows = db_optimizer.execute_query(
            """SELECT id, user_id, email, name, phone, company, source, stage, score,
                      created_at, updated_at, last_contact, notes, tags, metadata, withdrawn_at
               FROM leads WHERE id = ? AND user_id = ?""",
            (lead_id, user_id),
        )
        if not rows:
            return None
        return dict(rows[0])

    def list_crm_events(
        self, lead_id: int, user_id: int, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Append-only CRM timeline for a lead (lead + contact entity types)."""
        limit = min(max(limit, 1), 200)
        offset = max(offset, 0)
        own = db_optimizer.execute_query(
            "SELECT id FROM leads WHERE id = ? AND user_id = ?",
            (lead_id, user_id),
        )
        if not own:
            return {
                "success": False,
                "error": "Lead not found",
                "error_code": "LEAD_NOT_FOUND",
            }
        rows = db_optimizer.execute_query(
            """
            SELECT id, created_at, event_type,
                   entity_type, entity_id, correlation_id, supersedes_event_id,
                   payload_json, payload_truncated,
                   status, error_message, source
            FROM crm_events
            WHERE user_id = ? AND entity_id = ? AND entity_type IN ('lead', 'contact')
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, lead_id, limit, offset),
        )
        return {
            "success": True,
            "data": {"events": [dict(r) for r in (rows or [])], "limit": limit, "offset": offset},
        }
    
    def get_leads_summary(self, user_id: int, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get comprehensive leads summary with analytics and pagination"""
        base_query = """SELECT id, user_id, email, name, phone, company, source, stage, score, 
                       created_at, updated_at, last_contact, notes, tags, metadata 
                       FROM leads WHERE user_id = ?"""
        params = [user_id]
        if not (filters and filters.get("include_withdrawn")):
            base_query += f" AND {_ACTIVE_LEADS_SQL}"
        
        if filters:
            if filters.get('stage'):
                base_query += " AND stage = ?"
                params.append(filters['stage'])
            if filters.get('time_period'):
                cutoff_date = self._get_cutoff_date(filters['time_period'])
                base_query += " AND created_at >= ?"
                params.append(cutoff_date.isoformat())
            if filters.get('company'):
                base_query += " AND company LIKE ?"
                params.append(f"%{filters['company']}%")
        
        base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        leads_data = db_optimizer.execute_query(base_query, tuple(params))
        
        count_query = "SELECT COUNT(*) as total FROM leads WHERE user_id = ?"
        count_params = [user_id]
        if not (filters and filters.get("include_withdrawn")):
            count_query += f" AND {_ACTIVE_LEADS_SQL}"
        if filters:
            if filters.get('stage'):
                count_query += " AND stage = ?"
                count_params.append(filters['stage'])
            if filters.get('time_period'):
                cutoff_date = self._get_cutoff_date(filters['time_period'])
                count_query += " AND created_at >= ?"
                count_params.append(cutoff_date.isoformat())
            if filters.get('company'):
                count_query += " AND company LIKE ?"
                count_params.append(f"%{filters['company']}%")
        
        total_count_result = db_optimizer.execute_query(count_query, tuple(count_params))
        total_count = total_count_result[0]['total'] if total_count_result else 0
        
        leads = [self._format_lead(lead_data) for lead_data in leads_data]
        analytics = self._get_leads_analytics(user_id, leads)
        
        return {
            'success': True,
            'data': {
                'leads': leads,
                'total_count': total_count,
                'returned_count': len(leads),
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(leads)) < total_count,
                'analytics': analytics,
                'filters_applied': filters or {}
            }
        }
    
    def create_lead(self, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lead"""
        required_fields = ['email', 'name']
        for field in required_fields:
            if not lead_data.get(field):
                return {'success': False, 'error': f'Missing required field: {field}', 'error_code': 'MISSING_FIELD'}
        
        existing = db_optimizer.execute_query(
            "SELECT id, withdrawn_at FROM leads WHERE user_id = ? AND email = ?",
            (user_id, lead_data['email'])
        )
        if existing:
            row = existing[0]
            if not row.get("withdrawn_at"):
                return {
                    "success": False,
                    "error": "Lead with this email already exists",
                    "error_code": "LEAD_EXISTS",
                }
            lead_id = row["id"]
            db_optimizer.execute_query(
                "UPDATE leads SET withdrawn_at = NULL, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND user_id = ?",
                (lead_id, user_id),
                fetch=False,
            )
            re_upd = {
                k: v
                for k, v in lead_data.items()
                if k
                in (
                    "name",
                    "phone",
                    "company",
                    "source",
                    "stage",
                    "notes",
                    "tags",
                    "metadata",
                )
                and v is not None
                and v != ""
            }
            if re_upd:
                return self.update_lead(lead_id, user_id, re_upd)
            self._add_lead_activity(lead_id, "note_added", "Lead reactivated after withdraw")
            return {
                "success": True,
                "data": {"lead_id": lead_id, "message": "Lead reactivated successfully"},
            }
        
        score_result = self._score_lead_data(lead_data, activity_count=0, last_activity=None)
        lead_data['score'] = score_result['score']
        lead_data['metadata'] = {
            **lead_data.get('metadata', {}),
            'lead_quality': score_result['quality'],
            'score_breakdown': score_result['breakdown']
        }
        db_optimizer.execute_query(
            """INSERT INTO leads (user_id, email, name, phone, company, source, stage, score, notes, tags, metadata) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, lead_data['email'], lead_data['name'],
             lead_data.get('phone'), lead_data.get('company'),
             lead_data.get('source', 'manual'), lead_data.get('stage', 'new'),
             lead_data.get('score', 0), lead_data.get('notes'), json.dumps(lead_data.get('tags', [])),
             json.dumps(lead_data.get('metadata', {}))),
            fetch=False
        )
        row = db_optimizer.execute_query(
            "SELECT id FROM leads WHERE user_id = ? AND email = ? ORDER BY id DESC LIMIT 1",
            (user_id, lead_data['email'])
        )
        if not row:
            logger.error("Lead INSERT succeeded but SELECT id failed for user_id=%s email=%s", user_id, lead_data['email'])
            raise ValueError("Failed to retrieve created lead id")
        lead_id = row[0]['id'] if isinstance(row[0], dict) else row[0][0]
        
        self._add_lead_activity(lead_id, 'note_added', "Lead created manually")
        correlation_id = str(lead_data.get("correlation_id") or uuid4())
        
        try:
            from services.automation_engine import automation_engine, TriggerType
            automation_engine.execute_automation_rules(
                TriggerType.LEAD_CREATED,
                {
                    'lead_id': lead_id,
                    'email': lead_data['email'],
                    'name': lead_data['name'],
                    'source': lead_data.get('source', 'manual'),
                    'score': lead_data.get('score', 0),
                    'correlation_id': correlation_id,
                },
                user_id,
                automation_source="crm",
            )
        except Exception as auto_error:
            logger.warning(f"Automation trigger failed: {auto_error}")

        record_crm_event(
            user_id=user_id,
            event_type="lead.created",
            entity_type="lead",
            entity_id=lead_id,
            payload={
                "email": lead_data["email"],
                "name": lead_data["name"],
                "source": lead_data.get("source", "manual"),
                "stage": lead_data.get("stage", "new"),
                "score": lead_data.get("score", 0),
            },
            correlation_id=correlation_id,
        )
        record_crm_event(
            user_id=user_id,
            event_type="contact.created",
            entity_type="contact",
            entity_id=lead_id,
            payload={
                "email": lead_data["email"],
                "name": lead_data["name"],
                "source": lead_data.get("source", "manual"),
            },
            correlation_id=correlation_id,
        )
        
        logger.info(f"Lead created: {lead_data['email']} for user {user_id}")
        return {
            'success': True,
            'data': {
                'lead_id': lead_id,
                'message': 'Lead created successfully',
                'correlation_id': correlation_id,
            },
        }
    
    def update_lead(self, lead_id: int, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update lead information"""
        try:
            # Verify lead ownership (rulepack compliance: specific columns, not SELECT *)
            lead_data = db_optimizer.execute_query(
                "SELECT id, user_id, email, name, phone, company, source, stage, score, created_at, updated_at, last_contact, notes, tags, metadata FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )
            
            if not lead_data:
                return {
                    'success': False,
                    'error': 'Lead not found',
                    'error_code': 'LEAD_NOT_FOUND'
                }

            updates = dict(updates)
            correlation_id = str(updates.get("correlation_id") or uuid4())

            if "sms_consent" in updates:
                consent_flag = bool(updates.pop("sms_consent"))
                base_meta = _crm_meta_dict(lead_data[0].get("metadata"))
                base_meta["sms_consent"] = consent_flag
                base_meta["sms_consent_at"] = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    if consent_flag
                    else None
                )
                extra_meta = updates.pop("metadata", None)
                if isinstance(extra_meta, dict):
                    base_meta.update(extra_meta)
                updates["metadata"] = base_meta

            # Build update query
            update_fields = []
            update_values = []
            
            allowed_fields = ['name', 'phone', 'company', 'source', 'stage', 'notes', 'tags', 'metadata']
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field in ['tags', 'metadata']:
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
            
            update_values.extend([lead_id, user_id])
            
            old_row = dict(lead_data[0])
            old_stage = old_row.get('stage') or 'new'
            old_score = int(old_row.get('score') or 0)
            old_tags = _crm_tags_list(old_row.get('tags'))
            old_meta = _crm_meta_dict(old_row.get('metadata'))
            
            query = f"UPDATE leads SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?"
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Add update activity
            self._add_lead_activity(lead_id, 'note_added', f"Lead updated: {', '.join(updates.keys())}")
            
            # Get updated lead (rulepack compliance: specific columns, not SELECT *)
            updated_lead = db_optimizer.execute_query(
                "SELECT id, user_id, email, name, phone, company, source, stage, score, created_at, updated_at, last_contact, notes, tags, metadata FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )[0]

            updated_lead_dict = dict(updated_lead)
            activity_count, last_activity = self._get_lead_activity_metrics(lead_id)
            score_result = self._score_lead_data(updated_lead_dict, activity_count, last_activity)
            metadata = dict(_crm_meta_dict(updated_lead_dict.get('metadata')))
            metadata['lead_quality'] = score_result['quality']
            metadata['score_breakdown'] = score_result['breakdown']
            db_optimizer.execute_query(
                "UPDATE leads SET score = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (score_result['score'], json.dumps(metadata), lead_id, user_id),
                fetch=False
            )
            updated_lead_dict['score'] = score_result['score']
            updated_lead_dict['metadata'] = json.dumps(metadata)
            
            # Trigger automation: LEAD_STAGE_CHANGED (if stage was updated)
            if 'stage' in updates and updates['stage'] != old_stage:
                try:
                    from services.automation_engine import automation_engine, TriggerType
                    automation_engine.execute_automation_rules(
                        TriggerType.LEAD_STAGE_CHANGED,
                        {
                            'lead_id': lead_id,
                            'old_stage': old_stage,
                            'new_stage': updates['stage'],
                            'email': updated_lead['email'],
                            'correlation_id': correlation_id,
                        },
                        user_id,
                        automation_source="crm",
                    )
                except Exception as auto_error:
                    logger.warning(f"Automation trigger failed: {auto_error}")

            new_stage = updated_lead_dict.get('stage') or 'new'
            new_score = int(updated_lead_dict.get('score') or 0)
            new_tags = _crm_tags_list(updated_lead_dict.get('tags'))
            new_meta = _crm_meta_dict(updated_lead_dict.get('metadata'))
            fields_changed = sorted([k for k in updates if k in allowed_fields])

            record_crm_event(
                user_id=user_id,
                event_type="lead.updated",
                entity_type="lead",
                entity_id=lead_id,
                payload={
                    "fields_changed": fields_changed,
                    "stage": {"from": old_stage, "to": new_stage},
                    "score": {"from": old_score, "to": new_score},
                },
                correlation_id=correlation_id,
            )
            record_crm_event(
                user_id=user_id,
                event_type="contact.updated",
                entity_type="contact",
                entity_id=lead_id,
                payload={"fields_changed": fields_changed, "stage": {"from": old_stage, "to": new_stage}},
                correlation_id=correlation_id,
            )
            if new_stage != old_stage:
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.stage_changed",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"from": old_stage, "to": new_stage},
                    correlation_id=correlation_id,
                )
            if new_stage == 'closed' and old_stage != 'closed':
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.closed",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"stage": new_stage},
                    correlation_id=correlation_id,
                )
            if old_stage == 'closed' and new_stage != 'closed':
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.reopened",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"stage": new_stage},
                    correlation_id=correlation_id,
                )
            added_tags = sorted(set(new_tags) - set(old_tags))
            removed_tags = sorted(set(old_tags) - set(new_tags))
            if added_tags:
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.tagged",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"tags": added_tags},
                    correlation_id=correlation_id,
                )
            if removed_tags:
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.untagged",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"tags": removed_tags},
                    correlation_id=correlation_id,
                )
            was_withdrawn = bool(old_meta.get('withdrawn_by_client')) or 'withdrawn' in old_tags
            now_withdrawn = (
                bool(new_meta.get('withdrawn_by_client'))
                or 'withdrawn' in new_tags
                or 'client_withdrawn' in new_tags
            )
            if now_withdrawn and not was_withdrawn:
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.withdrawn",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={"reason": "metadata_or_tag"},
                    correlation_id=correlation_id,
                )
            if new_score != old_score:
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.scored",
                    entity_type="lead",
                    entity_id=lead_id,
                    payload={
                        "from": old_score,
                        "to": new_score,
                        "quality": new_meta.get('lead_quality'),
                    },
                    correlation_id=correlation_id,
                )
            
            return {
                'success': True,
                'data': {
                    'lead': self._format_lead(updated_lead_dict),
                    'message': 'Lead updated successfully'
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def add_lead_activity(self, lead_id: int, user_id: int, activity_type: str, 
                          description: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add activity to a lead"""
        try:
            # Verify lead ownership
            lead_data = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )
            
            if not lead_data:
                return {
                    'success': False,
                    'error': 'Lead not found',
                    'error_code': 'LEAD_NOT_FOUND'
                }
            
            # Add activity
            activity_id = self._add_lead_activity(lead_id, activity_type, description, metadata)
            
            # Update lead's last contact if it's a contact activity
            if activity_type in ['email_received', 'email_sent', 'call_made', 'meeting_scheduled']:
                db_optimizer.execute_query(
                    "UPDATE leads SET last_contact = CURRENT_TIMESTAMP WHERE id = ?",
                    (lead_id,),
                    fetch=False
                )

            record_crm_event(
                user_id=user_id,
                event_type="lead.activity_logged",
                entity_type="lead",
                entity_id=lead_id,
                payload={
                    "activity_id": activity_id,
                    "activity_type": activity_type,
                    "description_preview": (description or "")[:500],
                },
            )
            
            return {
                'success': True,
                'data': {
                    'activity_id': activity_id,
                    'message': 'Activity added successfully'
                }
            }
            
        except Exception as e:
            logger.error(f"Error adding lead activity: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_lead_activities(self, lead_id: int, user_id: int, limit: int = 50) -> Dict[str, Any]:
        """Get activities for a specific lead"""
        try:
            # Verify lead ownership
            lead_data = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )
            
            if not lead_data:
                return {
                    'success': False,
                    'error': 'Lead not found',
                    'error_code': 'LEAD_NOT_FOUND'
                }
            
            # Get activities with pagination (rulepack compliance: specific columns + offset)
            activities_data = db_optimizer.execute_query(
                """SELECT id, lead_id, activity_type, description, timestamp, metadata 
                   FROM lead_activities 
                   WHERE lead_id = ? 
                   ORDER BY timestamp DESC 
                   LIMIT ? OFFSET ?""",
                (lead_id, limit, 0)  # TODO: Add offset parameter to method signature
            )
            
            activities = []
            for activity_data in activities_data:
                activities.append(self._format_activity(activity_data))
            
            return {
                'success': True,
                'data': {
                    'activities': activities,
                    'count': len(activities)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting lead activities: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def sync_gmail_leads(self, user_id: int) -> Dict[str, Any]:
        """Sync leads from Gmail emails"""
        try:
            # Check if Gmail is connected - check gmail_tokens table directly
            gmail_connected = False
            try:
                gmail_token_check = db_optimizer.execute_query("""
                    SELECT id, user_id, access_token_enc, refresh_token_enc, is_active
                    FROM gmail_tokens 
                    WHERE user_id = ? AND is_active = TRUE
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id,))
                
                if gmail_token_check and len(gmail_token_check) > 0:
                    gmail_connected = True
            except Exception as check_error:
                logger.warning(f"Error checking gmail_tokens table: {check_error}")
            
            # Fallback: check oauth_tokens table if gmail_oauth_manager is available
            if not gmail_connected and gmail_oauth_manager:
                try:
                    gmail_connected = gmail_oauth_manager.is_gmail_connected(user_id)
                except Exception:
                    pass
            
            if not gmail_connected:
                return {
                    'success': False,
                    'error': 'Gmail not connected',
                    'error_code': 'GMAIL_NOT_CONNECTED'
                }
            
            # Get recent email activities
            activities_data = db_optimizer.execute_query(
                """SELECT DISTINCT la.lead_id, l.email, l.name, l.company
                   FROM lead_activities la
                   JOIN leads l ON la.lead_id = l.id
                   WHERE l.user_id = ? AND la.activity_type = 'email_received'
                   AND datetime(la.timestamp) >= datetime('now', '-7 days')
                   ORDER BY la.timestamp DESC""",
                (user_id,)
            )
            
            synced_leads = []
            for activity in activities_data:
                # Check if this is a new lead or existing
                existing_lead = db_optimizer.execute_query(
                    "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                    (user_id, activity['email'])
                )
                
                if not existing_lead:
                    # Create new lead from email
                    lead_data = {
                        'email': activity['email'],
                        'name': activity['name'] or activity['email'].split('@')[0],
                        'company': activity['company'],
                        'source': 'gmail',
                        'stage': 'new'
                    }
                    
                    result = self.create_lead(user_id, lead_data)
                    if result['success']:
                        synced_leads.append({
                            'email': activity['email'],
                            'action': 'created'
                        })
                else:
                    # Update existing lead activity
                    synced_leads.append({
                        'email': activity['email'],
                        'action': 'updated'
                    })
            
            return {
                'success': True,
                'data': {
                    'synced_leads': synced_leads,
                    'count': len(synced_leads)
                }
            }
            
        except Exception as e:
            logger.error(f"Error syncing Gmail leads: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_lead_pipeline(self, user_id: int) -> Dict[str, Any]:
        """Get lead pipeline with stage distribution"""
        try:
            # Get leads by stage
            pipeline_data = db_optimizer.execute_query(
                f"""SELECT stage, COUNT(*) as count, AVG(score) as avg_score
                   FROM leads
                   WHERE user_id = ? AND {_ACTIVE_LEADS_SQL}
                   GROUP BY stage
                   ORDER BY 
                     CASE stage
                       WHEN 'new' THEN 1
                       WHEN 'contacted' THEN 2
                       WHEN 'replied' THEN 3
                       WHEN 'qualified' THEN 4
                       WHEN 'closed' THEN 5
                     END""",
                (user_id,)
            )
            
            # Get conversion rates
            total_leads = db_optimizer.execute_query(
                f"SELECT COUNT(*) as count FROM leads WHERE user_id = ? AND {_ACTIVE_LEADS_SQL}",
                (user_id,)
            )[0]['count']
            
            closed_leads = db_optimizer.execute_query(
                f"SELECT COUNT(*) as count FROM leads WHERE user_id = ? AND stage = 'closed' AND {_ACTIVE_LEADS_SQL}",
                (user_id,)
            )[0]['count']
            
            conversion_rate = (closed_leads / total_leads * 100) if total_leads > 0 else 0
            
            return {
                'success': True,
                'data': {
                    'pipeline': [dict(stage) for stage in pipeline_data],
                    'total_leads': total_leads,
                    'closed_leads': closed_leads,
                    'conversion_rate': round(conversion_rate, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting lead pipeline: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _format_lead(self, lead_data: Dict[str, Any]) -> Lead:
        """Format lead data into Lead object"""
        return Lead(
            id=lead_data['id'],
            user_id=lead_data['user_id'],
            email=lead_data['email'],
            name=lead_data['name'],
            phone=lead_data.get('phone'),
            company=lead_data.get('company'),
            source=lead_data['source'],
            stage=lead_data['stage'],
            score=lead_data['score'],
            created_at=datetime.fromisoformat(lead_data['created_at']),
            updated_at=datetime.fromisoformat(lead_data['updated_at']),
            last_contact=datetime.fromisoformat(lead_data['last_contact']) if lead_data.get('last_contact') else None,
            notes=lead_data.get('notes'),
            tags=_crm_tags_list(lead_data.get('tags')),
            metadata=_crm_meta_dict(lead_data.get('metadata')),
        )
    
    def _format_activity(self, activity_data: Dict[str, Any]) -> LeadActivity:
        """Format activity data into LeadActivity object"""
        return LeadActivity(
            id=activity_data['id'],
            lead_id=activity_data['lead_id'],
            activity_type=activity_data['activity_type'],
            description=activity_data['description'],
            timestamp=datetime.fromisoformat(activity_data['timestamp']),
            metadata=_crm_meta_dict(activity_data.get('metadata')),
        )
    
    def _add_lead_activity(self, lead_id: int, activity_type: str, 
                           description: str, metadata: Dict[str, Any] = None) -> int:
        """Add activity to lead (internal method). Returns new activity row id."""
        rid = db_optimizer.execute_insert_returning_id(
            """INSERT INTO lead_activities (lead_id, activity_type, description, metadata) 
               VALUES (?, ?, ?, ?)""",
            (lead_id, activity_type, description, json.dumps(metadata or {})),
        )
        return int(rid or 0)
    
    def _score_lead_data(self, lead_data: Dict[str, Any], activity_count: int, last_activity: Optional[datetime]) -> Dict[str, Any]:
        """Score via LeadScoringService (weighted source/recency/stage/engagement/attributes). See docs/CRM_LEAD_SCORING.md."""
        service = get_lead_scoring_service()
        result = service.score_lead(lead_data, activity_count=activity_count, last_activity=last_activity)
        return {'score': result.score, 'quality': result.quality, 'breakdown': result.breakdown}

    def _get_lead_activity_metrics(self, lead_id: int) -> tuple:
        try:
            result = db_optimizer.execute_query(
                "SELECT COUNT(*) as count, MAX(timestamp) as last_activity FROM lead_activities WHERE lead_id = ?",
                (lead_id,)
            )
            if result:
                row = result[0]
                last = row.get('last_activity')
                last_dt = datetime.fromisoformat(last) if last else None
                return int(row.get('count', 0) or 0), last_dt
        except Exception as e:
            logger.warning(f"Failed to compute lead activity metrics: {e}")
        return 0, None

    def recalculate_lead_score(self, lead_id: int, user_id: int) -> Dict[str, Any]:
        lead_data = db_optimizer.execute_query(
            "SELECT id, user_id, email, name, phone, company, source, stage, score, created_at, updated_at, last_contact, notes, tags, metadata FROM leads WHERE id = ? AND user_id = ?",
            (lead_id, user_id)
        )
        if not lead_data:
            return {'success': False, 'error': 'Lead not found', 'error_code': 'LEAD_NOT_FOUND'}
        lead = dict(lead_data[0])
        old_score = int(lead.get('score') or 0)
        activity_count, last_activity = self._get_lead_activity_metrics(lead_id)
        score_result = self._score_lead_data(lead, activity_count, last_activity)
        metadata = dict(_crm_meta_dict(lead.get('metadata')))
        metadata['lead_quality'] = score_result['quality']
        metadata['score_breakdown'] = score_result['breakdown']
        db_optimizer.execute_query(
            "UPDATE leads SET score = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (score_result['score'], json.dumps(metadata), lead_id, user_id),
            fetch=False
        )
        lead['score'] = score_result['score']
        lead['metadata'] = json.dumps(metadata)
        new_score = int(score_result['score'])
        if new_score != old_score:
            correlation_id = str(uuid4())
            record_crm_event(
                user_id=user_id,
                event_type="lead.scored",
                entity_type="lead",
                entity_id=lead_id,
                payload={
                    "from": old_score,
                    "to": new_score,
                    "quality": score_result.get('quality'),
                    "source": "recalculate_lead_score",
                },
                correlation_id=correlation_id,
            )
        return {'success': True, 'data': {'lead': self._format_lead(lead)}}

    def import_leads(
        self,
        user_id: int,
        leads: List[Dict[str, Any]],
        on_duplicate: str = 'update',
    ) -> Dict[str, Any]:
        """Import leads. on_duplicate: 'skip' | 'update' | 'merge'.
        skip: do not update existing, count as skipped; update: overwrite; merge: update only non-empty fields."""
        created = 0
        updated = 0
        skipped_duplicate = 0
        errors = []
        allowed_dup = ('skip', 'update', 'merge')
        if on_duplicate not in allowed_dup:
            on_duplicate = 'update'
        for item in leads:
            email = item.get('email')
            name = item.get('name')
            if not email or not name:
                errors.append({'lead': item, 'error': 'Missing required field: email/name'})
                continue
            existing = db_optimizer.execute_query(
                "SELECT id, withdrawn_at FROM leads WHERE user_id = ? AND email = ?",
                (user_id, email)
            )
            if existing:
                lead_id = existing[0]["id"]
                if on_duplicate == 'skip':
                    skipped_duplicate += 1
                    continue
                if existing[0].get("withdrawn_at"):
                    db_optimizer.execute_query(
                        "UPDATE leads SET withdrawn_at = NULL, updated_at = CURRENT_TIMESTAMP "
                        "WHERE id = ? AND user_id = ?",
                        (lead_id, user_id),
                        fetch=False,
                    )
                if on_duplicate == 'merge':
                    updates = {k: v for k, v in item.items() if k != 'email' and v is not None and v != ''}
                    if not updates:
                        skipped_duplicate += 1
                        continue
                    self.update_lead(lead_id, user_id, updates)
                else:
                    self.update_lead(lead_id, user_id, item)
                updated += 1
            else:
                self.create_lead(user_id, item)
                created += 1
        return {
            'success': True,
            'data': {
                'created': created,
                'updated': updated,
                'skipped_duplicate': skipped_duplicate,
                'errors': errors,
                'total': len(leads)
            }
        }
    
    def _get_cutoff_date(self, time_period: str) -> datetime:
        """Get cutoff date for time period filter"""
        now = datetime.now()
        
        if time_period == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'yesterday':
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'this_week':
            return now - timedelta(days=now.weekday())
        elif time_period == 'last_week':
            return now - timedelta(days=now.weekday() + 7)
        elif time_period == 'this_month':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'last_month':
            last_month = now.replace(day=1) - timedelta(days=1)
            return last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return now - timedelta(days=30)  # Default to 30 days
    
    def delete_contact(
        self,
        contact_id: int,
        user_id: int,
        soft_delete: bool = False,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Withdraw a lead from active CRM (HTTP DELETE maps here): closed stage, withdrawn_at set,
        append-only crm_events; lead row and lead_activities are preserved.
        soft_delete is ignored (withdraw-only); correlation_id should be supplied for cancel flows.
        """
        _ = soft_delete
        try:
            lead_data = db_optimizer.execute_query(
                "SELECT id, user_id, email, name, stage, withdrawn_at FROM leads WHERE id = ? AND user_id = ?",
                (contact_id, user_id),
            )
            if not lead_data:
                return {
                    "success": False,
                    "error": "Contact not found or access denied",
                    "error_code": "CONTACT_NOT_FOUND",
                }
            lead = lead_data[0]
            lead_email = lead.get("email", "") or ""
            lead_name = lead.get("name", "") or ""
            correlation_id = correlation_id or str(uuid4())
            if lead.get("withdrawn_at"):
                record_crm_event(
                    user_id=user_id,
                    event_type="lead.withdrawn",
                    entity_type="lead",
                    entity_id=contact_id,
                    payload={"email": lead_email, "idempotent_repeat": True},
                    correlation_id=correlation_id,
                    status="noop",
                    source="crm.delete_contact",
                )
                return {
                    "success": True,
                    "data": {
                        "contact_id": contact_id,
                        "message": "Contact already withdrawn",
                    },
                }
            prior_stage = lead.get("stage") or "new"
            wtime = datetime.now(timezone.utc).isoformat()
            db_optimizer.execute_query(
                """UPDATE leads SET stage = 'closed', withdrawn_at = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?""",
                (wtime, contact_id, user_id),
                fetch=False,
            )
            self._add_lead_activity(
                contact_id,
                "note_added",
                "Lead withdrawn from active CRM; row and history retained",
            )
            record_crm_event(
                user_id=user_id,
                event_type="lead.withdrawn",
                entity_type="lead",
                entity_id=contact_id,
                payload={
                    "email": lead_email,
                    "name": lead_name,
                    "prior_stage": prior_stage,
                },
                correlation_id=correlation_id,
                status="applied",
                source="crm.delete_contact",
            )
            record_crm_event(
                user_id=user_id,
                event_type="contact.withdrawn",
                entity_type="contact",
                entity_id=contact_id,
                payload={"email": lead_email, "prior_stage": prior_stage},
                correlation_id=correlation_id,
                status="applied",
                source="crm.delete_contact",
            )
            logger.info(
                "Withdrew contact %s for user %s",
                contact_id,
                user_id,
                extra={
                    "event": "contact_withdrawn",
                    "service": "crm",
                    "severity": "INFO",
                    "contact_id": contact_id,
                    "user_id": user_id,
                },
            )
            return {
                "success": True,
                "data": {
                    "contact_id": contact_id,
                    "message": "Contact withdrawn successfully",
                },
            }
        except Exception as e:
            logger.error(
                "Error withdrawing contact: %s",
                e,
                extra={
                    "event": "contact_withdraw_failed",
                    "service": "crm",
                    "severity": "ERROR",
                    "contact_id": contact_id,
                    "user_id": user_id,
                },
            )
            return {
                "success": False,
                "error": str(e),
                "error_code": "DELETE_ERROR",
            }
    
    def _get_leads_analytics(self, user_id: int, leads: List[Lead]) -> Dict[str, Any]:
        """Get analytics for leads"""
        if not leads:
            return {
                'total_leads': 0,
                'leads_by_stage': {},
                'leads_by_source': {},
                'avg_score': 0,
                'recent_leads': 0
            }
        
        # Calculate analytics
        leads_by_stage = {}
        leads_by_source = {}
        total_score = 0
        recent_leads = 0
        
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for lead in leads:
            # By stage
            leads_by_stage[lead.stage] = leads_by_stage.get(lead.stage, 0) + 1
            
            # By source
            leads_by_source[lead.source] = leads_by_source.get(lead.source, 0) + 1
            
            # Total score
            total_score += lead.score
            
            # Recent leads
            if lead.created_at >= cutoff_date:
                recent_leads += 1
        
        return {
            'total_leads': len(leads),
            'leads_by_stage': leads_by_stage,
            'leads_by_source': leads_by_source,
            'avg_score': round(total_score / len(leads), 1),
            'recent_leads': recent_leads
        }

# Global enhanced CRM service instance
enhanced_crm_service = EnhancedCRMService()

# Export the enhanced CRM service
__all__ = [
    'EnhancedCRMService',
    'enhanced_crm_service',
    'Lead',
    'LeadActivity',
    'lead_row_to_public_dict',
    'lead_dataclass_to_public_dict',
]
