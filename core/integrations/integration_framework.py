#!/usr/bin/env python3
"""
Unified Integration Framework
Provider-agnostic integration system for Calendar, CRM, Payments, etc.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from core.database_optimization import db_optimizer

# Token encryption
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
TOKEN_REFRESH_BUFFER_MINUTES = 2  # Refresh token 2 minutes before expiry
OAUTH_STATE_EXPIRY_MINUTES = 10  # OAuth state expires in 10 minutes
DEFAULT_TOKEN_EXPIRY_SECONDS = 3600  # Default token expiry (1 hour)

# Initialize encryption
FERNET_KEY = os.getenv("FERNET_KEY")
if CRYPTOGRAPHY_AVAILABLE and FERNET_KEY:
    try:
        fernet = Fernet(FERNET_KEY.encode())
        ENCRYPTION_ENABLED = True
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        ENCRYPTION_ENABLED = False
        fernet = None
else:
    ENCRYPTION_ENABLED = False
    fernet = None

def encrypt_token(token: str) -> str:
    """Encrypt token for storage - FAILS CLOSED if encryption unavailable"""
    if not ENCRYPTION_ENABLED or not fernet:
        error_msg = "Token encryption unavailable: FERNET_KEY not configured. Set FERNET_KEY to enable integrations."
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt token from storage - FAILS CLOSED if encryption unavailable"""
    if not ENCRYPTION_ENABLED or not fernet:
        error_msg = "Token decryption unavailable: FERNET_KEY not configured. Set FERNET_KEY to enable integrations."
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    return fernet.decrypt(encrypted_token.encode()).decode()


class IntegrationProvider(ABC):
    """Base class for integration providers"""
    
    @abstractmethod
    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        """Generate OAuth authorization URL"""
        pass
    
    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        pass
    
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token"""
        pass
    
    @abstractmethod
    def revoke_token(self, access_token: str) -> bool:
        """Revoke access token"""
        pass


class IntegrationManager:
    """Unified integration manager for all providers"""
    
    def __init__(self):
        self._initialize_tables()
        self._providers: Dict[str, IntegrationProvider] = {}
    
    def _initialize_tables(self):
        """Create integration framework tables"""
        # Unified integrations table
        db_optimizer.execute_query("""
            CREATE TABLE IF NOT EXISTS integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                scopes TEXT,
                meta_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, provider),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """, fetch=False)
        
        # Integration tokens (encrypted) - one row per integration
        # expires_at: INTEGER (epoch seconds) for consistency with oauth_states
        db_optimizer.execute_query("""
            CREATE TABLE IF NOT EXISTS integration_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_id INTEGER NOT NULL UNIQUE,
                access_token_enc TEXT NOT NULL,
                refresh_token_enc TEXT,
                expires_at INTEGER,  -- Epoch seconds (consistent with oauth_states)
                token_type TEXT DEFAULT 'Bearer',
                enc_version INTEGER DEFAULT 1,  -- Encryption version for key rotation
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (integration_id) REFERENCES integrations(id) ON DELETE CASCADE
            )
        """, fetch=False)
        
        # Integration sync state - one row per integration+resource
        db_optimizer.execute_query("""
            CREATE TABLE IF NOT EXISTS integration_sync_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_id INTEGER NOT NULL,
                resource TEXT NOT NULL,
                cursor TEXT,
                last_synced_at TIMESTAMP,
                status TEXT DEFAULT 'idle',  -- idle, refreshing, error (operational state, NOT product state)
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (integration_id) REFERENCES integrations(id) ON DELETE CASCADE,
                UNIQUE(integration_id, resource)
            )
        """, fetch=False)
        
        # Calendar event links (maps internal entities to external events)
        db_optimizer.execute_query("""
            CREATE TABLE IF NOT EXISTS calendar_event_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                integration_id INTEGER NOT NULL,
                internal_entity_type TEXT NOT NULL,
                internal_entity_id INTEGER NOT NULL,
                external_event_id TEXT NOT NULL,
                external_calendar_id TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(integration_id, external_event_id),
                UNIQUE(user_id, internal_entity_type, internal_entity_id, integration_id),
                FOREIGN KEY (integration_id) REFERENCES integrations(id) ON DELETE CASCADE
            )
        """, fetch=False)
        
        # Create indexes for performance
        db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_integrations_user_provider 
            ON integrations(user_id, provider)
        """, fetch=False)
        
        db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_integration_tokens_integration 
            ON integration_tokens(integration_id)
        """, fetch=False)
        
        db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_calendar_links_entity 
            ON calendar_event_links(user_id, internal_entity_type, internal_entity_id)
        """, fetch=False)
        
        db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_calendar_links_integration_event 
            ON calendar_event_links(integration_id, external_event_id)
        """, fetch=False)
        
        db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_sync_state_integration_resource 
            ON integration_sync_state(integration_id, resource)
        """, fetch=False)
        
        logger.info("✅ Integration framework tables initialized")
    
    def register_provider(self, provider_name: str, provider: IntegrationProvider):
        """Register an integration provider"""
        self._providers[provider_name] = provider
        logger.info(f"✅ Registered integration provider: {provider_name}")
    
    def get_integration(self, user_id: int, provider: str) -> Optional[Dict]:
        """Get integration record"""
        result = db_optimizer.execute_query(
            "SELECT * FROM integrations WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        )
        return result[0] if result else None
    
    def get_integration_tokens(self, integration_id: int) -> Optional[Dict]:
        """Get decrypted tokens for integration (UNIQUE constraint ensures one row)"""
        result = db_optimizer.execute_query(
            "SELECT * FROM integration_tokens WHERE integration_id = ?",
            (integration_id,)
        )
        if not result:
            return None
        
        token_data = result[0]
        try:
            # expires_at is stored as epoch seconds (INTEGER), return as int
            expires_at = token_data.get('expires_at')
            if expires_at and isinstance(expires_at, str):
                # Handle legacy timestamp strings (migration support)
                try:
                    expires_at = int(datetime.fromisoformat(expires_at).timestamp())
                except (ValueError, TypeError):
                    expires_at = None
            
            return {
                'access_token': decrypt_token(token_data['access_token_enc']),
                'refresh_token': decrypt_token(token_data['refresh_token_enc']) if token_data.get('refresh_token_enc') else None,
                'expires_at': expires_at,  # Epoch seconds (int)
                'token_type': token_data.get('token_type', 'Bearer'),
                'enc_version': token_data.get('enc_version', 1)
            }
        except Exception as e:
            logger.error(f"Failed to decrypt tokens for integration {integration_id}: {e}")
            return None
    
    def connect(self, user_id: int, provider: str, token_data: Dict[str, Any], 
                scopes: List[str] = None, meta: Dict[str, Any] = None) -> Dict:
        """Store integration connection"""
        try:
            # Check if integration exists
            existing = self.get_integration(user_id, provider)
            
            if existing:
                integration_id = existing['id']
                # Update integration (ensure token_enc_version in meta)
                meta_dict = json.loads(meta) if isinstance(meta, str) else (meta or {})
                if 'token_enc_version' not in meta_dict:
                    # Preserve existing version or default to 1
                    existing_meta = json.loads(existing.get('meta_json') or '{}')
                    meta_dict['token_enc_version'] = existing_meta.get('token_enc_version', 1)
                
                db_optimizer.execute_query("""
                    UPDATE integrations 
                    SET status = 'active', scopes = ?, meta_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(scopes or []), json.dumps(meta_dict), integration_id), fetch=False)
                
                # Ensure sync state row exists (for reconnection)
                db_optimizer.execute_query("""
                    INSERT OR IGNORE INTO integration_sync_state
                    (integration_id, resource, status, updated_at)
                    VALUES (?, 'token_refresh', 'idle', CURRENT_TIMESTAMP)
                """, (integration_id,), fetch=False)
            else:
                # Create new integration
                # Ensure token_enc_version is in meta for key rotation
                meta_dict = json.loads(meta) if isinstance(meta, str) else (meta or {})
                if 'token_enc_version' not in meta_dict:
                    meta_dict['token_enc_version'] = 1
                
                integration_id = db_optimizer.execute_query("""
                    INSERT INTO integrations (user_id, provider, status, scopes, meta_json)
                    VALUES (?, ?, 'active', ?, ?)
                """, (user_id, provider, json.dumps(scopes or []), json.dumps(meta_dict)), fetch=False)
                
                # Initialize sync state for token refresh (ensure row exists)
                db_optimizer.execute_query("""
                    INSERT OR IGNORE INTO integration_sync_state
                    (integration_id, resource, status, updated_at)
                    VALUES (?, 'token_refresh', 'idle', CURRENT_TIMESTAMP)
                """, (integration_id,), fetch=False)
            
            # Store encrypted tokens
            if not token_data.get('access_token'):
                raise ValueError("access_token is required in token_data")
            
            access_token_enc = encrypt_token(token_data['access_token'])
            refresh_token_enc = None
            if token_data.get('refresh_token'):
                refresh_token_enc = encrypt_token(token_data['refresh_token'])
            
            # Normalize expires_at to epoch seconds (INTEGER)
            expires_at_epoch = None
            if token_data.get('expires_in'):
                expires_at_epoch = int((datetime.now() + timedelta(seconds=token_data['expires_in'])).timestamp())
            elif token_data.get('expires_at'):
                expires_at = token_data['expires_at']
                if isinstance(expires_at, datetime):
                    expires_at_epoch = int(expires_at.timestamp())
                elif isinstance(expires_at, str):
                    expires_at_epoch = int(datetime.fromisoformat(expires_at).timestamp())
                elif isinstance(expires_at, (int, float)):
                    expires_at_epoch = int(expires_at)
            
            # Get encryption version from meta or default to 1
            enc_version = 1
            if meta:
                meta_dict = json.loads(meta) if isinstance(meta, str) else meta
                enc_version = meta_dict.get('token_enc_version', 1)
            
            # Store tokens (INSERT OR REPLACE for UNIQUE constraint)
            db_optimizer.execute_query("""
                INSERT OR REPLACE INTO integration_tokens 
                (integration_id, access_token_enc, refresh_token_enc, expires_at, token_type, enc_version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                integration_id,
                access_token_enc,
                refresh_token_enc,
                expires_at_epoch,
                token_data.get('token_type', 'Bearer'),
                enc_version
            ), fetch=False)
            
            logger.info(f"✅ Connected {provider} for user {user_id}")
            return {'success': True, 'integration_id': integration_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to connect {provider}: {e}")
            raise
    
    def get_status(self, user_id: int, provider: str) -> Dict:
        """Get integration status with normalized status values"""
        integration = self.get_integration(user_id, provider)
        
        if not integration:
            return {'status': 'not_connected', 'connected': False}
        
        # Normalize status values: active, needs_reauth, revoked, error
        status = integration['status']
        if status not in ['active', 'needs_reauth', 'revoked', 'error']:
            status = 'error'
        
        # Check token expiry
        tokens = self.get_integration_tokens(integration['id'])
        if not tokens:
            return {'status': 'error', 'connected': False, 'error': 'No tokens found'}
        
        # Check if token is expired (with buffer) - expires_at is epoch seconds (int)
        if tokens.get('expires_at'):
            expires_at_epoch = tokens['expires_at']
            if isinstance(expires_at_epoch, str):
                # Legacy format support
                expires_at_epoch = int(datetime.fromisoformat(expires_at_epoch).timestamp())
            now_epoch = int(datetime.now().timestamp())
            buffer_seconds = TOKEN_REFRESH_BUFFER_MINUTES * 60
            if expires_at_epoch < now_epoch + buffer_seconds:
                # Try to refresh with concurrency protection
                if tokens.get('refresh_token') and provider in self._providers:
                    new_tokens = self._refresh_token_safely(integration['id'], provider, tokens['refresh_token'])
                    if new_tokens:
                        return {'status': 'active', 'connected': True}
                    else:
                        return {'status': 'needs_reauth', 'connected': False, 'error': 'Token refresh failed'}
        
        return {
            'status': status,
            'connected': status == 'active',
            'scopes': json.loads(integration.get('scopes') or '[]'),
            'meta': json.loads(integration.get('meta_json') or '{}')
        }
    
    def _refresh_token_safely(self, integration_id: int, provider: str, refresh_token: str) -> Optional[Dict]:
        """Refresh token with concurrency protection - HTTP call outside transaction"""
        # Get current token state
        tokens = self.get_integration_tokens(integration_id)
        if not tokens:
            return None
        
        # Check expiry (normalize to epoch seconds)
        expires_at = tokens.get('expires_at')
        if expires_at:
            # Handle both epoch (int) and timestamp (str) formats
            if isinstance(expires_at, str):
                expires_at = int(datetime.fromisoformat(expires_at).timestamp())
            elif isinstance(expires_at, datetime):
                expires_at = int(expires_at.timestamp())
            
            now_epoch = int(datetime.now().timestamp())
            buffer_seconds = TOKEN_REFRESH_BUFFER_MINUTES * 60
            
            # Only refresh if token is actually expired or expiring soon
            if expires_at >= now_epoch + buffer_seconds:
                # Token still valid, return existing
                return tokens
        
        # Initialize sync state for refresh tracking (ensure row exists)
        db_optimizer.execute_query("""
            INSERT OR IGNORE INTO integration_sync_state
            (integration_id, resource, status, updated_at)
            VALUES (?, 'token_refresh', 'idle', CURRENT_TIMESTAMP)
        """, (integration_id,), fetch=False)
        
        # Acquire lock (atomic CAS update) - COMMIT IMMEDIATELY
        lock_acquired = False
        try:
            # Update only if status is 'idle' (atomic operation)
            db_optimizer.execute_query("""
                UPDATE integration_sync_state 
                SET status = 'refreshing', updated_at = CURRENT_TIMESTAMP
                WHERE integration_id = ? AND resource = 'token_refresh' AND status = 'idle'
            """, (integration_id,), fetch=False)
            
            # Verify lock was acquired (check if status changed)
            sync_state = db_optimizer.execute_query("""
                SELECT status, updated_at FROM integration_sync_state
                WHERE integration_id = ? AND resource = 'token_refresh'
            """, (integration_id,))
            
            if not sync_state or sync_state[0]['status'] != 'refreshing':
                # Lock not acquired - another process is refreshing
                logger.info(f"Token refresh already in progress for integration {integration_id}")
                return tokens
            
            # Check if refresh is stale (older than 60 seconds)
            updated_at = sync_state[0]['updated_at']
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)
            elif isinstance(updated_at, (int, float)):
                updated_at = datetime.fromtimestamp(updated_at)
            
            if (datetime.now() - updated_at).total_seconds() < 60:
                # Another refresh in progress (not stale), return existing token
                logger.info(f"Token refresh already in progress for integration {integration_id}")
                return tokens
            
            lock_acquired = True
            
            # COMMIT TRANSACTION HERE (db_optimizer handles this)
            # Now perform HTTP call OUTSIDE transaction (no DB lock held)
            new_tokens = self._providers[provider].refresh_access_token(refresh_token)
            
            # Update tokens (new transaction)
            self._update_tokens(integration_id, new_tokens)
            
            # Release lock (new transaction)
            db_optimizer.execute_query("""
                UPDATE integration_sync_state 
                SET status = 'idle', error = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE integration_id = ? AND resource = 'token_refresh'
            """, (integration_id,), fetch=False)
            
            return new_tokens
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            # Store error and release lock
            self._store_sync_error(integration_id, 'token_refresh', str(e))
            if lock_acquired:
                # Release lock on error
                db_optimizer.execute_query("""
                    UPDATE integration_sync_state 
                    SET status = 'error', updated_at = CURRENT_TIMESTAMP
                    WHERE integration_id = ? AND resource = 'token_refresh'
                """, (integration_id,), fetch=False)
            return None
    
    def _store_sync_error(self, integration_id: int, resource: str, error: str):
        """Store error in sync state"""
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO integration_sync_state
            (integration_id, resource, status, error, updated_at)
            VALUES (?, ?, 'error', ?, CURRENT_TIMESTAMP)
        """, (integration_id, resource, error), fetch=False)
    
    def _update_tokens(self, integration_id: int, token_data: Dict[str, Any]):
        """Update tokens for integration (INSERT OR REPLACE for UNIQUE constraint)"""
        access_token_enc = encrypt_token(token_data['access_token'])
        refresh_token_enc = None
        if token_data.get('refresh_token'):
            refresh_token_enc = encrypt_token(token_data['refresh_token'])
        
        # Normalize expires_at to epoch seconds (INTEGER)
        expires_at_epoch = None
        if token_data.get('expires_in'):
            expires_at_epoch = int((datetime.now() + timedelta(seconds=token_data['expires_in'])).timestamp())
        elif token_data.get('expires_at'):
            expires_at = token_data['expires_at']
            if isinstance(expires_at, datetime):
                expires_at_epoch = int(expires_at.timestamp())
            elif isinstance(expires_at, str):
                expires_at_epoch = int(datetime.fromisoformat(expires_at).timestamp())
            elif isinstance(expires_at, (int, float)):
                expires_at_epoch = int(expires_at)
        
        # Get current encryption version (preserve existing or default to 1)
        existing_tokens = db_optimizer.execute_query(
            "SELECT enc_version FROM integration_tokens WHERE integration_id = ?",
            (integration_id,)
        )
        enc_version = existing_tokens[0]['enc_version'] if existing_tokens and existing_tokens[0].get('enc_version') else 1
        
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO integration_tokens 
            (integration_id, access_token_enc, refresh_token_enc, expires_at, token_type, enc_version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            integration_id,
            access_token_enc,
            refresh_token_enc,
            expires_at_epoch,
            token_data.get('token_type', 'Bearer'),
            enc_version
        ), fetch=False)
    
    def disconnect(self, user_id: int, provider: str) -> Dict:
        """Disconnect integration with cascade cleanup - correct order: revoke -> mark revoked -> delete tokens"""
        integration = self.get_integration(user_id, provider)
        if not integration:
            return {'success': False, 'error': 'Integration not found'}
        
        integration_id = integration['id']
        
        # Step 1: Get valid access token (if possible) BEFORE deleting anything
        revoke_success = False
        if provider in self._providers:
            tokens = self.get_integration_tokens(integration_id)
            if tokens and tokens.get('access_token'):
                try:
                    # Revoke token via provider API (network call)
                    revoke_success = self._providers[provider].revoke_token(tokens['access_token'])
                    if revoke_success:
                        logger.info(f"✅ Revoked token for integration {integration_id}")
                    else:
                        logger.warning(f"⚠️ Token revocation returned False for integration {integration_id}")
                except Exception as e:
                    # Don't block disconnect UX if revoke fails (network error, etc.)
                    logger.warning(f"⚠️ Failed to revoke token (non-blocking): {e}")
                    # Continue with disconnect anyway
        
        # Step 2: Mark integration as revoked (normalized status)
        db_optimizer.execute_query("""
            UPDATE integrations 
            SET status = 'revoked', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (integration_id,), fetch=False)
        
        # Step 3: Delete tokens (cascade will handle sync_state)
        db_optimizer.execute_query("""
            DELETE FROM integration_tokens WHERE integration_id = ?
        """, (integration_id,), fetch=False)
        
        # Step 4: Mark calendar event links as inactive (keep for history, but mark broken)
        db_optimizer.execute_query("""
            UPDATE calendar_event_links 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE integration_id = ?
        """, (integration_id,), fetch=False)
        
        logger.info(f"✅ Disconnected {provider} for user {user_id} (revoke: {revoke_success})")
        return {'success': True, 'revoked': revoke_success}
    
    def get_valid_token(self, user_id: int, provider: str) -> Optional[str]:
        """Get valid access token (refresh if needed)"""
        integration = self.get_integration(user_id, provider)
        if not integration:
            return None
        
        tokens = self.get_integration_tokens(integration['id'])
        if not tokens:
            return None
        
        # Check if token needs refresh - expires_at is epoch seconds (int)
        if tokens.get('expires_at'):
            expires_at_epoch = tokens['expires_at']
            if isinstance(expires_at_epoch, str):
                # Legacy format support
                expires_at_epoch = int(datetime.fromisoformat(expires_at_epoch).timestamp())
            now_epoch = int(datetime.now().timestamp())
            buffer_seconds = TOKEN_REFRESH_BUFFER_MINUTES * 60
            if expires_at_epoch < now_epoch + buffer_seconds:
                # Refresh token with concurrency protection
                if tokens.get('refresh_token') and provider in self._providers:
                    new_tokens = self._refresh_token_safely(integration['id'], provider, tokens['refresh_token'])
                    if new_tokens:
                        return new_tokens['access_token']
                    else:
                        return None
        
        return tokens['access_token']
    
    def link_calendar_event(self, user_id: int, integration_id: int, 
                           internal_entity_type: str, internal_entity_id: int,
                           external_event_id: str, external_calendar_id: str = 'primary'):
        """Link internal entity to external calendar event"""
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO calendar_event_links
            (user_id, integration_id, internal_entity_type, internal_entity_id,
             external_event_id, external_calendar_id, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (user_id, integration_id, internal_entity_type, internal_entity_id,
              external_event_id, external_calendar_id), fetch=False)
    
    def get_calendar_event_link(self, user_id: int, internal_entity_type: str, 
                                internal_entity_id: int, integration_id: int = None) -> Optional[Dict]:
        """Get calendar event link for internal entity (only active links)"""
        if integration_id:
            result = db_optimizer.execute_query("""
                SELECT * FROM calendar_event_links
                WHERE user_id = ? AND internal_entity_type = ? 
                AND internal_entity_id = ? AND integration_id = ? AND is_active = 1
            """, (user_id, internal_entity_type, internal_entity_id, integration_id))
        else:
            result = db_optimizer.execute_query("""
                SELECT * FROM calendar_event_links
                WHERE user_id = ? AND internal_entity_type = ? 
                AND internal_entity_id = ? AND is_active = 1
            """, (user_id, internal_entity_type, internal_entity_id))
        
        return result[0] if result else None


# Global integration manager instance
integration_manager = IntegrationManager()
