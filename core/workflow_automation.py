#!/usr/bin/env python3
"""
Fikiri Solutions - Workflow Automation Service
Handles automated workflows and scheduling.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

@dataclass
class WorkflowJob:
    """Workflow job definition."""
    id: str
    name: str
    job_type: str
    function: Callable
    interval: int  # seconds
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.next_run is None:
            self.next_run = datetime.now() + timedelta(seconds=self.interval)

class WorkflowManager:
    """Manages automated workflows and scheduling."""
    
    def __init__(self):
        """Initialize workflow manager."""
        self.jobs: Dict[str, WorkflowJob] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> bool:
        """Start the workflow scheduler."""
        if self.running:
            self.logger.warning("⚠️ Scheduler is already running")
            return True
        
        try:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            self.logger.info("🚀 Workflow scheduler started")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to start scheduler: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop the workflow scheduler."""
        if not self.running:
            self.logger.warning("⚠️ Scheduler is not running")
            return True
        
        try:
            self.running = False
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5)
            self.logger.info("⏹️ Workflow scheduler stopped")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to stop scheduler: {e}")
            return False
    
    def add_job(self, name: str, job_type: str, function: Callable, 
                interval: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new workflow job."""
        try:
            job_id = str(uuid.uuid4())
            job = WorkflowJob(
                id=job_id,
                name=name,
                job_type=job_type,
                function=function,
                interval=interval,
                metadata=metadata or {}
            )
            
            self.jobs[job_id] = job
            self.logger.info(f"✅ Added workflow job: {name} ({job_type})")
            return job_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add job: {e}")
            return ""
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a workflow job."""
        if job_id not in self.jobs:
            return False
        
        try:
            job_name = self.jobs[job_id].name
            del self.jobs[job_id]
            self.logger.info(f"🗑️ Removed workflow job: {job_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to remove job: {e}")
            return False
    
    def enable_job(self, job_id: str) -> bool:
        """Enable a workflow job."""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].enabled = True
        self.logger.info(f"✅ Enabled workflow job: {self.jobs[job_id].name}")
        return True
    
    def disable_job(self, job_id: str) -> bool:
        """Disable a workflow job."""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].enabled = False
        self.logger.info(f"⏸️ Disabled workflow job: {self.jobs[job_id].name}")
        return True
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all workflow jobs."""
        jobs_info = []
        for job in self.jobs.values():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'type': job.job_type,
                'interval': job.interval,
                'enabled': job.enabled,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'metadata': job.metadata
            })
        return jobs_info
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        self.logger.info("🔄 Scheduler loop started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                for job in self.jobs.values():
                    if not job.enabled:
                        continue
                    
                    if job.next_run and current_time >= job.next_run:
                        self._execute_job(job)
                
                # Sleep for 1 second before next check
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in scheduler loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _execute_job(self, job: WorkflowJob) -> None:
        """Execute a workflow job."""
        try:
            self.logger.info(f"🔄 Executing job: {job.name}")
            
            # Update job timing
            job.last_run = datetime.now()
            job.next_run = job.last_run + timedelta(seconds=job.interval)
            
            # Execute the job function
            job.function(**job.metadata)
            
            self.logger.info(f"✅ Completed job: {job.name}")
            
        except Exception as e:
            self.logger.error(f"❌ Job execution failed: {job.name} - {e}")
            # Still update timing to prevent immediate retry
            job.last_run = datetime.now()
            job.next_run = job.last_run + timedelta(seconds=job.interval)
    
    def schedule_email_processing(self, query: str = "is:unread", 
                                 interval_minutes: int = 30, 
                                 max_emails: int = 10, 
                                 auto_reply: bool = False) -> str:
        """Schedule automated email processing."""
        def email_processing_job():
            # This would integrate with Gmail service
            self.logger.info(f"📧 Processing emails: {query} (max: {max_emails})")
            # In a real implementation, this would call Gmail service
        
        return self.add_job(
            name=f"Email Processing - {query}",
            job_type="email_processing",
            function=email_processing_job,
            interval=interval_minutes * 60,
            metadata={
                'query': query,
                'max_emails': max_emails,
                'auto_reply': auto_reply
            }
        )
    
    def schedule_crm_followups(self, stage_filter: Optional[str] = None,
                              interval_hours: int = 24,
                              send: bool = False) -> str:
        """Schedule CRM follow-up processing."""
        def crm_followup_job():
            # This would integrate with CRM service
            self.logger.info(f"📋 Processing CRM follow-ups: {stage_filter or 'all'}")
            # In a real implementation, this would call CRM service
        
        return self.add_job(
            name=f"CRM Follow-ups - {stage_filter or 'all'}",
            job_type="crm_followups",
            function=crm_followup_job,
            interval=interval_hours * 3600,
            metadata={
                'stage_filter': stage_filter,
                'send': send
            }
        )
    
    def schedule_lead_ingestion(self, source: str = "webhook",
                               interval_minutes: int = 15) -> str:
        """Schedule lead ingestion."""
        def lead_ingestion_job():
            # This would integrate with lead sources
            self.logger.info(f"📥 Ingesting leads from: {source}")
            # In a real implementation, this would call lead ingestion
        
        return self.add_job(
            name=f"Lead Ingestion - {source}",
            job_type="lead_ingestion",
            function=lead_ingestion_job,
            interval=interval_minutes * 60,
            metadata={'source': source}
        )
    
    def schedule_business_hours_workflow(self, workflow_type: str = "email_processing") -> str:
        """Schedule business hours workflow."""
        def business_hours_job():
            # This would run during business hours only
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 18:  # 9 AM to 6 PM
                self.logger.info(f"🕒 Business hours workflow: {workflow_type}")
                # In a real implementation, this would call the appropriate service
        
        return self.add_job(
            name=f"Business Hours - {workflow_type}",
            job_type="business_hours",
            function=business_hours_job,
            interval=3600,  # Every hour
            metadata={'workflow_type': workflow_type}
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get workflow manager status."""
        enabled_jobs = len([job for job in self.jobs.values() if job.enabled])
        total_jobs = len(self.jobs)
        
        return {
            'running': self.running,
            'total_jobs': total_jobs,
            'enabled_jobs': enabled_jobs,
            'disabled_jobs': total_jobs - enabled_jobs,
            'scheduler_thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }

# Global workflow manager instance
workflow_manager = WorkflowManager()
