#!/usr/bin/env python3
"""
Integration Cleanup Jobs
Background cleanup for expired states, stale locks, and inactive links
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Cleanup thresholds
OAUTH_STATE_EXPIRY_HOURS = 24  # Clean up oauth_states older than 24 hours
STALE_REFRESH_SECONDS = 60  # Clean up stale refresh locks older than 60 seconds
INACTIVE_LINKS_MONTHS = 6  # Optional: prune inactive links older than 6 months


def cleanup_expired_oauth_states() -> Dict[str, Any]:
    """Delete expired OAuth states"""
    try:
        expiry_timestamp = int((datetime.now() - timedelta(hours=OAUTH_STATE_EXPIRY_HOURS)).timestamp())
        
        result = db_optimizer.execute_query("""
            DELETE FROM oauth_states 
            WHERE expires_at < ?
        """, (expiry_timestamp,), fetch=False)
        
        logger.info(f"✅ Cleaned up expired OAuth states (older than {OAUTH_STATE_EXPIRY_HOURS} hours)")
        return {'success': True, 'deleted': result if result else 0}
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup expired OAuth states: {e}")
        return {'success': False, 'error': str(e)}


def cleanup_stale_refresh_locks() -> Dict[str, Any]:
    """Clear stale refresh locks (status='refreshing' older than threshold)"""
    try:
        stale_threshold = datetime.now() - timedelta(seconds=STALE_REFRESH_SECONDS)
        
        result = db_optimizer.execute_query("""
            UPDATE integration_sync_state 
            SET status = 'error', 
                error = 'Stale refresh lock cleared',
                updated_at = CURRENT_TIMESTAMP
            WHERE resource = 'token_refresh' 
            AND status = 'refreshing'
            AND updated_at < ?
        """, (stale_threshold.isoformat(),), fetch=False)
        
        logger.info(f"✅ Cleaned up stale refresh locks (older than {STALE_REFRESH_SECONDS} seconds)")
        return {'success': True, 'cleared': result if result else 0}
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup stale refresh locks: {e}")
        return {'success': False, 'error': str(e)}


def cleanup_inactive_event_links(months: int = INACTIVE_LINKS_MONTHS) -> Dict[str, Any]:
    """Optionally prune inactive event links older than threshold"""
    try:
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        result = db_optimizer.execute_query("""
            DELETE FROM calendar_event_links 
            WHERE is_active = 0 
            AND updated_at < ?
        """, (cutoff_date.isoformat(),), fetch=False)
        
        logger.info(f"✅ Cleaned up inactive event links (older than {months} months)")
        return {'success': True, 'deleted': result if result else 0}
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup inactive event links: {e}")
        return {'success': False, 'error': str(e)}


def run_all_cleanup_jobs() -> Dict[str, Any]:
    """Run all cleanup jobs"""
    results = {
        'oauth_states': cleanup_expired_oauth_states(),
        'stale_refresh_locks': cleanup_stale_refresh_locks(),
        'inactive_links': cleanup_inactive_event_links()
    }
    
    logger.info(f"✅ Cleanup jobs completed: {results}")
    return results
