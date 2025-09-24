"""
Database migration to add email_actions table for Phase 1
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def create_email_actions_table(db_path: str = "data/fikiri.db"):
    """Create email_actions table for tracking email actions"""
    try:
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create email_actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                parameters TEXT,  -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_user_id 
            ON email_actions (user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_email_id 
            ON email_actions (email_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_actions_action_type 
            ON email_actions (action_type)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Email actions table created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create email actions table: {e}")
        return False

def create_lead_pipeline_stages_table(db_path: str = "data/fikiri.db"):
    """Create lead_pipeline_stages table for CRM stage tracking"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create lead_pipeline_stages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_pipeline_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                order_index INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default pipeline stages
        default_stages = [
            ('new', 'New leads that need initial contact', 1),
            ('contacted', 'Leads that have been contacted', 2),
            ('qualified', 'Leads that have been qualified', 3),
            ('proposal', 'Leads with active proposals', 4),
            ('won', 'Successfully converted leads', 5),
            ('lost', 'Leads that did not convert', 6)
        ]
        
        for stage_name, description, order_idx in default_stages:
            cursor.execute("""
                INSERT OR IGNORE INTO lead_pipeline_stages 
                (name, description, order_index) 
                VALUES (?, ?, ?)
            """, (stage_name, description, order_idx))
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Lead pipeline stages table created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create lead pipeline stages table: {e}")
        return False

def update_leads_table_for_pipeline(db_path: str = "data/fikiri.db"):
    """Update leads table to support pipeline stages"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Add user_id column
            cursor.execute("ALTER TABLE leads ADD COLUMN user_id INTEGER DEFAULT 1")
            logger.info("✅ Added user_id column to leads table")
        
        if 'stage' not in columns:
            # Add stage column
            cursor.execute("ALTER TABLE leads ADD COLUMN stage TEXT DEFAULT 'new'")
            logger.info("✅ Added stage column to leads table")
        
        if 'pipeline_stage_id' not in columns:
            # Add pipeline_stage_id column
            cursor.execute("ALTER TABLE leads ADD COLUMN pipeline_stage_id INTEGER")
            logger.info("✅ Added pipeline_stage_id column to leads table")
        
        if 'tags' not in columns:
            # Add tags column
            cursor.execute("ALTER TABLE leads ADD COLUMN tags TEXT")
            logger.info("✅ Added tags column to leads table")
        
        if 'metadata' not in columns:
            # Add metadata column
            cursor.execute("ALTER TABLE leads ADD COLUMN metadata TEXT")
            logger.info("✅ Added metadata column to leads table")
        
        # Update existing leads to have default stage
        cursor.execute("UPDATE leads SET stage = 'new' WHERE stage IS NULL")
        cursor.execute("UPDATE leads SET user_id = 1 WHERE user_id IS NULL")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Leads table updated for pipeline support")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update leads table: {e}")
        return False

def create_reminders_alerts_tables(db_path: str = "data/fikiri.db"):
    """Create reminders and alerts tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create reminders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                lead_id TEXT,
                reminder_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP NOT NULL,
                priority TEXT DEFAULT 'medium',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Create follow_up_tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_tasks (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                template_id TEXT NOT NULL,
                scheduled_for TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due_date ON reminders (due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_up_tasks_user_id ON follow_up_tasks (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_up_tasks_scheduled_for ON follow_up_tasks (scheduled_for)")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Reminders and alerts tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create reminders and alerts tables: {e}")
        return False

def run_phase1_migrations():
    """Run all Phase 1 database migrations"""
    logger.info("🚀 Running Phase 1 database migrations...")
    
    success = True
    
    # Create email actions table
    if not create_email_actions_table():
        success = False
    
    # Create pipeline stages table
    if not create_lead_pipeline_stages_table():
        success = False
    
    # Update leads table
    if not update_leads_table_for_pipeline():
        success = False
    
    # Create reminders and alerts tables
    if not create_reminders_alerts_tables():
        success = False
    
    if success:
        logger.info("✅ All Phase 1 migrations completed successfully")
    else:
        logger.error("❌ Some Phase 1 migrations failed")
    
    return success

if __name__ == "__main__":
    run_phase1_migrations()
