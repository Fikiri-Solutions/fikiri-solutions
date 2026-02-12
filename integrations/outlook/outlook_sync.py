#!/usr/bin/env python3
"""
Outlook Email Sync
Production-ready Outlook email synchronization following Gmail patterns
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

def decrypt_token(encrypted_token: str) -> Optional[str]:
    """Decrypt stored token"""
    try:
        from core.app_oauth import decrypt
        return decrypt(encrypted_token)
    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        return None

def get_outlook_tokens(user_id: int) -> Optional[Dict[str, Any]]:
    """Get Outlook tokens for user"""
    try:
        tokens = db_optimizer.execute_query("""
            SELECT access_token_enc, refresh_token_enc, expiry_timestamp, tenant_id
            FROM outlook_tokens 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY updated_at DESC
            LIMIT 1
        """, (user_id,))
        
        if not tokens or len(tokens) == 0:
            return None
        
        token_row = tokens[0]
        if isinstance(token_row, dict):
            access_token_enc = token_row.get('access_token_enc')
            refresh_token_enc = token_row.get('refresh_token_enc')
            expiry = token_row.get('expiry_timestamp')
            tenant_id = token_row.get('tenant_id')
        else:
            access_token_enc = token_row[0] if len(token_row) > 0 else None
            refresh_token_enc = token_row[1] if len(token_row) > 1 else None
            expiry = token_row[2] if len(token_row) > 2 else None
            tenant_id = token_row[3] if len(token_row) > 3 else None
        
        if not access_token_enc:
            return None
        
        access_token = decrypt_token(access_token_enc)
        refresh_token = decrypt_token(refresh_token_enc) if refresh_token_enc else None
        
        if not access_token:
            return None
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expiry,
            'tenant_id': tenant_id or os.getenv('MICROSOFT_TENANT_ID', 'common')
        }
    except Exception as e:
        logger.error(f"Failed to get Outlook tokens: {e}")
        return None

def refresh_outlook_token(user_id: int, refresh_token: str, tenant_id: str) -> Optional[str]:
    """Refresh Outlook access token"""
    try:
        client_id = os.getenv('MICROSOFT_CLIENT_ID')
        client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logger.error("Microsoft OAuth credentials not configured")
            return None
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': ' '.join([
                'https://graph.microsoft.com/Mail.ReadWrite',
                'https://graph.microsoft.com/User.Read',
                'offline_access'
            ])
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token', refresh_token)
        expires_in = token_data.get('expires_in', 3600)
        
        if new_access_token:
            # Update tokens in database
            from core.app_oauth import encrypt, upsert_outlook_tokens
            encrypted_access = encrypt(new_access_token)
            encrypted_refresh = encrypt(new_refresh_token) if new_refresh_token else None
            
            upsert_outlook_tokens(
                user_id=user_id,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                expiry=int(datetime.now().timestamp()) + expires_in,
                scopes=['Mail.ReadWrite', 'User.Read', 'offline_access'],
                tenant_id=tenant_id
            )
            
            logger.info(f"✅ Refreshed Outlook token for user {user_id}")
            return new_access_token
        
        return None
    except Exception as e:
        logger.error(f"Failed to refresh Outlook token: {e}")
        return None

def get_valid_outlook_token(user_id: int) -> Optional[str]:
    """Get valid Outlook access token, refreshing if needed"""
    tokens = get_outlook_tokens(user_id)
    if not tokens:
        return None
    
    access_token = tokens['access_token']
    expires_at = tokens.get('expires_at')
    
    # Check if token is expired (with 5 minute buffer)
    if expires_at:
        try:
            expiry_time = int(expires_at)
            if time.time() >= (expiry_time - 300):  # 5 minute buffer
                # Token expired or expiring soon, refresh it
                refresh_token = tokens.get('refresh_token')
                tenant_id = tokens.get('tenant_id', 'common')
                
                if refresh_token:
                    new_token = refresh_outlook_token(user_id, refresh_token, tenant_id)
                    if new_token:
                        return new_token
                    else:
                        logger.warning(f"Token refresh failed for user {user_id}")
                        return None
        except Exception as e:
            logger.warning(f"Error checking token expiry: {e}")
    
    return access_token

def sync_outlook_emails(user_id: int, limit: int = 50, days: int = 30) -> Dict[str, Any]:
    """Sync emails from Outlook for a user"""
    try:
        access_token = get_valid_outlook_token(user_id)
        if not access_token:
            return {
                'success': False,
                'error': 'No valid Outlook token',
                'count': 0
            }
        
        # Get messages from Microsoft Graph
        graph_url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Calculate date filter
        since_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            '$top': limit,
            '$orderby': 'receivedDateTime desc',
            '$filter': f"receivedDateTime ge {since_date}",
            '$select': 'id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments,body'
        }
        
        response = requests.get(graph_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        messages = data.get('value', [])
        
        # Store emails in database
        emails_synced = 0
        for msg in messages:
            try:
                email_id = msg.get('id')
                subject = msg.get('subject', 'No Subject')
                from_info = msg.get('from', {})
                sender_email = from_info.get('emailAddress', {}).get('address', '')
                sender_name = from_info.get('emailAddress', {}).get('name', '')
                received_date = msg.get('receivedDateTime', '')
                body_preview = msg.get('bodyPreview', '')
                is_read = msg.get('isRead', False)
                has_attachments = msg.get('hasAttachments', False)
                
                # Get full body if available
                body_content = ''
                body_obj = msg.get('body', {})
                if body_obj:
                    body_content = body_obj.get('content', '')
                
                # Check if email already exists
                existing = db_optimizer.execute_query("""
                    SELECT id FROM synced_emails 
                    WHERE user_id = ? AND external_id = ? AND provider = 'outlook'
                """, (user_id, email_id))
                
                if existing and len(existing) > 0:
                    continue  # Skip if already synced
                
                # Format sender for compatibility with existing schema
                sender = f"{sender_name} <{sender_email}>" if sender_name else sender_email
                
                # Insert email (using same schema as Gmail for compatibility)
                db_optimizer.execute_query("""
                    INSERT OR IGNORE INTO synced_emails 
                    (user_id, external_id, provider, subject, sender, recipient, date, body, labels, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_id, 
                    email_id, 
                    'outlook', 
                    subject, 
                    sender,
                    '',  # recipient not available from Graph API message list
                    received_date,
                    body_content or body_preview,
                    json.dumps(['UNREAD'] if not is_read else [])  # Labels format
                ), fetch=False)
                
                emails_synced += 1
                
                # Trigger automation for EMAIL_RECEIVED
                from core.automation_engine import automation_engine, TriggerType
                automation_engine.execute_automation_rules(
                    TriggerType.EMAIL_RECEIVED,
                    {
                        'email_id': email_id,
                        'sender_email': sender_email,
                        'subject': subject,
                        'text': body_preview
                    },
                    user_id
                )
                
            except Exception as e:
                logger.warning(f"Failed to store email {msg.get('id')}: {e}")
                continue
        
        logger.info(f"✅ Synced {emails_synced} Outlook emails for user {user_id}")
        
        return {
            'success': True,
            'count': emails_synced,
            'message': f'Synced {emails_synced} emails'
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.error(f"Outlook token expired for user {user_id}")
            return {
                'success': False,
                'error': 'Token expired, please reconnect Outlook',
                'count': 0
            }
        else:
            logger.error(f"Outlook API error: {e}")
            return {
                'success': False,
                'error': f'Outlook API error: {str(e)}',
                'count': 0
            }
    except Exception as e:
        logger.error(f"Outlook sync failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'count': 0
        }


