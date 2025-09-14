#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Main Entry Point
Lightweight CLI interface using minimal core services.
"""

import sys
import argparse
from pathlib import Path

# Import our minimal services
from core.minimal_config import get_config
from core.minimal_auth import setup_auth, authenticate_gmail
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_gmail_utils import MinimalGmailService
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_crm_service import MinimalCRMService

class MinimalFikiriCLI:
    """Minimal CLI for Fikiri Solutions."""
    
    def __init__(self):
        """Initialize the minimal CLI."""
        self.config = get_config()
        self.parser = MinimalEmailParser()
        self.gmail_service = MinimalGmailService()
        self.email_actions = MinimalEmailActions()
        self.crm_service = MinimalCRMService()
    
    def setup(self):
        """Setup authentication."""
        print("🔐 Fikiri Solutions - Setup")
        print("=" * 40)
        
        if setup_auth():
            print("✅ Setup completed successfully!")
            return True
        else:
            print("❌ Setup incomplete. Please follow the instructions above.")
            return False
    
    def status(self):
        """Check system status."""
        print("📊 Fikiri Solutions - Status")
        print("=" * 40)
        
        # Check config
        print(f"✅ Configuration loaded")
        print(f"   Debug mode: {self.config.is_debug()}")
        print(f"   Dry run: {self.config.is_dry_run()}")
        print(f"   Gmail max results: {self.config.gmail_max_results}")
        
        # Check authentication
        print(f"\n🔐 Authentication status:")
        if authenticate_gmail():
            print("   ✅ Authenticated")
        else:
            print("   ❌ Not authenticated")
        
        # Check core files
        print(f"\n📁 Core files:")
        core_files = [
            "core/minimal_config.py",
            "core/minimal_auth.py", 
            "core/minimal_email_parser.py"
        ]
        
        for file_path in core_files:
            if Path(file_path).exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path}")
        
        return True
    
    def test(self):
        """Test core functionality."""
        print("🧪 Fikiri Solutions - Test")
        print("=" * 40)
        
        # Test config
        print("Testing configuration...")
        config = get_config()
        print(f"✅ Config loaded: {config.gmail_max_results} max results")
        
        # Test auth
        print("\nTesting authentication...")
        if authenticate_gmail():
            print("✅ Authentication working")
        else:
            print("❌ Authentication not working")
        
        # Test email parser
        print("\nTesting email parser...")
        sample_message = {
            "id": "test123",
            "threadId": "thread123", 
            "snippet": "Test email",
            "labelIds": ["UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"}
                ],
                "mimeType": "text/plain",
                "body": {"data": "SGVsbG8gd29ybGQ="}  # "Hello world" in base64
            }
        }
        
        parsed = self.parser.parse_message(sample_message)
        print(f"✅ Email parser working: {self.parser.get_sender(parsed)}")
        
        # Test Gmail service
        print("\nTesting Gmail service...")
        print(f"✅ Gmail service created: {not self.gmail_service.is_authenticated()}")
        
        # Test email actions
        print("\nTesting email actions...")
        result = self.email_actions.process_email(parsed, "auto_reply")
        print(f"✅ Email actions working: {result['success']}")
        
        # Test CRM service
        print("\nTesting CRM service...")
        lead = self.crm_service.add_lead("test@example.com", "Test User")
        print(f"✅ CRM service working: {lead.email}")
        
        print("\n🎉 All tests completed!")
        return True
    
    def config_show(self):
        """Show current configuration."""
        print("⚙️  Fikiri Solutions - Configuration")
        print("=" * 40)
        
        config = get_config()
        print(f"Gmail credentials: {config.gmail_credentials_path}")
        print(f"Gmail token: {config.gmail_token_path}")
        print(f"Gmail max results: {config.gmail_max_results}")
        print(f"Auto reply enabled: {config.auto_reply_enabled}")
        print(f"Debug mode: {config.is_debug()}")
        print(f"Dry run: {config.is_dry_run()}")
        
        return True
    
    def config_save(self):
        """Save current configuration."""
        print("💾 Saving configuration...")
        self.config.save()
        return True
    
    def crm_stats(self):
        """Show CRM statistics."""
        print("📊 Fikiri Solutions - CRM Statistics")
        print("=" * 40)
        
        stats = self.crm_service.get_lead_stats()
        print(f"Total leads: {stats['total_leads']}")
        print(f"Recent leads (7 days): {stats['recent_leads']}")
        
        if stats['stages']:
            print(f"\nLeads by stage:")
            for stage, count in stats['stages'].items():
                print(f"  {stage}: {count}")
        
        if stats['sources']:
            print(f"\nLeads by source:")
            for source, count in stats['sources'].items():
                print(f"  {source}: {count}")
        
        if stats['tags']:
            print(f"\nLeads by tag:")
            for tag, count in stats['tags'].items():
                print(f"  {tag}: {count}")
        
        return True
    
    def process_emails(self, max_emails: int = 5):
        """Process emails (demo mode)."""
        print("📧 Fikiri Solutions - Email Processing")
        print("=" * 40)
        
        if not self.gmail_service.is_authenticated():
            print("❌ Gmail not authenticated. Run setup first.")
            return False
        
        print(f"Processing up to {max_emails} emails...")
        
        # Get messages
        messages = self.gmail_service.get_messages("is:unread", max_emails)
        
        if not messages:
            print("✅ No unread messages found")
            return True
        
        processed_count = 0
        for message in messages:
            try:
                # Get full message
                full_message = self.gmail_service.get_message(message['id'])
                if not full_message:
                    continue
                
                # Parse message
                parsed = self.parser.parse_message(full_message)
                
                # Extract sender email for CRM
                sender_email = self.parser.get_sender(parsed)
                sender_name = self._extract_name_from_email(sender_email)
                
                # Add to CRM
                lead = self.crm_service.find_lead_by_email(sender_email)
                if not lead:
                    lead = self.crm_service.add_lead(sender_email, sender_name, "email")
                
                # Process email
                result = self.email_actions.process_email(parsed, "auto_reply")
                
                if result['success']:
                    # Record contact
                    self.crm_service.record_contact(lead.id, "email")
                    
                    # Mark as read
                    self.gmail_service.mark_as_read(message['id'])
                    
                    processed_count += 1
                    print(f"✅ Processed email from {sender_email}")
                
            except Exception as e:
                print(f"❌ Error processing message {message['id']}: {e}")
        
        print(f"\n🎉 Processed {processed_count} emails successfully!")
        return True
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract name from email address."""
        if not email:
            return "Unknown"
        
        # Try to extract name from "Name <email@domain.com>" format
        if "<" in email and ">" in email:
            name_part = email.split("<")[0].strip()
            if name_part:
                return name_part
        
        # Extract name from email address
        email_part = email.split("@")[0]
        name = email_part.replace(".", " ").replace("_", " ")
        name = " ".join(word.capitalize() for word in name.split())
        
        return name if name else "Unknown"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fikiri Solutions - Minimal Gmail Lead Responder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_minimal.py setup          # Setup authentication
  python main_minimal.py status         # Check system status
  python main_minimal.py test           # Test core functionality
  python main_minimal.py config         # Show configuration
  python main_minimal.py config --save # Save configuration
  python main_minimal.py crm            # Show CRM statistics
  python main_minimal.py process        # Process emails
  python main_minimal.py process --max 10 # Process up to 10 emails
        """
    )
    
    parser.add_argument(
        'command',
        choices=['setup', 'status', 'test', 'config', 'crm', 'process'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save configuration (use with config command)'
    )
    
    parser.add_argument(
        '--max',
        type=int,
        default=5,
        help='Maximum number of emails to process (use with process command)'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = MinimalFikiriCLI()
    
    try:
        if args.command == 'setup':
            success = cli.setup()
        elif args.command == 'status':
            success = cli.status()
        elif args.command == 'test':
            success = cli.test()
        elif args.command == 'config':
            if args.save:
                success = cli.config_save()
            else:
                success = cli.config_show()
        elif args.command == 'crm':
            success = cli.crm_stats()
        elif args.command == 'process':
            success = cli.process_emails(args.max)
        else:
            parser.print_help()
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
