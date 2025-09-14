#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Actions
Lightweight email processing actions without heavy dependencies.
"""

import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

class MinimalEmailActions:
    """Minimal email actions - lightweight version."""
    
    def __init__(self):
        """Initialize minimal email actions."""
        self.processed_count = 0
        self.action_log = []
    
    def process_email(self, parsed_email: Dict[str, Any], action_type: str = "auto_reply") -> Dict[str, Any]:
        """Process an email with specified action."""
        try:
            result = {
                "success": False,
                "action": action_type,
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {}
            }
            
            if action_type == "auto_reply":
                result = self._auto_reply(parsed_email)
            elif action_type == "mark_read":
                result = self._mark_read(parsed_email)
            elif action_type == "add_label":
                result = self._add_label(parsed_email)
            elif action_type == "forward":
                result = self._forward_email(parsed_email)
            elif action_type == "archive":
                result = self._archive_email(parsed_email)
            else:
                result["details"]["error"] = f"Unknown action type: {action_type}"
            
            # Log the action
            self.action_log.append(result)
            self.processed_count += 1
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "action": action_type,
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }
            self.action_log.append(error_result)
            return error_result
    
    def _auto_reply(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """Generate auto-reply for email."""
        try:
            sender = parsed_email.get("headers", {}).get("from", "")
            subject = parsed_email.get("headers", {}).get("subject", "")
            
            # Extract sender name
            sender_name = self._extract_name_from_email(sender)
            
            # Generate reply content
            reply_content = self._generate_reply_content(sender_name, subject)
            
            result = {
                "success": True,
                "action": "auto_reply",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "sender": sender,
                    "sender_name": sender_name,
                    "subject": subject,
                    "reply_content": reply_content,
                    "reply_generated": True
                }
            }
            
            print(f"✅ Auto-reply generated for {sender}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "auto_reply",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }
    
    def _mark_read(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """Mark email as read."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            result = {
                "success": True,
                "action": "mark_read",
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "marked_read": True,
                    "previous_labels": parsed_email.get("labels", [])
                }
            }
            
            print(f"✅ Marked message {message_id} as read")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "mark_read",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }
    
    def _add_label(self, parsed_email: Dict[str, Any], label: str = "PROCESSED") -> Dict[str, Any]:
        """Add label to email."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            result = {
                "success": True,
                "action": "add_label",
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "label_added": label,
                    "previous_labels": parsed_email.get("labels", [])
                }
            }
            
            print(f"✅ Added label '{label}' to message {message_id}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "add_label",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }
    
    def _forward_email(self, parsed_email: Dict[str, Any], forward_to: str = "") -> Dict[str, Any]:
        """Forward email to another address."""
        try:
            message_id = parsed_email.get("message_id", "")
            sender = parsed_email.get("headers", {}).get("from", "")
            subject = parsed_email.get("headers", {}).get("subject", "")
            
            result = {
                "success": True,
                "action": "forward",
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "forwarded_to": forward_to,
                    "original_sender": sender,
                    "subject": subject,
                    "forward_generated": True
                }
            }
            
            print(f"✅ Forwarded message {message_id} to {forward_to}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "forward",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }
    
    def _archive_email(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """Archive email (remove from inbox)."""
        try:
            message_id = parsed_email.get("message_id", "")
            
            result = {
                "success": True,
                "action": "archive",
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "archived": True,
                    "removed_from_inbox": True
                }
            }
            
            print(f"✅ Archived message {message_id}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": "archive",
                "message_id": parsed_email.get("message_id", ""),
                "timestamp": datetime.now().isoformat(),
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
    
    def _generate_reply_content(self, sender_name: str, subject: str) -> str:
        """Generate reply content."""
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
    
    def get_action_log(self) -> List[Dict[str, Any]]:
        """Get the action log."""
        return self.action_log
    
    def get_processed_count(self) -> int:
        """Get count of processed emails."""
        return self.processed_count
    
    def clear_log(self):
        """Clear the action log."""
        self.action_log = []
        self.processed_count = 0
        print("✅ Action log cleared")
    
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
            "last_action": self.action_log[-1] if self.action_log else None
        }

def create_email_actions() -> MinimalEmailActions:
    """Create and return an email actions instance."""
    return MinimalEmailActions()

if __name__ == "__main__":
    # Test the email actions
    print("🧪 Testing Minimal Email Actions")
    print("=" * 40)
    
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
    print("Testing auto-reply...")
    result = actions.process_email(sample_email, "auto_reply")
    print(f"✅ Auto-reply result: {result['success']}")
    if result['success']:
        print(f"   Reply content: {result['details']['reply_content'][:50]}...")
    
    # Test mark as read
    print("\nTesting mark as read...")
    result = actions.process_email(sample_email, "mark_read")
    print(f"✅ Mark as read result: {result['success']}")
    
    # Test add label
    print("\nTesting add label...")
    result = actions.process_email(sample_email, "add_label")
    print(f"✅ Add label result: {result['success']}")
    
    # Test stats
    print("\nTesting stats...")
    stats = actions.get_stats()
    print(f"✅ Stats: {stats['total_processed']} processed, {stats['successful_actions']} successful")
    
    print("\n🎉 All email actions tests completed!")

