"""
Database Optimization System
Query performance, indexing, and migrations for Fikiri Solutions
"""

import sqlite3
import json
import time
import logging
import os
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager

# Optional encryption support
try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    Fernet = None

# Optional PostgreSQL support
try:
    import psycopg2
    import psycopg2.pool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    psycopg2 = None

logger = logging.getLogger(__name__)

def safe_json(obj):
    """Convert unsupported types to JSON-friendly values."""
    if isinstance(obj, sqlite3.Row):
        return dict(obj)
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)

def safe_json_serialize(obj):
    """Safely convert DB rows or complex objects to JSON-serializable data."""
    try:
        # Convert sqlite3.Row or SQLAlchemy Row to dict
        if isinstance(obj, sqlite3.Row):
            return dict(obj)
        elif hasattr(obj, "_mapping"):  # for SQLAlchemy Row
            return dict(obj._mapping)
        elif isinstance(obj, (list, tuple)):
            return [safe_json_serialize(o) for o in obj]
        elif isinstance(obj, dict):
            return {k: safe_json_serialize(v) for k, v in obj.items()}
        else:
            return obj
    except Exception as e:
        logger.warning("⚠️ Auto-converted non-serializable DB result to dict")
        return str(obj)

@dataclass
class QueryMetrics:
    """Database query performance metrics"""
    query: str
    execution_time: float
    rows_affected: int
    timestamp: datetime
    success: bool
    error: Optional[str] = None

@dataclass
class IndexInfo:
    """Database index information"""
    table_name: str
    index_name: str
    columns: List[str]
    unique: bool
    size_bytes: int

class DatabaseOptimizer:
    """Database optimization and performance monitoring with enterprise features"""
    
    def __init__(self, db_path: str = None, db_type: str = "sqlite"):
        # Use persistent storage on Render, fallback to local for development
        if db_path is None:
            if os.path.exists("/opt/render/project/data"):
                db_path = "/opt/render/project/data/fikiri.db"
            else:
                db_path = "data/fikiri.db"
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.db_type = db_type.lower()
        self.query_metrics: List[QueryMetrics] = []
        self.max_metrics = 10000
        self.lock = threading.Lock()
        
        # Initialize ready flag to prevent race conditions
        self._ready = False
        
        # Check database integrity on startup
        self._check_and_repair_database()
        
        # Initialize database schema
        self._initialize_database()
        self._ready = True
        
        # Connection pooling for PostgreSQL
        self.connection_pool = None
    
    def _check_and_repair_database(self):
        """Check database integrity and repair if corrupted"""
        try:
            if not os.path.exists(self.db_path):
                logger.info(f"📁 Database file doesn't exist, will be created: {self.db_path}")
                return
            
            # Test database integrity
            conn = sqlite3.connect(self.db_path)
            try:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result and result[0] == 'ok':
                    logger.info("✅ Database integrity check passed")
                else:
                    logger.warning(f"⚠️ Database integrity issues detected: {result}")
                    self._repair_database()
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"❌ Database integrity check failed: {e}")
            self._repair_database()
    
    def _repair_database(self):
        """Repair corrupted database by recreating it"""
        try:
            logger.warning("🔧 Attempting to repair corrupted database...")
            
            # Force remove corrupted database
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.corrupted.{int(time.time())}"
                try:
                    os.rename(self.db_path, backup_path)
                    logger.info(f"📦 Backed up corrupted database to: {backup_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not backup corrupted database: {e}")
                    # Force delete if rename fails
                    try:
                        os.remove(self.db_path)
                        logger.info("🗑️ Force deleted corrupted database")
                    except Exception as e2:
                        logger.error(f"❌ Could not delete corrupted database: {e2}")
            
            # Recreate database with fresh schema
            logger.info("🔄 Recreating database with fresh schema...")
            self._initialize_database()
            logger.info("✅ Database repair completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Database repair failed: {e}")
            # If repair fails, try to continue with a fresh database
            try:
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                self._initialize_database()
                logger.info("✅ Fresh database created as fallback")
            except Exception as e2:
                logger.error(f"❌ Complete database recovery failed: {e2}")
                # Last resort: create empty database file
                try:
                    open(self.db_path, 'a').close()
                    logger.info("🆘 Created empty database file as last resort")
                except Exception as e3:
                    logger.error(f"❌ Complete database recovery failed: {e3}")
        
        # Initialize encryption support
        self.cipher = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption for sensitive data"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key and ENCRYPTION_AVAILABLE:
            try:
                self.cipher = Fernet(encryption_key.encode())
                logger.info("✅ Database encryption initialized")
            except Exception as e:
                logger.error(f"❌ Encryption initialization failed: {e}")
                self.cipher = None
        elif encryption_key and not ENCRYPTION_AVAILABLE:
            logger.warning("⚠️ ENCRYPTION_KEY set but cryptography not available")
        else:
            logger.info("ℹ️ Database encryption disabled (no ENCRYPTION_KEY)")
    
    def _initialize_database(self):
        """Initialize database with optimized schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create optimized tables with proper indexes
            self._create_optimized_tables(cursor)
            self._create_indexes(cursor)
            self._create_views(cursor)
            
            # Create metrics persistence table
            self._create_metrics_table(cursor)
            
            conn.commit()
            logger.info("Database initialized with optimized schema")
    
    def _create_metrics_table(self, cursor):
        """Create table for persistent query performance metrics"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                query_text TEXT NOT NULL,
                execution_time REAL NOT NULL,
                rows_affected INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                endpoint TEXT
            )
        """)
        
        # Create indexes for metrics table
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_performance_timestamp 
            ON query_performance_log (timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_performance_query_hash 
            ON query_performance_log (query_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_performance_execution_time 
            ON query_performance_log (execution_time)
        """)
    
    def _create_optimized_tables(self, cursor):
        """Create tables with optimized structure"""
        
        # Users table for authentication and profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_hash_enc TEXT,  -- Encrypted version
                role TEXT DEFAULT 'user',
                business_name TEXT,
                business_email TEXT,
                industry TEXT,
                team_size TEXT,
                is_active BOOLEAN DEFAULT 1,
                email_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                onboarding_completed BOOLEAN DEFAULT 0,
                onboarding_step INTEGER DEFAULT 0,
                metadata TEXT  -- JSON object for additional user data
            )
        """)
        
        # Gmail OAuth tokens table (supporting both encrypted and plain storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gmail_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                access_token_enc TEXT,  -- Encrypted version
                refresh_token_enc TEXT, -- Encrypted version
                token_type TEXT DEFAULT 'Bearer',
                expires_at TIMESTAMP,
                expiry_timestamp INTEGER,  -- Unix timestamp version
                scope TEXT,  -- OAuth scopes granted (JSON string)
                scopes_json TEXT,  -- OAuth scopes granted (JSON string) for encrypted tokens
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Email sync tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sync_type TEXT NOT NULL,  -- 'initial', 'incremental', 'manual'
                status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
                emails_processed INTEGER DEFAULT 0,
                emails_total INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata TEXT,  -- JSON object for sync details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Onboarding info table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                company TEXT,
                industry TEXT,
                team_size TEXT,
                goals TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # OAuth states table for CSRF protection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                provider TEXT DEFAULT 'gmail',
                redirect_url TEXT,
                expires_at INTEGER,
                metadata TEXT,  -- JSON object for additional state data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL UNIQUE,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_valid BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Leads table with proper data types and constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                company TEXT,
                source TEXT DEFAULT 'web',
                stage TEXT DEFAULT 'new',
                score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_contact TIMESTAMP,
                notes TEXT,
                tags TEXT,  -- JSON array of tags
                metadata TEXT,  -- JSON object for additional data
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, email)  -- Unique email per user
            )
        """)
        
        # Activities table for lead interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
            )
        """)
        
        # Email templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                template_type TEXT DEFAULT 'general',
                industry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                response_time REAL NOT NULL,
                status_code INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT
            )
        """)
        
        # User privacy settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_privacy_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_retention_days INTEGER DEFAULT 90,
                email_scanning_enabled BOOLEAN DEFAULT 1,
                personal_email_exclusion BOOLEAN DEFAULT 1,
                auto_labeling_enabled BOOLEAN DEFAULT 1,
                lead_detection_enabled BOOLEAN DEFAULT 1,
                analytics_tracking_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)
        
        # Data retention logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_retention_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_type TEXT NOT NULL,  -- 'emails', 'leads', 'activities'
                records_deleted INTEGER DEFAULT 0,
                retention_policy_days INTEGER NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON object with deletion details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Privacy consent tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS privacy_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                consent_type TEXT NOT NULL,  -- 'gmail_access', 'data_processing', 'analytics'
                granted BOOLEAN NOT NULL,
                consent_text TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # System configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Automation rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL,
                trigger_conditions TEXT NOT NULL,  -- JSON object
                action_type TEXT NOT NULL,
                action_parameters TEXT NOT NULL,  -- JSON object
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Automation executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                trigger_data TEXT NOT NULL,  -- JSON object
                action_result TEXT NOT NULL,  -- JSON object
                status TEXT NOT NULL,  -- 'success', 'error'
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Parsed emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsed_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                thread_id TEXT,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                recipient_email TEXT,
                subject TEXT,
                body_text TEXT,
                body_html TEXT,
                email_date TIMESTAMP,
                labels TEXT,  -- JSON array
                attachments TEXT,  -- JSON array
                extracted_data TEXT,  -- JSON object
                lead_potential INTEGER DEFAULT 0,
                action_required BOOLEAN DEFAULT 0,
                parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Email insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                data TEXT NOT NULL,  -- JSON object
                suggested_action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Feature flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT NOT NULL UNIQUE,
                enabled BOOLEAN DEFAULT 0,
                description TEXT,
                rollout_percentage INTEGER DEFAULT 0,
                target_users TEXT,  -- JSON array of user IDs or conditions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User feature access table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feature_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feature_name TEXT NOT NULL,
                has_access BOOLEAN DEFAULT 0,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                granted_by TEXT,  -- 'system', 'admin', etc.
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, feature_name)
            )
        """)
        
        # Analytics events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_data TEXT,  -- JSON object
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        
        # Onboarding jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
                current_step TEXT DEFAULT 'initializing',
                progress INTEGER DEFAULT 0,  -- 0-100
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata TEXT,  -- JSON object with job details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Email actions log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT NOT NULL,
                message_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                details TEXT,  -- JSON object
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        
        # Create indexes for email actions log
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_user_id 
            ON email_actions_log (user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_timestamp 
            ON email_actions_log (timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_action_type 
            ON email_actions_log (action_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_success 
            ON email_actions_log (success)
        """)
    
    def _create_indexes(self, cursor):
        """Create optimized indexes for better query performance"""
        
        indexes = [
            # Users table indexes
            ("idx_users_email", "users", ["email"]),
            ("idx_users_role", "users", ["role"]),
            ("idx_users_active", "users", ["is_active"]),
            ("idx_users_onboarding", "users", ["onboarding_completed"]),
            ("idx_users_created_at", "users", ["created_at"]),
            
            # Gmail tokens indexes
            ("idx_gmail_tokens_user_id", "gmail_tokens", ["user_id"]),
            ("idx_gmail_tokens_active", "gmail_tokens", ["is_active"]),
            ("idx_gmail_tokens_expires", "gmail_tokens", ["expires_at"]),
            
            # Email sync indexes
            ("idx_email_sync_user_id", "email_sync", ["user_id"]),
            ("idx_email_sync_status", "email_sync", ["status"]),
            ("idx_email_sync_type", "email_sync", ["sync_type"]),
            ("idx_email_sync_started", "email_sync", ["started_at"]),
            
            # User sessions indexes
            ("idx_sessions_user_id", "user_sessions", ["user_id"]),
            ("idx_sessions_session_id", "user_sessions", ["session_id"]),
            ("idx_sessions_expires", "user_sessions", ["expires_at"]),
            ("idx_sessions_valid", "user_sessions", ["is_valid"]),
            
            # Privacy settings indexes
            ("idx_privacy_user_id", "user_privacy_settings", ["user_id"]),
            ("idx_privacy_retention", "user_privacy_settings", ["data_retention_days"]),
            
            # Data retention logs indexes
            ("idx_retention_user_id", "data_retention_logs", ["user_id"]),
            ("idx_retention_data_type", "data_retention_logs", ["data_type"]),
            ("idx_retention_deleted_at", "data_retention_logs", ["deleted_at"]),
            
            # Privacy consents indexes
            ("idx_consents_user_id", "privacy_consents", ["user_id"]),
            ("idx_consents_type", "privacy_consents", ["consent_type"]),
            ("idx_consents_granted", "privacy_consents", ["granted"]),
            ("idx_consents_granted_at", "privacy_consents", ["granted_at"]),
            
            # Automation rules indexes
            ("idx_automation_user_id", "automation_rules", ["user_id"]),
            ("idx_automation_trigger_type", "automation_rules", ["trigger_type"]),
            ("idx_automation_status", "automation_rules", ["status"]),
            ("idx_automation_last_executed", "automation_rules", ["last_executed"]),
            
            # Automation executions indexes
            ("idx_executions_rule_id", "automation_executions", ["rule_id"]),
            ("idx_executions_user_id", "automation_executions", ["user_id"]),
            ("idx_executions_status", "automation_executions", ["status"]),
            ("idx_executions_executed_at", "automation_executions", ["executed_at"]),
            
            # Parsed emails indexes
            ("idx_parsed_emails_user_id", "parsed_emails", ["user_id"]),
            ("idx_parsed_emails_email_id", "parsed_emails", ["email_id"]),
            ("idx_parsed_emails_sender", "parsed_emails", ["sender_email"]),
            ("idx_parsed_emails_date", "parsed_emails", ["email_date"]),
            ("idx_parsed_emails_lead_potential", "parsed_emails", ["lead_potential"]),
            
            # Email insights indexes
            ("idx_insights_user_id", "email_insights", ["user_id"]),
            ("idx_insights_email_id", "email_insights", ["email_id"]),
            ("idx_insights_type", "email_insights", ["insight_type"]),
            ("idx_insights_confidence", "email_insights", ["confidence"]),
            
            # Feature flags indexes
            ("idx_feature_flags_name", "feature_flags", ["feature_name"]),
            ("idx_feature_flags_enabled", "feature_flags", ["enabled"]),
            
            # User feature access indexes
            ("idx_user_feature_access_user_id", "user_feature_access", ["user_id"]),
            ("idx_user_feature_access_feature", "user_feature_access", ["feature_name"]),
            ("idx_user_feature_access_has_access", "user_feature_access", ["has_access"]),
            
            # Analytics events indexes
            ("idx_analytics_user_id", "analytics_events", ["user_id"]),
            ("idx_analytics_event_type", "analytics_events", ["event_type"]),
            ("idx_analytics_created_at", "analytics_events", ["created_at"]),
            
            # Onboarding jobs indexes
            ("idx_onboarding_jobs_user_id", "onboarding_jobs", ["user_id"]),
            ("idx_onboarding_jobs_status", "onboarding_jobs", ["status"]),
            ("idx_onboarding_jobs_started", "onboarding_jobs", ["started_at"]),
            
            # Metrics daily indexes
            ("idx_metrics_daily_user_id", "metrics_daily", ["user_id"]),
            ("idx_metrics_daily_day", "metrics_daily", ["day"]),
            
            # Performance metrics indexes
            ("idx_performance_endpoint", "performance_metrics", ["endpoint"]),
            ("idx_performance_timestamp", "performance_metrics", ["timestamp"]),
            ("idx_performance_response_time", "performance_metrics", ["response_time"]),
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                # Check if table exists before creating index
                if table_name == 'metrics_daily' and not self.table_exists('metrics_daily'):
                    logger.info(f"ℹ️ Skipping index {index_name} - table {table_name} doesn't exist")
                    continue
                    
                columns_str = ", ".join(columns)
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({columns_str})
                """)
            except Exception as e:
                logger.warning(f"Could not create index {index_name}: {e}")
    
    def _create_views(self, cursor):
        """Create optimized views for common queries"""
        
        # Active users view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_users AS
            SELECT id, email, name, role, business_name, created_at, last_login
            FROM users 
            WHERE is_active = 1
        """)
        
        # Recent leads view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS recent_leads AS
            SELECT l.*, u.name as user_name, u.email as user_email
            FROM leads l
            JOIN users u ON l.user_id = u.id
            WHERE l.created_at >= datetime('now', '-30 days')
            ORDER BY l.created_at DESC
        """)
        
        # Automation performance view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS automation_performance AS
            SELECT 
                ar.id,
                ar.name,
                ar.user_id,
                ar.execution_count,
                ar.success_count,
                ar.error_count,
                CASE 
                    WHEN ar.execution_count > 0 
                    THEN (ar.success_count * 100.0 / ar.execution_count)
                    ELSE 0 
                END as success_rate,
                ar.last_executed
            FROM automation_rules ar
            WHERE ar.status = 'active'
        """)
    
    def _initialize_postgres_pool(self):
        """Initialize PostgreSQL connection pool"""
        if not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL not available")
            return
        
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database=os.getenv('POSTGRES_DB', 'fikiri'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', '')
            )
            logger.info("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"❌ PostgreSQL pool initialization failed: {e}")
            self.connection_pool = None
    
    @contextmanager
    def get_connection(self, retries=3):
        """Get database connection with retry logic and corruption prevention"""
        conn = None
        last_error = None
        
        for attempt in range(retries):
            try:
                if self.db_type == "postgresql" and self.connection_pool:
                    conn = self.connection_pool.getconn()
                else:
                    # SQLite connection with corruption prevention
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.row_factory = sqlite3.Row  # Enable dict-like access
                    
                    # Production-safe PRAGMAs to prevent corruption
                    conn.execute("PRAGMA journal_mode=DELETE")  # Use DELETE mode for stability
                    conn.execute("PRAGMA synchronous=FULL")  # Maximum safety to prevent corruption
                    conn.execute("PRAGMA cache_size=2000")  # Smaller cache to reduce memory pressure
                    conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
                    conn.execute("PRAGMA busy_timeout = 10000")  # Longer timeout for locks
                    conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
                    
                    # Check integrity on connection
                    integrity_result = conn.execute("PRAGMA integrity_check").fetchone()
                    if integrity_result and integrity_result[0] != 'ok':
                        logger.error(f"Database integrity check failed: {integrity_result[0]}")
                        conn.close()
                        conn = None
                        raise sqlite3.DatabaseError("Database integrity check failed")
                
                yield conn
                return  # Success, exit retry loop
                
            except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                last_error = e
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None
                
                if "database disk image is malformed" in str(e):
                    logger.error(f"Database corruption detected on attempt {attempt + 1}: {e}")
                    if attempt < retries - 1:
                        logger.info("Attempting database repair...")
                        self._repair_database()
                        continue
                    else:
                        logger.error("All repair attempts failed")
                        break
                elif attempt < retries - 1:
                    logger.warning(f"Database connection failed on attempt {attempt + 1}: {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    break
            except Exception as e:
                last_error = e
                if conn:
                    try:
                        conn.rollback()
                        conn.close()
                    except:
                        pass
                    conn = None
                break
        
        # If we get here, all attempts failed
        if last_error:
            logger.error(f"Database connection failed after {retries} attempts: {last_error}")
            raise last_error
        else:
            raise sqlite3.DatabaseError("Database connection failed after all retry attempts")
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data using Fernet encryption"""
        if not self.cipher:
            return data
        
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using Fernet encryption"""
        if not self.cipher:
            return encrypted_data
        
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def validate_json(self, json_string: str) -> bool:
        """Validate JSON string before inserting"""
        try:
            json.loads(json_string)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def execute_query(self, query: str, params: Tuple = None, fetch: bool = True, 
                     user_id: int = None, endpoint: str = None) -> Any:
        """Execute a query with performance monitoring and JSON validation"""
        start_time = time.time()
        
        try:
            # Validate JSON parameters if present and convert lists to JSON
            if params:
                converted_params = []
                for param in params:
                    if isinstance(param, list):
                        # Convert list to JSON string for SQLite compatibility
                        param = json.dumps(param)
                    elif hasattr(param, 'keys') and hasattr(param, 'values'):
                        # Handle sqlite3.Row objects by converting to dict
                        try:
                            param = dict(param)
                        except Exception:
                            param = str(param)
                    elif isinstance(param, str) and param.startswith('{') and param.endswith('}'):
                        if not self.validate_json(param):
                            raise ValueError(f"Invalid JSON parameter: {param}")
                    converted_params.append(param)
                params = tuple(converted_params)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                        result = cursor.fetchall()
                        # Convert sqlite3.Row objects to dictionaries for JSON compatibility
                        if result and isinstance(result[0], sqlite3.Row):
                            result = [dict(row) for row in result]
                    else:
                        result = cursor.rowcount
                else:
                    result = cursor.rowcount
                
                conn.commit()
                
                execution_time = time.time() - start_time
                
                # Record metrics only if ready
                if self._ready:
                    self._record_query_metrics(query, execution_time, result, True, 
                                             user_id=user_id, endpoint=endpoint)
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            # Only record metrics on error if ready
            if self._ready:
                self._record_query_metrics(query, execution_time, 0, False, str(e),
                                         user_id=user_id, endpoint=endpoint)
            logger.error(f"Query execution error: {e}")
            raise
    
    def _record_query_metrics(self, query: str, execution_time: float, 
                            rows_affected: int, success: bool, error: str = None,
                            user_id: int = None, endpoint: str = None):
        """Record query performance metrics with persistence"""
        # Don't record metrics if not ready or if this is a metrics query
        if not self._ready:
            return
            
        import hashlib
        
        # Prevent recursive logging - if this is a metrics query, skip persistence
        if "query_performance_log" in query.lower() or "metrics" in query.lower():
            return
        
        # Skip performance logging on auth-related queries to avoid overhead
        if "users" in query.lower() and ("password" in query.lower() or "session" in query.lower()):
            return
        
        # Skip performance logging for fast queries to reduce database load
        if execution_time < 0.01:  # Skip queries faster than 10ms
            return
        
        # Only log every 10th query to reduce database load
        if hasattr(self, '_query_count'):
            self._query_count += 1
        else:
            self._query_count = 1
        
        if self._query_count % 10 != 0:
            return
        
        # Create query hash for deduplication
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        with self.lock:
            metric = QueryMetrics(
                query=query[:100],  # Truncate long queries
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=datetime.now(timezone.utc),  # Use UTC
                success=success,
                error=error
            )
            
            self.query_metrics.append(metric)
            
            # Keep only recent metrics in memory
            if len(self.query_metrics) > self.max_metrics:
                self.query_metrics = self.query_metrics[-self.max_metrics:]
        
        # Persist metrics to database
        try:
            self.execute_query("""
                INSERT INTO query_performance_log 
                (query_hash, query_text, execution_time, rows_affected, success, error_message, user_id, endpoint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                query[:500],  # Truncate for storage
                execution_time,
                rows_affected,
                success,
                error,
                user_id,
                endpoint
            ), fetch=False)
        except Exception as e:
            logger.warning(f"Failed to persist query metrics: {e}")
    
    def get_query_performance(self, hours: int = 24) -> Dict[str, Any]:
        """Get query performance analysis"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        recent_metrics = [
            m for m in self.query_metrics 
            if m.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_metrics:
            return {'message': 'No recent query metrics available'}
        
        # Calculate statistics
        execution_times = [m.execution_time for m in recent_metrics]
        successful_queries = [m for m in recent_metrics if m.success]
        failed_queries = [m for m in recent_metrics if not m.success]
        
        # Find slow queries
        slow_queries = [m for m in recent_metrics if m.execution_time > 1.0]
        
        # Most frequent queries
        query_counts = {}
        for m in recent_metrics:
            query_counts[m.query] = query_counts.get(m.query, 0) + 1
        
        return {
            'total_queries': len(recent_metrics),
            'successful_queries': len(successful_queries),
            'failed_queries': len(failed_queries),
            'success_rate': len(successful_queries) / len(recent_metrics) * 100,
            'average_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'slow_queries': len(slow_queries),
            'most_frequent_queries': sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization tasks with improved size query"""
        optimization_results = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Analyze tables
            cursor.execute("ANALYZE")
            optimization_results['analyze'] = 'Completed'
            
            # Vacuum database
            cursor.execute("VACUUM")
            optimization_results['vacuum'] = 'Completed'
            
            # Get database size with improved compatibility
            try:
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                optimization_results['database_size_bytes'] = page_count * page_size
            except Exception as e:
                logger.warning(f"Could not get database size: {e}")
                optimization_results['database_size_bytes'] = 0
            
            # Get index information
            cursor.execute("""
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = cursor.fetchall()
            optimization_results['indexes'] = [
                {
                    'name': idx[0],
                    'table': idx[1],
                    'sql': idx[2]
                }
                for idx in indexes
            ]
            
            conn.commit()
        
        return optimization_results
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table sizes
            cursor.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as table_count,
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as index_count
                FROM sqlite_master m
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            
            tables = cursor.fetchall()
            stats['tables'] = [
                {
                    'name': table[0],
                    'index_count': table[2]
                }
                for table in tables
            ]
            
            # Row counts
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[f'{table_name}_count'] = count
                except Exception as e:
                    logger.warning(f"Could not get count for table {table_name}: {e}")
            
            # Database file size with improved compatibility
            try:
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats['database_size_bytes'] = page_count * page_size
            except Exception as e:
                logger.warning(f"Could not get database size: {e}")
                stats['database_size_bytes'] = 0
        
        return stats
    
    def create_migration(self, version: str, description: str, up_sql: str, 
                       down_sql: str = None, depends_on: str = None):
        """Create a database migration with dependency support"""
        migration = {
            'version': version,
            'description': description,
            'up_sql': up_sql,
            'down_sql': down_sql,
            'depends_on': depends_on,
            'created_at': datetime.now(timezone.utc).isoformat()  # Use UTC
        }
        
        # Store migration in system config
        self.execute_query(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            (f"migration_{version}", json.dumps(safe_json_serialize(migration), default=str))
        )
        
        logger.info(f"Migration {version} created: {description}")
        return migration
    
    def run_migration(self, version: str) -> bool:
        """Run a specific migration with dependency checking"""
        try:
            # Get migration
            migration_data = self.execute_query(
                "SELECT value FROM system_config WHERE key = ?",
                (f"migration_{version}",)
            )
            
            if not migration_data:
                logger.error(f"Migration {version} not found")
                return False
            
            migration = json.loads(migration_data[0]['value'])
            
            # Check dependencies
            if migration.get('depends_on'):
                depends_on = migration['depends_on']
                dependency_check = self.execute_query(
                    "SELECT value FROM system_config WHERE key = ?",
                    (f"migration_{depends_on}",)
                )
                
                if not dependency_check:
                    logger.error(f"Dependency migration {depends_on} not found")
                    return False
            
            # Run migration
            self.execute_query(migration['up_sql'], fetch=False)
            
            # Mark as applied
            self.execute_query(
                "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
                (f"applied_migration_{version}", json.dumps(safe_json_serialize({
                    'applied_at': datetime.now(timezone.utc).isoformat(),
                    'version': version
                }), default=str))
            )
            
            logger.info(f"Migration {version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")
            return False
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations"""
        try:
            migrations = self.execute_query(
                "SELECT key, value FROM system_config WHERE key LIKE 'applied_migration_%'"
            )
            
            return [
                {
                    'version': key.replace('applied_migration_', ''),
                    'applied_at': json.loads(value)['applied_at']
                }
                for key, value in migrations
            ]
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 30):
        """Clean up old query performance metrics"""
        try:
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            deleted_count = self.execute_query(
                "DELETE FROM query_performance_log WHERE timestamp < ?",
                (cutoff_date.isoformat(),),
                fetch=False
            )
            
            logger.info(f"Cleaned up {deleted_count} old metrics records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Metrics cleanup failed: {e}")
            return 0
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            q = f"SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
            res = self.execute_query(q, (table_name,))
            return bool(res)
        except Exception as e:
            logger.warning(f"Could not check if table {table_name} exists: {e}")
            return False

# Global database optimizer instance
db_optimizer = DatabaseOptimizer()