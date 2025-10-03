#!/usr/bin/env python3
"""
Flask OAuth Blueprint with Proven Patterns
Implements reliable OAuth flow with CSRF protection and encrypted token storage
Based on production-proven patterns
"""

from flask import Blueprint, request, jsonify, redirect, session, url_for
from urllib.parse import urlencode
import os
import secrets
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import cryptography for token encryption
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("⚠️ Cryptography not available, tokens will be stored unencrypted")

# Try to import Google OAuth libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False
    print("⚠️ Google OAuth libraries not available")

oauth = Blueprint("oauth", __name__, url_prefix="/api/oauth")

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://fikirisolutions.com/api/oauth/gmail/callback")
FERNET_KEY = os.getenv("FERNET_KEY")

# Initialize encryption if available
if CRYPTOGRAPHY_AVAILABLE and FERNET_KEY:
    try:
        fernet = Fernet(FERNET_KEY.encode())
        ENCRYPTION_ENABLED = True
        logger.info("✅ Token encryption enabled")
    except Exception as e:
        logger.error(f"❌ Failed to initialize encryption: {e}")
        ENCRYPTION_ENABLED = False
        fernet = None
else:
    ENCRYPTION_ENABLED = False
    fernet = None
    logger.warning("⚠️ Token encryption disabled (missing cryptography or FERNET_KEY)")

# Gmail OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # modify gives reply+labels; readonly if truly read-only
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

def encrypt(s: str) -> str:
    """Encrypt string for storage"""
    if ENCRYPTION_ENABLED and fernet:
        return fernet.encrypt(s.encode()).decode()
    else:
        # Fallback to base64 encoding for development
        import base64
        return base64.b64encode(s.encode()).decode()

def decrypt(s: str) -> str:
    """Decrypt string from storage"""
    if ENCRYPTION_ENABLED and fernet:
        return fernet.decrypt(s.encode()).decode()
    else:
        # Fallback to base64 decoding for development
        import base64
        return base64.b64decode(s.encode()).decode()

@oauth.route("/gmail/start", methods=["GET"])
def gmail_start():
    """Start Gmail OAuth flow with CSRF protection"""
    try:
        # Get user_id from secure session (optional for onboarding)
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        
        # Allow bypass for onboarding flow - user_id will be handled in callback
        if not user_id:
            logger.info("🔗 OAuth start without authenticated user (onboarding flow)")
            user_id = None

        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return jsonify({"error": "OAuth not configured"}), 500

        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(24)
        
        # Store OAuth state in secure session data
        from flask import g
        if hasattr(g, 'session_data') and g.session_data:
            g.session_data['oauth_state'] = state
            g.session_data['post_connect_redirect'] = request.args.get("redirect", "/onboarding/sync")
        else:
            # Fallback to database for OAuth state storage
            from core.database_optimization import db_optimizer
            db_optimizer.execute_query("""
                INSERT OR REPLACE INTO oauth_states 
                (state, user_id, provider, redirect_url, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state, user_id or 0, 'gmail', 
                request.args.get("redirect", "/onboarding"),
                int(time.time()) + 600,  # 10 minutes
                json.dumps({'oauth_state': state, 'onboarding': user_id is None})
            ), fetch=False)

        if GOOGLE_OAUTH_AVAILABLE:
            # Use google-auth-oauthlib for production-grade OAuth
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "redirect_uris": [GOOGLE_REDIRECT_URI],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=SCOPES,
            )
            flow.redirect_uri = GOOGLE_REDIRECT_URI
            auth_url, _ = flow.authorization_url(
                access_type="offline",     # refresh token
                include_granted_scopes=True,
                prompt="consent",          # ensure refresh token the first time
                state=state                # CSRF + navigate post callback
            )
        else:
            # Fallback manual URL construction
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

        logger.info(f"✅ Generated OAuth URL for user {user_id}")
        return jsonify({"url": auth_url})

    except Exception as e:
        logger.error(f"❌ OAuth start failed: {e}")
        return jsonify({"error": f"OAuth start failed: {str(e)}"}), 500

@oauth.route("/gmail/callback", methods=["GET"])
def gmail_callback():
    """Handle Gmail OAuth callback with CSRF validation"""
    try:
        # 1) CSRF check
        state = request.args.get("state")
        
        # Get expected state from secure session or database
        expected_state = None
        redirect_url = "/onboarding/sync"
        
        from flask import g
        if hasattr(g, 'session_data') and g.session_data:
            expected_state = g.session_data.get('oauth_state')
            redirect_url = g.session_data.get('post_connect_redirect', "/onboarding/sync")
        else:
            # Fallback: check database for OAuth state
            from core.database_optimization import db_optimizer
            state_data = db_optimizer.execute_query("""
                SELECT state, redirect_url FROM oauth_states 
                WHERE state = ? AND expires_at > ?
            """, (state, int(time.time())))
            
            if state_data:
                expected_state = state_data[0]['state']
                redirect_url = state_data[0]['redirect_url']
        
        if not state or state != expected_state:
            logger.error(f"❌ State mismatch: {state} != {expected_state}")
            return jsonify({"error": "state_mismatch"}), 400

        code = request.args.get("code")
        error = request.args.get("error")
        
        if error:
            logger.error(f"❌ OAuth error: {error}")
            return jsonify({"error": f"OAuth error: {error}"}), 400
            
        if not code:
            return jsonify({"error": "missing_code"}), 400

        # Get user_id from secure session
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({"error": "no_user_session"}), 400

        logger.info(f"✅ Valid OAuth callback for user {user_id}")

        if GOOGLE_OAUTH_AVAILABLE:
            # Use google-auth-oauthlib for token exchange
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "redirect_uris": [GOOGLE_REDIRECT_URI],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=SCOPES
            )
            flow.redirect_uri = GOOGLE_REDIRECT_URI
            flow.fetch_token(code=code)
            creds = flow.credentials  # google.oauth2.credentials.Credentials

            # 2) Persist encrypted tokens
            payload = {
                "access_token": encrypt(creds.token),
                "refresh_token": encrypt(creds.refresh_token or ""),
                "expiry": int(creds.expiry.timestamp()) if creds.expiry else 0,
                "scopes": creds.scopes,
                "tenant": "gmail"
            }
            
            # Store tokens in database using our existing system
            upsert_gmail_tokens(user_id=user_id, **payload)

            # 3) Kick off first sync (RQ)
            try:
                from core.onboarding_jobs import onboarding_job_manager
                result = onboarding_job_manager.queue_first_sync_job(user_id)
                job_id = result.get('job_id')
                job = type('MockJob', (), {'id': job_id}) if job_id else None
                logger.info(f"✅ Queued first sync job {job_id} for user {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to queue sync job: {e}")
                job = None

            # Clean up session state and database
            if hasattr(g, 'session_data') and g.session_data:
                g.session_data.pop("oauth_state", None)
                g.session_data.pop("post_connect_redirect", None)
            
            # For API calls, return JSON response
            if request.headers.get('Accept', '').find('application/json') != -1:
                return jsonify({
                    'success': True,
                    'message': 'Google OAuth completed successfully',
                    'redirect_url': redirect_url,
                    'job_id': job.id if job and hasattr(job, 'id') else job_id
                })
            else:
                # For browser redirects, redirect to the frontend
                frontend_url = f"/{redirect_url.lstrip('/')}"
                return redirect(frontend_url)

        else:
            return jsonify({"error": "Google OAuth libraries not available"}), 500

    except Exception as e:
        logger.error(f"❌ OAuth callback failed: {e}")
        return jsonify({"error": f"OAuth callback failed: {str(e)}"}), 500

def upsert_gmail_tokens(user_id: int, **payload):
    """Store Gmail tokens in database"""
    try:
        from core.database_optimization import db_optimizer
        
        # Check if tokens exist for this user
        existing = db_optimizer.execute_query(
            "SELECT id FROM gmail_tokens WHERE user_id = ?",
            (user_id,)
        )
        
        if existing:
            # Update existing tokens with encrypted storage
            db_optimizer.execute_query("""
                UPDATE gmail_tokens 
                SET access_token_enc = ?, refresh_token_enc = ?, 
                    expiry_timestamp = ?, scopes_json = ?, 
                    updated_at = CURRENT_TIMESTAMP, is_active = TRUE
                WHERE user_id = ?
            """, (
                payload["access_token"],  # Already encrypted by encrypt()
                payload["refresh_token"], 
                payload["expiry"],
                json.dumps(payload["scopes"]),
                user_id
            ), fetch=False)
        else:
            # Insert new tokens with encrypted storage
            db_optimizer.execute_query("""
                INSERT INTO gmail_tokens 
                (user_id, access_token_enc, refresh_token_enc, expiry_timestamp, 
                 scopes_json, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
            """, (
                user_id,
                payload["access_token"],  # Already encrypted by encrypt()
                payload["refresh_token"],
                payload["expiry"], 
                json.dumps(payload["scopes"])
            ), fetch=False)
            
        logger.info(f"✅ Stored tokens for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store tokens: {e}")
        raise
