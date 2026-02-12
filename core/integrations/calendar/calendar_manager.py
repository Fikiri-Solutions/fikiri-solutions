#!/usr/bin/env python3
"""
Calendar Manager
Unified interface for calendar operations (Google, Outlook, etc.)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from core.integrations.integration_framework import integration_manager
from core.integrations.calendar.google_calendar_provider import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarManager:
    """Unified calendar manager"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_calendar_client(self, provider: str = 'google_calendar') -> Optional[Any]:
        """Get calendar client for provider"""
        integration = integration_manager.get_integration(self.user_id, provider)
        if not integration:
            return None
        
        access_token = integration_manager.get_valid_token(self.user_id, provider)
        if not access_token:
            return None
        
        if provider == 'google_calendar':
            return GoogleCalendarClient(access_token)
        # Add OutlookCalendarClient here when implemented
        # elif provider == 'outlook_calendar':
        #     return OutlookCalendarClient(access_token)
        
        return None
    
    def create_event(self, summary: str, start: datetime, end: datetime,
                    description: str = None, location: str = None,
                    attendees: List[str] = None, provider: str = 'google_calendar',
                    internal_entity_type: str = None, internal_entity_id: int = None) -> Dict:
        """Create calendar event and link to internal entity"""
        client = self.get_calendar_client(provider)
        if not client:
            raise ValueError(f"Calendar not connected for provider: {provider}")
        
        # Create event
        event = client.create_event(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees
        )
        
        # Link to internal entity if provided
        if internal_entity_type and internal_entity_id:
            integration = integration_manager.get_integration(self.user_id, provider)
            if not integration:
                logger.warning(f"Integration not found for user {self.user_id}, provider {provider}")
            else:
                integration_manager.link_calendar_event(
                    user_id=self.user_id,
                    integration_id=integration['id'],
                    internal_entity_type=internal_entity_type,
                    internal_entity_id=internal_entity_id,
                    external_event_id=event['id'],
                    external_calendar_id='primary'
                )
        
        return event
    
    def update_event(self, internal_entity_type: str, internal_entity_id: int,
                    updates: Dict, provider: str = 'google_calendar') -> Dict:
        """Update calendar event linked to internal entity"""
        # Get event link
        link = integration_manager.get_calendar_event_link(
            self.user_id, internal_entity_type, internal_entity_id
        )
        if not link:
            raise ValueError(f"No calendar event linked to {internal_entity_type}:{internal_entity_id}")
        
        client = self.get_calendar_client(provider)
        if not client:
            raise ValueError(f"Calendar not connected for provider: {provider}")
        
        return client.update_event(link['external_event_id'], updates)
    
    def delete_event(self, internal_entity_type: str, internal_entity_id: int,
                    provider: str = 'google_calendar') -> bool:
        """Delete calendar event linked to internal entity"""
        # Get event link
        link = integration_manager.get_calendar_event_link(
            self.user_id, internal_entity_type, internal_entity_id
        )
        if not link:
            return False
        
        client = self.get_calendar_client(provider)
        if not client:
            return False
        
        deleted = client.delete_event(link['external_event_id'])
        
        # Remove link
        if deleted:
            from core.database_optimization import db_optimizer
            db_optimizer.execute_query(
                "DELETE FROM calendar_event_links WHERE id = ?",
                (link['id'],),
                fetch=False
            )
        
        return deleted
    
    def get_freebusy(self, time_min: datetime, time_max: datetime,
                    provider: str = 'google_calendar') -> Dict:
        """Get free/busy information"""
        client = self.get_calendar_client(provider)
        if not client:
            raise ValueError(f"Calendar not connected for provider: {provider}")
        
        return client.get_freebusy(time_min, time_max)
    
    def check_conflicts(self, start: datetime, end: datetime,
                       provider: str = 'google_calendar') -> List[Dict]:
        """Check for scheduling conflicts"""
        freebusy = self.get_freebusy(start, end, provider)
        
        conflicts = []
        for calendar_id, calendar_data in freebusy.items():
            busy = calendar_data.get('busy', [])
            for busy_period in busy:
                conflicts.append({
                    'calendar': calendar_id,
                    'start': busy_period['start'],
                    'end': busy_period['end']
                })
        
        return conflicts
