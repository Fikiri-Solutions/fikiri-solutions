#!/usr/bin/env python3
"""
Monitoring and Health Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify
import os
import logging
from datetime import datetime

# Import monitoring modules
from core.monitoring import health_monitor
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.database_optimization import db_optimizer
from core.oauth_token_manager import oauth_token_manager

logger = logging.getLogger(__name__)

# Create monitoring blueprint
monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/api")

@monitoring_bp.route('/health-old')
@handle_api_errors
def api_health_old():
    """Comprehensive health check endpoint for system monitoring."""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'metrics': {
                'uptime': 'operational',
                'active_users': 0,  # Placeholder
                'active_connections': 0,  # Placeholder
                'initialized_services': 3  # Placeholder
            },
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'version': '1.0.0'
        }

        # Database connectivity check
        try:
            db_optimizer.execute_query("SELECT 1")
            health_status['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': 10,  # Placeholder
                'error': None
            }
            health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        # Redis connectivity check (REDIS_URL or UPSTASH_* via helper)
        try:
            from core.redis_connection_helper import is_redis_available
            if is_redis_available():
                health_status['checks']['redis'] = {
                    'status': 'healthy',
                    'response_time_ms': 5,
                    'error': None
                }
                health_status['metrics']['initialized_services'] += 1
            else:
                health_status['checks']['redis'] = {
                    'status': 'disabled',
                    'response_time_ms': 0,
                    'error': 'Redis not configured'
                }
        except Exception as e:
            health_status['checks']['redis'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # Gmail OAuth check (sample)
        try:
            health_status['checks']['gmail_auth'] = {
                'status': 'configured' if os.getenv('GOOGLE_CLIENT_ID') else 'not_configured',
                'response_time_ms': 5,
                'error': None
            }
            if os.getenv('GOOGLE_CLIENT_ID'):
                health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['gmail_auth'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # OpenAI API check
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            health_status['checks']['openai'] = {
                'status': 'configured' if openai_key else 'not_configured',
                'response_time_ms': 5,
                'error': None
            }
            if openai_key:
                health_status['metrics']['initialized_services'] += 1
        except Exception as e:
            health_status['checks']['openai'] = {
                'status': 'unhealthy',
                'response_time_ms': 0,
                'error': str(e)
            }

        # Calculate overall health
        unhealthy_checks = sum(1 for check in health_status['checks'].values() 
                             if check['status'] == 'unhealthy')
        
        if unhealthy_checks == 0:
            health_status['status'] = 'healthy'
            health_status['message'] = 'All systems operational'
        elif unhealthy_checks <= 2:
            health_status['status'] = 'degraded'
            health_status['message'] = f'{unhealthy_checks} system(s) experiencing issues'
        else:
            health_status['status'] = 'unhealthy'
            health_status['message'] = f'{unhealthy_checks} system(s) down'

        health_status['metrics']['initialized_services'] = health_status['metrics']['initialized_services']

        return create_success_response(health_status, 'Health check completed')

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return create_error_response("Health check failed", 500, 'HEALTH_CHECK_ERROR')

@monitoring_bp.route('/gmail/status', methods=['GET'])
@handle_api_errors
def gmail_status():
    """Get Gmail connection status"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        result = oauth_token_manager.get_token_status(user_id, "gmail")
        
        if result['success']:
            return create_success_response({
                'connected': True,
                'status': 'active',
                'last_sync': result.get('last_sync'),
                'expires_at': result.get('expires_at'),
                'scope': result.get('scope', [])
            }, 'Gmail connection status retrieved')
        else:
            return create_success_response({
                'connected': False,
                'status': 'not_connected',
                'error': result.get('error', 'No active connection')
            }, 'Gmail connection status retrieved')
            
    except Exception as e:
        logger.error(f"Gmail status error: {e}")
        return create_error_response("Failed to get Gmail status", 500, 'GMAIL_STATUS_ERROR')

@monitoring_bp.route('/email/sync/status', methods=['GET'])
@handle_api_errors
def email_sync_status():
    """Get email synchronization status"""
    try:
        # Try to get user_id from session/JWT first
        user_id = get_current_user_id()
        
        # Fallback: allow user_id from query parameter for development/testing
        if not user_id:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # First, check if Gmail is connected - check gmail_tokens table (where tokens are actually stored)
        gmail_connected = False
        try:
            # Check gmail_tokens table first (where tokens are actually stored)
            gmail_token_check = db_optimizer.execute_query("""
                SELECT access_token_enc, access_token, is_active
                FROM gmail_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if gmail_token_check and len(gmail_token_check) > 0:
                token_row = gmail_token_check[0]
                # Handle both dict and tuple result formats
                if isinstance(token_row, dict):
                    has_token = bool(token_row.get('access_token_enc') or token_row.get('access_token'))
                else:
                    has_token = bool((len(token_row) > 0 and token_row[0]) or (len(token_row) > 1 and token_row[1]))
                
                if has_token:
                    gmail_connected = True
                else:
                    # Fallback to oauth_token_manager
                    from core.oauth_token_manager import oauth_token_manager
                    token_status = oauth_token_manager.get_token_status(user_id, "gmail")
                    gmail_connected = token_status.get('success') and token_status.get('has_token')
            else:
                # No token in gmail_tokens, check oauth_tokens as fallback
                from core.oauth_token_manager import oauth_token_manager
                token_status = oauth_token_manager.get_token_status(user_id, "gmail")
                gmail_connected = token_status.get('success') and token_status.get('has_token')
        except Exception as e:
            logger.warning(f"Could not check Gmail connection status: {e}")

        # If Gmail is not connected, return appropriate status
        if not gmail_connected:
            return create_success_response({
                'sync_status': 'not_connected',
                'last_sync': None,
                'total_emails': 0,
                'syncing': False,
                'gmail_connected': False
            }, 'Gmail not connected')

        # Check if user_sync_status table exists, create if it doesn't
        table_exists = False
        try:
            table_exists = db_optimizer.table_exists('user_sync_status')
        except Exception as table_check_error:
            logger.warning(f"Error checking if user_sync_status table exists: {table_check_error}")
            # Assume table doesn't exist and try to create it
        
        if not table_exists:
            # Create the table if it doesn't exist
            try:
                logger.info("Creating user_sync_status table...")
                db_optimizer.execute_query("""
                    CREATE TABLE IF NOT EXISTS user_sync_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE,
                        last_sync DATETIME,
                        sync_status TEXT DEFAULT 'connected_pending_sync',
                        syncing INTEGER DEFAULT 0,
                        total_emails INTEGER DEFAULT 0,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """, fetch=False)
                db_optimizer.execute_query("""
                    CREATE INDEX IF NOT EXISTS idx_user_sync_status_user_id 
                    ON user_sync_status (user_id)
                """, fetch=False)
                table_exists = True
                logger.info("✅ user_sync_status table created")
            except Exception as create_error:
                logger.warning(f"Could not create user_sync_status table: {create_error}")
        
        if not table_exists:
            # Table doesn't exist yet, but Gmail is connected - return "sync pending"
            return create_success_response({
                'sync_status': 'pending',
                'last_sync': None,
                'total_emails': 0,
                'syncing': False,
                'gmail_connected': True
            }, 'Gmail connected, sync pending')
        
        # Check sync status from database (with timeout protection)
        try:
            sync_data = None
            try:
                sync_data = db_optimizer.execute_query(
                    "SELECT last_sync, sync_status, total_emails FROM user_sync_status WHERE user_id = ?",
                    (user_id,)
                )
            except Exception as query_ex:
                logger.warning(f"Database query error for sync status: {query_ex}")
                # Return default status instead of crashing
                return create_success_response({
                    'sync_status': 'pending',
                    'last_sync': None,
                    'total_emails': 0,
                    'syncing': False,
                    'progress': 0,
                    'emails_synced_this_job': 0,
                    'gmail_connected': True
                }, 'Gmail connected, sync status query failed')
            
            # Get progress from active sync job if syncing
            progress = None
            emails_synced_this_job = 0
            is_syncing = False
            
            if sync_data:
                sync_record = sync_data[0]
                # Handle both dict and tuple result formats
                if isinstance(sync_record, dict):
                    last_sync = sync_record.get('last_sync')
                    sync_status = sync_record.get('sync_status', 'connected_pending_sync')
                    total_emails = sync_record.get('total_emails', 0)
                else:
                    last_sync = sync_record[0] if len(sync_record) > 0 else None
                    sync_status = sync_record[1] if len(sync_record) > 1 else 'connected_pending_sync'
                    total_emails = sync_record[2] if len(sync_record) > 2 else 0
                
                # Determine if syncing is in progress
                is_syncing = sync_status in ['in_progress', 'processing', 'pending']
                
                # Get progress from job (whether syncing or just completed)
                # This ensures we show the final progress even after completion
                if is_syncing or sync_status == 'completed':
                    try:
                        # Check if gmail_sync_jobs table exists first to avoid errors
                        jobs_table_exists = db_optimizer.table_exists('gmail_sync_jobs')
                        logger.debug(f"gmail_sync_jobs table exists: {jobs_table_exists}")
                        if jobs_table_exists:
                            # Query for jobs - include completed if sync just finished
                            # This ensures we get the final progress (100%) when sync completes
                            status_conditions = ['pending', 'processing', 'in_progress']
                            if sync_status == 'completed':
                                status_conditions.append('completed')
                            
                            placeholders = ','.join(['?' for _ in status_conditions])
                            job_data = db_optimizer.execute_query(f"""
                                SELECT progress, emails_synced, status, job_id, created_at, started_at
                                FROM gmail_sync_jobs 
                                WHERE user_id = ? AND status IN ({placeholders})
                                ORDER BY created_at DESC
                                LIMIT 1
                            """, (user_id, *status_conditions))
                            
                            logger.debug(f"Job query returned {len(job_data) if job_data else 0} results")
                            
                            # If no job found, check for most recent job regardless of status
                            if not job_data or len(job_data) == 0:
                                job_data = db_optimizer.execute_query("""
                                    SELECT progress, emails_synced, status, job_id, created_at, started_at
                                    FROM gmail_sync_jobs 
                                    WHERE user_id = ?
                                    ORDER BY created_at DESC
                                    LIMIT 1
                                """, (user_id,))
                                logger.debug(f"Recent job query returned {len(job_data) if job_data else 0} results")
                            
                            if job_data and len(job_data) > 0:
                                job = job_data[0]
                                if isinstance(job, dict):
                                    progress = job.get('progress', 0) or 0
                                    emails_synced_this_job = job.get('emails_synced', 0) or 0
                                    job_status = job.get('status', '')
                                    job_id_found = job.get('job_id', '')
                                else:
                                    progress = job[0] if len(job) > 0 and job[0] is not None else 0
                                    emails_synced_this_job = job[1] if len(job) > 1 and job[1] is not None else 0
                                    job_status = job[2] if len(job) > 2 else ''
                                    job_id_found = job[3] if len(job) > 3 else ''
                                
                                logger.info(f"Found sync job {job_id_found}: progress={progress}%, emails={emails_synced_this_job}, status={job_status}")
                                
                                # Use job progress based on status
                                if job_status in ('processing', 'in_progress', 'pending'):
                                    # Use the actual progress from the job, but ensure it's at least 1% if job is active
                                    if progress == 0:
                                        progress = 1  # Show 1% minimum for active jobs
                                elif job_status == 'completed':
                                    # Job completed - use 100% progress or the actual final progress
                                    if progress == 0:
                                        progress = 100  # Completed jobs should show 100%
                                    # Keep the actual progress value if it's > 0
                                else:
                                    # Job failed or other status
                                    logger.debug(f"Job {job_id_found} status is {job_status}, progress={progress}")
                                    # Keep progress as is (might be partial progress before failure)
                        
                        # If no progress yet but syncing, try to estimate from synced emails
                        # But don't override progress if job is completed (should be 100%)
                        if (progress is None or progress == 0) and is_syncing:
                            # Try to estimate progress from recent email activity
                            try:
                                # Check if emails are being synced by looking at recent synced_emails
                                recent_sync_check = db_optimizer.execute_query("""
                                    SELECT COUNT(*) as count 
                                    FROM synced_emails 
                                    WHERE user_id = ? AND created_at > datetime('now', '-5 minutes')
                                """, (user_id,))
                                if recent_sync_check and len(recent_sync_check) > 0:
                                    recent_count = recent_sync_check[0].get('count', 0) if isinstance(recent_sync_check[0], dict) else recent_sync_check[0][0] if len(recent_sync_check[0]) > 0 else 0
                                    if recent_count > 0:
                                        # Estimate progress based on recent activity (rough estimate)
                                        progress = min(10 + (recent_count * 2), 95)  # Cap at 95% until complete
                                        logger.debug(f"Estimated progress from recent sync activity: {progress}%")
                            except Exception as estimate_error:
                                logger.debug(f"Could not estimate progress: {estimate_error}")
                            
                            # If still no progress, show minimal progress to indicate activity
                            if progress is None or progress == 0:
                                progress = 1  # Show 1% to indicate activity started
                    except Exception as job_error:
                        logger.warning(f"Could not get sync job progress: {job_error}")
                        import traceback
                        logger.debug(f"Job progress error traceback: {traceback.format_exc()}")
                        # If syncing but can't get progress, show minimal progress
                        if is_syncing:
                            progress = 1
                
                # Ensure progress is always a number, never None
                # If sync is completed, show 100% progress (or the actual final progress if available)
                if sync_status == 'completed' and (progress is None or progress == 0):
                    final_progress = 100  # Completed syncs should show 100%
                elif progress is not None:
                    final_progress = progress
                elif is_syncing:
                    final_progress = 1  # Show 1% minimum when syncing
                else:
                    final_progress = 0
                
                logger.debug(f"Returning sync status: progress={final_progress}%, syncing={is_syncing}, status={sync_status}, job_progress={progress}")
                
                return create_success_response({
                    'last_sync': last_sync,
                    'sync_status': sync_status,
                    'total_emails': total_emails,
                    'syncing': is_syncing,
                    'progress': final_progress,  # 0-100 percentage
                    'emails_synced_this_job': emails_synced_this_job if emails_synced_this_job is not None else 0,
                    'gmail_connected': True
                }, 'Email sync status retrieved')
            else:
                # Gmail is connected but no sync record yet - check if emails exist
                # If emails exist, sync has happened but status wasn't recorded
                try:
                    email_count_result = db_optimizer.execute_query(
                        "SELECT COUNT(*) as total FROM synced_emails WHERE user_id = ?",
                        (user_id,)
                    )
                    total_emails = email_count_result[0]['total'] if email_count_result and email_count_result[0] else 0
                    
                    if total_emails > 0:
                        # Emails exist but no status record - create/update status
                        try:
                            # Get the most recent email date as last_sync
                            last_email_result = db_optimizer.execute_query(
                                "SELECT MAX(date) as last_date FROM synced_emails WHERE user_id = ?",
                                (user_id,)
                            )
                            last_sync_date = last_email_result[0]['last_date'] if last_email_result and last_email_result[0] else None
                            
                            # Update user_sync_status
                            db_optimizer.execute_query("""
                                INSERT OR REPLACE INTO user_sync_status 
                                (user_id, last_sync, sync_status, syncing, total_emails, updated_at)
                                VALUES (?, ?, 'completed', 0, ?, datetime('now'))
                            """, (user_id, last_sync_date, total_emails), fetch=False)
                            
                            return create_success_response({
                                'last_sync': last_sync_date,
                                'sync_status': 'completed',
                                'total_emails': total_emails,
                                'syncing': False,
                                'gmail_connected': True
                            }, 'Email sync status retrieved (inferred from existing emails)')
                        except Exception as update_error:
                            logger.warning(f"Could not update inferred sync status: {update_error}")
                            # Return inferred status anyway
                            return create_success_response({
                                'last_sync': None,
                                'sync_status': 'completed',
                                'total_emails': total_emails,
                                'syncing': False,
                                'gmail_connected': True
                            }, 'Gmail connected, emails found but status not recorded')
                    
                    # No emails and no status - show as pending
                    return create_success_response({
                        'sync_status': 'pending',
                        'last_sync': None,
                        'total_emails': 0,
                        'syncing': False,
                        'gmail_connected': True
                    }, 'Gmail connected, sync pending')
                except Exception as check_error:
                    logger.warning(f"Error checking for existing emails: {check_error}")
                    return create_success_response({
                        'sync_status': 'pending',
                        'last_sync': None,
                        'total_emails': 0,
                        'syncing': False,
                        'gmail_connected': True
                    }, 'Gmail connected, sync pending')
        except Exception as query_error:
            # Query failed (table might not exist or other DB error)
            logger.warning(f"Query failed for sync status: {query_error}")
            return create_success_response({
                'sync_status': 'pending',
                'last_sync': None,
                'total_emails': 0,
                'syncing': False,
                'gmail_connected': True
            }, 'Gmail connected, sync status unavailable')
            
    except Exception as e:
        logger.error(f"Email sync status error: {e}")
        import traceback
        logger.error(f"Email sync status traceback: {traceback.format_exc()}")
        # Return a default response instead of error to prevent frontend crashes
        # Always return a response, never let it hang
        try:
            return create_success_response({
                'sync_status': 'never_synced',
                'last_sync': None,
                'total_emails': 0,
                'syncing': False,
                'progress': 0,
                'emails_synced_this_job': 0,
                'gmail_connected': False,
                'error': 'Unable to retrieve sync status'
            }, 'Sync status unavailable')
        except Exception as response_error:
            # Last resort: return a simple JSON response
            logger.error(f"Failed to create error response: {response_error}")
            return jsonify({
                'success': True,
                'data': {
                    'sync_status': 'never_synced',
                    'last_sync': None,
                    'total_emails': 0,
                    'syncing': False,
                    'progress': 0,
                    'emails_synced_this_job': 0,
                    'gmail_connected': False,
                    'error': 'Unable to retrieve sync status'
                },
                'message': 'Sync status unavailable'
            }), 200

@monitoring_bp.route('/rate-limits/status', methods=['GET'])
@handle_api_errors
def rate_limits_status():
    """Get rate limiting status for current user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        from core.rate_limiter import enhanced_rate_limiter
        
        # Get rate limit status
        rate_limit_status = enhanced_rate_limiter.get_user_limits(user_id)
        
        return create_success_response({
            'user_id': user_id,
            'limits': rate_limit_status,
            'current_usage': enhanced_rate_limiter.get_current_usage(user_id),
            'reset_time': enhanced_rate_limiter.get_reset_time(user_id)
        }, 'Rate limits status retrieved')
        
    except Exception as e:
        logger.error(f"Rate limits status error: {e}")
        return create_error_response("Failed to get rate limits status", 500, 'RATE_LIMITS_STATUS_ERROR')

@monitoring_bp.route('/system/metrics', methods=['GET'])
@handle_api_errors
def system_metrics():
    """Get system performance metrics"""
    try:
        from core.performance_monitor import performance_monitor
        
        metrics = performance_monitor.get_system_metrics()
        
        return create_success_response(metrics, 'System metrics retrieved')
        
    except Exception as e:
        logger.error(f"System metrics error: {e}")
        return create_error_response("Failed to get system metrics", 500, 'SYSTEM_METRICS_ERROR')

@monitoring_bp.route('/alerts', methods=['GET'])
@handle_api_errors
def get_alerts():
    """Get system alerts and notifications"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Get alerts from database for specific user or global alerts
        alerts_data = db_optimizer.execute_query(
            """
            SELECT id, alert_type, alert_level, message, timestamp, resolved 
            FROM system_alerts 
            WHERE user_id = ? OR user_id IS NULL 
            ORDER BY timestamp DESC 
            LIMIT 100
            """,
            (user_id,)
        )
        
        alerts = []
        if alerts_data:
            alerts = [{
                'id': row['id'],
                'type': row['alert_type'],
                'level': row['alert_level'],
                'message': row['message'],
                'timestamp': row['timestamp'],
                'resolved': row['resolved']
            } for row in alerts_data]
        
        return create_success_response({'alerts': alerts}, 'System alerts retrieved')
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return create_error_response("Failed to get alerts", 500, 'ALERTS_ERROR')
