"""
Enhanced CRM Service with Real-time Gmail Sync
Manages leads, contacts, and activities with automatic Gmail integration
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from core.database_optimization import db_optimizer
# Gmail OAuth functionality - disabled pending OAuth refactor
# from core.gmail_oauth import gmail_oauth_manager, gmail_sync_manager
gmail_oauth_manager = None
gmail_sync_manager = None

logger = logging.getLogger(__name__)

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
    
    def get_leads_summary(self, user_id: int, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get comprehensive leads summary with analytics"""
        try:
            # Build base query
            base_query = "SELECT * FROM leads WHERE user_id = ?"
            params = [user_id]
            
            # Apply filters
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
            
            # Get leads
            leads_data = db_optimizer.execute_query(base_query, tuple(params))
            
            # Process leads
            leads = []
            for lead_data in leads_data:
                leads.append(self._format_lead(lead_data))
            
            # Get analytics
            analytics = self._get_leads_analytics(user_id, leads)
            
            return {
                'success': True,
                'data': {
                    'leads': leads,
                    'total_count': len(leads),
                    'analytics': analytics,
                    'filters_applied': filters or {}
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting leads summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def create_lead(self, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lead"""
        try:
            # Validate required fields
            required_fields = ['email', 'name']
            for field in required_fields:
                if not lead_data.get(field):
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'error_code': 'MISSING_FIELD'
                    }
            
            # Check if lead already exists
            existing = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                (user_id, lead_data['email'])
            )
            
            if existing:
                return {
                    'success': False,
                    'error': 'Lead with this email already exists',
                    'error_code': 'LEAD_EXISTS'
                }
            
            # Calculate lead score
            score = self._calculate_lead_score(lead_data)
            
            # Create lead
            lead_id = db_optimizer.execute_query(
                """INSERT INTO leads 
                   (user_id, email, name, phone, company, source, stage, score, notes, tags, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, lead_data['email'], lead_data['name'],
                 lead_data.get('phone'), lead_data.get('company'),
                 lead_data.get('source', 'manual'), lead_data.get('stage', 'new'),
                 score, lead_data.get('notes'), json.dumps(lead_data.get('tags', [])),
                 json.dumps(lead_data.get('metadata', {}))),
                fetch=False
            )
            
            # Add creation activity
            self._add_lead_activity(lead_id, 'note_added', f"Lead created manually")
            
            logger.info(f"Lead created: {lead_data['email']} for user {user_id}")
            
            return {
                'success': True,
                'data': {
                    'lead_id': lead_id,
                    'message': 'Lead created successfully'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def update_lead(self, lead_id: int, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update lead information"""
        try:
            # Verify lead ownership
            lead_data = db_optimizer.execute_query(
                "SELECT * FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )
            
            if not lead_data:
                return {
                    'success': False,
                    'error': 'Lead not found',
                    'error_code': 'LEAD_NOT_FOUND'
                }
            
            # Build update query
            update_fields = []
            update_values = []
            
            allowed_fields = ['name', 'phone', 'company', 'stage', 'notes', 'tags', 'metadata']
            
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
            
            query = f"UPDATE leads SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?"
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Add update activity
            self._add_lead_activity(lead_id, 'note_added', f"Lead updated: {', '.join(updates.keys())}")
            
            # Get updated lead
            updated_lead = db_optimizer.execute_query(
                "SELECT * FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id)
            )[0]
            
            return {
                'success': True,
                'data': {
                    'lead': self._format_lead(updated_lead),
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
            
            # Get activities
            activities_data = db_optimizer.execute_query(
                """SELECT * FROM lead_activities 
                   WHERE lead_id = ? 
                   ORDER BY timestamp DESC 
                   LIMIT ?""",
                (lead_id, limit)
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
            # Check if Gmail is connected
            if not gmail_oauth_manager.is_gmail_connected(user_id):
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
                   AND la.timestamp >= datetime('now', '-7 days')
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
                """SELECT stage, COUNT(*) as count, AVG(score) as avg_score
                   FROM leads
                   WHERE user_id = ?
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
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            closed_leads = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ? AND stage = 'closed'",
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
            tags=json.loads(lead_data.get('tags', '[]')),
            metadata=json.loads(lead_data.get('metadata', '{}'))
        )
    
    def _format_activity(self, activity_data: Dict[str, Any]) -> LeadActivity:
        """Format activity data into LeadActivity object"""
        return LeadActivity(
            id=activity_data['id'],
            lead_id=activity_data['lead_id'],
            activity_type=activity_data['activity_type'],
            description=activity_data['description'],
            timestamp=datetime.fromisoformat(activity_data['timestamp']),
            metadata=json.loads(activity_data.get('metadata', '{}'))
        )
    
    def _add_lead_activity(self, lead_id: int, activity_type: str, 
                           description: str, metadata: Dict[str, Any] = None) -> int:
        """Add activity to lead (internal method)"""
        return db_optimizer.execute_query(
            """INSERT INTO lead_activities (lead_id, activity_type, description, metadata) 
               VALUES (?, ?, ?, ?)""",
            (lead_id, activity_type, description, json.dumps(metadata or {})),
            fetch=False
        )
    
    def _calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
        """Calculate lead score based on available data"""
        score = 0
        
        # Base score
        score += 10
        
        # Company information
        if lead_data.get('company'):
            score += 20
        
        # Phone number
        if lead_data.get('phone'):
            score += 15
        
        # Source scoring
        source_scores = {
            'gmail': 25,
            'website': 20,
            'referral': 30,
            'manual': 10
        }
        score += source_scores.get(lead_data.get('source', 'manual'), 10)
        
        # Email domain scoring (basic)
        email = lead_data.get('email', '')
        if '@' in email:
            domain = email.split('@')[1].lower()
            if any(corp in domain for corp in ['corp', 'inc', 'llc', 'ltd']):
                score += 10
        
        return min(score, 100)  # Cap at 100
    
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
__all__ = ['EnhancedCRMService', 'enhanced_crm_service', 'Lead', 'LeadActivity']
