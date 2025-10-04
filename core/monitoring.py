"""
Production Monitoring and Alerting System
Sentry integration with Slack/Email notifications - Production Ready
"""

import os
import logging
import requests
import json
import uuid
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

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
    from flask import Flask, request, g, jsonify
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
                            "value": datetime.now(timezone.utc).isoformat(),
                            "short": True
                        }
                    ],
                    "footer": "Fikiri Solutions Monitoring",
                    "ts": int(datetime.now(timezone.utc).timestamp())
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
        """Send alert via email with enhanced implementation"""
        if not self.admin_email:
            logger.warning("Admin email not configured")
            return
            
        # Enhanced email implementation
        try:
            # Try to use SendGrid if available
            sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            if sendgrid_api_key:
                self._send_via_sendgrid(subject, message, level)
                return
            
            # Try to use AWS SES if available
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            if aws_access_key:
                self._send_via_ses(subject, message, level)
                return
            
            # Fallback to SMTP
            smtp_server = os.getenv('SMTP_SERVER')
            if smtp_server:
                self._send_via_smtp(subject, message, level)
                return
            
            # Final fallback - log email content
            email_content = f"""
            Subject: {subject}
            To: {self.admin_email}
            From: alerts@fikirisolutions.com
            
            {message}
            
            Environment: {self.environment}
            Timestamp: {datetime.now(timezone.utc).isoformat()}
            """
            
            logger.info(f"Email alert (logged): {email_content}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_via_sendgrid(self, subject: str, message: str, level: str):
        """Send email via SendGrid"""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            
            sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
            
            email_content = f"""
            {message}
            
            Environment: {self.environment}
            Timestamp: {datetime.now(timezone.utc).isoformat()}
            """
            
            mail = Mail(
                from_email='alerts@fikirisolutions.com',
                to_emails=self.admin_email,
                subject=f"[{level.upper()}] {subject}",
                html_content=email_content
            )
            
            response = sg.send(mail)
            logger.info(f"Email sent via SendGrid: {response.status_code}")
            
        except ImportError:
            logger.warning("SendGrid not available")
        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
    
    def _send_via_ses(self, subject: str, message: str, level: str):
        """Send email via AWS SES"""
        try:
            import boto3
            
            ses_client = boto3.client('ses')
            
            email_content = f"""
            {message}
            
            Environment: {self.environment}
            Timestamp: {datetime.now(timezone.utc).isoformat()}
            """
            
            response = ses_client.send_email(
                Source='alerts@fikirisolutions.com',
                Destination={'ToAddresses': [self.admin_email]},
                Message={
                    'Subject': {'Data': f"[{level.upper()}] {subject}"},
                    'Body': {'Text': {'Data': email_content}}
                }
            )
            
            logger.info(f"Email sent via SES: {response['MessageId']}")
            
        except ImportError:
            logger.warning("boto3 not available")
        except Exception as e:
            logger.error(f"SES email failed: {e}")
    
    def _send_via_smtp(self, subject: str, message: str, level: str):
        """Send email via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            msg = MIMEMultipart()
            msg['From'] = 'alerts@fikirisolutions.com'
            msg['To'] = self.admin_email
            msg['Subject'] = f"[{level.upper()}] {subject}"
            
            email_content = f"""
            {message}
            
            Environment: {self.environment}
            Timestamp: {datetime.now(timezone.utc).isoformat()}
            """
            
            msg.attach(MIMEText(email_content, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            
            text = msg.as_string()
            server.sendmail('alerts@fikirisolutions.com', self.admin_email, text)
            server.quit()
            
            logger.info("Email sent via SMTP")
            
        except Exception as e:
            logger.error(f"SMTP email failed: {e}")
    
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
    
    # Configure enable_logs based on environment
    enable_logs = os.getenv('SENTRY_ENABLE_LOGS', 'true').lower() == 'true'
    if os.getenv('SENTRY_ENVIRONMENT', 'development') == 'production':
        enable_logs = False  # Disable in production to avoid double-logging
    
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
        enable_logs=enable_logs,
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
    """Filter events before sending to Sentry with enhanced safety"""
    
    # Add custom context
    event['tags']['service'] = 'fikiri-solutions'
    event['tags']['component'] = 'backend'
    
    # Add request context if available and safe
    if FLASK_AVAILABLE and request:
        try:
            event['extra']['request_id'] = getattr(g, 'request_id', None)
            event['extra']['user_id'] = getattr(g, 'user_id', None)
            event['extra']['endpoint'] = request.endpoint
            event['extra']['method'] = request.method
            event['extra']['url'] = request.url
            event['extra']['user_agent'] = request.headers.get('User-Agent')
            event['extra']['ip_address'] = request.remote_addr
        except Exception as e:
            logger.warning(f"Failed to add request context to Sentry event: {e}")
    
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
    """Monitor application health and send alerts with enhanced features"""
    
    def __init__(self):
        self.alert_manager = alert_manager
        self.health_checks = {}
        self.last_health_check = None
        self.health_history = []
        self.max_history = 100  # Keep last 100 health checks
        
    def register_health_check(self, name: str, check_func):
        """Register a health check function"""
        self.health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks with enhanced features"""
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'healthy',
            'checks': {},
            'uptime_seconds': self._get_uptime(),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('SENTRY_ENVIRONMENT', 'development')
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
        
        # Store in history
        self.health_history.append(results)
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
        
        return results
    
    def _get_uptime(self) -> float:
        """Get application uptime in seconds"""
        try:
            # Try to read from uptime file
            uptime_file = Path('data/uptime.txt')
            if uptime_file.exists():
                with open(uptime_file, 'r') as f:
                    start_time = float(f.read().strip())
                return time.time() - start_time
            else:
                # Create uptime file
                uptime_file.parent.mkdir(exist_ok=True)
                with open(uptime_file, 'w') as f:
                    f.write(str(time.time()))
                return 0.0
        except Exception:
            return 0.0
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity with enhanced checks"""
        try:
            # Try to import and check database optimizer
            from core.database_optimization import db_optimizer
            
            start_time = time.time()
            
            # Simple query to test connectivity
            result = db_optimizer.execute_query("SELECT 1", fetch=True)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'connected': True,
                'response_time_ms': round(response_time, 2),
                'database_type': getattr(db_optimizer, 'db_type', 'unknown'),
                'test_query_success': True
            }
        except Exception as e:
            raise Exception(f"Database check failed: {e}")
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity with enhanced checks"""
        try:
            import redis
            
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                client = redis.from_url(redis_url, decode_responses=True)
            else:
                client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
            
            start_time = time.time()
            client.ping()
            response_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = client.info()
            
            return {
                'connected': True,
                'response_time_ms': round(response_time, 2),
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory_mb': round(info.get('used_memory', 0) / 1024 / 1024, 2),
                'connected_clients': info.get('connected_clients', 0)
            }
        except Exception as e:
            raise Exception(f"Redis check failed: {e}")
    
    def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity with enhanced timeout handling"""
        services = {
            'gmail_api': 'https://gmail.googleapis.com',
            'openai_api': 'https://api.openai.com',
            'stripe_api': 'https://api.stripe.com'
        }
        
        results = {}
        for service, url in services.items():
            try:
                # Use shorter timeout for health checks
                response = requests.get(url, timeout=3)
                results[service] = {
                    'status': 'healthy',
                    'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2),
                    'status_code': response.status_code
                }
            except requests.exceptions.Timeout:
                results[service] = {
                    'status': 'timeout',
                    'error': 'Request timeout (>3s)',
                    'response_time_ms': 3000
                }
            except requests.exceptions.ConnectionError:
                results[service] = {
                    'status': 'connection_error',
                    'error': 'Connection failed',
                    'response_time_ms': None
                }
            except Exception as e:
                results[service] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'response_time_ms': None
                }
        
        return results

# Global health monitor instance
health_monitor = HealthMonitor()

def init_health_monitoring(app: Flask):
    """Initialize health monitoring with enhanced features"""
    
    # Register health checks
    health_monitor.register_health_check('database', health_monitor.check_database)
    health_monitor.register_health_check('redis', health_monitor.check_redis)
    health_monitor.register_health_check('external_services', health_monitor.check_external_services)
    
    # Add health check endpoint with proper JSON response
    @app.route('/health')
    def health_check():
        """Health check endpoint for external monitoring"""
        results = health_monitor.run_health_checks()
        return jsonify(results)
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check endpoint with history"""
        results = health_monitor.run_health_checks()
        
        # Add health history
        results['health_history'] = health_monitor.health_history[-10:]  # Last 10 checks
        
        return jsonify(results)
    
    logger.info("Health monitoring initialized")

class PerformanceMonitor:
    """Monitor application performance and send alerts with persistence"""
    
    def __init__(self):
        self.alert_manager = alert_manager
        self.performance_thresholds = {
            'response_time_ms': 1000,  # 1 second
            'memory_usage_mb': 500,    # 500 MB
            'cpu_usage_percent': 80,   # 80%
            'error_rate_percent': 5     # 5%
        }
        self.performance_history = []
        self.max_history = 1000  # Keep last 1000 performance records
    
    def check_performance(self, metrics: Dict[str, Any]):
        """Check performance metrics and send alerts if thresholds exceeded"""
        
        # Add timestamp to metrics
        metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Store in history
        self.performance_history.append(metrics)
        if len(self.performance_history) > self.max_history:
            self.performance_history = self.performance_history[-self.max_history:]
        
        # Persist to file
        self._persist_performance_metrics(metrics)
        
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
    
    def _persist_performance_metrics(self, metrics: Dict[str, Any]):
        """Persist performance metrics to file"""
        try:
            metrics_file = Path('data/performance_metrics.json')
            metrics_file.parent.mkdir(exist_ok=True)
            
            # Load existing metrics
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        content = f.read().strip()
                        if content:  # Guard against empty files
                            all_metrics = json.loads(content)
                        else:
                            all_metrics = []
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Corrupted performance metrics file: {metrics_file}. Starting fresh.")
                    all_metrics = []
            else:
                all_metrics = []
            
            # Add new metrics
            all_metrics.append(metrics)
            
            # Keep only last 1000 records
            if len(all_metrics) > 1000:
                all_metrics = all_metrics[-1000:]
            
            # Save back to file
            with open(metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to persist performance metrics: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.performance_history:
            return {'error': 'No performance data available'}
        
        response_times = [m.get('response_time_ms', 0) for m in self.performance_history if 'response_time_ms' in m]
        
        if response_times:
            return {
                'total_requests': len(self.performance_history),
                'avg_response_time_ms': round(sum(response_times) / len(response_times), 2),
                'max_response_time_ms': max(response_times),
                'min_response_time_ms': min(response_times),
                'threshold_exceeded_count': len([t for t in response_times if t > self.performance_thresholds['response_time_ms']])
            }
        else:
            return {'error': 'No response time data available'}

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def periodic_health_check():
    """Periodic health check job for uptime monitoring"""
    while True:
        try:
            results = health_monitor.run_health_checks()
            if results['overall_status'] != 'healthy':
                alert_manager.alert_warning("Background health check issue", results)
            
            # Sleep for 5 minutes
            time.sleep(300)
        except Exception as e:
            logger.error(f"Periodic health check failed: {e}")
            time.sleep(60)  # Sleep for 1 minute on error

def init_monitoring(app: Flask):
    """Initialize all monitoring systems with enhanced features"""
    
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
                'endpoint': request.endpoint,
                'request_id': getattr(g, 'request_id', None)
            })
        
        return response
    
    # Start periodic health check in background thread
    health_check_thread = threading.Thread(target=periodic_health_check, daemon=True)
    health_check_thread.start()
    
    # Add performance stats endpoint
    @app.route('/performance/stats')
    def performance_stats():
        """Get performance statistics"""
        stats = performance_monitor.get_performance_stats()
        return jsonify(stats)
    
    logger.info("Monitoring system initialized with enhanced features")

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