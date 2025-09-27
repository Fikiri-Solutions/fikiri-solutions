#!/usr/bin/env python3
"""
Webhook Sentry Configuration for Fikiri Solutions
Separate Sentry instance for webhook and background job monitoring
"""

import os

# Optional Sentry integration
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    # Create dummy functions when Sentry is not available
    def sentry_sdk():
        pass
    def FlaskIntegration():
        pass
    def RedisIntegration():
        pass

def init_webhook_sentry():
    """Initialize Sentry for webhook monitoring"""
    if not SENTRY_AVAILABLE:
        print("⚠️ Sentry SDK not available, skipping webhook Sentry")
        return None
        
    webhook_dsn = os.getenv('SENTRY_DSN_WEBHOOKS')
    
    if not webhook_dsn:
        print("⚠️ SENTRY_DSN_WEBHOOKS not configured, skipping webhook Sentry")
        return None
    
    try:
        sentry_sdk.init(
            dsn=webhook_dsn,
            integrations=[
                FlaskIntegration(),
                RedisIntegration(),
            ],
            # Add data like inputs and responses to/from LLMs and tools;
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            # Performance monitoring - full tracing for comprehensive monitoring
            traces_sample_rate=1.0,  # 100% of transactions for performance monitoring
            # Enable logs to be sent to Sentry
            enable_logs=True,
            # Environment
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
            # Release tracking
            release=os.getenv('GITHUB_SHA', 'unknown'),
            # Webhook-specific tags
            before_send=lambda event, hint: add_webhook_context(event, hint)
        )
        
        print("✅ Webhook Sentry initialized successfully")
        return sentry_sdk
        
    except Exception as e:
        print(f"❌ Webhook Sentry initialization failed: {e}")
        return None

def add_webhook_context(event, hint):
    """Add webhook-specific context to Sentry events"""
    try:
        # Add webhook-specific tags
        event.setdefault('tags', {})
        event['tags']['service'] = 'webhooks'
        event['tags']['component'] = 'background_jobs'
        
        # Add webhook-specific context
        event.setdefault('contexts', {})
        event['contexts']['webhook'] = {
            'service': 'fikiri-webhooks',
            'monitoring': 'background_jobs'
        }
        
        return event
        
    except Exception as e:
        print(f"❌ Error adding webhook context: {e}")
        return event

def capture_webhook_error(error, webhook_data=None, user_id=None):
    """Capture webhook-specific errors"""
    if not SENTRY_AVAILABLE:
        print(f"⚠️ Sentry not available, skipping error capture: {error}")
        return
        
    try:
        with sentry_sdk.push_scope() as scope:
            # Add webhook-specific context
            scope.set_tag("error_type", "webhook_error")
            scope.set_tag("service", "webhooks")
            
            if webhook_data:
                scope.set_context("webhook_data", webhook_data)
            
            if user_id:
                scope.set_user({"id": user_id})
            
            # Capture the error
            sentry_sdk.capture_exception(error)
            
    except Exception as e:
        print(f"❌ Error capturing webhook error: {e}")

def capture_webhook_performance(operation_name, webhook_data=None, duration=None):
    """Capture webhook performance metrics"""
    if not SENTRY_AVAILABLE:
        print(f"⚠️ Sentry not available, skipping performance capture: {operation_name}")
        return
        
    try:
        with sentry_sdk.start_transaction(op="webhook", name=operation_name) as transaction:
            # Add webhook-specific context
            transaction.set_tag("service", "webhooks")
            transaction.set_tag("operation", operation_name)
            
            if webhook_data:
                transaction.set_context("webhook_data", webhook_data)
            
            if duration:
                transaction.set_data("duration_ms", duration)
            
            return transaction
            
    except Exception as e:
        print(f"❌ Error capturing webhook performance: {e}")
        return None

# Initialize webhook Sentry
webhook_sentry = init_webhook_sentry()

# Export functions for use in webhook handlers
__all__ = [
    'webhook_sentry',
    'capture_webhook_error',
    'capture_webhook_performance',
    'add_webhook_context'
]
