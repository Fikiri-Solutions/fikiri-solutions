"""
Database Optimization System
Query performance, indexing, and migrations for Fikiri Solutions
"""

import sqlite3
import json
import time
import logging
import os
import re
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

from core.postgres_compat import (
    PostgresBootstrapCursor,
    adapt_qmark_params_to_psycopg2,
    is_postgresql_dsn,
    translate_postgres_ddl_to_sqlite,
    translate_sqlite_ddl_to_postgres,
    should_translate_sqlite_ddl,
)

logger = logging.getLogger(__name__)


def _production_requires_postgres_uri() -> bool:
    """Production must use PostgreSQL (e.g. Supabase) unless explicitly overridden."""
    if os.getenv("FLASK_ENV", "").lower() != "production":
        return False
    return os.getenv("FIKIRI_ALLOW_SQLITE_PRODUCTION", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


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


def query_row_scalar(row: Any, column_name: str) -> Any:
    """
    Read one column from a row returned by execute_query.

    PostgreSQL uses dict-shaped rows (RealDictCursor); SQLite often returns tuples
    or sqlite3.Row. Never index rows with [0] unless the row is sequence-shaped.
    """
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(column_name)
    if isinstance(row, (list, tuple)):
        return row[0] if len(row) > 0 else None
    try:
        return row[column_name]
    except (KeyError, TypeError):
        return None


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
        self.query_metrics: List[QueryMetrics] = []
        self.max_metrics = 10000
        self.lock = threading.Lock()
        self._ready = False
        self.connection_pool = None
        self._postgres_dsn: Optional[str] = None

        dsn = (os.getenv("DATABASE_URL") or "").strip()
        force_sqlite = os.getenv("FIKIRI_FORCE_SQLITE", "").strip().lower() in ("1", "true", "yes")

        if dsn and is_postgresql_dsn(dsn) and not force_sqlite and POSTGRES_AVAILABLE:
            self.db_type = "postgresql"
            self.db_path = dsn.split("@", 1)[-1] if "@" in dsn else "postgresql"
            self._postgres_dsn = dsn
            try:
                mx = int(os.getenv("FIKIRI_POSTGRES_POOL_MAX", "12"))
            except ValueError:
                mx = 12
            try:
                self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    1, max(2, mx), dsn
                )
                logger.info(
                    "Primary database: PostgreSQL via DATABASE_URL "
                    "(use Supabase *Postgres* URI from Dashboard → Database → Connection string)"
                )
            except Exception as e:
                logger.exception("PostgreSQL pool init failed; falling back to SQLite: %s", e)
                self.db_type = "sqlite"
                self._postgres_dsn = None
                self.connection_pool = None
            else:
                self._initialize_database()
                self._ready = True
                return

        if dsn and is_postgresql_dsn(dsn) and not POSTGRES_AVAILABLE:
            logger.error(
                "DATABASE_URL is PostgreSQL but psycopg2 is not installed; "
                "add psycopg2-binary to requirements or unset DATABASE_URL. Using SQLite."
            )

        if _production_requires_postgres_uri():
            if not dsn or not is_postgresql_dsn(dsn):
                raise RuntimeError(
                    "FLASK_ENV=production requires DATABASE_URL to be a PostgreSQL URI "
                    "(Supabase: Project Settings → Database → Connection string / pooler). "
                    "Set FIKIRI_ALLOW_SQLITE_PRODUCTION=1 only for emergency SQLite."
                )
            if force_sqlite:
                raise RuntimeError(
                    "FLASK_ENV=production cannot use FIKIRI_FORCE_SQLITE unless "
                    "FIKIRI_ALLOW_SQLITE_PRODUCTION=1."
                )
            if not POSTGRES_AVAILABLE:
                raise RuntimeError(
                    "FLASK_ENV=production requires psycopg2-binary when DATABASE_URL is PostgreSQL."
                )
            if self.connection_pool is None:
                raise RuntimeError(
                    "FLASK_ENV=production: PostgreSQL pool failed to initialize; "
                    "refusing SQLite fallback. Fix DATABASE_URL, SSL, or network."
                )

        # SQLite (default): file on disk or Render persistent disk
        self.db_type = "sqlite"
        if db_path is None:
            if os.path.exists("/opt/render/project/data"):
                db_path = "/opt/render/project/data/fikiri.db"
            else:
                db_path = "data/fikiri.db"

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path

        self._check_and_repair_database()
        self._initialize_database()
        self._ready = True
    
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
        if self.db_type == "postgresql":
            with self.get_connection() as conn:
                wrapped = PostgresBootstrapCursor(conn.cursor())
                self._create_optimized_tables(wrapped)
                self._create_indexes(wrapped)
                self._create_metrics_table(wrapped)
                self._run_migrations(wrapped)
                conn.commit()
            logger.info("PostgreSQL schema bootstrap complete (SQLite DDL translated + PRAGMA shim)")
            return

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
            if 'withdrawn_at' not in lead_columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN withdrawn_at TIMESTAMP")
                logger.info("✅ Added withdrawn_at column to leads table")

            # Email sync: run before heavier migrations — if a later step fails, inbox queries still work.
            cursor.execute("PRAGMA table_info(synced_emails)")
            synced_email_columns = [row[1] for row in cursor.fetchall()]
            if synced_email_columns:
                if 'external_id' not in synced_email_columns:
                    cursor.execute("ALTER TABLE synced_emails ADD COLUMN external_id TEXT")
                    logger.info("✅ Added external_id column to synced_emails table")
                if 'provider' not in synced_email_columns:
                    cursor.execute(
                        "ALTER TABLE synced_emails ADD COLUMN provider TEXT DEFAULT 'gmail'"
                    )
                    logger.info("✅ Added provider column to synced_emails table")
                if 'is_read' not in synced_email_columns:
                    cursor.execute(
                        "ALTER TABLE synced_emails ADD COLUMN is_read BOOLEAN DEFAULT 0"
                    )
                    logger.info("✅ Added is_read column to synced_emails table")

            cursor.execute("PRAGMA table_info(crm_events)")
            crm_event_columns = [row[1] for row in cursor.fetchall()]
            if crm_event_columns:
                if "user_id" not in crm_event_columns:
                    cursor.execute("ALTER TABLE crm_events ADD COLUMN user_id INTEGER")
                    if "tenant_user_id" in crm_event_columns:
                        cursor.execute(
                            "UPDATE crm_events SET user_id = tenant_user_id "
                            "WHERE user_id IS NULL"
                        )
                    logger.info("✅ Added user_id column to crm_events")
                if "status" not in crm_event_columns:
                    cursor.execute("ALTER TABLE crm_events ADD COLUMN status TEXT")
                    logger.info("✅ Added status column to crm_events")
                if "error_message" not in crm_event_columns:
                    cursor.execute("ALTER TABLE crm_events ADD COLUMN error_message TEXT")
                    logger.info("✅ Added error_message column to crm_events")
                if "source" not in crm_event_columns:
                    cursor.execute("ALTER TABLE crm_events ADD COLUMN source TEXT")
                    logger.info("✅ Added source column to crm_events")
                if "created_at" not in crm_event_columns:
                    cursor.execute(
                        "ALTER TABLE crm_events ADD COLUMN created_at TIMESTAMP"
                    )
                    if "occurred_at" in crm_event_columns:
                        cursor.execute(
                            "UPDATE crm_events SET created_at = occurred_at "
                            "WHERE created_at IS NULL"
                        )
                    else:
                        cursor.execute(
                            "UPDATE crm_events SET created_at = CURRENT_TIMESTAMP "
                            "WHERE created_at IS NULL"
                        )
                    logger.info("✅ Added created_at column to crm_events")
                if "occurred_at" in crm_event_columns:
                    cursor.execute(
                        "UPDATE crm_events SET created_at = occurred_at "
                        "WHERE created_at IS NULL AND occurred_at IS NOT NULL"
                    )

            # Chatbot query log: confidence breakdown for eval
            cursor.execute("PRAGMA table_info(chatbot_query_log)")
            qlog_columns = [row[1] for row in cursor.fetchall()]
            if qlog_columns and 'metadata' not in qlog_columns:
                cursor.execute("ALTER TABLE chatbot_query_log ADD COLUMN metadata TEXT")
                logger.info("✅ Added metadata column to chatbot_query_log")
            if qlog_columns and 'correlation_id' not in qlog_columns:
                cursor.execute("ALTER TABLE chatbot_query_log ADD COLUMN correlation_id TEXT")
                logger.info("✅ Added correlation_id column to chatbot_query_log")
            if qlog_columns and 'content_fingerprint' not in qlog_columns:
                cursor.execute("ALTER TABLE chatbot_query_log ADD COLUMN content_fingerprint TEXT")
                logger.info("✅ Added content_fingerprint column to chatbot_query_log")

            # Chatbot tables: canonical user_id (drop legacy tenant_user_id)
            self._migrate_chatbot_tables_user_id(cursor)

            # Conversation feedback: store confidence etc. with feedback
            cursor.execute("PRAGMA table_info(conversation_feedback)")
            cf_columns = [row[1] for row in cursor.fetchall()]
            if cf_columns and 'metadata' not in cf_columns:
                cursor.execute("ALTER TABLE conversation_feedback ADD COLUMN metadata TEXT")
                logger.info("✅ Added metadata column to conversation_feedback")
        except Exception as e:
            logger.warning(f"Migration warning: {e}")

    def _migrate_chatbot_tables_user_id(self, cursor) -> None:
        """Align chatbot_* tables with canonical user_id; remove tenant_user_id."""
        cursor.execute("PRAGMA table_info(chatbot_content_events)")
        ev_cols = [row[1] for row in cursor.fetchall()]
        if ev_cols:
            if "tenant_user_id" in ev_cols:
                cursor.execute("DROP INDEX IF EXISTS idx_chatbot_content_events_tenant_time")
                if "user_id" not in ev_cols:
                    cursor.execute(
                        "ALTER TABLE chatbot_content_events ADD COLUMN user_id INTEGER"
                    )
                    cursor.execute(
                        "UPDATE chatbot_content_events SET user_id = tenant_user_id"
                    )
                    logger.info("✅ Added user_id to chatbot_content_events (backfilled)")
                else:
                    cursor.execute(
                        "UPDATE chatbot_content_events SET user_id = COALESCE("
                        "user_id, tenant_user_id)"
                    )
                try:
                    cursor.execute(
                        "ALTER TABLE chatbot_content_events DROP COLUMN tenant_user_id"
                    )
                    logger.info("✅ Dropped tenant_user_id from chatbot_content_events")
                except Exception as drop_exc:  # noqa: BLE001
                    logger.warning(
                        "Could not DROP tenant_user_id from chatbot_content_events: %s",
                        drop_exc,
                    )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chatbot_content_events_user_time
                ON chatbot_content_events (user_id, created_at DESC)
                """
            )

        cursor.execute("PRAGMA table_info(chatbot_faq_current)")
        faq_cols = [row[1] for row in cursor.fetchall()]
        if faq_cols:
            if "tenant_user_id" in faq_cols:
                cursor.execute("DROP INDEX IF EXISTS idx_chatbot_faq_current_tenant")
                if "user_id" not in faq_cols:
                    cursor.execute("ALTER TABLE chatbot_faq_current ADD COLUMN user_id INTEGER")
                    cursor.execute(
                        "UPDATE chatbot_faq_current SET user_id = tenant_user_id"
                    )
                    logger.info("✅ Added user_id to chatbot_faq_current (backfilled)")
                else:
                    cursor.execute(
                        "UPDATE chatbot_faq_current SET user_id = COALESCE("
                        "user_id, tenant_user_id)"
                    )
                try:
                    cursor.execute(
                        "ALTER TABLE chatbot_faq_current DROP COLUMN tenant_user_id"
                    )
                    logger.info("✅ Dropped tenant_user_id from chatbot_faq_current")
                except Exception as drop_exc:  # noqa: BLE001
                    logger.warning(
                        "Could not DROP tenant_user_id from chatbot_faq_current: %s",
                        drop_exc,
                    )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chatbot_faq_current_user
                ON chatbot_faq_current (user_id)
                """
            )

        cursor.execute("PRAGMA table_info(chatbot_kb_current)")
        kb_cols = [row[1] for row in cursor.fetchall()]
        if kb_cols and "tenant_user_id" in kb_cols:
            if "user_id" not in kb_cols:
                cursor.execute("ALTER TABLE chatbot_kb_current ADD COLUMN user_id INTEGER")
                cursor.execute(
                    "UPDATE chatbot_kb_current SET user_id = tenant_user_id"
                )
                logger.info("✅ Added user_id to chatbot_kb_current (backfilled)")
            else:
                cursor.execute(
                    "UPDATE chatbot_kb_current SET user_id = COALESCE("
                    "user_id, tenant_user_id)"
                )
            try:
                cursor.execute(
                    "ALTER TABLE chatbot_kb_current DROP COLUMN tenant_user_id"
                )
                logger.info("✅ Dropped tenant_user_id from chatbot_kb_current")
            except Exception as drop_exc:  # noqa: BLE001
                logger.warning(
                    "Could not DROP tenant_user_id from chatbot_kb_current: %s",
                    drop_exc,
                )
    
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
        
        # OAuth states table for CSRF protection (single definition; was duplicated below)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                provider TEXT NOT NULL DEFAULT 'gmail',
                redirect_url TEXT,
                expires_at INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

        # Synced emails (Gmail/Outlook inbox copy) — required by dashboard timeseries & inbox routes.
        # Also created by email_automation/gmail_sync_jobs.py; must exist on fresh prod DB before any sync job runs.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synced_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gmail_id TEXT,
                external_id TEXT,
                provider TEXT DEFAULT 'gmail',
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                date DATETIME,
                body TEXT,
                labels TEXT DEFAULT '[]',
                attachments TEXT DEFAULT '[]',
                processed BOOLEAN DEFAULT FALSE,
                is_read BOOLEAN DEFAULT FALSE,
                lead_score INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, external_id, provider)
            )
        """)

        # Gmail sync job queue + contacts + sync status (also created in email_automation/gmail_sync_jobs.py).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gmail_sync_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                emails_synced INTEGER DEFAULT 0,
                contacts_found INTEGER DEFAULT 0,
                leads_identified INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                error_message TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                company TEXT,
                last_contact DATETIME,
                contact_count INTEGER DEFAULT 1,
                lead_score INTEGER DEFAULT 0,
                source TEXT DEFAULT 'gmail',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, email)
            )
        """)
        cursor.execute("""
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
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lead_activities_lead_id
            ON lead_activities (lead_id)
        """)

        # Append-only CRM audit / timeline (mutations also recorded from crm/service.py)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                correlation_id TEXT,
                supersedes_event_id INTEGER,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                status TEXT,
                error_message TEXT,
                source TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_crm_events_tenant_entity_time
            ON crm_events (user_id, entity_type, entity_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_crm_events_tenant_occurred
            ON crm_events (user_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_crm_events_tenant_event_type
            ON crm_events (user_id, event_type, created_at DESC)
        """)

        # Append-only AI lifecycle (LLM router + future approval/execution)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT 'ai',
                entity_id INTEGER,
                correlation_id TEXT,
                supersedes_event_id INTEGER,
                status TEXT,
                error_message TEXT,
                source TEXT,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_events_user_created
            ON ai_events (user_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_events_correlation
            ON ai_events (correlation_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_events_type_created
            ON ai_events (event_type, created_at DESC)
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

        # User customization / branding (logo, colors, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_customizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                logo_data_url TEXT,
                accent_color TEXT,
                company_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)

        # Public customer submissions (contact form, etc.)
        # Stored to DB so we can route/triage later even if email providers fail temporarily.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_contact_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_type TEXT NOT NULL DEFAULT 'contact',
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                company TEXT,
                subject TEXT,
                message TEXT NOT NULL,
                email_subject TEXT,
                to_email TEXT,
                from_email TEXT,
                payload_json TEXT,          -- best-effort raw request payload (JSON-serialized)
                payload_truncated BOOLEAN DEFAULT 0,
                send_status TEXT NOT NULL DEFAULT 'pending',  -- pending, sent, failed
                send_error TEXT,
                request_ip TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_contact_submissions_email
            ON customer_contact_submissions (email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_contact_submissions_created_at
            ON customer_contact_submissions (created_at)
        """)

        # Backfill schema for existing DBs (dev envs may already have this table)
        cursor.execute("PRAGMA table_info(customer_contact_submissions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'payload_json' not in columns:
            cursor.execute("ALTER TABLE customer_contact_submissions ADD COLUMN payload_json TEXT")
        if 'payload_truncated' not in columns:
            cursor.execute("ALTER TABLE customer_contact_submissions ADD COLUMN payload_truncated BOOLEAN DEFAULT 0")

        # Public intake submissions (webhook forms / lead captures)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_form_intake_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,              -- authenticated API key owner (if provided)
                api_key_id TEXT,
                form_id TEXT,
                source TEXT,
                email TEXT,
                name TEXT,
                phone TEXT,
                company TEXT,
                subject TEXT,
                payload_json TEXT,
                payload_truncated BOOLEAN DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'received', -- received, completed, deduplicated, failed, honeypot_filled, updated, cancelled
                error TEXT,
                lead_id TEXT,
                client_submission_id TEXT,
                supersedes_intake_id INTEGER,
                request_ip TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_form_intake_email
            ON customer_form_intake_submissions (email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_form_intake_created_at
            ON customer_form_intake_submissions (created_at)
        """)

        cursor.execute("PRAGMA table_info(customer_form_intake_submissions)")
        _form_intake_cols = [row[1] for row in cursor.fetchall()]
        if "client_submission_id" not in _form_intake_cols:
            cursor.execute(
                "ALTER TABLE customer_form_intake_submissions ADD COLUMN client_submission_id TEXT"
            )
        if "supersedes_intake_id" not in _form_intake_cols:
            cursor.execute(
                "ALTER TABLE customer_form_intake_submissions ADD COLUMN supersedes_intake_id INTEGER"
            )

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_form_intake_user_form_client_submission
            ON customer_form_intake_submissions (user_id, form_id, client_submission_id)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_lead_capture_intake_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                api_key_id TEXT,
                source TEXT,
                email TEXT,
                name TEXT,
                phone TEXT,
                company TEXT,
                payload_json TEXT,
                payload_truncated BOOLEAN DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'received', -- received, completed, deduplicated, failed
                error TEXT,
                lead_id TEXT,
                request_ip TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_lead_capture_email
            ON customer_lead_capture_intake_submissions (email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_lead_capture_created_at
            ON customer_lead_capture_intake_submissions (created_at)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                correlation_id TEXT,
                content_fingerprint TEXT
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                user_id TEXT,
                tenant_id TEXT,
                category TEXT NOT NULL,
                route TEXT NOT NULL,
                conversation_id TEXT,
                message_id TEXT,
                correlation_id TEXT,
                payload_json TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_feedback_events_route_created
            ON user_feedback_events (route, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_feedback_events_user_created
            ON user_feedback_events (user_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_feedback_events_tenant_created
            ON user_feedback_events (tenant_id, created_at DESC)
        """)

        # Append-only chatbot / FAQ / KB content events (audit + rollback-ready snapshots)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_content_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                source TEXT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                correlation_id TEXT,
                supersedes_event_id INTEGER,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'applied',
                error_message TEXT
            )
        """)
        # idx_chatbot_content_events_user_time is created in _migrate_chatbot_tables_user_id
        # so existing DBs get user_id column before indexing.
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chatbot_content_events_entity
            ON chatbot_content_events (entity_type, entity_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chatbot_content_events_correlation
            ON chatbot_content_events (correlation_id)
        """)

        # Durable current-state rows for FAQ (serving + sync with events)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_faq_current (
                faq_id TEXT PRIMARY KEY,
                user_id INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT NOT NULL,
                keywords_json TEXT,
                variations_json TEXT,
                priority INTEGER NOT NULL DEFAULT 1,
                content_version INTEGER NOT NULL DEFAULT 1,
                last_event_id INTEGER,
                vector_key TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # idx_chatbot_faq_current_user is created in _migrate_chatbot_tables_user_id

        # Durable current-state rows for knowledge documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_kb_current (
                doc_id TEXT PRIMARY KEY,
                user_id INTEGER,
                tenant_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                document_type TEXT NOT NULL,
                format TEXT NOT NULL DEFAULT 'markdown',
                category TEXT,
                tags_json TEXT,
                keywords_json TEXT,
                author TEXT,
                metadata_json TEXT,
                content_version INTEGER NOT NULL DEFAULT 1,
                last_event_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chatbot_kb_current_tenant_id
            ON chatbot_kb_current (tenant_id)
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

        # Appointment / booking intake (after appointments — Postgres validates FKs at CREATE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_appointment_intake_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT,
                appointment_id INTEGER,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                service_type TEXT,
                requested_date DATE,
                requested_time TIME,
                timezone TEXT,
                status TEXT NOT NULL DEFAULT 'received',  -- received, completed, rescheduled, cancelled, failed, deduplicated
                error_message TEXT,
                payload_json TEXT,
                payload_truncated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_appointment_intake_user_id
            ON customer_appointment_intake_submissions (user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_appointment_intake_appointment_id
            ON customer_appointment_intake_submissions (appointment_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_appointment_intake_customer_email
            ON customer_appointment_intake_submissions (customer_email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_appointment_intake_created_at
            ON customer_appointment_intake_submissions (created_at)
        """)

        # Backfill for existing DBs missing columns (best-effort).
        cursor.execute("PRAGMA table_info(customer_appointment_intake_submissions)")
        cols = [row[1] for row in cursor.fetchall()]
        # These columns are intentionally safe to backfill with ALTER TABLE.
        if 'payload_truncated' not in cols:
            cursor.execute("ALTER TABLE customer_appointment_intake_submissions ADD COLUMN payload_truncated BOOLEAN DEFAULT 0")
        if 'payload_json' not in cols:
            cursor.execute("ALTER TABLE customer_appointment_intake_submissions ADD COLUMN payload_json TEXT")
        if 'updated_at' not in cols:
            cursor.execute("ALTER TABLE customer_appointment_intake_submissions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                provider TEXT,
                message_id TEXT,
                thread_id TEXT,
                synced_email_id INTEGER,
                lead_id INTEGER,
                correlation_id TEXT,
                supersedes_event_id INTEGER,
                idempotency_key TEXT,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                status TEXT,
                error_message TEXT,
                source TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_events_user_created
            ON email_events (user_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_events_user_message
            ON email_events (user_id, message_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_events_user_correlation
            ON email_events (user_id, correlation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_events_user_type_created
            ON email_events (user_id, event_type, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_events_lead
            ON email_events (lead_id)
            WHERE lead_id IS NOT NULL
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
            ("idx_synced_emails_user_id", "synced_emails", ["user_id"]),
            ("idx_gmail_sync_jobs_user_id", "gmail_sync_jobs", ["user_id"]),
            ("idx_contacts_user_id", "contacts", ["user_id"]),
            ("idx_user_sync_status_user_id", "user_sync_status", ["user_id"]),
            
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
            # Leads table indexes (CRM / webhook queries; prevents slow dashboards)
            ("idx_leads_user_id", "leads", ["user_id"]),
            ("idx_leads_email", "leads", ["email"]),
            ("idx_leads_created_at", "leads", ["created_at"]),
            # Tenant list sorted by recency: WHERE user_id = ? ORDER BY created_at DESC
            ("idx_leads_user_created", "leads", ["user_id", "created_at"]),
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
        active_user_pred = self.sql_cast_int_eq_one("is_active")
        recent_lead_pred = self.sql_column_newer_than_n_days_ago("l.created_at", 30)
        
        # Active users view
        cursor.execute(f"""
            CREATE VIEW IF NOT EXISTS active_users AS
            SELECT id, email, name, role, business_name, created_at, last_login
            FROM users 
            WHERE {active_user_pred}
        """)
        
        # Recent leads view
        cursor.execute(f"""
            CREATE VIEW IF NOT EXISTS recent_leads AS
            SELECT l.*, u.name as user_name, u.email as user_email
            FROM leads l
            JOIN users u ON l.user_id = u.id
            WHERE {recent_lead_pred}
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
            if conn and self.db_type == "postgresql" and self.connection_pool:
                discard_conn = False
                try:
                    conn.commit()
                except Exception as commit_err:
                    logger.debug("Postgres commit on release: %s", commit_err)
                    discard_conn = True
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                try:
                    if getattr(conn, "closed", 0):
                        discard_conn = True
                except Exception:
                    discard_conn = True
                try:
                    self.connection_pool.putconn(conn, close=discard_conn)
                except Exception as pool_error:
                    logger.debug("Failed to return PostgreSQL connection to pool: %s", pool_error)
            elif conn and self.db_type != "postgresql":
                try:
                    conn.close()
                except Exception as close_error:
                    logger.debug("Failed to close SQLite connection: %s", close_error)

    def probe_database_for_health(self, max_wait_seconds: float = 2.0) -> None:
        """
        Lightweight DB check for load balancers and /api/health.

        ``get_connection`` uses a 30s SQLite busy timeout so normal queries can wait
        for writers; health probes should not hold gevent/async workers that long.
        Raises on failure (caller marks DB disconnected).
        """
        if self.db_type == "postgresql" and self.connection_pool:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            return
        busy_ms = max(int(max_wait_seconds * 1000), 100)
        conn = sqlite3.connect(self.db_path, timeout=max_wait_seconds, check_same_thread=False)
        try:
            conn.execute(f"PRAGMA busy_timeout={busy_ms}")
            conn.execute("SELECT 1")
        finally:
            conn.close()

    def sql_cast_int_eq_one(self, column_expr: str) -> str:
        """
        Portable active/valid predicate: SQLite stores 0/1; PostgreSQL uses BOOLEAN.
        ``boolean = 1`` is invalid in Postgres; CAST works for both.
        """
        return f"(CAST({column_expr} AS INTEGER) = 1)"

    def _pg_ts(self, column_expr: str) -> str:
        """
        Cast a column to timestamptz for postgres comparisons.

        Some legacy tables (e.g. automation_jobs) declare timestamp columns
        as TEXT and store ISO strings, so a direct `text > timestamptz`
        comparison fails with `operator does not exist`. Casting is a no-op
        for native TIMESTAMP/TIMESTAMPTZ columns and parses ISO strings.
        """
        return f"({column_expr})::timestamptz"

    def sql_timestamp_gt_now(self, column_expr: str) -> str:
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} > CURRENT_TIMESTAMP)"
        return f"(datetime({column_expr}) > datetime('now'))"

    def sql_timestamp_lt_now(self, column_expr: str) -> str:
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} < CURRENT_TIMESTAMP)"
        return f"(datetime({column_expr}) < datetime('now'))"

    def sql_column_newer_than_n_hours_ago(self, column_expr: str, hours: int) -> str:
        """True when column is strictly after (current time - hours). SQLite vs PostgreSQL."""
        h = max(1, int(hours))
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} > (CURRENT_TIMESTAMP - ({h} * INTERVAL '1 hour')))"
        return f"(datetime({column_expr}) > datetime('now', '-{h} hours'))"

    def sql_column_newer_than_n_minutes_ago(self, column_expr: str, minutes: int) -> str:
        m = max(1, int(minutes))
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} > (CURRENT_TIMESTAMP - ({m} * INTERVAL '1 minute')))"
        return f"(datetime({column_expr}) > datetime('now', '-{m} minutes'))"

    def sql_column_newer_than_n_seconds_ago(self, column_expr: str, seconds: int) -> str:
        s = max(1, int(seconds))
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} > (CURRENT_TIMESTAMP - ({s} * INTERVAL '1 second')))"
        return f"(datetime({column_expr}) > datetime('now', '-{s} seconds'))"

    def sql_column_older_than_n_minutes_ago(self, column_expr: str, minutes: int) -> str:
        """True when column is strictly before (current time - minutes)."""
        m = max(1, int(minutes))
        if self.db_type == "postgresql":
            return f"({self._pg_ts(column_expr)} < (CURRENT_TIMESTAMP - ({m} * INTERVAL '1 minute')))"
        return f"(datetime({column_expr}) < datetime('now', '-{m} minutes'))"

    def sql_column_newer_than_n_days_ago(self, column_expr: str, days: int) -> str:
        """Same as n_hours with days * 24 (readable call sites for week/month windows)."""
        d = max(1, int(days))
        return self.sql_column_newer_than_n_hours_ago(column_expr, d * 24)

    def sql_false_literal(self) -> str:
        """Literal for UPDATE ... SET flag = ... (BOOLEAN vs INTEGER)."""
        return "FALSE" if self.db_type == "postgresql" else "0"

    def sql_true_literal(self) -> str:
        """Literal for UPDATE ... SET truthy flag = ... (BOOLEAN vs INTEGER)."""
        return "TRUE" if self.db_type == "postgresql" else "1"

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
    
    def _is_retryable_postgres_error(self, error: Exception) -> bool:
        """Detect transient PostgreSQL connection/SSL failures worth one retry."""
        msg = str(error).lower()
        retry_markers = (
            "ssl error: decryption failed or bad record mac",
            "server closed the connection unexpectedly",
            "terminating connection due to administrator command",
            "could not receive data from server",
            "connection already closed",
            "connection not open",
        )
        return any(marker in msg for marker in retry_markers)

    def execute_query(self, query: str, params: Tuple = None, fetch: bool = True, 
                     user_id: int = None, endpoint: str = None, _retry_depth: int = 0) -> Any:
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
                q_strip = query.strip()
                q_upper = q_strip.upper()
                is_select_like = q_upper.startswith(("SELECT", "PRAGMA", "WITH"))

                if self.db_type == "postgresql":
                    from psycopg2.extras import RealDictCursor

                    raw = query.strip()
                    if should_translate_sqlite_ddl(raw):
                        q_pg = adapt_qmark_params_to_psycopg2(
                            translate_sqlite_ddl_to_postgres(query)
                        )
                    else:
                        q_pg = adapt_qmark_params_to_psycopg2(query)
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    if params:
                        cursor.execute(q_pg, params)
                    else:
                        cursor.execute(q_pg)
                else:
                    if should_translate_sqlite_ddl(q_strip):
                        query = translate_postgres_ddl_to_sqlite(query)
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                if fetch:
                    if is_select_like:
                        result = cursor.fetchall()
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
                    if fetch and is_select_like:
                        rows_affected = len(result) if isinstance(result, list) else (1 if result else 0)
                    else:
                        rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0

                    self._record_query_metrics(
                        query,
                        execution_time,
                        rows_affected,
                        True,
                        user_id=user_id,
                        endpoint=endpoint,
                    )
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            # Only record metrics on error if ready
            if self._ready:
                self._record_query_metrics(query, execution_time, 0, False, str(e),
                                         user_id=user_id, endpoint=endpoint)
            if self.db_type == "postgresql" and _retry_depth == 0 and self._is_retryable_postgres_error(e):
                logger.warning("Retrying transient PostgreSQL error once: %s", e)
                time.sleep(0.1)
                return self.execute_query(
                    query,
                    params=params,
                    fetch=fetch,
                    user_id=user_id,
                    endpoint=endpoint,
                    _retry_depth=1,
                )
            logger.error(f"Query execution error: {e}")
            raise

    @contextmanager
    def transaction(self):
        """
        Yield (conn, cursor) for a single transactional block where multiple
        statements must execute atomically (e.g. conflict-check + insert).

        On PostgreSQL the cursor is wrapped with ``PostgresBootstrapCursor`` so
        SQLite-style ``?`` placeholders are translated to psycopg2's ``%s`` and
        any inline DDL is also adapted. Callers should still issue ``RETURNING``
        explicitly when they need the inserted id; do NOT rely on
        ``cursor.lastrowid`` (always ``None`` on psycopg2).

        On SQLite the cursor is the raw sqlite3 cursor; ``cursor.lastrowid`` is
        valid as usual.

        The caller is responsible for ``conn.commit()`` on success. On any
        exception the transaction is rolled back before the exception
        propagates.
        """
        with self.get_connection() as conn:
            if self.db_type == "postgresql":
                from psycopg2.extras import RealDictCursor
                cursor = PostgresBootstrapCursor(conn.cursor(cursor_factory=RealDictCursor))
            else:
                cursor = conn.cursor()
            try:
                yield conn, cursor
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise

    def execute_insert_returning_id(self, query: str, params: Tuple = None) -> Optional[int]:
        """Run INSERT on a single connection and return lastrowid (SQLite). Best-effort for Postgres."""
        if self.db_type == "postgresql":
            from psycopg2.extras import RealDictCursor

            q_pg = adapt_qmark_params_to_psycopg2(query)
            if "RETURNING" not in q_pg.upper():
                q_pg = q_pg.rstrip().rstrip(";") + " RETURNING id"
            with self.get_connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                if params:
                    cur.execute(q_pg, params)
                else:
                    cur.execute(q_pg)
                row = cur.fetchone()
                conn.commit()
                if row and row.get("id") is not None:
                    return int(row["id"])
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rid = getattr(cursor, "lastrowid", None)
            conn.commit()
            return int(rid) if rid is not None else None
    
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
            import json

            serialized_error = error
            if isinstance(error, (list, dict)):
                serialized_error = json.dumps(error)

            serialized_user_id = user_id
            if isinstance(user_id, (list, dict)):
                serialized_user_id = json.dumps(user_id)

            serialized_endpoint = endpoint
            if isinstance(endpoint, (list, dict)):
                serialized_endpoint = json.dumps(endpoint)

            if self.db_type == "postgresql":
                self.execute_query(
                    """
                    INSERT INTO query_performance_log
                    (query_hash, query_text, execution_time, rows_affected, success, error_message, user_id, endpoint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query_hash,
                        query[:500],
                        execution_time,
                        rows_affected,
                        success,
                        serialized_error,
                        serialized_user_id,
                        serialized_endpoint,
                    ),
                    fetch=False,
                )
            else:
                import sqlite3

                conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO query_performance_log
                    (query_hash, query_text, execution_time, rows_affected, success, error_message, user_id, endpoint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query_hash,
                        query[:500],
                        execution_time,
                        rows_affected,
                        success,
                        serialized_error,
                        serialized_user_id,
                        serialized_endpoint,
                    ),
                )
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
        optimization_results: Dict[str, Any] = {}

        if self.db_type == "postgresql":
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("ANALYZE")
            optimization_results["analyze"] = "Completed"
            optimization_results["note"] = "VACUUM/sqlite_master skipped on PostgreSQL"
            return optimization_results

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
        """
        Comprehensive database statistics for both backends.

        SQLite path uses ``sqlite_master`` + ``PRAGMA page_count/page_size``.
        Postgres path uses ``information_schema.tables`` for the table list
        and ``pg_total_relation_size()`` aggregated over the same set for
        size. ``pg_relation_size`` covers heap only, so the total form gives
        a number comparable to SQLite's page-count * page-size value.
        """
        stats: Dict[str, Any] = {}

        if self.db_type == "postgresql":
            tables_rows = self.execute_query(
                """
                SELECT t.table_name,
                       COALESCE(i.index_count, 0) AS index_count
                FROM information_schema.tables t
                LEFT JOIN (
                    SELECT schemaname, tablename, COUNT(*) AS index_count
                    FROM pg_indexes
                    GROUP BY schemaname, tablename
                ) i
                  ON i.schemaname = t.table_schema
                 AND i.tablename = t.table_name
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
                """
            ) or []
            stats["tables"] = [
                {"name": r.get("table_name") if isinstance(r, dict) else r[0],
                 "index_count": r.get("index_count") if isinstance(r, dict) else r[1]}
                for r in tables_rows
            ]
            for entry in stats["tables"]:
                tname = entry["name"]
                if not tname or not tname.replace("_", "").isalnum():
                    continue
                try:
                    cnt_rows = self.execute_query(f"SELECT COUNT(*) AS c FROM public.\"{tname}\"")
                    if cnt_rows:
                        row = cnt_rows[0]
                        stats[f"{tname}_count"] = row.get("c") if isinstance(row, dict) else row[0]
                except Exception as exc:
                    logger.warning("Could not get count for table %s: %s", tname, exc)
            try:
                size_rows = self.execute_query(
                    """
                    SELECT COALESCE(SUM(pg_total_relation_size(c.oid)), 0) AS total
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relkind = 'r'
                    """
                )
                if size_rows:
                    row = size_rows[0]
                    stats["database_size_bytes"] = int(row.get("total") if isinstance(row, dict) else row[0])
                else:
                    stats["database_size_bytes"] = 0
            except Exception as exc:
                logger.warning("Could not get database size: %s", exc)
                stats["database_size_bytes"] = 0
            return stats

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name,
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as table_count,
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as index_count
                FROM sqlite_master m
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
            )
            tables = cursor.fetchall()
            stats["tables"] = [
                {"name": table[0], "index_count": table[2]} for table in tables
            ]
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[f"{table_name}_count"] = count
                except Exception as e:
                    logger.warning("Could not get count for table %s: %s", table_name, e)
            try:
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats["database_size_bytes"] = page_count * page_size
            except Exception as e:
                logger.warning("Could not get database size: %s", e)
                stats["database_size_bytes"] = 0

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
            """
            INSERT INTO system_config (key, value)
            VALUES (?, ?)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
            """,
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
                """
                INSERT INTO system_config (key, value)
                VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
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
            if self.db_type == "postgresql":
                res = self.execute_query(
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM information_schema.tables
                      WHERE table_schema = 'public' AND table_name = ?
                    ) AS e
                    """,
                    (table_name.lower(),),
                )
                if not res:
                    return False
                row = res[0]
                if isinstance(row, dict):
                    v = row.get("e")
                    return bool(v)
                return bool(row[0])
            q = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
            res = self.execute_query(q, (table_name,))
            return bool(res)
        except Exception as e:
            logger.warning(f"Could not check if table {table_name} exists: {e}")
            return False

    def list_table_columns(self, table_name: str):
        """
        Ordered column names for a table. Used instead of PRAGMA on PostgreSQL
        (PRAGMA is SQLite-only).
        """
        ident = "".join(c for c in (table_name or "") if c.isalnum() or c == "_")
        if not ident:
            return []
        try:
            if self.db_type == "postgresql":
                rows = self.execute_query(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ?
                    ORDER BY ordinal_position
                    """,
                    (ident.lower(),),
                )
                names = []
                for row in rows or []:
                    if isinstance(row, dict):
                        c = row.get("column_name")
                    else:
                        c = row[0]
                    if c:
                        names.append(str(c))
                return names
            rows = self.execute_query(f"PRAGMA table_info({ident})", fetch=True)
            names = []
            for row in rows or []:
                if isinstance(row, dict):
                    n = row.get("name")
                else:
                    n = row[1]
                if n:
                    names.append(str(n))
            return names
        except Exception as e:
            logger.warning("list_table_columns failed for %s: %s", ident, e)
            return []

    def upsert_user_services_row(
        self,
        user_id,
        service_id,
        service_name,
        enabled,
        status,
        settings_json,
    ) -> None:
        """Upsert user_services on UNIQUE(user_id, service_id)."""
        params = (user_id, service_id, service_name, enabled, status, settings_json)
        if self.db_type == "postgresql":
            self.execute_query(
                """
                INSERT INTO user_services (
                    user_id, service_id, service_name, enabled, status, settings, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, service_id) DO UPDATE SET
                    service_name = EXCLUDED.service_name,
                    enabled = EXCLUDED.enabled,
                    status = EXCLUDED.status,
                    settings = EXCLUDED.settings,
                    updated_at = CURRENT_TIMESTAMP
                """,
                params,
                fetch=False,
            )
        else:
            self.execute_query(
                """
                INSERT OR REPLACE INTO user_services
                (user_id, service_id, service_name, enabled, status, settings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                params,
                fetch=False,
            )

    def upsert_user_sync_status_pending(self, user_id: int) -> None:
        """Mark sync as pending for user (portable upsert on user_id)."""
        self.execute_query(
            """
            INSERT INTO user_sync_status (user_id, last_sync, sync_status, syncing, updated_at)
            VALUES (?, CURRENT_TIMESTAMP, 'pending', 1, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                last_sync = EXCLUDED.last_sync,
                sync_status = EXCLUDED.sync_status,
                syncing = EXCLUDED.syncing,
                updated_at = EXCLUDED.updated_at
            """,
            (user_id,),
            fetch=False,
        )

    def upsert_user_sync_status_completed(self, user_id: int, total_emails: int) -> None:
        """Mark sync completed and set total_emails (portable upsert on user_id)."""
        self.execute_query(
            """
            INSERT INTO user_sync_status (
                user_id, last_sync, sync_status, syncing, total_emails, updated_at
            ) VALUES (?, CURRENT_TIMESTAMP, 'completed', 0, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                last_sync = EXCLUDED.last_sync,
                sync_status = EXCLUDED.sync_status,
                syncing = EXCLUDED.syncing,
                total_emails = EXCLUDED.total_emails,
                updated_at = EXCLUDED.updated_at
            """,
            (user_id, total_emails),
            fetch=False,
        )

    def upsert_user_sync_status_merge(self, user_id: int, **kwargs: Any) -> None:
        """
        Upsert user_sync_status on user_id updating only provided columns (plus updated_at).
        Allowed keys: last_sync, sync_status, syncing, total_emails.
        """
        allowed = ("last_sync", "sync_status", "syncing", "total_emails")
        for k in kwargs:
            if k not in allowed:
                raise ValueError(f"upsert_user_sync_status_merge: unknown field {k!r}")
        field_names = [k for k in allowed if k in kwargs]
        if not field_names:
            raise ValueError("upsert_user_sync_status_merge: need at least one field")
        cols = ["user_id"] + field_names + ["updated_at"]
        ph = ", ".join(["?"] * (1 + len(field_names))) + ", CURRENT_TIMESTAMP"
        params = tuple([user_id] + [kwargs[k] for k in field_names])
        set_parts = [f"{k} = EXCLUDED.{k}" for k in field_names] + ["updated_at = EXCLUDED.updated_at"]
        sql = f"""
            INSERT INTO user_sync_status ({", ".join(cols)})
            VALUES ({ph})
            ON CONFLICT (user_id) DO UPDATE SET {", ".join(set_parts)}
        """
        self.execute_query(sql, params, fetch=False)

    def upsert_synced_email_from_gmail(
        self,
        user_id: int,
        gmail_id: str,
        thread_id: Any,
        subject: str,
        sender: str,
        recipient: str,
        date_iso: str,
        body: str,
        labels_json: str,
        is_read: int,
    ) -> None:
        """
        Upsert a Gmail row into synced_emails using UNIQUE(user_id, external_id, provider).
        external_id is set to gmail_id so Postgres ON CONFLICT matches the schema.
        """
        params = (
            user_id,
            gmail_id,
            gmail_id,
            "gmail",
            thread_id,
            subject,
            sender,
            recipient,
            date_iso,
            body,
            labels_json,
            is_read,
        )
        self.execute_query(
            """
            INSERT INTO synced_emails (
                user_id, gmail_id, external_id, provider, thread_id, subject, sender, recipient,
                date, body, labels, is_read
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, external_id, provider) DO UPDATE SET
                gmail_id = EXCLUDED.gmail_id,
                thread_id = EXCLUDED.thread_id,
                subject = EXCLUDED.subject,
                sender = EXCLUDED.sender,
                recipient = EXCLUDED.recipient,
                date = EXCLUDED.date,
                body = EXCLUDED.body,
                labels = EXCLUDED.labels,
                is_read = EXCLUDED.is_read
            """,
            params,
            fetch=False,
        )

    def upsert_oauth_state_row(
        self,
        state: str,
        user_id: Optional[int],
        provider: str,
        redirect_url: Any,
        expires_at: int,
        metadata_json: Optional[str] = None,
    ) -> None:
        """Upsert oauth_states row (state is UNIQUE)."""
        cols = "state, user_id, provider, redirect_url, expires_at"
        vals = "?, ?, ?, ?, ?"
        params: Tuple[Any, ...] = (state, user_id, provider, redirect_url, expires_at)
        if metadata_json is not None:
            cols += ", metadata"
            vals += ", ?"
            params = params + (metadata_json,)
        if self.db_type == "postgresql":
            set_meta = (
                "metadata = EXCLUDED.metadata"
                if metadata_json is not None
                else "metadata = oauth_states.metadata"
            )
            self.execute_query(
                f"""
                INSERT INTO oauth_states ({cols})
                VALUES ({vals})
                ON CONFLICT (state) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    provider = EXCLUDED.provider,
                    redirect_url = EXCLUDED.redirect_url,
                    expires_at = EXCLUDED.expires_at,
                    {set_meta}
                """,
                params,
                fetch=False,
            )
        else:
            self.execute_query(
                f"""
                INSERT OR REPLACE INTO oauth_states ({cols})
                VALUES ({vals})
                """,
                params,
                fetch=False,
            )

    def upsert_kpi_snapshot_row(
        self, snapshot_date: str, company_stage: str, kpi_type: str, kpi_value: Any
    ) -> None:
        """Upsert kpi_snapshots on UNIQUE(snapshot_date, company_stage, kpi_type)."""
        params = (snapshot_date, company_stage, kpi_type, kpi_value)
        if self.db_type == "postgresql":
            self.execute_query(
                """
                INSERT INTO kpi_snapshots (snapshot_date, company_stage, kpi_type, kpi_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (snapshot_date, company_stage, kpi_type) DO UPDATE SET
                    kpi_value = EXCLUDED.kpi_value
                """,
                params,
                fetch=False,
            )
        else:
            self.execute_query(
                """
                INSERT OR REPLACE INTO kpi_snapshots
                (snapshot_date, company_stage, kpi_type, kpi_value)
                VALUES (?, ?, ?, ?)
                """,
                params,
                fetch=False,
            )

    def upsert_stripe_subscription_row(
        self,
        user_id: int,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        status: str,
        tier: str,
        billing_period: str,
        current_period_start: Any,
        current_period_end: Any,
        trial_end: Any,
        cancel_at_period_end: Any,
    ) -> None:
        """Upsert subscriptions cache row (stripe_subscription_id is UNIQUE)."""
        params = (
            user_id,
            stripe_customer_id,
            stripe_subscription_id,
            status,
            tier,
            billing_period,
            current_period_start,
            current_period_end,
            trial_end,
            cancel_at_period_end,
        )
        if self.db_type == "postgresql":
            self.execute_query(
                """
                INSERT INTO subscriptions (
                    user_id, stripe_customer_id, stripe_subscription_id, status, tier,
                    billing_period, current_period_start, current_period_end,
                    trial_end, cancel_at_period_end, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    status = EXCLUDED.status,
                    tier = EXCLUDED.tier,
                    billing_period = EXCLUDED.billing_period,
                    current_period_start = EXCLUDED.current_period_start,
                    current_period_end = EXCLUDED.current_period_end,
                    trial_end = EXCLUDED.trial_end,
                    cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                    updated_at = CURRENT_TIMESTAMP
                """,
                params,
                fetch=False,
            )
        else:
            self.execute_query(
                """
                INSERT OR REPLACE INTO subscriptions 
                (user_id, stripe_customer_id, stripe_subscription_id, status, tier,
                 billing_period, current_period_start, current_period_end, 
                 trial_end, cancel_at_period_end, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                params,
                fetch=False,
            )

    def json_field_expr(self, column: str, dotted_path: str) -> str:
        """Portable JSON field read (SQLite json_extract vs PostgreSQL ::jsonb)."""
        key = (dotted_path or "").strip()
        if key.startswith("$."):
            key = key[2:]
        if not key or not re.match(r"^[a-zA-Z0-9_]+$", key):
            raise ValueError("json_field_expr supports simple $.identifier paths only")
        if self.db_type == "postgresql":
            return f"({column}::jsonb->>'{key}')"
        esc = (dotted_path or "").replace("'", "''")
        return f"json_extract({column}, '{esc}')"

# Global database optimizer instance
db_optimizer = DatabaseOptimizer()
