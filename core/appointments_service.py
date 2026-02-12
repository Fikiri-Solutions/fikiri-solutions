#!/usr/bin/env python3
"""
Appointments Service
Core appointment scheduling with conflict detection and calendar sync
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from core.database_optimization import db_optimizer
from core.integrations.calendar.calendar_manager import CalendarManager
from core.integrations.integration_framework import integration_manager

logger = logging.getLogger(__name__)

# Status machine: scheduled -> confirmed -> completed
# scheduled/confirmed -> canceled/no_show
VALID_STATUSES = ['scheduled', 'confirmed', 'completed', 'canceled', 'no_show']
STATUS_TRANSITIONS = {
    'scheduled': ['confirmed', 'canceled'],
    'confirmed': ['completed', 'canceled', 'no_show'],
    'completed': [],  # Terminal state
    'canceled': [],  # Terminal state
    'no_show': []  # Terminal state
}

# Constants (replace magic numbers)
DEFAULT_SLOT_DURATION_MINUTES = 30
SUGGESTED_SLOTS_COUNT = 3

# Input validation constants
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_LOCATION_LENGTH = 500
MAX_NOTES_LENGTH = 2000
MAX_CONTACT_NAME_LENGTH = 100
MAX_CONTACT_EMAIL_LENGTH = 255
MAX_CONTACT_PHONE_LENGTH = 20

# Allowed fields for updates (security: prevent SQL injection)
ALLOWED_UPDATE_FIELDS = {
    'title', 'description', 'start_time', 'end_time', 'status',
    'contact_id', 'contact_name', 'contact_email', 'contact_phone',
    'location', 'notes', 'sync_to_calendar'
}


class AppointmentsService:
    """Appointment scheduling service with conflict detection"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def create_appointment(self, title: str, start_time: datetime, end_time: datetime,
                          description: str = None, contact_id: int = None,
                          contact_name: str = None, contact_email: str = None,
                          contact_phone: str = None, location: str = None,
                          notes: str = None, sync_to_calendar: bool = False) -> Dict:
        """Create new appointment with conflict validation and input validation"""
        # Input validation
        if not title or not title.strip():
            raise ValueError("title is required and cannot be empty")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or less")
        
        if description and len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"description must be {MAX_DESCRIPTION_LENGTH} characters or less")
        
        if location and len(location) > MAX_LOCATION_LENGTH:
            raise ValueError(f"location must be {MAX_LOCATION_LENGTH} characters or less")
        
        if notes and len(notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"notes must be {MAX_NOTES_LENGTH} characters or less")
        
        if contact_name and len(contact_name) > MAX_CONTACT_NAME_LENGTH:
            raise ValueError(f"contact_name must be {MAX_CONTACT_NAME_LENGTH} characters or less")
        
        if contact_email:
            if len(contact_email) > MAX_CONTACT_EMAIL_LENGTH:
                raise ValueError(f"contact_email must be {MAX_CONTACT_EMAIL_LENGTH} characters or less")
            if '@' not in contact_email or '.' not in contact_email.split('@')[-1]:
                raise ValueError("contact_email must be a valid email address")
        
        if contact_phone and len(contact_phone) > MAX_CONTACT_PHONE_LENGTH:
            raise ValueError(f"contact_phone must be {MAX_CONTACT_PHONE_LENGTH} characters or less")
        
        # Validate times
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        
        # Use timezone-aware now for comparison
        from datetime import timezone
        now = datetime.now(timezone.utc) if start_time.tzinfo else datetime.now()
        if start_time < now:
            raise ValueError("start_time cannot be in the past")
        
        # Atomic conflict check + insert using a single transaction
        # This prevents race conditions by checking and inserting in one operation
        with db_optimizer.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for conflicts within the same transaction
            conflict_check = cursor.execute("""
                SELECT id FROM appointments 
                WHERE user_id = ? 
                AND status NOT IN ('canceled', 'no_show')
                AND start_time < ? AND end_time > ?
            """, (self.user_id, end_time.isoformat(), start_time.isoformat())).fetchall()
            
            if conflict_check:
                conn.rollback()
                conflict_ids = [row[0] for row in conflict_check]
                raise ValueError(f"Time slot conflicts with existing appointment(s): {conflict_ids}")
            
            # Insert appointment (still in same transaction)
            cursor.execute("""
                INSERT INTO appointments 
                (user_id, title, description, start_time, end_time, status,
                 contact_id, contact_name, contact_email, contact_phone, location, notes, sync_to_calendar)
                VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id, title.strip(), description, start_time.isoformat(), end_time.isoformat(),
                contact_id, contact_name, contact_email, contact_phone, location, notes, 1 if sync_to_calendar else 0
            ))
            
            appointment_id = cursor.lastrowid
            conn.commit()
        
        # Fetch created appointment
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise ValueError(f"Failed to retrieve created appointment {appointment_id}")
        
        # Sync to calendar if requested and integration active
        if sync_to_calendar:
            try:
                self._sync_to_calendar(appointment, 'create')
            except Exception as e:
                logger.warning(f"⚠️ Calendar sync failed for appointment {appointment_id}: {e}")
                # Don't fail appointment creation if calendar sync fails
        
        logger.info(f"✅ Created appointment {appointment_id} for user {self.user_id}")
        return appointment
    
    def get_appointment(self, appointment_id: int) -> Optional[Dict]:
        """Get appointment by ID"""
        result = db_optimizer.execute_query("""
            SELECT * FROM appointments 
            WHERE id = ? AND user_id = ?
        """, (appointment_id, self.user_id))
        
        if not result:
            return None
        
        return self._format_appointment(result[0])
    
    def list_appointments(self, start: datetime = None, end: datetime = None,
                         status: str = None) -> List[Dict]:
        """List appointments with optional filters"""
        query = "SELECT * FROM appointments WHERE user_id = ?"
        params = [self.user_id]
        
        if start:
            query += " AND end_time >= ?"
            params.append(start.isoformat())
        
        if end:
            query += " AND start_time <= ?"
            params.append(end.isoformat())
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY start_time ASC"
        
        result = db_optimizer.execute_query(query, tuple(params))
        return [self._format_appointment(row) for row in result]
    
    def update_appointment(self, appointment_id: int, updates: Dict) -> Dict:
        """Update appointment with conflict validation"""
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        # Validate status transition
        if 'status' in updates:
            new_status = updates['status']
            if new_status not in VALID_STATUSES:
                raise ValueError(f"Invalid status: {new_status}")
            
            current_status = appointment['status']
            if new_status not in STATUS_TRANSITIONS.get(current_status, []):
                # Allow same status
                if new_status != current_status:
                    raise ValueError(f"Cannot transition from {current_status} to {new_status}")
        
        # Check for conflicts if time changed
        # Parse times (handle both datetime objects and ISO strings)
        start_time_str = updates.get('start_time', appointment['start_time'])
        end_time_str = updates.get('end_time', appointment['end_time'])
        
        start_time = start_time_str if isinstance(start_time_str, datetime) else datetime.fromisoformat(start_time_str)
        end_time = end_time_str if isinstance(end_time_str, datetime) else datetime.fromisoformat(end_time_str)
        
        appointment_start = appointment['start_time'] if isinstance(appointment['start_time'], datetime) else datetime.fromisoformat(appointment['start_time'])
        appointment_end = appointment['end_time'] if isinstance(appointment['end_time'], datetime) else datetime.fromisoformat(appointment['end_time'])
        
        if start_time != appointment_start or end_time != appointment_end:
            # Time changed, check conflicts atomically within transaction
            with db_optimizer.get_connection() as conn:
                cursor = conn.cursor()
                conflict_check = cursor.execute("""
                    SELECT id FROM appointments 
                    WHERE user_id = ? 
                    AND status NOT IN ('canceled', 'no_show')
                    AND start_time < ? AND end_time > ?
                    AND id != ?
                """, (self.user_id, end_time.isoformat(), start_time.isoformat(), appointment_id)).fetchall()
                
                if conflict_check:
                    conn.rollback()
                    conflict_ids = [row[0] for row in conflict_check]
                    raise ValueError(f"Time slot conflicts with existing appointment(s): {conflict_ids}")
        
        # Build update query with field name validation (prevent SQL injection)
        set_clauses = []
        params = []
        
        for field in updates.keys():
            # Security: validate field name is in allowed list
            if field not in ALLOWED_UPDATE_FIELDS:
                raise ValueError(f"Field '{field}' is not allowed for updates")
            
            set_clauses.append(f"{field} = ?")
            if field in ['start_time', 'end_time'] and isinstance(updates[field], datetime):
                params.append(updates[field].isoformat())
            elif field == 'sync_to_calendar':
                params.append(1 if updates[field] else 0)
            elif field == 'title':
                # Validate title
                title_value = updates[field]
                if not title_value or not str(title_value).strip():
                    raise ValueError("title cannot be empty")
                if len(str(title_value)) > MAX_TITLE_LENGTH:
                    raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or less")
                params.append(str(title_value).strip())
            elif field == 'description' and updates[field] is not None:
                if len(str(updates[field])) > MAX_DESCRIPTION_LENGTH:
                    raise ValueError(f"description must be {MAX_DESCRIPTION_LENGTH} characters or less")
                params.append(updates[field])
            elif field == 'location' and updates[field] is not None:
                if len(str(updates[field])) > MAX_LOCATION_LENGTH:
                    raise ValueError(f"location must be {MAX_LOCATION_LENGTH} characters or less")
                params.append(updates[field])
            elif field == 'notes' and updates[field] is not None:
                if len(str(updates[field])) > MAX_NOTES_LENGTH:
                    raise ValueError(f"notes must be {MAX_NOTES_LENGTH} characters or less")
                params.append(updates[field])
            elif field == 'contact_email' and updates[field] is not None:
                email_value = str(updates[field])
                if len(email_value) > MAX_CONTACT_EMAIL_LENGTH:
                    raise ValueError(f"contact_email must be {MAX_CONTACT_EMAIL_LENGTH} characters or less")
                if '@' not in email_value or '.' not in email_value.split('@')[-1]:
                    raise ValueError("contact_email must be a valid email address")
                params.append(email_value)
            elif field == 'contact_name' and updates[field] is not None:
                if len(str(updates[field])) > MAX_CONTACT_NAME_LENGTH:
                    raise ValueError(f"contact_name must be {MAX_CONTACT_NAME_LENGTH} characters or less")
                params.append(updates[field])
            elif field == 'contact_phone' and updates[field] is not None:
                if len(str(updates[field])) > MAX_CONTACT_PHONE_LENGTH:
                    raise ValueError(f"contact_phone must be {MAX_CONTACT_PHONE_LENGTH} characters or less")
                params.append(updates[field])
            else:
                params.append(updates[field])
        
        if not set_clauses:
            return appointment
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([appointment_id, self.user_id])
        
        # Use parameterized query with validated field names
        query = f"UPDATE appointments SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?"
        db_optimizer.execute_query(query, tuple(params), fetch=False)
        
        updated_appointment = self.get_appointment(appointment_id)
        
        # Sync to calendar if enabled
        if updated_appointment.get('sync_to_calendar'):
            try:
                self._sync_to_calendar(updated_appointment, 'update')
            except Exception as e:
                logger.warning(f"⚠️ Calendar sync failed for appointment {appointment_id}: {e}")
        
        logger.info(f"✅ Updated appointment {appointment_id} for user {self.user_id}")
        return updated_appointment
    
    def cancel_appointment(self, appointment_id: int) -> Dict:
        """Cancel appointment"""
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        if appointment['status'] in ['completed', 'canceled']:
            raise ValueError(f"Cannot cancel appointment with status: {appointment['status']}")
        
        canceled = self.update_appointment(appointment_id, {'status': 'canceled'})
        
        # Sync cancellation to calendar if linked
        if appointment.get('sync_to_calendar'):
            try:
                self._sync_to_calendar(canceled, 'cancel')
            except Exception as e:
                logger.warning(f"⚠️ Calendar sync failed for appointment {appointment_id}: {e}")
        
        return canceled
    
    def _check_internal_conflicts(self, start_time: datetime, end_time: datetime,
                                  exclude_id: int = None) -> List[Dict]:
        """Check for conflicts with internal appointments (simplified overlap logic)"""
        # Simplified: appointments overlap if start < new_end AND end > new_start
        query = """
            SELECT * FROM appointments 
            WHERE user_id = ? 
            AND status NOT IN ('canceled', 'no_show')
            AND start_time < ? AND end_time > ?
        """
        params = [self.user_id, end_time.isoformat(), start_time.isoformat()]
        
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        
        result = db_optimizer.execute_query(query, tuple(params))
        return [self._format_appointment(row) for row in result]
    
    def check_conflicts(self, start_time: datetime, end_time: datetime,
                       exclude_id: int = None) -> List[Dict]:
        """Check for conflicts (internal appointments)"""
        return self._check_internal_conflicts(start_time, end_time, exclude_id)
    
    def get_freebusy(self, start: datetime, end: datetime) -> Dict:
        """Get free/busy information from internal appointments"""
        appointments = self.list_appointments(start=start, end=end)
        
        busy_periods = []
        for apt in appointments:
            if apt['status'] not in ['canceled', 'no_show']:
                busy_periods.append({
                    'start': apt['start_time'],
                    'end': apt['end_time'],
                    'appointment_id': apt['id'],
                    'title': apt['title']
                })
        
        return {
            'start': start.isoformat(),
            'end': end.isoformat(),
            'busy': busy_periods,
            'free': self.calculate_free_slots(start, end, busy_periods)
        }
    
    def calculate_free_slots(self, start: datetime, end: datetime,
                             busy_periods: List[Dict], slot_duration_minutes: int = DEFAULT_SLOT_DURATION_MINUTES) -> List[Dict]:
        """Calculate free time slots (public method for API)"""
        if not busy_periods:
            # All free
            free_slots = []
            current = start
            while current + timedelta(minutes=slot_duration_minutes) <= end:
                free_slots.append({
                    'start': current.isoformat(),
                    'end': (current + timedelta(minutes=slot_duration_minutes)).isoformat()
                })
                current += timedelta(minutes=slot_duration_minutes)
            return free_slots
        
        # Sort busy periods
        busy_sorted = sorted(busy_periods, key=lambda x: x['start'])
        
        free_slots = []
        current = start
        
        for busy in busy_sorted:
            busy_start = datetime.fromisoformat(busy['start']) if isinstance(busy['start'], str) else busy['start']
            busy_end = datetime.fromisoformat(busy['end']) if isinstance(busy['end'], str) else busy['end']
            
            # Add free slots before this busy period
            while current + timedelta(minutes=slot_duration_minutes) <= busy_start and len(free_slots) < max_slots:
                free_slots.append({
                    'start': current.isoformat(),
                    'end': (current + timedelta(minutes=slot_duration_minutes)).isoformat()
                })
                current += timedelta(minutes=slot_duration_minutes)
            
            # Move current past busy period
            current = max(current, busy_end)
        
        # Add remaining free slots
        while current + timedelta(minutes=slot_duration_minutes) <= end and len(free_slots) < max_slots:
            free_slots.append({
                'start': current.isoformat(),
                'end': (current + timedelta(minutes=slot_duration_minutes)).isoformat()
            })
            current += timedelta(minutes=slot_duration_minutes)
        
        return free_slots
    
    def _sync_to_calendar(self, appointment: Dict, action: str):
        """Sync appointment to calendar (create/update/cancel)"""
        # Check if calendar integration is active
        integration = integration_manager.get_integration(self.user_id, 'google_calendar')
        if not integration or integration['status'] != 'active':
            logger.debug(f"Calendar not connected for user {self.user_id}")
            return
        
        calendar_manager = CalendarManager(self.user_id)
        
        start_time = datetime.fromisoformat(appointment['start_time'])
        end_time = datetime.fromisoformat(appointment['end_time'])
        
        if action == 'create':
            # Create calendar event
            calendar_manager.create_event(
                summary=appointment['title'],
                start=start_time,
                end=end_time,
                description=appointment.get('description'),
                location=appointment.get('location'),
                attendees=[appointment['contact_email']] if appointment.get('contact_email') else None,
                provider='google_calendar',
                internal_entity_type='appointment',
                internal_entity_id=appointment['id']
            )
            logger.info(f"✅ Created calendar event for appointment {appointment['id']}")
        
        elif action == 'update':
            # Update calendar event
            updates = {
                'summary': appointment['title'],
                'start': start_time,
                'end': end_time
            }
            if appointment.get('description'):
                updates['description'] = appointment['description']
            if appointment.get('location'):
                updates['location'] = appointment['location']
            
            calendar_manager.update_event(
                internal_entity_type='appointment',
                internal_entity_id=appointment['id'],
                updates=updates,
                provider='google_calendar'
            )
            logger.info(f"✅ Updated calendar event for appointment {appointment['id']}")
        
        elif action == 'cancel':
            # Delete or update calendar event (provider-dependent)
            # For Google Calendar, we'll delete the event
            deleted = calendar_manager.delete_event(
                internal_entity_type='appointment',
                internal_entity_id=appointment['id'],
                provider='google_calendar'
            )
            if deleted:
                logger.info(f"✅ Deleted calendar event for appointment {appointment['id']}")
            else:
                logger.warning(f"⚠️ Failed to delete calendar event for appointment {appointment['id']}")
    
    def _format_appointment(self, row: Dict) -> Dict:
        """Format appointment row to API response"""
        return {
            'id': row['id'],
            'user_id': row['user_id'],
            'title': row['title'],
            'description': row.get('description'),
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'status': row['status'],
            'contact_id': row.get('contact_id'),
            'contact_name': row.get('contact_name'),
            'contact_email': row.get('contact_email'),
            'contact_phone': row.get('contact_phone'),
            'location': row.get('location'),
            'notes': row.get('notes'),
            'sync_to_calendar': bool(row.get('sync_to_calendar', 0)),
            'reminder_24h_sent': bool(row.get('reminder_24h_sent', 0)),
            'reminder_2h_sent': bool(row.get('reminder_2h_sent', 0)),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at')
        }
