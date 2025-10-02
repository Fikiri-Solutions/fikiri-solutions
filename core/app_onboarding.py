#!/usr/bin/env python3
"""
Onboarding Status API
Simple endpoints for checking sync progress and onboarding status
Based on proven polling patterns
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not available for status tracking")

status_bp = Blueprint("onboarding_status", __name__, url_prefix="/api/onboarding")

# Global Redis connection
redis_client = None

def init_redis():
    """Initialize Redis connection"""
    global redis_client
    if REDIS_AVAILABLE:
        try:
            import os
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                redis_client = Redis.from_url(redis_url, decode_responses=True)
                redis_client.ping()
                logger.info("✅ Onboarding status Redis connection established")
            else:
                logger.warning("⚠️ Redis URL not configured")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_client = None

# Initialize Redis on import
init_redis()

@status_bp.route("/status", methods=["GET"])
def onboarding_status():
    """Get onboarding sync status for user"""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id parameter required"}), 400
        
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "Invalid user_id"}), 400
        
        # Get progress from Redis
        prog_key = f"onboarding:{user_id}:progress"
        
        if redis_client:
            progress_data = redis_client.hgetall(prog_key)
            if progress_data:
                # Convert Redis bytes to strings if needed
                decoded_data = {}
                for key, value in progress_data.items():
                    if isinstance(key, bytes):
                        key = key.decode()
                    if isinstance(value, bytes):
                        value = value.decode()
                    decoded_data[key] = value
        
                logger.info(f"✅ Retrieved progress for user {user_id}: {decoded_data}")
                
                return jsonify({
                    "success": True,
                    "progress": decoded_data,
                    "message": "Progress retrieved successfully"
                })
            else:
                # No progress data found
                return jsonify({
                    "success": True,
                    "progress": {
                        "step": "none",
                        "pct": "0",
                        "total": "0",
                        "processed": "0",
                        "status": "not_started"
                    },
                    "message": "No sync in progress"
                })
        else:
            return jsonify({
                "success": False,
                "error": "Redis not available",
                "error_code": "REDIS_UNAVAILABLE"
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Failed to get onboarding status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_code": "STATUS_RETRIEVE_FAILED"
        }), 500

@status_bp.route("/reset", methods=["POST"])
def reset_onboarding_status():
    """Reset onboarding status for user (for testing)"""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id parameter required"}), 400
        
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "Invalid user_id"}), 400
        
        if redis_client:
            # Clear progress data
            prog_key = f"onboarding:{user_id}:progress"
            seen_key = f"seen:{user_id}"
            
            redis_client.delete(prog_key)
            redis_client.delete(seen_key)
            
            logger.info(f"✅ Reset onboarding status for user {user_id}")
            
            return jsonify({
                "success": True,
                "message": "Onboarding status reset successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Redis not available",
                "error_code": "REDIS_UNAVAILABLE"
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Failed to reset onboarding status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_code": "STATUS_RESET_FAILED"
        }), 500
