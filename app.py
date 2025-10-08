#!/usr/bin/env python3
"""
Fikiri Solutions - Production-Ready Flask Application
Enterprise-grade modular architecture with comprehensive monitoring
"""

import os
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Environment file loading for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("ℹ️ python-dotenv not available - using system environment variables")

# Ensure logging directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Centralized Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Environment Mode Validation
if os.getenv("FLASK_ENV") not in ["production", "development", "staging"]:
    logger.warning(f"⚠️ Invalid FLASK_ENV value: {os.getenv('FLASK_ENV')}")

# Safe Startup Logging
print("🚀 Starting Fikiri API environment:", os.getenv("FLASK_ENV", "production"))

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
from core.redis_sessions import init_flask_sessions
from core.security import init_security

# Optional limiter import for health check exemptions
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    Limiter = None
from core.backend_excellence import create_api_blueprint
from core.business_operations import create_business_blueprint
from core.enterprise_logging import log_api_request
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
from core.ai_chat_api import ai_bp
from core.dashboard_api import dashboard_bp

# OAuth blueprint (conditional import)
try:
    from core.app_oauth import oauth
except ImportError:
    logger.warning("OAuth blueprint not available")
    oauth = None

# Route blueprints (extracted modules)
from routes import auth_bp, business_bp, test_bp, user_bp, monitoring_bp

# Global services dictionary
services = {}

def create_app():
    """Flask Application Factory Pattern with Enhanced Monitoring"""
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # 🔧 Database sanity check and initialization
    try:
        from core.database_init import init_database, check_database_health
        from core.database_optimization import db_optimizer
        
        print("🔍 Checking database connectivity...")
        try:
            print(f"Database path: {db_optimizer.db_path}")
            result = db_optimizer.execute_query("SELECT name FROM sqlite_master WHERE type='table';")
            print(f"Existing tables: {[r['name'] for r in result]}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
        
        print("⚙️ Running init_database() ...")
        if init_database():
            print("✅ Database initialized.")
        else:
            print("❌ Database initialization failed")
        
        print("🏥 Running database health check ...")
        if check_database_health():
            print("✅ Health check completed.")
        else:
            print("❌ Health check failed")
            
    except Exception as e:
        print(f"❌ Database startup error: {e}")
        logger.error(f"❌ Database startup error: {e}")
    
    # Enhanced CORS configuration
    CORS(app, 
         resources={r"/api/*": {"origins": [
             "https://fikirisolutions.com",
             "http://localhost:3000"
         ]}},
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         supports_credentials=True,
         max_age=3600
    )
    
    # Setup request logging
    setup_request_logging(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Setup routes
    setup_routes(app)
    
    # Initialize services with app reference
    if initialize_services(app):
        register_blueprints(app)
        logger.info(f"✅ Flask app created - environment: {os.getenv('FLASK_ENV', 'production')}")
    else:
        logger.error("Failed to initialize services")
    
    return app

def initialize_services(app):
    """Initialize all core services with app reference."""
    global services
    
    try:
        # Initialize core services
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

        # ✅ Security / session layers
        jwt_auth_manager._initialize_tables()
        init_flask_sessions(app)
        if callable(init_secure_sessions):
            init_secure_sessions(app)
        init_security(app)

        # ✅ Observability layer - Single monitoring initialization
        from core.monitoring import init_monitoring
        init_monitoring(app)

        logger.info("✅ All services initialized successfully")
        return True
    except Exception as e:
        logger.exception("❌ Error initializing services: %s", e)
        return False

def setup_request_logging(app):
    """Setup request logging middleware"""
    
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
        
        return response  # Always return response outside the if-block

def setup_error_handlers(app):
    """Setup error handlers"""
    
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

def setup_routes(app):
    """Setup application routes with consolidated health checks"""
    
    @app.route('/api/test/init-db', methods=['POST'])
    def init_database():
        """Manually initialize database tables"""
        try:
            from core.database_optimization import db_optimizer
            
            # Force database initialization
            db_optimizer._initialize_tables()
            
            return jsonify({
                'success': True,
                'message': 'Database tables initialized successfully',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return jsonify({
                'success': False,
                'error': f'Database initialization failed: {str(e)}',
                'code': 'DB_INIT_ERROR'
            }), 500

    # Consolidated health check endpoints
    @app.route('/health/summary')
    def health_summary():
        """Simple health check summary"""
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
                'health': '/health/summary'
            },
            "frontend": "https://fikirisolutions.com"
        })

    @app.route('/api/health')
    def api_health_check():
        """API health check endpoint for Render"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'message': 'Fikiri Solutions API is running',
            'service': 'fikiri-backend',
            'environment': os.getenv('FLASK_ENV', 'production')
        })
    
    # Apply limiter exemptions to health check routes
    if LIMITER_AVAILABLE:
        try:
            limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])
            limiter.exempt(health_summary)
            limiter.exempt(api_health_check)
        except Exception as e:
            logger.warning(f"⚠️ Failed to exempt health check routes from rate limiting: {e}")

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
    
    # Direct dashboard API routes for testing
    @app.route('/api/dashboard/test-direct', methods=['GET'])
    def test_dashboard_direct():
        """Direct test endpoint for dashboard"""
        return jsonify({'success': True, 'message': 'Direct dashboard route is working'})
    
    @app.route('/api/dashboard/metrics-direct', methods=['GET'])
    def dashboard_metrics_direct():
        """Direct dashboard metrics endpoint"""
        try:
            metrics_data = {
                'success': True,
                'data': {
                    'user': {
                        'id': 1,
                        'name': 'Demo User',
                        'email': 'demo@example.com',
                        'onboarding_completed': True,
                        'onboarding_step': -1
                    },
                    'leads': {
                        'total': 45,
                        'new_today': 5,
                        'converted': 12,
                        'pending': 28
                    },
                    'emails': {
                        'processed_today': 125,
                        'replied': 89,
                        'pending': 36
                    },
                    'automation': {
                        'active_rules': 8,
                        'emails_sent': 234,
                        'success_rate': 94.5
                    }
                },
                'message': 'Dashboard metrics retrieved successfully'
            }
            return jsonify(metrics_data)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Direct AI response endpoint for testing
    @app.route('/api/ai-response', methods=['POST'])
    def ai_response_direct():
        """Direct AI response endpoint for frontend"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Request body cannot be empty'}), 400
            
            message = data.get('message', '')
            if not message:
                return jsonify({'success': False, 'error': 'Message is required'}), 400
            
            # Simple AI response logic
            response_data = {
                'success': True,
                'data': {
                    'response': f"I understand you said: '{message}'. This is a demo response from the Fikiri AI assistant. The full AI system will be available once authentication is fully configured.",
                    'confidence': 0.85,
                    'intent': 'general_inquiry',
                    'suggested_actions': [
                        'Connect your Gmail account',
                        'Set up email automation rules',
                        'View your dashboard analytics'
                    ]
                },
                'message': 'AI response generated successfully'
            }
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# Register blueprints
def register_blueprints(app):
    """Register all application blueprints with safe error handling"""
    
    # Core feature blueprints
    blueprints = [
        (create_api_blueprint('v1'), 'api_v1'),
        (create_api_blueprint('v2'), 'api_v2'),
        (create_business_blueprint(), 'business'),
        (onboarding_bp, 'onboarding'),
        (billing_bp, 'billing'),
        (webhook_bp, 'webhook'),
        (crm_bp, 'crm'),
        (docs_forms_bp, 'docs_forms'),
        (chatbot_bp, 'chatbot'),
        (workflow_templates_bp, 'workflow_templates'),
        (monitoring_dashboard_bp, 'monitoring_dashboard'),
        (ai_bp, 'ai'),
        (dashboard_bp, 'dashboard'),
        (auth_bp, 'auth'),
        (business_bp, 'routes_business'),
        (test_bp, 'routes_test'),
        (user_bp, 'routes_user'),
        (monitoring_bp, 'routes_monitoring')
    ]
    
    # Register blueprints with error handling
    for bp, name in blueprints:
        try:
            app.register_blueprint(bp)
            logger.info(f"✅ Registered blueprint: {name}")
        except Exception as e:
            logger.error(f"❌ Failed to register blueprint {name}: {e}")
    
    # OAuth blueprint (conditional)
    if oauth:
        try:
            app.register_blueprint(oauth)
            logger.info("✅ OAuth blueprint registered")
        except Exception as e:
            logger.error(f"❌ OAuth blueprint failed: {e}")

# Create Flask app instance
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development',
        threaded=True
    )# Database corruption fix - Sat Oct  4 20:29:41 EDT 2025
