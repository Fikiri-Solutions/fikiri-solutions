"""
Database initialization module for Fikiri Solutions
Ensures all required tables exist on startup
"""
import os
import logging
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

PERSISTENT_DB_PATH = "/opt/render/project/data/fikiri.db"

def ensure_persistent_storage():
    """Ensure the persistent Render storage path exists"""
    try:
        os.makedirs(os.path.dirname(PERSISTENT_DB_PATH), exist_ok=True)
        if not os.path.exists(PERSISTENT_DB_PATH):
            logger.info(f"📁 Creating new persistent database at {PERSISTENT_DB_PATH}")
            open(PERSISTENT_DB_PATH, "a").close()
        else:
            logger.info("✅ Persistent database file confirmed.")
    except Exception as e:
        logger.error(f"❌ Failed to ensure persistent storage: {e}")

def init_database():
    """Initialize all required database tables"""
    try:
        logger.info("🔧 Initializing database tables...")

        # Ensure persistent path
        ensure_persistent_storage()
        
        # Users table with consistent schema
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            business_name TEXT,
            business_email TEXT,
            industry TEXT,
            team_size TEXT,
            metadata TEXT,
            is_active INTEGER DEFAULT 1,
            email_verified INTEGER DEFAULT 0,
            onboarding_completed BOOLEAN DEFAULT 0,
            onboarding_step INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 🔹 Add user_sessions (missing table)
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_valid INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)
        
        # Onboarding info table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS onboarding_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            industry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)
        
        # Query performance log table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS query_performance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_name TEXT,
            query_text TEXT,
            duration REAL,
            user_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Refresh tokens table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            device_id TEXT,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)
        
        # Email actions log table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS email_actions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            email_id TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # ML scoring log table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS ml_scoring_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lead_id TEXT,
            score REAL,
            features TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # ML feedback log table
        db_optimizer.execute_query("""
        CREATE TABLE IF NOT EXISTS ml_feedback_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lead_id TEXT,
            outcome TEXT,
            score REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Optional triggers for automatic updated_at
        db_optimizer.execute_query("""
        CREATE TRIGGER IF NOT EXISTS trg_users_updated
        AFTER UPDATE ON users
        FOR EACH ROW
        BEGIN
            UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """)

        # Performance indexes
        db_optimizer.execute_query("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        db_optimizer.execute_query("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);")
        db_optimizer.execute_query("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);")
        db_optimizer.execute_query("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);")
        db_optimizer.execute_query("CREATE INDEX IF NOT EXISTS idx_query_performance_created ON query_performance_log(created_at);")
        
        logger.info("✅ All core tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False

def check_database_health():
    """Check if all required tables exist"""
    try:
        required_tables = [
            'users', 'user_sessions', 'onboarding_info',
            'query_performance_log', 'refresh_tokens',
            'email_actions_log', 'ml_scoring_log', 'ml_feedback_log'
        ]
        for table in required_tables:
            result = db_optimizer.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)
            )
            if not result:
                logger.warning(f"⚠️ Table {table} missing.")
                return False
        logger.info("✅ All required tables verified.")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False
