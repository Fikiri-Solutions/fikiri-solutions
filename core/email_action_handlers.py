"""
Email Action Handlers for Fikiri Solutions
Handles email actions like archive, forward, tag, and automated responses
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from core.minimal_config import get_config
from core.gmail_oauth import gmail_oauth_manager
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class EmailAction:
    """Email action data structure"""
    action_type: str  # archive, forward, tag, reply
    email_id: str
    user_id: int
    parameters: Dict[str, Any]
    created_at: datetime

class EmailActionHandler:
    """Handles email actions and automation"""
    
    def __init__(self):
        self.oauth_manager = gmail_oauth_manager
    
    def archive_email(self, user_id: int, email_id: str) -> Dict[str, Any]:
        """Archive an email in Gmail"""
        try:
            # Get user's Gmail tokens
            token = self.oauth_manager.get_user_tokens(user_id)
            if not token:
                return {"success": False, "error": "No Gmail tokens found"}
            
            # Check if token needs refresh
            if token.expires_at and token.expires_at < datetime.now():
                refresh_result = self.oauth_manager.refresh_access_token(user_id)
                if not refresh_result['success']:
                    return {"success": False, "error": "Failed to refresh token"}
                token = self.oauth_manager.get_user_tokens(user_id)
            
            # Archive the email using Gmail API
            headers = {
                'Authorization': f'Bearer {token.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Remove INBOX label to archive
            data = {
                'removeLabelIds': ['INBOX']
            }
            
            response = requests.post(
                f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}/modify',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                # Log the action
                self._log_email_action(user_id, email_id, 'archive', {})
                
                logger.info(f"✅ Email archived: {email_id}")
                return {"success": True, "message": "Email archived successfully"}
            else:
                logger.error(f"❌ Failed to archive email: {response.status_code}")
                return {"success": False, "error": f"Gmail API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Archive email error: {e}")
            return {"success": False, "error": str(e)}
    
    def forward_email(self, user_id: int, email_id: str, to_email: str, message: str = "") -> Dict[str, Any]:
        """Forward an email to another address"""
        try:
            # Get user's Gmail tokens
            token = self.oauth_manager.get_user_tokens(user_id)
            if not token:
                return {"success": False, "error": "No Gmail tokens found"}
            
            # Check if token needs refresh
            if token.expires_at and token.expires_at < datetime.now():
                refresh_result = self.oauth_manager.refresh_access_token(user_id)
                if not refresh_result['success']:
                    return {"success": False, "error": "Failed to refresh token"}
                token = self.oauth_manager.get_user_tokens(user_id)
            
            # Get the original email
            headers = {
                'Authorization': f'Bearer {token.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get email details
            email_response = requests.get(
                f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}',
                headers=headers
            )
            
            if email_response.status_code != 200:
                return {"success": False, "error": "Failed to retrieve email"}
            
            email_data = email_response.json()
            
            # Extract email headers
            headers_data = email_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers_data if h['name'] == 'Subject'), '')
            from_email = next((h['value'] for h in headers_data if h['name'] == 'From'), '')
            
            # Create forward message
            forward_subject = f"Fwd: {subject}"
            forward_body = f"""
{message}

---------- Forwarded message ---------
From: {from_email}
Subject: {subject}

[Original email content would be here]
"""
            
            # Send the forwarded email
            message_data = {
                'raw': self._create_message_raw(
                    to_email,
                    forward_subject,
                    forward_body
                )
            }
            
            send_response = requests.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                headers=headers,
                json=message_data
            )
            
            if send_response.status_code == 200:
                # Log the action
                self._log_email_action(user_id, email_id, 'forward', {
                    'to_email': to_email,
                    'message': message
                })
                
                logger.info(f"✅ Email forwarded: {email_id} to {to_email}")
                return {"success": True, "message": "Email forwarded successfully"}
            else:
                logger.error(f"❌ Failed to forward email: {send_response.status_code}")
                return {"success": False, "error": f"Gmail API error: {send_response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Forward email error: {e}")
            return {"success": False, "error": str(e)}
    
    def tag_email(self, user_id: int, email_id: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags/labels to an email"""
        try:
            # Get user's Gmail tokens
            token = self.oauth_manager.get_user_tokens(user_id)
            if not token:
                return {"success": False, "error": "No Gmail tokens found"}
            
            # Check if token needs refresh
            if token.expires_at and token.expires_at < datetime.now():
                refresh_result = self.oauth_manager.refresh_access_token(user_id)
                if not refresh_result['success']:
                    return {"success": False, "error": "Failed to refresh token"}
                token = self.oauth_manager.get_user_tokens(user_id)
            
            # Get or create labels for tags
            label_ids = []
            for tag in tags:
                label_id = self._get_or_create_label(token.access_token, tag)
                if label_id:
                    label_ids.append(label_id)
            
            if not label_ids:
                return {"success": False, "error": "No valid labels found"}
            
            # Add labels to email
            headers = {
                'Authorization': f'Bearer {token.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'addLabelIds': label_ids
            }
            
            response = requests.post(
                f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}/modify',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                # Log the action
                self._log_email_action(user_id, email_id, 'tag', {'tags': tags})
                
                logger.info(f"✅ Email tagged: {email_id} with {tags}")
                return {"success": True, "message": f"Email tagged with: {', '.join(tags)}"}
            else:
                logger.error(f"❌ Failed to tag email: {response.status_code}")
                return {"success": False, "error": f"Gmail API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Tag email error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_ai_response(self, user_id: int, email_id: str, ai_response: str) -> Dict[str, Any]:
        """Send an AI-generated response to an email"""
        try:
            # Get user's Gmail tokens
            token = self.oauth_manager.get_user_tokens(user_id)
            if not token:
                return {"success": False, "error": "No Gmail tokens found"}
            
            # Check if token needs refresh
            if token.expires_at and token.expires_at < datetime.now():
                refresh_result = self.oauth_manager.refresh_access_token(user_id)
                if not refresh_result['success']:
                    return {"success": False, "error": "Failed to refresh token"}
                token = self.oauth_manager.get_user_tokens(user_id)
            
            # Get the original email to extract recipient
            headers = {
                'Authorization': f'Bearer {token.access_token}',
                'Content-Type': 'application/json'
            }
            
            email_response = requests.get(
                f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}',
                headers=headers
            )
            
            if email_response.status_code != 200:
                return {"success": False, "error": "Failed to retrieve email"}
            
            email_data = email_response.json()
            
            # Extract recipient email
            headers_data = email_data.get('payload', {}).get('headers', [])
            from_email = next((h['value'] for h in headers_data if h['name'] == 'From'), '')
            subject = next((h['value'] for h in headers_data if h['name'] == 'Subject'), '')
            
            # Clean up email address
            if '<' in from_email and '>' in from_email:
                from_email = from_email.split('<')[1].split('>')[0]
            
            # Create reply message
            reply_subject = f"Re: {subject}" if not subject.startswith('Re:') else subject
            
            # Send the reply
            message_data = {
                'raw': self._create_message_raw(
                    from_email,
                    reply_subject,
                    ai_response
                )
            }
            
            send_response = requests.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                headers=headers,
                json=message_data
            )
            
            if send_response.status_code == 200:
                # Log the action
                self._log_email_action(user_id, email_id, 'ai_reply', {
                    'ai_response': ai_response,
                    'to_email': from_email
                })
                
                logger.info(f"✅ AI response sent: {email_id}")
                return {"success": True, "message": "AI response sent successfully"}
            else:
                logger.error(f"❌ Failed to send AI response: {send_response.status_code}")
                return {"success": False, "error": f"Gmail API error: {send_response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Send AI response error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_or_create_label(self, access_token: str, label_name: str) -> Optional[str]:
        """Get existing label or create new one"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get existing labels
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/labels',
                headers=headers
            )
            
            if response.status_code == 200:
                labels = response.json().get('labels', [])
                
                # Check if label exists
                for label in labels:
                    if label['name'] == label_name:
                        return label['id']
                
                # Create new label
                label_data = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                
                create_response = requests.post(
                    'https://gmail.googleapis.com/gmail/v1/users/me/labels',
                    headers=headers,
                    json=label_data
                )
                
                if create_response.status_code == 200:
                    return create_response.json()['id']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Label creation error: {e}")
            return None
    
    def _create_message_raw(self, to_email: str, subject: str, body: str) -> str:
        """Create raw message for Gmail API"""
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return raw_message
    
    def _log_email_action(self, user_id: int, email_id: str, action_type: str, parameters: Dict[str, Any]):
        """Log email action to database"""
        try:
            query = """
                INSERT INTO email_actions (
                    user_id, email_id, action_type, parameters, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """
            
            values = (
                user_id,
                email_id,
                action_type,
                json.dumps(parameters),
                datetime.now().isoformat()
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
        except Exception as e:
            logger.error(f"❌ Failed to log email action: {e}")

# Global instance
email_action_handler = None

def get_email_action_handler() -> Optional[EmailActionHandler]:
    """Get the global email action handler instance"""
    global email_action_handler
    
    if email_action_handler is None:
        email_action_handler = EmailActionHandler()
    
    return email_action_handler
