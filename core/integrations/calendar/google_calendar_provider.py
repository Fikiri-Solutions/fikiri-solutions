#!/usr/bin/env python3
"""
Google Calendar Integration Provider
First plugin for the unified integration framework
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

from core.integrations.integration_framework import IntegrationProvider

logger = logging.getLogger(__name__)

# Google OAuth libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("⚠️ Google API libraries not available")

# OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/integrations/google-calendar/callback")

# Constants
DEFAULT_TOKEN_EXPIRY_SECONDS = 3600  # Default token expiry (1 hour)
API_TIMEOUT_SECONDS = 10  # API request timeout

# OAuth scopes (minimal - only what we need)
# calendar.events: create/update/delete events we manage
# calendar.readonly: check availability (free/busy) - required for conflict detection
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",  # Manage events
    "https://www.googleapis.com/auth/calendar.readonly",  # Read calendar (for free/busy)
]


class GoogleCalendarProvider(IntegrationProvider):
    """Google Calendar integration provider"""
    
    def __init__(self):
        if not GOOGLE_API_AVAILABLE:
            raise ImportError("Google API libraries not available")
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logger.warning("⚠️ Google Calendar OAuth not configured")
    
    def get_auth_url(self, state: str, redirect_uri: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        redirect_uri = redirect_uri or GOOGLE_REDIRECT_URI
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(GOOGLE_CALENDAR_SCOPES),
            'response_type': 'code',
            'access_type': 'offline',  # Required for refresh token
            'prompt': 'consent',  # Force consent to get refresh token
            'state': state
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return auth_url
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        redirect_uri = redirect_uri or GOOGLE_REDIRECT_URI
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        response = requests.post(token_url, data=data, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        
        token_data = response.json()
        
        return {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in', DEFAULT_TOKEN_EXPIRY_SECONDS),
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope', ' '.join(GOOGLE_CALENDAR_SCOPES))
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token"""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        
        token_data = response.json()
        
        if 'access_token' not in token_data:
            raise ValueError("Missing access_token in refresh response")
        
        return {
            'access_token': token_data['access_token'],
            'expires_in': token_data.get('expires_in', DEFAULT_TOKEN_EXPIRY_SECONDS),
            'token_type': token_data.get('token_type', 'Bearer')
        }
    
    def revoke_token(self, access_token: str) -> bool:
        """Revoke access token"""
        revoke_url = "https://oauth2.googleapis.com/revoke"
        data = {'token': access_token}
        
        try:
            response = requests.post(revoke_url, data=data, timeout=API_TIMEOUT_SECONDS)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False


class GoogleCalendarClient:
    """Google Calendar API client"""
    
    def __init__(self, access_token: str):
        if not GOOGLE_API_AVAILABLE:
            raise ImportError("Google API libraries not available")
        
        credentials = Credentials(
            token=access_token,
            refresh_token=None,  # Not needed for API calls
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        self.service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        self.provider = 'google_calendar'
    
    def create_event(self, summary: str, start: datetime, end: datetime,
                    description: str = None, location: str = None,
                    attendees: List[str] = None, calendar_id: str = 'primary') -> Dict:
        """Create calendar event"""
        event = {
            'summary': summary,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'UTC'
            }
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute(timeout=API_TIMEOUT_SECONDS)
            
            return {
                'id': created_event['id'],
                'htmlLink': created_event.get('htmlLink'),
                'summary': created_event.get('summary'),
                'start': created_event['start'],
                'end': created_event['end']
            }
        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise
    
    def get_event(self, event_id: str, calendar_id: str = 'primary') -> Dict:
        """Get calendar event"""
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute(timeout=API_TIMEOUT_SECONDS)
            
            return {
                'id': event['id'],
                'summary': event.get('summary'),
                'description': event.get('description'),
                'location': event.get('location'),
                'start': event.get('start'),
                'end': event.get('end'),
                'status': event.get('status'),
                'htmlLink': event.get('htmlLink')
            }
        except HttpError as e:
            logger.error(f"Failed to get calendar event: {e}")
            raise
    
    def update_event(self, event_id: str, updates: Dict, calendar_id: str = 'primary') -> Dict:
        """Update calendar event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute(timeout=API_TIMEOUT_SECONDS)
            
            # Apply updates
            for key, value in updates.items():
                if key in ['start', 'end']:
                    event[key] = {
                        'dateTime': value.isoformat() if isinstance(value, datetime) else value,
                        'timeZone': 'UTC'
                    }
                else:
                    event[key] = value
            
            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute(timeout=API_TIMEOUT_SECONDS)
            
            return {
                'id': updated_event['id'],
                'htmlLink': updated_event.get('htmlLink'),
                'summary': updated_event.get('summary')
            }
        except HttpError as e:
            logger.error(f"Failed to update calendar event: {e}")
            raise
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete calendar event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute(timeout=API_TIMEOUT_SECONDS)
            return True
        except HttpError as e:
            logger.error(f"Failed to delete calendar event: {e}")
            raise
    
    def list_events(self, time_min: datetime = None, time_max: datetime = None,
                   max_results: int = 10, calendar_id: str = 'primary') -> List[Dict]:
        """List calendar events"""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() if time_min else None,
                timeMax=time_max.isoformat() if time_max else None,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute(timeout=API_TIMEOUT_SECONDS)
            
            events = events_result.get('items', [])
            
            return [{
                'id': event['id'],
                'summary': event.get('summary'),
                'start': event.get('start'),
                'end': event.get('end'),
                'status': event.get('status')
            } for event in events]
        except HttpError as e:
            logger.error(f"Failed to list calendar events: {e}")
            raise
    
    def get_freebusy(self, time_min: datetime, time_max: datetime,
                    calendars: List[str] = None) -> Dict:
        """Get free/busy information"""
        try:
            body = {
                'timeMin': time_min.isoformat(),
                'timeMax': time_max.isoformat(),
                'items': [{'id': cal} for cal in (calendars or ['primary'])]
            }
            
            freebusy = self.service.freebusy().query(body=body).execute(timeout=API_TIMEOUT_SECONDS)
            
            return freebusy.get('calendars', {})
        except HttpError as e:
            logger.error(f"Failed to get free/busy: {e}")
            raise
