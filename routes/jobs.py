#!/usr/bin/env python3
"""
Job Status and Management Routes
Endpoints for checking background job status and managing job queues
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, Optional

from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.redis_queues import (
    get_email_queue, get_ai_queue, get_crm_queue,
    email_queue, ai_queue, crm_queue
)

logger = logging.getLogger(__name__)

# Create jobs blueprint
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

@jobs_bp.route('/<job_id>', methods=['GET'])
@handle_api_errors
def get_job_status(job_id: str):
    """Get status of a background job"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Try to find job in any queue
        job = None
        queue_name = None
        
        for queue, name in [(email_queue, 'email'), (ai_queue, 'ai'), (crm_queue, 'crm')]:
            if queue.is_connected():
                job = queue.get_job_status(job_id)
                if job:
                    queue_name = name
                    break
        
        if not job:
            # Check Gmail sync jobs table
            try:
                from core.database_optimization import db_optimizer
                sync_job = db_optimizer.execute_query("""
                    SELECT job_id, user_id, status, progress, emails_synced, contacts_found, 
                           leads_identified, created_at, started_at, completed_at, error_message
                    FROM gmail_sync_jobs 
                    WHERE job_id = ?
                """, (job_id,))
                
                if sync_job and len(sync_job) > 0:
                    job_data = sync_job[0]
                    # Verify user owns this job
                    if job_data['user_id'] != user_id:
                        return create_error_response("Job not found", 404, 'JOB_NOT_FOUND')
                    
                    return create_success_response({
                        'job_id': job_data['job_id'],
                        'status': job_data['status'],
                        'progress': job_data['progress'],
                        'emails_synced': job_data['emails_synced'],
                        'contacts_found': job_data['contacts_found'],
                        'leads_identified': job_data['leads_identified'],
                        'created_at': job_data['created_at'],
                        'started_at': job_data['started_at'],
                        'completed_at': job_data['completed_at'],
                        'error': job_data['error_message'],
                        'queue': 'gmail_sync'
                    }, 'Job status retrieved')
            except Exception as e:
                logger.warning(f"Error checking Gmail sync jobs: {e}")
        
        if not job:
            return create_error_response("Job not found", 404, 'JOB_NOT_FOUND')
        
        # Convert Job dataclass to dict
        job_dict = {
            'job_id': job.id,
            'task': job.task,
            'status': job.status.value if hasattr(job.status, 'value') else str(job.status),
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'retry_count': job.retry_count,
            'max_retries': job.max_retries,
            'error': job.error,
            'queue': queue_name
        }
        
        # Include result if completed
        if job.status.value == 'completed' and queue_name:
            queue = {'email': email_queue, 'ai': ai_queue, 'crm': crm_queue}[queue_name]
            result = queue.get_job_result(job_id)
            if result:
                job_dict['result'] = result
        
        return create_success_response(job_dict, 'Job status retrieved')
        
    except Exception as e:
        logger.error(f"Get job status error: {e}")
        return create_error_response("Failed to get job status", 500, 'JOB_STATUS_ERROR')

@jobs_bp.route('/queue/<queue_name>/stats', methods=['GET'])
@handle_api_errors
def get_queue_stats(queue_name: str):
    """Get statistics for a job queue"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Map queue names to queue instances
        queue_map = {
            'email': email_queue,
            'ai': ai_queue,
            'crm': crm_queue,
            'gmail_sync': email_queue  # Gmail sync uses email queue
        }
        
        if queue_name not in queue_map:
            return create_error_response(f"Unknown queue: {queue_name}", 400, 'INVALID_QUEUE')
        
        queue = queue_map[queue_name]
        
        if not queue.is_connected():
            return create_error_response("Queue not available", 503, 'QUEUE_UNAVAILABLE')
        
        stats = queue.get_queue_stats()
        
        return create_success_response({
            'queue': queue_name,
            'stats': stats
        }, 'Queue statistics retrieved')
        
    except Exception as e:
        logger.error(f"Get queue stats error: {e}")
        return create_error_response("Failed to get queue statistics", 500, 'QUEUE_STATS_ERROR')

@jobs_bp.route('/user/<user_id>/recent', methods=['GET'])
@handle_api_errors
def get_user_recent_jobs(user_id: int):
    """Get recent jobs for a user"""
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Users can only see their own jobs
        if int(user_id) != current_user_id:
            return create_error_response("Unauthorized", 403, 'UNAUTHORIZED')
        
        # Get recent Gmail sync jobs
        try:
            from core.database_optimization import db_optimizer
            recent_jobs = db_optimizer.execute_query("""
                SELECT job_id, status, progress, emails_synced, created_at, completed_at, error_message
                FROM gmail_sync_jobs 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (user_id,))
            
            jobs = []
            if recent_jobs:
                jobs = [{
                    'job_id': row['job_id'],
                    'status': row['status'],
                    'progress': row['progress'],
                    'emails_synced': row['emails_synced'],
                    'created_at': row['created_at'],
                    'completed_at': row['completed_at'],
                    'error': row['error_message'],
                    'type': 'gmail_sync'
                } for row in recent_jobs]
            
            return create_success_response({
                'user_id': user_id,
                'jobs': jobs,
                'count': len(jobs)
            }, 'Recent jobs retrieved')
            
        except Exception as e:
            logger.error(f"Error fetching recent jobs: {e}")
            return create_error_response("Failed to get recent jobs", 500, 'RECENT_JOBS_ERROR')
        
    except Exception as e:
        logger.error(f"Get user recent jobs error: {e}")
        return create_error_response("Failed to get recent jobs", 500, 'RECENT_JOBS_ERROR')
