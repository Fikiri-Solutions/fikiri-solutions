"""
Development-only smoke test routes for verifying fixes.
These routes should only be available in development mode.
"""

from flask import Blueprint, jsonify, request
import json
import os
from core.redis_cache import get_redis_client

# Create blueprint for dev tests
dev_tests_bp = Blueprint('dev_tests', __name__, url_prefix='/api/dev')

@dev_tests_bp.route('/redis-serialization-test', methods=['POST'])
def redis_serialization_test():
    """Test Redis dict serialization to ensure no raw dicts are written."""
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({"error": "Not available in production"}), 403
    
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return jsonify({"error": "Redis not available"}), 503
        
        # Test data with various types
        test_data = {
            "string": "test_value",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested_dict": {
                "key": "value",
                "nested_list": ["a", "b", "c"]
            },
            "null_value": None
        }
        
        # Write using json.dumps (correct way)
        redis_client.setex("dev_test:serialization", 60, json.dumps(test_data))
        
        # Read back and verify
        retrieved_data = redis_client.get("dev_test:serialization")
        if retrieved_data:
            parsed_data = json.loads(retrieved_data)
            
            # Verify data integrity
            if parsed_data == test_data:
                return jsonify({
                    "success": True,
                    "message": "Redis serialization working correctly",
                    "test_data": test_data,
                    "retrieved_data": parsed_data
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Data integrity check failed",
                    "expected": test_data,
                    "retrieved": parsed_data
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": "Failed to retrieve data from Redis"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Redis serialization test failed: {str(e)}"
        }), 500

@dev_tests_bp.route('/database-health-check', methods=['GET'])
def database_health_check():
    """Comprehensive database health check."""
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({"error": "Not available in production"}), 403
    
    try:
        from core.database_optimization import DatabaseOptimizer
        
        db_optimizer = DatabaseOptimizer()
        
        # Check critical tables exist
        tables_check = db_optimizer.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'query_performance_log', 'email_jobs', 'leads')
        """)
        
        table_names = [row[0] for row in tables_check]
        expected_tables = {'users', 'query_performance_log', 'email_jobs', 'leads'}
        missing_tables = expected_tables - set(table_names)
        
        # Check table row counts
        counts = {}
        for table in table_names:
            count_result = db_optimizer.execute_query(f"SELECT COUNT(*) FROM {table}")
            counts[table] = count_result[0][0] if count_result else 0
        
        # Check if database is ready for metrics
        ready_status = db_optimizer._ready
        
        return jsonify({
            "success": True,
            "database_ready": ready_status,
            "tables_found": table_names,
            "missing_tables": list(missing_tables),
            "row_counts": counts,
            "all_critical_tables_present": len(missing_tables) == 0
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Database health check failed: {str(e)}"
        }), 500

@dev_tests_bp.route('/jwt-stability-test', methods=['POST'])
def jwt_stability_test():
    """Test JWT token stability across restarts."""
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({"error": "Not available in production"}), 403
    
    try:
        from core.jwt_auth import JWTManager
        
        jwt_manager = JWTManager()
        
        # Create a test token
        test_payload = {
            "user_id": 999,
            "email": "test@example.com",
            "role": "user"
        }
        
        token = jwt_manager.create_access_token(test_payload)
        
        # Verify token immediately
        decoded = jwt_manager.verify_token(token)
        
        return jsonify({
            "success": True,
            "message": "JWT token created and verified successfully",
            "token_created": bool(token),
            "token_verified": bool(decoded),
            "payload": decoded if decoded else None,
            "jwt_secret_configured": bool(os.getenv('JWT_SECRET_KEY'))
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"JWT stability test failed: {str(e)}"
        }), 500

@dev_tests_bp.route('/metrics-recording-test', methods=['POST'])
def metrics_recording_test():
    """Test metrics recording without recursion."""
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({"error": "Not available in production"}), 403
    
    try:
        from core.database_optimization import DatabaseOptimizer
        
        db_optimizer = DatabaseOptimizer()
        
        # Test a simple query that should trigger metrics recording
        test_query = "SELECT 1 as test_value"
        result = db_optimizer.execute_query(test_query)
        
        # Check if metrics were recorded
        metrics_check = db_optimizer.execute_query("""
            SELECT COUNT(*) FROM query_performance_log 
            WHERE query_text LIKE '%test_value%'
        """)
        
        metrics_count = metrics_check[0][0] if metrics_check else 0
        
        return jsonify({
            "success": True,
            "message": "Metrics recording test completed",
            "query_result": result[0][0] if result else None,
            "metrics_recorded": metrics_count > 0,
            "metrics_count": metrics_count,
            "database_ready": db_optimizer._ready
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Metrics recording test failed: {str(e)}"
        }), 500
