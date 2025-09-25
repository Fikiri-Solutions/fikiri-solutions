"""
Email Scheduling System for Fikiri Solutions
Advanced email scheduling with timezone support and automation
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pytz
from core.minimal_config import get_config
from core.redis_queues import get_redis_queue

logger = logging.getLogger(__name__)

@dataclass
class ScheduledEmail:
    """Scheduled email data structure"""
    id: str
    user_id: int
    recipient_email: str
    subject: str
    body: str
    scheduled_time: datetime
    timezone: str
    status: str  # pending, sent, failed, cancelled
    priority: str  # low, medium, high, urgent
    retry_count: int
    created_at: datetime
    metadata: Dict[str, Any]

class EmailSchedulingSystem:
    """Advanced email scheduling with timezone and automation support"""
    
    def __init__(self):
        self.redis_queue = get_redis_queue()
        self.scheduled_emails = {}
        self.timezone_cache = {}
        
        # Business hours configuration
        self.business_hours = {
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
            "saturday": {"start": "10:00", "end": "15:00"},
            "sunday": {"start": "closed", "end": "closed"}
        }
        
        # Optimal sending times by industry
        self.optimal_times = {
            "landscaping": {
                "best_days": ["tuesday", "wednesday", "thursday"],
                "best_hours": ["09:00", "10:00", "14:00", "15:00"],
                "avoid_days": ["monday", "friday"],
                "avoid_hours": ["12:00", "13:00"]
            },
            "real_estate": {
                "best_days": ["tuesday", "wednesday", "thursday"],
                "best_hours": ["10:00", "11:00", "15:00", "16:00"],
                "avoid_days": ["monday", "friday"],
                "avoid_hours": ["12:00", "13:00"]
            },
            "healthcare": {
                "best_days": ["tuesday", "wednesday", "thursday"],
                "best_hours": ["09:00", "10:00", "14:00", "15:00"],
                "avoid_days": ["monday", "friday"],
                "avoid_hours": ["12:00", "13:00"]
            },
            "general": {
                "best_days": ["tuesday", "wednesday", "thursday"],
                "best_hours": ["10:00", "11:00", "14:00", "15:00"],
                "avoid_days": ["monday", "friday"],
                "avoid_hours": ["12:00", "13:00"]
            }
        }
    
    def schedule_email(self, user_id: int, recipient_email: str, subject: str, body: str,
                      scheduled_time: datetime, timezone: str = "UTC", 
                      priority: str = "medium", industry: str = "general",
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Schedule an email for future sending"""
        try:
            # Generate unique ID
            email_id = f"scheduled_{int(datetime.now().timestamp())}_{user_id}"
            
            # Validate scheduled time
            if scheduled_time <= datetime.now():
                return {"success": False, "error": "Scheduled time must be in the future"}
            
            # Convert to timezone
            if timezone != "UTC":
                try:
                    tz = pytz.timezone(timezone)
                    scheduled_time = tz.localize(scheduled_time)
                except Exception as e:
                    logger.warning(f"⚠️ Invalid timezone {timezone}, using UTC: {e}")
                    timezone = "UTC"
            
            # Create scheduled email
            scheduled_email = ScheduledEmail(
                id=email_id,
                user_id=user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                scheduled_time=scheduled_time,
                timezone=timezone,
                status="pending",
                priority=priority,
                retry_count=0,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # Store in memory and Redis
            self.scheduled_emails[email_id] = scheduled_email
            self._store_in_redis(scheduled_email)
            
            # Add to processing queue
            self._add_to_queue(scheduled_email)
            
            logger.info(f"✅ Email scheduled: {email_id} for {scheduled_time}")
            
            return {
                "success": True,
                "email_id": email_id,
                "scheduled_time": scheduled_time.isoformat(),
                "timezone": timezone,
                "status": "pending"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule email: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_optimal_time(self, user_id: int, recipient_email: str, subject: str, body: str,
                            timezone: str = "UTC", industry: str = "general",
                            preferred_days: List[str] = None, 
                            preferred_hours: List[str] = None) -> Dict[str, Any]:
        """Schedule email at optimal time based on industry and preferences"""
        try:
            # Get optimal times for industry
            optimal_config = self.optimal_times.get(industry, self.optimal_times["general"])
            
            # Use preferences or defaults
            best_days = preferred_days or optimal_config["best_days"]
            best_hours = preferred_hours or optimal_config["best_hours"]
            
            # Find next optimal time
            optimal_time = self._find_next_optimal_time(best_days, best_hours, timezone)
            
            if not optimal_time:
                return {"success": False, "error": "No optimal time found"}
            
            # Schedule the email
            return self.schedule_email(
                user_id=user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                scheduled_time=optimal_time,
                timezone=timezone,
                industry=industry,
                metadata={"scheduled_by": "optimal_time", "industry": industry}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule optimal time: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_business_hours(self, user_id: int, recipient_email: str, subject: str, body: str,
                               timezone: str = "UTC", delay_hours: int = 0) -> Dict[str, Any]:
        """Schedule email during business hours"""
        try:
            # Calculate business hours time
            business_time = self._find_next_business_hours(timezone, delay_hours)
            
            if not business_time:
                return {"success": False, "error": "No business hours time found"}
            
            # Schedule the email
            return self.schedule_email(
                user_id=user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                scheduled_time=business_time,
                timezone=timezone,
                metadata={"scheduled_by": "business_hours", "delay_hours": delay_hours}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule business hours: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_follow_up(self, user_id: int, recipient_email: str, subject: str, body: str,
                          follow_up_days: int, timezone: str = "UTC",
                          industry: str = "general") -> Dict[str, Any]:
        """Schedule follow-up email after specified days"""
        try:
            # Calculate follow-up time
            follow_up_time = datetime.now() + timedelta(days=follow_up_days)
            
            # Adjust to optimal time if possible
            optimal_config = self.optimal_times.get(industry, self.optimal_times["general"])
            follow_up_time = self._adjust_to_optimal_time(follow_up_time, optimal_config, timezone)
            
            # Schedule the email
            return self.schedule_email(
                user_id=user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                scheduled_time=follow_up_time,
                timezone=timezone,
                metadata={"scheduled_by": "follow_up", "follow_up_days": follow_up_days, "industry": industry}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule follow-up: {e}")
            return {"success": False, "error": str(e)}
    
    def _find_next_optimal_time(self, best_days: List[str], best_hours: List[str], timezone: str) -> Optional[datetime]:
        """Find next optimal time based on preferences"""
        try:
            tz = pytz.timezone(timezone) if timezone != "UTC" else pytz.UTC
            now = datetime.now(tz)
            
            # Check next 7 days
            for day_offset in range(7):
                check_date = now + timedelta(days=day_offset)
                day_name = check_date.strftime("%A").lower()
                
                if day_name in best_days:
                    # Check each preferred hour
                    for hour_str in best_hours:
                        hour, minute = map(int, hour_str.split(":"))
                        optimal_time = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        if optimal_time > now:
                            return optimal_time
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find optimal time: {e}")
            return None
    
    def _find_next_business_hours(self, timezone: str, delay_hours: int = 0) -> Optional[datetime]:
        """Find next business hours time"""
        try:
            tz = pytz.timezone(timezone) if timezone != "UTC" else pytz.UTC
            now = datetime.now(tz)
            
            # Add delay
            if delay_hours > 0:
                now += timedelta(hours=delay_hours)
            
            # Check next 7 days
            for day_offset in range(7):
                check_date = now + timedelta(days=day_offset)
                day_name = check_date.strftime("%A").lower()
                
                if day_name in self.business_hours:
                    hours_config = self.business_hours[day_name]
                    
                    if hours_config["start"] == "closed":
                        continue
                    
                    start_hour, start_minute = map(int, hours_config["start"].split(":"))
                    end_hour, end_minute = map(int, hours_config["end"].split(":"))
                    
                    # Check if we're within business hours today
                    if day_offset == 0:
                        current_hour = now.hour
                        if start_hour <= current_hour < end_hour:
                            return now
                    
                    # Use start of business hours
                    business_time = check_date.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                    
                    if business_time > now:
                        return business_time
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find business hours: {e}")
            return None
    
    def _adjust_to_optimal_time(self, base_time: datetime, optimal_config: Dict[str, Any], timezone: str) -> datetime:
        """Adjust time to optimal sending time"""
        try:
            tz = pytz.timezone(timezone) if timezone != "UTC" else pytz.UTC
            base_time = base_time.replace(tzinfo=tz)
            
            day_name = base_time.strftime("%A").lower()
            
            # If it's an optimal day, adjust to optimal hour
            if day_name in optimal_config["best_days"]:
                best_hours = optimal_config["best_hours"]
                for hour_str in best_hours:
                    hour, minute = map(int, hour_str.split(":"))
                    optimal_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if optimal_time > base_time:
                        return optimal_time
            
            return base_time
            
        except Exception as e:
            logger.error(f"❌ Failed to adjust to optimal time: {e}")
            return base_time
    
    def get_scheduled_emails(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get scheduled emails for user"""
        try:
            emails = []
            
            for email_id, email in self.scheduled_emails.items():
                if email.user_id == user_id:
                    if status is None or email.status == status:
                        emails.append({
                            "id": email.id,
                            "recipient_email": email.recipient_email,
                            "subject": email.subject,
                            "scheduled_time": email.scheduled_time.isoformat(),
                            "timezone": email.timezone,
                            "status": email.status,
                            "priority": email.priority,
                            "created_at": email.created_at.isoformat(),
                            "metadata": email.metadata
                        })
            
            # Sort by scheduled time
            emails.sort(key=lambda x: x["scheduled_time"])
            
            return emails
            
        except Exception as e:
            logger.error(f"❌ Failed to get scheduled emails: {e}")
            return []
    
    def cancel_scheduled_email(self, email_id: str, user_id: int) -> Dict[str, Any]:
        """Cancel a scheduled email"""
        try:
            if email_id not in self.scheduled_emails:
                return {"success": False, "error": "Email not found"}
            
            email = self.scheduled_emails[email_id]
            
            if email.user_id != user_id:
                return {"success": False, "error": "Unauthorized"}
            
            if email.status != "pending":
                return {"success": False, "error": "Email cannot be cancelled"}
            
            # Update status
            email.status = "cancelled"
            self._store_in_redis(email)
            
            logger.info(f"✅ Email cancelled: {email_id}")
            
            return {"success": True, "email_id": email_id, "status": "cancelled"}
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel email: {e}")
            return {"success": False, "error": str(e)}
    
    def reschedule_email(self, email_id: str, user_id: int, new_time: datetime) -> Dict[str, Any]:
        """Reschedule an email"""
        try:
            if email_id not in self.scheduled_emails:
                return {"success": False, "error": "Email not found"}
            
            email = self.scheduled_emails[email_id]
            
            if email.user_id != user_id:
                return {"success": False, "error": "Unauthorized"}
            
            if email.status != "pending":
                return {"success": False, "error": "Email cannot be rescheduled"}
            
            if new_time <= datetime.now():
                return {"success": False, "error": "New time must be in the future"}
            
            # Update scheduled time
            email.scheduled_time = new_time
            email.metadata["rescheduled_at"] = datetime.now().isoformat()
            self._store_in_redis(email)
            
            logger.info(f"✅ Email rescheduled: {email_id} to {new_time}")
            
            return {"success": True, "email_id": email_id, "new_time": new_time.isoformat()}
            
        except Exception as e:
            logger.error(f"❌ Failed to reschedule email: {e}")
            return {"success": False, "error": str(e)}
    
    def _store_in_redis(self, email: ScheduledEmail):
        """Store scheduled email in Redis"""
        try:
            if self.redis_queue and self.redis_queue.is_connected():
                key = f"scheduled_email:{email.id}"
                data = {
                    "id": email.id,
                    "user_id": email.user_id,
                    "recipient_email": email.recipient_email,
                    "subject": email.subject,
                    "body": email.body,
                    "scheduled_time": email.scheduled_time.isoformat(),
                    "timezone": email.timezone,
                    "status": email.status,
                    "priority": email.priority,
                    "retry_count": email.retry_count,
                    "created_at": email.created_at.isoformat(),
                    "metadata": json.dumps(email.metadata)
                }
                self.redis_queue.set(key, json.dumps(data), expire=86400 * 30)  # 30 days
        except Exception as e:
            logger.error(f"❌ Failed to store in Redis: {e}")
    
    def _add_to_queue(self, email: ScheduledEmail):
        """Add email to processing queue"""
        try:
            if self.redis_queue and self.redis_queue.is_connected():
                queue_data = {
                    "email_id": email.id,
                    "scheduled_time": email.scheduled_time.isoformat(),
                    "priority": email.priority
                }
                self.redis_queue.lpush("email_schedule_queue", json.dumps(queue_data))
        except Exception as e:
            logger.error(f"❌ Failed to add to queue: {e}")
    
    def get_scheduling_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get scheduling statistics for user"""
        try:
            user_emails = [email for email in self.scheduled_emails.values() if email.user_id == user_id]
            
            if not user_emails:
                return {"total_scheduled": 0}
            
            # Calculate statistics
            total_scheduled = len(user_emails)
            pending_count = len([e for e in user_emails if e.status == "pending"])
            sent_count = len([e for e in user_emails if e.status == "sent"])
            failed_count = len([e for e in user_emails if e.status == "failed"])
            cancelled_count = len([e for e in user_emails if e.status == "cancelled"])
            
            # Priority distribution
            priority_counts = {}
            for email in user_emails:
                priority = email.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Timezone distribution
            timezone_counts = {}
            for email in user_emails:
                tz = email.timezone
                timezone_counts[tz] = timezone_counts.get(tz, 0) + 1
            
            return {
                "total_scheduled": total_scheduled,
                "pending": pending_count,
                "sent": sent_count,
                "failed": failed_count,
                "cancelled": cancelled_count,
                "priority_distribution": priority_counts,
                "timezone_distribution": timezone_counts,
                "success_rate": (sent_count / total_scheduled) * 100 if total_scheduled > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get scheduling statistics: {e}")
            return {"error": "Statistics generation failed"}

# Global instance
email_scheduler = None

def get_email_scheduler() -> Optional[EmailSchedulingSystem]:
    """Get the global email scheduler instance"""
    global email_scheduler
    
    if email_scheduler is None:
        email_scheduler = EmailSchedulingSystem()
    
    return email_scheduler
