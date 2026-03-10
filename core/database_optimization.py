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
            
            # Test database integrity with proper connection settings
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                # Set threading mode to serialized for thread safety
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
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
            
            # Run migrations
            self._run_migrations(cursor)
            
            conn.commit()
            logger.info("Database initialized with optimized schema")
    
    def _run_migrations(self, cursor):
        """Run database migrations for schema updates"""
        try:
            # Migration: Add stripe_customer_id to users table if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'stripe_customer_id' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
                logger.info("✅ Added stripe_customer_id column to users table")

            # Migration: Add missing lead columns if they don't exist
            cursor.execute("PRAGMA table_info(leads)")
            lead_columns = [row[1] for row in cursor.fetchall()]
            if 'external_id' not in lead_columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN external_id TEXT")
                logger.info("✅ Added external_id column to leads table")
            if 'subject' not in lead_columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN subject TEXT")
                logger.info("✅ Added subject column to leads table")

            # Chatbot query log: confidence breakdown for eval
            cursor.execute("PRAGMA table_info(chatbot_query_log)")
            qlog_columns = [row[1] for row in cursor.fetchall()]
            if qlog_columns and 'metadata' not in qlog_columns:
                cursor.execute("ALTER TABLE chatbot_query_log ADD COLUMN metadata TEXT")
                logger.info("✅ Added metadata column to chatbot_query_log")

            # Conversation feedback: store confidence etc. with feedback
            cursor.execute("PRAGMA table_info(conversation_feedback)")
            cf_columns = [row[1] for row in cursor.fetchall()]
            if cf_columns and 'metadata' not in cf_columns:
                cursor.execute("ALTER TABLE conversation_feedback ADD COLUMN metadata TEXT")
                logger.info("✅ Added metadata column to conversation_feedback")
        except Exception as e:
            logger.warning(f"Migration warning: {e}")
    
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
        
        # Outlook OAuth tokens table (similar to Gmail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outlook_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                access_token_enc TEXT,  -- Encrypted version
                refresh_token_enc TEXT, -- Encrypted version
                token_type TEXT DEFAULT 'Bearer',
                expires_at TIMESTAMP,
                expiry_timestamp INTEGER,  -- Unix timestamp version
                scope TEXT,  -- OAuth scopes granted
                scopes_json TEXT,  -- OAuth scopes granted (JSON string) for encrypted tokens
                tenant_id TEXT,  -- Azure AD tenant ID
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # OAuth states table for CSRF protection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                provider TEXT NOT NULL,
                redirect_url TEXT,
                expires_at INTEGER,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        
        # Subscriptions table for Stripe subscription caching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stripe_customer_id TEXT NOT NULL,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,  -- active, trialing, past_due, canceled, unpaid, incomplete
                tier TEXT NOT NULL,    -- starter, growth, business, enterprise
                billing_period TEXT,   -- monthly, annual
                current_period_start INTEGER,
                current_period_end INTEGER,
                trial_end INTEGER,
                cancel_at_period_end BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Billing usage table for usage-based billing (emails, leads, AI, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS billing_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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
        
        # Expert teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expert_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, name)
            )
        """)
        
        # Expert team members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expert_team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'expert',  -- 'expert', 'admin'
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES expert_teams (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            )
        """)
        
        # Escalated questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escalated_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                user_id TEXT,  -- End user who asked
                question TEXT NOT NULL,
                original_answer TEXT,
                confidence REAL,
                assigned_to INTEGER,  -- Expert user_id
                team_id INTEGER,
                status TEXT DEFAULT 'pending',  -- 'pending', 'assigned', 'in_progress', 'resolved', 'closed'
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (assigned_to) REFERENCES users (id),
                FOREIGN KEY (team_id) REFERENCES expert_teams (id)
            )
        """)
        
        # Expert responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expert_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalated_question_id INTEGER NOT NULL,
                expert_user_id INTEGER NOT NULL,
                response_text TEXT NOT NULL,
                added_to_kb BOOLEAN DEFAULT 0,
                faq_id INTEGER,  -- If added as FAQ
                kb_document_id TEXT,  -- If added as KB doc
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (escalated_question_id) REFERENCES escalated_questions (id) ON DELETE CASCADE,
                FOREIGN KEY (expert_user_id) REFERENCES users (id)
            )
        """)
        
        # Conversation feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message_id TEXT,
                helpful BOOLEAN,
                feedback_text TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chatbot query log: each turn (query + response) for feedback evaluation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                confidence REAL,
                fallback_used BOOLEAN,
                sources_json TEXT,
                tenant_id TEXT,
                user_id TEXT,
                llm_trace_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chatbot feedback: ratings on answers (question, answer, retrieved_doc_ids, rating)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                retrieved_doc_ids TEXT,
                rating TEXT NOT NULL CHECK(rating IN ('correct', 'somewhat_correct', 'somewhat_incorrect', 'incorrect')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                prompt_version TEXT,
                retriever_version TEXT
            )
        """)
        
        # KPI tracking table for historical KPI data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kpi_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                company_stage TEXT NOT NULL,  -- 'early_stage' or 'mid_stage'
                kpi_type TEXT NOT NULL,  -- 'cac', 'clv', 'burn_rate', 'gross_margin', 'retention_rate', 'arpu', 'sales_efficiency', 'nrr'
                kpi_value REAL NOT NULL,
                metadata TEXT,  -- JSON object with additional context
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, company_stage, kpi_type)
            )
        """)
        
        # Marketing and sales costs tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS acquisition_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cost_date DATE NOT NULL,
                cost_type TEXT NOT NULL,  -- 'marketing', 'sales', 'advertising', 'other'
                amount REAL NOT NULL,
                description TEXT,
                channel TEXT,  -- 'organic', 'paid', 'referral', 'direct', etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Revenue tracking table (for detailed revenue analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revenue_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                revenue_date DATE NOT NULL,
                user_id INTEGER,
                subscription_id INTEGER,
                revenue_type TEXT NOT NULL,  -- 'subscription', 'upsell', 'expansion', 'one_time'
                amount REAL NOT NULL,
                tier TEXT,
                billing_period TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
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
        
        # Services table for user service configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'inactive',  -- 'active', 'inactive', 'error'
                settings TEXT,  -- JSON object for service-specific settings
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, service_id)
            )
        """)
        
        # Email attachments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                attachment_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT,
                size INTEGER DEFAULT 0,
                stored_path TEXT,  -- Path to stored file if downloaded
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for services table
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_services_user_id 
            ON user_services (user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_services_service_id 
            ON user_services (service_id)
        """)
        
        # Create indexes for email attachments table
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_attachments_user_id 
            ON email_attachments (user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_attachments_email_id 
            ON email_attachments (email_id)
        """)
        
        # Appointments table (core primitive - real table, not flexible entity)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled, confirmed, completed, canceled, no_show
                contact_id INTEGER,  -- Link to CRM contact
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                location TEXT,
                notes TEXT,
                sync_to_calendar BOOLEAN DEFAULT 0,
                reminder_24h_sent BOOLEAN DEFAULT 0,
                reminder_2h_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (contact_id) REFERENCES leads (id) ON DELETE SET NULL
            )
        """)

        # Follow-up tasks (email follow-ups)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_tasks (
                id TEXT PRIMARY KEY,
                lead_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                template_id TEXT NOT NULL,
                scheduled_for TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',  -- pending, sent, failed
                idempotency_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Scheduled follow-ups (SMS or custom follow-ups)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                follow_up_date TIMESTAMP NOT NULL,
                follow_up_type TEXT NOT NULL,  -- email, sms
                message TEXT,
                status TEXT DEFAULT 'scheduled',  -- scheduled, sent, failed
                idempotency_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Calendar events (for workflow scheduling)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                title TEXT NOT NULL,
                event_date TIMESTAMP NOT NULL,
                duration INTEGER DEFAULT 60,
                description TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # SMS messages log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                phone_number TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Invoices (workflow generated)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                amount REAL DEFAULT 0,
                description TEXT,
                due_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Generated documents metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_documents (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                template_id TEXT NOT NULL,
                format TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Table/sheet exports metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_id INTEGER,
                name TEXT,
                columns TEXT,  -- JSON array
                row_count INTEGER DEFAULT 0,
                format TEXT DEFAULT 'csv',
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
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
            ("idx_outlook_tokens_user_id", "outlook_tokens", ["user_id"]),
            ("idx_outlook_tokens_active", "outlook_tokens", ["is_active"]),
            ("idx_outlook_tokens_expires", "outlook_tokens", ["expires_at"]),
            
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
            
            # Subscriptions table indexes
            ("idx_subscriptions_user_id", "subscriptions", ["user_id"]),
            ("idx_subscriptions_stripe_customer", "subscriptions", ["stripe_customer_id"]),
            ("idx_subscriptions_stripe_subscription", "subscriptions", ["stripe_subscription_id"]),
            ("idx_subscriptions_status", "subscriptions", ["status"]),
            
            # Billing usage indexes
            ("idx_billing_usage_user_month", "billing_usage", ["user_id", "month"]),
            
            # Appointments table indexes
            ("idx_appointments_user_id", "appointments", ["user_id"]),
            ("idx_appointments_start_time", "appointments", ["start_time"]),
            ("idx_appointments_end_time", "appointments", ["end_time"]),
            ("idx_appointments_status", "appointments", ["status"]),
            ("idx_appointments_contact_id", "appointments", ["contact_id"]),
            ("idx_appointments_time_range", "appointments", ["start_time", "end_time"]),
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
        """Get database connection with retry logic"""
        conn = None
        last_error = None
        yielded = False
        
        try:
            for attempt in range(retries):
                try:
                    if self.db_type == "postgresql" and self.connection_pool:
                        conn = self.connection_pool.getconn()
                    else:
                        # Use check_same_thread=False for thread safety with serialized mode
                        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
                        conn.row_factory = sqlite3.Row
                        # Use WAL mode for better concurrency and performance
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=30000")
                        # Use NORMAL synchronous mode for better performance (FULL is too slow)
                        conn.execute("PRAGMA synchronous=NORMAL")
                        conn.execute("PRAGMA foreign_keys=ON")
                        # Remove integrity check from every connection (too expensive)
                        # Integrity is checked once during initialization
                    
                    yielded = True
                    yield conn
                    return
                    
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                    if yielded:
                        # Exception raised from within the with-body; do not retry here
                        raise
                    if conn:
                        try:
                            conn.close()
                        except Exception as close_error:
                            logger.debug("Failed to close SQLite connection: %s", close_error)
                        conn = None
                    
                    last_error = e
                    if "database disk image is malformed" in str(e) and attempt < retries - 1:
                        logger.warning(f"Database corruption detected, attempting repair...")
                        self._repair_database()
                    
                    if attempt < retries - 1:
                        time.sleep(0.1 * (attempt + 1))
                    else:
                        break
                except Exception as e:
                    if yielded:
                        # Exception raised from within the with-body; do not retry here
                        raise
                    if conn:
                        try:
                            conn.close()
                        except Exception as close_error:
                            logger.debug("Failed to close SQLite connection: %s", close_error)
                    last_error = e
                    break
            
            logger.error(f"Database connection failed after {retries} attempts: {last_error}")
            raise last_error or sqlite3.DatabaseError("Connection failed")
        finally:
            # Ensure connection is closed for SQLite (PostgreSQL connections are returned to pool)
            if conn and self.db_type != "postgresql":
                try:
                    conn.close()
                except Exception as close_error:
                    logger.debug("Failed to close SQLite connection: %s", close_error)
            elif conn and self.db_type == "postgresql" and self.connection_pool:
                try:
                    self.connection_pool.putconn(conn)
                except Exception as pool_error:
                    logger.debug("Failed to return PostgreSQL connection to pool: %s", pool_error)
    
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
                    # Calculate rows_affected properly
                    if fetch and query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                        # For SELECT queries, rows_affected is the number of rows returned
                        rows_affected = len(result) if isinstance(result, list) else (1 if result else 0)
                    else:
                        # For INSERT/UPDATE/DELETE, use rowcount
                        rows_affected = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                    
                    self._record_query_metrics(query, execution_time, rows_affected, True, 
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
        
        # Persist metrics to database using direct connection to avoid recursion
        try:
            import sqlite3
            import json
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()
            
            # Serialize complex data types
            serialized_error = error
            if isinstance(error, (list, dict)):
                serialized_error = json.dumps(error)
            
            serialized_user_id = user_id
            if isinstance(user_id, (list, dict)):
                serialized_user_id = json.dumps(user_id)
            
            serialized_endpoint = endpoint
            if isinstance(endpoint, (list, dict)):
                serialized_endpoint = json.dumps(endpoint)
            
            cursor.execute("""
                INSERT INTO query_performance_log 
                (query_hash, query_text, execution_time, rows_affected, success, error_message, user_id, endpoint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                query[:500],  # Truncate for storage
                execution_time,
                rows_affected,
                success,
                serialized_error,
                serialized_user_id,
                serialized_endpoint
            ))
            conn.commit()
            conn.close()
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
