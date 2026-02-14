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
except ImportError:
    pass  # python-dotenv not available - using system environment variables

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
logger.info("Starting Fikiri API environment: %s", os.getenv("FLASK_ENV", "production"))

# Core imports
from core.minimal_config import get_config
from email_automation.parser import MinimalEmailParser
from integrations.gmail.utils import MinimalGmailService
from email_automation.actions import MinimalEmailActions
from email_automation.ai_assistant import MinimalAIEmailAssistant
from core.minimal_ml_scoring import MinimalMLScoring
from core.minimal_vector_search import MinimalVectorSearch
from core.feature_flags import get_feature_flags
from email_automation.service_manager import EmailServiceManager

# Enhanced services
from core.jwt_auth import get_jwt_manager
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
from services.business_operations import create_business_blueprint

# Blueprint imports
from core.app_onboarding import bp as onboarding_bp
from core.billing_api import billing_bp
from core.webhook_api import webhook_bp
from crm.completion_api import crm_bp
from core.docs_forms_api import docs_forms_bp
from core.chatbot_smart_faq_api import chatbot_bp
from core.public_chatbot_api import public_chatbot_bp
from core.ai_analysis_api import ai_analysis_bp
from core.workflow_templates_api import workflow_templates_bp
from analytics.monitoring_api import monitoring_dashboard_bp
from core.ai_chat_api import ai_bp
from analytics.dashboard_api import dashboard_bp

# Dev test routes (development only)
if os.getenv('FLASK_ENV') == 'development':
    from core.dev_test_routes import dev_tests_bp

# OAuth blueprint (conditional import)
try:
    from core.app_oauth import oauth
except ImportError:
    logger.warning("OAuth blueprint not available")
    oauth = None

# Route blueprints (extracted modules)
from routes import auth_bp, business_bp, test_bp, user_bp, monitoring_bp
from routes.integrations import integrations_bp
from routes.appointments import appointments_bp

# Global services dictionary
services = {}

def create_app():
    """Flask Application Factory Pattern with Enhanced Monitoring"""
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    app.socketio = None  # Will be initialized in create_app() if available
    
    # 🔧 Database sanity check and initialization
    try:
        from core.database_init import init_database, check_database_health
        from core.database_optimization import db_optimizer
        
        logger.info("Checking database connectivity...")
        try:
            logger.info("Database path: %s", db_optimizer.db_path)
            result = db_optimizer.execute_query("SELECT name FROM sqlite_master WHERE type='table';")
            logger.info("Existing tables: %s", [r['name'] for r in result])
        except Exception as e:
            logger.error("Database connection failed: %s", e)
        logger.info("Running init_database() ...")
        if init_database():
            logger.info("Database initialized.")
        else:
            logger.warning("Database initialization failed")
        logger.info("Running database health check ...")
        if check_database_health():
            logger.info("Health check completed.")
        else:
            logger.warning("Health check failed")
    except Exception as e:
        logger.error("Database startup error: %s", e)
    
    # Enhanced CORS configuration for cookie-based auth
    # Allow both local development ports (3000 for Next.js, 5173/5174 for Vite)
    cors_origins = [
        "https://fikirisolutions.com",
        "https://www.fikirisolutions.com",
        "https://fikirisolutions.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    
    # In development, dynamically allow the requesting origin
    # Note: Cannot use '*' with supports_credentials=True
    def get_cors_origins():
        if os.getenv('FLASK_ENV') == 'development':
            # In development, allow any localhost or local network origin
            return cors_origins  # Will be validated dynamically
        return cors_origins
    
    CORS(app, 
         resources={r"/api/*": {"origins": get_cors_origins()}},
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken', 'Accept', 'Cache-Control', 'Pragma', 'x-cache-version', 'x-deployment-timestamp', 'expires'],
         supports_credentials=True,
         max_age=3600,
         vary_header=True,
         automatic_options=True  # Automatically handle OPTIONS requests
    )
    # Mark CORS as configured to prevent init_security from overriding it
    app._cors_configured = True
    
    # Add explicit OPTIONS handler for CORS preflight in development
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')
            # In development, allow any localhost or local network origin
            if os.getenv('FLASK_ENV') == 'development' and origin:
                if (origin.startswith('http://localhost') or 
                    origin.startswith('http://127.0.0.1') or
                    origin.startswith('http://10.') or
                    origin.startswith('http://192.168.') or
                    origin.startswith('http://172.')):
                    response = jsonify({})
                    response.headers.add("Access-Control-Allow-Origin", origin)
                    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,X-CSRFToken,Accept,Cache-Control,Pragma,x-cache-version,x-deployment-timestamp,expires")
                    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH,HEAD")
                    response.headers.add("Access-Control-Allow-Credentials", "true")
                    response.headers.add("Access-Control-Max-Age", "3600")
                    return response
    
    # Setup request logging
    setup_request_logging(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Setup routes
    setup_routes(app)
    
    # Initialize SocketIO for real-time updates (optional, non-blocking)
    app.socketio = None
    try:
        from flask_socketio import SocketIO
        
        # SocketIO origin validation function
        def validate_socketio_origin(origin):
            """Validate SocketIO origin, allowing local network IPs in development"""
            if not origin:
                return False
            # Production origins
            if origin in cors_origins:
                return True
            # In development, allow localhost and local network IPs
            if os.getenv('FLASK_ENV') == 'development':
                if (origin.startswith('http://localhost') or 
                    origin.startswith('http://127.0.0.1') or
                    origin.startswith('http://10.') or
                    origin.startswith('http://192.168.') or
                    origin.startswith('http://172.')):
                    return True
            return False
        
        # SocketIO with dynamic origin validation (callable function)
        socketio = SocketIO(
            app, 
            cors_allowed_origins=validate_socketio_origin,
            async_mode='threading', 
            logger=False, 
            engineio_logger=False
        )
        
        app.socketio = socketio
        setup_socketio_handlers(socketio)
        logger.info("✅ SocketIO initialized with secure CORS (supports local network IPs in development)")
    except ImportError:
        logger.info("ℹ️ SocketIO not installed, skipping WebSocket support")
        app.socketio = None
    except Exception as e:
        logger.warning(f"⚠️ SocketIO initialization failed: {e}, continuing without WebSocket support")
        app.socketio = None
    
    # Initialize services with app reference
    if initialize_services(app):
        register_blueprints(app)
        logger.info(f"✅ Flask app created - environment: {os.getenv('FLASK_ENV', 'production')}")
    else:
        logger.error("Failed to initialize services")
    
    return app

def setup_socketio_handlers(socketio):
    """Simple WebSocket handlers for real-time updates"""
    from flask import request
    from flask_socketio import emit, join_room
    
    @socketio.on('connect')
    def handle_connect():
        emit('connected', {'status': 'ok'})
    
    @socketio.on('subscribe_dashboard')
    def handle_subscribe(*args):
        """Handle dashboard subscription with flexible argument handling"""
        # SocketIO may pass data as first arg, or no args at all
        data = args[0] if args and len(args) > 0 else {}
        if not isinstance(data, dict):
            data = {}
        user_id = data.get('user_id', '1')
        room = f"user:{user_id}"
        join_room(room)
        emit('subscribed', {'room': room})

def initialize_services(app):
    """Initialize all core services with app reference."""
    global services
    
    try:
        # Initialize core services
        services['config'] = get_config()
        services['parser'] = MinimalEmailParser()
        services['gmail'] = MinimalGmailService()
        services['actions'] = MinimalEmailActions()
        services['ai_assistant'] = MinimalAIEmailAssistant(api_key=os.getenv("OPENAI_API_KEY"))
        services['ml_scoring'] = MinimalMLScoring(services=services)
        # Lazy-load vector search to avoid mutex contention (will be created on first use)
        # Don't create here - let get_vector_search() handle it
        services['vector_search'] = None  # Will be initialized lazily
        services['feature_flags'] = get_feature_flags()
        services['email_manager'] = EmailServiceManager()

        # ✅ Security / session layers
        jwt_manager = get_jwt_manager()
        jwt_manager._initialize_tables()
        init_flask_sessions(app)
        if callable(init_secure_sessions):
            init_secure_sessions(app)
        init_security(app)

        # ✅ Observability layer - Single monitoring initialization
        from core.monitoring import init_monitoring
        init_monitoring(app)
        
        # ✅ Cleanup scheduler - Start background cleanup jobs
        from core.cleanup_scheduler import cleanup_scheduler
        cleanup_scheduler.start()
        logger.info("✅ Cleanup scheduler started")

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
        # Skip logging for OPTIONS preflight requests - let CORS handle it
        if request.method == 'OPTIONS':
            return None
        request.start_time = time.time()
    
    @app.after_request
    def log_response(response):
        """Log responses and performance"""
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            # Simple logging - no need for multiple logging systems
            logger.debug(f"{request.method} {request.path} - {response.status_code} - {response_time:.3f}s")
        
        return response

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

# Register blueprints
def register_blueprints(app):
    """Register all application blueprints with safe error handling"""
    
    # Core feature blueprints
    blueprints = [
        (appointments_bp, 'appointments'),
        (create_business_blueprint(), 'business'),
        (onboarding_bp, 'onboarding'),
        (billing_bp, 'billing'),
        (webhook_bp, 'webhook'),
        (crm_bp, 'crm'),
        (docs_forms_bp, 'docs_forms'),
        (chatbot_bp, 'chatbot'),
        (public_chatbot_bp, 'public_chatbot'),
        (ai_analysis_bp, 'ai_analysis'),
        (workflow_templates_bp, 'workflow_templates'),
        (monitoring_dashboard_bp, 'monitoring_dashboard'),
        (ai_bp, 'ai'),
        (dashboard_bp, 'dashboard'),
        (auth_bp, 'auth'),
        (business_bp, 'routes_business'),
        (test_bp, 'routes_test'),
        (user_bp, 'routes_user'),
        (monitoring_bp, 'routes_monitoring'),
        (integrations_bp, 'integrations')
    ]
    
    # Add dev test blueprint in development
    if os.getenv('FLASK_ENV') == 'development':
        blueprints.append((dev_tests_bp, 'dev_tests'))
    
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

# Add direct API routes for frontend components
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

@app.route('/api/test-simple', methods=['GET'])
def test_simple():
    """Simple test endpoint"""
    return jsonify({'success': True, 'message': 'Simple test endpoint working'})

@app.route('/api/repair-database', methods=['POST'])
def repair_database():
    """Force database repair endpoint"""
    try:
        from core.database_optimization import db_optimizer
        logger.info("🔧 Forcing database repair...")
        
        # Force database repair
        db_optimizer._repair_database()
        
        return jsonify({
            'success': True, 
            'message': 'Database repair completed successfully'
        })
    except Exception as e:
        logger.error(f"❌ Database repair failed: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

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
        
        # Prefer real LLM response; fall back to demo response
        try:
            from core.ai.llm_router import LLMRouter
            router = LLMRouter()
            if router and router.client and router.client.is_enabled():
                llm_result = router.process(
                    input_data=message,
                    intent='general',
                    context={'channel': 'ai_response_direct'}
                )
                if llm_result.get('success'):
                    return jsonify({
                        'success': True,
                        'data': {
                            'response': llm_result.get('content', ''),
                            'confidence': 0.75,
                            'intent': 'general_inquiry',
                            'suggested_actions': []
                        },
                        'message': 'AI response generated successfully'
                    })
        except Exception as llm_error:
            logger.error("AI response direct LLM failed: %s", llm_error)

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

if __name__ == '__main__':
    # Use app already created at module level (create_app() above) — avoid duplicate init
    port = int(os.getenv('PORT') or os.getenv('FLASK_RUN_PORT', 8081))
    debug = os.getenv('FLASK_ENV') == 'development'

    if app.socketio:
        logger.info(f"🚀 Starting Flask server with SocketIO on port {port}")
        app.socketio.run(app, host='0.0.0.0', port=port, debug=debug, use_reloader=False)
    else:
        logger.info(f"🚀 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, use_reloader=False)
