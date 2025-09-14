#!/usr/bin/env python3
"""
Fikiri Solutions - Gmail Lead Responder
Main entry point with CLI interface for automated email processing.

This module provides a command-line interface for the Gmail Lead Responder,
allowing users to authenticate, process emails, and manage automated responses.
"""

import os
import sys
import argparse
import logging
import json
# Removed numpy import that causes hanging
# import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

# Minimal imports only
print("✅ Fikiri Solutions - Minimal Version Loading...")

# Import configuration
from core.config import get_config, Config, GmailConfig, EmailConfig, LoggingConfig

# Import core modules
from core.email_parser import EmailParser
from core.gmail_utils import GmailService
from core.actions import EmailActions
from core.auth import GmailAuthenticator, authenticate_gmail
from core.crm_service import CRMService, Lead
from core.crm_followups import CRMFollowupService


class FikiriCLI:
    """Command-line interface for Fikiri Solutions Gmail Lead Responder."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.config = get_config()
        self.setup_logging()
        self.gmail_service: Optional[GmailService] = None
        self.email_parser = EmailParser()
        self.email_actions: Optional[EmailActions] = None
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        log_config = self.config.logging
        
        logging.basicConfig(
            level=getattr(logging, log_config.level),
            format=log_config.format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_config.file_path) if log_config.file_path else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None) -> bool:
        """
        Authenticate with Gmail API.
        
        Args:
            credentials_path: Path to credentials file (optional)
            token_path: Path to token file (optional)
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            creds_path = credentials_path or self.config.gmail.credentials_path
            token_path = token_path or self.config.gmail.token_path
            
            authenticator = GmailAuthenticator(creds_path, token_path)
            service = authenticator.authenticate()
            
            self.gmail_service = GmailService(service)
            self.email_actions = EmailActions(service)
            
            self.logger.info("✅ Gmail authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Authentication failed: {e}")
            return False
    
    def list_emails(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List emails matching the given query.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of email messages
        """
        if not self.gmail_service:
            self.logger.error("❌ Not authenticated. Run 'authenticate' first.")
            return []
        
        try:
            messages = self.gmail_service.list_messages(query, max_results)
            self.logger.info(f"📧 Found {len(messages)} messages")
            return messages
        except Exception as e:
            self.logger.error(f"❌ Failed to list emails: {e}")
            return []
    
    def process_email(self, msg_id: str, auto_reply: bool = False) -> Dict[str, Any]:
        """
        Process a single email message.
        
        Args:
            msg_id: Gmail message ID
            auto_reply: Whether to send automatic reply
            
        Returns:
            Processed email data
        """
        if not self.gmail_service:
            self.logger.error("❌ Not authenticated. Run 'authenticate' first.")
            return {}
        
        try:
            # Get full message
            message = self.gmail_service.get_message(msg_id)
            
            # Parse message
            parsed_data = self.email_parser.parse_message(message)
            
            # Log processing
            sender = parsed_data.get('headers', {}).get('from', 'Unknown')
            subject = parsed_data.get('headers', {}).get('subject', 'No Subject')
            self.logger.info(f"📨 Processing email from {sender}: {subject}")
            
            # Auto-reply if enabled
            if auto_reply and self.config.email.auto_reply_enabled:
                self.send_auto_reply(msg_id, parsed_data)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process email {msg_id}: {e}")
            return {}
    
    def send_auto_reply(self, msg_id: str, parsed_data: Dict[str, Any]) -> bool:
        """
        Send automatic reply to an email.
        
        Args:
            msg_id: Original message ID
            parsed_data: Parsed email data
            
        Returns:
            True if reply sent successfully, False otherwise
        """
        if not self.gmail_service:
            return False
        
        try:
            sender = parsed_data.get('headers', {}).get('from', '')
            subject = parsed_data.get('headers', {}).get('subject', '')
            
            # Generate reply text
            reply_text = self.generate_reply_text(sender, subject, parsed_data)
            
            if self.config.dry_run:
                self.logger.info(f"🔍 DRY RUN: Would send reply to {sender}")
                self.logger.info(f"Reply content: {reply_text}")
                return True
            
            # Send reply
            result = self.gmail_service.send_reply(msg_id, reply_text)
            self.logger.info(f"✅ Auto-reply sent to {sender}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send auto-reply: {e}")
            return False
    
    def generate_reply_text(self, sender: str, subject: str, parsed_data: Dict[str, Any]) -> str:
        """
        Generate automatic reply text.
        
        Args:
            sender: Sender email address
            subject: Email subject
            parsed_data: Parsed email data
            
        Returns:
            Generated reply text
        """
        # Extract sender name
        sender_name = sender.split('@')[0] if '@' in sender else sender
        
        # Use template if available
        template = self.config.email.reply_template
        if template:
            reply_text = template.format(
                sender_name=sender_name,
                sender_email=sender,
                subject=subject
            )
        else:
            # Default reply
            reply_text = f"""Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team"""
        
        # Add signature if available
        if self.config.email.signature:
            reply_text += f"\n\n{self.config.email.signature}"
        
        return reply_text
    
    def batch_process(self, query: str = "is:unread", max_results: int = 10, auto_reply: bool = False) -> Dict[str, Any]:
        """
        Process multiple emails in batch.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of emails to process
            auto_reply: Whether to send automatic replies
            
        Returns:
            Batch processing results
        """
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'replies_sent': 0,
            'errors': []
        }
        
        # Get list of emails
        messages = self.list_emails(query, max_results)
        
        for message in messages:
            msg_id = message['id']
            results['processed'] += 1
            
            try:
                # Process email
                parsed_data = self.process_email(msg_id, auto_reply)
                
                if parsed_data:
                    results['successful'] += 1
                    if auto_reply and self.config.email.auto_reply_enabled:
                        results['replies_sent'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Message {msg_id}: {str(e)}")
                self.logger.error(f"❌ Error processing {msg_id}: {e}")
        
        self.logger.info(f"📊 Batch processing complete: {results['successful']}/{results['processed']} successful")
        return results
    
    def show_status(self) -> None:
        """Show current status and configuration."""
        print("🔍 Fikiri Solutions - Gmail Lead Responder Status")
        print("=" * 50)
        print(f"Authenticated: {'✅ Yes' if self.gmail_service else '❌ No'}")
        print(f"Debug Mode: {'✅ On' if self.config.debug else '❌ Off'}")
        print(f"Dry Run Mode: {'✅ On' if self.config.dry_run else '❌ Off'}")
        print(f"Auto Reply: {'✅ Enabled' if self.config.email.auto_reply_enabled else '❌ Disabled'}")
        print(f"Credentials: {self.config.gmail.credentials_path}")
        print(f"Token: {self.config.gmail.token_path}")
        print(f"Max Results: {self.config.gmail.max_results}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fikiri Solutions - Gmail Lead Responder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Authenticate with Gmail
  python main.py auth
  
  # List unread emails
  python main.py list --query "is:unread" --max 5
  
  # Process emails with auto-reply
  python main.py process --query "is:unread" --auto-reply
  
  # Show status
  python main.py status
  
  # Dry run mode
  python main.py process --query "is:unread" --dry-run
        """
    )
    
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Auth command
    auth_parser = subparsers.add_parser('auth', help='Authenticate with Gmail API')
    auth_parser.add_argument('--credentials', help='Path to credentials file')
    auth_parser.add_argument('--token', help='Path to token file')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List emails')
    list_parser.add_argument('--query', default='', help='Gmail search query')
    list_parser.add_argument('--max', type=int, default=10, help='Maximum number of results')
    
    # Fetch command (alias for list with better naming)
    fetch_parser = subparsers.add_parser('fetch', help='Fetch and display emails')
    fetch_parser.add_argument('--query', default='is:unread', help='Gmail search query')
    fetch_parser.add_argument('--max', type=int, default=10, help='Maximum number of results')
    fetch_parser.add_argument('--detailed', action='store_true', help='Show detailed email content')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process emails')
    process_parser.add_argument('--query', default='is:unread', help='Gmail search query')
    process_parser.add_argument('--max', type=int, default=10, help='Maximum number of emails to process')
    process_parser.add_argument('--auto-reply', action='store_true', help='Send automatic replies')
    process_parser.add_argument('--msg-id', help='Process specific message ID')
    
    # Reply command
    reply_parser = subparsers.add_parser('reply', help='Send test replies')
    reply_parser.add_argument('--msg-id', required=True, help='Message ID to reply to')
    reply_parser.add_argument('--text', help='Custom reply text')
    reply_parser.add_argument('--template', help='Use specific template')
    
    # Actions command
    actions_parser = subparsers.add_parser('actions', help='Email management actions')
    actions_parser.add_argument('--msg-id', required=True, help='Message ID to act on')
    actions_parser.add_argument('--action', required=True, choices=['read', 'unread', 'archive', 'delete', 'star', 'important'], help='Action to perform')
    
    # CRM command group
    crm_parser = subparsers.add_parser('crm', help='CRM operations')
    crm_sub = crm_parser.add_subparsers(dest='crm_command', help='CRM subcommands')

    crm_ingest = crm_sub.add_parser('ingest', help='Ingest raw leads (JSON string or CSV)')
    crm_ingest.add_argument('--json', help='JSON array of leads')
    crm_ingest.add_argument('--from-csv', help='Path to CSV file with leads')

    crm_list = crm_sub.add_parser('list', help='List stored leads')

    crm_follow = crm_sub.add_parser('followup', help='Generate or send follow-up')
    crm_follow.add_argument('--stage', help='Filter by stage')
    crm_follow.add_argument('--send', action='store_true', help='Actually send emails')

    crm_stage = crm_sub.add_parser('stage', help='Update lead stage')
    crm_stage.add_argument('--id', required=True, help='Lead ID')
    crm_stage.add_argument('--to', required=True, help='New stage')

    # Status command
    subparsers.add_parser('status', help='Show current status')
    
    # Workflow command group
    workflow_parser = subparsers.add_parser('workflow', help='Business Workflow Automations')
    workflow_sub = workflow_parser.add_subparsers(dest='workflow_command', help='Workflow subcommands')

    # Schedule email processing
    workflow_email = workflow_sub.add_parser('schedule-email', help='Schedule automated email processing')
    workflow_email.add_argument('--query', default='is:unread', help='Gmail search query')
    workflow_email.add_argument('--interval', type=int, default=30, help='Processing interval in minutes')
    workflow_email.add_argument('--max-emails', type=int, default=10, help='Maximum emails per run')
    workflow_email.add_argument('--auto-reply', action='store_true', help='Send automatic replies')

    # Schedule CRM follow-ups
    workflow_crm = workflow_sub.add_parser('schedule-crm', help='Schedule CRM follow-up processing')
    workflow_crm.add_argument('--stage', help='Filter leads by stage')
    workflow_crm.add_argument('--interval-hours', type=int, default=24, help='Processing interval in hours')
    workflow_crm.add_argument('--send', action='store_true', help='Actually send follow-up emails')

    # Schedule lead ingestion
    workflow_leads = workflow_sub.add_parser('schedule-leads', help='Schedule lead ingestion')
    workflow_leads.add_argument('--source', default='webhook', help='Lead source')
    workflow_leads.add_argument('--interval', type=int, default=15, help='Processing interval in minutes')

    # Business hours workflow
    workflow_business = workflow_sub.add_parser('schedule-business', help='Schedule business hours workflow')
    workflow_business.add_argument('--type', choices=['email_processing', 'crm_followups'], default='email_processing', help='Workflow type')

    # List workflows
    workflow_sub.add_parser('list', help='List active workflows')

    # Stop workflows
    workflow_stop = workflow_sub.add_parser('stop', help='Stop workflows')
    workflow_stop.add_argument('--job-id', help='Stop specific workflow by job ID')
    workflow_stop.add_argument('--all', action='store_true', help='Stop all workflows')

    # Start/stop scheduler
    workflow_sub.add_parser('start', help='Start workflow scheduler')
    workflow_sub.add_parser('stop-scheduler', help='Stop workflow scheduler')
    
    # Chatbot command group
    chatbot_parser = subparsers.add_parser('chatbot', help='Chatbot Integration & Smart FAQs')
    chatbot_sub = chatbot_parser.add_subparsers(dest='chatbot_command', help='Chatbot subcommands')

    # Chat with bot
    chatbot_chat = chatbot_sub.add_parser('chat', help='Start interactive chat session')
    chatbot_chat.add_argument('--session-id', help='Continue existing session')
    chatbot_chat.add_argument('--user-id', help='User identifier')

    # Query bot
    chatbot_query = chatbot_sub.add_parser('query', help='Send a single query to the bot')
    chatbot_query.add_argument('query', help='Query to send to the bot')
    chatbot_query.add_argument('--session-id', help='Session ID to use')
    chatbot_query.add_argument('--user-id', help='User identifier')

    # FAQ management
    chatbot_faq = chatbot_sub.add_parser('faq', help='FAQ management')
    chatbot_faq_sub = chatbot_faq.add_subparsers(dest='faq_command', help='FAQ subcommands')
    
    chatbot_faq_sub.add_parser('list', help='List all FAQs')
    chatbot_faq_sub.add_parser('search', help='Search FAQs').add_argument('query', help='Search query')
    
    chatbot_faq_add = chatbot_faq_sub.add_parser('add', help='Add new FAQ')
    chatbot_faq_add.add_argument('--question', required=True, help='FAQ question')
    chatbot_faq_add.add_argument('--answer', required=True, help='FAQ answer')
    chatbot_faq_add.add_argument('--keywords', help='Comma-separated keywords')
    chatbot_faq_add.add_argument('--category', default='general', help='FAQ category')
    chatbot_faq_add.add_argument('--priority', type=int, default=1, help='Priority (1-5)')
    
    chatbot_faq_update = chatbot_faq_sub.add_parser('update', help='Update FAQ')
    chatbot_faq_update.add_argument('--id', required=True, help='FAQ ID')
    chatbot_faq_update.add_argument('--question', help='New question')
    chatbot_faq_update.add_argument('--answer', help='New answer')
    chatbot_faq_update.add_argument('--keywords', help='New keywords')
    chatbot_faq_update.add_argument('--category', help='New category')
    chatbot_faq_update.add_argument('--priority', type=int, help='New priority')
    
    chatbot_faq_sub.add_parser('delete', help='Delete FAQ').add_argument('--id', required=True, help='FAQ ID')

    # Session management
    chatbot_sub.add_parser('sessions', help='List active chat sessions')
    chatbot_sub.add_parser('session-history', help='Get session history').add_argument('--session-id', required=True, help='Session ID')
    
    # AI Creative command group
    ai_parser = subparsers.add_parser('ai-creative', help='AI-Enhanced Creative Services')
    ai_sub = ai_parser.add_subparsers(dest='ai_command', help='AI Creative subcommands')

    # Content generation
    ai_generate = ai_sub.add_parser('generate', help='Generate AI content')
    ai_generate.add_argument('--type', choices=['email', 'blog', 'social', 'proposal', 'summary'], default='email', help='Content type')
    ai_generate.add_argument('--topic', required=True, help='Content topic')
    ai_generate.add_argument('--tone', default='professional', help='Content tone')
    ai_generate.add_argument('--length', choices=['short', 'medium', 'long'], default='medium', help='Content length')
    ai_generate.add_argument('--audience', default='general', help='Target audience')
    ai_generate.add_argument('--requirements', help='Comma-separated requirements')

    # Document ingestion
    ai_ingest = ai_sub.add_parser('ingest', help='Ingest documents for RAG')
    ai_ingest.add_argument('--file', help='Document file path')
    ai_ingest.add_argument('--text', help='Document text content')
    ai_ingest.add_argument('--metadata', help='JSON metadata')

    # ML model training
    ai_train = ai_sub.add_parser('train', help='Train ML models')
    ai_train.add_argument('--type', choices=['regression', 'classification'], required=True, help='Model type')
    ai_train.add_argument('--algorithm', help='Specific algorithm (linear, lasso, ridge, random_forest, svm, naive_bayes)')
    ai_train.add_argument('--data-file', help='Training data file (CSV)')

    # Analytics and insights
    ai_sub.add_parser('analytics', help='Get AI Creative analytics')
    ai_sub.add_parser('models', help='List trained models')

    # Sentiment analysis
    ai_sentiment = ai_sub.add_parser('sentiment', help='Analyze text sentiment')
    ai_sentiment.add_argument('--text', required=True, help='Text to analyze')

    # Business profile management
    ai_profile = ai_sub.add_parser('profile', help='Manage business profile')
    ai_profile_sub = ai_profile.add_subparsers(dest='profile_command', help='Profile subcommands')
    
    ai_profile_sub.add_parser('show', help='Show current business profile')
    ai_profile_sub.add_parser('update', help='Update business profile').add_argument('--type', help='Business type')
    ai_profile_sub.add_parser('reset', help='Reset to default profile')
    
    # Self-Training Chatbot command group
    stc_parser = subparsers.add_parser('self-training', help='Self-Training Chatbot System')
    stc_sub = stc_parser.add_subparsers(dest='stc_command', help='Self-Training subcommands')

    # Chat and learning
    stc_chat = stc_sub.add_parser('chat', help='Interactive chat with learning')
    stc_chat.add_argument('--session-id', help='Continue existing session')
    stc_chat.add_argument('--user-id', help='User ID for session tracking')

    stc_query = stc_sub.add_parser('query', help='Single query with learning')
    stc_query.add_argument('--query', required=True, help='Query to process')
    stc_query.add_argument('--session-id', help='Session ID')
    stc_query.add_argument('--user-id', help='User ID')

    # Learning management
    stc_feedback = stc_sub.add_parser('feedback', help='Provide feedback for learning')
    stc_feedback.add_argument('--session-id', required=True, help='Session ID')
    stc_feedback.add_argument('--feedback', required=True, help='Feedback (good/bad/helpful/unhelpful)')

    stc_analytics = stc_sub.add_parser('analytics', help='Get learning analytics')
    stc_profile = stc_sub.add_parser('profile', help='Manage business learning profile')
    stc_profile_sub = stc_profile.add_subparsers(dest='profile_command', help='Profile subcommands')
    
    stc_profile_sub.add_parser('show', help='Show business learning profile')
    stc_profile_update = stc_profile_sub.add_parser('update', help='Update business profile')
    stc_profile_update.add_argument('--type', help='Business type')
    stc_profile_update.add_argument('--keywords', help='Comma-separated keywords')

    # Service Learning command group
    sl_parser = subparsers.add_parser('service-learning', help='Service Learning Management')
    sl_sub = sl_parser.add_subparsers(dest='sl_command', help='Service Learning subcommands')

    sl_sub.add_parser('analytics', help='Get service learning analytics')
    sl_sub.add_parser('insights', help='Get service insights').add_argument('--service', required=True, help='Service name')
    sl_sub.add_parser('recommendations', help='Get improvement recommendations').add_argument('--service', required=True, help='Service name')
    sl_sub.add_parser('cross-service', help='Get cross-service analytics')
    sl_sub.add_parser('integrate', help='Integrate learning with services')
    
    # Advanced Self-Learning Chatbot command group
    ac_parser = subparsers.add_parser('advanced-chatbot', help='Advanced Self-Learning Chatbot System')
    ac_sub = ac_parser.add_subparsers(dest='ac_command', help='Advanced Chatbot subcommands')

    # Chat and interaction
    ac_chat = ac_sub.add_parser('chat', help='Chat with advanced chatbot')
    ac_chat.add_argument('--message', required=True, help='Message to send')
    ac_chat.add_argument('--session-id', help='Session ID')
    ac_chat.add_argument('--user-id', help='User ID')

    # Training and retraining
    ac_train = ac_sub.add_parser('train', help='Train new models')
    ac_train.add_argument('--data-file', help='Training data file path')
    ac_train.add_argument('--model-type', default='nlp', help='Model type (regression, classification, nlp)')
    ac_train.add_argument('--algorithm', default='naive_bayes', help='ML algorithm to use')

    ac_retrain = ac_sub.add_parser('retrain', help='Retrain existing models')
    ac_retrain.add_argument('--model-id', help='Specific model ID to retrain')

    # Data ingestion
    ac_ingest = ac_sub.add_parser('ingest', help='Ingest data for training')
    ac_ingest_sub = ac_ingest.add_subparsers(dest='ingest_type', help='Data source type')
    
    ac_ingest_sub.add_parser('csv', help='Ingest CSV data').add_argument('--file-path', required=True, help='CSV file path')
    ac_ingest_sub.add_parser('google-form', help='Ingest Google Form data').add_argument('--form-data', help='Form data JSON')
    ac_ingest_sub.add_parser('crm', help='Ingest CRM data').add_argument('--crm-data', help='CRM data JSON')
    ac_ingest_sub.add_parser('email', help='Ingest email metadata').add_argument('--email-data', help='Email data JSON')

    # Management
    ac_sub.add_parser('logs', help='Get training logs')
    ac_sub.add_parser('models', help='List all model versions')
    ac_sub.add_parser('status', help='Get system status')
    ac_sub.add_parser('pause', help='Pause retraining')
    ac_sub.add_parser('resume', help='Resume retraining')
    ac_sub.add_parser('reset', help='Reset all models')
    
    # Chatbot Tier Management
    ct_parser = subparsers.add_parser('chatbot-tiers', help='Chatbot Tier Management')
    ct_sub = ct_parser.add_subparsers(dest='ct_command', help='Chatbot Tier subcommands')
    
    # List tiers
    ct_sub.add_parser('list', help='List available chatbot tiers')
    
    # Chat with tier
    ct_chat = ct_sub.add_parser('chat', help='Chat with tiered chatbot')
    ct_chat.add_argument('--tier', choices=['basic', 'professional', 'enterprise'], 
                        default='basic', help='Chatbot tier to use')
    ct_chat.add_argument('--message', required=True, help='Message to send')
    ct_chat.add_argument('--session-id', help='Session ID for conversation')
    ct_chat.add_argument('--user-id', default='demo-user', help='User ID')
    
    # Get tier features
    ct_features = ct_sub.add_parser('features', help='Get tier features')
    ct_features.add_argument('--tier', choices=['basic', 'professional', 'enterprise'], 
                           help='Specific tier to show features for')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = FikiriCLI()
    
    # Override config if specified
    if args.config:
        from core.config import set_config_path
        set_config_path(args.config)
        cli.config = get_config()
    
    if args.debug:
        cli.config.debug = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.dry_run:
        cli.config.dry_run = True
    
    # Execute command
    try:
        if args.command == 'auth':
            success = cli.authenticate(args.credentials, args.token)
            if success:
                print("✅ Authentication successful!")
            else:
                print("❌ Authentication failed!")
                sys.exit(1)
        
        elif args.command == 'list':
            if not cli.authenticate():
                print("❌ Authentication required!")
                sys.exit(1)
            
            messages = cli.list_emails(args.query, args.max)
            for i, msg in enumerate(messages, 1):
                print(f"{i}. Message ID: {msg['id']}")
        
        elif args.command == 'fetch':
            if not cli.authenticate():
                print("❌ Authentication required!")
                sys.exit(1)
            
            messages = cli.list_emails(args.query, args.max)
            print(f"📧 Fetched {len(messages)} emails")
            
            for i, msg in enumerate(messages, 1):
                msg_id = msg['id']
                print(f"\n📨 Email {i}/{len(messages)} (ID: {msg_id})")
                
                if args.detailed:
                    # Get detailed email content
                    try:
                        full_message = cli.gmail_service.get_message(msg_id)
                        parsed_data = cli.email_parser.parse_message(full_message)
                        
                        sender = parsed_data.get('headers', {}).get('from', 'Unknown')
                        subject = parsed_data.get('headers', {}).get('subject', 'No Subject')
                        snippet = parsed_data.get('snippet', '')
                        
                        print(f"  👤 From: {sender}")
                        print(f"  📝 Subject: {subject}")
                        print(f"  📄 Snippet: {snippet}")
                        
                    except Exception as e:
                        print(f"  ❌ Error fetching details: {e}")
                else:
                    print(f"  📧 Message ID: {msg_id}")
        
        elif args.command == 'process':
            if not cli.authenticate():
                print("❌ Authentication required!")
                sys.exit(1)
            
            if args.msg_id:
                # Process single message
                result = cli.process_email(args.msg_id, args.auto_reply)
                if result:
                    print("✅ Message processed successfully!")
                else:
                    print("❌ Failed to process message!")
            else:
                # Batch process
                results = cli.batch_process(args.query, args.max, args.auto_reply)
                print(f"📊 Processed: {results['successful']}/{results['processed']}")
                if results['replies_sent'] > 0:
                    print(f"📧 Replies sent: {results['replies_sent']}")
        
        elif args.command == 'reply':
            if not cli.authenticate():
                print("❌ Authentication required!")
                sys.exit(1)
            
            try:
                if args.text:
                    reply_text = args.text
                elif args.template:
                    reply_text = cli.generate_reply_text("Test User", "Test Subject", {})
                else:
                    reply_text = "This is a test reply from Fikiri Solutions."
                
                if cli.config.dry_run:
                    print(f"🔍 DRY RUN: Would send reply to message {args.msg_id}")
                    print(f"📧 Reply content: {reply_text}")
                else:
                    result = cli.gmail_service.send_reply(args.msg_id, reply_text)
                    print(f"✅ Reply sent successfully! Message ID: {result['id']}")
                    
            except Exception as e:
                print(f"❌ Failed to send reply: {e}")
        
        elif args.command == 'actions':
            if not cli.authenticate():
                print("❌ Authentication required!")
                sys.exit(1)
            
            try:
                action_map = {
                    'read': cli.email_actions.mark_as_read,
                    'unread': cli.email_actions.mark_as_unread,
                    'archive': cli.email_actions.archive_message,
                    'delete': cli.email_actions.delete_message,
                    'star': cli.email_actions.star_message,
                    'important': cli.email_actions.mark_as_important
                }
                
                action_func = action_map[args.action]
                
                if cli.config.dry_run:
                    print(f"🔍 DRY RUN: Would {args.action} message {args.msg_id}")
                else:
                    success = action_func(args.msg_id)
                    if success:
                        print(f"✅ Successfully {args.action}ed message {args.msg_id}")
                    else:
                        print(f"❌ Failed to {args.action} message {args.msg_id}")
                        
            except Exception as e:
                print(f"❌ Action failed: {e}")
        
        elif args.command == 'status':
            cli.show_status()
        
        elif args.command == 'workflow':
            # Start scheduler if not running
            if not workflow_manager.scheduler.running:
                workflow_manager.start()
            
            if args.workflow_command == 'schedule-email':
                job_id = workflow_manager.schedule_email_processing(
                    query=args.query,
                    interval_minutes=args.interval,
                    max_emails=args.max_emails,
                    auto_reply=args.auto_reply
                )
                print(f"✅ Scheduled email processing: {job_id}")
                print(f"📧 Query: {args.query}")
                print(f"⏰ Interval: {args.interval} minutes")
                print(f"📊 Max emails: {args.max_emails}")
                print(f"🤖 Auto-reply: {'Yes' if args.auto_reply else 'No'}")
            
            elif args.workflow_command == 'schedule-crm':
                job_id = workflow_manager.schedule_crm_followups(
                    stage_filter=args.stage,
                    interval_hours=args.interval_hours,
                    send_emails=args.send
                )
                print(f"✅ Scheduled CRM follow-ups: {job_id}")
                print(f"📊 Stage filter: {args.stage or 'all'}")
                print(f"⏰ Interval: {args.interval_hours} hours")
                print(f"📧 Send emails: {'Yes' if args.send else 'No (preview only)'}")
            
            elif args.workflow_command == 'schedule-leads':
                job_id = workflow_manager.schedule_lead_ingestion(
                    source=args.source,
                    interval_minutes=args.interval
                )
                print(f"✅ Scheduled lead ingestion: {job_id}")
                print(f"📥 Source: {args.source}")
                print(f"⏰ Interval: {args.interval} minutes")
            
            elif args.workflow_command == 'schedule-business':
                job_id = workflow_manager.schedule_business_hours_workflow(
                    workflow_type=args.type
                )
                print(f"✅ Scheduled business hours workflow: {job_id}")
                print(f"🕒 Type: {args.type}")
                print(f"⏰ Schedule: 9 AM - 6 PM EST, every hour")
            
            elif args.workflow_command == 'list':
                workflows = workflow_manager.list_active_workflows()
                if workflows:
                    print(f"📋 Active Workflows ({len(workflows)}):")
                    for workflow in workflows:
                        print(f"  🔹 {workflow['job_id']}")
                        print(f"     Name: {workflow['name']}")
                        print(f"     Type: {workflow['type']}")
                        print(f"     Next run: {workflow['next_run']}")
                        print(f"     Trigger: {workflow['trigger']}")
                        print()
                else:
                    print("📋 No active workflows")
            
            elif args.workflow_command == 'stop':
                if args.all:
                    count = workflow_manager.stop_all_workflows()
                    print(f"⏹️ Stopped {count} workflows")
                elif args.job_id:
                    if workflow_manager.stop_workflow(args.job_id):
                        print(f"⏹️ Stopped workflow: {args.job_id}")
                    else:
                        print(f"❌ Failed to stop workflow: {args.job_id}")
                else:
                    print("❌ Please specify --job-id or --all")
            
            elif args.workflow_command == 'start':
                workflow_manager.start()
                print("🚀 Workflow scheduler started")
            
            elif args.workflow_command == 'stop-scheduler':
                workflow_manager.stop()
                print("⏹️ Workflow scheduler stopped")
            
            else:
                workflow_parser.print_help()
        
        elif args.command == 'chatbot':
            if args.chatbot_command == 'chat':
                # Interactive chat session
                session_id = args.session_id or chatbot_engine.create_session(args.user_id)
                print(f"🤖 Starting chat session: {session_id}")
                print("Type 'quit' or 'exit' to end the session")
                print("=" * 50)
                
                while True:
                    try:
                        user_input = input("\n👤 You: ").strip()
                        if user_input.lower() in ['quit', 'exit', 'bye']:
                            chatbot_engine.end_session(session_id)
                            print("👋 Chat session ended. Goodbye!")
                            break
                        
                        if not user_input:
                            continue
                        
                        response = chatbot_engine.process_query(session_id, user_input, args.user_id)
                        print(f"\n🤖 Bot: {response['answer']}")
                        
                        if response.get('suggestions'):
                            print(f"\n💡 Related questions:")
                            for suggestion in response['suggestions']:
                                print(f"   • {suggestion}")
                    
                    except KeyboardInterrupt:
                        chatbot_engine.end_session(session_id)
                        print("\n👋 Chat session ended. Goodbye!")
                        break
                    except Exception as e:
                        print(f"❌ Error: {e}")
            
            elif args.chatbot_command == 'query':
                # Single query
                session_id = args.session_id or chatbot_engine.create_session(args.user_id)
                response = chatbot_engine.process_query(session_id, args.query, args.user_id)
                
                print(f"🤖 Bot Response:")
                print(f"   {response['answer']}")
                print(f"\n📊 Confidence: {response['confidence']:.2f}")
                print(f"📂 Category: {response['category']}")
                print(f"🔍 Source: {response['source']}")
                
                if response.get('suggestions'):
                    print(f"\n💡 Related questions:")
                    for suggestion in response['suggestions']:
                        print(f"   • {suggestion}")
            
            elif args.chatbot_command == 'faq':
                if args.faq_command == 'list':
                    faqs = chatbot_engine.knowledge_base.faqs
                    print(f"📋 FAQ Knowledge Base ({len(faqs)} items):")
                    for faq_id, faq in faqs.items():
                        print(f"\n🔹 {faq_id}")
                        print(f"   Q: {faq.question}")
                        print(f"   A: {faq.answer[:100]}{'...' if len(faq.answer) > 100 else ''}")
                        print(f"   Category: {faq.category} | Priority: {faq.priority} | Usage: {faq.usage_count}")
                
                elif args.faq_command == 'search':
                    results = chatbot_engine.knowledge_base.search_faqs(args.query, top_k=5)
                    print(f"🔍 Search results for '{args.query}':")
                    for i, (faq, confidence) in enumerate(results, 1):
                        print(f"\n{i}. {faq.question}")
                        print(f"   Confidence: {confidence:.2f}")
                        print(f"   Answer: {faq.answer[:150]}{'...' if len(faq.answer) > 150 else ''}")
                
                elif args.faq_command == 'add':
                    keywords = args.keywords.split(',') if args.keywords else []
                    faq = FAQItem(
                        id=f"faq_{len(chatbot_engine.knowledge_base.faqs) + 1:03d}",
                        question=args.question,
                        answer=args.answer,
                        keywords=[k.strip() for k in keywords],
                        category=args.category,
                        priority=args.priority
                    )
                    chatbot_engine.knowledge_base.add_faq(faq)
                    print(f"✅ Added FAQ: {faq.id}")
                
                elif args.faq_command == 'update':
                    updates = {}
                    if args.question:
                        updates['question'] = args.question
                    if args.answer:
                        updates['answer'] = args.answer
                    if args.keywords:
                        updates['keywords'] = [k.strip() for k in args.keywords.split(',')]
                    if args.category:
                        updates['category'] = args.category
                    if args.priority:
                        updates['priority'] = args.priority
                    
                    chatbot_engine.knowledge_base.update_faq(args.id, **updates)
                    print(f"✅ Updated FAQ: {args.id}")
                
                elif args.faq_command == 'delete':
                    chatbot_engine.knowledge_base.delete_faq(args.id)
                    print(f"✅ Deleted FAQ: {args.id}")
                
                else:
                    chatbot_faq.print_help()
            
            elif args.chatbot_command == 'sessions':
                sessions = chatbot_engine.sessions
                if sessions:
                    print(f"📋 Active Chat Sessions ({len(sessions)}):")
                    for session_id, session in sessions.items():
                        status = "Active" if not session.resolved else "Ended"
                        print(f"  🔹 {session_id}")
                        print(f"     User: {session.user_id or 'Anonymous'}")
                        print(f"     Status: {status}")
                        print(f"     Messages: {len(session.messages)}")
                        print(f"     Last Activity: {session.last_activity}")
                        print()
                else:
                    print("📋 No active chat sessions")
            
            elif args.chatbot_command == 'session-history':
                history = chatbot_engine.get_session_history(args.session_id)
                if history:
                    print(f"📜 Chat History for {args.session_id}:")
                    for msg in history:
                        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                        print(f"\n{role_emoji} {msg['role'].title()}: {msg['content']}")
                        print(f"   Time: {msg['timestamp']}")
                else:
                    print(f"❌ No history found for session: {args.session_id}")
            
            else:
                chatbot_parser.print_help()
        
        elif args.command == 'ai-creative':
            if args.ai_command == 'generate':
                # Generate AI content
                requirements = args.requirements.split(',') if args.requirements else []
                
                content_request = ContentRequest(
                    content_type=args.type,
                    topic=args.topic,
                    tone=args.tone,
                    length=args.length,
                    target_audience=args.audience,
                    business_context={},
                    requirements=requirements
                )
                
                result = ai_creative_engine.generate_content(content_request)
                
                if 'error' in result:
                    print(f"❌ Content generation failed: {result['error']}")
                else:
                    print(f"🎨 Generated {args.type} content:")
                    print("=" * 50)
                    print(result['content'])
                    print("=" * 50)
                    print(f"📊 Context used: {result['context_used']} documents")
                    print(f"🤖 Model: {result['model']}")
                    print(f"⏰ Generated at: {result['generated_at']}")
            
            elif args.ai_command == 'ingest':
                # Ingest documents
                documents = []
                
                if args.file:
                    try:
                        with open(args.file, 'r') as f:
                            content = f.read()
                        documents.append({
                            'content': content,
                            'metadata': {
                                'file_path': args.file,
                                'doc_id': f"file_{Path(args.file).stem}"
                            }
                        })
                    except Exception as e:
                        print(f"❌ Failed to read file: {e}")
                        return
                
                if args.text:
                    metadata = {}
                    if args.metadata:
                        try:
                            metadata = json.loads(args.metadata)
                        except Exception as e:
                            print(f"⚠️ Invalid metadata JSON: {e}")
                    
                    documents.append({
                        'content': args.text,
                        'metadata': {
                            **metadata,
                            'doc_id': f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        }
                    })
                
                if documents:
                    success = ai_creative_engine.ingest_documents(documents)
                    if success:
                        print(f"✅ Successfully ingested {len(documents)} documents")
                    else:
                        print("❌ Document ingestion failed")
                else:
                    print("❌ No documents provided")
            
            elif args.ai_command == 'train':
                # Train ML models
                if not args.data_file:
                    print("❌ Training data file required")
                    return
                
                try:
                    import pandas as pd
                    df = pd.read_csv(args.data_file)
                    
                    # Simple feature extraction (would be more sophisticated in production)
                    X = df.select_dtypes(include=[np.number]).values
                    y = df.iloc[:, -1].values  # Last column as target
                    
                    if args.type == 'regression':
                        result = ai_creative_engine.ml_manager.train_regression_model(
                            X, y, args.algorithm or 'linear'
                        )
                    elif args.type == 'classification':
                        result = ai_creative_engine.ml_manager.train_classification_model(
                            X, y, args.algorithm or 'random_forest'
                        )
                    
                    if 'error' in result:
                        print(f"❌ Training failed: {result['error']}")
                    else:
                        print(f"✅ Model trained successfully: {result['model_name']}")
                        print(f"📊 Metrics: {result['metrics']}")
                        print(f"📈 Training samples: {result['training_samples']}")
                        print(f"📉 Validation samples: {result['validation_samples']}")
                
                except Exception as e:
                    print(f"❌ Training failed: {e}")
            
            elif args.ai_command == 'analytics':
                # Get analytics
                analytics = ai_creative_engine.get_analytics()
                
                if 'error' in analytics:
                    print(f"❌ Analytics failed: {analytics['error']}")
                else:
                    print("📊 AI Creative Services Analytics:")
                    print(f"  🤖 Models trained: {analytics['models_trained']}")
                    print(f"  📂 Model types: {', '.join(analytics['model_types'])}")
                    print(f"  🏢 Business type: {analytics['business_profile']['business_type']}")
                    print(f"  ⏰ Last training: {analytics['last_training']}")
                    print(f"  📝 Training logs: {analytics['training_logs']}")
            
            elif args.ai_command == 'models':
                # List trained models
                model_info = ai_creative_engine.ml_manager.get_model_info()
                
                if model_info:
                    print("🤖 Trained Models:")
                    for model in model_info:
                        print(f"  🔹 {model['name']}")
                        print(f"     Type: {model['type']}")
                        print(f"     Trained: {model['trained_at']}")
                        print()
                else:
                    print("📋 No trained models found")
            
            elif args.ai_command == 'sentiment':
                # Analyze sentiment
                result = ai_creative_engine.analyze_sentiment(args.text)
                
                if 'error' in result:
                    print(f"❌ Sentiment analysis failed: {result['error']}")
                else:
                    print(f"😊 Sentiment Analysis:")
                    print(f"  📊 Sentiment: {result['sentiment']}")
                    print(f"  🎯 Confidence: {result['confidence']:.2f}")
                    print(f"  😊 Positive words: {result['positive_words']}")
                    print(f"  😞 Negative words: {result['negative_words']}")
            
            elif args.ai_command == 'profile':
                if args.profile_command == 'show':
                    # Show business profile
                    profile = ai_creative_engine.business_profile
                    print("🏢 Business Profile:")
                    print(f"  📂 Type: {profile.business_type}")
                    print(f"  🔑 Priority keywords: {', '.join(profile.priority_keywords)}")
                    print(f"  📄 Document types: {', '.join(profile.document_types)}")
                    print(f"  🎭 Response tone: {profile.response_tone}")
                    print(f"  📝 Custom prompts: {len(profile.custom_prompts)}")
                
                elif args.profile_command == 'update':
                    # Update business profile
                    if args.type:
                        ai_creative_engine.business_profile.business_type = args.type
                        ai_creative_engine._save_business_profile()
                        print(f"✅ Updated business type to: {args.type}")
                    else:
                        print("❌ No updates specified")
                
                elif args.profile_command == 'reset':
                    # Reset to default profile
                    ai_creative_engine._create_default_profile()
                    print("✅ Reset to default business profile")
                
                else:
                    ai_profile.print_help()
            
            else:
                ai_parser.print_help()
        
        elif args.command == 'self-training':
            if args.stc_command == 'chat':
                # Interactive chat with learning
                session_id = args.session_id or self_training_chatbot.start_session(args.user_id)
                
                print("🤖 Self-Training Chatbot - Interactive Learning Mode")
                print("Type 'quit' to exit, 'feedback <good/bad>' to provide feedback")
                print("=" * 60)
                
                while True:
                    try:
                        user_input = input("\n👤 You: ").strip()
                        
                        if user_input.lower() == 'quit':
                            print("👋 Goodbye! Learning session saved.")
                            break
                        
                        if user_input.lower().startswith('feedback '):
                            feedback = user_input[9:].strip()
                            success = self_training_chatbot.provide_feedback(session_id, feedback)
                            if success:
                                print("✅ Feedback recorded for learning!")
                            else:
                                print("❌ Failed to record feedback")
                            continue
                        
                        if not user_input:
                            continue
                        
                        # Process query with learning
                        result = self_training_chatbot.process_query(user_input, args.user_id, session_id)
                        
                        print(f"🤖 Bot: {result['response']}")
                        print(f"   Intent: {result['intent']} (confidence: {result['intent_confidence']:.2f})")
                        print(f"   Sentiment: {result['sentiment']} (confidence: {result['sentiment_confidence']:.2f})")
                        print(f"   Learning: {'✅ Applied' if result['learning_applied'] else '❌ Failed'}")
                        
                    except KeyboardInterrupt:
                        print("\n👋 Goodbye! Learning session saved.")
                        break
                    except Exception as e:
                        print(f"❌ Error: {e}")
            
            elif args.stc_command == 'query':
                # Single query with learning
                result = self_training_chatbot.process_query(args.query, args.user_id, args.session_id)
                
                print("🤖 Self-Training Chatbot Response:")
                print("=" * 40)
                print(f"Query: {args.query}")
                print(f"Response: {result['response']}")
                print(f"Intent: {result['intent']} (confidence: {result['intent_confidence']:.2f})")
                print(f"Sentiment: {result['sentiment']} (confidence: {result['sentiment_confidence']:.2f})")
                print(f"Session ID: {result['session_id']}")
                print(f"Learning Applied: {'✅ Yes' if result['learning_applied'] else '❌ No'}")
            
            elif args.stc_command == 'feedback':
                # Provide feedback for learning
                success = self_training_chatbot.provide_feedback(args.session_id, args.feedback)
                
                if success:
                    print(f"✅ Feedback '{args.feedback}' recorded for session {args.session_id}")
                else:
                    print(f"❌ Failed to record feedback for session {args.session_id}")
            
            elif args.stc_command == 'analytics':
                # Get learning analytics
                analytics = self_training_chatbot.get_learning_analytics()
                
                if 'error' in analytics:
                    print(f"❌ Analytics failed: {analytics['error']}")
                else:
                    print("📊 Self-Training Chatbot Analytics:")
                    print(f"  🎯 Learning Metrics:")
                    metrics = analytics['learning_metrics']
                    print(f"    Accuracy: {metrics['accuracy']:.2f}")
                    print(f"    Precision: {metrics['precision']:.2f}")
                    print(f"    Recall: {metrics['recall']:.2f}")
                    print(f"    F1 Score: {metrics['f1_score']:.2f}")
                    print(f"    Confidence Threshold: {metrics['confidence_threshold']:.2f}")
                    print(f"    Learning Rate: {metrics['learning_rate']:.2f}")
                    print(f"    Adaptation Speed: {metrics['adaptation_speed']:.2f}")
                    print(f"    Business Specificity: {metrics['business_specificity']:.2f}")
                    
                    print(f"  📈 Learning Progress:")
                    progress = analytics['learning_progress']
                    print(f"    Total Sessions: {progress['total_sessions']}")
                    print(f"    Active Sessions: {progress['active_sessions']}")
                    print(f"    Total Interactions: {progress['total_interactions']}")
                    print(f"    Avg Interactions/Session: {progress['avg_interactions_per_session']:.1f}")
                    print(f"    Avg Learning Score: {progress['learning_score_avg']:.2f}")
                    
                    print(f"  🏢 Business Insights:")
                    insights = analytics['business_insights']
                    print(f"    Business Type: {insights['business_type']}")
                    print(f"    Industry Keywords: {', '.join(insights['industry_keywords'])}")
                    print(f"    Common Queries: {len(insights['common_queries'])}")
                    print(f"    Response Patterns: {insights['response_patterns_count']}")
            
            elif args.stc_command == 'profile':
                if args.profile_command == 'show':
                    # Show business learning profile
                    analytics = self_training_chatbot.get_learning_analytics()
                    insights = analytics.get('business_insights', {})
                    
                    print("🏢 Business Learning Profile:")
                    print(f"  📂 Type: {insights.get('business_type', 'unknown')}")
                    print(f"  🔑 Keywords: {', '.join(insights.get('industry_keywords', []))}")
                    print(f"  ❓ Common Queries: {len(insights.get('common_queries', []))}")
                    print(f"  📝 Response Patterns: {insights.get('response_patterns_count', 0)}")
                
                elif args.profile_command == 'update':
                    # Update business profile
                    keywords = args.keywords.split(',') if args.keywords else None
                    success = self_training_chatbot.update_business_profile(args.type, keywords)
                    
                    if success:
                        print(f"✅ Updated business profile: {args.type}")
                        if keywords:
                            print(f"   Keywords: {', '.join(keywords)}")
                    else:
                        print("❌ Failed to update business profile")
                
                else:
                    stc_profile.print_help()
            
            else:
                stc_parser.print_help()
        
        elif args.command == 'service-learning':
            if args.sl_command == 'analytics':
                # Get service learning analytics
                analytics = service_learning_manager.get_cross_service_analytics()
                
                if 'error' in analytics:
                    print(f"❌ Analytics failed: {analytics['error']}")
                else:
                    print("📊 Service Learning Analytics:")
                    print(f"  🔄 Total Services: {analytics['total_services']}")
                    print(f"  💬 Total Interactions: {analytics['total_interactions']}")
                    print(f"  📅 Last Analyzed: {analytics['last_analyzed']}")
                    
                    print(f"  🎯 Shared Patterns:")
                    for business_type, patterns in analytics['shared_patterns'].items():
                        print(f"    {business_type}: {', '.join(patterns[:5])}")
                    
                    print(f"  ⚙️ Business Preferences:")
                    for pref, value in analytics['business_preferences'].items():
                        print(f"    {pref}: {value}")
                    
                    print(f"  ⚠️ Common Issues: {', '.join(analytics['common_issues'])}")
                    print(f"  ✅ Success Factors: {', '.join(analytics['success_factors'])}")
            
            elif args.sl_command == 'insights':
                # Get service insights
                insights = service_learning_manager.get_service_insights(args.service)
                
                if 'error' in insights:
                    print(f"❌ Insights failed: {insights['error']}")
                else:
                    print(f"📊 Service Insights: {args.service}")
                    print(f"  📈 Performance Metrics:")
                    metrics = insights['performance_metrics']
                    print(f"    Success Rate: {metrics.get('success_rate', 0):.2f}")
                    print(f"    Avg Response Time: {metrics.get('avg_response_time', 0):.2f}s")
                    print(f"    Avg Satisfaction: {metrics.get('avg_satisfaction', 0):.2f}")
                    print(f"    Total Interactions: {metrics.get('total_interactions', 0)}")
                    
                    print(f"  📊 Performance Trend: {insights['performance_trend']}")
                    print(f"  🏢 Business Type: {insights['business_insights'].get('most_common_business_type', 'unknown')}")
                    print(f"  📅 Last Updated: {insights['last_updated']}")
            
            elif args.sl_command == 'recommendations':
                # Get improvement recommendations
                recommendations = service_learning_manager.recommend_improvements(args.service)
                
                print(f"💡 Improvement Recommendations for {args.service}:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")
            
            elif args.sl_command == 'cross-service':
                # Get cross-service analytics
                analytics = service_learning_manager.get_cross_service_analytics()
                
                print("🔄 Cross-Service Learning Analytics:")
                print(f"  📊 Total Services: {analytics['total_services']}")
                print(f"  💬 Total Interactions: {analytics['total_interactions']}")
                print(f"  📅 Last Analyzed: {analytics['last_analyzed']}")
            
            elif args.sl_command == 'integrate':
                # Integrate learning with services
                print("🔗 Integrating learning with services...")
                
                try:
                    # Import services
                    # Removed gmail_utils import that causes hanging
# from core.gmail_utils import GmailService
                    # Removed CRM imports that cause hanging
# from core.crm_service import CRMService
                    from core.chatbot import chatbot_engine
                    from core.ai_creative import ai_creative_engine
                    
                    # Integrate with each service
                    gmail_service = GmailService()
                    learning_integrator.integrate_with_email_service(gmail_service)
                    
                    crm_service = CRMService()
                    learning_integrator.integrate_with_crm_service(crm_service)
                    
                    learning_integrator.integrate_with_chatbot_service(chatbot_engine)
                    learning_integrator.integrate_with_ai_creative_service(ai_creative_engine)
                    
                    print("✅ Learning integration completed for all services")
                    
                except Exception as e:
                    print(f"❌ Integration failed: {e}")
            
            else:
                sl_parser.print_help()
        
        elif args.command == 'advanced-chatbot':
            if args.ac_command == 'chat':
                # Chat with advanced chatbot
                result = await advanced_chatbot_engine.chat(
                    args.message, 
                    args.session_id, 
                    args.user_id
                )
                
                print("🤖 Advanced Self-Learning Chatbot Response:")
                print("=" * 50)
                print(f"Message: {args.message}")
                print(f"Response: {result['response']}")
                print(f"Session ID: {result['session_id']}")
                print(f"Intent: {result.get('intent', 'unknown')}")
                print(f"Confidence: {result.get('confidence', 0.0):.2f}")
                print(f"Context Used: {'✅ Yes' if result.get('context_used', False) else '❌ No'}")
            
            elif args.ac_command == 'train':
                # Train new models
                print("🧠 Training Advanced Chatbot Models...")
                
                # Create sample training data
                training_data = {
                    'features': {
                        'text': {
                            'columns': ['message'],
                            'data': np.array([
                                "What services do you offer?",
                                "How much does it cost?",
                                "I need help with my business",
                                "Can you help me automate my processes?",
                                "What are your pricing options?"
                            ]).reshape(-1, 1),
                            'vectorizer': TfidfVectorizer(max_features=1000).fit([
                                "What services do you offer?",
                                "How much does it cost?",
                                "I need help with my business",
                                "Can you help me automate my processes?",
                                "What are your pricing options?"
                            ])
                        }
                    },
                    'target': np.array(['services', 'pricing', 'support', 'services', 'pricing']),
                    'data_shape': (5, 1)
                }
                
                # Create model config
                config = ModelConfig(
                    model_type=args.model_type,
                    algorithm=args.algorithm,
                    hyperparameters={},
                    feature_engineering={},
                    training_config={'epochs': 5}
                )
                
                result = await advanced_chatbot_engine.learning_engine.train_model(config, training_data)
                
                print(f"✅ Model training completed!")
                print(f"   Model ID: {result.model_id}")
                print(f"   Accuracy: {result.accuracy:.3f}")
                print(f"   Loss: {result.loss:.3f}")
                print(f"   Training Time: {result.training_time:.2f}s")
                print(f"   Model Path: {result.model_path}")
            
            elif args.ac_command == 'retrain':
                # Retrain existing models
                print("🔄 Retraining Advanced Chatbot Models...")
                
                if args.model_id:
                    result = await advanced_chatbot_engine.learning_engine.retrain_model(args.model_id, {})
                    print(f"✅ Model {args.model_id} retrained successfully!")
                else:
                    await advanced_chatbot_engine.learning_engine.retrain_all_models()
                    print("✅ All models retrained successfully!")
            
            elif args.ac_command == 'ingest':
                if args.ingest_type == 'csv':
                    # Ingest CSV data
                    print(f"📊 Ingesting CSV data from {args.file_path}...")
                    
                    result = advanced_chatbot_engine.data_ingestion.ingest_csv(args.file_path)
                    
                    if result['success']:
                        print(f"✅ CSV ingestion completed!")
                        print(f"   Records: {result['records_count']}")
                        print(f"   Ingestion ID: {result['ingestion_id']}")
                    else:
                        print(f"❌ CSV ingestion failed: {result['error']}")
                
                elif args.ingest_type == 'google-form':
                    # Ingest Google Form data
                    print("📝 Ingesting Google Form data...")
                    
                    form_data = json.loads(args.form_data) if args.form_data else [
                        {"name": "John Doe", "email": "john@example.com", "message": "Interested in services"},
                        {"name": "Jane Smith", "email": "jane@example.com", "message": "Need pricing info"}
                    ]
                    
                    result = advanced_chatbot_engine.data_ingestion.ingest_google_form(form_data)
                    
                    if result['success']:
                        print(f"✅ Google Form ingestion completed!")
                        print(f"   Records: {result['records_count']}")
                        print(f"   Ingestion ID: {result['ingestion_id']}")
                    else:
                        print(f"❌ Google Form ingestion failed: {result['error']}")
                
                elif args.ingest_type == 'crm':
                    # Ingest CRM data
                    print("📋 Ingesting CRM data...")
                    
                    crm_data = json.loads(args.crm_data) if args.crm_data else [
                        {"lead_id": "1", "name": "Lead 1", "stage": "new", "score": 8.5},
                        {"lead_id": "2", "name": "Lead 2", "stage": "contacted", "score": 7.2}
                    ]
                    
                    result = advanced_chatbot_engine.data_ingestion.ingest_crm_logs(crm_data)
                    
                    if result['success']:
                        print(f"✅ CRM data ingestion completed!")
                        print(f"   Records: {result['records_count']}")
                        print(f"   Ingestion ID: {result['ingestion_id']}")
                    else:
                        print(f"❌ CRM data ingestion failed: {result['error']}")
                
                elif args.ingest_type == 'email':
                    # Ingest email metadata
                    print("📧 Ingesting email metadata...")
                    
                    email_data = json.loads(args.email_data) if args.email_data else [
                        {"subject": "Service Inquiry", "sender": "client@example.com", "priority": "high"},
                        {"subject": "Pricing Question", "sender": "prospect@example.com", "priority": "medium"}
                    ]
                    
                    result = advanced_chatbot_engine.data_ingestion.ingest_email_metadata(email_data)
                    
                    if result['success']:
                        print(f"✅ Email metadata ingestion completed!")
                        print(f"   Records: {result['records_count']}")
                        print(f"   Ingestion ID: {result['ingestion_id']}")
                    else:
                        print(f"❌ Email metadata ingestion failed: {result['error']}")
                
                else:
                    ac_ingest.print_help()
            
            elif args.ac_command == 'logs':
                # Get training logs
                logs = advanced_chatbot_engine.get_training_logs()
                
                print("📊 Advanced Chatbot Training Logs:")
                print("=" * 50)
                
                if logs:
                    for log in logs[:10]:  # Show last 10 logs
                        print(f"Model: {log['model_id']}")
                        print(f"Epoch: {log['epoch']}")
                        print(f"Accuracy: {log['accuracy']:.3f}")
                        print(f"Loss: {log['loss']:.3f}")
                        print(f"Timestamp: {log['timestamp']}")
                        print("-" * 30)
                else:
                    print("No training logs found.")
            
            elif args.ac_command == 'models':
                # List all model versions
                models = advanced_chatbot_engine.get_model_versions()
                
                print("🤖 Advanced Chatbot Model Versions:")
                print("=" * 50)
                
                if models:
                    for model in models[:10]:  # Show last 10 models
                        print(f"Model: {model['model_name']}")
                        print(f"Type: {model['model_type']}")
                        print(f"Version: {model['version']}")
                        print(f"Accuracy: {model['accuracy']:.3f}")
                        print(f"Loss: {model['loss']:.3f}")
                        print(f"Inference Time: {model['inference_time']:.3f}s")
                        print(f"Active: {'✅ Yes' if model['is_active'] else '❌ No'}")
                        print(f"Created: {model['created_at']}")
                        print("-" * 30)
                else:
                    print("No models found.")
            
            elif args.ac_command == 'status':
                # Get system status
                print("📊 Advanced Chatbot System Status:")
                print("=" * 50)
                
                active_models = len(advanced_chatbot_engine.learning_engine.active_models)
                active_sessions = len(advanced_chatbot_engine.chat_contexts)
                retraining_enabled = advanced_chatbot_engine.learning_engine.scheduler.running
                
                print(f"Active Models: {active_models}")
                print(f"Active Sessions: {active_sessions}")
                print(f"Retraining Enabled: {'✅ Yes' if retraining_enabled else '❌ No'}")
                print(f"Data Sources: CSV, Google Form, CRM, Email")
                print(f"Supported Models: Linear Regression, Ridge, Lasso, Naive Bayes, KNN, SVM, LDA, QDA, PCA, Kernel PCA, LSTM, GRU, Transformer, XGBoost, LightGBM")
            
            elif args.ac_command == 'pause':
                # Pause retraining
                advanced_chatbot_engine.learning_engine.pause_retraining()
                print("⏸️ Automatic retraining paused.")
            
            elif args.ac_command == 'resume':
                # Resume retraining
                advanced_chatbot_engine.learning_engine.resume_retraining()
                print("▶️ Automatic retraining resumed.")
            
            elif args.ac_command == 'reset':
                # Reset all models
                advanced_chatbot_engine.learning_engine.reset_models()
                print("🔄 All models reset.")
            
            else:
                ac_parser.print_help()
        
        elif args.command == 'chatbot-tiers':
            if args.ct_command == 'list':
                # List all tiers
                print("🎯 Available Chatbot Tiers:")
                print("=" * 50)
                
                tiers = tier_manager.get_all_tiers()
                for tier_info in tiers:
                    tier = tier_info['tier']
                    features = tier_info['features']
                    pricing = tier_info['pricing']
                    
                    print(f"\n🥇 {tier.title()} Tier")
                    print(f"   💰 ${pricing['monthly']}/month (${pricing['yearly']}/year)")
                    print(f"   📊 Sessions/day: {features['max_sessions_per_day']}")
                    print(f"   💬 Messages/session: {features['max_messages_per_session']}")
                    print(f"   📚 FAQ items: {features['max_faq_items']}")
                    print(f"   🧠 Learning: {'✅' if features['learning_enabled'] else '❌'}")
                    print(f"   🤖 Advanced ML: {'✅' if features['advanced_ml_enabled'] else '❌'}")
                    print(f"   🔌 API Access: {'✅' if features['api_access'] else '❌'}")
                    print(f"   🎓 Custom Training: {'✅' if features['custom_training'] else '❌'}")
                    print(f"   🚀 Priority Support: {'✅' if features['priority_support'] else '❌'}")
            
            elif args.ct_command == 'chat':
                # Chat with tiered chatbot
                print(f"🤖 Chatting with {args.tier.title()} Tier Chatbot...")
                print("=" * 50)
                
                result = await tier_manager.process_chat(
                    args.user_id,
                    args.message,
                    args.session_id
                )
                
                if result['success']:
                    print(f"Message: {args.message}")
                    print(f"Response: {result['response']}")
                    print(f"Tier: {result['tier']}")
                    print(f"Intent: {result.get('intent', 'unknown')}")
                    print(f"Confidence: {result.get('confidence', 0.0):.2f}")
                    
                    if 'limits' in result:
                        limits = result['limits']
                        print(f"\n📊 Usage Limits:")
                        print(f"   Sessions remaining today: {limits['sessions_remaining']}")
                        print(f"   Messages remaining in session: {limits['messages_remaining']}")
                else:
                    print(f"❌ Error: {result['error']}")
                    if result.get('upgrade_required'):
                        print("💡 Consider upgrading your tier for more features!")
            
            elif args.ct_command == 'features':
                # Get tier features
                if args.tier:
                    tier = ChatbotTier(args.tier)
                    tier_info = tier_manager.get_tier_features(tier)
                    
                    print(f"🎯 {args.tier.title()} Tier Features:")
                    print("=" * 50)
                    
                    features = tier_info['features']
                    pricing = tier_info['pricing']
                    
                    print(f"💰 Pricing: ${pricing['monthly']}/month (${pricing['yearly']}/year)")
                    print(f"📊 Daily Sessions: {features['max_sessions_per_day']}")
                    print(f"💬 Session Messages: {features['max_messages_per_session']}")
                    print(f"📚 FAQ Items: {features['max_faq_items']}")
                    print(f"🧠 Learning Enabled: {'✅ Yes' if features['learning_enabled'] else '❌ No'}")
                    print(f"🤖 Advanced ML: {'✅ Yes' if features['advanced_ml_enabled'] else '❌ No'}")
                    print(f"🔌 API Access: {'✅ Yes' if features['api_access'] else '❌ No'}")
                    print(f"🎓 Custom Training: {'✅ Yes' if features['custom_training'] else '❌ No'}")
                    print(f"🚀 Priority Support: {'✅ Yes' if features['priority_support'] else '❌ No'}")
                else:
                    print("Please specify a tier with --tier (basic, professional, enterprise)")
            
            else:
                ct_parser.print_help()
        
        elif args.command == 'crm':
            # Initialize CRM service
            crm = CRMService()
            
            if args.crm_command == 'ingest':
                import json as pyjson
                from core.crm_sources import leads_from_csv
                raw: list = []
                if args.json:
                    raw = pyjson.loads(args.json)
                    if not isinstance(raw, list):
                        raise ValueError('Ingest expects a JSON array of leads')
                if args.from_csv:
                    raw += [l.__dict__ for l in leads_from_csv(args.from_csv)]
                results = crm.ingest(raw)
                print(f"✅ Ingested {len(results)} leads")
            
            elif args.crm_command == 'list':
                leads = crm.list()
                print(f"📇 {len(leads)} leads")
                for l in leads:
                    print(f"- {l.id} | {l.name} <{l.email}> | stage: {l.stage} | score: {l.score}")
            
            elif args.crm_command == 'followup':
                result = crm.batch_followup(stage_filter=args.stage, send=args.send)
                if args.send:
                    print(f"✅ Sent {result['sent']} follow-ups (processed {result['count']})")
                else:
                    print(f"🔍 Previewing {len(result['preview'])} follow-ups (processed {result['count']})")
                    for p in result['preview'][:5]:
                        print(f"- {p['lead']}: {p['text']}")
            
            elif args.crm_command == 'stage':
                updated = crm.set_stage(args.id, args.to)
                if updated:
                    print(f"✅ Lead {updated.id} moved to stage '{updated.stage}'")
                else:
                    print("❌ Lead not found")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        if cli.config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
