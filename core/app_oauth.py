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
    logger.warning("Cryptography not available, tokens will be stored unencrypted")

# Try to import Google OAuth libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False
    logger.warning("Google OAuth libraries not available")

oauth = Blueprint("oauth", __name__, url_prefix="/api/oauth")

# Configuration - Google
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
DEFAULT_GOOGLE_REDIRECT_URI = "http://localhost:5000/api/oauth/gmail/callback"
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", DEFAULT_GOOGLE_REDIRECT_URI)

# Configuration - Microsoft/Outlook
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")  # 'common' for multi-tenant
DEFAULT_OUTLOOK_REDIRECT_URI = "http://localhost:5000/api/oauth/outlook/callback"
OUTLOOK_REDIRECT_URI = os.getenv("OUTLOOK_REDIRECT_URI", DEFAULT_OUTLOOK_REDIRECT_URI)

if not GOOGLE_REDIRECT_URI.startswith("http"):
    logger.warning(f"⚠️ Invalid GOOGLE_REDIRECT_URI '{GOOGLE_REDIRECT_URI}', falling back to default")
    GOOGLE_REDIRECT_URI = DEFAULT_GOOGLE_REDIRECT_URI

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
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # modify gives reply+labels; readonly if truly read-only
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# Outlook OAuth scopes (Microsoft Graph API)
OUTLOOK_SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "offline_access"  # Required for refresh tokens
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
            g.session_data['post_connect_redirect'] = request.args.get("redirect", "/onboarding-flow/2")

        # Always persist state in DB to survive missing/cleared sessions
        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO oauth_states 
            (state, user_id, provider, redirect_url, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            state, user_id or 0, 'gmail', 
            request.args.get("redirect", "/onboarding-flow/2"),
            int(time.time()) + 600,  # 10 minutes
            json.dumps({'oauth_state': state, 'onboarding': user_id is None, 'user_id': user_id})
        ), fetch=False)
        logger.info("🧪 OAuth state persisted (gmail) state=%s user_id=%s", state, user_id)

        # Use manual URL construction for full control over OAuth parameters
        # This ensures we send exactly what Google expects
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'scope': ' '.join(GMAIL_SCOPES),
            'response_type': 'code',
            'access_type': 'offline',
            'include_granted_scopes': 'true',  # Must be lowercase string 'true'
            'prompt': 'consent',
            'state': state
        }
        auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

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
        redirect_url = "/onboarding-flow/2"
        stored_user_id = None
        
        from flask import g
        if hasattr(g, 'session_data') and g.session_data:
            expected_state = g.session_data.get('oauth_state')
            redirect_url = g.session_data.get('post_connect_redirect', "/onboarding-flow/2")

        # Fallback: check database for OAuth state if session missing/empty
        if not expected_state:
            from core.database_optimization import db_optimizer
            state_data = db_optimizer.execute_query("""
                SELECT state, redirect_url, user_id, metadata FROM oauth_states 
                WHERE state = ? AND expires_at > ?
            """, (state, int(time.time())))
            
            if state_data:
                expected_state = state_data[0]['state']
                redirect_url = state_data[0]['redirect_url']
                stored_user_id = state_data[0].get('user_id')
                logger.info(
                    "🧪 OAuth state loaded (gmail) state=%s user_id=%s redirect=%s",
                    expected_state,
                    stored_user_id,
                    redirect_url,
                )
            else:
                logger.warning("🧪 OAuth state not found in DB (gmail) state=%s", state)
                # Also try to get user_id from metadata if stored there
                if not stored_user_id or stored_user_id == 0:
                    metadata_str = state_data[0].get('metadata', '{}')
                    try:
                        metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                        if metadata and 'user_id' in metadata:
                            stored_user_id = metadata.get('user_id')
                    except Exception as parse_error:
                        logger.debug("Failed to parse oauth state metadata: %s", parse_error)
        
        if not state or state != expected_state:
            logger.error(f"❌ State mismatch: {state} != {expected_state}")
            return jsonify({"error": "state_mismatch", "message": "Invalid or expired OAuth state. Please try connecting again."}), 400

        code = request.args.get("code")
        error = request.args.get("error")
        
        if error:
            logger.error(f"❌ OAuth error: {error}")
            return jsonify({"error": f"OAuth error: {error}"}), 400
            
        if not code:
            return jsonify({"error": "missing_code", "message": "Authorization code not provided"}), 400

        # Get user_id from secure session, or fall back to stored user_id from OAuth state
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        
        # If no session user_id, try to use stored user_id from OAuth state
        # Note: stored_user_id might be 0 if user wasn't logged in during OAuth start
        if not user_id:
            if stored_user_id and stored_user_id > 0:
                user_id = stored_user_id
                logger.info(f"📝 Using stored user_id {user_id} from OAuth state")
            else:
                logger.warning("⚠️ No user_id in session or OAuth state - will try to get from userinfo")
        
        # If still no user_id, try to get it from the token exchange (userinfo endpoint)
        if not user_id:
            logger.warning("⚠️ No user_id found in session or OAuth state. Attempting to get from token exchange...")
            # We'll handle this after token exchange

        logger.info(f"✅ Valid OAuth callback for user {user_id}")

        # Use manual token exchange for full control
        import requests
        
        # Log the redirect URI being used for debugging
        logger.info(f"🔍 Using redirect_uri: {GOOGLE_REDIRECT_URI}")
        logger.info(f"🔍 Client ID: {GOOGLE_CLIENT_ID[:20]}...")
        
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': GOOGLE_REDIRECT_URI
        }
        
        response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        token_response = response.json()
        
        if 'error' in token_response:
            error_code = token_response.get('error')
            error_description = token_response.get('error_description', 'Token exchange failed')
            
            logger.error(f"❌ Token exchange failed: {error_code} - {error_description}")
            logger.error(f"🔍 Redirect URI used: {GOOGLE_REDIRECT_URI}")
            logger.error(f"🔍 Code length: {len(code) if code else 0}")
            
            # Provide helpful error messages based on error type
            if error_code == 'invalid_grant':
                user_message = (
                    "The authorization code has expired or was already used. "
                    "Please try connecting your Gmail account again from the beginning."
                )
            elif error_code == 'redirect_uri_mismatch':
                user_message = (
                    f"Redirect URI mismatch. Expected: {GOOGLE_REDIRECT_URI}. "
                    "Please check your Google Cloud Console OAuth configuration."
                )
            else:
                user_message = f"OAuth error: {error_description}"
            
            return jsonify({
                "error": error_code,
                "message": user_message,
                "details": error_description
            }), 400
        
        # Extract tokens from response
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')
        expires_in = token_response.get('expires_in', 3600)
        
        # Validate that we got an access token
        if not access_token:
            logger.error(f"❌ No access_token in token response: {token_response}")
            return jsonify({
                "error": "no_access_token",
                "message": "Failed to get access token from Google. Please try again."
            }), 400
        
        # If we still don't have user_id, try to get it from userinfo endpoint
        if not user_id and access_token:
            try:
                userinfo_response = requests.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                if userinfo_response.status_code == 200:
                    userinfo = userinfo_response.json()
                    user_email = userinfo.get('email')
                    if user_email:
                        # Try to find user by email
                        from core.database_optimization import db_optimizer
                        user_data = db_optimizer.execute_query(
                            "SELECT id FROM users WHERE email = ? LIMIT 1",
                            (user_email,)
                        )
                        if user_data:
                            user_id = user_data[0]['id']
                            logger.info(f"✅ Found user_id {user_id} from email {user_email}")
            except Exception as e:
                logger.warning(f"⚠️ Could not get user_id from userinfo: {e}")
        
        # If still no user_id, we can't proceed
        if not user_id:
            logger.error("❌ No user_id available - cannot store tokens")
            return jsonify({
                "error": "no_user_session",
                "message": "Please sign in first, then connect your Gmail account."
            }), 400
        
        # Calculate expiry timestamp
        expiry_timestamp = int(time.time()) + expires_in
        
        # 2) Persist encrypted tokens
        try:
            encrypted_access_token = encrypt(access_token) if access_token else None
            encrypted_refresh_token = encrypt(refresh_token) if refresh_token else None
            
            if not encrypted_access_token:
                logger.error("❌ Failed to encrypt access_token")
                return jsonify({
                    "error": "encryption_failed",
                    "message": "Failed to encrypt access token. Please try again."
                }), 500
            
            payload = {
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token or "",
                "expiry": expiry_timestamp,
                "scopes": GMAIL_SCOPES,
                "tenant": "gmail"
            }
            
            # Store tokens in database using our existing system
            upsert_gmail_tokens(user_id=user_id, **payload)
            logger.info(f"✅ Successfully stored tokens for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to store tokens: {e}", exc_info=True)
            return jsonify({
                "error": "token_storage_failed",
                "message": f"Failed to store tokens: {str(e)}"
            }), 500

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
            # Get frontend URL from environment or default to localhost
            frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:5174')
            
            # Ensure redirect_url is a valid frontend route
            if redirect_url.startswith('http'):
                # Already a full URL
                frontend_url = redirect_url
            else:
                # Relative path - prepend frontend base URL
                redirect_path = redirect_url.lstrip('/')
                frontend_url = f"{frontend_base}/{redirect_path}"
            
            # Add success parameter to URL so frontend knows OAuth succeeded
            separator = '&' if '?' in frontend_url else '?'
            frontend_url_with_success = f"{frontend_url}{separator}oauth_success=true"
            
            logger.info(f"🔄 OAuth successful! Redirecting to frontend: {frontend_url_with_success}")
            logger.info(f"✅ Gmail tokens stored for user {user_id}")
            logger.info(f"📧 User can now access inbox at: {frontend_base}/inbox")
            
            # Redirect to frontend with success indicator
            return redirect(frontend_url_with_success)

    except Exception as e:
        logger.error(f"❌ OAuth callback failed: {e}")
        # If this is a browser redirect, redirect to frontend with error
        if request.headers.get('Accept', '').startswith('text/html'):
            frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:5174')
            error_url = f"{frontend_base}/integrations/gmail?oauth_error={urlencode({'error': str(e)})}"
            return redirect(error_url)
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
                SET access_token = '[encrypted]',
                    access_token_enc = ?, 
                    refresh_token = ?,
                    refresh_token_enc = ?, 
                    expiry_timestamp = ?, scopes_json = ?, 
                    updated_at = CURRENT_TIMESTAMP, is_active = TRUE
                WHERE user_id = ?
            """, (
                payload["access_token"],  # Already encrypted by encrypt()
                '[encrypted]' if payload.get("refresh_token") else None,  # Placeholder
                payload["refresh_token"],  # Already encrypted
                payload["expiry"],
                json.dumps(payload["scopes"]),
                user_id
            ), fetch=False)
        else:
            # Insert new tokens with encrypted storage
            # Note: access_token column is NOT NULL, so we provide a placeholder
            # The actual token is stored encrypted in access_token_enc
            db_optimizer.execute_query("""
                INSERT INTO gmail_tokens 
                (user_id, access_token, access_token_enc, refresh_token, refresh_token_enc, 
                 expiry_timestamp, scopes_json, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
            """, (
                user_id,
                '[encrypted]',  # Placeholder for NOT NULL constraint
                payload["access_token"],  # Already encrypted by encrypt()
                '[encrypted]' if payload.get("refresh_token") else None,  # Placeholder
                payload["refresh_token"],  # Already encrypted
                payload["expiry"], 
                json.dumps(payload["scopes"])
            ), fetch=False)
            
        logger.info(f"✅ Stored tokens for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store tokens: {e}")
        raise

# ============================================================================
# OUTLOOK OAUTH ROUTES
# ============================================================================

@oauth.route("/outlook/start", methods=["GET"])
def outlook_start():
    """Start Outlook OAuth flow with CSRF protection"""
    try:
        from core.secure_sessions import get_current_user_id
        user_id = get_current_user_id()
        
        if not user_id:
            logger.info("🔗 Outlook OAuth start without authenticated user (onboarding flow)")
            user_id = None

        if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
            return jsonify({"error": "Outlook OAuth not configured"}), 500

        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(24)
        
        # Store OAuth state
        from flask import g
        if hasattr(g, 'session_data') and g.session_data:
            g.session_data['oauth_state'] = state
            g.session_data['post_connect_redirect'] = request.args.get("redirect", "/onboarding-flow/2")

        from core.database_optimization import db_optimizer
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO oauth_states 
            (state, user_id, provider, redirect_url, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            state, user_id or 0, 'outlook', 
            request.args.get("redirect", "/onboarding-flow/2"),
            int(time.time()) + 600,  # 10 minutes
            json.dumps({'oauth_state': state, 'onboarding': user_id is None, 'user_id': user_id})
        ), fetch=False)

        # Microsoft OAuth 2.0 authorization URL
        auth_base = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0"
        params = {
            'client_id': MICROSOFT_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': OUTLOOK_REDIRECT_URI,
            'response_mode': 'query',
            'scope': ' '.join(OUTLOOK_SCOPES),
            'state': state,
            'prompt': 'consent'  # Force consent to get refresh token
        }
        auth_url = f"{auth_base}/authorize?{urlencode(params)}"

        logger.info(f"✅ Generated Outlook OAuth URL for user {user_id}")
        return jsonify({"url": auth_url})

    except Exception as e:
        logger.error(f"❌ Outlook OAuth start failed: {e}")
        return jsonify({"error": f"Outlook OAuth start failed: {str(e)}"}), 500

@oauth.route("/outlook/callback", methods=["GET"])
def outlook_callback():
    """Handle Outlook OAuth callback with CSRF validation"""
    try:
        # 1) CSRF check
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"❌ Outlook OAuth error: {error}")
            return jsonify({"error": f"Outlook OAuth error: {error}"}), 400
        
        if not code or not state:
            return jsonify({"error": "Missing code or state parameter"}), 400
        
        # Validate state
        from core.database_optimization import db_optimizer
        state_record = db_optimizer.execute_query("""
            SELECT user_id, provider, redirect_url, expires_at, metadata
            FROM oauth_states 
            WHERE state = ? AND provider = 'outlook' AND expires_at > ?
        """, (state, int(time.time())))
        
        if not state_record:
            logger.error(f"❌ Invalid or expired OAuth state: {state}")
            return jsonify({"error": "Invalid or expired OAuth state"}), 400
        
        state_data = state_record[0]
        user_id = state_data.get('user_id') or 0
        redirect_url = state_data.get('redirect_url', '/onboarding-flow/2')
        
        # Clean up state
        db_optimizer.execute_query("DELETE FROM oauth_states WHERE state = ?", (state,), fetch=False)
        
        # 2) Exchange code for tokens
        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        token_data = {
            'client_id': MICROSOFT_CLIENT_ID,
            'client_secret': MICROSOFT_CLIENT_SECRET,
            'code': code,
            'redirect_uri': OUTLOOK_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'scope': ' '.join(OUTLOOK_SCOPES)
        }
        
        import requests
        token_response = requests.post(token_url, data=token_data, timeout=30)
        
        if token_response.status_code != 200:
            error_data = token_response.json()
            error_code = error_data.get('error', 'token_exchange_failed')
            error_description = error_data.get('error_description', 'Token exchange failed')
            
            logger.error(f"❌ Outlook token exchange failed: {error_code} - {error_description}")
            return jsonify({
                "error": error_code,
                "message": f"Outlook OAuth error: {error_description}"
            }), 400
        
        # Extract tokens
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        refresh_token = token_json.get('refresh_token')
        expires_in = token_json.get('expires_in', 3600)
        
        if not access_token:
            return jsonify({"error": "No access token received"}), 400
        
        # Get user info to determine user_id if not set
        if not user_id or user_id == 0:
            user_info_response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                user_email = user_info.get('mail') or user_info.get('userPrincipalName')
                if user_email:
                    from core.user_auth import user_auth_manager
                    user = user_auth_manager.get_user_by_email(user_email)
                    if user:
                        user_id = user.id
        
        if not user_id or user_id == 0:
            return jsonify({"error": "Could not determine user ID"}), 400
        
        # 3) Store tokens
        expiry_timestamp = int(time.time()) + expires_in
        encrypted_access = encrypt(access_token)
        encrypted_refresh = encrypt(refresh_token) if refresh_token else None
        
        upsert_outlook_tokens(
            user_id=user_id,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expiry=expiry_timestamp,
            scopes=OUTLOOK_SCOPES,
            tenant_id=MICROSOFT_TENANT_ID
        )
        
        logger.info(f"✅ Outlook OAuth completed for user {user_id}")
        
        # 4) Redirect to frontend
        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:5174')
        if redirect_url.startswith('/'):
            frontend_url = f"{frontend_base}{redirect_url}"
        else:
            frontend_url = redirect_url
        
        separator = '&' if '?' in frontend_url else '?'
        frontend_url_with_success = f"{frontend_url}{separator}oauth_success=true"
        
        logger.info(f"🔄 Outlook OAuth successful! Redirecting to: {frontend_url_with_success}")
        return redirect(frontend_url_with_success)

    except Exception as e:
        logger.error(f"❌ Outlook OAuth callback failed: {e}")
        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:5174')
        error_url = f"{frontend_base}/integrations/outlook?oauth_error={urlencode({'error': str(e)})}"
        return redirect(error_url)

def upsert_outlook_tokens(user_id: int, access_token: str, refresh_token: Optional[str] = None, 
                         expiry: int = None, scopes: list = None, tenant_id: str = None):
    """Store Outlook tokens in database"""
    try:
        from core.database_optimization import db_optimizer
        
        # Check if tokens exist
        existing = db_optimizer.execute_query(
            "SELECT id FROM outlook_tokens WHERE user_id = ?",
            (user_id,)
        )
        
        if existing:
            # Update existing tokens
            db_optimizer.execute_query("""
                UPDATE outlook_tokens 
                SET access_token = '[encrypted]',
                    access_token_enc = ?, 
                    refresh_token = ?,
                    refresh_token_enc = ?, 
                    expiry_timestamp = ?, 
                    scopes_json = ?, 
                    tenant_id = ?,
                    updated_at = CURRENT_TIMESTAMP, 
                    is_active = TRUE
                WHERE user_id = ?
            """, (
                access_token,  # Already encrypted
                '[encrypted]' if refresh_token else None,
                refresh_token,  # Already encrypted
                expiry,
                json.dumps(scopes or []),
                tenant_id,
                user_id
            ), fetch=False)
        else:
            # Insert new tokens
            db_optimizer.execute_query("""
                INSERT INTO outlook_tokens 
                (user_id, access_token, access_token_enc, refresh_token, refresh_token_enc, 
                 expiry_timestamp, scopes_json, tenant_id, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
            """, (
                user_id,
                '[encrypted]',
                access_token,  # Already encrypted
                '[encrypted]' if refresh_token else None,
                refresh_token,  # Already encrypted
                expiry,
                json.dumps(scopes or []),
                tenant_id
            ), fetch=False)
            
        logger.info(f"✅ Stored Outlook tokens for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store Outlook tokens: {e}")
        raise
