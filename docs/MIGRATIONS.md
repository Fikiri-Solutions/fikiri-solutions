# Database Migrations Guide

**Status**: Migration strategy documented  
**Last Updated**: Feb 2026

---

## Overview

Fikiri uses SQLite (development) and PostgreSQL (production). Migrations are currently ad-hoc scripts in `scripts/migrations/`. This document outlines the migration strategy and setup for Alembic (recommended for production).

---

## Current State

**Ad-hoc Migrations:**
- `scripts/migrations/001_add_user_id_to_leads.py` - Example migration script
- Manual migration tracking via `migration_log` table
- No Alembic setup yet

**Migration Log Table:**
```sql
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_id TEXT UNIQUE NOT NULL,
    description TEXT,
    version TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed'
)
```

---

## Recommended: Alembic Setup

### Why Alembic?

- **Version control**: Track schema changes in git
- **Rollback support**: Easy to revert migrations
- **Multi-database**: Works with SQLite and PostgreSQL
- **Industry standard**: Widely used, well-documented

### Setup Steps

#### 1. Install Alembic

```bash
pip install alembic
```

#### 2. Initialize Alembic

```bash
cd /Users/mac/Downloads/Fikiri
alembic init alembic
```

#### 3. Configure `alembic/env.py`

Update to use your database URL:

```python
from core.minimal_config import get_config

config = context.config
db_url = get_config().get('DATABASE_URL') or os.getenv('DATABASE_URL', 'sqlite:///data/fikiri.db')
config.set_main_option('sqlalchemy.url', db_url)
```

#### 4. Create Initial Migration

```bash
# Generate migration from current schema
alembic revision --autogenerate -m "Initial schema"

# Review generated migration in alembic/versions/
# Edit if needed, then apply:
alembic upgrade head
```

---

## Migration Workflow

### Creating a Migration

1. **Make schema changes** in code (e.g., add column to model)
2. **Generate migration:**
   ```bash
   alembic revision --autogenerate -m "Add tenant_id to leads table"
   ```
3. **Review migration file** in `alembic/versions/`
4. **Test migration:**
   ```bash
   # Test on dev database
   alembic upgrade head
   ```
5. **Commit migration** to git
6. **Apply in production:**
   ```bash
   alembic upgrade head
   ```

### Rolling Back

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Checking Migration Status

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

---

## Migration Best Practices

### 1. Always Backup First

```bash
# SQLite
cp data/fikiri.db data/fikiri_backup_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Test Migrations

- Test on development database first
- Test rollback procedures
- Test with sample data

### 3. Migration Naming

Use descriptive names:
- ✅ `add_tenant_id_to_leads_table`
- ✅ `create_subscriptions_table`
- ❌ `migration_1`
- ❌ `update`

### 4. Data Migrations

For data transformations, use separate data migration scripts:

```python
def upgrade():
    # Schema change
    op.add_column('leads', sa.Column('tenant_id', sa.String(255)))
    
    # Data migration (run separately)
    # python scripts/migrations/data_migrate_tenant_ids.py

def downgrade():
    op.drop_column('leads', 'tenant_id')
```

### 5. Large Table Migrations

For large tables, use batched updates:

```python
def upgrade():
    # Add column (nullable first)
    op.add_column('leads', sa.Column('tenant_id', sa.String(255), nullable=True))
    
    # Batch update (run in background job)
    # See scripts/migrations/batch_update_tenant_ids.py
```

---

## Migration Status Endpoint

**TODO**: Add migration status endpoint:

```python
@monitoring_bp.route('/admin/migrations', methods=['GET'])
@require_admin
def get_migration_status():
    """Get current migration status"""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        
        # Get current revision
        # Get pending migrations
        # Return status
        pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## Rollback Procedures

### Emergency Rollback

1. **Stop application**
2. **Restore database from backup:**
   ```bash
   # SQLite
   cp backup_YYYYMMDD_HHMMSS.db data/fikiri.db
   
   # PostgreSQL
   psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql
   ```
3. **Rollback Alembic revision:**
   ```bash
   alembic downgrade -1
   ```
4. **Restart application**
5. **Verify functionality**

### Partial Rollback

If migration partially applied:
1. Check `alembic_version` table
2. Manually fix schema if needed
3. Update `alembic_version` to correct revision
4. Continue with rollback

---

## Migration Checklist

Before deploying migration:

- [ ] Migration tested on development database
- [ ] Rollback tested
- [ ] Backup created
- [ ] Migration reviewed by team
- [ ] Data migration scripts ready (if needed)
- [ ] Downtime window scheduled (if needed)
- [ ] Rollback plan documented

---

## Troubleshooting

### Migration Fails Midway

1. Check error message
2. Manually fix schema if needed
3. Update `alembic_version` table
4. Retry migration or rollback

### Migration Conflicts

If two developers create migrations:
1. Merge migrations manually
2. Or rebase one migration on top of the other
3. Test merged migration

### Database Out of Sync

If database schema doesn't match migrations:
1. Create backup
2. Generate new migration: `alembic revision --autogenerate`
3. Review and apply carefully

---

## Next Steps

1. [ ] Set up Alembic (see setup steps above)
2. [ ] Create initial migration from current schema
3. [ ] Migrate existing ad-hoc migrations to Alembic
4. [ ] Add migration status endpoint
5. [ ] Document in deployment procedures

---

*Last updated: Feb 2026*
