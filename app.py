#!/usr/bin/env python3
"""
Fikiri Solutions - Simplified Flask Application
Production-ready modular architecture with clean separation of concerns
"""

import os
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Sentry integration handled by core/monitoring.py

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
CORS(app, resources={r"/api/*": {"origins": ["https://fikirisolutions.com"]}})

# Core imports
from core.minimal_config import get_config
from core.minimal_auth import MinimalAuthenticator
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_gmail_utils import MinimalGmailService
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_crm_service import MinimalCRMService
from core.minimal_ai_assistant import MinimalAIEmailAssistant
from core.minimal_ml_scoring import MinimalMLScoring
from core.minimal_vector_search import MinimalVectorSearch
from core.feature_flags import get_feature_flags
from core.email_service_manager import EmailServiceManager

# Enhanced services
from core.jwt_auth import jwt_auth_manager
from core.secure_sessions import secure_session_manager, init_secure_sessions
from core.idempotency_manager import idempotency_manager
from core.rate_limiter import enhanced_rate_limiter
# Removed unused imports: create_api_blueprint, create_business_blueprint
from core.enterprise_logging import log_api_request, log_api_request
from core.monitoring import init_health_monitoring, init_sentry
from core.business_operations import business_intelligence, legal_compliance
from core.structured_logging import monitor, error_tracker
from core.performance_monitor import performance_monitor

# Blueprint imports
from core.app_onboarding import bp as onboarding_bp
from core.billing_api import billing_bp
from core.webhook_api import webhook_bp
from core.crm_completion_api import crm_bp
from core.docs_forms_api import docs_forms_bp
from core.chatbot_smart_faq_api import chatbot_bp
from core.workflow_templates_api import workflow_templates_bp
from core.monitoring_dashboard_api import monitoring_dashboard_bp
from core.app_oauth import oauth

# Route blueprints (extracted modules)
from routes import auth_bp, business_bp, test_bp, user_bp, monitoring_bp

logger = logging.getLogger(__name__)

# Global services dictionary
services = {}

def initialize_services():
    """Initialize all core services."""
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
        services['feature_flags'] = get_feature_flags()
        services['email_manager'] = EmailServiceManager()
        
        # Initialize health monitoring
        try:
            init_health_monitoring(app)
            print("✅ Health monitoring initialized")
        except Exception as e:
            print(f"⚠️ Health monitoring initialization failed: {e}")
        
        # Initialize Sentry
        try:
            init_sentry(app)
            print("✅ Sentry initialized")
        except Exception as e:
            print(f"⚠️ Sentry initialization failed: {e}")
        
        print("✅ All services initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

# Initialize secure sessions
@init_secure_sessions(app)

# Request logging middleware
@app.before_request
def log_request():
    """Log incoming requests"""
    request.start_time = time.time()

@app.after_request
def log_response(response):
    """Log responses and performance"""
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        
        # Log to enterprise logging
        try:
            log_api_request(
                endpoint=request.endpoint or request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.warning(f"Logging failed: {e}")
        
        # Record performance metrics
        performance_monitor.record_request(
            endpoint=request.endpoint or request.path,
            method=request.method,
            response_time=response_time,
            status_code=response.status_code
        )
        
        return response
        
# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500

# Register blueprints
def register_blueprints():
    """Register all application blueprints"""
    
    # Core feature blueprints
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(docs_forms_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(workflow_templates_bp)
    app.register_blueprint(monitoring_dashboard_bp)
    
    # OAuth blueprint
    try:
        app.register_blueprint(oauth)
        print("✅ OAuth blueprint registered")
    except Exception as e:
        print(f"❌ OAuth blueprint failed: {e}")
    
    # Extracted route blueprints
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(business_bp, url_prefix="/api")
    app.register_blueprint(test_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(monitoring_bp, url_prefix="/api")

# Health check endpoint
@app.route('/health')
def health_check():
    """Simple health check"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'message': 'Fikiri Solutions API',
        'endpoints': {
            'auth': '/api/auth/*',
            'business': '/api/business/*',
            'test': '/api/test/*',
            'user': '/api/user/*',
            'monitoring': '/api/monitoring/*',
            'health': '/api/health'
        },
        "frontend": "https://fikirisolutions.com"
    })

# Main endpoint
@app.route('/')
def home():
    """API information endpoint"""
    return jsonify({
        'message': 'Fikiri Solutions API',
        'status': 'running',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'frontend': 'https://fikirisolutions.com'
    })

# Frontend routes
@app.route('/dashboard')
def dashboard():
    """Serve dashboard page"""
    return render_template('dashboard.html')

# Initialize services and register blueprints
if initialize_services():
    register_blueprints()
else:
    logger.error("Failed to initialize services")

if __name__ == '__main__':
    # Development server configuration
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development',
        threaded=True
    )