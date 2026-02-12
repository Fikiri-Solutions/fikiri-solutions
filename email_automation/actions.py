#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Actions
Lightweight email processing actions with AI integration and Gmail API support.
"""

import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps

# Optional Gmail API integration
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    build = None
    HttpError = Exception

# Optional rate limiting
try:
    from core.rate_limiter import enhanced_rate_limiter
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    enhanced_rate_limiter = None

logger = logging.getLogger(__name__)

def rate_limit_email_action(limit: str = "10/minute"):
    """Decorator for rate limiting email actions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if RATE_LIMITING_AVAILABLE:
                # Use the rate_limit decorator from rate_limiter
                from core.rate_limiter import rate_limit
                return rate_limit("email_send")(func)(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

class MinimalEmailActions:
    """Minimal email actions with AI integration and Gmail API support."""
    
    def __init__(self, services: Dict[str, Any] = None):
        """Initialize minimal email actions with service dependencies."""
        self.processed_count = 0
        self.action_log = []
        self.services = services or {}
        
        # Initialize Gmail service if available
        self.gmail_service = None
        self._initialize_gmail_service()
        
        # Initialize database for logging
        self.db_optimizer = None
        self._initialize_database()
    
    def _initialize_gmail_service(self):
        """Initialize Gmail API service if credentials are available."""
        if not GMAIL_API_AVAILABLE:
            logger.info("ℹ️ Gmail API not available")
            return
        
        try:
            # Try to get Gmail service from services
            if 'gmail' in self.services:
                self.gmail_service = self.services['gmail']
                logger.info("✅ Gmail service initialized from services")
            else:
                logger.info("ℹ️ Gmail service not available in services")
        except Exception as e:
            logger.error(f"❌ Gmail service initialization failed: {e}")
    
    def _initialize_database(self):
        """Initialize database for action logging."""
        try:
            from core.database_optimization import db_optimizer
            self.db_optimizer = db_optimizer
            logger.info("✅ Database initialized for action logging")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    @rate_limit_email_action("10/minute")
    def process_email(self, parsed_email: Dict[str, Any], action_type: str = "auto_reply", 
                     user_id: int = None) -> Dict[str, Any]:
        """Process an email with specified action."""
        action_handlers = {
            "auto_reply": self._auto_reply,
            "mark_read": self._mark_read,
            "add_label": self._add_label,
            "forward": self._forward_email,
            "archive": self._archive_email
        }
        
        handler = action_handlers.get(action_type)
        if not handler:
            result = {
                "success": False,
                "action": action_type,
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": f"Unknown action type: {action_type}"}
            }
        else:
            result = handler(parsed_email, user_id)
        
        self.action_log.append(result)
        self.processed_count += 1
        self._persist_action_log(result)
        return result
    
    def _auto_reply(self, parsed_email: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Generate and send auto-reply for email."""
        try:
            sender = parsed_email.get("headers", {}).get("from", "")
            subject = parsed_email.get("headers", {}).get("subject", "")
            message_id = parsed_email.get("message_id", "")
            
            # Extract sender name
            sender_name = self._extract_name_from_email(sender)
            
            # Generate reply content using AI if available
            reply_content = self._generate_reply_content(sender_name, subject, parsed_email)
            
            # Send reply via Gmail API if available
            reply_sent = False
            reply_message_id = None
            
            if self.gmail_service:
                try:
                    reply_message_id = self._send_gmail_reply(
                        parsed_email, reply_content, sender_name
                    )
                    reply_sent = True
                    logger.info(f"✅ Auto-reply sent via Gmail API: {reply_message_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send Gmail reply: {e}")
                    reply_sent = False
            
            result = {
                "success": True,
                "action": "auto_reply",
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {
                    "sender": sender,
                    "sender_name": sender_name,
                    "subject": subject,
                    "reply_content": reply_content,
                    "reply_generated": True,
                    "reply_sent": reply_sent,
                    "reply_message_id": reply_message_id
                }
            }
            
            logger.info(f"✅ Auto-reply generated for {sender}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "auto_reply",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": str(e)}
            }
    
    def _send_gmail_reply(self, parsed_email: Dict[str, Any], reply_content: str, 
                         sender_name: str) -> str:
        """Send reply via Gmail API."""
        if not self.gmail_service:
            raise Exception("Gmail service not available")
        
        try:
            # Get original sender
            original_sender = parsed_email.get("headers", {}).get("from", "")
            original_subject = parsed_email.get("headers", {}).get("subject", "")
            
            # Extract email address from sender
            if "<" in original_sender and ">" in original_sender:
                to_email = original_sender.split("<")[1].split(">")[0].strip()
            else:
                to_email = original_sender
            
            # Create reply subject
            reply_subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
            
            # Create message
            message = {
                'raw': base64.urlsafe_b64encode(
                    f"To: {to_email}\r\n"
                    f"Subject: {reply_subject}\r\n"
                    f"Content-Type: text/plain; charset=UTF-8\r\n"
                    f"\r\n"
                    f"{reply_content}".encode('utf-8')
                ).decode('utf-8')
            }
            
            # Send message
            sent_message = self.gmail_service.users().messages().send(
                userId='me', body=message
            ).execute()
            
            return sent_message['id']
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise Exception(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Failed to send Gmail reply: {e}")
            raise
    
    def _generate_reply_content(self, sender_name: str, subject: str, 
                               parsed_email: Dict[str, Any] = None) -> str:
        """Generate reply content using AI if available, otherwise use templates."""
        
        # Try AI-generated reply first
        if 'ai_assistant' in self.services:
            try:
                ai_reply = self.services['ai_assistant'].generate_reply(
                    sender_name=sender_name,
                    subject=subject,
                    email_content=parsed_email.get("snippet", "") if parsed_email else "",
                    email_body=parsed_email.get("body_text", "") if parsed_email else ""
                )
                if ai_reply:
                    logger.info("✅ AI-generated reply used")
                    return ai_reply
            except Exception as e:
                logger.warning(f"AI reply generation failed: {e}")
        
        # Fallback to template-based reply
        return self._generate_template_reply(sender_name, subject)
    
    def _generate_template_reply(self, sender_name: str, subject: str) -> str:
        """Generate reply content using templates."""
        templates = {
            "general": f"""Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team""",
            
            "lead": f"""Hi {sender_name},

Thank you for your interest in our services!

I've received your inquiry about "{subject}" and I'm excited to learn more about your needs.

I'll be in touch within 24 hours to discuss how we can help you.

Best regards,
Fikiri Solutions Team""",
            
            "support": f"""Hi {sender_name},

Thank you for contacting our support team regarding "{subject}".

I've received your message and will investigate this issue for you.

I'll get back to you with a solution as soon as possible.

Best regards,
Fikiri Solutions Support Team"""
        }
        
        # Simple keyword matching for template selection
        subject_lower = subject.lower()
        if any(word in subject_lower for word in ["support", "help", "issue", "problem"]):
            return templates["support"]
        elif any(word in subject_lower for word in ["quote", "price", "service", "lead"]):
            return templates["lead"]
        else:
            return templates["general"]
    
    @rate_limit_email_action("20/minute")
    def _mark_read(self, parsed_email: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Mark email as read."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            # Try to mark as read via Gmail API
            marked_read = False
            if self.gmail_service:
                try:
                    self.gmail_service.users().messages().modify(
                        userId='me',
                        id=message_id,
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                    marked_read = True
                    logger.info(f"✅ Marked message {message_id} as read via Gmail API")
                except Exception as e:
                    logger.error(f"❌ Failed to mark as read via Gmail API: {e}")
            
            result = {
                "success": True,
                "action": "mark_read",
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {
                    "marked_read": True,
                    "marked_via_api": marked_read,
                    "previous_labels": parsed_email.get("labels", [])
                }
            }
            
            logger.info(f"✅ Marked message {message_id} as read")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "mark_read",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": str(e)}
            }
    
    @rate_limit_email_action("15/minute")
    def _add_label(self, parsed_email: Dict[str, Any], user_id: int = None, 
                   label: str = "PROCESSED") -> Dict[str, Any]:
        """Add label to email."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            # Try to add label via Gmail API
            label_added = False
            if self.gmail_service:
                try:
                    self.gmail_service.users().messages().modify(
                        userId='me',
                        id=message_id,
                        body={'addLabelIds': [label]}
                    ).execute()
                    label_added = True
                    logger.info(f"✅ Added label '{label}' to message {message_id} via Gmail API")
                except Exception as e:
                    logger.error(f"❌ Failed to add label via Gmail API: {e}")
            
            result = {
                "success": True,
                "action": "add_label",
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {
                    "label_added": label,
                    "added_via_api": label_added,
                    "previous_labels": parsed_email.get("labels", [])
                }
            }
            
            logger.info(f"✅ Added label '{label}' to message {message_id}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "add_label",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": str(e)}
            }
    
    @rate_limit_email_action("5/minute")
    def _forward_email(self, parsed_email: Dict[str, Any], user_id: int = None, 
                      forward_to: str = "") -> Dict[str, Any]:
        """Forward email to another address."""
        try:
            message_id = parsed_email.get("message_id", "")
            sender = parsed_email.get("headers", {}).get("from", "")
            subject = parsed_email.get("headers", {}).get("subject", "")
            
            # Try to forward via Gmail API
            forwarded = False
            if self.gmail_service and forward_to:
                try:
                    # Get the original message
                    original_message = self.gmail_service.users().messages().get(
                        userId='me', id=message_id
                    ).execute()
                    
                    # Create forward message
                    forward_message = {
                        'raw': base64.urlsafe_b64encode(
                            f"To: {forward_to}\r\n"
                            f"Subject: Fwd: {subject}\r\n"
                            f"Content-Type: text/plain; charset=UTF-8\r\n"
                            f"\r\n"
                            f"---------- Forwarded message ---------\r\n"
                            f"From: {sender}\r\n"
                            f"Subject: {subject}\r\n"
                            f"\r\n"
                            f"{parsed_email.get('snippet', '')}".encode('utf-8')
                        ).decode('utf-8')
                    }
                    
                    self.gmail_service.users().messages().send(
                        userId='me', body=forward_message
                    ).execute()
                    forwarded = True
                    logger.info(f"✅ Forwarded message {message_id} to {forward_to} via Gmail API")
                except Exception as e:
                    logger.error(f"❌ Failed to forward via Gmail API: {e}")
            
            result = {
                "success": True,
                "action": "forward",
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {
                    "forwarded_to": forward_to,
                    "original_sender": sender,
                    "subject": subject,
                    "forward_generated": True,
                    "forwarded_via_api": forwarded
                }
            }
            
            logger.info(f"✅ Forwarded message {message_id} to {forward_to}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "forward",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": str(e)}
            }
    
    @rate_limit_email_action("20/minute")
    def _archive_email(self, parsed_email: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Archive email (remove from inbox)."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            # Try to archive via Gmail API
            archived = False
            if self.gmail_service:
                try:
                    self.gmail_service.users().messages().modify(
                        userId='me',
                        id=message_id,
                        body={'removeLabelIds': ['INBOX']}
                    ).execute()
                    archived = True
                    logger.info(f"✅ Archived message {message_id} via Gmail API")
                except Exception as e:
                    logger.error(f"❌ Failed to archive via Gmail API: {e}")
            
            result = {
                "success": True,
                "action": "archive",
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {
                    "archived": True,
                    "removed_from_inbox": True,
                    "archived_via_api": archived
                }
            }
            
            logger.info(f"✅ Archived message {message_id}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "archive",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "details": {"error": str(e)}
            }
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract name from email address."""
        if not email:
            return "Valued Customer"
        
        # Try to extract name from "Name <email@domain.com>" format
        if "<" in email and ">" in email:
            name_part = email.split("<")[0].strip()
            if name_part:
                return name_part
        
        # Extract name from email address
        email_part = email.split("@")[0]
        # Replace dots and underscores with spaces
        name = email_part.replace(".", " ").replace("_", " ")
        # Capitalize words
        name = " ".join(word.capitalize() for word in name.split())
        
        return name if name else "Valued Customer"
    
    def _persist_action_log(self, action_result: Dict[str, Any]):
        """Persist action log to database."""
        if not self.db_optimizer:
            return
        
        try:
            # Ensure details is JSON string
            details_json = json.dumps(action_result.get('details', {}))
            
            self.db_optimizer.execute_query("""
                INSERT INTO email_actions_log 
                (user_id, action_type, message_id, success, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                action_result.get('user_id'),
                action_result.get('action'),
                action_result.get('message_id'),
                action_result.get('success'),
                details_json,
                action_result.get('timestamp')
            ), fetch=False)
        except Exception as e:
            logger.warning(f"Failed to persist action log: {e}")
    
    def get_action_log(self) -> List[Dict[str, Any]]:
        """Get the action log."""
        return self.action_log
    
    def get_persisted_actions(self, user_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get persisted actions from database."""
        if not self.db_optimizer:
            return []
        
        try:
            # Rulepack compliance: specific columns, not SELECT *, with pagination
            if user_id:
                actions = self.db_optimizer.execute_query("""
                    SELECT id, user_id, action_type, message_id, success, details, timestamp 
                    FROM email_actions_log 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, limit, 0))  # TODO: Add offset parameter to method signature
            else:
                actions = self.db_optimizer.execute_query("""
                    SELECT id, user_id, action_type, message_id, success, details, timestamp 
                    FROM email_actions_log 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (limit, 0))  # TODO: Add offset parameter to method signature
            
            return [
                {
                    'id': action['id'],
                    'user_id': action['user_id'],
                    'action_type': action['action_type'],
                    'message_id': action['message_id'],
                    'success': action['success'],
                    'details': json.loads(action['details']) if action['details'] else {},
                    'timestamp': action['timestamp']
                }
                for action in actions
            ]
        except Exception as e:
            logger.error(f"Failed to get persisted actions: {e}")
            return []
    
    def get_processed_count(self) -> int:
        """Get count of processed emails."""
        return self.processed_count
    
    def clear_log(self):
        """Clear the action log."""
        self.action_log = []
        self.processed_count = 0
        logger.info("✅ Action log cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        successful_actions = sum(1 for action in self.action_log if action.get("success", False))
        failed_actions = len(self.action_log) - successful_actions
        
        action_types = {}
        for action in self.action_log:
            action_type = action.get("action", "unknown")
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        return {
            "total_processed": self.processed_count,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "action_types": action_types,
            "last_action": self.action_log[-1] if self.action_log else None,
            "gmail_api_available": bool(self.gmail_service),
            "ai_assistant_available": 'ai_assistant' in self.services,
            "rate_limiting_available": RATE_LIMITING_AVAILABLE
        }

def create_email_actions(services: Dict[str, Any] = None) -> MinimalEmailActions:
    """Create and return an email actions instance with services."""
    return MinimalEmailActions(services)

if __name__ == "__main__":
    # Test the email actions
    logger.info("🧪 Testing Minimal Email Actions")
    logger.info("=" * 40)
    
    actions = MinimalEmailActions()
    
    # Test with sample email
    sample_email = {
        "message_id": "test123",
        "headers": {
            "from": "John Doe <john.doe@example.com>",
            "subject": "Inquiry about your services",
            "to": "info@fikirisolutions.com"
        },
        "labels": ["UNREAD", "INBOX"],
        "snippet": "I'm interested in learning more about your services..."
    }
    
    # Test auto-reply
    logger.info("Testing auto-reply...")
    result = actions.process_email(sample_email, "auto_reply")
    logger.info(f"✅ Auto-reply result: {result['success']}")
    if result['success']:
        logger.info(f"   Reply content: {result['details']['reply_content'][:50]}...")
    
    # Test mark as read
    logger.info("Testing mark as read...")
    result = actions.process_email(sample_email, "mark_read")
    logger.info(f"✅ Mark as read result: {result['success']}")
    
    # Test add label
    logger.info("Testing add label...")
    result = actions.process_email(sample_email, "add_label")
    logger.info(f"✅ Add label result: {result['success']}")
    
    # Test stats
    logger.info("Testing stats...")
    stats = actions.get_stats()
    logger.info(f"✅ Stats: {stats['total_processed']} processed, {stats['successful_actions']} successful")
    
    logger.info("🎉 All email actions tests completed!")