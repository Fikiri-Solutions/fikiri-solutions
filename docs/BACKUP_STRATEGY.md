# Backup Strategy & Restore Procedures

**Status**: Strategy documented  
**Last Updated**: Feb 2026

---

## Overview

Fikiri Solutions requires regular backups of:
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Redis**: Sessions, cache, queues
- **Environment Variables**: Critical for recovery
- **Vector Index**: In-memory or Pinecone (Pinecone handles its own backups)

---

## Backup Cadence

| Environment | Database | Redis | Frequency |
|------------|----------|-------|-----------|
| **Production** | Daily | Daily | Every 24 hours |
| **Staging** | Weekly | Weekly | Every 7 days |
| **Development** | On-demand | N/A | Before major changes |

**Retention Policy:**
- Production: 30 days
- Staging: 14 days
- Development: 7 days

---

## Automated Backup System

**Existing Script**: `scripts/backup_system.py`

### Setup Automated Backups

#### Option A: Cron (Linux/Mac)

```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * cd /Users/mac/Downloads/Fikiri && python3 scripts/backup_system.py --type=all --retention=30
```

#### Option B: Systemd Timer (Linux)

Create `/etc/systemd/system/fikiri-backup.service`:
```ini
[Unit]
Description=Fikiri Backup Service
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/Users/mac/Downloads/Fikiri
ExecStart=/usr/bin/python3 scripts/backup_system.py --type=all --retention=30
```

Create `/etc/systemd/system/fikiri-backup.timer`:
```ini
[Unit]
Description=Run Fikiri backup daily
Requires=fikiri-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable fikiri-backup.timer
sudo systemctl start fikiri-backup.timer
```

#### Option C: Render/Vercel Cron Jobs

Use platform cron jobs to trigger backup endpoint:
```python
@monitoring_bp.route('/admin/backup', methods=['POST'])
@require_admin
def trigger_backup():
    """Trigger manual backup"""
    from scripts.backup_system import BackupManager
    manager = BackupManager()
    result = manager.backup_all()
    return jsonify(result)
```

---

## Backup Procedures

### Database Backup

#### SQLite

```bash
# Manual backup
cp data/fikiri.db data/backups/fikiri_backup_$(date +%Y%m%d_%H%M%S).db

# Using backup script
python3 scripts/backup_system.py --type=database
```

#### PostgreSQL

```bash
# Manual backup
pg_dump $DATABASE_URL | gzip > backups/postgres_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Using backup script
python3 scripts/backup_system.py --type=database
```

### Redis Backup

```bash
# Manual backup
redis-cli -u $REDIS_URL --rdb backups/redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# Using backup script
python3 scripts/backup_system.py --type=redis
```

### Environment Variables Backup

**Critical**: Backup these before any deployment:

```bash
# Export to secure location
env | grep -E "(JWT_SECRET_KEY|FERNET_KEY|DATABASE_URL|REDIS_URL|STRIPE_SECRET_KEY|OPENAI_API_KEY)" > backups/env_backup_$(date +%Y%m%d_%H%M%S).env
```

**Note**: Store encrypted, never commit to git.

---

## Restore Procedures

### Database Restore

#### SQLite

```bash
# Stop application
# Restore from backup
cp backups/fikiri_backup_YYYYMMDD_HHMMSS.db data/fikiri.db
# Restart application
```

#### PostgreSQL

```bash
# Stop application
# Restore from backup
gunzip -c backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz | psql $DATABASE_URL
# Restart application
```

### Redis Restore

```bash
# Stop Redis (if local) or flush target Redis
redis-cli -u $REDIS_URL FLUSHALL

# Restore from backup
redis-cli -u $REDIS_URL --rdb backups/redis_backup_YYYYMMDD_HHMMSS.rdb
```

### Full System Restore

1. **Stop application**
2. **Restore database** (see above)
3. **Restore Redis** (see above)
4. **Restore environment variables** (if needed)
5. **Verify data integrity**
6. **Restart application**
7. **Run health checks**

---

## Backup Verification

### Automated Verification

Add to `scripts/backup_system.py`:

```python
def verify_backup(backup_path: str) -> bool:
    """Verify backup file integrity"""
    # Check file exists
    # Check file size > 0
    # For SQLite: try to open and query
    # For PostgreSQL: try to restore to temp database
    # Return True if valid
    pass
```

### Manual Verification

```bash
# SQLite backup
sqlite3 backup_file.db "SELECT COUNT(*) FROM users;"

# PostgreSQL backup
pg_restore --list backup_file.sql | head -20

# Redis backup
redis-cli --rdb-check backup_file.rdb
```

---

## Backup Storage

### Local Storage

- **Path**: `data/backups/` or `backups/`
- **Rotation**: Keep last N backups (based on retention policy)
- **Compression**: Use gzip for PostgreSQL backups

### Cloud Storage (Recommended for Production)

**AWS S3:**
```python
import boto3
s3 = boto3.client('s3')
s3.upload_file(backup_path, 'fikiri-backups', f'backups/{filename}')
```

**Google Cloud Storage:**
```python
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('fikiri-backups')
blob = bucket.blob(f'backups/{filename}')
blob.upload_from_filename(backup_path)
```

**Update `scripts/backup_system.py`** to support cloud storage.

---

## Disaster Recovery

### RTO (Recovery Time Objective)

**Target**: < 4 hours

**Steps:**
1. Identify failure (5 min)
2. Restore from backup (30 min)
3. Verify data integrity (15 min)
4. Restart services (10 min)
5. Health checks (10 min)
6. **Total**: ~70 minutes (well under 4 hours)

### RPO (Recovery Point Objective)

**Target**: < 24 hours

- Daily backups = max 24 hours of data loss
- For critical systems, consider hourly backups

---

## Backup Monitoring

### Health Checks

Add backup health check endpoint:

```python
@monitoring_bp.route('/admin/backup/status', methods=['GET'])
@require_admin
def backup_status():
    """Check backup status"""
    # Check last backup time
    # Check backup file integrity
    # Check backup storage availability
    # Return status
    pass
```

### Alerts

- Alert if backup hasn't run in 25 hours (production)
- Alert if backup file is missing or corrupted
- Alert if backup storage is full

---

## Quarterly Backup Drills

**Schedule**: Every 90 days

**Procedure:**
1. Select random backup from last 30 days
2. Restore to test environment
3. Verify data integrity
4. Test application functionality
5. Document results

**Success Criteria:**
- ✅ Backup restores successfully
- ✅ Data integrity verified
- ✅ Application functions correctly
- ✅ RTO < 4 hours achieved

---

## Backup Checklist

**Before Deployment:**
- [ ] Backup created
- [ ] Backup verified
- [ ] Backup stored off-site
- [ ] Restore procedure tested

**After Deployment:**
- [ ] New backup created
- [ ] Old backups retained (per retention policy)
- [ ] Backup monitoring verified

---

## Next Steps

1. [ ] Set up automated backups (cron/systemd)
2. [ ] Configure cloud storage for backups
3. [ ] Add backup verification
4. [ ] Add backup monitoring endpoint
5. [ ] Schedule quarterly backup drills
6. [ ] Document in runbook

---

*Last updated: Feb 2026*
