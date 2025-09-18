"""
Performance Monitoring and Metrics System
Comprehensive performance tracking for Fikiri Solutions
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import logging
from dataclasses import dataclass, asdict
import json

# Gracefully handle missing psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not available for system monitoring")

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    timestamp: datetime
    endpoint: str
    method: str
    response_time: float
    status_code: int
    memory_usage: float
    cpu_usage: float
    user_agent: str
    ip_address: str

@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: tuple
    active_connections: int
    uptime: float

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, max_metrics: int = 10000, max_system_metrics: int = 1000):
        self.max_metrics = max_metrics
        self.max_system_metrics = max_system_metrics
        
        # Performance data storage
        self.metrics: deque = deque(maxlen=max_metrics)
        self.system_metrics: deque = deque(maxlen=max_system_metrics)
        
        # Aggregated statistics
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'error_count': 0,
            'status_codes': defaultdict(int)
        })
        
        # Performance thresholds
        self.thresholds = {
            'response_time_warning': 1.0,  # 1 second
            'response_time_critical': 3.0,  # 3 seconds
            'memory_warning': 80.0,        # 80%
            'memory_critical': 95.0,       # 95%
            'cpu_warning': 80.0,           # 80%
            'cpu_critical': 95.0           # 95%
        }
        
        # Performance alerts
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts = 100
        
        # Start monitoring
        self.start_time = time.time()
        self._start_system_monitoring()
    
    def record_request(self, endpoint: str, method: str, response_time: float, 
                      status_code: int, user_agent: str = "", ip_address: str = ""):
        """Record a request performance metric"""
        try:
            # Get current system metrics
            if PSUTIL_AVAILABLE:
                memory_usage = psutil.virtual_memory().percent
                cpu_usage = psutil.cpu_percent()
            else:
                memory_usage = 0.0
                cpu_usage = 0.0
            
            # Create metric
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=status_code,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            # Store metric
            self.metrics.append(metric)
            
            # Update endpoint statistics
            self._update_endpoint_stats(endpoint, response_time, status_code)
            
            # Check for performance issues
            self._check_performance_thresholds(metric)
            
        except Exception as e:
            logger.error(f"Error recording performance metric: {e}")
    
    def _update_endpoint_stats(self, endpoint: str, response_time: float, status_code: int):
        """Update aggregated endpoint statistics"""
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_time'] += response_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], response_time)
        stats['max_time'] = max(stats['max_time'], response_time)
        stats['status_codes'][status_code] += 1
        
        if status_code >= 400:
            stats['error_count'] += 1
    
    def _check_performance_thresholds(self, metric: PerformanceMetric):
        """Check if performance metrics exceed thresholds"""
        alerts = []
        
        # Response time checks
        if metric.response_time > self.thresholds['response_time_critical']:
            alerts.append({
                'type': 'critical',
                'metric': 'response_time',
                'endpoint': metric.endpoint,
                'value': metric.response_time,
                'threshold': self.thresholds['response_time_critical'],
                'message': f"Critical response time: {metric.response_time:.2f}s for {metric.endpoint}"
            })
        elif metric.response_time > self.thresholds['response_time_warning']:
            alerts.append({
                'type': 'warning',
                'metric': 'response_time',
                'endpoint': metric.endpoint,
                'value': metric.response_time,
                'threshold': self.thresholds['response_time_warning'],
                'message': f"Slow response time: {metric.response_time:.2f}s for {metric.endpoint}"
            })
        
        # Memory checks
        if metric.memory_usage > self.thresholds['memory_critical']:
            alerts.append({
                'type': 'critical',
                'metric': 'memory',
                'value': metric.memory_usage,
                'threshold': self.thresholds['memory_critical'],
                'message': f"Critical memory usage: {metric.memory_usage:.1f}%"
            })
        elif metric.memory_usage > self.thresholds['memory_warning']:
            alerts.append({
                'type': 'warning',
                'metric': 'memory',
                'value': metric.memory_usage,
                'threshold': self.thresholds['memory_warning'],
                'message': f"High memory usage: {metric.memory_usage:.1f}%"
            })
        
        # CPU checks
        if metric.cpu_usage > self.thresholds['cpu_critical']:
            alerts.append({
                'type': 'critical',
                'metric': 'cpu',
                'value': metric.cpu_usage,
                'threshold': self.thresholds['cpu_critical'],
                'message': f"Critical CPU usage: {metric.cpu_usage:.1f}%"
            })
        elif metric.cpu_usage > self.thresholds['cpu_warning']:
            alerts.append({
                'type': 'warning',
                'metric': 'cpu',
                'value': metric.cpu_usage,
                'threshold': self.thresholds['cpu_warning'],
                'message': f"High CPU usage: {metric.cpu_usage:.1f}%"
            })
        
        # Add alerts
        for alert in alerts:
            alert['timestamp'] = metric.timestamp
            self.alerts.append(alert)
            
            # Keep only recent alerts
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
            
            logger.warning(f"Performance alert: {alert['message']}")
    
    def _start_system_monitoring(self):
        """Start background system monitoring"""
        def monitor_system():
            while True:
                try:
                    # Collect system metrics
                    if PSUTIL_AVAILABLE:
                        cpu_percent = psutil.cpu_percent(interval=1)
                        memory_percent = psutil.virtual_memory().percent
                        disk_percent = psutil.disk_usage('/').percent
                        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
                        active_connections = len(psutil.net_connections())
                    else:
                        cpu_percent = 0.0
                        memory_percent = 0.0
                        disk_percent = 0.0
                        load_avg = (0, 0, 0)
                        active_connections = 0
                    
                    # Create system metric
                    system_metric = SystemMetrics(
                        timestamp=datetime.now(),
                        cpu_percent=cpu_percent,
                        memory_percent=memory_percent,
                        disk_percent=disk_percent,
                        load_average=load_avg,
                        active_connections=active_connections,
                        uptime=time.time() - self.start_time
                    )
                    
                    # Store system metric
                    self.system_metrics.append(system_metric)
                    
                    # Sleep for 30 seconds
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
                    time.sleep(30)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # Filter recent metrics
        recent_metrics = [m for m in self.metrics if m.timestamp > last_hour]
        daily_metrics = [m for m in self.metrics if m.timestamp > last_day]
        
        # Calculate summary statistics
        if recent_metrics:
            response_times = [m.response_time for m in recent_metrics]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            # Error rate
            error_count = sum(1 for m in recent_metrics if m.status_code >= 400)
            error_rate = (error_count / len(recent_metrics)) * 100
            
            # Throughput (requests per minute)
            throughput = len(recent_metrics) / 60
            
        else:
            avg_response_time = 0
            max_response_time = 0
            min_response_time = 0
            error_rate = 0
            throughput = 0
        
        # System metrics
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            current_cpu = latest_system.cpu_percent
            current_memory = latest_system.memory_percent
            current_disk = latest_system.disk_percent
            uptime = latest_system.uptime
        else:
            current_cpu = 0
            current_memory = 0
            current_disk = 0
            uptime = time.time() - self.start_time
        
        # Top endpoints by request count
        top_endpoints = sorted(
            self.endpoint_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]
        
        # Recent alerts
        recent_alerts = [a for a in self.alerts if a['timestamp'] > last_hour]
        
        return {
            'timestamp': now.isoformat(),
            'uptime_seconds': uptime,
            'requests': {
                'total_last_hour': len(recent_metrics),
                'total_last_day': len(daily_metrics),
                'avg_response_time': round(avg_response_time, 3),
                'max_response_time': round(max_response_time, 3),
                'min_response_time': round(min_response_time, 3),
                'error_rate_percent': round(error_rate, 2),
                'throughput_rpm': round(throughput, 2)
            },
            'system': {
                'cpu_percent': round(current_cpu, 1),
                'memory_percent': round(current_memory, 1),
                'disk_percent': round(current_disk, 1),
                'load_average': latest_system.load_average if self.system_metrics else (0, 0, 0)
            },
            'endpoints': {
                endpoint: {
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 3),
                    'min_time': round(stats['min_time'], 3),
                    'max_time': round(stats['max_time'], 3),
                    'error_count': stats['error_count'],
                    'error_rate': round((stats['error_count'] / stats['count']) * 100, 2) if stats['count'] > 0 else 0
                }
                for endpoint, stats in top_endpoints
            },
            'alerts': {
                'total_last_hour': len(recent_alerts),
                'critical_count': len([a for a in recent_alerts if a['type'] == 'critical']),
                'warning_count': len([a for a in recent_alerts if a['type'] == 'warning']),
                'recent_alerts': recent_alerts[-5:]  # Last 5 alerts
            },
            'thresholds': self.thresholds
        }
    
    def get_endpoint_performance(self, endpoint: str) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific endpoint"""
        if endpoint not in self.endpoint_stats:
            return {'error': 'Endpoint not found'}
        
        stats = self.endpoint_stats[endpoint]
        
        # Get recent metrics for this endpoint
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        recent_metrics = [
            m for m in self.metrics 
            if m.endpoint == endpoint and m.timestamp > last_hour
        ]
        
        if recent_metrics:
            response_times = [m.response_time for m in recent_metrics]
            avg_response_time = sum(response_times) / len(response_times)
            
            # Status code distribution
            status_codes = defaultdict(int)
            for m in recent_metrics:
                status_codes[m.status_code] += 1
        else:
            avg_response_time = 0
            status_codes = {}
        
        return {
            'endpoint': endpoint,
            'total_requests': stats['count'],
            'avg_response_time': round(stats['avg_time'], 3),
            'min_response_time': round(stats['min_time'], 3),
            'max_response_time': round(stats['max_time'], 3),
            'error_count': stats['error_count'],
            'error_rate': round((stats['error_count'] / stats['count']) * 100, 2) if stats['count'] > 0 else 0,
            'status_codes': dict(stats['status_codes']),
            'recent_avg_response_time': round(avg_response_time, 3),
            'recent_status_codes': dict(status_codes)
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        if not self.system_metrics:
            return {'status': 'unknown', 'message': 'No system metrics available'}
        
        latest = self.system_metrics[-1]
        
        # Determine health status
        health_issues = []
        
        if latest.cpu_percent > self.thresholds['cpu_critical']:
            health_issues.append('critical_cpu')
        elif latest.cpu_percent > self.thresholds['cpu_warning']:
            health_issues.append('high_cpu')
        
        if latest.memory_percent > self.thresholds['memory_critical']:
            health_issues.append('critical_memory')
        elif latest.memory_percent > self.thresholds['memory_warning']:
            health_issues.append('high_memory')
        
        if latest.disk_percent > 90:
            health_issues.append('low_disk_space')
        
        # Determine overall status
        if any('critical' in issue for issue in health_issues):
            status = 'critical'
        elif health_issues:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'timestamp': latest.timestamp.isoformat(),
            'uptime_seconds': latest.uptime,
            'metrics': {
                'cpu_percent': round(latest.cpu_percent, 1),
                'memory_percent': round(latest.memory_percent, 1),
                'disk_percent': round(latest.disk_percent, 1),
                'load_average': latest.load_average,
                'active_connections': latest.active_connections
            },
            'issues': health_issues,
            'message': f"System is {status}" + (f" with issues: {', '.join(health_issues)}" if health_issues else "")
        }
    
    def export_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Export metrics for external analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        filtered_system_metrics = [m for m in self.system_metrics if m.timestamp > cutoff_time]
        
        return {
            'export_timestamp': datetime.now().isoformat(),
            'time_range_hours': hours,
            'request_metrics': [asdict(m) for m in filtered_metrics],
            'system_metrics': [asdict(m) for m in filtered_system_metrics],
            'endpoint_stats': dict(self.endpoint_stats),
            'alerts': self.alerts[-100:]  # Last 100 alerts
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

