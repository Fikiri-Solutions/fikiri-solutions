#!/usr/bin/env python3
"""
Appointments API Routes
Step 1: Appointment CRUD (no calendar yet)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from core.appointments_service import AppointmentsService, SUGGESTED_SLOTS_COUNT, DEFAULT_SLOT_DURATION_MINUTES
from core.jwt_auth import jwt_required, get_current_user
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.integrations.calendar.calendar_manager import CalendarManager
from core.integrations.integration_framework import integration_manager
from datetime import timedelta

logger = logging.getLogger(__name__)

# Create appointments blueprint
appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")


@appointments_bp.route('', methods=['POST'])
@handle_api_errors
@jwt_required
def create_appointment():
    """Create new appointment"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        data = request.get_json()
        if not data:
            return create_error_response("Request body required", 400, 'MISSING_BODY')
        
        # Required fields
        title = data.get('title')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        if not title or not start_time_str or not end_time_str:
            return create_error_response("title, start_time, and end_time are required", 400, 'MISSING_FIELDS')
        
        # Parse times
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError as e:
            return create_error_response(f"Invalid date format: {e}", 400, 'INVALID_DATE')
        
        # Create appointment
        service = AppointmentsService(user_id)
        appointment = service.create_appointment(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=data.get('description'),
            contact_id=data.get('contact_id'),
            contact_name=data.get('contact_name'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            location=data.get('location'),
            notes=data.get('notes'),
            sync_to_calendar=data.get('sync_to_calendar', False)
        )
        
        logger.info(f"✅ Created appointment {appointment['id']} for user {user_id}")
        return create_success_response(appointment, 201)
        
    except ValueError as e:
        return create_error_response(str(e), 400, 'VALIDATION_ERROR')
    except Exception as e:
        logger.error(f"❌ Failed to create appointment: {e}")
        return create_error_response("Failed to create appointment", 500, 'CREATE_ERROR')


@appointments_bp.route('', methods=['GET'])
@handle_api_errors
@jwt_required
def list_appointments():
    """List appointments with optional filters"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        # Parse query parameters
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        status = request.args.get('status')
        
        start_time = None
        end_time = None
        
        if start_str:
            try:
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            except ValueError:
                return create_error_response("Invalid start date format", 400, 'INVALID_DATE')
        
        if end_str:
            try:
                end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            except ValueError:
                return create_error_response("Invalid end date format", 400, 'INVALID_DATE')
        
        service = AppointmentsService(user_id)
        appointments = service.list_appointments(
            start=start_time,
            end=end_time,
            status=status
        )
        
        return create_success_response({'appointments': appointments})
        
    except Exception as e:
        logger.error(f"❌ Failed to list appointments: {e}")
        return create_error_response("Failed to list appointments", 500, 'LIST_ERROR')


@appointments_bp.route('/<int:appointment_id>', methods=['PUT'])
@handle_api_errors
@jwt_required
def update_appointment(appointment_id):
    """Update appointment"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        data = request.get_json()
        if not data:
            return create_error_response("Request body required", 400, 'MISSING_BODY')
        
        # Parse datetime fields if present
        updates = {}
        for field in ['start_time', 'end_time']:
            if field in data:
                try:
                    updates[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                except ValueError:
                    return create_error_response(f"Invalid {field} format", 400, 'INVALID_DATE')
        
        # Copy other fields
        allowed_fields = ['title', 'description', 'status', 'contact_id', 'contact_name',
                         'contact_email', 'contact_phone', 'location', 'notes', 'sync_to_calendar']
        for field in allowed_fields:
            if field in data:
                updates[field] = data[field]
        
        service = AppointmentsService(user_id)
        appointment = service.update_appointment(appointment_id, updates)
        
        logger.info(f"✅ Updated appointment {appointment_id} for user {user_id}")
        return create_success_response(appointment)
        
    except ValueError as e:
        return create_error_response(str(e), 400, 'VALIDATION_ERROR')
    except Exception as e:
        logger.error(f"❌ Failed to update appointment: {e}")
        return create_error_response("Failed to update appointment", 500, 'UPDATE_ERROR')


@appointments_bp.route('/<int:appointment_id>/cancel', methods=['POST'])
@handle_api_errors
@jwt_required
def cancel_appointment(appointment_id):
    """Cancel appointment"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        service = AppointmentsService(user_id)
        appointment = service.cancel_appointment(appointment_id)
        
        logger.info(f"✅ Canceled appointment {appointment_id} for user {user_id}")
        return create_success_response(appointment)
        
    except ValueError as e:
        return create_error_response(str(e), 400, 'VALIDATION_ERROR')
    except Exception as e:
        logger.error(f"❌ Failed to cancel appointment: {e}")
        return create_error_response("Failed to cancel appointment", 500, 'CANCEL_ERROR')


@appointments_bp.route('/freebusy', methods=['GET'])
@handle_api_errors
@jwt_required
def get_freebusy():
    """Get free/busy information"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not start_str or not end_str:
            return create_error_response("start and end query parameters required", 400, 'MISSING_PARAMS')
        
        try:
            start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        except ValueError:
            return create_error_response("Invalid date format", 400, 'INVALID_DATE')
        
        service = AppointmentsService(user_id)
        
        # Check if calendar is connected
        integration = integration_manager.get_integration(user_id, 'google_calendar')
        calendar_connected = integration and integration['status'] == 'active'
        
        if calendar_connected:
            # Use provider free/busy
            try:
                calendar_manager = CalendarManager(user_id)
                provider_freebusy = calendar_manager.get_freebusy(start_time, end_time, provider='google_calendar')
                
                # Merge with internal appointments
                internal_freebusy = service.get_freebusy(start_time, end_time)
                
                # Combine busy periods
                all_busy = provider_freebusy.get('busy', []) + internal_freebusy.get('busy', [])
                
                return create_success_response({
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'busy': all_busy,
                    'source': 'calendar_and_internal',
                    'free': service.calculate_free_slots(start_time, end_time, all_busy)
                })
            except Exception as e:
                logger.warning(f"Calendar free/busy failed, falling back to internal: {e}")
                # Fall through to internal-only
        
        # Use internal appointments only
        freebusy = service.get_freebusy(start_time, end_time)
        return create_success_response({
            **freebusy,
            'source': 'internal_only'
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get free/busy: {e}")
        return create_error_response("Failed to get free/busy", 500, 'FREEBUSY_ERROR')


@appointments_bp.route('/check-conflicts', methods=['POST'])
@handle_api_errors
@jwt_required
def check_conflicts():
    """Check for scheduling conflicts"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        data = request.get_json()
        if not data:
            return create_error_response("Request body required", 400, 'MISSING_BODY')
        
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        exclude_id = data.get('exclude_id')  # For updates
        
        if not start_time_str or not end_time_str:
            return create_error_response("start_time and end_time required", 400, 'MISSING_FIELDS')
        
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            return create_error_response("Invalid date format", 400, 'INVALID_DATE')
        
        service = AppointmentsService(user_id)
        
        # Check internal conflicts
        internal_conflicts = service.check_conflicts(start_time, end_time, exclude_id=exclude_id)
        
        # Check calendar conflicts if connected
        calendar_conflicts = []
        integration = integration_manager.get_integration(user_id, 'google_calendar')
        if integration and integration['status'] == 'active':
            try:
                calendar_manager = CalendarManager(user_id)
                calendar_conflicts = calendar_manager.check_conflicts(start_time, end_time, provider='google_calendar')
            except Exception as e:
                logger.warning(f"Calendar conflict check failed: {e}")
        
        # Combine conflicts
        all_conflicts = internal_conflicts + calendar_conflicts
        
        # Get suggested alternatives (next N available slots)
        suggested_slots = []
        if all_conflicts:
            # Find next available slots after the requested time
            current = end_time
            for _ in range(SUGGESTED_SLOTS_COUNT):
                # Try DEFAULT_SLOT_DURATION_MINUTES slots
                slot_start = current
                slot_end = current + timedelta(minutes=DEFAULT_SLOT_DURATION_MINUTES)
                
                # Check if this slot is free
                slot_conflicts = service.check_conflicts(slot_start, slot_end, exclude_id=exclude_id)
                if not slot_conflicts:
                    suggested_slots.append({
                        'start': slot_start.isoformat(),
                        'end': slot_end.isoformat()
                    })
                    if len(suggested_slots) >= SUGGESTED_SLOTS_COUNT:
                        break
                
                current += timedelta(minutes=DEFAULT_SLOT_DURATION_MINUTES)
        
        return create_success_response({
            'has_conflicts': len(all_conflicts) > 0,
            'conflicts': all_conflicts,
            'suggested_slots': suggested_slots
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to check conflicts: {e}")
        return create_error_response("Failed to check conflicts", 500, 'CONFLICT_CHECK_ERROR')
