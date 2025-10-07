"""
Database initialization module for Fikiri Solutions
Delegates to db_optimizer to avoid schema conflicts
"""
import logging
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database by delegating to optimizer"""
    try:
        logger.info("🧩 Delegating initialization to db_optimizer...")
        # Trigger db_optimizer initialization manually
        db_optimizer._initialize_database()
        logger.info("✅ Database initialized successfully (delegated).")
        return True
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        return False

def check_database_health():
    """Ensure all required tables exist"""
    required = ['users', 'user_sessions', 'refresh_tokens', 'email_actions_log']
    missing = [t for t in required if not db_optimizer.table_exists(t)]
    if missing:
        logger.warning(f"⚠️ Missing tables: {missing}")
        return False
    logger.info("✅ Database health OK.")
    return True
