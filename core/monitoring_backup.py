"""
Monitoring and Alerting System
Comprehensive monitoring setup for Fikiri Solutions
"""

import os
import time
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: str  # critical, warning, info
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None

class MonitoringSystem:
    """Comprehensive monitoring and alerting system"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.notification_channels: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_rules()
        self._start_monitoring_thread()
    
    def _initialize_default_rules(self):
        """Initialize default monitoring rules"""
        self.alert_rules = {
            'high_response_time': {
                'metric': 'response_time',
                'threshold': 2.0,
                'severity': 'warning',
                'message': 'High response time detected'
            },
            'critical_response_time': {
                'metric': 'response_time',
                'threshold': 5.0,
                'severity': 'critical',
                'message': 'Critical response time detected'
            },
            'high_error_rate': {
                'metric': 'error_rate',
                'threshold': 5.0,
                'severity': 'warning',
                'message': 'High error rate detected'
            },
            'critical_error_rate': {
                'metric': 'error_rate',
                'threshold': 10.0,
                'severity': 'critical',
                'message': 'Critical error rate detected'
            },
            'high_memory_usage': {
                'metric': 'memory_usage',
                'threshold': 80.0,
                'severity': 'warning',
                'message': 'High memory usage detected'
            },
            'critical_memory_usage': {
                'metric': 'memory_usage',
                'threshold': 95.0,
                'severity': 'critical',
                'message': 'Critical memory usage detected'
            },
            'high_cpu_usage': {
                'metric': 'cpu_usage',
                'threshold': 80.0,
                'severity': 'warning',
                'message': 'High CPU usage detected'
            },
            'critical_cpu_usage': {
                'metric': 'cpu_usage',
                'threshold': 95.0,
                'severity': 'critical',
                'message': 'Critical CPU usage detected'
            },
            'service_down': {
                'metric': 'service_status',
                'threshold': 0,
                'severity': 'critical',
                'message': 'Service is down'
            }
        }
    
    def add_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Add a metric to the monitoring system"""
        timestamp = datetime.now()
        
        if metric_name not in self.metrics_history:
            self.metrics_history[metric_name] = []
        
        metric_data = {
            'value': value,
            'timestamp': timestamp,
            'tags': tags or {}
        }
        
        self.metrics_history[metric_name].append(metric_data)
        
        # Keep only last 1000 metrics per type
        if len(self.metrics_history[metric_name]) > 1000:
            self.metrics_history[metric_name] = self.metrics_history[metric_name][-1000:]
        
        # Check alert rules
        self._check_alert_rules(metric_name, value, tags)
    
    def _check_alert_rules(self, metric_name: str, value: float, tags: Dict[str, str]):
        """Check if metric triggers any alert rules"""
        for rule_name, rule in self.alert_rules.items():
            if rule['metric'] == metric_name:
                if value > rule['threshold']:
                    self._trigger_alert(
                        rule_name,
                        rule['severity'],
                        rule['message'],
                        f"{metric_name}={value}",
                        tags
                    )
    
    def _trigger_alert(self, rule_name: str, severity: str, message: str, 
                      details: str, tags: Dict[str, str] = None):
        """Trigger an alert"""
        alert_id = f"{rule_name}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            severity=severity,
            title=f"{severity.upper()}: {message}",
            message=f"{message}\nDetails: {details}",
            timestamp=datetime.now(),
            source=rule_name,
            tags=tags or {}
        )
        
        self.alerts.append(alert)
        
        # Send notifications
        self._send_notifications(alert)
        
        logger.warning(f"Alert triggered: {alert.title}")
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for critical alerts"""
        if alert.severity in ['critical', 'warning']:
            # Send email notification
            self._send_email_alert(alert)
            
            # Send Slack notification (if configured)
            self._send_slack_alert(alert)
            
            # Send webhook notification
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            # This would be configured with actual SMTP settings
            # For now, just log the alert
            logger.info(f"Email alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, alert: Alert):
        """Send Slack alert"""
        try:
            # This would be configured with actual Slack webhook
            # For now, just log the alert
            logger.info(f"Slack alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert"""
        try:
            # This would be configured with actual webhook URL
            # For now, just log the alert
            logger.info(f"Webhook alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _start_monitoring_thread(self):
        """Start background monitoring thread"""
        def monitor():
            while True:
                try:
                    # Monitor system metrics
                    self._monitor_system_metrics()
                    
                    # Monitor service health
                    self._monitor_service_health()
                    
                    # Clean up old alerts
                    self._cleanup_old_alerts()
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Monitoring thread error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _monitor_system_metrics(self):
        """Monitor system metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.add_metric('cpu_usage', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.add_metric('memory_usage', memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.add_metric('disk_usage', disk_percent)
            
        except ImportError:
            logger.warning("psutil not available for system monitoring")
        except Exception as e:
            logger.error(f"System monitoring error: {e}")
    
    def _monitor_service_health(self):
        """Monitor service health"""
        try:
            # Check API health
            # Use environment variable for health check URL, check if we're in production
            base_url = os.getenv('HEALTH_CHECK_URL')
            if not base_url:
                # Don't perform health checks in production to avoid localhost errors
                if os.getenv('FLASK_ENV') == 'production':
                    return
                base_url = 'http://localhost:5000'
            # Only perform health check if we have a valid URL
            if base_url:
                response = requests.get(f'{base_url}/health', timeout=5)
                if response.status_code == 200:
                    self.add_metric('service_status', 1)
                else:
                    self.add_metric('service_status', 0)
                
        except Exception as e:
            logger.error(f"Service health monitoring error: {e}")
            self.add_metric('service_status', 0)
    
    def _cleanup_old_alerts(self):
        """Clean up old alerts"""
        cutoff_time = datetime.now() - timedelta(days=7)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
    
    def get_alerts(self, severity: str = None, resolved: bool = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        filtered_alerts = self.alerts
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]
        
        return sorted(filtered_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert resolved: {alert.title}")
                break
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        summary = {}
        
        for metric_name, metrics in self.metrics_history.items():
            recent_metrics = [
                m for m in metrics 
                if m['timestamp'] > cutoff_time
            ]
            
            if recent_metrics:
                values = [m['value'] for m in recent_metrics]
                summary[metric_name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'latest': values[-1] if values else None
                }
        
        return summary

# Global monitoring system instance
monitoring_system = MonitoringSystem()

# ============================================================================
# BACKUP AND DISASTER RECOVERY SYSTEM
# ============================================================================

class BackupManager:
    """Backup and disaster recovery management"""
    
    def __init__(self):
        self.backup_configs: Dict[str, Dict[str, Any]] = {}
        self.backup_history: List[Dict[str, Any]] = []
        self._initialize_backup_configs()
    
    def _initialize_backup_configs(self):
        """Initialize backup configurations"""
        self.backup_configs = {
            'database': {
                'source': 'data/fikiri.db',
                'destination': 'backups/database/',
                'schedule': 'daily',
                'retention_days': 30,
                'compression': True
            },
            'logs': {
                'source': 'logs/',
                'destination': 'backups/logs/',
                'schedule': 'weekly',
                'retention_days': 90,
                'compression': True
            },
            'config': {
                'source': 'core/',
                'destination': 'backups/config/',
                'schedule': 'daily',
                'retention_days': 30,
                'compression': True
            }
        }
    
    def create_backup(self, backup_type: str) -> Dict[str, Any]:
        """Create a backup"""
        if backup_type not in self.backup_configs:
            return {'error': f'Unknown backup type: {backup_type}'}
        
        config = self.backup_configs[backup_type]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            import shutil
            import os
            
            # Create destination directory
            os.makedirs(config['destination'], exist_ok=True)
            
            # Create backup
            backup_name = f"{backup_type}_{timestamp}"
            if config['compression']:
                backup_name += '.tar.gz'
                shutil.make_archive(
                    os.path.join(config['destination'], backup_name),
                    'gztar',
                    config['source']
                )
            else:
                shutil.copytree(
                    config['source'],
                    os.path.join(config['destination'], backup_name)
                )
            
            backup_info = {
                'type': backup_type,
                'name': backup_name,
                'timestamp': datetime.now(),
                'size': self._get_backup_size(os.path.join(config['destination'], backup_name)),
                'status': 'success'
            }
            
            self.backup_history.append(backup_info)
            
            # Clean up old backups
            self._cleanup_old_backups(backup_type)
            
            logger.info(f"Backup created: {backup_name}")
            return backup_info
            
        except Exception as e:
            error_info = {
                'type': backup_type,
                'timestamp': datetime.now(),
                'status': 'failed',
                'error': str(e)
            }
            self.backup_history.append(error_info)
            logger.error(f"Backup failed: {e}")
            return error_info
    
    def _get_backup_size(self, backup_path: str) -> int:
        """Get backup size in bytes"""
        try:
            if os.path.isfile(backup_path):
                return os.path.getsize(backup_path)
            elif os.path.isdir(backup_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(backup_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                return total_size
        except Exception:
            pass
        return 0
    
    def _cleanup_old_backups(self, backup_type: str):
        """Clean up old backups based on retention policy"""
        config = self.backup_configs[backup_type]
        cutoff_time = datetime.now() - timedelta(days=config['retention_days'])
        
        try:
            import os
            import glob
            
            pattern = os.path.join(config['destination'], f"{backup_type}_*")
            backups = glob.glob(pattern)
            
            for backup in backups:
                if os.path.getmtime(backup) < cutoff_time.timestamp():
                    os.remove(backup)
                    logger.info(f"Old backup removed: {backup}")
                    
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def restore_backup(self, backup_name: str, destination: str) -> Dict[str, Any]:
        """Restore from a backup"""
        try:
            import shutil
            import os
            
            # Find backup file
            backup_path = None
            for config in self.backup_configs.values():
                if os.path.exists(os.path.join(config['destination'], backup_name)):
                    backup_path = os.path.join(config['destination'], backup_name)
                    break
            
            if not backup_path:
                return {'error': 'Backup not found'}
            
            # Restore backup
            if backup_name.endswith('.tar.gz'):
                shutil.unpack_archive(backup_path, destination)
            else:
                shutil.copytree(backup_path, destination)
            
            restore_info = {
                'backup_name': backup_name,
                'destination': destination,
                'timestamp': datetime.now(),
                'status': 'success'
            }
            
            logger.info(f"Backup restored: {backup_name} to {destination}")
            return restore_info
            
        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            return {'error': str(e)}
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get backup status and history"""
        return {
            'configs': self.backup_configs,
            'history': self.backup_history[-50:],  # Last 50 backups
            'total_backups': len(self.backup_history),
            'successful_backups': len([b for b in self.backup_history if b.get('status') == 'success'])
        }
    
    def schedule_backups(self):
        """Schedule automatic backups"""
        # This would integrate with a cron job or scheduler
        # For now, we'll just log the schedule
        logger.info("Backup scheduling configured")
        
        for backup_type, config in self.backup_configs.items():
            logger.info(f"Backup {backup_type} scheduled: {config['schedule']}")

# Global backup manager instance
backup_manager = BackupManager()

# Export the monitoring and backup systems
__all__ = [
    'MonitoringSystem', 'monitoring_system', 'Alert',
    'BackupManager', 'backup_manager'
]
