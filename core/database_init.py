"""
Database initialization module for Fikiri Solutions
Delegates to db_optimizer to avoid schema conflicts
"""
import logging

from core.database_optimization import db_optimizer, schema_bootstrap_allowed

logger = logging.getLogger(__name__)


def init_database():
    """
    Startup database prepare.

    PostgreSQL: verify connectivity / expected tables only unless
    FIKIRI_ALLOW_SCHEMA_BOOTSTRAP=1 (legacy one-shot CREATE/ALTER path).
    SQLite: process-once schema bootstrap via db_optimizer.
    """
    try:
        if not schema_bootstrap_allowed():
            logger.info(
                "Startup schema bootstrap skipped on PostgreSQL "
                "(connectivity + table health check only)"
            )
            try:
                db_optimizer.execute_query("SELECT 1 AS ok")
            except Exception as e:
                logger.error("❌ Database connectivity check failed: %s", e)
                return False
            return check_database_health()

        logger.info("🧩 Delegating initialization to db_optimizer...")
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
