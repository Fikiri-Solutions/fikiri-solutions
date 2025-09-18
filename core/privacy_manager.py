"""
Privacy Management System
Handles user privacy settings, data retention, and consent management
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class PrivacySettings:
    """User privacy settings data structure"""
    id: int
    user_id: int
    data_retention_days: int
    email_scanning_enabled: bool
    personal_email_exclusion: bool
    auto_labeling_enabled: bool
    lead_detection_enabled: bool
    analytics_tracking_enabled: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class PrivacyConsent:
    """Privacy consent data structure"""
    id: int
    user_id: int
    consent_type: str
    granted: bool
    consent_text: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    granted_at: datetime
    revoked_at: Optional[datetime]

class PrivacyManager:
    """Comprehensive privacy and data retention management"""
    
    def __init__(self):
        self.default_retention_days = 90
        self.max_retention_days = 365
        self.min_retention_days = 30
    
    def create_default_privacy_settings(self, user_id: int) -> Dict[str, Any]:
        """Create default privacy settings for new user"""
        try:
            # Check if settings already exist
            existing = db_optimizer.execute_query(
                "SELECT id FROM user_privacy_settings WHERE user_id = ?",
                (user_id,)
            )
            
            if existing:
                return {
                    'success': True,
                    'message': 'Privacy settings already exist'
                }
            
            # Create default settings
            db_optimizer.execute_query(
                """INSERT INTO user_privacy_settings 
                   (user_id, data_retention_days, email_scanning_enabled, 
                    personal_email_exclusion, auto_labeling_enabled, 
                    lead_detection_enabled, analytics_tracking_enabled) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, self.default_retention_days, True, True, True, True, True),
                fetch=False
            )
            
            logger.info(f"Default privacy settings created for user {user_id}")
            
            return {
                'success': True,
                'message': 'Default privacy settings created'
            }
            
        except Exception as e:
            logger.error(f"Error creating privacy settings: {e}")
            return {
                'success': False,
                'error': 'Failed to create privacy settings',
                'error_code': 'PRIVACY_SETTINGS_ERROR'
            }
    
    def get_privacy_settings(self, user_id: int) -> Optional[PrivacySettings]:
        """Get user privacy settings"""
        try:
            settings_data = db_optimizer.execute_query(
                "SELECT * FROM user_privacy_settings WHERE user_id = ?",
                (user_id,)
            )
            
            if not settings_data:
                return None
            
            settings = settings_data[0]
            return PrivacySettings(
                id=settings['id'],
                user_id=settings['user_id'],
                data_retention_days=settings['data_retention_days'],
                email_scanning_enabled=bool(settings['email_scanning_enabled']),
                personal_email_exclusion=bool(settings['personal_email_exclusion']),
                auto_labeling_enabled=bool(settings['auto_labeling_enabled']),
                lead_detection_enabled=bool(settings['lead_detection_enabled']),
                analytics_tracking_enabled=bool(settings['analytics_tracking_enabled']),
                created_at=datetime.fromisoformat(settings['created_at']),
                updated_at=datetime.fromisoformat(settings['updated_at'])
            )
            
        except Exception as e:
            logger.error(f"Error getting privacy settings: {e}")
            return None
    
    def update_privacy_settings(self, user_id: int, **updates) -> Dict[str, Any]:
        """Update user privacy settings"""
        try:
            # Validate retention days
            if 'data_retention_days' in updates:
                retention_days = updates['data_retention_days']
                if not (self.min_retention_days <= retention_days <= self.max_retention_days):
                    return {
                        'success': False,
                        'error': f'Retention days must be between {self.min_retention_days} and {self.max_retention_days}',
                        'error_code': 'INVALID_RETENTION_DAYS'
                    }
            
            # Build update query
            update_fields = []
            update_values = []
            
            allowed_fields = [
                'data_retention_days', 'email_scanning_enabled', 'personal_email_exclusion',
                'auto_labeling_enabled', 'lead_detection_enabled', 'analytics_tracking_enabled'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update',
                    'error_code': 'NO_UPDATES'
                }
            
            update_values.append(user_id)
            
            query = f"UPDATE user_privacy_settings SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Get updated settings
            updated_settings = self.get_privacy_settings(user_id)
            
            return {
                'success': True,
                'settings': updated_settings,
                'message': 'Privacy settings updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating privacy settings: {e}")
            return {
                'success': False,
                'error': 'Failed to update privacy settings',
                'error_code': 'UPDATE_ERROR'
            }
    
    def record_privacy_consent(self, user_id: int, consent_type: str, 
                              granted: bool, consent_text: str,
                              ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Record user privacy consent"""
        try:
            # Revoke previous consent of same type if granting new consent
            if granted:
                db_optimizer.execute_query(
                    "UPDATE privacy_consents SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = ? AND consent_type = ? AND granted = 1",
                    (user_id, consent_type),
                    fetch=False
                )
            
            # Record new consent
            db_optimizer.execute_query(
                """INSERT INTO privacy_consents 
                   (user_id, consent_type, granted, consent_text, ip_address, user_agent) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, consent_type, granted, consent_text, ip_address, user_agent),
                fetch=False
            )
            
            logger.info(f"Privacy consent recorded for user {user_id}: {consent_type} = {granted}")
            
            return {
                'success': True,
                'message': 'Privacy consent recorded successfully'
            }
            
        except Exception as e:
            logger.error(f"Error recording privacy consent: {e}")
            return {
                'success': False,
                'error': 'Failed to record privacy consent',
                'error_code': 'CONSENT_ERROR'
            }
    
    def get_privacy_consents(self, user_id: int) -> List[PrivacyConsent]:
        """Get all privacy consents for user"""
        try:
            consents_data = db_optimizer.execute_query(
                "SELECT * FROM privacy_consents WHERE user_id = ? ORDER BY granted_at DESC",
                (user_id,)
            )
            
            consents = []
            for consent in consents_data:
                consents.append(PrivacyConsent(
                    id=consent['id'],
                    user_id=consent['user_id'],
                    consent_type=consent['consent_type'],
                    granted=bool(consent['granted']),
                    consent_text=consent['consent_text'],
                    ip_address=consent['ip_address'],
                    user_agent=consent['user_agent'],
                    granted_at=datetime.fromisoformat(consent['granted_at']),
                    revoked_at=datetime.fromisoformat(consent['revoked_at']) if consent['revoked_at'] else None
                ))
            
            return consents
            
        except Exception as e:
            logger.error(f"Error getting privacy consents: {e}")
            return []
    
    def has_consent(self, user_id: int, consent_type: str) -> bool:
        """Check if user has granted specific consent"""
        try:
            consent_data = db_optimizer.execute_query(
                """SELECT granted FROM privacy_consents 
                   WHERE user_id = ? AND consent_type = ? AND granted = 1 
                   AND revoked_at IS NULL 
                   ORDER BY granted_at DESC LIMIT 1""",
                (user_id, consent_type)
            )
            
            return bool(consent_data) and consent_data[0]['granted']
            
        except Exception as e:
            logger.error(f"Error checking consent: {e}")
            return False
    
    def cleanup_expired_data(self, user_id: int) -> Dict[str, Any]:
        """Clean up expired data based on user's retention settings"""
        try:
            settings = self.get_privacy_settings(user_id)
            if not settings:
                return {
                    'success': False,
                    'error': 'Privacy settings not found',
                    'error_code': 'SETTINGS_NOT_FOUND'
                }
            
            cutoff_date = datetime.now() - timedelta(days=settings.data_retention_days)
            cleanup_results = {}
            
            # Clean up old emails (if email scanning is disabled)
            if not settings.email_scanning_enabled:
                email_result = db_optimizer.execute_query(
                    """DELETE FROM leads WHERE user_id = ? AND created_at < ? 
                       AND source = 'gmail'""",
                    (user_id, cutoff_date.isoformat()),
                    fetch=False
                )
                cleanup_results['emails_deleted'] = email_result
            
            # Clean up old lead activities
            activity_result = db_optimizer.execute_query(
                """DELETE FROM lead_activities WHERE lead_id IN 
                   (SELECT id FROM leads WHERE user_id = ?) 
                   AND timestamp < ?""",
                (user_id, cutoff_date.isoformat()),
                fetch=False
            )
            cleanup_results['activities_deleted'] = activity_result
            
            # Clean up old email sync records
            sync_result = db_optimizer.execute_query(
                """DELETE FROM email_sync WHERE user_id = ? 
                   AND started_at < ?""",
                (user_id, cutoff_date.isoformat()),
                fetch=False
            )
            cleanup_results['sync_records_deleted'] = sync_result
            
            # Log cleanup activity
            total_deleted = sum(cleanup_results.values())
            db_optimizer.execute_query(
                """INSERT INTO data_retention_logs 
                   (user_id, data_type, records_deleted, retention_policy_days, metadata) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, 'general_cleanup', total_deleted, settings.data_retention_days,
                 json.dumps(cleanup_results)),
                fetch=False
            )
            
            logger.info(f"Data cleanup completed for user {user_id}: {total_deleted} records deleted")
            
            return {
                'success': True,
                'cleanup_results': cleanup_results,
                'total_deleted': total_deleted,
                'message': 'Data cleanup completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up expired data: {e}")
            return {
                'success': False,
                'error': 'Failed to cleanup expired data',
                'error_code': 'CLEANUP_ERROR'
            }
    
    def get_data_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's data for privacy dashboard"""
        try:
            # Get data counts
            leads_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            activities_count = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM lead_activities la 
                   JOIN leads l ON la.lead_id = l.id 
                   WHERE l.user_id = ?""",
                (user_id,)
            )[0]['count']
            
            sync_records_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM email_sync WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            # Get privacy settings
            settings = self.get_privacy_settings(user_id)
            
            # Get consent status
            gmail_consent = self.has_consent(user_id, 'gmail_access')
            data_processing_consent = self.has_consent(user_id, 'data_processing')
            analytics_consent = self.has_consent(user_id, 'analytics')
            
            return {
                'success': True,
                'data_summary': {
                    'leads_count': leads_count,
                    'activities_count': activities_count,
                    'sync_records_count': sync_records_count,
                    'privacy_settings': settings,
                    'consents': {
                        'gmail_access': gmail_consent,
                        'data_processing': data_processing_consent,
                        'analytics': analytics_consent
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {
                'success': False,
                'error': 'Failed to get data summary',
                'error_code': 'SUMMARY_ERROR'
            }
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all user data for GDPR compliance"""
        try:
            # Get user profile
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            # Get leads data
            leads_data = db_optimizer.execute_query(
                "SELECT * FROM leads WHERE user_id = ?",
                (user_id,)
            )
            
            # Get activities data
            activities_data = db_optimizer.execute_query(
                """SELECT la.*, l.email as lead_email FROM lead_activities la 
                   JOIN leads l ON la.lead_id = l.id 
                   WHERE l.user_id = ?""",
                (user_id,)
            )
            
            # Get privacy settings
            privacy_settings = self.get_privacy_settings(user_id)
            
            # Get consent history
            consents = self.get_privacy_consents(user_id)
            
            export_data = {
                'user_profile': dict(user_data),
                'leads': [dict(lead) for lead in leads_data],
                'activities': [dict(activity) for activity in activities_data],
                'privacy_settings': privacy_settings.__dict__ if privacy_settings else None,
                'consents': [consent.__dict__ for consent in consents],
                'export_timestamp': datetime.now().isoformat(),
                'data_retention_policy': f"{privacy_settings.data_retention_days} days" if privacy_settings else "Default"
            }
            
            return {
                'success': True,
                'export_data': export_data,
                'message': 'User data exported successfully'
            }
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return {
                'success': False,
                'error': 'Failed to export user data',
                'error_code': 'EXPORT_ERROR'
            }
    
    def delete_user_data(self, user_id: int) -> Dict[str, Any]:
        """Delete all user data for GDPR compliance"""
        try:
            # Get data counts before deletion
            leads_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            activities_count = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM lead_activities la 
                   JOIN leads l ON la.lead_id = l.id 
                   WHERE l.user_id = ?""",
                (user_id,)
            )[0]['count']
            
            # Delete user data (cascade will handle related records)
            db_optimizer.execute_query(
                "DELETE FROM users WHERE id = ?",
                (user_id,),
                fetch=False
            )
            
            # Log deletion
            db_optimizer.execute_query(
                """INSERT INTO data_retention_logs 
                   (user_id, data_type, records_deleted, retention_policy_days, metadata) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, 'complete_deletion', leads_count + activities_count, 0,
                 json.dumps({'reason': 'user_request', 'deletion_type': 'complete'})),
                fetch=False
            )
            
            logger.info(f"Complete user data deletion completed for user {user_id}")
            
            return {
                'success': True,
                'deleted_records': {
                    'leads': leads_count,
                    'activities': activities_count
                },
                'message': 'User data deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return {
                'success': False,
                'error': 'Failed to delete user data',
                'error_code': 'DELETION_ERROR'
            }

# Global privacy manager instance
privacy_manager = PrivacyManager()

# Export the privacy management system
__all__ = ['PrivacyManager', 'privacy_manager', 'PrivacySettings', 'PrivacyConsent']
