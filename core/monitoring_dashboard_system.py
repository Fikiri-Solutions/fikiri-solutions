"""
Monitoring Dashboard System
Real-time monitoring for Redis queues, system health, and alerts
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import psutil
from core.redis_service import redis_service
from core.redis_queues import email_queue, ai_queue, crm_queue, webhook_queue
from core.redis_cache import fikiri_cache
from core.redis_sessions import session_manager

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemMetric:
    """System metric data structure"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    status: str  # "healthy", "warning", "critical"
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class MonitoringDashboardSystem:
    """System for monitoring Redis queues, system health, and generating alerts"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.metrics_history: Dict[str, List[SystemMetric]] = {}
        self.alert_thresholds = {
            'redis_memory_usage': {'warning': 80.0, 'critical': 95.0},
            'queue_length': {'warning': 100, 'critical': 500},
            'cpu_usage': {'warning': 80.0, 'critical': 95.0},
            'memory_usage': {'warning': 85.0, 'critical': 95.0},
            'disk_usage': {'warning': 80.0, 'critical': 90.0}
        }
    
    def get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis-specific metrics"""
        try:
            # Get Redis info
            redis_info = redis_service.get_info()
            
            # Calculate memory usage percentage
            used_memory = redis_info.get('used_memory', 0)
            max_memory = redis_info.get('maxmemory', 0)
            memory_usage_percent = (used_memory / max_memory * 100) if max_memory > 0 else 0
            
            # Get queue lengths
            queue_lengths = {}
            queue_instances = {
                'email_processing': email_queue,
                'ai_responses': ai_queue,
                'webhook_processing': webhook_queue,
                'scheduled_tasks': crm_queue
            }
            
            for queue_name, queue_instance in queue_instances.items():
                    try:
                        queue_stats = queue_instance.get_queue_stats()
                        queue_length = queue_stats.get('pending_jobs', 0)
                        queue_lengths[queue_name] = queue_length
                    except Exception as e:
                        logger.warning(f"Could not get length for queue {queue_name}: {e}")
                        queue_lengths[queue_name] = 0
            
            # Get cache statistics
            cache_stats = fikiri_cache.get_cache_stats()
            
            # Get session statistics
            session_stats = session_manager.get_session_stats()
            
            return {
                'redis_memory_usage': {
                    'value': memory_usage_percent,
                    'unit': '%',
                    'status': self._get_status(memory_usage_percent, 'redis_memory_usage'),
                    'details': {
                        'used_memory': used_memory,
                        'max_memory': max_memory,
                        'memory_fragmentation_ratio': redis_info.get('mem_fragmentation_ratio', 0)
                    }
                },
                'queue_lengths': queue_lengths,
                'cache_stats': cache_stats,
                'session_stats': session_stats,
                'redis_info': {
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                    'uptime_in_seconds': redis_info.get('uptime_in_seconds', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            return {'error': str(e)}
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                'cpu_usage': {
                    'value': cpu_percent,
                    'unit': '%',
                    'status': self._get_status(cpu_percent, 'cpu_usage'),
                    'details': {
                        'cpu_count': psutil.cpu_count(),
                        'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                    }
                },
                'memory_usage': {
                    'value': memory_percent,
                    'unit': '%',
                    'status': self._get_status(memory_percent, 'memory_usage'),
                    'details': {
                        'total_memory': memory.total,
                        'available_memory': memory.available,
                        'used_memory': memory.used
                    }
                },
                'disk_usage': {
                    'value': disk_percent,
                    'unit': '%',
                    'status': self._get_status(disk_percent, 'disk_usage'),
                    'details': {
                        'total_disk': disk.total,
                        'used_disk': disk.used,
                        'free_disk': disk.free
                    }
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'processes': {
                    'count': process_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {'error': str(e)}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            # Get metrics from various systems
            metrics = {}
            
            # AI Assistant metrics
            try:
                from core.universal_ai_assistant import universal_ai_assistant
                ai_stats = universal_ai_assistant.get_usage_stats()
                metrics['ai_assistant'] = ai_stats
            except Exception as e:
                logger.warning(f"Could not get AI assistant metrics: {e}")
                metrics['ai_assistant'] = {'error': str(e)}
            
            # CRM metrics
            try:
                from core.enhanced_crm_service import enhanced_crm_service
                crm_stats = enhanced_crm_service.get_statistics()
                metrics['crm'] = crm_stats
            except Exception as e:
                logger.warning(f"Could not get CRM metrics: {e}")
                metrics['crm'] = {'error': str(e)}
            
            # Document processing metrics
            try:
                from core.document_analytics_system import get_document_analytics
                doc_analytics = get_document_analytics()
                doc_stats = doc_analytics.get_statistics()
                metrics['document_processing'] = doc_stats
            except Exception as e:
                logger.warning(f"Could not get document processing metrics: {e}")
                metrics['document_processing'] = {'error': str(e)}
            
            # Workflow automation metrics
            try:
                from core.automation_engine import automation_engine
                automation_stats = automation_engine.get_automation_statistics()
                metrics['workflow_automation'] = automation_stats
            except Exception as e:
                logger.warning(f"Could not get workflow automation metrics: {e}")
                metrics['workflow_automation'] = {'error': str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting application metrics: {e}")
            return {'error': str(e)}
    
    def check_alerts(self) -> List[Alert]:
        """Check for alert conditions and generate alerts"""
        new_alerts = []
        
        try:
            # Get current metrics
            redis_metrics = self.get_redis_metrics()
            system_metrics = self.get_system_metrics()
            
            # Check Redis memory usage
            if 'redis_memory_usage' in redis_metrics:
                memory_usage = redis_metrics['redis_memory_usage']['value']
                if memory_usage >= self.alert_thresholds['redis_memory_usage']['critical']:
                    new_alerts.append(Alert(
                        id=f"redis_memory_critical_{int(time.time())}",
                        level=AlertLevel.CRITICAL,
                        title="Redis Memory Usage Critical",
                        message=f"Redis memory usage is at {memory_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
                elif memory_usage >= self.alert_thresholds['redis_memory_usage']['warning']:
                    new_alerts.append(Alert(
                        id=f"redis_memory_warning_{int(time.time())}",
                        level=AlertLevel.WARNING,
                        title="Redis Memory Usage High",
                        message=f"Redis memory usage is at {memory_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
            
            # Check queue lengths
            if 'queue_lengths' in redis_metrics:
                for queue_name, length in redis_metrics['queue_lengths'].items():
                    if length >= self.alert_thresholds['queue_length']['critical']:
                        new_alerts.append(Alert(
                            id=f"queue_critical_{queue_name}_{int(time.time())}",
                            level=AlertLevel.CRITICAL,
                            title=f"Queue {queue_name} Length Critical",
                            message=f"Queue {queue_name} has {length} items",
                            timestamp=datetime.now()
                        ))
                    elif length >= self.alert_thresholds['queue_length']['warning']:
                        new_alerts.append(Alert(
                            id=f"queue_warning_{queue_name}_{int(time.time())}",
                            level=AlertLevel.WARNING,
                            title=f"Queue {queue_name} Length High",
                            message=f"Queue {queue_name} has {length} items",
                            timestamp=datetime.now()
                        ))
            
            # Check system CPU usage
            if 'cpu_usage' in system_metrics:
                cpu_usage = system_metrics['cpu_usage']['value']
                if cpu_usage >= self.alert_thresholds['cpu_usage']['critical']:
                    new_alerts.append(Alert(
                        id=f"cpu_critical_{int(time.time())}",
                        level=AlertLevel.CRITICAL,
                        title="CPU Usage Critical",
                        message=f"CPU usage is at {cpu_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
                elif cpu_usage >= self.alert_thresholds['cpu_usage']['warning']:
                    new_alerts.append(Alert(
                        id=f"cpu_warning_{int(time.time())}",
                        level=AlertLevel.WARNING,
                        title="CPU Usage High",
                        message=f"CPU usage is at {cpu_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
            
            # Check system memory usage
            if 'memory_usage' in system_metrics:
                memory_usage = system_metrics['memory_usage']['value']
                if memory_usage >= self.alert_thresholds['memory_usage']['critical']:
                    new_alerts.append(Alert(
                        id=f"memory_critical_{int(time.time())}",
                        level=AlertLevel.CRITICAL,
                        title="System Memory Usage Critical",
                        message=f"System memory usage is at {memory_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
                elif memory_usage >= self.alert_thresholds['memory_usage']['warning']:
                    new_alerts.append(Alert(
                        id=f"memory_warning_{int(time.time())}",
                        level=AlertLevel.WARNING,
                        title="System Memory Usage High",
                        message=f"System memory usage is at {memory_usage:.1f}%",
                        timestamp=datetime.now()
                    ))
            
            # Add new alerts to the list
            for alert in new_alerts:
                # Check if alert already exists
                if not any(existing_alert.id == alert.id for existing_alert in self.alerts):
                    self.alerts.append(alert)
                    logger.warning(f"New alert: {alert.level.value} - {alert.title}")
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        try:
            # Get all metrics
            redis_metrics = self.get_redis_metrics()
            system_metrics = self.get_system_metrics()
            application_metrics = self.get_application_metrics()
            
            # Check for new alerts
            new_alerts = self.check_alerts()
            
            # Get active alerts
            active_alerts = [alert for alert in self.alerts if not alert.resolved]
            
            # Calculate overall system health
            overall_health = self._calculate_overall_health(redis_metrics, system_metrics)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_health': overall_health,
                'redis_metrics': redis_metrics,
                'system_metrics': system_metrics,
                'application_metrics': application_metrics,
                'alerts': {
                    'active': len(active_alerts),
                    'new': len(new_alerts),
                    'total': len(self.alerts),
                    'recent': [self._alert_to_dict(alert) for alert in active_alerts[-10:]]
                },
                'status': 'healthy' if overall_health['score'] >= 80 else 'warning' if overall_health['score'] >= 60 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def _get_status(self, value: float, metric_name: str) -> str:
        """Get status based on value and thresholds"""
        if metric_name in self.alert_thresholds:
            thresholds = self.alert_thresholds[metric_name]
            if value >= thresholds.get('critical', 100):
                return 'critical'
            elif value >= thresholds.get('warning', 80):
                return 'warning'
        return 'healthy'
    
    def _calculate_overall_health(self, redis_metrics: Dict, system_metrics: Dict) -> Dict[str, Any]:
        """Calculate overall system health score"""
        try:
            scores = []
            
            # Redis health
            if 'redis_memory_usage' in redis_metrics:
                redis_score = 100 - redis_metrics['redis_memory_usage']['value']
                scores.append(max(0, min(100, redis_score)))
            
            # System health
            if 'cpu_usage' in system_metrics:
                cpu_score = 100 - system_metrics['cpu_usage']['value']
                scores.append(max(0, min(100, cpu_score)))
            
            if 'memory_usage' in system_metrics:
                memory_score = 100 - system_metrics['memory_usage']['value']
                scores.append(max(0, min(100, memory_score)))
            
            if 'disk_usage' in system_metrics:
                disk_score = 100 - system_metrics['disk_usage']['value']
                scores.append(max(0, min(100, disk_score)))
            
            # Calculate average score
            overall_score = sum(scores) / len(scores) if scores else 100
            
            return {
                'score': round(overall_score, 1),
                'status': 'healthy' if overall_score >= 80 else 'warning' if overall_score >= 60 else 'critical',
                'components': {
                    'redis': scores[0] if len(scores) > 0 else 100,
                    'cpu': scores[1] if len(scores) > 1 else 100,
                    'memory': scores[2] if len(scores) > 2 else 100,
                    'disk': scores[3] if len(scores) > 3 else 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall health: {e}")
            return {'score': 0, 'status': 'critical', 'error': str(e)}
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'id': alert.id,
            'level': alert.level.value,
            'title': alert.title,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'resolved': alert.resolved,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            for alert in self.alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    logger.info(f"Alert resolved: {alert_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            total_alerts = len(self.alerts)
            active_alerts = len([alert for alert in self.alerts if not alert.resolved])
            resolved_alerts = total_alerts - active_alerts
            
            # Count by level
            level_counts = {}
            for alert in self.alerts:
                level = alert.level.value
                level_counts[level] = level_counts.get(level, 0) + 1
            
            return {
                'total_alerts': total_alerts,
                'active_alerts': active_alerts,
                'resolved_alerts': resolved_alerts,
                'level_counts': level_counts,
                'resolution_rate': (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 100
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {'error': str(e)}

# Global monitoring dashboard system instance
monitoring_dashboard_system = MonitoringDashboardSystem()

# Export the system
__all__ = ['MonitoringDashboardSystem', 'monitoring_dashboard_system', 'SystemMetric', 'Alert', 'AlertLevel']
