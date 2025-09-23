"""
Fikiri Solutions - Database Configuration
SQLAlchemy setup with PostgreSQL support
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

def get_database_url():
    """Get database URL from environment variables"""
    # Try PostgreSQL first, fall back to SQLite for development
    postgres_url = os.getenv("DATABASE_URL")
    if postgres_url:
        logger.info("Using PostgreSQL database")
        return postgres_url
    
    # Fallback to SQLite for development
    sqlite_url = os.getenv("SQLITE_DATABASE_URL", "sqlite:///data/fikiri.db")
    logger.info("Using SQLite database for development")
    return sqlite_url

def create_database_engine():
    """Create SQLAlchemy engine with appropriate configuration"""
    database_url = get_database_url()
    
    if database_url.startswith("postgresql"):
        # PostgreSQL configuration
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    else:
        # SQLite configuration
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    
    return engine

# Create engine and session
engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database tables"""
    try:
        # Import all models to ensure they're registered
        from app.models import Organization, User, Lead
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Create default organization if none exists
        db = SessionLocal()
        try:
            from app.models import Organization
            if not db.query(Organization).first():
                default_org = Organization(name="Fikiri Solutions")
                db.add(default_org)
                db.commit()
                logger.info("✅ Default organization created")
        except Exception as e:
            logger.error(f"Error creating default organization: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def test_database_connection():
    """Test database connection"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
