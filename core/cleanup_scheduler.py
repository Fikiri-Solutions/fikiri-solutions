#!/usr/bin/env python3
"""
Cleanup Job Scheduler
Scheduled background tasks for data cleanup and maintenance
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class CleanupScheduler:
    """Scheduled cleanup jobs for system maintenance"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.cleanup_interval = 3600  # Run cleanup checks every hour
        self.job_retention_days = int(os.getenv('CLEANUP_JOB_RETENTION_DAYS', '30'))
        self.email_retention_days = int(os.getenv('CLEANUP_EMAIL_RETENTION_DAYS', '90'))
        self.log_retention_days = int(os.getenv('CLEANUP_LOG_RETENTION_DAYS', '30'))
    
    def start(self):
        """Start the cleanup scheduler"""
        if self.running:
            logger.warning("⚠️ Cleanup scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("✅ Cleanup scheduler started")
    
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Cleanup scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Run cleanup tasks
                self.cleanup_old_email_jobs()
                self.cleanup_old_sync_records()
                self.cleanup_old_analytics_events()
                self.cleanup_old_performance_logs()
                self.cleanup_expired_sessions()
                
                # Sleep until next cleanup cycle
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ Cleanup scheduler error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def cleanup_old_email_jobs(self) -> Dict[str, Any]:
        """Clean up old email jobs"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.job_retention_days)
        result = db_optimizer.execute_query(
            "DELETE FROM email_jobs WHERE created_at < ? AND status IN ('sent', 'failed', 'cancelled')",
            (cutoff_date.isoformat(),), fetch=False
        )
        deleted_count = result if isinstance(result, int) else 0
        logger.info(f"✅ Cleaned up {deleted_count} old email jobs")
        return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
    
    def cleanup_old_sync_records(self) -> Dict[str, Any]:
        """Clean up old email sync records"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.email_retention_days)
        result = db_optimizer.execute_query(
            "DELETE FROM email_sync WHERE started_at < ? AND status IN ('completed', 'failed')",
            (cutoff_date.isoformat(),), fetch=False
        )
        deleted_count = result if isinstance(result, int) else 0
        logger.info(f"✅ Cleaned up {deleted_count} old sync records")
        return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
    
    def cleanup_old_analytics_events(self) -> Dict[str, Any]:
        """Clean up old analytics events"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.log_retention_days)
        result = db_optimizer.execute_query(
            "DELETE FROM analytics_events WHERE created_at < ?",
            (cutoff_date.isoformat(),), fetch=False
        )
        deleted_count = result if isinstance(result, int) else 0
        logger.info(f"✅ Cleaned up {deleted_count} old analytics events")
        return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
    
    def cleanup_old_performance_logs(self) -> Dict[str, Any]:
        """Clean up old performance logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.log_retention_days)
        result = db_optimizer.execute_query(
            "DELETE FROM query_performance_log WHERE timestamp < ?",
            (cutoff_date.isoformat(),), fetch=False
        )
        deleted_count = result if isinstance(result, int) else 0
        logger.info(f"✅ Cleaned up {deleted_count} old performance logs")
        return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired user sessions"""
        now = datetime.utcnow()
        result = db_optimizer.execute_query(
            "DELETE FROM user_sessions WHERE expires_at < ? OR is_valid = 0",
            (now.isoformat(),), fetch=False
        )
        deleted_count = result if isinstance(result, int) else 0
        logger.info(f"✅ Cleaned up {deleted_count} expired sessions")
        return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': now.isoformat()}
    
    def run_manual_cleanup(self, cleanup_type: str = 'all') -> Dict[str, Any]:
        """Run cleanup manually"""
        results = {}
        
        if cleanup_type == 'all' or cleanup_type == 'jobs':
            results['email_jobs'] = self.cleanup_old_email_jobs()
        
        if cleanup_type == 'all' or cleanup_type == 'sync':
            results['sync_records'] = self.cleanup_old_sync_records()
        
        if cleanup_type == 'all' or cleanup_type == 'analytics':
            results['analytics'] = self.cleanup_old_analytics_events()
        
        if cleanup_type == 'all' or cleanup_type == 'performance':
            results['performance'] = self.cleanup_old_performance_logs()
        
        if cleanup_type == 'all' or cleanup_type == 'sessions':
            results['sessions'] = self.cleanup_expired_sessions()
        
        return results

# Global cleanup scheduler instance
cleanup_scheduler = CleanupScheduler()

