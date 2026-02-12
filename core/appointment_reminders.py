#!/usr/bin/env python3
"""
Appointment Reminders
Simple poller job for email reminders (24h and 2h before appointment)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Constants (replace magic numbers)
REMINDER_24H_WINDOW_START_HOURS = 24
REMINDER_24H_WINDOW_END_HOURS = 25
REMINDER_2H_WINDOW_START_HOURS = 2
REMINDER_2H_WINDOW_END_HOURS = 3

# Email sending (simple implementation - can be replaced with proper email service)
def send_appointment_reminder_email(user_email: str, appointment: Dict, hours_before: int):
    """Send appointment reminder email"""
    # TODO: Integrate with email service
    logger.info(f"📧 Would send {hours_before}h reminder email to {user_email} for appointment {appointment['id']}")
    # For now, just log - replace with actual email sending
    return True


def run_reminder_job():
    """Run reminder job - checks appointments and sends reminders"""
    try:
        # Use UTC consistently for timezone-aware datetime
        now = datetime.now(timezone.utc)
        
        # 24-hour window: appointments starting between 24h and 25h from now
        window_24h_start = now + timedelta(hours=REMINDER_24H_WINDOW_START_HOURS)
        window_24h_end = now + timedelta(hours=REMINDER_24H_WINDOW_END_HOURS)
        
        # 2-hour window: appointments starting between 2h and 3h from now
        window_2h_start = now + timedelta(hours=REMINDER_2H_WINDOW_START_HOURS)
        window_2h_end = now + timedelta(hours=REMINDER_2H_WINDOW_END_HOURS)
        
        # Get appointments needing 24h reminder
        appointments_24h = db_optimizer.execute_query("""
            SELECT a.*, u.email as user_email
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.start_time >= ? AND a.start_time < ?
            AND a.status IN ('scheduled', 'confirmed')
            AND a.reminder_24h_sent = 0
        """, (window_24h_start.isoformat(), window_24h_end.isoformat()))
        
        # Get appointments needing 2h reminder
        appointments_2h = db_optimizer.execute_query("""
            SELECT a.*, u.email as user_email
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.start_time >= ? AND a.start_time < ?
            AND a.status IN ('scheduled', 'confirmed')
            AND a.reminder_2h_sent = 0
        """, (window_2h_start.isoformat(), window_2h_end.isoformat()))
        
        sent_count = 0
        
        # Send 24h reminders
        for apt in appointments_24h:
            try:
                # Send email
                send_appointment_reminder_email(apt['user_email'], apt, REMINDER_24H_WINDOW_START_HOURS)
                
                # Mark as sent
                db_optimizer.execute_query("""
                    UPDATE appointments 
                    SET reminder_24h_sent = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (apt['id'],), fetch=False)
                
                sent_count += 1
                logger.info(f"✅ Sent 24h reminder for appointment {apt['id']}")
            except Exception as e:
                logger.error(f"❌ Failed to send 24h reminder for appointment {apt['id']}: {e}")
        
        # Send 2h reminders
        for apt in appointments_2h:
            try:
                # Send email
                send_appointment_reminder_email(apt['user_email'], apt, REMINDER_2H_WINDOW_START_HOURS)
                
                # Mark as sent
                db_optimizer.execute_query("""
                    UPDATE appointments 
                    SET reminder_2h_sent = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (apt['id'],), fetch=False)
                
                sent_count += 1
                logger.info(f"✅ Sent 2h reminder for appointment {apt['id']}")
            except Exception as e:
                logger.error(f"❌ Failed to send 2h reminder for appointment {apt['id']}: {e}")
        
        if sent_count > 0:
            logger.info(f"✅ Reminder job completed: {sent_count} reminders sent")
        else:
            logger.debug("ℹ️ Reminder job: no reminders needed")
        
        return {'success': True, 'reminders_sent': sent_count}
        
    except Exception as e:
        logger.error(f"❌ Reminder job failed: {e}")
        return {'success': False, 'error': str(e)}
