"""
Backend Excellence Enhancements
API versioning, async operations, and connection pooling for Fikiri Solutions
"""

from flask import Blueprint, request, jsonify
import asyncio
import aiohttp
from functools import wraps
import time
import logging
from typing import Dict, Any, Optional, List
import threading
from concurrent.futures import ThreadPoolExecutor
try:
    import psycopg2
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================================
# API VERSIONING SYSTEM
# ============================================================================

class APIVersion:
    """API version management"""
    
    SUPPORTED_VERSIONS = ['v1', 'v2']
    DEFAULT_VERSION = 'v1'
    CURRENT_VERSION = 'v2'
    
    @staticmethod
    def get_version_from_header():
        """Extract API version from request headers"""
        version = request.headers.get('API-Version', APIVersion.DEFAULT_VERSION)
        if version not in APIVersion.SUPPORTED_VERSIONS:
            version = APIVersion.DEFAULT_VERSION
        return version
    
    @staticmethod
    def get_version_from_url():
        """Extract API version from URL path"""
        path_parts = request.path.split('/')
        if len(path_parts) > 2 and path_parts[2].startswith('v'):
            return path_parts[2]
        return APIVersion.DEFAULT_VERSION

def api_version(version: str):
    """Decorator for API versioning"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if this endpoint supports the requested version
            requested_version = APIVersion.get_version_from_header()
            if requested_version != version:
                return jsonify({
                    'success': False,
                    'error': f'API version {requested_version} not supported for this endpoint',
                    'supported_version': version,
                    'code': 'UNSUPPORTED_API_VERSION'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# ASYNC OPERATIONS SYSTEM
# ============================================================================

class AsyncOperationManager:
    """Manage async operations and background tasks"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks: Dict[str, Any] = {}
        self.task_results: Dict[str, Any] = {}
    
    def submit_task(self, task_id: str, func, *args, **kwargs):
        """Submit a task for async execution"""
        future = self.executor.submit(func, *args, **kwargs)
        self.running_tasks[task_id] = future
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a running task"""
        if task_id not in self.running_tasks:
            return {'status': 'not_found'}
        
        future = self.running_tasks[task_id]
        
        if future.done():
            try:
                result = future.result()
                self.task_results[task_id] = result
                del self.running_tasks[task_id]
                return {
                    'status': 'completed',
                    'result': result
                }
            except Exception as e:
                del self.running_tasks[task_id]
                return {
                    'status': 'failed',
                    'error': str(e)
                }
        else:
            return {'status': 'running'}
    
    def get_task_result(self, task_id: str) -> Any:
        """Get the result of a completed task"""
        return self.task_results.get(task_id)

# Global async operation manager
async_manager = AsyncOperationManager()

def async_operation(operation_name: str):
    """Decorator for async operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            task_id = f"{operation_name}_{int(time.time())}"
            task_id = async_manager.submit_task(task_id, f, *args, **kwargs)
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': f'{operation_name} started',
                'status_endpoint': f'/api/tasks/{task_id}'
            })
        return decorated_function
    return decorator

# ============================================================================
# CONNECTION POOLING SYSTEM
# ============================================================================

class DatabaseConnectionPool:
    """Database connection pooling for optimal performance"""
    
    def __init__(self, min_connections: int = 2, max_connections: int = 20):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            # For SQLite (development)
            if not hasattr(self, 'pool') or self.pool is None:
                # Create a simple connection pool for SQLite
                self.connections = []
                self.lock = threading.Lock()
                logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
    
    def get_connection(self):
        """Get a connection from the pool"""
        with self.lock:
            if self.connections:
                return self.connections.pop()
            else:
                # Create new connection
                return self._create_connection()
    
    def return_connection(self, connection):
        """Return a connection to the pool"""
        with self.lock:
            if len(self.connections) < self.max_connections:
                self.connections.append(connection)
            else:
                # Close excess connections
                connection.close()
    
    def _create_connection(self):
        """Create a new database connection"""
        # This would be implemented based on your database choice
        # For now, return a mock connection
        return MockConnection()
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()

class MockConnection:
    """Mock database connection for development"""
    def __init__(self):
        self.closed = False
    
    def close(self):
        self.closed = True
    
    def execute(self, query, params=None):
        # Mock query execution
        return MockResult()

class MockResult:
    """Mock query result"""
    def fetchall(self):
        return []
    
    def fetchone(self):
        return None

# Global connection pool
db_pool = DatabaseConnectionPool()

# ============================================================================
# REDIS CACHING SYSTEM
# ============================================================================

class CacheManager:
    """Redis-based caching system"""
    
    def __init__(self, host: str = None, port: int = None, db: int = None):
        if REDIS_AVAILABLE:
            try:
                # Use configuration system for Redis connection
                from core.minimal_config import get_config
                config = get_config()
                
                # Use provided parameters or fall back to config
                redis_host = host or config.redis_host
                redis_port = port or config.redis_port
                redis_db = db or config.redis_db
                redis_password = config.redis_password
                
                # Connect using config parameters
                if config.redis_url:
                    self.redis_client = redis.from_url(
                        config.redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                else:
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        db=redis_db,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                
                self.redis_client.ping()  # Test connection
                self.enabled = True
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.enabled = False
                self.memory_cache = {}
        else:
            logger.warning("Redis not installed, using in-memory cache")
            self.enabled = False
            self.memory_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.enabled:
                value = self.redis_client.get(key)
                return value if value else None
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            if self.enabled:
                return self.redis_client.setex(key, ttl, str(value))
            else:
                self.memory_cache[key] = value
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.enabled:
                return bool(self.redis_client.delete(key))
            else:
                return self.memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            if self.enabled:
                return self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

# Global cache manager
cache_manager = CacheManager()

def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {cache_key}")
            
            return result
        return decorated_function
    return decorator

# ============================================================================
# BACKGROUND TASK SYSTEM
# ============================================================================

class BackgroundTaskManager:
    """Manage background tasks and scheduled jobs"""
    
    def __init__(self):
        self.tasks: Dict[str, Any] = {}
        self.scheduled_tasks: Dict[str, Any] = {}
    
    def schedule_task(self, task_id: str, func, delay: int, *args, **kwargs):
        """Schedule a task to run after delay seconds"""
        def delayed_task():
            time.sleep(delay)
            try:
                result = func(*args, **kwargs)
                self.tasks[task_id] = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': time.time()
                }
            except Exception as e:
                self.tasks[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'completed_at': time.time()
                }
        
        thread = threading.Thread(target=delayed_task, daemon=True)
        thread.start()
        
        self.scheduled_tasks[task_id] = {
            'status': 'scheduled',
            'scheduled_at': time.time(),
            'delay': delay
        }
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a background task"""
        if task_id in self.tasks:
            return self.tasks[task_id]
        elif task_id in self.scheduled_tasks:
            return self.scheduled_tasks[task_id]
        else:
            return {'status': 'not_found'}

# Global background task manager
background_tasks = BackgroundTaskManager()

# ============================================================================
# PERFORMANCE OPTIMIZATION UTILITIES
# ============================================================================

def optimize_query(query: str, params: Dict[str, Any] = None) -> str:
    """Optimize database queries"""
    # Add query optimization logic here
    # For now, just return the query as-is
    return query

def batch_operations(operations: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """Split operations into batches for optimal processing"""
    batches = []
    for i in range(0, len(operations), batch_size):
        batches.append(operations[i:i + batch_size])
    return batches

def rate_limit(max_requests: int = 100, window: int = 3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple rate limiting implementation
            # In production, use Redis or similar for distributed rate limiting
            client_ip = request.remote_addr
            cache_key = f"rate_limit:{client_ip}:{f.__name__}"
            
            current_requests = cache_manager.get(cache_key) or 0
            if int(current_requests) >= max_requests:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }), 429
            
            # Increment counter
            cache_manager.set(cache_key, int(current_requests) + 1, window)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# API BLUEPRINT FOR VERSIONED ENDPOINTS
# ============================================================================

def create_api_blueprint(version: str) -> Blueprint:
    """Create a versioned API blueprint"""
    blueprint = Blueprint(f'api_{version}', f'/api/{version}')
    
    @blueprint.route('/status', methods=['GET'])
    def api_status():
        """Versioned status endpoint"""
        return jsonify({
            'success': True,
            'version': version,
            'status': 'healthy',
            'timestamp': time.time()
        })
    
    @blueprint.route('/tasks/<task_id>', methods=['GET'])
    def get_task_status(task_id: str):
        """Get async task status"""
        status = async_manager.get_task_status(task_id)
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': status
        })
    
    @blueprint.route('/cache/clear', methods=['POST'])
    def clear_cache():
        """Clear application cache"""
        success = cache_manager.clear()
        return jsonify({
            'success': success,
            'message': 'Cache cleared successfully' if success else 'Failed to clear cache'
        })
    
    return blueprint

# Export the enhanced systems
__all__ = [
    'APIVersion', 'api_version', 'async_manager', 'async_operation',
    'db_pool', 'cache_manager', 'cached', 'background_tasks',
    'rate_limit', 'create_api_blueprint'
]
