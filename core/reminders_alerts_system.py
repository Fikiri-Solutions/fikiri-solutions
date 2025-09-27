"""
Reminders and Alerts System for Fikiri Solutions
Handles automated reminders using Redis TTL and notification service
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

try:
    from core.database_optimization import db_optimizer
    DB_OPTIMIZER_AVAILABLE = True
except ImportError:
    DB_OPTIMIZER_AVAILABLE = False
    db_optimizer = None

logger = logging.getLogger(__name__)

@dataclass
class Reminder:
    """Reminder data structure"""
    id: str
    user_id: int
    lead_id: Optional[str]
    reminder_type: str  # follow_up, task, deadline, meeting
    title: str
    description: str
    due_date: datetime
    priority: str  # low, medium, high, urgent
    is_active: bool
    created_at: datetime

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    user_id: int
    alert_type: str  # lead_score, stage_change, deadline, system
    title: str
    message: str
    priority: str
    is_read: bool
    created_at: datetime

class RemindersAlertsSystem:
    """Reminders and alerts system with Redis TTL"""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
        
        # Default reminder templates
        self.default_reminders = {
            'follow_up': {
                'title': 'Follow-up Reminder',
                'description': 'Time to follow up with {lead_name}',
                'priority': 'medium'
            },
            'task': {
                'title': 'Task Reminder',
                'description': 'Task due: {task_name}',
                'priority': 'high'
            },
            'deadline': {
                'title': 'Deadline Reminder',
                'description': 'Deadline approaching: {deadline_name}',
                'priority': 'urgent'
            },
            'meeting': {
                'title': 'Meeting Reminder',
                'description': 'Meeting scheduled: {meeting_name}',
                'priority': 'medium'
            }
        }
    
    def _init_redis(self):
        """Initialize Redis client"""
        try:
            config = get_config()
            redis_url = getattr(config, 'redis_url', '')
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis client initialized for reminders")
            else:
                logger.warning("⚠️ Redis URL not configured - using in-memory storage")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {e}")
    
    def create_reminder(self, user_id: int, reminder_type: str, title: str, 
                      description: str, due_date: datetime, priority: str = 'medium',
                      lead_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new reminder"""
        try:
            # Generate reminder ID
            reminder_id = f"reminder_{user_id}_{int(due_date.timestamp())}"
            
            # Create reminder object
            reminder = Reminder(
                id=reminder_id,
                user_id=user_id,
                lead_id=lead_id,
                reminder_type=reminder_type,
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                is_active=True,
                created_at=datetime.now()
            )
            
            # Store in database
            query = """
                INSERT INTO reminders (
                    id, user_id, lead_id, reminder_type, title, description,
                    due_date, priority, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                reminder.id,
                reminder.user_id,
                reminder.lead_id,
                reminder.reminder_type,
                reminder.title,
                reminder.description,
                reminder.due_date.isoformat(),
                reminder.priority,
                reminder.is_active,
                reminder.created_at.isoformat()
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
            # Store in Redis with TTL
            if self.redis_client:
                ttl_seconds = int((due_date - datetime.now()).total_seconds())
                if ttl_seconds > 0:
                    reminder_data = {
                        'id': reminder.id,
                        'user_id': reminder.user_id,
                        'lead_id': reminder.lead_id,
                        'reminder_type': reminder.reminder_type,
                        'title': reminder.title,
                        'description': reminder.description,
                        'priority': reminder.priority
                    }
                    
                    self.redis_client.setex(
                        f"reminder:{reminder.id}",
                        ttl_seconds,
                        json.dumps(reminder_data)
                    )
            
            logger.info(f"✅ Reminder created: {reminder_id}")
            return {"success": True, "reminder_id": reminder_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to create reminder: {e}")
            return {"success": False, "error": str(e)}
    
    def create_alert(self, user_id: int, alert_type: str, title: str, 
                   message: str, priority: str = 'medium') -> Dict[str, Any]:
        """Create a new alert"""
        try:
            # Generate alert ID
            alert_id = f"alert_{user_id}_{int(datetime.now().timestamp())}"
            
            # Store in database
            query = """
                INSERT INTO alerts (
                    id, user_id, alert_type, title, message, priority,
                    is_read, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                alert_id,
                user_id,
                alert_type,
                title,
                message,
                priority,
                False,
                datetime.now().isoformat()
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
            # Store in Redis for real-time notifications
            if self.redis_client:
                alert_data = {
                    'id': alert_id,
                    'user_id': user_id,
                    'alert_type': alert_type,
                    'title': title,
                    'message': message,
                    'priority': priority,
                    'created_at': datetime.now().isoformat()
                }
                
                # Store with 24-hour TTL
                self.redis_client.setex(
                    f"alert:{alert_id}",
                    86400,  # 24 hours
                    json.dumps(alert_data)
                )
                
                # Add to user's alert list
                self.redis_client.lpush(f"user_alerts:{user_id}", alert_id)
                self.redis_client.expire(f"user_alerts:{user_id}", 86400)
            
            logger.info(f"✅ Alert created: {alert_id}")
            return {"success": True, "alert_id": alert_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to create alert: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_alerts(self, user_id: int, limit: int = 50) -> Dict[str, Any]:
        """Get user's alerts"""
        try:
            alerts = []
            
            # Get from Redis first (real-time)
            if self.redis_client:
                alert_ids = self.redis_client.lrange(f"user_alerts:{user_id}", 0, limit - 1)
                for alert_id in alert_ids:
                    alert_data = self.redis_client.get(f"alert:{alert_id}")
                    if alert_data:
                        alerts.append(json.loads(alert_data))
            
            # Fallback to database
            if not alerts:
                query = """
                    SELECT * FROM alerts 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """
                
                db_alerts = db_optimizer.execute_query(query, (user_id, limit))
                for alert_data in db_alerts:
                    alerts.append({
                        'id': alert_data['id'],
                        'user_id': alert_data['user_id'],
                        'alert_type': alert_data['alert_type'],
                        'title': alert_data['title'],
                        'message': alert_data['message'],
                        'priority': alert_data['priority'],
                        'is_read': alert_data['is_read'],
                        'created_at': alert_data['created_at']
                    })
            
            return {"success": True, "alerts": alerts}
            
        except Exception as e:
            logger.error(f"❌ Failed to get user alerts: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_reminders(self, user_id: int, upcoming_days: int = 7) -> Dict[str, Any]:
        """Get user's upcoming reminders"""
        try:
            query = """
                SELECT * FROM reminders 
                WHERE user_id = ? 
                AND is_active = 1
                AND due_date BETWEEN ? AND ?
                ORDER BY due_date ASC
            """
            
            now = datetime.now()
            future_date = now + timedelta(days=upcoming_days)
            
            reminders = db_optimizer.execute_query(query, (
                user_id,
                now.isoformat(),
                future_date.isoformat()
            ))
            
            formatted_reminders = []
            for reminder_data in reminders:
                formatted_reminders.append({
                    'id': reminder_data['id'],
                    'user_id': reminder_data['user_id'],
                    'lead_id': reminder_data['lead_id'],
                    'reminder_type': reminder_data['reminder_type'],
                    'title': reminder_data['title'],
                    'description': reminder_data['description'],
                    'due_date': reminder_data['due_date'],
                    'priority': reminder_data['priority'],
                    'is_active': reminder_data['is_active']
                })
            
            return {"success": True, "reminders": formatted_reminders}
            
        except Exception as e:
            logger.error(f"❌ Failed to get user reminders: {e}")
            return {"success": False, "error": str(e)}
    
    def mark_alert_read(self, alert_id: str) -> Dict[str, Any]:
        """Mark an alert as read"""
        try:
            # Update database
            query = "UPDATE alerts SET is_read = 1 WHERE id = ?"
            db_optimizer.execute_query(query, (alert_id,), fetch=False)
            
            # Remove from Redis
            if self.redis_client:
                self.redis_client.delete(f"alert:{alert_id}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Failed to mark alert as read: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_reminder(self, reminder_id: str) -> Dict[str, Any]:
        """Cancel a reminder"""
        try:
            # Update database
            query = "UPDATE reminders SET is_active = 0 WHERE id = ?"
            db_optimizer.execute_query(query, (reminder_id,), fetch=False)
            
            # Remove from Redis
            if self.redis_client:
                self.redis_client.delete(f"reminder:{reminder_id}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel reminder: {e}")
            return {"success": False, "error": str(e)}
    
    def create_lead_reminders(self, lead_id: str, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create automatic reminders for a lead"""
        try:
            reminders_created = []
            
            # Follow-up reminder (1 day)
            follow_up_date = datetime.now() + timedelta(days=1)
            result = self.create_reminder(
                user_id=user_id,
                reminder_type='follow_up',
                title=f"Follow up with {lead_data.get('name', 'Lead')}",
                description=f"Time to follow up with {lead_data.get('name', 'this lead')} from {lead_data.get('company', 'their company')}",
                due_date=follow_up_date,
                priority='medium',
                lead_id=lead_id
            )
            if result['success']:
                reminders_created.append(result['reminder_id'])
            
            # Check-in reminder (7 days)
            check_in_date = datetime.now() + timedelta(days=7)
            result = self.create_reminder(
                user_id=user_id,
                reminder_type='task',
                title=f"Check in with {lead_data.get('name', 'Lead')}",
                description=f"Check in with {lead_data.get('name', 'this lead')} to see if they need any assistance",
                due_date=check_in_date,
                priority='low',
                lead_id=lead_id
            )
            if result['success']:
                reminders_created.append(result['reminder_id'])
            
            logger.info(f"✅ Created {len(reminders_created)} reminders for lead {lead_id}")
            return {"success": True, "reminders_created": reminders_created}
            
        except Exception as e:
            logger.error(f"❌ Failed to create lead reminders: {e}")
            return {"success": False, "error": str(e)}
    
    def process_expired_reminders(self) -> Dict[str, Any]:
        """Process expired reminders and create alerts"""
        try:
            # Get expired reminders
            query = """
                SELECT * FROM reminders 
                WHERE is_active = 1 
                AND due_date <= ?
            """
            
            expired_reminders = db_optimizer.execute_query(query, (datetime.now().isoformat(),))
            
            processed_count = 0
            
            for reminder_data in expired_reminders:
                try:
                    # Create alert for expired reminder
                    alert_result = self.create_alert(
                        user_id=reminder_data['user_id'],
                        alert_type='reminder_expired',
                        title=f"Reminder: {reminder_data['title']}",
                        message=reminder_data['description'],
                        priority=reminder_data['priority']
                    )
                    
                    if alert_result['success']:
                        # Mark reminder as inactive
                        self.cancel_reminder(reminder_data['id'])
                        processed_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process reminder {reminder_data['id']}: {e}")
            
            logger.info(f"✅ Processed {processed_count} expired reminders")
            return {"success": True, "processed": processed_count}
            
        except Exception as e:
            logger.error(f"❌ Failed to process expired reminders: {e}")
            return {"success": False, "error": str(e)}

# Global instance
reminders_alerts_system = None

def get_reminders_alerts_system() -> Optional[RemindersAlertsSystem]:
    """Get the global reminders and alerts system instance"""
    global reminders_alerts_system
    
    if reminders_alerts_system is None:
        reminders_alerts_system = RemindersAlertsSystem()
    
    return reminders_alerts_system
