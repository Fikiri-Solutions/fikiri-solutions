"""
Automation Safety Controls
Global kill-switch and safety mechanisms for production automation
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class AutomationSafetyConfig:
    """Safety configuration for automation rules"""
    global_kill_switch: bool = False
    max_auto_replies_per_contact_per_day: int = 2
    max_actions_per_user_per_5min: int = 50
    max_actions_per_user_per_hour: int = 200
    dry_run_mode: bool = True  # Default to safe mode
    oauth_failure_threshold: int = 3
    oauth_failure_window_minutes: int = 15

class AutomationSafetyManager:
    """Manages automation safety controls and rate limiting"""
    
    def __init__(self, db_optimizer):
        self.db_optimizer = db_optimizer
        self.config = AutomationSafetyConfig()
        self._initialize_safety_tables()
    
    def _initialize_safety_tables(self):
        """Initialize safety tracking tables"""
        try:
            # Automation safety config table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS automation_safety_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    global_kill_switch BOOLEAN DEFAULT FALSE,
                    max_auto_replies_per_contact_per_day INTEGER DEFAULT 2,
                    max_actions_per_user_per_5min INTEGER DEFAULT 50,
                    max_actions_per_user_per_hour INTEGER DEFAULT 200,
                    dry_run_mode BOOLEAN DEFAULT TRUE,
                    oauth_failure_threshold INTEGER DEFAULT 3,
                    oauth_failure_window_minutes INTEGER DEFAULT 15,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Automation action tracking table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS automation_action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rule_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    target_contact TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'pending',  -- 'pending', 'completed', 'failed', 'throttled'
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # OAuth failure tracking table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS oauth_failure_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    failure_type TEXT NOT NULL,  -- 'refresh_failed', 'token_expired', 'revoked'
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Create indexes for performance
            indexes = [
                ("idx_automation_action_user_id", "automation_action_log", ["user_id"]),
                ("idx_automation_action_created_at", "automation_action_log", ["created_at"]),
                ("idx_automation_action_idempotency", "automation_action_log", ["idempotency_key"]),
                ("idx_oauth_failure_user_id", "oauth_failure_log", ["user_id"]),
                ("idx_oauth_failure_created_at", "oauth_failure_log", ["created_at"]),
            ]
            
            for index_name, table, columns in indexes:
                try:
                    self.db_optimizer.execute_query(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)})",
                        fetch=False
                    )
                except Exception as e:
                    logger.warning(f"Failed to create index {index_name}: {e}")
            
            logger.info("Automation safety tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize safety tables: {e}")
            raise
    
    def is_global_kill_switch_enabled(self) -> bool:
        """Check if global kill-switch is enabled"""
        try:
            result = self.db_optimizer.execute_query(
                "SELECT global_kill_switch FROM automation_safety_config WHERE user_id IS NULL LIMIT 1"
            )
            if result:
                return bool(result[0][0])
            return False
        except Exception as e:
            logger.error(f"Failed to check global kill-switch: {e}")
            return True  # Fail safe - assume kill-switch is on
    
    def toggle_global_kill_switch(self, enabled: bool) -> Dict[str, Any]:
        """Toggle global automation kill-switch"""
        try:
            # Update or insert global config
            self.db_optimizer.execute_query(
                """
                INSERT OR REPLACE INTO automation_safety_config 
                (user_id, global_kill_switch, updated_at)
                VALUES (NULL, ?, CURRENT_TIMESTAMP)
                """,
                (enabled,),
                fetch=False
            )
            
            logger.info(f"Global kill-switch {'enabled' if enabled else 'disabled'}")
            return {
                'success': True,
                'kill_switch_enabled': enabled,
                'message': f"Global kill-switch {'enabled' if enabled else 'disabled'}"
            }
        except Exception as e:
            logger.error(f"Failed to toggle global kill-switch: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'KILL_SWITCH_TOGGLE_FAILED'
            }
    
    def check_rate_limits(self, user_id: int, action_type: str, target_contact: str) -> Dict[str, Any]:
        """Check if action is within rate limits"""
        try:
            config = self._get_user_safety_config(user_id)
            
            # Check global kill-switch
            if self.is_global_kill_switch_enabled():
                return {
                    'allowed': False,
                    'reason': 'global_kill_switch',
                    'message': 'Global automation kill-switch is enabled'
                }
            
            # Check per-contact daily limit for auto-replies
            if action_type == 'auto_reply':
                daily_count = self._get_contact_action_count(
                    user_id, target_contact, action_type, hours=24
                )
                if daily_count >= config.max_auto_replies_per_contact_per_day:
                    return {
                        'allowed': False,
                        'reason': 'contact_daily_limit',
                        'message': f'Daily auto-reply limit ({config.max_auto_replies_per_contact_per_day}) exceeded for contact'
                    }
            
            # Check user burst limit (5 minutes)
            burst_count = self._get_user_action_count(user_id, minutes=5)
            if burst_count >= config.max_actions_per_user_per_5min:
                return {
                    'allowed': False,
                    'reason': 'user_burst_limit',
                    'message': f'User burst limit ({config.max_actions_per_user_per_5min}) exceeded in 5 minutes'
                }
            
            # Check user hourly limit
            hourly_count = self._get_user_action_count(user_id, minutes=60)
            if hourly_count >= config.max_actions_per_user_per_hour:
                return {
                    'allowed': False,
                    'reason': 'user_hourly_limit',
                    'message': f'User hourly limit ({config.max_actions_per_user_per_hour}) exceeded'
                }
            
            return {
                'allowed': True,
                'reason': 'within_limits',
                'message': 'Action is within rate limits'
            }
            
        except Exception as e:
            logger.error(f"Failed to check rate limits: {e}")
            return {
                'allowed': False,
                'reason': 'error',
                'message': f'Rate limit check failed: {str(e)}'
            }
    
    def log_automation_action(self, user_id: int, rule_id: int, action_type: str, 
                            target_contact: str, idempotency_key: str, 
                            status: str = 'pending', error_message: Optional[str] = None) -> Dict[str, Any]:
        """Log automation action for tracking and idempotency"""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO automation_action_log 
                (user_id, rule_id, action_type, target_contact, idempotency_key, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, rule_id, action_type, target_contact, idempotency_key, status, error_message),
                fetch=False
            )
            
            return {
                'success': True,
                'message': 'Action logged successfully'
            }
        except Exception as e:
            logger.error(f"Failed to log automation action: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'ACTION_LOG_FAILED'
            }
    
    def log_oauth_failure(self, user_id: int, failure_type: str, error_message: str) -> Dict[str, Any]:
        """Log OAuth failure for tracking"""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO oauth_failure_log (user_id, failure_type, error_message)
                VALUES (?, ?, ?)
                """,
                (user_id, failure_type, error_message),
                fetch=False
            )
            
            # Check if user should be paused due to OAuth failures
            self._check_oauth_failure_threshold(user_id)
            
            return {
                'success': True,
                'message': 'OAuth failure logged'
            }
        except Exception as e:
            logger.error(f"Failed to log OAuth failure: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'OAUTH_LOG_FAILED'
            }
    
    def _get_user_safety_config(self, user_id: int) -> AutomationSafetyConfig:
        """Get user-specific safety configuration"""
        try:
            # Rulepack compliance: specific columns, not SELECT *
            result = self.db_optimizer.execute_query(
                "SELECT id, user_id, global_kill_switch, max_auto_replies_per_contact_per_day, max_actions_per_user_per_5min, max_actions_per_user_per_hour, dry_run_mode, oauth_failure_threshold, oauth_failure_window_minutes, created_at, updated_at FROM automation_safety_config WHERE user_id = ? LIMIT 1",
                (user_id,)
            )
            
            if result:
                row = result[0]
                # Handle both dict and tuple result formats
                if isinstance(row, dict):
                    return AutomationSafetyConfig(
                        global_kill_switch=bool(row.get('global_kill_switch', False)),
                        max_auto_replies_per_contact_per_day=row.get('max_auto_replies_per_contact_per_day', 2),
                        max_actions_per_user_per_5min=row.get('max_actions_per_user_per_5min', 50),
                        max_actions_per_user_per_hour=row.get('max_actions_per_user_per_hour', 200),
                        dry_run_mode=bool(row.get('dry_run_mode', True)),
                        oauth_failure_threshold=row.get('oauth_failure_threshold', 3),
                        oauth_failure_window_minutes=row.get('oauth_failure_window_minutes', 15)
                    )
                else:
                    # Fallback for tuple format
                    return AutomationSafetyConfig(
                        global_kill_switch=bool(row[2]),
                        max_auto_replies_per_contact_per_day=row[3],
                        max_actions_per_user_per_5min=row[4],
                        max_actions_per_user_per_hour=row[5],
                        dry_run_mode=bool(row[6]),
                        oauth_failure_threshold=row[7],
                        oauth_failure_window_minutes=row[8]
                    )
            else:
                # Return default config
                return AutomationSafetyConfig()
        except Exception as e:
            logger.error(f"Failed to get user safety config: {e}")
            return AutomationSafetyConfig()
    
    def _get_contact_action_count(self, user_id: int, target_contact: str, 
                                action_type: str, hours: int) -> int:
        """Get action count for specific contact within time window"""
        try:
            result = self.db_optimizer.execute_query(
                """
                SELECT COUNT(*) FROM automation_action_log 
                WHERE user_id = ? AND target_contact = ? AND action_type = ? 
                AND created_at > datetime('now', '-{} hours')
                """.format(hours),
                (user_id, target_contact, action_type)
            )
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get contact action count: {e}")
            return 0
    
    def _get_user_action_count(self, user_id: int, minutes: int) -> int:
        """Get action count for user within time window"""
        try:
            result = self.db_optimizer.execute_query(
                """
                SELECT COUNT(*) FROM automation_action_log 
                WHERE user_id = ? AND created_at > datetime('now', '-{} minutes')
                """.format(minutes),
                (user_id,)
            )
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get user action count: {e}")
            return 0
    
    def _check_oauth_failure_threshold(self, user_id: int):
        """Check if user should be paused due to OAuth failures"""
        try:
            config = self._get_user_safety_config(user_id)
            
            # Count failures in the window
            result = self.db_optimizer.execute_query(
                """
                SELECT COUNT(*) FROM oauth_failure_log 
                WHERE user_id = ? AND created_at > datetime('now', '-{} minutes')
                """.format(config.oauth_failure_window_minutes),
                (user_id,)
            )
            
            failure_count = result[0][0] if result else 0
            
            if failure_count >= config.oauth_failure_threshold:
                # Pause user's automations
                self._pause_user_automations(user_id)
                logger.warning(f"User {user_id} automations paused due to OAuth failures ({failure_count})")
                
        except Exception as e:
            logger.error(f"Failed to check OAuth failure threshold: {e}")
    
    def _pause_user_automations(self, user_id: int):
        """Pause all automations for a user"""
        try:
            self.db_optimizer.execute_query(
                "UPDATE automation_rules SET status = 'paused' WHERE user_id = ?",
                (user_id,),
                fetch=False
            )
            logger.info(f"Paused all automations for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to pause user automations: {e}")
    
    def get_safety_status(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive safety status for user"""
        try:
            config = self._get_user_safety_config(user_id)
            global_kill_switch = self.is_global_kill_switch_enabled()
            
            # Get recent action counts
            recent_actions_5min = self._get_user_action_count(user_id, 5)
            recent_actions_1hour = self._get_user_action_count(user_id, 60)
            
            # Get OAuth failure count
            # Check if oauth_failure_log table exists
            try:
                oauth_failures = self.db_optimizer.execute_query(
                    """
                    SELECT COUNT(*) as failure_count FROM oauth_failure_log 
                    WHERE user_id = ? AND created_at > datetime('now', '-{} minutes')
                    """.format(config.oauth_failure_window_minutes),
                    (user_id,)
                )
                # Handle both dict and tuple result formats
                if oauth_failures:
                    if isinstance(oauth_failures[0], dict):
                        oauth_failure_count = oauth_failures[0].get('failure_count', 0) or oauth_failures[0].get('COUNT(*)', 0) or 0
                    else:
                        oauth_failure_count = oauth_failures[0][0] if isinstance(oauth_failures[0], (tuple, list)) else 0
                else:
                    oauth_failure_count = 0
            except Exception as e:
                logger.warning(f"Could not get OAuth failure count: {e}")
                oauth_failure_count = 0
            
            return {
                'success': True,
                'data': {
                    'global_kill_switch_enabled': global_kill_switch,
                    'user_config': {
                        'max_auto_replies_per_contact_per_day': config.max_auto_replies_per_contact_per_day,
                        'max_actions_per_user_per_5min': config.max_actions_per_user_per_5min,
                        'max_actions_per_user_per_hour': config.max_actions_per_user_per_hour,
                        'dry_run_mode': config.dry_run_mode,
                        'oauth_failure_threshold': config.oauth_failure_threshold
                    },
                    'current_usage': {
                        'actions_last_5min': recent_actions_5min,
                        'actions_last_hour': recent_actions_1hour,
                        'oauth_failures_recent': oauth_failure_count
                    },
                    'status': 'paused' if global_kill_switch else 'active'
                }
            }
        except Exception as e:
            logger.error(f"Failed to get safety status: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SAFETY_STATUS_FAILED'
            }

# Initialize safety manager
automation_safety_manager = AutomationSafetyManager(db_optimizer)
