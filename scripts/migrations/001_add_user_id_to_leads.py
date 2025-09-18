#!/usr/bin/env python3
"""
Database Migration Script: Add user_id to leads table
Version: 1.0.0
Date: 2024-01-20

This script safely migrates the leads table to support multi-user functionality
by adding a user_id column with proper constraints and indexes.

UP Migration: Add user_id column → backfill → set NOT NULL → add constraints
DOWN Migration: Drop constraints → drop column

Usage:
    python scripts/migrations/001_add_user_id_to_leads.py up
    python scripts/migrations/001_add_user_id_to_leads.py down
    python scripts/migrations/001_add_user_id_to_leads.py dry-run
"""

import sys
import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class LeadsTableMigration:
    """Migration to add user_id column to leads table"""
    
    def __init__(self):
        self.migration_id = "001_add_user_id_to_leads"
        self.description = "Add user_id column to leads table for multi-user support"
        self.version = "1.0.0"
        self.created_at = "2024-01-20"
        
    def up(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        UP Migration: Add user_id column to leads table
        
        Steps:
        1. Add user_id column as nullable
        2. Backfill with default user_id (1) for existing records
        3. Set user_id as NOT NULL
        4. Add foreign key constraint
        5. Add indexes
        """
        try:
            logger.info(f"Starting UP migration {self.migration_id} (dry_run={dry_run})")
            
            if dry_run:
                return self._dry_run_up()
            
            # Step 1: Check if migration already applied
            if self._is_migration_applied():
                return {
                    'success': True,
                    'message': 'Migration already applied',
                    'skipped': True
                }
            
            # Step 2: Backup existing table
            backup_table = f"leads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._backup_table('leads', backup_table)
            
            # Step 3: Add user_id column as nullable
            logger.info("Step 1: Adding user_id column as nullable")
            db_optimizer.execute_query(
                "ALTER TABLE leads ADD COLUMN user_id INTEGER",
                fetch=False
            )
            
            # Step 4: Backfill with default user_id (1)
            logger.info("Step 2: Backfilling user_id with default value (1)")
            db_optimizer.execute_query(
                "UPDATE leads SET user_id = 1 WHERE user_id IS NULL",
                fetch=False
            )
            
            # Step 5: Create new table with proper constraints
            logger.info("Step 3: Creating new table with proper constraints")
            db_optimizer.execute_query("""
                CREATE TABLE leads_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
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
                    tags TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, email)
                )
            """, fetch=False)
            
            # Step 6: Copy data to new table
            logger.info("Step 4: Copying data to new table")
            db_optimizer.execute_query(
                """
                INSERT INTO leads_new 
                SELECT * FROM leads
                """,
                fetch=False
            )
            
            # Step 7: Drop old table and rename new table
            logger.info("Step 5: Replacing old table with new table")
            db_optimizer.execute_query("DROP TABLE leads", fetch=False)
            db_optimizer.execute_query("ALTER TABLE leads_new RENAME TO leads", fetch=False)
            
            # Step 8: Create indexes
            logger.info("Step 6: Creating indexes")
            indexes = [
                "CREATE INDEX idx_leads_user_id ON leads (user_id)",
                "CREATE INDEX idx_leads_email ON leads (email)",
                "CREATE INDEX idx_leads_stage ON leads (stage)",
                "CREATE INDEX idx_leads_source ON leads (source)",
                "CREATE INDEX idx_leads_created_at ON leads (created_at)",
                "CREATE INDEX idx_leads_score ON leads (score)",
                "CREATE INDEX idx_leads_company ON leads (company)",
                "CREATE INDEX idx_leads_stage_source ON leads (stage, source)",
                "CREATE INDEX idx_leads_created_stage ON leads (created_at, stage)",
                "CREATE INDEX idx_leads_user_stage ON leads (user_id, stage)",
                "CREATE INDEX idx_leads_user_source ON leads (user_id, source)"
            ]
            
            for index_sql in indexes:
                try:
                    db_optimizer.execute_query(index_sql, fetch=False)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            # Step 9: Record migration
            self._record_migration()
            
            logger.info(f"UP migration {self.migration_id} completed successfully")
            return {
                'success': True,
                'message': 'Migration completed successfully',
                'backup_table': backup_table,
                'steps_completed': 6
            }
            
        except Exception as e:
            logger.error(f"UP migration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'UP_MIGRATION_FAILED'
            }
    
    def down(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        DOWN Migration: Remove user_id column from leads table
        
        Steps:
        1. Drop foreign key constraints
        2. Drop indexes
        3. Remove user_id column
        """
        try:
            logger.info(f"Starting DOWN migration {self.migration_id} (dry_run={dry_run})")
            
            if dry_run:
                return self._dry_run_down()
            
            # Check if migration was applied
            if not self._is_migration_applied():
                return {
                    'success': True,
                    'message': 'Migration not applied, nothing to rollback',
                    'skipped': True
                }
            
            # Step 1: Backup current table
            backup_table = f"leads_backup_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._backup_table('leads', backup_table)
            
            # Step 2: Create table without user_id
            logger.info("Step 1: Creating table without user_id column")
            db_optimizer.execute_query("""
                CREATE TABLE leads_old (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
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
                    tags TEXT,
                    metadata TEXT
                )
            """, fetch=False)
            
            # Step 3: Copy data (excluding user_id)
            logger.info("Step 2: Copying data without user_id")
            db_optimizer.execute_query("""
                INSERT INTO leads_old 
                (id, email, name, phone, company, source, stage, score, 
                 created_at, updated_at, last_contact, notes, tags, metadata)
                SELECT 
                    id, email, name, phone, company, source, stage, score,
                    created_at, updated_at, last_contact, notes, tags, metadata
                FROM leads
            """, fetch=False)
            
            # Step 4: Replace table
            logger.info("Step 3: Replacing table")
            db_optimizer.execute_query("DROP TABLE leads", fetch=False)
            db_optimizer.execute_query("ALTER TABLE leads_old RENAME TO leads", fetch=False)
            
            # Step 5: Recreate original indexes
            logger.info("Step 4: Recreating original indexes")
            original_indexes = [
                "CREATE INDEX idx_leads_email ON leads (email)",
                "CREATE INDEX idx_leads_stage ON leads (stage)",
                "CREATE INDEX idx_leads_source ON leads (source)",
                "CREATE INDEX idx_leads_created_at ON leads (created_at)",
                "CREATE INDEX idx_leads_score ON leads (score)",
                "CREATE INDEX idx_leads_company ON leads (company)",
                "CREATE INDEX idx_leads_stage_source ON leads (stage, source)",
                "CREATE INDEX idx_leads_created_stage ON leads (created_at, stage)"
            ]
            
            for index_sql in original_indexes:
                try:
                    db_optimizer.execute_query(index_sql, fetch=False)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            # Step 6: Remove migration record
            self._remove_migration_record()
            
            logger.info(f"DOWN migration {self.migration_id} completed successfully")
            return {
                'success': True,
                'message': 'Rollback completed successfully',
                'backup_table': backup_table,
                'steps_completed': 4
            }
            
        except Exception as e:
            logger.error(f"DOWN migration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'DOWN_MIGRATION_FAILED'
            }
    
    def _dry_run_up(self) -> Dict[str, Any]:
        """Simulate UP migration without making changes"""
        try:
            # Check current table structure
            current_schema = db_optimizer.execute_query("PRAGMA table_info(leads)")
            current_columns = [row[1] for row in current_schema] if current_schema else []
            
            # Check if user_id already exists
            has_user_id = 'user_id' in current_columns
            
            if has_user_id:
                return {
                    'success': True,
                    'message': 'Migration already applied - user_id column exists',
                    'dry_run': True,
                    'would_skip': True
                }
            
            # Simulate steps
            steps = [
                "Add user_id column as nullable",
                "Backfill with default user_id (1)",
                "Create new table with proper constraints",
                "Copy data to new table",
                "Replace old table with new table",
                "Create indexes"
            ]
            
            return {
                'success': True,
                'message': 'Dry run completed - would execute UP migration',
                'dry_run': True,
                'steps': steps,
                'current_columns': current_columns,
                'would_add_user_id': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'dry_run': True
            }
    
    def _dry_run_down(self) -> Dict[str, Any]:
        """Simulate DOWN migration without making changes"""
        try:
            # Check current table structure
            current_schema = db_optimizer.execute_query("PRAGMA table_info(leads)")
            current_columns = [row[1] for row in current_schema] if current_schema else []
            
            # Check if user_id exists
            has_user_id = 'user_id' in current_columns
            
            if not has_user_id:
                return {
                    'success': True,
                    'message': 'Migration not applied - user_id column does not exist',
                    'dry_run': True,
                    'would_skip': True
                }
            
            # Simulate steps
            steps = [
                "Create table without user_id column",
                "Copy data excluding user_id",
                "Replace current table",
                "Recreate original indexes"
            ]
            
            return {
                'success': True,
                'message': 'Dry run completed - would execute DOWN migration',
                'dry_run': True,
                'steps': steps,
                'current_columns': current_columns,
                'would_remove_user_id': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'dry_run': True
            }
    
    def _backup_table(self, table_name: str, backup_name: str):
        """Create backup of table"""
        try:
            db_optimizer.execute_query(
                f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}",
                fetch=False
            )
            logger.info(f"Backup created: {backup_name}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def _is_migration_applied(self) -> bool:
        """Check if migration has been applied"""
        try:
            # Check if user_id column exists
            schema = db_optimizer.execute_query("PRAGMA table_info(leads)")
            if schema:
                columns = [row[1] for row in schema]
                return 'user_id' in columns
            return False
        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return False
    
    def _record_migration(self):
        """Record migration in migration log"""
        try:
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS migration_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_id TEXT UNIQUE NOT NULL,
                    description TEXT,
                    version TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed'
                )
            """, fetch=False)
            
            db_optimizer.execute_query(
                """
                INSERT OR REPLACE INTO migration_log 
                (migration_id, description, version, status)
                VALUES (?, ?, ?, ?)
                """,
                (self.migration_id, self.description, self.version, 'completed'),
                fetch=False
            )
        except Exception as e:
            logger.warning(f"Failed to record migration: {e}")
    
    def _remove_migration_record(self):
        """Remove migration record from log"""
        try:
            db_optimizer.execute_query(
                "DELETE FROM migration_log WHERE migration_id = ?",
                (self.migration_id,),
                fetch=False
            )
        except Exception as e:
            logger.warning(f"Failed to remove migration record: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get migration status"""
        try:
            applied = self._is_migration_applied()
            
            # Get migration log
            log_entry = db_optimizer.execute_query(
                "SELECT * FROM migration_log WHERE migration_id = ? LIMIT 1",
                (self.migration_id,)
            )
            
            return {
                'success': True,
                'data': {
                    'migration_id': self.migration_id,
                    'description': self.description,
                    'version': self.version,
                    'applied': applied,
                    'log_entry': dict(log_entry[0]) if log_entry else None
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """Main migration script entry point"""
    if len(sys.argv) < 2:
        print("Usage: python 001_add_user_id_to_leads.py [up|down|dry-run]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    migration = LeadsTableMigration()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if command == 'up':
        result = migration.up()
    elif command == 'down':
        result = migration.down()
    elif command == 'dry-run':
        result = migration.up(dry_run=True)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    if result['success']:
        print(f"✅ {result['message']}")
        if 'steps' in result:
            print("Steps that would be executed:")
            for i, step in enumerate(result['steps'], 1):
                print(f"  {i}. {step}")
    else:
        print(f"❌ Migration failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == '__main__':
    main()
