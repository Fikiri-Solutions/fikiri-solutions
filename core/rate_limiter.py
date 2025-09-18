"""
Rate Limiting and Concurrency Controls
Per-user API rate limits and automation throttling
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import threading
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 100  # Max requests in 5 minutes
    automation_actions_per_5min: int = 50
    automation_actions_per_hour: int = 200
    auto_replies_per_contact_per_day: int = 2

class RateLimiter:
    """Rate limiter with sliding window and per-user tracking"""
    
    def __init__(self, db_optimizer):
        self.db_optimizer = db_optimizer
        self.config = RateLimitConfig()
        self._initialize_rate_limit_tables()
        
        # In-memory tracking for performance
        self.user_requests = defaultdict(list)  # user_id -> [timestamps]
        self.user_automations = defaultdict(list)  # user_id -> [timestamps]
        self.lock = threading.RLock()
    
    def _initialize_rate_limit_tables(self):
        """Initialize rate limiting tracking tables"""
        try:
            # API rate limiting table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS api_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Automation rate limiting table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS automation_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    contact_email TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Create indexes
            indexes = [
                ("idx_api_rate_user_endpoint", "api_rate_limits", ["user_id", "endpoint"]),
                ("idx_api_rate_window_start", "api_rate_limits", ["window_start"]),
                ("idx_automation_rate_user_contact", "automation_rate_limits", ["user_id", "contact_email"]),
                ("idx_automation_rate_window_start", "automation_rate_limits", ["window_start"])
            ]
            
            for index_name, table, columns in indexes:
                try:
                    self.db_optimizer.execute_query(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)})",
                        fetch=False
                    )
                except Exception as e:
                    logger.warning(f"Failed to create index {index_name}: {e}")
            
            logger.info("Rate limiting tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting tables: {e}")
            raise
    
    def check_api_rate_limit(self, user_id: int, endpoint: str) -> Dict[str, Any]:
        """Check if API request is within rate limits"""
        try:
            with self.lock:
                current_time = time.time()
                
                # Clean old entries from memory
                self._cleanup_user_requests(user_id, current_time)
                
                # Check in-memory rate limit (faster)
                user_requests = self.user_requests[user_id]
                
                # Count requests in last minute
                minute_ago = current_time - 60
                requests_last_minute = len([t for t in user_requests if t > minute_ago])
                
                # Count requests in last hour
                hour_ago = current_time - 3600
                requests_last_hour = len([t for t in user_requests if t > hour_ago])
                
                # Count requests in last 5 minutes (burst limit)
                five_min_ago = current_time - 300
                requests_last_5min = len([t for t in user_requests if t > five_min_ago])
                
                # Check limits
                if requests_last_minute >= self.config.requests_per_minute:
                    return {
                        'allowed': False,
                        'reason': 'minute_limit',
                        'limit': self.config.requests_per_minute,
                        'current': requests_last_minute,
                        'retry_after': 60
                    }
                
                if requests_last_hour >= self.config.requests_per_hour:
                    return {
                        'allowed': False,
                        'reason': 'hour_limit',
                        'limit': self.config.requests_per_hour,
                        'current': requests_last_hour,
                        'retry_after': 3600
                    }
                
                if requests_last_5min >= self.config.burst_limit:
                    return {
                        'allowed': False,
                        'reason': 'burst_limit',
                        'limit': self.config.burst_limit,
                        'current': requests_last_5min,
                        'retry_after': 300
                    }
                
                # Record this request
                self.user_requests[user_id].append(current_time)
                
                # Also record in database for persistence
                self._record_api_request(user_id, endpoint)
                
                return {
                    'allowed': True,
                    'reason': 'within_limits',
                    'limits': {
                        'per_minute': self.config.requests_per_minute,
                        'per_hour': self.config.requests_per_hour,
                        'burst_5min': self.config.burst_limit
                    },
                    'current': {
                        'last_minute': requests_last_minute + 1,
                        'last_hour': requests_last_hour + 1,
                        'last_5min': requests_last_5min + 1
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to check API rate limit: {e}")
            return {
                'allowed': False,
                'reason': 'error',
                'error': str(e)
            }
    
    def check_automation_rate_limit(self, user_id: int, contact_email: str, 
                                  action_type: str) -> Dict[str, Any]:
        """Check if automation action is within rate limits"""
        try:
            with self.lock:
                current_time = time.time()
                
                # Clean old entries from memory
                self._cleanup_user_automations(user_id, current_time)
                
                # Check in-memory automation limits
                user_automations = self.user_automations[user_id]
                
                # Count automation actions in last 5 minutes
                five_min_ago = current_time - 300
                actions_last_5min = len([t for t in user_automations if t > five_min_ago])
                
                # Count automation actions in last hour
                hour_ago = current_time - 3600
                actions_last_hour = len([t for t in user_automations if t > hour_ago])
                
                # Check general automation limits
                if actions_last_5min >= self.config.automation_actions_per_5min:
                    return {
                        'allowed': False,
                        'reason': 'automation_5min_limit',
                        'limit': self.config.automation_actions_per_5min,
                        'current': actions_last_5min,
                        'retry_after': 300
                    }
                
                if actions_last_hour >= self.config.automation_actions_per_hour:
                    return {
                        'allowed': False,
                        'reason': 'automation_hour_limit',
                        'limit': self.config.automation_actions_per_hour,
                        'current': actions_last_hour,
                        'retry_after': 3600
                    }
                
                # Check per-contact limits for auto-replies
                if action_type == 'auto_reply':
                    contact_actions = self._get_contact_action_count(user_id, contact_email, action_type)
                    if contact_actions >= self.config.auto_replies_per_contact_per_day:
                        return {
                            'allowed': False,
                            'reason': 'contact_daily_limit',
                            'limit': self.config.auto_replies_per_contact_per_day,
                            'current': contact_actions,
                            'retry_after': 86400  # 24 hours
                        }
                
                # Record this automation action
                self.user_automations[user_id].append(current_time)
                
                # Also record in database
                self._record_automation_action(user_id, contact_email, action_type)
                
                return {
                    'allowed': True,
                    'reason': 'within_limits',
                    'limits': {
                        'per_5min': self.config.automation_actions_per_5min,
                        'per_hour': self.config.automation_actions_per_hour,
                        'per_contact_per_day': self.config.auto_replies_per_contact_per_day
                    },
                    'current': {
                        'last_5min': actions_last_5min + 1,
                        'last_hour': actions_last_hour + 1,
                        'contact_today': contact_actions if action_type == 'auto_reply' else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to check automation rate limit: {e}")
            return {
                'allowed': False,
                'reason': 'error',
                'error': str(e)
            }
    
    def _cleanup_user_requests(self, user_id: int, current_time: float):
        """Clean up old request timestamps from memory"""
        try:
            hour_ago = current_time - 3600
            self.user_requests[user_id] = [
                t for t in self.user_requests[user_id] if t > hour_ago
            ]
        except Exception as e:
            logger.error(f"Failed to cleanup user requests: {e}")
    
    def _cleanup_user_automations(self, user_id: int, current_time: float):
        """Clean up old automation timestamps from memory"""
        try:
            hour_ago = current_time - 3600
            self.user_automations[user_id] = [
                t for t in self.user_automations[user_id] if t > hour_ago
            ]
        except Exception as e:
            logger.error(f"Failed to cleanup user automations: {e}")
    
    def _record_api_request(self, user_id: int, endpoint: str):
        """Record API request in database"""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO api_rate_limits (user_id, endpoint, request_count)
                VALUES (?, ?, 1)
                """,
                (user_id, endpoint),
                fetch=False
            )
        except Exception as e:
            logger.warning(f"Failed to record API request: {e}")
    
    def _record_automation_action(self, user_id: int, contact_email: str, action_type: str):
        """Record automation action in database"""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO automation_rate_limits (user_id, contact_email, action_type, action_count)
                VALUES (?, ?, ?, 1)
                """,
                (user_id, contact_email, action_type),
                fetch=False
            )
        except Exception as e:
            logger.warning(f"Failed to record automation action: {e}")
    
    def _get_contact_action_count(self, user_id: int, contact_email: str, action_type: str) -> int:
        """Get action count for specific contact today"""
        try:
            result = self.db_optimizer.execute_query(
                """
                SELECT SUM(action_count) FROM automation_rate_limits 
                WHERE user_id = ? AND contact_email = ? AND action_type = ? 
                AND DATE(created_at) = DATE('now')
                """,
                (user_id, contact_email, action_type)
            )
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            logger.error(f"Failed to get contact action count: {e}")
            return 0
    
    def get_rate_limit_status(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive rate limit status for user"""
        try:
            with self.lock:
                current_time = time.time()
                
                # Clean up old entries
                self._cleanup_user_requests(user_id, current_time)
                self._cleanup_user_automations(user_id, current_time)
                
                # Get current counts
                user_requests = self.user_requests[user_id]
                user_automations = self.user_automations[user_id]
                
                # Calculate current usage
                minute_ago = current_time - 60
                hour_ago = current_time - 3600
                five_min_ago = current_time - 300
                
                api_usage = {
                    'last_minute': len([t for t in user_requests if t > minute_ago]),
                    'last_hour': len([t for t in user_requests if t > hour_ago]),
                    'last_5min': len([t for t in user_requests if t > five_min_ago])
                }
                
                automation_usage = {
                    'last_5min': len([t for t in user_automations if t > five_min_ago]),
                    'last_hour': len([t for t in user_automations if t > hour_ago])
                }
                
                return {
                    'success': True,
                    'data': {
                        'api_limits': {
                            'per_minute': self.config.requests_per_minute,
                            'per_hour': self.config.requests_per_hour,
                            'burst_5min': self.config.burst_limit
                        },
                        'automation_limits': {
                            'per_5min': self.config.automation_actions_per_5min,
                            'per_hour': self.config.automation_actions_per_hour,
                            'per_contact_per_day': self.config.auto_replies_per_contact_per_day
                        },
                        'current_usage': {
                            'api': api_usage,
                            'automation': automation_usage
                        },
                        'status': 'active'
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'STATUS_CHECK_FAILED'
            }
    
    def reset_user_limits(self, user_id: int) -> Dict[str, Any]:
        """Reset rate limits for a user (admin function)"""
        try:
            with self.lock:
                # Clear in-memory tracking
                self.user_requests[user_id] = []
                self.user_automations[user_id] = []
                
                # Clear database tracking
                self.db_optimizer.execute_query(
                    "DELETE FROM api_rate_limits WHERE user_id = ?",
                    (user_id,),
                    fetch=False
                )
                
                self.db_optimizer.execute_query(
                    "DELETE FROM automation_rate_limits WHERE user_id = ?",
                    (user_id,),
                    fetch=False
                )
                
                logger.info(f"Reset rate limits for user {user_id}")
                return {
                    'success': True,
                    'message': 'Rate limits reset successfully'
                }
                
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'RESET_FAILED'
            }

# Initialize rate limiter
rate_limiter = RateLimiter(db_optimizer)
