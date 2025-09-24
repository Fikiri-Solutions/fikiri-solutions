#!/usr/bin/env python3
"""
Fikiri Solutions - Flask Web Application
Web interface for testing and deploying Fikiri services.
"""

import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

# Initialize Sentry before Flask app
sentry_sdk.init(
    dsn="https://05d4170350ee081a3bfee0dda0220df6@o4510053728845824.ingest.us.sentry.io/4510053767249920",
    integrations=[
        FlaskIntegration(),
        RedisIntegration(),
        SqlalchemyIntegration(),
    ],
    # Add data like inputs and responses to/from LLMs and tools;
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # Performance monitoring - full tracing for comprehensive monitoring
    traces_sample_rate=1.0,  # 100% of transactions for performance monitoring
    # Enable logs to be sent to Sentry
    enable_logs=True,
    # Environment
    environment=os.getenv('FLASK_ENV', 'production'),
    # Release tracking
    release=os.getenv('GITHUB_SHA', 'unknown'),
)

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Import our core services
from core.minimal_config import get_config
from core.minimal_auth import MinimalAuthenticator
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_gmail_utils import MinimalGmailService
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_crm_service import MinimalCRMService
from core.minimal_ai_assistant import MinimalAIEmailAssistant
from core.minimal_ml_scoring import MinimalMLScoring
from core.minimal_vector_search import MinimalVectorSearch
# from core.strategic_hybrid_service import StrategicHybridService  # Removed - causing issues
from core.feature_flags import get_feature_flags
from core.email_service_manager import EmailServiceManager

# Import Responses API migration system
from core.responses_api_migration import responses_manager
from core.client_analytics import analytics_engine

# Import billing system
from core.billing_api import billing_bp
from core.fikiri_stripe_manager import FikiriStripeManager
from core.usage_tracker import UsageTracker

# Import Redis integration
from core.redis_cache import get_cache, cache_result
from core.redis_sessions import init_flask_sessions, create_user_session, get_current_user, logout_user, require_login
from core.redis_rate_limiting import init_rate_limiting, rate_limit, get_rate_limiter
from core.redis_queues import get_email_queue, get_ai_queue, get_crm_queue, get_webhook_queue
from core.webhook_sentry import capture_webhook_error, capture_webhook_performance

# Dashboard routes will be added directly to Flask app

# Import enterprise features
from core.enterprise_logging import log_api_request, log_service_action, log_security_event
from core.enterprise_security import security_manager, UserRole, Permission

# Import API validation
from core.api_validation import (
    validate_api_request, handle_api_errors, create_success_response, create_error_response,
    LOGIN_SCHEMA, LEAD_SCHEMA, CHAT_SCHEMA, ValidationError, APIError
)

# Import backend excellence features
from core.backend_excellence import (
    APIVersion, api_version, async_manager, async_operation,
    db_pool, cache_manager, cached, background_tasks,
    rate_limit, create_api_blueprint
)

# Import database optimization
from core.database_optimization import (
    db_optimizer, migration_manager, QueryMetrics, IndexInfo
)

# Import business operations
from core.business_operations import (
    business_analytics, business_intelligence, legal_compliance,
    create_business_blueprint
)

# Import monitoring and backup systems
from core.monitoring_backup import (
    monitoring_system, backup_manager, Alert
)

# Import monitoring and performance tracking
from core.structured_logging import logger, monitor, error_tracker
from core.performance_monitor import performance_monitor

# ML dependencies removed for lightweight operation
# Using lightweight alternatives for optimal performance

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:3000',  # Local development
    'https://fikirisolutions.vercel.app',  # Vercel deployment
    'https://fikirisolutions.com',  # Custom domain
    'https://www.fikirisolutions.com'  # Custom domain with www
])

# Initialize Redis integration
init_flask_sessions(app)
init_rate_limiting(app)

# Register versioned API blueprints
app.register_blueprint(create_api_blueprint('v1'))
app.register_blueprint(create_api_blueprint('v2'))

# Register business operations blueprint
app.register_blueprint(create_business_blueprint())

# Register billing blueprint
app.register_blueprint(billing_bp)

# Register webhook blueprint
from core.webhook_api import webhook_bp
app.register_blueprint(webhook_bp)

# Register CRM completion blueprint
from core.crm_completion_api import crm_bp
app.register_blueprint(crm_bp)

# Initialize SocketIO for real-time updates (disabled for now)
# socketio = SocketIO(app, cors_allowed_origins=[
#     'http://localhost:3000',
#     'https://fikirisolutions.vercel.app',
#     'https://fikirisolutions.com',
#     'https://www.fikirisolutions.com'
# ])
app.secret_key = os.getenv('SECRET_KEY', 'fikiri-secret-key-2024')

# Global service instances
services = {
    'config': None,
    'auth': None,
    'parser': None,
    'gmail': None,
    'actions': None,
    'crm': None,
    'ai_assistant': None,
    'ml_scoring': None,
    'vector_search': None,
    'hybrid': None,  # Removed - causing issues
    'feature_flags': None,
    'email_manager': None
}

def initialize_services():
    """Initialize all services."""
    global services
    
    try:
        services['config'] = get_config()
        services['auth'] = MinimalAuthenticator()
        services['parser'] = MinimalEmailParser()
        services['gmail'] = MinimalGmailService()
        services['actions'] = MinimalEmailActions()
        services['crm'] = MinimalCRMService()
        services['ai_assistant'] = MinimalAIEmailAssistant(api_key=os.getenv("OPENAI_API_KEY"))
        services['ml_scoring'] = MinimalMLScoring()
        services['vector_search'] = MinimalVectorSearch()
        # services['hybrid'] = StrategicHybridService()  # Removed - causing issues
        services['feature_flags'] = get_feature_flags()
        services['email_manager'] = EmailServiceManager()
        
        print("✅ All services initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

# Initialize services on startup
initialize_services()

# Add request logging middleware
@app.before_request
def log_request():
    """Log all incoming requests."""
    request.start_time = time.time()

@app.after_request
def log_response(response):
    """Log all outgoing responses with performance monitoring."""
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        
        # Log to enterprise logging
        log_api_request(
            endpoint=request.endpoint or request.path,
            method=request.method,
            status_code=response.status_code,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Record performance metrics
        performance_monitor.record_request(
            endpoint=request.endpoint or request.path,
            method=request.method,
            response_time=response_time,
            status_code=response.status_code,
            user_agent=request.headers.get('User-Agent', ''),
            ip_address=request.remote_addr or ''
        )
    return response

# Add security endpoints
@app.route('/api/auth/login', methods=['POST'])
@handle_api_errors
def api_login():
    """User login endpoint with comprehensive validation."""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
    
    # Basic validation
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')
    
    email = data['email']
    password = data['password']
    
    # For demo purposes, accept any password
    user = security_manager.authenticate_user(email, password)
    
    if user:
        session_obj = security_manager.create_session(
            user, 
            request.remote_addr, 
            request.headers.get('User-Agent', '')
        )
        
        session['session_id'] = session_obj.session_id
        session['user_id'] = user.id
        
        log_security_event(
            event_type="user_login",
            severity="info",
            details={"user_id": user.id, "email": user.email}
        )
        
        # Track business analytics
        business_analytics.track_event('user_login', {
            'user_id': user.id,
            'email': user.email,
            'login_method': 'email_password'
        })
        
        return create_success_response({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role.value
            },
            'session_id': session_obj.session_id
        }, "Login successful")
    else:
        log_security_event(
            event_type="failed_login",
            severity="warning",
            details={"email": email, "ip": request.remote_addr}
        )
        return create_error_response("Invalid credentials", 401, "INVALID_CREDENTIALS")

# Import new authentication modules
from core.user_auth import user_auth_manager
from core.gmail_oauth import gmail_oauth_manager, gmail_sync_manager
from core.privacy_manager import privacy_manager
from core.universal_ai_assistant import universal_ai_assistant
from core.enhanced_crm_service import enhanced_crm_service
from core.email_parser_service import email_parser_service
from core.automation_engine import automation_engine
from core.onboarding_orchestrator import onboarding_orchestrator
from core.automation_safety import automation_safety_manager
from core.rate_limiter import rate_limiter
from core.oauth_token_manager import oauth_token_manager

# User registration endpoint
@app.route('/api/auth/signup', methods=['POST'])
@handle_api_errors
def api_signup():
    """User registration endpoint with comprehensive validation."""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
    
    # Basic validation
    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')
    
    result = user_auth_manager.create_user(
        email=data['email'],
        password=data['password'],
        name=data['name'],
        business_name=data.get('business_name'),
        business_email=data.get('business_email'),
        industry=data.get('industry'),
        team_size=data.get('team_size')
    )
    
    if result['success']:
        log_security_event(
            event_type="user_registration",
            severity="info",
            details={"user_id": result['user'].id, "email": result['user'].email}
        )
        
        # Track business analytics
        business_analytics.track_event('user_signup', {
            'user_id': result['user'].id,
            'email': result['user'].email,
            'industry': data.get('industry'),
            'team_size': data.get('team_size')
        })
        
        return create_success_response({
            'user': {
                'id': result['user'].id,
                'email': result['user'].email,
                'name': result['user'].name,
                'role': result['user'].role,
                'onboarding_completed': result['user'].onboarding_completed,
                'onboarding_step': result['user'].onboarding_step
            }
        }, "Account created successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# Gmail OAuth endpoints
@app.route('/api/auth/gmail/connect', methods=['POST'])
@handle_api_errors
def api_gmail_connect():
    """Generate Gmail OAuth authorization URL."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = gmail_oauth_manager.generate_auth_url(user_id)
    
    if result['success']:
        return create_success_response({
            'auth_url': result['auth_url'],
            'state': result['state']
        }, "Gmail authorization URL generated")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/auth/gmail/callback', methods=['GET'])
@handle_api_errors
def api_gmail_callback():
    """Handle Gmail OAuth callback."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return create_error_response(f"OAuth error: {error}", 400, "OAUTH_ERROR")
    
    if not code or not state:
        return create_error_response("Missing code or state parameter", 400, "MISSING_PARAMETERS")
    
    result = gmail_oauth_manager.handle_oauth_callback(code, state)
    
    if result['success']:
        return create_success_response({
            'user_id': result['user_id']
        }, "Gmail account connected successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/auth/gmail/status', methods=['GET'])
@handle_api_errors
def api_gmail_status():
    """Check Gmail connection status."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    is_connected = gmail_oauth_manager.is_gmail_connected(int(user_id))
    
    return create_success_response({
        'connected': is_connected,
        'user_id': user_id
    }, "Gmail status retrieved")

@app.route('/api/auth/gmail/disconnect', methods=['POST'])
@handle_api_errors
def api_gmail_disconnect():
    """Disconnect Gmail account."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = gmail_oauth_manager.revoke_gmail_access(int(user_id))
    
    if result['success']:
        return create_success_response({
            'user_id': user_id
        }, "Gmail account disconnected")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# Email sync endpoints
@app.route('/api/email/sync/start', methods=['POST'])
@handle_api_errors
def api_start_email_sync():
    """Start initial email synchronization."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = gmail_sync_manager.start_initial_sync(int(user_id))
    
    if result['success']:
        return create_success_response({
            'sync_id': result['sync_id']
        }, "Email sync started")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/email/sync/status', methods=['GET'])
@handle_api_errors
def api_email_sync_status():
    """Get email sync status."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    sync_status = gmail_sync_manager.get_sync_status(int(user_id))
    
    if sync_status:
        return create_success_response({
            'sync_id': sync_status.id,
            'status': sync_status.status,
            'emails_processed': sync_status.emails_processed,
            'emails_total': sync_status.emails_total,
            'started_at': sync_status.started_at.isoformat(),
            'completed_at': sync_status.completed_at.isoformat() if sync_status.completed_at else None,
            'error_message': sync_status.error_message
        }, "Sync status retrieved")
    else:
        return create_success_response({
            'status': 'no_sync'
        }, "No sync found")

# Onboarding endpoints
@app.route('/api/onboarding/update', methods=['POST'])
@handle_api_errors
def api_update_onboarding(validated_data):
    """Update user onboarding progress."""
    user_id = data['user_id']
    step = data['step']
    completed = data.get('completed', False)
    
    result = user_auth_manager.update_user_profile(
        user_id,
        onboarding_step=step,
        onboarding_completed=completed
    )
    
    if result['success']:
        return create_success_response({
            'user': {
                'id': result['user'].id,
                'onboarding_step': result['user'].onboarding_step,
                'onboarding_completed': result['user'].onboarding_completed
            }
        }, "Onboarding progress updated")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/onboarding/status', methods=['GET'])
@handle_api_errors
def api_onboarding_status():
    """Get user onboarding status."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    user = user_auth_manager.get_user_by_id(int(user_id))
    
    if not user:
        return create_error_response("User not found", 404, "USER_NOT_FOUND")
    
    return create_success_response({
        'user_id': user.id,
        'onboarding_step': user.onboarding_step,
        'onboarding_completed': user.onboarding_completed,
        'gmail_connected': gmail_oauth_manager.is_gmail_connected(user.id)
    }, "Onboarding status retrieved")

# Privacy and Data Management endpoints
@app.route('/api/privacy/settings', methods=['GET'])
@handle_api_errors
def api_get_privacy_settings():
    """Get user privacy settings."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    settings = privacy_manager.get_privacy_settings(int(user_id))
    
    if settings:
        return create_success_response({
            'data_retention_days': settings.data_retention_days,
            'email_scanning_enabled': settings.email_scanning_enabled,
            'personal_email_exclusion': settings.personal_email_exclusion,
            'auto_labeling_enabled': settings.auto_labeling_enabled,
            'lead_detection_enabled': settings.lead_detection_enabled,
            'analytics_tracking_enabled': settings.analytics_tracking_enabled,
            'updated_at': settings.updated_at.isoformat()
        }, "Privacy settings retrieved")
    else:
        # Create default settings if none exist
        result = privacy_manager.create_default_privacy_settings(int(user_id))
        if result['success']:
            settings = privacy_manager.get_privacy_settings(int(user_id))
            return create_success_response({
                'data_retention_days': settings.data_retention_days,
                'email_scanning_enabled': settings.email_scanning_enabled,
                'personal_email_exclusion': settings.personal_email_exclusion,
                'auto_labeling_enabled': settings.auto_labeling_enabled,
                'lead_detection_enabled': settings.lead_detection_enabled,
                'analytics_tracking_enabled': settings.analytics_tracking_enabled,
                'updated_at': settings.updated_at.isoformat()
            }, "Default privacy settings created")
        else:
            return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/settings', methods=['PUT'])
@handle_api_errors
def api_update_privacy_settings(validated_data):
    """Update user privacy settings."""
    user_id = data['user_id']
    
    # Remove user_id from updates
    updates = {k: v for k, v in validated_data.items() if k != 'user_id'}
    
    result = privacy_manager.update_privacy_settings(user_id, **updates)
    
    if result['success']:
        return create_success_response({
            'settings': {
                'data_retention_days': result['settings'].data_retention_days,
                'email_scanning_enabled': result['settings'].email_scanning_enabled,
                'personal_email_exclusion': result['settings'].personal_email_exclusion,
                'auto_labeling_enabled': result['settings'].auto_labeling_enabled,
                'lead_detection_enabled': result['settings'].lead_detection_enabled,
                'analytics_tracking_enabled': result['settings'].analytics_tracking_enabled,
                'updated_at': result['settings'].updated_at.isoformat()
            }
        }, "Privacy settings updated successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/consent', methods=['POST'])
@handle_api_errors
def api_record_privacy_consent(validated_data):
    """Record user privacy consent."""
    result = privacy_manager.record_privacy_consent(
        user_id=data['user_id'],
        consent_type=data['consent_type'],
        granted=data['granted'],
        consent_text=data['consent_text'],
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    if result['success']:
        return create_success_response({
            'consent_type': data['consent_type'],
            'granted': data['granted']
        }, "Privacy consent recorded successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/consents', methods=['GET'])
@handle_api_errors
def api_get_privacy_consents():
    """Get user privacy consents."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    consents = privacy_manager.get_privacy_consents(int(user_id))
    
    return create_success_response({
        'consents': [
            {
                'id': consent.id,
                'consent_type': consent.consent_type,
                'granted': consent.granted,
                'consent_text': consent.consent_text,
                'granted_at': consent.granted_at.isoformat(),
                'revoked_at': consent.revoked_at.isoformat() if consent.revoked_at else None
            }
            for consent in consents
        ]
    }, "Privacy consents retrieved")

@app.route('/api/privacy/data-summary', methods=['GET'])
@handle_api_errors
def api_get_data_summary():
    """Get user data summary for privacy dashboard."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = privacy_manager.get_data_summary(int(user_id))
    
    if result['success']:
        return create_success_response(result['data_summary'], "Data summary retrieved")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/cleanup', methods=['POST'])
@handle_api_errors
def api_cleanup_expired_data():
    """Clean up expired data based on retention settings."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = privacy_manager.cleanup_expired_data(int(user_id))
    
    if result['success']:
        return create_success_response({
            'cleanup_results': result['cleanup_results'],
            'total_deleted': result['total_deleted']
        }, "Data cleanup completed successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/export', methods=['GET'])
@handle_api_errors
def api_export_user_data():
    """Export all user data for GDPR compliance."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = privacy_manager.export_user_data(int(user_id))
    
    if result['success']:
        return create_success_response(result['export_data'], "User data exported successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/privacy/delete', methods=['POST'])
@handle_api_errors
def api_delete_user_data(validated_data):
    """Delete all user data for GDPR compliance."""
    if data['confirmation'] != 'DELETE_ALL_MY_DATA':
        return create_error_response("Invalid confirmation", 400, "INVALID_CONFIRMATION")
    
    result = privacy_manager.delete_user_data(data['user_id'])
    
    if result['success']:
        return create_success_response({
            'deleted_records': result['deleted_records']
        }, "User data deleted successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# Test endpoint to debug AI assistant
@app.route('/api/ai/test', methods=['POST'])
def api_ai_test():
    """Test endpoint to debug AI assistant issues."""
    try:
        print("🔍 AI Test Debug: Starting test")
        
        # Test 1: Check if universal_ai_assistant is imported
        print(f"🔍 AI Test Debug: universal_ai_assistant type: {type(universal_ai_assistant)}")
        
        # Test 2: Check if it has process_query method
        print(f"🔍 AI Test Debug: Has process_query: {hasattr(universal_ai_assistant, 'process_query')}")
        
        # Test 3: Try to call process_query
        print("🔍 AI Test Debug: Calling process_query...")
        result = universal_ai_assistant.process_query(
            user_message="test message",
            user_id=1,
            context={}
        )
        
        print(f"🔍 AI Test Debug: Result success: {result.success}")
        print(f"🔍 AI Test Debug: Response: {result.response[:100] if result.response else 'No response'}...")
        
        return jsonify({
            'success': True,
            'message': 'AI test completed',
            'result_success': result.success,
            'response_preview': result.response[:100] if result.response else 'No response'
        })
        
    except Exception as e:
        print(f"❌ AI Test Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Simple AI endpoint as fallback
@app.route('/api/ai/simple', methods=['POST'])
@handle_api_errors
def api_ai_simple():
    """Simple AI endpoint that works without complex dependencies."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
        
        message = data.get('message', '')
        user_id = data.get('user_id', 1)
        
        if not message:
            return create_error_response("Message is required", 400, 'MISSING_MESSAGE')
        
        # Use the minimal AI assistant directly
        from core.minimal_ai_assistant import MinimalAIEmailAssistant
        ai_assistant = MinimalAIEmailAssistant()
        
        # Generate a simple response
        response = ai_assistant.generate_chat_response(message)
        
        return create_success_response({
            'response': response.get('response', 'I received your message but had trouble generating a response.'),
            'suggested_actions': ['Try rephrasing your question'],
            'confidence': 0.8,
            'service_queries': []
        }, "Simple AI response generated")
        
    except Exception as e:
        print(f"❌ Simple AI Error: {e}")
        import traceback
        traceback.print_exc()
        return create_error_response(f"Simple AI error: {str(e)}", 500, "SIMPLE_AI_ERROR")

# Dashboard API endpoints
@app.route('/api/dashboard/timeseries', methods=['GET'])
@handle_api_errors
def api_dashboard_timeseries():
    """Get dashboard timeseries data for the last 14 days with change calculations"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        
        # Mock data for now - replace with actual database queries
        import random
        from datetime import datetime, timedelta
        
        # Generate mock timeseries data for the last 14 days
        timeseries = []
        base_date = datetime.now() - timedelta(days=13)
        
        for i in range(14):
            day = base_date + timedelta(days=i)
            timeseries.append({
                "day": day.strftime("%Y-%m-%d"),
                "leads": random.randint(3, 15),
                "emails": random.randint(8, 25),
                "revenue": random.randint(500, 2000)
            })
        
        # Split into current vs previous 7 days
        current = timeseries[-7:]
        previous = timeseries[:7]
        
        def calc_change(key):
            cur = sum(d[key] for d in current)
            prev = sum(d[key] for d in previous) if previous else 0
            if prev == 0: 
                return {"change_pct": None, "positive": True}
            change = ((cur - prev) / prev) * 100
            return {"change_pct": round(change, 1), "positive": change >= 0}
        
        return create_success_response({
            "timeseries": timeseries,
            "summary": {
                "leads": calc_change("leads"),
                "emails": calc_change("emails"),
                "revenue": calc_change("revenue")
            }
        })
    except Exception as e:
        logger.error(f"Dashboard timeseries error: {e}")
        return create_error_response(f"Failed to fetch dashboard data: {str(e)}", 500, 'DASHBOARD_TIMESERIES_ERROR')

@app.route('/api/dashboard/metrics', methods=['GET'])
@handle_api_errors
def api_dashboard_metrics():
    """Get current dashboard metrics summary"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        
        # Mock data for now - replace with actual database queries
        import random
        
        return create_success_response({
            "total_leads": random.randint(50, 200),
            "total_emails": random.randint(200, 500),
            "total_revenue": random.randint(10000, 50000),
            "today_leads": random.randint(2, 8),
            "today_emails": random.randint(5, 15)
        })
    except Exception as e:
        logger.error(f"Dashboard metrics error: {e}")
        return create_error_response(f"Failed to fetch dashboard metrics: {str(e)}", 500, 'DASHBOARD_METRICS_ERROR')

# Universal AI Assistant endpoints
@app.route('/api/ai/chat', methods=['POST'])
@handle_api_errors
def api_ai_chat():
    """Universal AI Assistant chat endpoint."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
        
        # Basic validation
        required_fields = ['message', 'user_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return create_error_response(f"{field} is required", 400, f'MISSING_{field.upper()}')
        
        print(f"🔍 AI Chat Debug: Processing message: {data.get('message', 'No message')}")
        print(f"🔍 AI Chat Debug: User ID: {data.get('user_id', 'No user_id')}")
        print(f"🔍 AI Chat Debug: Context: {data.get('context', {})}")
        
        result = universal_ai_assistant.process_query(
            user_message=data['message'],
            user_id=data['user_id'],
            context=data.get('context', {})
        )
        
        print(f"🔍 AI Chat Debug: Result success: {result.success}")
        print(f"🔍 AI Chat Debug: Response: {result.response[:100] if result.response else 'No response'}...")
        
        if result.success:
            return create_success_response({
                'response': result.response,
                'suggested_actions': result.suggested_actions,
                'confidence': result.confidence,
                'service_queries': [
                    {
                        'service': query.service,
                        'action': query.action,
                        'parameters': query.parameters
                    }
                    for query in result.service_queries
                ]
            }, "AI response generated")
        else:
            return create_error_response("Failed to process AI query", 500, "AI_PROCESSING_ERROR")
            
    except Exception as e:
        print(f"❌ AI Chat Error: {e}")
        import traceback
        traceback.print_exc()
        return create_error_response(f"AI processing error: {str(e)}", 500, "AI_PROCESSING_ERROR")

# Enhanced CRM Service endpoints
@app.route('/api/crm/leads', methods=['GET'])
@handle_api_errors
def api_get_leads():
    """Get leads with filtering and analytics."""
    user_id = request.args.get('user_id')
    stage = request.args.get('stage')
    time_period = request.args.get('time_period')
    company = request.args.get('company')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    filters = {}
    if stage:
        filters['stage'] = stage
    if time_period:
        filters['time_period'] = time_period
    if company:
        filters['company'] = company
    
    result = enhanced_crm_service.get_leads_summary(int(user_id), filters)
    
    if result['success']:
        return create_success_response(result['data'], "Leads retrieved successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/leads', methods=['POST'])
@handle_api_errors
def api_create_lead():
    """Create a new lead."""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
    
    user_id = data.pop('user_id')
    result = enhanced_crm_service.create_lead(user_id, data)
    
    if result['success']:
        return create_success_response(result['data'], "Lead created successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/leads/<int:lead_id>', methods=['PUT'])
@handle_api_errors
def api_update_lead(validated_data, lead_id):
    """Update lead information."""
    user_id = validated_data.pop('user_id')
    result = enhanced_crm_service.update_lead(lead_id, user_id, validated_data)
    
    if result['success']:
        return create_success_response(result['data'], "Lead updated successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/leads/<int:lead_id>/activities', methods=['POST'])
@handle_api_errors
def api_add_lead_activity(validated_data, lead_id):
    """Add activity to a lead."""
    user_id = validated_data.pop('user_id')
    result = enhanced_crm_service.add_lead_activity(
        lead_id, user_id, 
        data['activity_type'], 
        data['description'],
        data.get('metadata', {})
    )
    
    if result['success']:
        return create_success_response(result['data'], "Activity added successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/leads/<int:lead_id>/activities', methods=['GET'])
@handle_api_errors
def api_get_lead_activities(lead_id):
    """Get activities for a specific lead."""
    user_id = request.args.get('user_id')
    limit = int(request.args.get('limit', 50))
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = enhanced_crm_service.get_lead_activities(lead_id, int(user_id), limit)
    
    if result['success']:
        return create_success_response(result['data'], "Activities retrieved successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/pipeline', methods=['GET'])
@handle_api_errors
def api_get_lead_pipeline():
    """Get lead pipeline with stage distribution."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = enhanced_crm_service.get_lead_pipeline(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Pipeline retrieved successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/crm/sync-gmail', methods=['POST'])
@handle_api_errors
def api_sync_gmail_leads():
    """Sync leads from Gmail emails."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = enhanced_crm_service.sync_gmail_leads(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Gmail leads synced successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# Email Parser Service endpoints
@app.route('/api/email/parse', methods=['POST'])
@handle_api_errors
def api_parse_email(validated_data):
    """Parse email and extract structured data."""
    try:
        parsed_email = email_parser_service.parse_email(
            data['email_data'], 
            data['user_id']
        )
        
        return create_success_response({
            'parsed_email': {
                'id': parsed_email.id,
                'sender_email': parsed_email.sender_email,
                'sender_name': parsed_email.sender_name,
                'subject': parsed_email.subject,
                'extracted_data': parsed_email.extracted_data,
                'lead_potential': parsed_email.lead_potential,
                'action_required': parsed_email.action_required
            }
        }, "Email parsed successfully")
        
    except Exception as e:
        return create_error_response(str(e), 500, "EMAIL_PARSING_ERROR")

@app.route('/api/email/insights', methods=['GET'])
@handle_api_errors
def api_get_email_insights():
    """Get email insights and analytics."""
    user_id = request.args.get('user_id')
    time_period = request.args.get('time_period', 'today')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    insights = email_parser_service.get_email_insights(int(user_id), time_period)
    
    return create_success_response({
        'insights': [
            {
                'email_id': insight.email_id,
                'insight_type': insight.insight_type,
                'confidence': insight.confidence,
                'data': insight.data,
                'suggested_action': insight.suggested_action
            }
            for insight in insights
        ]
    }, "Email insights retrieved successfully")

@app.route('/api/email/classify-intent', methods=['POST'])
@handle_api_errors
def api_classify_email_intent(validated_data):
    """Classify email intent and suggest actions."""
    intent = email_parser_service.classify_email_intent(data['email_data'])
    
    return create_success_response(intent, "Email intent classified successfully")

@app.route('/api/email/extract-contacts', methods=['POST'])
@handle_api_errors
def api_extract_contacts(validated_data):
    """Extract contact information from email."""
    contacts = email_parser_service.extract_contacts_from_email(data['email_data'])
    
    return create_success_response({
        'contacts': contacts
    }, "Contacts extracted successfully")

# Automation Engine endpoints
@app.route('/api/automation/rules', methods=['GET'])
@handle_api_errors
def api_get_automation_rules():
    """Get automation rules for user."""
    user_id = request.args.get('user_id')
    status = request.args.get('status')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = automation_engine.get_automation_rules(int(user_id), status)
    
    if result['success']:
        return create_success_response(result['data'], "Automation rules retrieved successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/rules', methods=['POST'])
@handle_api_errors
def api_create_automation_rule(validated_data):
    """Create a new automation rule."""
    user_id = validated_data.pop('user_id')
    result = automation_engine.create_automation_rule(user_id, validated_data)
    
    if result['success']:
        return create_success_response(result['data'], "Automation rule created successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/rules/<int:rule_id>', methods=['PUT'])
@handle_api_errors
def api_update_automation_rule(validated_data, rule_id):
    """Update automation rule."""
    user_id = validated_data.pop('user_id')
    result = automation_engine.update_automation_rule(rule_id, user_id, validated_data)
    
    if result['success']:
        return create_success_response(result['data'], "Automation rule updated successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/suggestions', methods=['GET'])
@handle_api_errors
def api_get_automation_suggestions():
    """Get automation suggestions based on user patterns."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = automation_engine.get_automation_suggestions(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Automation suggestions retrieved successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/execute', methods=['POST'])
@handle_api_errors
def api_execute_automation(validated_data):
    """Execute automation rules based on trigger."""
    from core.automation_engine import TriggerType
    
    try:
        trigger_type = TriggerType(data['trigger_type'])
        result = automation_engine.execute_automation_rules(
            trigger_type, 
            data['trigger_data'], 
            data['user_id']
        )
        
        if result['success']:
            return create_success_response(result['data'], "Automation executed successfully")
        else:
            return create_error_response(result['error'], 400, result['error_code'])
            
    except ValueError:
        return create_error_response("Invalid trigger type", 400, "INVALID_TRIGGER_TYPE")

# Onboarding Orchestration endpoints
@app.route('/api/onboarding/start', methods=['POST'])
@handle_api_errors
def api_start_onboarding():
    """Start the complete onboarding process."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = onboarding_orchestrator.start_onboarding_job(int(user_id))
    
    if result['success']:
        return create_success_response({
            'job_id': result['job_id']
        }, "Onboarding job started successfully")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/onboarding/status', methods=['GET'])
@handle_api_errors
def api_get_onboarding_status():
    """Get onboarding job status."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    job = onboarding_orchestrator.get_job_status(int(user_id))
    
    if job:
        return create_success_response({
            'status': job.status,
            'current_step': job.current_step,
            'progress': job.progress,
            'started_at': job.started_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message
        }, "Onboarding status retrieved")
    else:
        return create_success_response({
            'status': 'not_started',
            'current_step': None,
            'progress': 0,
            'started_at': None,
            'completed_at': None,
            'error_message': None
        }, "No onboarding job found")

@app.route('/api/onboarding/summary', methods=['GET'])
@handle_api_errors
def api_get_onboarding_summary():
    """Get complete onboarding summary."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = onboarding_orchestrator.get_onboarding_summary(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Onboarding summary retrieved")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# Automation Safety Control endpoints
@app.route('/api/automation/kill-switch', methods=['POST'])
@handle_api_errors
def api_toggle_kill_switch():
    """Toggle global automation kill-switch."""
    data = request.get_json()
    enabled = data.get('enabled', False)
    
    result = automation_safety_manager.toggle_global_kill_switch(enabled)
    
    if result['success']:
        return create_success_response({
            'kill_switch_enabled': result['kill_switch_enabled']
        }, result['message'])
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/safety-status', methods=['GET'])
@handle_api_errors
def api_get_safety_status():
    """Get automation safety status."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = automation_safety_manager.get_safety_status(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Safety status retrieved")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/automation/check-limits', methods=['POST'])
@handle_api_errors
def api_check_automation_limits():
    """Check if automation action is within rate limits."""
    data = request.get_json()
    user_id = data.get('user_id')
    contact_email = data.get('contact_email')
    action_type = data.get('action_type')
    
    if not all([user_id, contact_email, action_type]):
        return create_error_response("user_id, contact_email, and action_type are required", 400, "MISSING_PARAMETERS")
    
    # Check automation safety limits
    safety_result = automation_safety_manager.check_rate_limits(int(user_id), action_type, contact_email)
    
    # Check general rate limits
    rate_result = rate_limiter.check_automation_rate_limit(int(user_id), contact_email, action_type)
    
    # Combine results
    if not safety_result['allowed'] or not rate_result['allowed']:
        return create_success_response({
            'allowed': False,
            'reason': safety_result.get('reason') if not safety_result['allowed'] else rate_result.get('reason'),
            'message': safety_result.get('message') if not safety_result['allowed'] else rate_result.get('message'),
            'retry_after': rate_result.get('retry_after')
        }, "Action blocked by rate limits")
    
    return create_success_response({
        'allowed': True,
        'reason': 'within_limits',
        'message': 'Action is within rate limits'
    }, "Action allowed")

# Rate Limiting endpoints
@app.route('/api/rate-limits/check', methods=['POST'])
@handle_api_errors
def api_check_rate_limits():
    """Check API rate limits."""
    data = request.get_json()
    user_id = data.get('user_id')
    endpoint = data.get('endpoint', 'unknown')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = rate_limiter.check_api_rate_limit(int(user_id), endpoint)
    
    if result['allowed']:
        return create_success_response(result, "Request allowed")
    else:
        return create_error_response(
            result.get('message', 'Rate limit exceeded'), 
            429, 
            result.get('reason', 'RATE_LIMIT_EXCEEDED'),
            headers={'Retry-After': str(result.get('retry_after', 60))}
        )

@app.route('/api/rate-limits/status', methods=['GET'])
@handle_api_errors
def api_get_rate_limit_status():
    """Get rate limit status for user."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = rate_limiter.get_rate_limit_status(int(user_id))
    
    if result['success']:
        return create_success_response(result['data'], "Rate limit status retrieved")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

# OAuth Token Management endpoints
@app.route('/api/oauth/token-status', methods=['GET'])
@handle_api_errors
def api_get_token_status():
    """Get OAuth token status."""
    user_id = request.args.get('user_id')
    service = request.args.get('service', 'gmail')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = oauth_token_manager.get_token_status(int(user_id), service)
    
    if result['success']:
        return create_success_response(result['data'], "Token status retrieved")
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/oauth/refresh-token', methods=['POST'])
@handle_api_errors
def api_refresh_token():
    """Refresh OAuth token."""
    data = request.get_json()
    user_id = data.get('user_id')
    service = data.get('service', 'gmail')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = oauth_token_manager.refresh_token(int(user_id), service)
    
    if result['success']:
        return create_success_response({
            'expires_in': result.get('expires_in')
        }, result['message'])
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/oauth/revoke-tokens', methods=['POST'])
@handle_api_errors
def api_revoke_tokens():
    """Revoke OAuth tokens."""
    data = request.get_json()
    user_id = data.get('user_id')
    service = data.get('service', 'gmail')
    
    if not user_id:
        return create_error_response("User ID is required", 400, "MISSING_USER_ID")
    
    result = oauth_token_manager.revoke_tokens(int(user_id), service)
    
    if result['success']:
        return create_success_response({}, result['message'])
    else:
        return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """User logout endpoint."""
    try:
        session_id = session.get('session_id')
        if session_id:
            security_manager.revoke_session(session_id)
            session.clear()
            
            log_security_event(
                event_type="user_logout",
                severity="info",
                details={"session_id": session_id}
            )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/status')
def api_auth_status():
    """Check authentication status."""
    try:
        session_id = session.get('session_id')
        if session_id:
            session_obj = security_manager.validate_session(session_id)
            if session_obj:
                user = security_manager.get_user_by_id(session_obj.user_id)
                if user:
                    return jsonify({
                        'authenticated': True,
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'name': user.name,
                            'role': user.role.value
                        }
                    })
        
        return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users')
def api_admin_users():
    """Admin endpoint to list users."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        session_obj = security_manager.validate_session(session_id)
        if not session_obj:
            return jsonify({'error': 'Invalid session'}), 401
        
        user = security_manager.get_user_by_id(session_obj.user_id)
        if not user or not security_manager.check_permission(user, Permission.MANAGE_USERS):
            return jsonify({'error': 'Permission denied'}), 403
        
        users = security_manager.list_users()
        return jsonify({
            'users': [
                {
                    'id': u.id,
                    'email': u.email,
                    'name': u.name,
                    'role': u.role.value,
                    'is_active': u.is_active,
                    'created_at': u.created_at,
                    'last_login': u.last_login
                }
                for u in users
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/security-stats')
def api_admin_security_stats():
    """Admin endpoint for security statistics."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        session_obj = security_manager.validate_session(session_id)
        if not session_obj:
            return jsonify({'error': 'Invalid session'}), 401
        
        user = security_manager.get_user_by_id(session_obj.user_id)
        if not user or not security_manager.check_permission(user, Permission.SYSTEM_CONFIG):
            return jsonify({'error': 'Permission denied'}), 403
        
        stats = security_manager.get_security_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Removed root route - frontend now handles root URL with React landing page

@app.route('/api/health-old')
def api_health_old():
    """Comprehensive health check endpoint for system monitoring."""
    try:
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'version': '1.0.0',
            'uptime': 'running',
            'checks': {
                'gmail_auth': {'status': 'unknown', 'details': ''},
                'vector_db': {'status': 'unknown', 'details': ''},
                'crm_leads': {'status': 'unknown', 'details': ''},
                'openai_key': {'status': 'unknown', 'details': ''},
                'services': {'status': 'unknown', 'details': ''},
                'feature_flags': {'status': 'unknown', 'details': ''}
            },
            'metrics': {
                'total_services': len(services),
                'initialized_services': 0,
                'authenticated_services': 0,
                'enabled_features': 0
            }
        }
        
        # Check Gmail Authentication
        try:
            if services['auth'] and services['auth'].is_authenticated():
                health_status['checks']['gmail_auth'] = {
                    'status': 'healthy',
                    'details': 'Gmail OAuth authenticated successfully'
                }
            else:
                health_status['checks']['gmail_auth'] = {
                    'status': 'unhealthy',
                    'details': 'Gmail authentication required'
                }
        except Exception as e:
            health_status['checks']['gmail_auth'] = {
                'status': 'error',
                'details': f'Gmail auth check failed: {str(e)}'
            }
        
        # Check Vector DB
        try:
            if services['vector_search']:
                stats = services['vector_search'].get_stats()
                if stats.get('document_count', 0) > 0:
                    health_status['checks']['vector_db'] = {
                        'status': 'healthy',
                        'details': f'Vector DB loaded with {stats["document_count"]} documents'
                    }
                else:
                    health_status['checks']['vector_db'] = {
                        'status': 'warning',
                        'details': 'Vector DB initialized but no documents loaded'
                    }
            else:
                health_status['checks']['vector_db'] = {
                    'status': 'unhealthy',
                    'details': 'Vector search service not initialized'
                }
        except Exception as e:
            health_status['checks']['vector_db'] = {
                'status': 'error',
                'details': f'Vector DB check failed: {str(e)}'
            }
        
        # Check CRM Leads
        try:
            if services['crm']:
                stats = services['crm'].get_lead_stats()
                lead_count = stats.get('total_leads', 0)
                if lead_count > 0:
                    health_status['checks']['crm_leads'] = {
                        'status': 'healthy',
                        'details': f'CRM has {lead_count} leads available'
                    }
                else:
                    health_status['checks']['crm_leads'] = {
                        'status': 'warning',
                        'details': 'CRM initialized but no leads available'
                    }
            else:
                health_status['checks']['crm_leads'] = {
                    'status': 'unhealthy',
                    'details': 'CRM service not initialized'
                }
        except Exception as e:
            health_status['checks']['crm_leads'] = {
                'status': 'error',
                'details': f'CRM check failed: {str(e)}'
            }
        
        # Check OpenAI Key
        try:
            if services['ai_assistant']:
                # Try to get usage stats to verify API key
                stats = services['ai_assistant'].get_usage_stats()
                health_status['checks']['openai_key'] = {
                    'status': 'healthy',
                    'details': f'OpenAI API key valid (calls: {stats.get("total_calls", 0)})'
                }
            else:
                health_status['checks']['openai_key'] = {
                    'status': 'unhealthy',
                    'details': 'AI Assistant service not initialized'
                }
        except Exception as e:
            health_status['checks']['openai_key'] = {
                'status': 'error',
                'details': f'OpenAI key check failed: {str(e)}'
            }
        
        # Check All Services
        initialized_count = 0
        authenticated_count = 0
        
        for service_name, service in services.items():
            if service:
                initialized_count += 1
                if hasattr(service, 'is_authenticated') and service.is_authenticated():
                    authenticated_count += 1
        
        health_status['metrics']['initialized_services'] = initialized_count
        health_status['metrics']['authenticated_services'] = authenticated_count
        
        if initialized_count == len(services):
            health_status['checks']['services'] = {
                'status': 'healthy',
                'details': f'All {initialized_count} services initialized'
            }
        else:
            health_status['checks']['services'] = {
                'status': 'warning',
                'details': f'{initialized_count}/{len(services)} services initialized'
            }
        
        # Check Feature Flags
        try:
            if services['feature_flags']:
                flags_status = services['feature_flags'].get_status_report()
                enabled_count = sum(1 for flag in flags_status.get('flags', {}).values() if flag.get('enabled', False))
                health_status['metrics']['enabled_features'] = enabled_count
                
                health_status['checks']['feature_flags'] = {
                    'status': 'healthy',
                    'details': f'Feature flags system active ({enabled_count} enabled)'
                }
            else:
                health_status['checks']['feature_flags'] = {
                    'status': 'unhealthy',
                    'details': 'Feature flags service not initialized'
                }
        except Exception as e:
            health_status['checks']['feature_flags'] = {
                'status': 'error',
                'details': f'Feature flags check failed: {str(e)}'
            }
        
        # Determine overall health status
        unhealthy_checks = [check for check in health_status['checks'].values() 
                          if check['status'] in ['unhealthy', 'error']]
        
        if unhealthy_checks:
            health_status['status'] = 'unhealthy'
        elif any(check['status'] == 'warning' for check in health_status['checks'].values()):
            health_status['status'] = 'degraded'
        
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """Legacy status endpoint - redirects to health."""
    return redirect(url_for('api_health'))

@app.route('/api/test/email-parser', methods=['POST'])
def api_test_email_parser():
    """Test email parser with sample data."""
    try:
        data = request.get_json()
        
        # Create sample email if none provided
        if not data:
            data = {
                "id": "test123",
                "threadId": "thread123",
                "snippet": "Test email snippet",
                "labelIds": ["UNREAD", "INBOX"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "test@example.com"},
                        {"name": "To", "value": "info@fikirisolutions.com"},
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
                    ],
                    "mimeType": "text/plain",
                    "body": {
                        "data": "SGVsbG8gd29ybGQ="  # "Hello world" in base64
                    }
                }
            }
        
        # Parse email
        parsed = services['parser'].parse_message(data)
        
        return jsonify({
            'success': True,
            'parsed_email': parsed,
            'sender': services['parser'].get_sender(parsed),
            'subject': services['parser'].get_subject(parsed),
            'body': services['parser'].get_body_text(parsed),
            'is_unread': services['parser'].is_unread(parsed)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/email-actions', methods=['POST'])
def api_test_email_actions():
    """Test email actions."""
    try:
        data = request.get_json()
        
        # Create sample parsed email
        sample_email = {
            "message_id": "test123",
            "headers": {
                "from": data.get('sender', 'test@example.com'),
                "subject": data.get('subject', 'Test Subject')
            },
            "labels": ["UNREAD"]
        }
        
        # Test different actions
        results = {}
        actions = ['auto_reply', 'mark_read', 'add_label']
        
        for action in actions:
            result = services['actions'].process_email(sample_email, action)
            results[action] = result
        
        # Get stats
        stats = services['actions'].get_stats()
        
        return jsonify({
            'success': True,
            'results': results,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crm/leads', methods=['POST'])
@handle_api_errors
def api_add_lead():
    """Add a new lead to CRM with comprehensive validation."""
    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')
    
    # Basic validation
    required_fields = ['user_id', 'email', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')
    
    if not services['crm']:
        return create_error_response("CRM service not available", 503, "SERVICE_UNAVAILABLE")
    
    # Create lead using validated data
    lead = services['crm'].add_lead(
        email=data['email'],
        name=data['name'],
        source=data.get('source', 'web')
    )
    
    # Add additional fields if provided
    if data.get('phone'):
        lead.phone = data['phone']
    if data.get('company'):
        lead.company = data['company']
    if data.get('notes'):
        lead.notes.append(data['notes'])
    if data.get('status'):
        lead.stage = data['status']
    
    lead_data = lead.to_dict()
    
    # Track business analytics
    business_analytics.track_event('lead_created', {
        'lead_id': lead.id,
        'source': data.get('source', 'web'),
        'company': data.get('company'),
        'stage': data.get('status', 'new')
    })
    
    return create_success_response({
        'lead_id': lead.id,
        'lead': lead_data
    }, "Lead added successfully")

@app.route('/api/test/crm', methods=['POST'])
def api_test_crm():
    """Test CRM service."""
    try:
        data = request.get_json()
        
        # Add test lead
        email = data.get('email', 'test@example.com')
        name = data.get('name', 'Test User')
        
        lead = services['crm'].add_lead(email, name, 'web_test')
        
        # Update lead
        services['crm'].update_lead_stage(lead.id, 'qualified')
        services['crm'].add_note(lead.id, 'Test note from web interface')
        services['crm'].add_tag(lead.id, 'web-test')
        services['crm'].record_contact(lead.id, 'web')
        
        # Get stats
        stats = services['crm'].get_lead_stats()
        
        return jsonify({
            'success': True,
            'lead': lead.to_dict(),
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/ai-assistant', methods=['POST'])
def api_test_ai_assistant():
    """Test AI assistant."""
    try:
        data = request.get_json()
        
        email_content = data.get('content', 'Hi, I need help with your services.')
        sender_name = data.get('sender', 'Test User')
        subject = data.get('subject', 'Test Subject')
        
        # Test classification
        classification = services['ai_assistant'].classify_email_intent(email_content, subject)
        
        # Test response generation
        response = services['ai_assistant'].generate_response(
            email_content, sender_name, subject, classification['intent']
        )
        
        # Test contact extraction
        contact_info = services['ai_assistant'].extract_contact_info(email_content)
        
        # Get usage stats
        stats = services['ai_assistant'].get_usage_stats()
        
        return jsonify({
            'success': True,
            'classification': classification,
            'response': response,
            'contact_info': contact_info,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/openai-key', methods=['GET'])
def test_openai_key():
    """Test OpenAI API key status."""
    try:
        if not services['ai_assistant'].is_enabled():
            return jsonify({
                "status": "error",
                "message": "AI Assistant not enabled",
                "api_key_configured": False
            })
        
        # Test the API key with a simple request
        test_response = services['ai_assistant']._generate_ai_response("Test message")
        
        return jsonify({
            "status": "success",
            "message": "OpenAI API key is working",
            "api_key_configured": True,
            "test_response": test_response[:100] + "..." if len(test_response) > 100 else test_response
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"OpenAI API key test failed: {str(e)}",
            "api_key_configured": False,
            "error_details": str(e)
        })

@app.route('/api/test/ml-scoring', methods=['POST'])
def api_test_ml_scoring():
    """Test ML scoring service."""
    try:
        data = request.get_json()
        
        email_data = {
            'content': data.get('content', 'I need urgent pricing for your premium services.'),
            'subject': data.get('subject', 'Urgent: Pricing Request'),
            'timestamp': datetime.now().isoformat()
        }
        
        lead_data = {
            'email': data.get('email', 'test@example.com'),
            'contact_count': data.get('contact_count', 1)
        }
        
        # Calculate score
        score_result = services['ml_scoring'].calculate_lead_score(email_data, lead_data)
        
        # Get stats
        stats = services['ml_scoring'].get_scoring_stats()
        
        return jsonify({
            'success': True,
            'score_result': score_result,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/vector-search', methods=['POST'])
def api_test_vector_search():
    """Test vector search service."""
    try:
        data = request.get_json()
        
        # Add test documents
        documents = [
            {
                'text': 'Fikiri Solutions provides Gmail automation and lead management services.',
                'metadata': {'category': 'services', 'type': 'description'}
            },
            {
                'text': 'Our AI-powered email assistant can automatically respond to customer inquiries.',
                'metadata': {'category': 'features', 'type': 'ai_assistant'}
            },
            {
                'text': 'Contact us at info@fikirisolutions.com for pricing information.',
                'metadata': {'category': 'contact', 'type': 'pricing'}
            }
        ]
        
        # Add documents
        doc_ids = []
        for doc in documents:
            doc_id = services['vector_search'].add_document(doc['text'], doc['metadata'])
            doc_ids.append(doc_id)
        
        # Test search
        query = data.get('query', 'How can I get pricing for your services?')
        results = services['vector_search'].search_similar(query, top_k=3)
        
        # Test RAG context
        context = services['vector_search'].get_context_for_rag(query)
        
        # Get stats
        stats = services['vector_search'].get_stats()
        
        return jsonify({
            'success': True,
            'doc_ids': doc_ids,
            'search_results': results,
            'context': context,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feature-flags')
def api_feature_flags():
    """Get feature flags status."""
    try:
        if services['feature_flags']:
            status = services['feature_flags'].get_status_report()
            return jsonify(status)
        else:
            return jsonify({'error': 'Feature flags not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feature-flags/<feature_name>', methods=['POST'])
def api_toggle_feature_flag(feature_name):
    """Toggle a feature flag."""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        if services['feature_flags']:
            if enabled:
                services['feature_flags'].enable_feature(feature_name)
            else:
                services['feature_flags'].disable_feature(feature_name)
            
            return jsonify({'success': True, 'feature': feature_name, 'enabled': enabled})
        else:
            return jsonify({'error': 'Feature flags not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket Event Handlers for Real-Time Updates
# SocketIO functionality disabled - removed heavy dependencies

# SocketIO disconnect handler removed

# SocketIO dashboard subscription handler removed

# SocketIO metrics update handler removed

# SocketIO services update handler removed
    try:
        service_list = []
        
        # Gmail Service
        gmail_status = 'active' if services['gmail'] and services['gmail'].is_authenticated() else 'inactive'
        service_list.append({
            'id': 'gmail',
            'name': 'Gmail Integration',
            'status': gmail_status,
            'description': 'Connect and manage Gmail accounts for email automation'
        })
        
        # AI Assistant Service
        ai_status = 'active' if services['ai_assistant'] and services['ai_assistant'].is_enabled() else 'inactive'
        service_list.append({
            'id': 'ai_assistant',
            'name': 'AI Assistant',
            'status': ai_status,
            'description': 'AI-powered email responses and lead analysis'
        })
        
        # CRM Service
        crm_status = 'active' if services['crm'] else 'inactive'
        service_list.append({
            'id': 'crm',
            'name': 'CRM System',
            'status': crm_status,
            'description': 'Customer relationship management and lead tracking'
        })
        
        emit('services_update', {
            'services': service_list,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        emit('error', {'message': f'Failed to update services: {str(e)}'})

# SocketIO broadcast function removed - real-time updates disabled

@app.route('/api/performance/summary', methods=['GET'])
def api_performance_summary():
    """Get comprehensive performance summary."""
    try:
        summary = performance_monitor.get_performance_summary()
        return create_success_response(summary, "Performance summary retrieved successfully")
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return create_error_response("Failed to retrieve performance summary", 500, "PERFORMANCE_ERROR")

@app.route('/api/performance/endpoint/<endpoint>', methods=['GET'])
def api_endpoint_performance(endpoint):
    """Get performance metrics for a specific endpoint."""
    try:
        metrics = performance_monitor.get_endpoint_performance(endpoint)
        return create_success_response(metrics, f"Performance metrics for {endpoint}")
    except Exception as e:
        logger.error(f"Error getting endpoint performance: {e}")
        return create_error_response("Failed to retrieve endpoint performance", 500, "PERFORMANCE_ERROR")

@app.route('/api/performance/system-health', methods=['GET'])
def api_system_health():
    """Get current system health status."""
    try:
        health = performance_monitor.get_system_health()
        return create_success_response(health, "System health retrieved successfully")
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return create_error_response("Failed to retrieve system health", 500, "PERFORMANCE_ERROR")

@app.route('/api/performance/export', methods=['GET'])
def api_export_metrics():
    """Export performance metrics for analysis."""
    try:
        hours = request.args.get('hours', 24, type=int)
        metrics = performance_monitor.export_metrics(hours)
        return create_success_response(metrics, f"Performance metrics exported for last {hours} hours")
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        return create_error_response("Failed to export metrics", 500, "PERFORMANCE_ERROR")

@app.route('/api/async/bulk-process', methods=['POST'])
@async_operation("bulk_process")
def api_bulk_process():
    """Start bulk processing operation asynchronously."""
    def bulk_process_task():
        """Simulate bulk processing task"""
        time.sleep(5)  # Simulate processing time
        return {
            'processed_items': 1000,
            'success_count': 950,
            'error_count': 50,
            'processing_time': 5.0
        }
    
    # This will return immediately with a task ID
    # The actual processing happens in the background
    return bulk_process_task()

@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_get_task_status(task_id: str):
    """Get the status of an async task."""
    try:
        status = async_manager.get_task_status(task_id)
        return create_success_response(status, f"Task {task_id} status")
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return create_error_response("Failed to get task status", 500, "TASK_ERROR")

@app.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    """Clear application cache."""
    try:
        success = cache_manager.clear()
        return create_success_response(
            {'cleared': success}, 
            "Cache cleared successfully" if success else "Failed to clear cache"
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return create_error_response("Failed to clear cache", 500, "CACHE_ERROR")

@app.route('/api/database/optimize', methods=['POST'])
def api_optimize_database():
    """Run database optimization tasks."""
    try:
        results = db_optimizer.optimize_database()
        return create_success_response(results, "Database optimization completed")
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return create_error_response("Failed to optimize database", 500, "DATABASE_ERROR")

@app.route('/api/database/stats', methods=['GET'])
def api_database_stats():
    """Get database statistics."""
    try:
        stats = db_optimizer.get_database_stats()
        return create_success_response(stats, "Database statistics retrieved")
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return create_error_response("Failed to get database stats", 500, "DATABASE_ERROR")

@app.route('/api/database/query-performance', methods=['GET'])
def api_query_performance():
    """Get query performance analysis."""
    try:
        hours = request.args.get('hours', 24, type=int)
        performance = db_optimizer.get_query_performance(hours)
        return create_success_response(performance, f"Query performance for last {hours} hours")
    except Exception as e:
        logger.error(f"Error getting query performance: {e}")
        return create_error_response("Failed to get query performance", 500, "DATABASE_ERROR")

@app.route('/api/database/migrations', methods=['GET'])
def api_migration_status():
    """Get migration status."""
    try:
        status = migration_manager.get_migration_status()
        return create_success_response(status, "Migration status retrieved")
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        return create_error_response("Failed to get migration status", 500, "DATABASE_ERROR")

@app.route('/api/database/migrations/run', methods=['POST'])
def api_run_migrations():
    """Run all pending migrations."""
    try:
        applied_migrations = migration_manager.run_all_pending_migrations()
        return create_success_response(
            {'applied_migrations': applied_migrations},
            f"Applied {len(applied_migrations)} migrations"
        )
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return create_error_response("Failed to run migrations", 500, "DATABASE_ERROR")

@app.route('/api/monitoring/alerts', methods=['GET'])
def api_get_alerts():
    """Get monitoring alerts."""
    try:
        severity = request.args.get('severity')
        resolved = request.args.get('resolved', type=bool)
        
        alerts = monitoring_system.get_alerts(severity, resolved)
        
        return create_success_response({
            'alerts': [
                {
                    'id': alert.id,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'source': alert.source,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                }
                for alert in alerts
            ],
            'total_count': len(alerts)
        }, "Alerts retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return create_error_response("Failed to get alerts", 500, "MONITORING_ERROR")

@app.route('/api/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
def api_resolve_alert(alert_id: str):
    """Resolve a monitoring alert."""
    try:
        monitoring_system.resolve_alert(alert_id)
        return create_success_response(
            {'alert_id': alert_id},
            "Alert resolved successfully"
        )
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return create_error_response("Failed to resolve alert", 500, "MONITORING_ERROR")

@app.route('/api/monitoring/metrics', methods=['GET'])
def api_get_metrics():
    """Get monitoring metrics summary."""
    try:
        hours = request.args.get('hours', 24, type=int)
        metrics = monitoring_system.get_metrics_summary(hours)
        
        return create_success_response(metrics, f"Metrics for last {hours} hours")
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return create_error_response("Failed to get metrics", 500, "MONITORING_ERROR")

@app.route('/api/backup/status', methods=['GET'])
def api_backup_status():
    """Get backup status and history."""
    try:
        status = backup_manager.get_backup_status()
        return create_success_response(status, "Backup status retrieved")
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        return create_error_response("Failed to get backup status", 500, "BACKUP_ERROR")

@app.route('/api/backup/create', methods=['POST'])
def api_create_backup():
    """Create a backup."""
    try:
        data = request.get_json()
        backup_type = data.get('type', 'database')
        
        result = backup_manager.create_backup(backup_type)
        
        if 'error' in result:
            return create_error_response(result['error'], 400, "BACKUP_ERROR")
        
        return create_success_response(result, "Backup created successfully")
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return create_error_response("Failed to create backup", 500, "BACKUP_ERROR")

@app.route('/api/backup/restore', methods=['POST'])
def api_restore_backup():
    """Restore from a backup."""
    try:
        data = request.get_json()
        backup_name = data.get('backup_name')
        destination = data.get('destination')
        
        if not backup_name or not destination:
            return create_error_response("Backup name and destination required", 400, "BACKUP_ERROR")
        
        result = backup_manager.restore_backup(backup_name, destination)
        
        if 'error' in result:
            return create_error_response(result['error'], 400, "BACKUP_ERROR")
        
        return create_success_response(result, "Backup restored successfully")
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        return create_error_response("Failed to restore backup", 500, "BACKUP_ERROR")

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for deployment monitoring."""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {}
        }
        
        # Check each service
        service_checks = {
            'config': lambda: services['config'] is not None,
            'auth': lambda: services['auth'] is not None,
            'parser': lambda: services['parser'] is not None,
            'gmail': lambda: services['gmail'] is not None,
            'actions': lambda: services['actions'] is not None,
            'crm': lambda: services['crm'] is not None,
            'ai_assistant': lambda: services['ai_assistant'] is not None,
            'ml_scoring': lambda: services['ml_scoring'] is not None,
            'vector_search': lambda: services['vector_search'] is not None,
            'feature_flags': lambda: services['feature_flags'] is not None
        }
        
        # Service-specific status checks
        service_status_checks = {
            'auth': lambda: {
                'authenticated': services['auth'].check_token_file(verbose=False) if services['auth'] else False,
                'enabled': True
            },
            'ai_assistant': lambda: {
                'enabled': services['ai_assistant'].is_enabled() if services['ai_assistant'] else False
            },
            'gmail': lambda: {
                'authenticated': services['gmail'].is_authenticated() if services['gmail'] else False,
                'enabled': True
            }
        }
        
        all_healthy = True
        for service_name, check_func in service_checks.items():
            try:
                is_healthy = check_func()
                
                # Base status
                service_status = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'available': is_healthy,
                    'initialized': is_healthy
                }
                
                # Add service-specific status if available
                if service_name in service_status_checks:
                    try:
                        specific_status = service_status_checks[service_name]()
                        service_status.update(specific_status)
                    except Exception as e:
                        print(f"Warning: Could not get specific status for {service_name}: {e}")
                
                health_status['services'][service_name] = service_status
                
                if not is_healthy:
                    all_healthy = False
            except Exception as e:
                health_status['services'][service_name] = {
                    'status': 'error',
                    'error': str(e),
                    'available': False,
                    'initialized': False
                }
                all_healthy = False
        
        # Overall status
        if not all_healthy:
            health_status['status'] = 'degraded'
        
        status_code = 200 if all_healthy else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

# Email Service Integration Routes
@app.route('/api/auth/microsoft/connect', methods=['POST'])
def microsoft_connect():
    """Initiate Microsoft Graph OAuth flow"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'})
        
        # Import our Microsoft Graph service
        from core.microsoft_graph import microsoft_graph_service
        
        if not microsoft_graph_service.is_configured():
            return jsonify({'success': False, 'error': 'Microsoft Graph not configured'})
        
        # Generate auth URL with user state
        auth_url = microsoft_graph_service.get_auth_url()
        if auth_url:
            # Add state parameter to track user
            auth_url += f"&state=user_{user_id}"
        
        return jsonify({
            'success': True,
            'auth_url': auth_url
        })
        
    except Exception as e:
        print(f"❌ Microsoft connect error: {e}")
        return jsonify({'success': False, 'error': 'Failed to initiate Microsoft connection'})

@app.route('/api/auth/microsoft/callback', methods=['GET'])
def microsoft_callback():
    """Handle Microsoft Graph OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code or not state:
            return redirect('/onboarding-flow/2?error=microsoft_auth_failed')
        
        user_id = state.replace('user_', '')
        
        # Import our Microsoft Graph service
        from core.microsoft_graph import microsoft_graph_service
        
        if not microsoft_graph_service.is_configured():
            return redirect('/onboarding-flow/2?error=microsoft_provider_unavailable')
        
        # Exchange code for token
        auth_result = microsoft_graph_service.authenticate_user(code)
        if auth_result['success']:
            # Store tokens in session or database for the user
            session[f'microsoft_tokens_{user_id}'] = {
                'access_token': auth_result['access_token'],
                'refresh_token': auth_result['refresh_token'],
                'expires_in': auth_result['expires_in']
            }
            
            return redirect(f'/onboarding-flow/3?microsoft_connected=true')
        else:
            return redirect('/onboarding-flow/2?error=microsoft_token_exchange_failed')
            
    except Exception as e:
        print(f"❌ Microsoft callback error: {e}")
        return redirect('/onboarding-flow/2?error=microsoft_callback_error')

# Microsoft Graph API Endpoints
@app.route('/api/microsoft/user/profile', methods=['GET'])
@handle_api_errors
def microsoft_user_profile():
    """Get Microsoft user profile"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return create_error_response("User ID required", 400, 'MISSING_USER_ID')
        
        # Get tokens from session
        tokens = session.get(f'microsoft_tokens_{user_id}')
        if not tokens:
            return create_error_response("Microsoft not connected", 401, 'NOT_CONNECTED')
        
        from core.microsoft_graph import microsoft_graph_service
        
        # Set tokens in the service
        microsoft_graph_service.client.access_token = tokens['access_token']
        microsoft_graph_service.client.refresh_token = tokens['refresh_token']
        
        result = microsoft_graph_service.get_user_info()
        if result['success']:
            return create_success_response(result['user'], "User profile retrieved")
        else:
            return create_error_response(result['error'], 400, 'PROFILE_ERROR')
            
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/microsoft/emails', methods=['GET'])
@handle_api_errors
def microsoft_emails():
    """Get Microsoft emails"""
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 50))
        
        if not user_id:
            return create_error_response("User ID required", 400, 'MISSING_USER_ID')
        
        # Get tokens from session
        tokens = session.get(f'microsoft_tokens_{user_id}')
        if not tokens:
            return create_error_response("Microsoft not connected", 401, 'NOT_CONNECTED')
        
        from core.microsoft_graph import microsoft_graph_service
        
        # Set tokens in the service
        microsoft_graph_service.client.access_token = tokens['access_token']
        microsoft_graph_service.client.refresh_token = tokens['refresh_token']
        
        result = microsoft_graph_service.get_user_emails(limit=limit)
        if result['success']:
            return create_success_response(result['emails'], "Emails retrieved")
        else:
            return create_error_response(result['error'], 400, 'EMAIL_ERROR')
            
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/microsoft/send-email', methods=['POST'])
@handle_api_errors
def microsoft_send_email():
    """Send email via Microsoft Graph"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not all([user_id, to, subject, body]):
            return create_error_response("Missing required fields", 400, 'MISSING_FIELDS')
        
        # Get tokens from session
        tokens = session.get(f'microsoft_tokens_{user_id}')
        if not tokens:
            return create_error_response("Microsoft not connected", 401, 'NOT_CONNECTED')
        
        from core.microsoft_graph import microsoft_graph_service
        
        # Set tokens in the service
        microsoft_graph_service.client.access_token = tokens['access_token']
        microsoft_graph_service.client.refresh_token = tokens['refresh_token']
        
        result = microsoft_graph_service.send_user_email(to, subject, body)
        if result['success']:
            return create_success_response({}, "Email sent successfully")
        else:
            return create_error_response(result['error'], 400, 'SEND_ERROR')
            
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/microsoft/calendar', methods=['GET'])
@handle_api_errors
def microsoft_calendar():
    """Get Microsoft calendar events"""
    try:
        user_id = request.args.get('user_id')
        days_ahead = int(request.args.get('days_ahead', 7))
        
        if not user_id:
            return create_error_response("User ID required", 400, 'MISSING_USER_ID')
        
        # Get tokens from session
        tokens = session.get(f'microsoft_tokens_{user_id}')
        if not tokens:
            return create_error_response("Microsoft not connected", 401, 'NOT_CONNECTED')
        
        from core.microsoft_graph import microsoft_graph_service
        
        # Set tokens in the service
        microsoft_graph_service.client.access_token = tokens['access_token']
        microsoft_graph_service.client.refresh_token = tokens['refresh_token']
        
        result = microsoft_graph_service.get_user_calendar(days_ahead=days_ahead)
        if result['success']:
            return create_success_response(result['data'], "Calendar events retrieved")
        else:
            return create_error_response(result['error'], 400, 'CALENDAR_ERROR')
            
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/microsoft/create-event', methods=['POST'])
@handle_api_errors
def microsoft_create_event():
    """Create Microsoft calendar event"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        subject = data.get('subject')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        attendees = data.get('attendees', [])
        body = data.get('body')
        
        if not all([user_id, subject, start_time, end_time]):
            return create_error_response("Missing required fields", 400, 'MISSING_FIELDS')
        
        # Get tokens from session
        tokens = session.get(f'microsoft_tokens_{user_id}')
        if not tokens:
            return create_error_response("Microsoft not connected", 401, 'NOT_CONNECTED')
        
        from core.microsoft_graph import microsoft_graph_service
        
        # Set tokens in the service
        microsoft_graph_service.client.access_token = tokens['access_token']
        microsoft_graph_service.client.refresh_token = tokens['refresh_token']
        
        result = microsoft_graph_service.create_calendar_event(
            subject, start_time, end_time, attendees, body
        )
        if result['success']:
            return create_success_response(result['data'], "Event created successfully")
        else:
            return create_error_response(result['error'], 400, 'CREATE_EVENT_ERROR')
            
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/microsoft/disconnect', methods=['POST'])
@handle_api_errors
def microsoft_disconnect():
    """Disconnect Microsoft account"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return create_error_response("User ID required", 400, 'MISSING_USER_ID')
        
        # Remove tokens from session
        session.pop(f'microsoft_tokens_{user_id}', None)
        
        return create_success_response({}, "Microsoft account disconnected")
        
    except Exception as e:
        return create_error_response(str(e), 500, 'INTERNAL_ERROR')

@app.route('/api/auth/mailchimp/connect', methods=['POST'])
def mailchimp_connect():
    """Connect Mailchimp account"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'})
        
        # Get Mailchimp provider
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        mailchimp_provider = email_manager.get_provider('mailchimp')
        if not mailchimp_provider:
            return jsonify({'success': False, 'error': 'Mailchimp provider not configured'})
        
        # Test connection
        if mailchimp_provider.authenticate():
            return jsonify({
                'success': True,
                'message': 'Mailchimp connected successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to authenticate with Mailchimp'})
        
    except Exception as e:
        print(f"❌ Mailchimp connect error: {e}")
        return jsonify({'success': False, 'error': 'Failed to connect Mailchimp'})

@app.route('/api/auth/apple/connect', methods=['POST'])
def apple_connect():
    """Connect Apple iCloud account"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'})
        
        # Get Apple iCloud provider
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        apple_provider = email_manager.get_provider('icloud')
        if not apple_provider:
            return jsonify({'success': False, 'error': 'Apple iCloud provider not configured'})
        
        # Test connection
        if apple_provider.authenticate():
            return jsonify({
                'success': True,
                'message': 'Apple iCloud connected successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to authenticate with Apple iCloud'})
        
    except Exception as e:
        print(f"❌ Apple iCloud connect error: {e}")
        return jsonify({'success': False, 'error': 'Failed to connect Apple iCloud'})

@app.route('/api/email/services/status', methods=['GET'])
def email_services_status():
    """Get status of all email services"""
    try:
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        status = email_manager.get_provider_status()
        
        return jsonify({
            'success': True,
            'services': status
        })
        
    except Exception as e:
        print(f"❌ Email services status error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get email services status'})

@app.route('/api/email/services/<service_name>/messages', methods=['GET'])
def get_service_messages(service_name):
    """Get messages from a specific email service"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        provider = email_manager.get_provider(service_name)
        if not provider:
            return jsonify({'success': False, 'error': f'Service {service_name} not available'})
        
        if not provider.is_authenticated():
            return jsonify({'success': False, 'error': f'Service {service_name} not authenticated'})
        
        messages = provider.get_messages(limit)
        
        return jsonify({
            'success': True,
            'messages': messages,
            'service': service_name
        })
        
    except Exception as e:
        print(f"❌ Get service messages error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get messages'})

@app.route('/api/email/services/<service_name>/send', methods=['POST'])
def send_service_message(service_name):
    """Send message via a specific email service"""
    try:
        data = request.get_json()
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not all([to, subject, body]):
            return jsonify({'success': False, 'error': 'Missing required fields: to, subject, body'})
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        provider = email_manager.get_provider(service_name)
        if not provider:
            return jsonify({'success': False, 'error': f'Service {service_name} not available'})
        
        if not provider.is_authenticated():
            return jsonify({'success': False, 'error': f'Service {service_name} not authenticated'})
        
        success = provider.send_message(to, subject, body)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message sent successfully',
                'service': service_name
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to send message'})
        
    except Exception as e:
        print(f"❌ Send service message error: {e}")
        return jsonify({'success': False, 'error': 'Failed to send message'})

# Mailchimp specific routes
@app.route('/api/mailchimp/campaigns', methods=['GET'])
def get_mailchimp_campaigns():
    """Get Mailchimp campaigns"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        mailchimp_provider = email_manager.get_provider('mailchimp')
        if not mailchimp_provider:
            return jsonify({'success': False, 'error': 'Mailchimp provider not available'})
        
        if not mailchimp_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Mailchimp not authenticated'})
        
        campaigns = mailchimp_provider.get_campaigns(limit)
        
        return jsonify({
            'success': True,
            'campaigns': campaigns
        })
        
    except Exception as e:
        print(f"❌ Get Mailchimp campaigns error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get campaigns'})

@app.route('/api/mailchimp/subscribers', methods=['GET'])
def get_mailchimp_subscribers():
    """Get Mailchimp subscribers"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        mailchimp_provider = email_manager.get_provider('mailchimp')
        if not mailchimp_provider:
            return jsonify({'success': False, 'error': 'Mailchimp provider not available'})
        
        if not mailchimp_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Mailchimp not authenticated'})
        
        subscribers = mailchimp_provider.get_subscribers(limit=limit)
        
        return jsonify({
            'success': True,
            'subscribers': subscribers
        })
        
    except Exception as e:
        print(f"❌ Get Mailchimp subscribers error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get subscribers'})

@app.route('/api/mailchimp/subscribers', methods=['POST'])
def add_mailchimp_subscriber():
    """Add subscriber to Mailchimp"""
    try:
        data = request.get_json()
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        tags = data.get('tags', [])
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'})
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        mailchimp_provider = email_manager.get_provider('mailchimp')
        if not mailchimp_provider:
            return jsonify({'success': False, 'error': 'Mailchimp provider not available'})
        
        if not mailchimp_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Mailchimp not authenticated'})
        
        success = mailchimp_provider.add_subscriber(email, first_name, last_name, tags)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Subscriber added successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add subscriber'})
        
    except Exception as e:
        print(f"❌ Add Mailchimp subscriber error: {e}")
        return jsonify({'success': False, 'error': 'Failed to add subscriber'})

# Microsoft Graph specific routes
@app.route('/api/microsoft/calendar/events', methods=['GET'])
def get_microsoft_calendar_events():
    """Get Microsoft Graph calendar events"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        microsoft_provider = email_manager.get_provider('microsoft365')
        if not microsoft_provider:
            return jsonify({'success': False, 'error': 'Microsoft provider not available'})
        
        if not microsoft_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Microsoft not authenticated'})
        
        events = microsoft_provider.get_calendar_events(limit)
        
        return jsonify({
            'success': True,
            'events': events
        })
        
    except Exception as e:
        print(f"❌ Get Microsoft calendar events error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get calendar events'})

@app.route('/api/microsoft/contacts', methods=['GET'])
def get_microsoft_contacts():
    """Get Microsoft Graph contacts"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        microsoft_provider = email_manager.get_provider('microsoft365')
        if not microsoft_provider:
            return jsonify({'success': False, 'error': 'Microsoft provider not available'})
        
        if not microsoft_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Microsoft not authenticated'})
        
        contacts = microsoft_provider.get_contacts(limit)
        
        return jsonify({
            'success': True,
            'contacts': contacts
        })
        
    except Exception as e:
        print(f"❌ Get Microsoft contacts error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get contacts'})

# Apple iCloud specific routes
@app.route('/api/apple/calendar/events', methods=['GET'])
def get_apple_calendar_events():
    """Get Apple iCloud calendar events"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        apple_provider = email_manager.get_provider('icloud')
        if not apple_provider:
            return jsonify({'success': False, 'error': 'Apple iCloud provider not available'})
        
        if not apple_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Apple iCloud not authenticated'})
        
        events = apple_provider.get_calendar_events(limit)
        
        return jsonify({
            'success': True,
            'events': events
        })
        
    except Exception as e:
        print(f"❌ Get Apple calendar events error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get calendar events'})

@app.route('/api/apple/contacts', methods=['GET'])
def get_apple_contacts():
    """Get Apple iCloud contacts"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        email_manager = services.get('email_manager')
        if not email_manager:
            return jsonify({'success': False, 'error': 'Email manager not available'})
        
        apple_provider = email_manager.get_provider('icloud')
        if not apple_provider:
            return jsonify({'success': False, 'error': 'Apple iCloud provider not available'})
        
        if not apple_provider.is_authenticated():
            return jsonify({'success': False, 'error': 'Apple iCloud not authenticated'})
        
        contacts = apple_provider.get_contacts(limit)
        
        return jsonify({
            'success': True,
            'contacts': contacts
        })
        
    except Exception as e:
        print(f"❌ Get Apple contacts error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get contacts'})

# Webhook routes
@app.route('/api/webhooks/mailchimp', methods=['POST'])
def mailchimp_webhook():
    """Handle Mailchimp webhooks"""
    try:
        # Get webhook signature
        signature = request.headers.get('X-Mailchimp-Signature')
        payload = request.get_data(as_text=True)
        
        # Verify webhook signature
        email_manager = services.get('email_manager')
        if email_manager:
            mailchimp_provider = email_manager.get_provider('mailchimp')
            if mailchimp_provider and not mailchimp_provider.verify_webhook(payload, signature):
                return jsonify({'success': False, 'error': 'Invalid webhook signature'}), 401
        
        # Process webhook data
        data = request.get_json()
        event_type = data.get('type')
        
        print(f"📧 Mailchimp webhook received: {event_type}")
        
        # Handle different webhook events
        if event_type == 'subscribe':
            print(f"✅ New subscriber: {data.get('data', {}).get('email')}")
        elif event_type == 'unsubscribe':
            print(f"❌ Unsubscribed: {data.get('data', {}).get('email')}")
        elif event_type == 'profile':
            print(f"🔄 Profile updated: {data.get('data', {}).get('email')}")
        
        return jsonify({'success': True, 'message': 'Webhook processed'})
        
    except Exception as e:
        print(f"❌ Mailchimp webhook error: {e}")
        return jsonify({'success': False, 'error': 'Webhook processing failed'}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic dashboard template
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fikiri Solutions - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .service { background: white; padding: 20px; border-radius: 8px; }
        .status { padding: 5px 10px; border-radius: 4px; color: white; font-size: 12px; }
        .active { background: #10b981; }
        .inactive { background: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Fikiri Solutions - Backend Dashboard</h1>
            <p>All services are running and ready for production!</p>
        </div>
        <div class="services">
            <div class="service">
                <h3>AI Assistant</h3>
                <span class="status active">Active</span>
                <p>AI-powered email responses and lead analysis</p>
            </div>
            <div class="service">
                <h3>CRM Service</h3>
                <span class="status active">Active</span>
                <p>Lead management and customer relationships</p>
            </div>
            <div class="service">
                <h3>Email Parser</h3>
                <span class="status active">Active</span>
                <p>Email processing and content extraction</p>
            </div>
            <div class="service">
                <h3>Automation Engine</h3>
                <span class="status active">Active</span>
                <p>Automated workflows and email actions</p>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    with open('templates/dashboard.html', 'w') as f:
        f.write(dashboard_html)
    
    print("🚀 Starting Fikiri Flask Application...")
    base_url = os.getenv('BASE_URL', 'http://localhost:8081')
    print(f"📊 Dashboard: {base_url}")
    print(f"🔧 API Endpoints: {base_url}/api/")
    
    # Flask app will be started at the end of the file

# Dashboard Data Endpoints
@app.route('/api/services', methods=['GET'])
def api_get_services():
    """Get all available services and their status."""
    try:
        service_list = []
        
        # Gmail Service
        gmail_status = 'active' if services['gmail'] and services['gmail'].is_authenticated() else 'inactive'
        service_list.append({
            'id': 'gmail',
            'name': 'Gmail Integration',
            'status': gmail_status,
            'description': 'Connect and manage Gmail accounts for email automation'
        })
        
        # Outlook Service (placeholder for future integration)
        service_list.append({
            'id': 'outlook',
            'name': 'Outlook Integration',
            'status': 'inactive',
            'description': 'Microsoft Outlook integration (coming soon)'
        })
        
        # AI Assistant Service
        ai_status = 'active' if services['ai_assistant'] and services['ai_assistant'].is_enabled() else 'inactive'
        service_list.append({
            'id': 'ai_assistant',
            'name': 'AI Assistant',
            'status': ai_status,
            'description': 'AI-powered email responses and lead analysis'
        })
        
        # CRM Service
        crm_status = 'active' if services['crm'] else 'inactive'
        service_list.append({
            'id': 'crm',
            'name': 'CRM System',
            'status': crm_status,
            'description': 'Customer relationship management and lead tracking'
        })
        
        # Email Parser Service
        parser_status = 'active' if services['parser'] else 'inactive'
        service_list.append({
            'id': 'email_parser',
            'name': 'Email Parser',
            'status': parser_status,
            'description': 'Intelligent email content analysis and extraction'
        })
        
        # ML Scoring Service
        ml_status = 'active' if services['ml_scoring'] else 'inactive'
        service_list.append({
            'id': 'ml_scoring',
            'name': 'Lead Scoring',
            'status': ml_status,
            'description': 'Machine learning-powered lead qualification'
        })
        
        return jsonify(service_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def api_get_dashboard_metrics():
    """Get dashboard metrics."""
    try:
        # Get real data from services
        total_emails = 0
        active_leads = 0
        ai_responses = 0
        avg_response_time = 0.0
        
        # Count leads from CRM
        if services['crm']:
            try:
                leads = services['crm'].get_all_leads()
                active_leads = len(leads)
            except:
                active_leads = 0
        
        # Get AI stats
        if services['ai_assistant']:
            try:
                stats = services['ai_assistant'].get_usage_stats()
                ai_responses = stats.get('successful_responses', 0)
                avg_response_time = stats.get('avg_response_time', 0.0)
            except:
                ai_responses = 0
                avg_response_time = 0.0
        
        # Simulate email count (would come from Gmail API in real implementation)
        if services['gmail'] and services['gmail'].is_authenticated():
            total_emails = 42  # Placeholder - would query Gmail API
        
        metrics = {
            'totalEmails': total_emails,
            'activeLeads': active_leads,
            'aiResponses': ai_responses,
            'avgResponseTime': round(avg_response_time, 2)
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity', methods=['GET'])
def api_get_activity():
    """Get recent activity feed."""
    try:
        activity_list = []
        
        # Add AI Assistant activity
        if services['ai_assistant']:
            try:
                stats = services['ai_assistant'].get_usage_stats()
                if stats.get('successful_responses', 0) > 0:
                    activity_list.append({
                        'id': 1,
                        'type': 'ai_response',
                        'message': f'AI Assistant generated {stats.get("successful_responses", 0)} responses',
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
            except:
                pass
        
        # Add CRM activity
        if services['crm']:
            try:
                leads = services['crm'].get_all_leads()
                if leads:
                    activity_list.append({
                        'id': 2,
                        'type': 'lead_added',
                        'message': f'{len(leads)} leads in CRM system',
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
            except:
                pass
        
        # Add Gmail activity
        if services['gmail'] and services['gmail'].is_authenticated():
            activity_list.append({
                'id': 3,
                'type': 'email_sync',
                'message': 'Gmail account connected successfully',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
        else:
            activity_list.append({
                'id': 4,
                'type': 'email_sync',
                'message': 'Gmail integration not configured',
                'timestamp': datetime.now().isoformat(),
                'status': 'warning'
            })
        
        # Sort by timestamp (newest first)
        activity_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify(activity_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Email Service Integration Endpoints
@app.route('/api/email/providers', methods=['GET'])
def api_get_email_providers():
    """Get all available email providers and their status."""
    try:
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        status = services['email_manager'].get_provider_status()
        return jsonify({
            'providers': status,
            'active_provider': services['email_manager'].active_provider
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/switch-provider', methods=['POST'])
def api_switch_email_provider():
    """Switch to a different email provider."""
    try:
        data = request.get_json()
        provider_name = data.get('provider')
        
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        if services['email_manager'].switch_provider(provider_name):
            return jsonify({
                'success': True,
                'active_provider': provider_name,
                'message': f'Switched to {provider_name}'
            })
        else:
            return jsonify({'error': f'Provider {provider_name} not available'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/messages', methods=['GET'])
def api_get_email_messages():
    """Get recent messages from the active email provider."""
    try:
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        limit = request.args.get('limit', 10, type=int)
        messages = services['email_manager'].get_all_messages(limit)
        
        return jsonify({
            'messages': messages,
            'count': len(messages),
            'provider': services['email_manager'].active_provider
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/send', methods=['POST'])
def api_send_email():
    """Send an email via the active provider."""
    try:
        data = request.get_json()
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not all([to, subject, body]):
            return jsonify({'error': 'Missing required fields: to, subject, body'}), 400
        
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        success = services['email_manager'].send_message(to, subject, body)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Email sent successfully',
                'provider': services['email_manager'].active_provider
            })
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RESPONSES API MIGRATION ENDPOINTS - Industry-Specific AI Automation
# ============================================================================

@app.route('/api/industry/chat', methods=['POST'])
def industry_chat():
    """Industry-specific AI chat using Responses API with structured workflows"""
    try:
        data = request.get_json()
        industry = data.get('industry', 'general')
        client_id = data.get('client_id', 'default')
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Process with industry-specific prompt and tools
        result = responses_manager.process_industry_request(industry, client_id, message)
        
        return jsonify({
            'response': result['response'],
            'industry': result.get('industry', industry),
            'conversation_id': result.get('conversation_id'),
            'tools_used': result.get('tools_used', []),
            'usage_metrics': result.get('usage_metrics', {}),
            'success': result['success']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/industry/prompts', methods=['GET'])
def get_industry_prompts():
    """Get available industry-specific prompts"""
    try:
        prompts = {}
        for industry, config in responses_manager.industry_prompts.items():
            prompts[industry] = {
                'industry': config.industry,
                'tone': config.tone,
                'focus_areas': config.focus_areas,
                'tools': config.tools,
                'pricing_tier': config.pricing_tier
            }
        
        return jsonify({
            'prompts': prompts,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/industry/analytics/<client_id>', methods=['GET'])
def get_client_analytics(client_id):
    """Get comprehensive analytics for client reporting and pricing tiers"""
    try:
        analytics = responses_manager.get_client_analytics(client_id)
        
        return jsonify({
            'analytics': analytics,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/industry/create-prompt', methods=['POST'])
def create_industry_prompt():
    """Create a new industry-specific prompt"""
    try:
        data = request.get_json()
        industry = data.get('industry')
        client_id = data.get('client_id')
        
        if not industry or not client_id:
            return jsonify({'error': 'Industry and client_id are required'}), 400
        
        prompt_id = responses_manager.create_industry_prompt(industry, client_id)
        
        return jsonify({
            'prompt_id': prompt_id,
            'industry': industry,
            'client_id': client_id,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/industry/pricing-tiers', methods=['GET'])
def get_pricing_tiers():
    """Get pricing tier information based on usage"""
    try:
        tiers = {
            'starter': {
                'name': 'Starter',
                'price': 39.00,
                'responses_limit': 200,
                'features': ['Basic AI responses', 'Email automation', 'Simple CRM', '500 emails/month']
            },
            'growth': {
                'name': 'Growth',
                'price': 79.00,
                'responses_limit': 800,
                'features': ['Advanced AI responses', 'Advanced CRM', 'Priority support', '2,000 emails/month']
            },
            'business': {
                'name': 'Business',
                'price': 199.00,
                'responses_limit': 4000,
                'features': ['White-label options', 'Custom integrations', 'Phone support', '10,000 emails/month']
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 399.00,
                'responses_limit': 'unlimited',
                'features': ['Custom AI training', 'Dedicated support', 'SLA guarantee', 'Unlimited emails']
            }
        }
        
        return jsonify({
            'tiers': tiers,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# CLIENT ANALYTICS & REPORTING ENDPOINTS
# ============================================================================

@app.route('/api/analytics/generate-report', methods=['POST'])
def generate_client_report():
    """Generate comprehensive client report with ROI analysis"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        industry = data.get('industry')
        usage_data = data.get('usage_data', {})
        
        if not client_id or not industry:
            return jsonify({'error': 'client_id and industry are required'}), 400
        
        # Generate comprehensive report
        report = analytics_engine.generate_client_report(client_id, industry, usage_data)
        
        # Format for client presentation
        formatted_report = analytics_engine.format_report_for_client(report)
        
        return jsonify({
            'report': formatted_report,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/roi-calculator', methods=['POST'])
def calculate_roi():
    """Calculate ROI for potential clients"""
    try:
        data = request.get_json()
        industry = data.get('industry')
        current_hours_wasted = data.get('hours_wasted_per_month', 0)
        current_revenue = data.get('monthly_revenue', 0)
        
        if not industry:
            return jsonify({'error': 'industry is required'}), 400
        
        # Calculate potential savings
        monthly_cost = analytics_engine._get_monthly_cost(industry)
        hours_saved = min(current_hours_wasted * 0.8, 40)  # Assume 80% reduction, max 40 hours
        hourly_rate = current_revenue / 160 if current_revenue > 0 else 50  # Assume 160 working hours/month
        
        time_savings_value = hours_saved * hourly_rate
        efficiency_gain = (hours_saved / 160) * 100
        
        # Calculate ROI
        roi_percentage = (time_savings_value / monthly_cost) * 100 if monthly_cost > 0 else 0
        payback_period = monthly_cost / (time_savings_value / 30) if time_savings_value > 0 else 0
        
        return jsonify({
            'roi_analysis': {
                'monthly_cost': monthly_cost,
                'hours_saved': hours_saved,
                'time_savings_value': time_savings_value,
                'efficiency_gain': efficiency_gain,
                'roi_percentage': roi_percentage,
                'payback_period_days': int(payback_period)
            },
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/industry-benchmarks', methods=['GET'])
def get_industry_benchmarks():
    """Get industry benchmarks for comparison"""
    try:
        industry = request.args.get('industry')
        
        if industry:
            benchmarks = analytics_engine.industry_benchmarks.get(industry, {})
            return jsonify({
                'industry': industry,
                'benchmarks': benchmarks,
                'success': True
            })
        else:
            return jsonify({
                'all_benchmarks': analytics_engine.industry_benchmarks,
                'success': True
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic dashboard template
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fikiri Solutions - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .service { background: white; padding: 20px; border-radius: 8px; }
        .status { padding: 5px 10px; border-radius: 4px; color: white; font-size: 12px; }
        .active { background: #10b981; }
        .inactive { background: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Fikiri Solutions - Backend Dashboard</h1>
            <p>All services are running and ready for production!</p>
        </div>
        <div class="services">
            <div class="service">
                <h3>AI Assistant</h3>
                <span class="status active">Active</span>
                <p>AI-powered email responses and lead analysis</p>
            </div>
            <div class="service">
                <h3>CRM Service</h3>
                <span class="status active">Active</span>
                <p>Lead management and customer relationships</p>
            </div>
            <div class="service">
                <h3>Email Parser</h3>
                <span class="status active">Active</span>
                <p>Email processing and content extraction</p>
            </div>
            <div class="service">
                <h3>Automation Engine</h3>
                <span class="status active">Active</span>
                <p>Automated workflows and email actions</p>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    with open('templates/dashboard.html', 'w') as f:
        f.write(dashboard_html)
    
    print("🚀 Starting Fikiri Flask Application...")
    base_url = os.getenv('BASE_URL', 'http://localhost:8081')
    print(f"📊 Dashboard: {base_url}")
    print(f"🔧 API Endpoints: {base_url}/api/")
    
    # Run Flask app (SocketIO disabled for now)
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 8081)))

# Sentry Test Routes
@app.route('/api/sentry-test', methods=['GET'])
def sentry_test():
    """Test Sentry integration by triggering an error."""
    try:
        # This will trigger a Sentry error for testing
        1/0  # raises a ZeroDivisionError
    except Exception as e:
        # Capture the exception in Sentry
        sentry_sdk.capture_exception(e)
        return jsonify({
            'message': 'Sentry test error triggered',
            'error': str(e),
            'status': 'error_sent_to_sentry'
        }), 500

@app.route('/api/sentry-performance-test', methods=['GET'])
def sentry_performance_test():
    """Test Sentry performance monitoring."""
    with sentry_sdk.start_transaction(op="test", name="sentry_performance_test"):
        # Simulate some work
        time.sleep(0.1)
        
        # Test Redis operations
        cache = get_cache()
        if cache.is_connected():
            cache.cache_ai_response("test", "response", "test_user")
        
        return jsonify({
            'message': 'Sentry performance test completed',
            'status': 'success',
            'redis_connected': cache.is_connected()
        }), 200

# Webhook Sentry Test Routes
@app.route('/api/webhook-sentry-test', methods=['GET'])
def webhook_sentry_test():
    """Test webhook Sentry integration by triggering an error."""
    try:
        # This will trigger a webhook Sentry error for testing
        webhook_data = {
            'type': 'test_webhook',
            'source': 'sentry_test',
            'timestamp': datetime.now().isoformat()
        }
        
        # Simulate webhook processing error
        raise Exception('This is a webhook Sentry test error!')
        
    except Exception as e:
        # Capture the error in webhook Sentry
        capture_webhook_error(e, webhook_data, 'test_user')
        return jsonify({
            'message': 'Webhook Sentry test error triggered',
            'error': str(e),
            'webhook_data': webhook_data,
            'status': 'error_sent_to_webhook_sentry'
        }), 500

@app.route('/api/webhook-sentry-performance-test', methods=['GET'])
def webhook_sentry_performance_test():
    """Test webhook Sentry performance monitoring."""
    webhook_data = {
        'type': 'performance_test',
        'source': 'sentry_test',
        'timestamp': datetime.now().isoformat()
    }
    
    with capture_webhook_performance('webhook_performance_test', webhook_data) as transaction:
        # Simulate webhook processing work
        time.sleep(0.1)
        
        # Test Redis operations
        cache = get_cache()
        if cache.is_connected():
            cache.cache_ai_response("webhook_test", "webhook_response", "test_user")
        
        # Test webhook queue
        webhook_queue = get_webhook_queue()
        if webhook_queue.is_connected():
            job_id = webhook_queue.enqueue_job(
                "process_webhook",
                {
                    "webhook_data": webhook_data,
                    "test": True
                }
            )
            transaction.set_data("job_id", job_id)
        
        return jsonify({
            'message': 'Webhook Sentry performance test completed',
            'status': 'success',
            'redis_connected': cache.is_connected(),
            'webhook_queue_connected': webhook_queue.is_connected(),
            'webhook_data': webhook_data
        }), 200

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic dashboard template
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fikiri Solutions - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Fikiri Solutions</h1>
            <p>AI-Powered Email Automation Platform</p>
        </div>
        
        <div class="status success">
            <strong>✅ Backend Status:</strong> Running successfully
        </div>
        
        <div class="status info">
            <strong>📧 Email Services:</strong> Gmail, Microsoft 365, Mailchimp, Apple iCloud
        </div>
        
        <div class="status info">
            <strong>🤖 AI Features:</strong> Email parsing, response generation, lead scoring
        </div>
        
        <div class="status info">
            <strong>📊 CRM:</strong> Lead management, contact tracking, analytics
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <p>Visit <a href="/api/health">/api/health</a> for detailed system status</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Write dashboard template
    dashboard_path = templates_dir / 'dashboard.html'
    dashboard_path.write_text(dashboard_html)
    
    print("🚀 Starting Fikiri Solutions Flask Application...")
    print("📧 Email Services: Gmail, Microsoft 365, Mailchimp, Apple iCloud")
    print("🤖 AI Features: Email parsing, response generation, lead scoring")
    print("📊 CRM: Lead management, contact tracking, analytics")
    print("🌐 Frontend: React application with Vite")
    print("🔧 Backend: Flask with comprehensive API")
    print("📱 PWA: Progressive Web App capabilities")
    print("🔒 Security: Rate limiting, CORS, input validation")
    print("📈 Monitoring: Sentry integration, performance tracking")
    print("💾 Database: SQLite with Redis caching")
    print("🚀 Deployment: Render + Vercel")
    print("=" * 60)
    print("🌐 Application will be available at: http://localhost:5000")
    print("📊 Health check: http://localhost:5000/api/health")
    print("📚 API docs: http://localhost:5000/api/docs")
    print("=" * 60)
    
    # Start the Flask application
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=True,
        threaded=True
    )
