#!/usr/bin/env python3
"""
Automated Backup System for Fikiri Solutions
Handles SQLite/PostgreSQL and Redis backups with scheduling
"""

import os
import sys
import shutil
import subprocess
import json
import gzip
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import logging
# Optional dependencies
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

import time
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups for database and Redis"""
    
    def __init__(self):
        self.backup_dir = Path(os.getenv('BACKUP_STORAGE_PATH', '/backups'))
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        self.aws_s3_bucket = os.getenv('AWS_S3_BUCKET')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize AWS S3 client if configured
        self.s3_client = None
        if self.aws_s3_bucket:
            try:
                self.s3_client = boto3.client('s3', region_name=self.aws_region)
                logger.info(f"AWS S3 backup configured: {self.aws_s3_bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
    
    def create_backup_filename(self, backup_type: str, extension: str = 'sql') -> str:
        """Create timestamped backup filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{backup_type}_{timestamp}.{extension}"
    
    def backup_sqlite(self) -> Optional[str]:
        """Backup SQLite database"""
        try:
            db_path = os.getenv('DATABASE_URL', 'sqlite:///data/fikiri.db')
            if not db_path.startswith('sqlite:///'):
                logger.info("Not using SQLite database, skipping SQLite backup")
                return None
            
            # Extract database path
            db_file = db_path.replace('sqlite:///', '')
            if not os.path.exists(db_file):
                logger.error(f"SQLite database file not found: {db_file}")
                return None
            
            # Create backup filename
            backup_filename = self.create_backup_filename('sqlite', 'db')
            backup_path = self.backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(db_file, backup_path)
            
            # Compress backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(backup_path)
            
            logger.info(f"SQLite backup created: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"SQLite backup failed: {e}")
            return None
    
    def backup_postgresql(self) -> Optional[str]:
        """Backup PostgreSQL database"""
        try:
            db_url = os.getenv('DATABASE_URL')
            if not db_url or not db_url.startswith('postgresql://'):
                logger.info("Not using PostgreSQL database, skipping PostgreSQL backup")
                return None
            
            # Create backup filename
            backup_filename = self.create_backup_filename('postgresql', 'sql')
            backup_path = self.backup_dir / backup_filename
            
            # Run pg_dump
            cmd = ['pg_dump', db_url]
            with open(backup_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None
            
            # Compress backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(backup_path)
            
            logger.info(f"PostgreSQL backup created: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            return None
    
    def backup_redis(self) -> Optional[str]:
        """Backup Redis data"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            # Create backup filename
            backup_filename = self.create_backup_filename('redis', 'rdb')
            backup_path = self.backup_dir / backup_filename
            
            # Connect to Redis
            r = redis.from_url(redis_url)
            
            # Get all keys and their values
            redis_data = {}
            for key in r.scan_iter():
                key_str = key.decode('utf-8')
                value = r.get(key)
                if value:
                    redis_data[key_str] = value.decode('utf-8')
            
            # Save to JSON file
            with open(backup_path, 'w') as f:
                json.dump(redis_data, f, indent=2)
            
            # Compress backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(backup_path)
            
            logger.info(f"Redis backup created: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            return None
    
    def backup_application_files(self) -> Optional[str]:
        """Backup important application files"""
        try:
            # Create backup filename
            backup_filename = self.create_backup_filename('app_files', 'tar.gz')
            backup_path = self.backup_dir / backup_filename
            
            # Files to backup
            files_to_backup = [
                'data/',
                'logs/',
                'uploads/',
                'config.json',
                'requirements.txt'
            ]
            
            # Create tar.gz archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        tar.add(file_path)
            
            logger.info(f"Application files backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Application files backup failed: {e}")
            return None
    
    def upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """Upload backup to S3"""
        if not self.s3_client:
            logger.warning("S3 client not configured, skipping S3 upload")
            return False
        
        try:
            self.s3_client.upload_file(local_path, self.aws_s3_bucket, s3_key)
            logger.info(f"Backup uploaded to S3: s3://{self.aws_s3_bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for backup_file in self.backup_dir.glob('*'):
                if backup_file.is_file():
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        logger.info(f"Removed old backup: {backup_file}")
            
            logger.info("Old backups cleanup completed")
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
    
    def run_full_backup(self) -> Dict[str, Any]:
        """Run a full backup of all systems"""
        logger.info("Starting full backup")
        
        backup_results = {
            'timestamp': datetime.now().isoformat(),
            'backups': {},
            'success': True,
            'errors': []
        }
        
        # Backup database
        if os.getenv('DATABASE_URL', '').startswith('sqlite:///'):
            sqlite_backup = self.backup_sqlite()
            if sqlite_backup:
                backup_results['backups']['sqlite'] = sqlite_backup
            else:
                backup_results['success'] = False
                backup_results['errors'].append('SQLite backup failed')
        
        elif os.getenv('DATABASE_URL', '').startswith('postgresql://'):
            postgres_backup = self.backup_postgresql()
            if postgres_backup:
                backup_results['backups']['postgresql'] = postgres_backup
            else:
                backup_results['success'] = False
                backup_results['errors'].append('PostgreSQL backup failed')
        
        # Backup Redis
        redis_backup = self.backup_redis()
        if redis_backup:
            backup_results['backups']['redis'] = redis_backup
        else:
            backup_results['success'] = False
            backup_results['errors'].append('Redis backup failed')
        
        # Backup application files
        app_backup = self.backup_application_files()
        if app_backup:
            backup_results['backups']['application'] = app_backup
        
        # Upload to S3 if configured
        if self.s3_client:
            for backup_type, backup_path in backup_results['backups'].items():
                s3_key = f"backups/{backup_type}/{os.path.basename(backup_path)}"
                if self.upload_to_s3(backup_path, s3_key):
                    backup_results['backups'][f"{backup_type}_s3"] = s3_key
        
        # Cleanup old backups
        self.cleanup_old_backups()
        
        # Log results
        if backup_results['success']:
            logger.info(f"Full backup completed successfully: {backup_results['backups']}")
        else:
            logger.error(f"Backup completed with errors: {backup_results['errors']}")
        
        return backup_results
    
    def restore_from_backup(self, backup_path: str, backup_type: str) -> bool:
        """Restore from backup file"""
        try:
            if backup_type == 'sqlite':
                return self.restore_sqlite(backup_path)
            elif backup_type == 'postgresql':
                return self.restore_postgresql(backup_path)
            elif backup_type == 'redis':
                return self.restore_redis(backup_path)
            else:
                logger.error(f"Unknown backup type: {backup_type}")
                return False
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def restore_sqlite(self, backup_path: str) -> bool:
        """Restore SQLite database from backup"""
        try:
            db_path = os.getenv('DATABASE_URL', 'sqlite:///data/fikiri.db').replace('sqlite:///', '')
            
            # Decompress if needed
            if backup_path.endswith('.gz'):
                temp_path = backup_path[:-3]  # Remove .gz
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path
            
            # Restore database
            shutil.copy2(backup_path, db_path)
            
            logger.info(f"SQLite database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"SQLite restore failed: {e}")
            return False
    
    def restore_postgresql(self, backup_path: str) -> bool:
        """Restore PostgreSQL database from backup"""
        try:
            db_url = os.getenv('DATABASE_URL')
            
            # Decompress if needed
            if backup_path.endswith('.gz'):
                temp_path = backup_path[:-3]  # Remove .gz
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path
            
            # Restore database
            cmd = ['psql', db_url, '-f', backup_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"PostgreSQL restore failed: {result.stderr}")
                return False
            
            logger.info(f"PostgreSQL database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL restore failed: {e}")
            return False
    
    def restore_redis(self, backup_path: str) -> bool:
        """Restore Redis data from backup"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            # Decompress if needed
            if backup_path.endswith('.gz'):
                temp_path = backup_path[:-3]  # Remove .gz
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path
            
            # Load Redis data
            with open(backup_path, 'r') as f:
                redis_data = json.load(f)
            
            # Connect to Redis and restore data
            r = redis.from_url(redis_url)
            r.flushdb()  # Clear existing data
            
            for key, value in redis_data.items():
                r.set(key, value)
            
            logger.info(f"Redis data restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Redis restore failed: {e}")
            return False

def schedule_backups():
    """Schedule automated backups"""
    
    backup_manager = BackupManager()
    
    # Schedule daily full backup at 2 AM
    schedule.every().day.at("02:00").do(backup_manager.run_full_backup)
    
    # Schedule weekly cleanup
    schedule.every().sunday.at("03:00").do(backup_manager.cleanup_old_backups)
    
    logger.info("Backup scheduling initialized")
    
    # Run scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def run_backup_now():
    """Run backup immediately (for manual execution)"""
    backup_manager = BackupManager()
    return backup_manager.run_full_backup()

def main():
    """Main function for backup script"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'run':
            # Run backup immediately
            result = run_backup_now()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'schedule':
            # Start scheduled backups
            schedule_backups()
        elif sys.argv[1] == 'restore':
            # Restore from backup
            if len(sys.argv) < 4:
                print("Usage: python backup.py restore <backup_path> <backup_type>")
                sys.exit(1)
            
            backup_manager = BackupManager()
            success = backup_manager.restore_from_backup(sys.argv[2], sys.argv[3])
            print(f"Restore {'successful' if success else 'failed'}")
        else:
            print("Usage: python backup.py [run|schedule|restore]")
            sys.exit(1)
    else:
        # Default: run backup immediately
        result = run_backup_now()
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
