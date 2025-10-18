#!/usr/bin/env python3
"""
Prestart initialization script for Fikiri Solutions.
Ensures database schema is created before workers start.
"""

import os
import sys
import sqlite3
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_init_lock(db_path):
    """Create initialization lock to prevent double initialization."""
    lock_path = Path(db_path).parent / ".db_init_lock"
    if lock_path.exists():
        print("✅ Database already initialized (lock file exists)")
        return True
    
    # Create lock file
    lock_path.write_text(f"initialized_at={time.time()}")
    return False

def initialize_database():
    """Initialize database schema with proper order."""
    db_path = "data/fikiri.db"
    
    # Check if already initialized
    if create_init_lock(db_path):
        return True
    
    print("🚀 Initializing database schema...")
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Create tables in proper order (metrics first)
        tables_sql = [
            # Core system tables first
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Metrics table (critical for avoiding race conditions)
            """
            CREATE TABLE IF NOT EXISTS query_performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                query_type TEXT,
                execution_time REAL,
                rows_affected INTEGER,
                success BOOLEAN,
                error_message TEXT,
                user_id INTEGER,
                endpoint TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # User tables
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'user',
                onboarding_completed BOOLEAN DEFAULT FALSE,
                onboarding_step INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            
            # JWT and session tables
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                device_id TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            
            # Other essential tables
            """
            CREATE TABLE IF NOT EXISTS email_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email_id TEXT,
                job_type TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                name TEXT,
                company TEXT,
                status TEXT DEFAULT 'new',
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Rate limiting
            """
            CREATE TABLE IF NOT EXISTS rate_limit_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                endpoint TEXT,
                violation_count INTEGER DEFAULT 1,
                first_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        # Execute all table creation statements
        for sql in tables_sql:
            cursor.execute(sql)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_query_performance_timestamp ON query_performance_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_query_performance_user ON query_performance_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_email_jobs_user ON email_jobs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)",
            "CREATE INDEX IF NOT EXISTS idx_rate_limit_ip ON rate_limit_violations(ip_address)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Insert schema version
        cursor.execute("""
            INSERT OR REPLACE INTO system_config (key, value) 
            VALUES ('schema_version', '1.0.0')
        """)
        
        conn.commit()
        print("✅ Database schema initialized successfully")
        
        # Verify critical tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'query_performance_log', 'email_jobs')")
        tables = [row[0] for row in cursor.fetchall()]
        
        if len(tables) == 3:
            print("✅ All critical tables verified")
            return True
        else:
            print(f"❌ Missing tables: {set(['users', 'query_performance_log', 'email_jobs']) - set(tables)}")
            return False
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main prestart function."""
    print("🔧 Fikiri Solutions Prestart Initialization")
    
    if initialize_database():
        print("✅ Prestart initialization completed successfully")
        sys.exit(0)
    else:
        print("❌ Prestart initialization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
