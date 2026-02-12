#!/usr/bin/env python3
"""
Integration API Routes
Unified endpoints for all integrations (Calendar, CRM, etc.)
"""

import os
import secrets
import json
import logging
from flask import Blueprint, request, jsonify, redirect, session
from datetime import datetime, timedelta
from typing import Dict, Any

from core.jwt_auth import jwt_required, get_current_user
from core.integrations.integration_framework import integration_manager
from core.integrations.calendar.google_calendar_provider import GoogleCalendarProvider
from core.integrations.calendar.calendar_manager import CalendarManager
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/integrations")

# Register providers
google_calendar_provider = GoogleCalendarProvider()
integration_manager.register_provider('google_calendar', google_calendar_provider)

# Constants
OAUTH_STATE_EXPIRY_MINUTES = 10
OAUTH_STATE_TOKEN_LENGTH = 24

# OAuth state storage
def store_oauth_state(state: str, user_id: int, provider: str, redirect_url: str = None):
    """Store OAuth state for CSRF protection"""
    expires_at = int((datetime.now() + timedelta(minutes=OAUTH_STATE_EXPIRY_MINUTES)).timestamp())
    db_optimizer.execute_query("""
        INSERT OR REPLACE INTO oauth_states 
        (state, user_id, provider, redirect_url, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (state, user_id, provider, redirect_url, expires_at), fetch=False)

def verify_oauth_state(state: str) -> Dict:
    """Verify OAuth state"""
    result = db_optimizer.execute_query(
        "SELECT * FROM oauth_states WHERE state = ? AND expires_at > ?",
        (state, int(datetime.now().timestamp()))
    )
    if result:
        return result[0]
    return None


# ============================================================================
# GOOGLE CALENDAR INTEGRATION
# ============================================================================

@integrations_bp.route("/google-calendar/connect", methods=["GET"])
@jwt_required
def google_calendar_connect():
    """Start Google Calendar OAuth flow"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        # Generate state
        state = secrets.token_urlsafe(OAUTH_STATE_TOKEN_LENGTH)
        redirect_url = request.args.get('redirect', '/dashboard')
        
        # Store state
        store_oauth_state(state, user_id, 'google_calendar', redirect_url)
        
        # Get auth URL
        auth_url = google_calendar_provider.get_auth_url(
            state=state,
            redirect_uri=os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/integrations/google-calendar/callback')
        )
        
        return jsonify({'success': True, 'auth_url': auth_url})
        
    except Exception as e:
        logger.error(f"Failed to start Google Calendar OAuth: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/google-calendar/callback", methods=["GET"])
def google_calendar_callback():
    """Handle Google Calendar OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/integrations?error={error}")
        
        if not code or not state:
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/integrations?error=missing_params")
        
        # Verify state
        state_data = verify_oauth_state(state)
        if not state_data:
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/integrations?error=invalid_state")
        
        user_id = state_data['user_id']
        
        # Exchange code for tokens
        token_data = google_calendar_provider.exchange_code_for_tokens(
            code=code,
            redirect_uri=os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/integrations/google-calendar/callback')
        )
        
        # Store integration with encryption version in meta
        integration_manager.connect(
            user_id=user_id,
            provider='google_calendar',
            token_data=token_data,
            scopes=token_data.get('scope', '').split(),
            meta={'calendar_id': 'primary', 'token_enc_version': 1}
        )
        
        # Clean up state
        db_optimizer.execute_query(
            "DELETE FROM oauth_states WHERE state = ?",
            (state,),
            fetch=False
        )
        
        redirect_url = state_data.get('redirect_url') or '/dashboard'
        return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}{redirect_url}?calendar_connected=true")
        
    except Exception as e:
        logger.error(f"Failed to handle Google Calendar callback: {e}")
        return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/integrations?error={str(e)}")


@integrations_bp.route("/google-calendar/status", methods=["GET"])
@jwt_required
def google_calendar_status():
    """Get Google Calendar integration status"""
    try:
        user = get_current_user()
        status = integration_manager.get_status(user['id'], 'google_calendar')
        return jsonify(status)
    except Exception as e:
        logger.error(f"Failed to get Google Calendar status: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/google-calendar/disconnect", methods=["POST"])
@jwt_required
def google_calendar_disconnect():
    """Disconnect Google Calendar integration"""
    try:
        user = get_current_user()
        result = integration_manager.disconnect(user['id'], 'google_calendar')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to disconnect Google Calendar: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CALENDAR OPERATIONS
# ============================================================================

@integrations_bp.route("/calendar/events", methods=["GET"])
@jwt_required
def list_calendar_events():
    """List calendar events"""
    try:
        user = get_current_user()
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        provider = request.args.get('provider', 'google_calendar')
        
        manager = CalendarManager(user['id'])
        client = manager.get_calendar_client(provider)
        
        if not client:
            return jsonify({'error': 'Calendar not connected'}), 400
        
        time_min = datetime.fromisoformat(start_date) if start_date else datetime.now()
        time_max = datetime.fromisoformat(end_date) if end_date else time_min + timedelta(days=30)
        
        events = client.list_events(time_min=time_min, time_max=time_max)
        
        return jsonify({'success': True, 'events': events})
        
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/calendar/freebusy", methods=["GET"])
@jwt_required
def get_freebusy():
    """Get free/busy information"""
    try:
        user = get_current_user()
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        provider = request.args.get('provider', 'google_calendar')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start and end dates required'}), 400
        
        manager = CalendarManager(user['id'])
        time_min = datetime.fromisoformat(start_date)
        time_max = datetime.fromisoformat(end_date)
        
        freebusy = manager.get_freebusy(time_min, time_max, provider)
        
        return jsonify({'success': True, 'freebusy': freebusy})
        
    except Exception as e:
        logger.error(f"Failed to get free/busy: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/calendar/events", methods=["POST"])
@jwt_required
def create_calendar_event():
    """Create calendar event"""
    try:
        user = get_current_user()
        data = request.json
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        if 'start' not in data or 'end' not in data:
            return jsonify({'error': 'start and end dates required'}), 400
        
        if 'summary' not in data:
            return jsonify({'error': 'summary required'}), 400
        
        manager = CalendarManager(user['id'])
        
        try:
            start = datetime.fromisoformat(data['start'])
            end = datetime.fromisoformat(data['end'])
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid date format: {e}'}), 400
        
        event = manager.create_event(
            summary=data['summary'],
            start=start,
            end=end,
            description=data.get('description'),
            location=data.get('location'),
            attendees=data.get('attendees'),
            provider=data.get('provider', 'google_calendar'),
            internal_entity_type=data.get('entity_type'),
            internal_entity_id=data.get('entity_id')
        )
        
        return jsonify({'success': True, 'event': event})
        
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/calendar/events/<entity_type>/<int:entity_id>", methods=["PUT"])
@jwt_required
def update_calendar_event(entity_type: str, entity_id: int):
    """Update calendar event linked to internal entity"""
    try:
        user = get_current_user()
        data = request.json
        provider = data.get('provider', 'google_calendar')
        
        manager = CalendarManager(user['id'])
        
        updates = {}
        if 'start' in data:
            updates['start'] = datetime.fromisoformat(data['start'])
        if 'end' in data:
            updates['end'] = datetime.fromisoformat(data['end'])
        if 'summary' in data:
            updates['summary'] = data['summary']
        if 'description' in data:
            updates['description'] = data['description']
        if 'location' in data:
            updates['location'] = data['location']
        
        event = manager.update_event(entity_type, entity_id, updates, provider)
        
        return jsonify({'success': True, 'event': event})
        
    except Exception as e:
        logger.error(f"Failed to update calendar event: {e}")
        return jsonify({'error': str(e)}), 500


@integrations_bp.route("/calendar/events/<entity_type>/<int:entity_id>", methods=["DELETE"])
@jwt_required
def delete_calendar_event(entity_type: str, entity_id: int):
    """Delete calendar event linked to internal entity"""
    try:
        user = get_current_user()
        provider = request.args.get('provider', 'google_calendar')
        
        manager = CalendarManager(user['id'])
        deleted = manager.delete_event(entity_type, entity_id, provider)
        
        return jsonify({'success': deleted})
        
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return jsonify({'error': str(e)}), 500
