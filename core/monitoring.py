"""
Production Monitoring and Alerting System
Sentry integration with Slack/Email notifications
"""

import os
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Optional imports with fallbacks
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    print("Warning: sentry-sdk not available. Install with: pip install sentry-sdk[flask]")

try:
    from flask import Flask, request, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Warning: Flask not available. Install with: pip install flask")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fikiri.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages alerts and notifications for production monitoring"""
    
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.admin_email = os.getenv('ADMIN_EMAIL')
        self.support_email = os.getenv('SUPPORT_EMAIL')
        self.environment = os.getenv('SENTRY_ENVIRONMENT', 'development')
        
    def send_slack_alert(self, message: str, level: str = 'error', context: Optional[Dict[str, Any]] = None):
        """Send alert to Slack"""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured")
            return
            
        # Determine color based on level
        color_map = {
            'error': '#FF0000',      # Red
            'warning': '#FFA500',     # Orange
            'info': '#00FF00',        # Green
            'success': '#008000'      # Dark Green
        }
        
        color = color_map.get(level, '#FF0000')
        
        # Create Slack message
        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Fikiri Solutions Alert - {level.upper()}",
                    "text": message,
                    "fields": [
                        {
                            "title": "Environment",
                            "value": self.environment,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.utcnow().isoformat(),
                            "short": True
                        }
                    ],
                    "footer": "Fikiri Solutions Monitoring",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        # Add context if provided
        if context:
            for key, value in context.items():
                slack_message["attachments"][0]["fields"].append({
                    "title": key,
                    "value": str(value),
                    "short": True
                })
        
        try:
            response = requests.post(
                self.slack_webhook,
                json=slack_message,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Slack alert sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def send_email_alert(self, subject: str, message: str, level: str = 'error'):
        """Send alert via email"""
        if not self.admin_email:
            logger.warning("Admin email not configured")
            return
            
        # This would integrate with your email service
        # For now, we'll log the email content
        email_content = f"""
        Subject: {subject}
        To: {self.admin_email}
        From: alerts@fikirisolutions.com
        
        {message}
        
        Environment: {self.environment}
        Timestamp: {datetime.utcnow().isoformat()}
        """
        
        logger.info(f"Email alert: {email_content}")
        
        # TODO: Integrate with actual email service (SendGrid, SES, etc.)
    
    def alert_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Send error alert"""
        self.send_slack_alert(message, 'error', context)
        self.send_email_alert(f"ERROR: {message}", message, 'error')
    
    def alert_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Send warning alert"""
        self.send_slack_alert(message, 'warning', context)
    
    def alert_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Send info alert"""
        self.send_slack_alert(message, 'info', context)
    
    def alert_success(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Send success alert"""
        self.send_slack_alert(message, 'success', context)

# Global alert manager instance
alert_manager = AlertManager()

def init_sentry(app):
    """Initialize Sentry for error tracking and performance monitoring"""
    
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not available - error tracking disabled")
        return
    
    if not FLASK_AVAILABLE:
        logger.warning("Flask not available - Sentry initialization skipped")
        return
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not sentry_dsn:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        return
    
    # Configure Sentry
    integrations = [
        FlaskIntegration(),
        RedisIntegration(),
        LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
    ]
    
    # Only add SQLAlchemy integration if available
    try:
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        integrations.append(SqlalchemyIntegration())
    except ImportError:
        logger.warning("SQLAlchemy integration not available for Sentry")
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=integrations,
        environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
        release=os.getenv('SENTRY_RELEASE', '1.0.0'),
        # Add data like inputs and responses to/from LLMs and tools;
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Performance monitoring - full tracing for comprehensive monitoring
        traces_sample_rate=1.0,  # 100% of transactions for performance monitoring
        # Enable logs to be sent to Sentry
        enable_logs=True,
        before_send=before_send_filter,
        before_send_transaction=before_send_transaction_filter
    )
    
    logger.info("Sentry initialized for error tracking and performance monitoring")
    
    # Example: Send logs directly to Sentry using Sentry's logger
    sentry_sdk.logger.info("Sentry logging initialized - logs will be sent to Sentry")
    sentry_sdk.logger.warning("This is a warning message sent to Sentry")
    
    # Example: Using Python's built-in logging (automatically forwarded to Sentry)
    logger.info("This log will be automatically sent to Sentry")
    logger.warning("User login failed - this will be sent to Sentry")
    logger.error("Something went wrong - this will be sent to Sentry")

def before_send_filter(event, hint):
    """Filter events before sending to Sentry"""
    
    # Add custom context
    event['tags']['service'] = 'fikiri-solutions'
    event['tags']['component'] = 'backend'
    
    # Add request context if available
    if request:
        event['extra']['request_id'] = getattr(g, 'request_id', None)
        event['extra']['user_id'] = getattr(g, 'user_id', None)
        event['extra']['endpoint'] = request.endpoint
        event['extra']['method'] = request.method
        event['extra']['url'] = request.url
        event['extra']['user_agent'] = request.headers.get('User-Agent')
        event['extra']['ip_address'] = request.remote_addr
    
    # Send alert for critical errors
    if event.get('level') == 'error':
        error_message = event.get('message', 'Unknown error')
        alert_manager.alert_error(f"Sentry Error: {error_message}", {
            'event_id': event.get('event_id'),
            'level': event.get('level'),
            'logger': event.get('logger')
        })
    
    return event

def before_send_transaction_filter(event, hint):
    """Filter transactions before sending to Sentry"""
    
    # Add custom context
    event['tags']['service'] = 'fikiri-solutions'
    event['tags']['component'] = 'backend'
    
    return event

class HealthMonitor:
    """Monitor application health and send alerts"""
    
    def __init__(self):
        self.alert_manager = alert_manager
        self.health_checks = {}
        self.last_health_check = None
        
    def register_health_check(self, name: str, check_func):
        """Register a health check function"""
        self.health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        for name, check_func in self.health_checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = {
                    'status': 'healthy',
                    'details': check_result
                }
            except Exception as e:
                results['checks'][name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                results['overall_status'] = 'unhealthy'
                
                # Send alert for unhealthy check
                self.alert_manager.alert_error(
                    f"Health check failed: {name}",
                    {'error': str(e), 'check_name': name}
                )
        
        self.last_health_check = results
        return results
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # This would check your actual database
            # For now, return a mock result
            return {
                'connected': True,
                'response_time_ms': 5
            }
        except Exception as e:
            raise Exception(f"Database check failed: {e}")
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            # This would check your actual Redis connection
            # For now, return a mock result
            return {
                'connected': True,
                'response_time_ms': 2
            }
        except Exception as e:
            raise Exception(f"Redis check failed: {e}")
    
    def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        services = {
            'gmail_api': 'https://gmail.googleapis.com',
            'openai_api': 'https://api.openai.com',
            'stripe_api': 'https://api.stripe.com'
        }
        
        results = {}
        for service, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                results[service] = {
                    'status': 'healthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                results[service] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return results

# Global health monitor instance
health_monitor = HealthMonitor()

def init_health_monitoring(app: Flask):
    """Initialize health monitoring"""
    
    # Register health checks
    health_monitor.register_health_check('database', health_monitor.check_database)
    health_monitor.register_health_check('redis', health_monitor.check_redis)
    health_monitor.register_health_check('external_services', health_monitor.check_external_services)
    
    # Add health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for external monitoring"""
        return health_monitor.run_health_checks()
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check endpoint"""
        return health_monitor.run_health_checks()
    
    logger.info("Health monitoring initialized")

class PerformanceMonitor:
    """Monitor application performance and send alerts"""
    
    def __init__(self):
        self.alert_manager = alert_manager
        self.performance_thresholds = {
            'response_time_ms': 1000,  # 1 second
            'memory_usage_mb': 500,    # 500 MB
            'cpu_usage_percent': 80,   # 80%
            'error_rate_percent': 5     # 5%
        }
    
    def check_performance(self, metrics: Dict[str, Any]):
        """Check performance metrics and send alerts if thresholds exceeded"""
        
        alerts = []
        
        # Check response time
        if metrics.get('response_time_ms', 0) > self.performance_thresholds['response_time_ms']:
            alerts.append(f"High response time: {metrics['response_time_ms']}ms")
        
        # Check memory usage
        if metrics.get('memory_usage_mb', 0) > self.performance_thresholds['memory_usage_mb']:
            alerts.append(f"High memory usage: {metrics['memory_usage_mb']}MB")
        
        # Check CPU usage
        if metrics.get('cpu_usage_percent', 0) > self.performance_thresholds['cpu_usage_percent']:
            alerts.append(f"High CPU usage: {metrics['cpu_usage_percent']}%")
        
        # Check error rate
        if metrics.get('error_rate_percent', 0) > self.performance_thresholds['error_rate_percent']:
            alerts.append(f"High error rate: {metrics['error_rate_percent']}%")
        
        # Send alerts
        if alerts:
            self.alert_manager.alert_warning(
                f"Performance issues detected: {', '.join(alerts)}",
                metrics
            )

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def init_monitoring(app: Flask):
    """Initialize all monitoring systems"""
    
    # Initialize Sentry
    init_sentry(app)
    
    # Initialize health monitoring
    init_health_monitoring(app)
    
    # Add request ID middleware
    @app.before_request
    def add_request_id():
        g.request_id = str(uuid.uuid4())
    
    # Add performance monitoring middleware
    @app.before_request
    def start_timer():
        g.start_time = time.time()
    
    @app.after_request
    def log_request(response):
        # Calculate response time
        if hasattr(g, 'start_time'):
            response_time = (time.time() - g.start_time) * 1000
            
            # Log request
            logger.info(f"Request completed: {request.method} {request.path} - {response.status_code} - {response_time:.2f}ms")
            
            # Check performance
            performance_monitor.check_performance({
                'response_time_ms': response_time,
                'status_code': response.status_code,
                'endpoint': request.endpoint
            })
        
        return response
    
    logger.info("Monitoring system initialized")

# Utility functions for manual alerts
def alert_deployment_success(version: str, environment: str):
    """Send deployment success alert"""
    alert_manager.alert_success(
        f"Deployment successful: {version} to {environment}",
        {'version': version, 'environment': environment}
    )

def alert_deployment_failure(version: str, environment: str, error: str):
    """Send deployment failure alert"""
    alert_manager.alert_error(
        f"Deployment failed: {version} to {environment}",
        {'version': version, 'environment': environment, 'error': error}
    )

def alert_high_error_rate(error_rate: float, time_window: str):
    """Send high error rate alert"""
    alert_manager.alert_warning(
        f"High error rate detected: {error_rate}% in {time_window}",
        {'error_rate': error_rate, 'time_window': time_window}
    )

def alert_service_down(service: str, error: str):
    """Send service down alert"""
    alert_manager.alert_error(
        f"Service down: {service}",
        {'service': service, 'error': error}
    )
