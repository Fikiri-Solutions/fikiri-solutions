#!/usr/bin/env python3
"""
Webhook Sentry Configuration for Fikiri Solutions
Separate Sentry instance for webhook and background job monitoring
"""

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import os

def init_webhook_sentry():
    """Initialize Sentry for webhook monitoring"""
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
            # Add data like request headers and IP for users
            send_default_pii=True,
            # Performance monitoring
            traces_sample_rate=0.1,  # 10% of transactions
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
