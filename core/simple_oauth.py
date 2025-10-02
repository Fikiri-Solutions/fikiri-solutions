#!/usr/bin/env python3
"""
Simple OAuth Blueprint - Minimal version for immediate deployment
Avoids complex dependencies to get OAuth working first
"""

from flask import Blueprint, request, jsonify, redirect, session
from urllib.parse import urlencode
import os
import secrets
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

oauth_simple = Blueprint("oauth_simple", __name__, url_prefix="/api/oauth")

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://fikirisolutions.onrender.com/api/oauth/gmail/callback")

# Gmail OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email", 
    "https://www.googleapis.com/auth/userinfo.profile"
]

@oauth_simple.route("/gmail/start", methods=["GET"])
def gmail_start_simple():
    """Start Gmail OAuth flow - simplified version"""
    try:
        logger.info("🔗 OAuth start requested")
        
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return jsonify({"error": "OAuth not configured"}), 500

        # Generate simple state for CSRF protection
        state = secrets.token_urlsafe(24)
        
        # Build authorization URL manually
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'scope': ' '.join(SCOPES),
            'response_type': 'code',
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'prompt': 'consent',
            'state': state
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/auth/chooser?{urlencode(params)}"
        
        logger.info(f"✅ Generated OAuth URL")
        return jsonify({"url": auth_url})

    except Exception as e:
        logger.error(f"❌ OAuth start failed: {e}")
        return jsonify({"error": f"OAuth start failed: {str(e)}"}), 500

@oauth_simple.route("/gmail/callback", methods=["GET"])
def gmail_callback_simple():
    """Handle Gmail OAuth callback - simplified version"""
    try:
        logger.info("🔗 OAuth callback received")
        
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")
        
        if error:
            logger.error(f"❌ OAuth error: {error}")
            return jsonify({"error": f"OAuth error: {error}"}), 400
            
        if not code:
            return jsonify({"error": "missing_code"}), 400

        logger.info(f"✅ Valid OAuth callback received")
        
        # For now, just return success
        # TODO: Exchange code for tokens when libraries are available
        
        # Redirect back to frontend
        frontend_url = "/onboarding-flow/sync"
        return redirect(frontend_url)

    except Exception as e:
        logger.error(f"❌ OAuth callback failed: {e}")
        return jsonify({"error": f"OAuth callback failed: {str(e)}"}), 500

@oauth_simple.route("/test", methods=["GET"])
def test_endpoint():
    """Test endpoint to verify blueprint is working"""
    return jsonify({
        "message": "OAuth blueprint is working!",
        "client_id_set": bool(GOOGLE_CLIENT_ID),
        "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": GOOGLE_REDIRECT_URI
    })
