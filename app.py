#!/usr/bin/env python3
"""
Fikiri Solutions - Production-Ready Flask Application
Enterprise-grade modular architecture with comprehensive monitoring
"""

import json
import os
import time
import uuid
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# Environment file loading for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not available - using system environment variables

from config import IS_PRODUCTION

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
from core.flask_secret import resolve_flask_secret_key
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
from core.security import init_security, resolve_flask_limiter_storage_uri

# Optional Flask-Limiter for health check exemptions (single instance, init_app in setup_routes)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
    _app_limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=resolve_flask_limiter_storage_uri(),
        default_limits=[
            os.getenv("APP_RATE_LIMIT_PER_HOUR", "1000 per hour"),
            os.getenv("APP_RATE_LIMIT_PER_MINUTE", "100 per minute"),
        ],
    )
except ImportError:
    LIMITER_AVAILABLE = False
    Limiter = None
    _app_limiter = None
from services.business_operations import create_business_blueprint

# Blueprint imports
from core.app_onboarding import bp as onboarding_bp
from core.billing_api import billing_bp
from core.webhook_api import webhook_bp
from crm.completion_api import crm_bp
from core.docs_forms_api import docs_forms_bp
from core.migration_api import migration_bp
from core.chatbot_smart_faq_api import chatbot_bp
from core.public_chatbot_api import public_chatbot_bp
from core.ai_analysis_api import ai_analysis_bp
from core.workflow_templates_api import workflow_templates_bp
from core.contact_api import contact_bp
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
from routes import auth_bp, business_bp, test_bp, user_bp, monitoring_bp, jobs_bp, expert_bp, kpi_bp
from routes.integrations import integrations_bp
from routes.appointments import appointments_bp
from routes.google_risc import google_risc_bp

# Global services dictionary
services = {}


def _cors_default_base_origins():
    """Align with core/security.py: prod deploys only need public origins; dev adds localhost."""
    prod = [
        "https://fikirisolutions.com",
        "https://www.fikirisolutions.com",
        "https://fikirisolutions.onrender.com",
        "https://fikirisolutions.vercel.app",
        "https://fikiri-solutions.vercel.app",
    ]
    dev = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    return prod + dev if not IS_PRODUCTION else prod


def _merge_cors_origins_from_env(base_origins):
    """
    Append origins from CORS_ORIGINS (comma-separated).

    app.py previously ignored this env var; core/security.py only reads it when CORS
    is not already configured. Render and local .env often list Vercel / preview URLs
    here — those must be merged or production browsers see missing Access-Control-Allow-Origin.
    """
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw.strip():
        return list(base_origins)
    merged = list(base_origins)
    for part in raw.split(","):
        origin = part.strip()
        if origin and origin not in merged:
            merged.append(origin)
    return merged


def create_app():
    """Flask Application Factory Pattern with Enhanced Monitoring"""
    app = Flask(__name__)
    env = os.getenv('FLASK_ENV', 'production')
    secret = resolve_flask_secret_key()
    if env in ('production', 'staging') and not secret:
        raise RuntimeError('FLASK_SECRET_KEY or SECRET_KEY is required in production and staging')
    app.secret_key = secret
    app.socketio = None  # Will be initialized in create_app() if available
    
    # 🔧 Database sanity check and initialization
    env = os.getenv('FLASK_ENV', 'production')
    run_startup_checks = env == 'development' or os.getenv('DB_STARTUP_CHECKS') == '1'
    try:
        from core.database_init import init_database, check_database_health
        from core.database_optimization import db_optimizer
        
        logger.info("Running init_database() ...")
        if init_database():
            logger.info("Database initialized.")
        else:
            logger.warning("Database initialization failed")
        if run_startup_checks:
            logger.info("Checking database connectivity...")
            try:
                logger.info("Database path: %s", db_optimizer.db_path)
                result = db_optimizer.execute_query("SELECT name FROM sqlite_master WHERE type='table';")
                logger.info("Existing tables: %s", [r['name'] for r in result])
            except Exception as e:
                logger.error("Database connection failed: %s", e)
            logger.info("Running database health check ...")
            if check_database_health():
                logger.info("Health check completed.")
            else:
                logger.warning("Health check failed")
    except Exception as e:
        logger.error("Database startup error: %s", e)
    
    # Enhanced CORS configuration for cookie-based auth
    # Allow both local development ports (3000 for Next.js, 5173/5174 for Vite)
    # Vercel default hostnames (hyphen vs no-hyphen) — also merge CORS_ORIGINS from env
    cors_origins = _merge_cors_origins_from_env(_cors_default_base_origins())

    # Private LAN origins when Vite uses --host 0.0.0.0 (e.g. http://10.0.0.148:5174).
    # Flask-CORS matches these regexes; OPTIONS preflight is handled separately in handle_preflight.
    _dev_private_lan_origin_patterns = [
        r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$",
        r"^http://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$",
        r"^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}(:\d+)?$",
    ]

    def get_cors_origins():
        # Cannot use '*' with supports_credentials=True; extend allowlist in dev only.
        if os.getenv("FLASK_ENV") == "development":
            return list(cors_origins) + _dev_private_lan_origin_patterns
        return cors_origins

    CORS(app, 
         resources={r"/api/*": {"origins": get_cors_origins()}},
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken', 'Accept', 'Cache-Control', 'Pragma', 'x-cache-version', 'x-deployment-timestamp', 'expires', 'x-correlation-id'],
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
                    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,X-CSRFToken,Accept,Cache-Control,Pragma,x-cache-version,x-deployment-timestamp,expires,x-correlation-id")
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
    # Gunicorn + threading does not support WebSocket upgrade; use gevent worker + async_mode
    # Render: SOCKETIO_ASYNC_MODE=gevent and gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker
    app.socketio = None
    try:
        from flask_socketio import SocketIO

        def _socketio_async_mode() -> str:
            if os.getenv('FLASK_ENV') == 'test':
                return 'threading'
            override = (os.getenv('SOCKETIO_ASYNC_MODE') or '').strip().lower()
            if override in ('threading', 'eventlet', 'gevent'):
                return override
            return 'threading'

        socketio_async_mode = _socketio_async_mode()
        if socketio_async_mode == 'eventlet':
            try:
                import eventlet  # noqa: F401
            except ImportError:
                logger.warning("eventlet not installed; SocketIO using threading (WebSockets may fail behind Gunicorn)")
                socketio_async_mode = 'threading'
        elif socketio_async_mode == 'gevent':
            try:
                import gevent  # noqa: F401
                import geventwebsocket  # noqa: F401
            except ImportError:
                logger.warning(
                    "gevent/gevent-websocket not installed; SocketIO using threading "
                    "(WebSockets may fail behind Gunicorn)"
                )
                socketio_async_mode = 'threading'
        
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
            async_mode=socketio_async_mode,
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

    # When SocketIO is not available, handle /socket.io/ explicitly to avoid
    # Werkzeug "write() before start_response" when frontend attempts WebSocket.
    if app.socketio is None:
        @app.route('/socket.io/', defaults={'path': ''})
        @app.route('/socket.io/<path:path>')
        def socketio_unavailable(path=''):
            return jsonify({
                'error': 'WebSocket support not available',
                'code': 'SOCKETIO_UNAVAILABLE'
            }), 503
    
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
    services = services  # satisfy F824: name is assigned (mutated below)
    
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

        # ✅ Security / session layers (get_jwt_manager() builds tables in JWTAuthManager.__init__)
        get_jwt_manager()
        init_flask_sessions(app)
        if callable(init_secure_sessions):
            init_secure_sessions(app)
        
        # Initialize request timeout middleware
        try:
            from core.request_timeout import init_request_timeout
            init_request_timeout(app)
            logger.info("✅ Request timeout middleware initialized")
        except Exception as e:
            logger.warning(f"⚠️ Request timeout middleware initialization failed: {e}")
        
        # Initialize trace context middleware
        try:
            from core.trace_context import init_trace_context
            init_trace_context(app)
            logger.info("✅ Trace context middleware initialized")
        except Exception as e:
            logger.warning(f"⚠️ Trace context middleware initialization failed: {e}")
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

    @app.route('/api/health/live')
    def api_health_live():
        """
        Liveness probe only: no database or Redis.
        Point Render healthCheckPath here — Render times out after 5s; /api/health can exceed
        that when SQLite is locked or Redis is slow to connect.
        """
        return jsonify({
            'status': 'ok',
            'service': 'fikiri-backend',
            'timestamp': datetime.now().isoformat(),
        }), 200

    @app.route('/api/health')
    def api_health_check():
        """
        Full readiness when called by browsers/monitors; fast liveness when probed by Render.
        Render often keeps Health Check Path on /api/health — UA is Render/1.0 (no DB/Redis).
        """
        ua = request.headers.get('User-Agent') or ''
        if 'Render/' in ua:
            return api_health_live()
        db_status = 'unknown'
        redis_status = 'unknown'
        try:
            from core.database_optimization import db_optimizer
            db_optimizer.execute_query('SELECT 1', fetch=False)
            db_status = 'connected'
        except Exception:
            db_status = 'disconnected'
        try:
            from core.redis_connection_helper import get_redis_client
            client = get_redis_client(decode_responses=True, db=0)
            if client and client.ping():
                redis_status = 'connected'
            else:
                redis_status = 'disconnected'
        except Exception:
            redis_status = 'disconnected'
        # Public contract: healthy | degraded | unhealthy (uptime monitors expect these)
        if db_status != 'connected':
            overall = 'unhealthy'
        elif redis_status != 'connected':
            overall = 'degraded'
        else:
            overall = 'healthy'
        return jsonify({
            'status': overall,
            'database': db_status,
            'redis': redis_status,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'message': 'Fikiri Solutions API is running',
            'service': 'fikiri-backend',
            'environment': os.getenv('FLASK_ENV', 'production')
        })

    @app.route('/api/errors', methods=['POST'])
    def ingest_client_error():
        """
        React ErrorBoundary client error reports (JSON). No auth; bounded payload; logs only.
        """
        max_bytes = 64 * 1024
        cl = request.content_length
        if cl is not None and cl > max_bytes:
            return jsonify({'ok': True}), 202
        raw = request.get_data(cache=True, as_text=True) or ''
        if len(raw.encode('utf-8', errors='replace')) > max_bytes:
            return jsonify({'ok': True}), 202
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except (json.JSONDecodeError, TypeError):
            return jsonify({'ok': True}), 202
        if not isinstance(payload, dict):
            return jsonify({'ok': True}), 202

        msg = str(payload.get('message') or '')[:500]
        url = str(payload.get('url') or '')[:500]
        ts = str(payload.get('timestamp') or '')[:80]
        uid = str(payload.get('userId') or '')[:64]
        stack = str(payload.get('stack') or '')[:4000]
        comp = str(payload.get('componentStack') or '')[:4000]
        ua = str(payload.get('userAgent') or '')[:300]

        logger.warning(
            "frontend_client_error | ts=%s url=%s user_ref=%s msg=%s",
            ts,
            url,
            uid,
            msg,
        )
        if stack or comp:
            logger.debug(
                "frontend_client_error stacks | stack=%s | componentStack=%s | ua=%s",
                stack[:2000],
                comp[:2000],
                ua,
            )
        return jsonify({'ok': True}), 200
    
    # Single limiter attached to app so exemptions apply
    if LIMITER_AVAILABLE and _app_limiter is not None:
        try:
            _app_limiter.init_app(app)
            _app_limiter.exempt(health_summary)
            _app_limiter.exempt(api_health_live)
            _app_limiter.exempt(api_health_check)
            _app_limiter.exempt(ingest_client_error)
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

    @app.route('/integrations/universal/fikiri-sdk.js')
    def serve_fikiri_universal_sdk():
        """Embed SDK for PublicChatbotWidget and external installs (same-origin or proxied)."""
        universal_dir = os.path.join(app.root_path, 'integrations', 'universal')
        return send_from_directory(
            universal_dir,
            'fikiri-sdk.js',
            mimetype='application/javascript',
            max_age=3600,
        )

    # Frontend routes
    @app.route('/dashboard')
    def dashboard():
        """Serve dashboard page"""
        return render_template('dashboard.html')
    
    # Demo routes
    @app.route('/demo/chatbot')
    def chatbot_demo():
        """Serve chatbot demo page"""
        try:
            demo_path = os.path.join(os.path.dirname(__file__), 'demo', 'chatbot-demo.html')
            if os.path.exists(demo_path):
                with open(demo_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return jsonify({'error': 'Demo file not found'}), 404
        except Exception as e:
            logger.error(f"Error serving demo: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/demo/simple')
    def simple_chatbot_demo():
        """Serve simple chatbot demo page"""
        try:
            demo_path = os.path.join(os.path.dirname(__file__), 'demo', 'simple-chatbot.html')
            if os.path.exists(demo_path):
                with open(demo_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return jsonify({'error': 'Demo file not found'}), 404
        except Exception as e:
            logger.error(f"Error serving demo: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/demo/widget')
    def chatbot_widget_demo():
        """Serve chatbot widget demo (floating button + popup)"""
        try:
            demo_path = os.path.join(os.path.dirname(__file__), 'demo', 'chatbot-widget.html')
            if os.path.exists(demo_path):
                with open(demo_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return jsonify({'error': 'Demo file not found'}), 404
        except Exception as e:
            logger.error(f"Error serving demo: {e}")
            return jsonify({'error': str(e)}), 500

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
        (migration_bp, 'migration'),
        (chatbot_bp, 'chatbot'),
        (public_chatbot_bp, 'public_chatbot'),
        (ai_analysis_bp, 'ai_analysis'),
        (workflow_templates_bp, 'workflow_templates'),
        (contact_bp, 'contact'),
        (monitoring_dashboard_bp, 'monitoring_dashboard'),
        (ai_bp, 'ai'),
        (dashboard_bp, 'dashboard'),
        (auth_bp, 'auth'),
        (business_bp, 'routes_business'),
        (jobs_bp, 'routes_jobs'),
        (test_bp, 'routes_test'),
        (user_bp, 'routes_user'),
        (monitoring_bp, 'routes_monitoring'),
        (expert_bp, 'routes_expert'),
        (kpi_bp, 'routes_kpi'),
        (integrations_bp, 'integrations'),
    ]

    if os.getenv("GOOGLE_RISC_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        blueprints.append((google_risc_bp, "google_risc"))
    
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

# Gunicorn WSGI target: must be the Flask application object.
# Flask-SocketIO 5.x: the SocketIO instance is NOT WSGI-callable (callable(socketio) is False), so gunicorn app:wsgi_app
# would raise "Application object must be callable". SocketIO attaches middleware via app.wsgi_app instead.
# Use: gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:$PORT app:wsgi_app
wsgi_app = app

# Dev-only routes (bypass auth/plan gating; not registered in production/staging)
if os.getenv('FLASK_ENV') == 'development':
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
        """Direct AI response endpoint for frontend (requires auth and respects AI budget)."""
        try:
            from core.secure_sessions import get_current_user_id
            from core.ai_budget_guardrails import ai_budget_guardrails
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Request body cannot be empty'}), 400
            message = data.get('message', '')
            if not message:
                return jsonify({'success': False, 'error': 'Message is required'}), 400
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            budget_decision = ai_budget_guardrails.evaluate(user_id, projected_increment=1)
            if not budget_decision.allowed:
                msg = ("AI monthly budget cap reached. Upgrade or wait until next billing period."
                       if budget_decision.reason == "monthly_budget_cap_reached"
                       else "AI monthly budget approval required.")
                return jsonify({'success': False, 'error': msg, 'error_code': 'AI_BUDGET_SOFT_STOP'}), 402
            try:
                from core.ai.llm_router import LLMRouter
                router = LLMRouter()
                if router and router.client and router.client.is_enabled():
                    hdr_cid = request.headers.get("X-Correlation-ID")
                    correlation_id = (
                        str(hdr_cid).strip() if hdr_cid and str(hdr_cid).strip() else str(uuid.uuid4())
                    )
                    llm_result = router.process(
                        input_data=message,
                        intent='general',
                        context={
                            'channel': 'ai_response_direct',
                            'source': 'ai_response_direct',
                            'user_id': user_id,
                            'correlation_id': correlation_id,
                        },
                    )
                    if llm_result.get('success'):
                        ai_budget_guardrails.record_ai_usage(user_id, 1)
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
        # Flask-SocketIO 5.6+ refuses to run Werkzeug in non-TTY environments unless
        # we explicitly allow it. Safe to allow only in development.
        app.socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=False,
            allow_unsafe_werkzeug=debug,
        )
    else:
        logger.info(f"🚀 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, use_reloader=False)
