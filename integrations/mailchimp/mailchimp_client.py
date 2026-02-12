#!/usr/bin/env python3
"""
Mailchimp Marketing API Integration for Fikiri Solutions
Email marketing and automation platform integration
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import hmac

logger = logging.getLogger(__name__)


class MailchimpProvider:
    """Mailchimp Marketing API provider for email marketing and automation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = "Mailchimp"
        self.authenticated = False
        
        # Mailchimp API configuration
        self.api_key = config.get('api_key')
        self.server_prefix = config.get('server_prefix')  # e.g., 'us1', 'us2', etc.
        self.list_id = config.get('list_id')
        self.webhook_secret = config.get('webhook_secret')
        
        # API endpoints
        self.base_url = f"https://{self.server_prefix}.api.mailchimp.com/3.0"
        self.headers = {
            'Authorization': f'apikey {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def authenticate(self) -> bool:
        """Authenticate with Mailchimp API."""
        if not all([self.api_key, self.server_prefix]):
            return False
        
        try:
            # Test API connection by getting account info
            response = requests.get(f"{self.base_url}/", headers=self.headers)
            response.raise_for_status()
            
            self.authenticated = True
            logger.info("Mailchimp API authentication successful")
            return True
            
        except Exception as e:
            logger.error("Mailchimp API authentication failed: %s", e)
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get Mailchimp account information."""
        if not self.authenticated:
            return {}
        
        try:
            response = requests.get(f"{self.base_url}/", headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                'account_id': data.get('account_id'),
                'account_name': data.get('account_name'),
                'email': data.get('email'),
                'username': data.get('username'),
                'total_subscribers': data.get('total_subscribers'),
                'provider': 'mailchimp'
            }
            
        except Exception as e:
            logger.error("Failed to get Mailchimp account info: %s", e)
            return {}
    
    def get_lists(self) -> List[Dict[str, Any]]:
        """Get all audience lists."""
        if not self.authenticated:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/lists", headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            lists = []
            
            for list_item in data.get('lists', []):
                list_data = {
                    'id': list_item['id'],
                    'name': list_item['name'],
                    'member_count': list_item['stats']['member_count'],
                    'unsubscribe_count': list_item['stats']['unsubscribe_count'],
                    'created_at': list_item['date_created'],
                    'provider': 'mailchimp'
                }
                lists.append(list_data)
            
            logger.info(f"✅ Retrieved {len(lists)} Mailchimp lists")
            return lists
            
        except Exception as e:
            logger.error("Failed to get Mailchimp lists: %s", e)
            return []
    
    def add_subscriber(self, email: str, first_name: str = None, last_name: str = None, 
                      tags: List[str] = None, merge_fields: Dict[str, Any] = None) -> bool:
        """Add a subscriber to the default list."""
        if not self.authenticated or not self.list_id:
            return False
        
        try:
            # Prepare subscriber data
            subscriber_data = {
                'email_address': email,
                'status': 'subscribed'
            }
            
            # Add merge fields if provided
            if first_name or last_name or merge_fields:
                subscriber_data['merge_fields'] = {}
                if first_name:
                    subscriber_data['merge_fields']['FNAME'] = first_name
                if last_name:
                    subscriber_data['merge_fields']['LNAME'] = last_name
                if merge_fields:
                    subscriber_data['merge_fields'].update(merge_fields)
            
            # Add tags if provided
            if tags:
                subscriber_data['tags'] = tags
            
            # Create subscriber hash for API endpoint
            subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
            
            url = f"{self.base_url}/lists/{self.list_id}/members/{subscriber_hash}"
            response = requests.put(url, headers=self.headers, json=subscriber_data)
            response.raise_for_status()
            
            logger.info(f"✅ Added subscriber to Mailchimp: {email}")
            return True
            
        except Exception as e:
            logger.error("Failed to add Mailchimp subscriber: %s", e)
            return False
    
    def get_subscribers(self, list_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get subscribers from a list."""
        if not self.authenticated:
            return []
        
        target_list_id = list_id or self.list_id
        if not target_list_id:
            return []
        
        try:
            url = f"{self.base_url}/lists/{target_list_id}/members"
            params = {
                'count': limit,
                'status': 'subscribed'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            subscribers = []
            
            for member in data.get('members', []):
                subscriber_data = {
                    'id': member['id'],
                    'email': member['email_address'],
                    'first_name': member.get('merge_fields', {}).get('FNAME', ''),
                    'last_name': member.get('merge_fields', {}).get('LNAME', ''),
                    'status': member['status'],
                    'subscribed_at': member['timestamp_signup'],
                    'last_changed': member['last_changed'],
                    'tags': [tag['name'] for tag in member.get('tags', [])],
                    'provider': 'mailchimp'
                }
                subscribers.append(subscriber_data)
            
            logger.info(f"✅ Retrieved {len(subscribers)} Mailchimp subscribers")
            return subscribers
            
        except Exception as e:
            logger.error("Failed to get Mailchimp subscribers: %s", e)
            return []
    
    def create_campaign(self, subject: str, from_name: str, reply_to: str, 
                       html_content: str, text_content: str = None) -> Optional[str]:
        """Create an email campaign."""
        if not self.authenticated or not self.list_id:
            return None
        
        try:
            # Create campaign
            campaign_data = {
                'type': 'regular',
                'recipients': {
                    'list_id': self.list_id
                },
                'settings': {
                    'subject_line': subject,
                    'from_name': from_name,
                    'reply_to': reply_to,
                    'to_name': '*|FNAME|*'
                }
            }
            
            response = requests.post(f"{self.base_url}/campaigns", 
                                   headers=self.headers, json=campaign_data)
            response.raise_for_status()
            
            campaign_id = response.json()['id']
            
            # Set campaign content
            content_data = {
                'html': html_content
            }
            if text_content:
                content_data['plain_text'] = text_content
            
            content_response = requests.put(
                f"{self.base_url}/campaigns/{campaign_id}/content",
                headers=self.headers, json=content_data
            )
            content_response.raise_for_status()
            
            logger.info(f"✅ Created Mailchimp campaign: {campaign_id}")
            return campaign_id
            
        except Exception as e:
            logger.error("Failed to create Mailchimp campaign: %s", e)
            return None
    
    def send_campaign(self, campaign_id: str) -> bool:
        """Send a campaign."""
        if not self.authenticated:
            return False
        
        try:
            response = requests.post(f"{self.base_url}/campaigns/{campaign_id}/actions/send",
                                   headers=self.headers)
            response.raise_for_status()
            
            logger.info(f"✅ Sent Mailchimp campaign: {campaign_id}")
            return True
            
        except Exception as e:
            logger.error("Failed to send Mailchimp campaign: %s", e)
            return False
    
    def get_campaigns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent campaigns."""
        if not self.authenticated:
            return []
        
        try:
            url = f"{self.base_url}/campaigns"
            params = {
                'count': limit,
                'sort_field': 'send_time',
                'sort_dir': 'DESC'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            campaigns = []
            
            for campaign in data.get('campaigns', []):
                campaign_data = {
                    'id': campaign['id'],
                    'type': campaign['type'],
                    'status': campaign['status'],
                    'subject': campaign['settings']['subject_line'],
                    'from_name': campaign['settings']['from_name'],
                    'reply_to': campaign['settings']['reply_to'],
                    'created_at': campaign['create_time'],
                    'sent_at': campaign.get('send_time'),
                    'recipients': campaign['recipients']['recipient_count'],
                    'opens': campaign['report_summary'].get('opens', 0),
                    'clicks': campaign['report_summary'].get('clicks', 0),
                    'provider': 'mailchimp'
                }
                campaigns.append(campaign_data)
            
            logger.info(f"✅ Retrieved {len(campaigns)} Mailchimp campaigns")
            return campaigns
            
        except Exception as e:
            logger.error("Failed to get Mailchimp campaigns: %s", e)
            return []
    
    def create_automation(self, trigger_type: str, trigger_settings: Dict[str, Any],
                         actions: List[Dict[str, Any]]) -> Optional[str]:
        """Create a marketing automation workflow."""
        if not self.authenticated:
            return None
        
        try:
            automation_data = {
                'trigger_settings': {
                    'trigger_type': trigger_type,
                    **trigger_settings
                },
                'actions': actions
            }
            
            response = requests.post(f"{self.base_url}/automations",
                                   headers=self.headers, json=automation_data)
            response.raise_for_status()
            
            automation_id = response.json()['id']
            logger.info(f"✅ Created Mailchimp automation: {automation_id}")
            return automation_id
            
        except Exception as e:
            logger.error("Failed to create Mailchimp automation: %s", e)
            return None
    
    def get_automations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get automation workflows."""
        if not self.authenticated:
            return []
        
        try:
            url = f"{self.base_url}/automations"
            params = {'count': limit}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            automations = []
            
            for automation in data.get('automations', []):
                automation_data = {
                    'id': automation['id'],
                    'name': automation['settings']['title'],
                    'status': automation['status'],
                    'trigger_type': automation['trigger_settings']['trigger_type'],
                    'created_at': automation['create_time'],
                    'emails_sent': automation['emails_sent'],
                    'recipients': automation['recipients'],
                    'provider': 'mailchimp'
                }
                automations.append(automation_data)
            
            logger.info(f"✅ Retrieved {len(automations)} Mailchimp automations")
            return automations
            
        except Exception as e:
            logger.error("Failed to get Mailchimp automations: %s", e)
            return []
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get account analytics for the specified period."""
        if not self.authenticated:
            return {}
        
        try:
            # Get account overview
            response = requests.get(f"{self.base_url}/", headers=self.headers)
            response.raise_for_status()
            
            account_data = response.json()
            
            # Get recent campaigns for analytics
            campaigns_response = requests.get(f"{self.base_url}/campaigns", 
                                            headers=self.headers, 
                                            params={'count': 100})
            campaigns_response.raise_for_status()
            
            campaigns_data = campaigns_response.json()
            
            # Calculate analytics
            total_campaigns = len(campaigns_data.get('campaigns', []))
            total_opens = sum(campaign['report_summary'].get('opens', 0) 
                            for campaign in campaigns_data.get('campaigns', []))
            total_clicks = sum(campaign['report_summary'].get('clicks', 0) 
                             for campaign in campaigns_data.get('campaigns', []))
            
            analytics = {
                'total_subscribers': account_data.get('total_subscribers', 0),
                'total_campaigns': total_campaigns,
                'total_opens': total_opens,
                'total_clicks': total_clicks,
                'open_rate': (total_opens / max(total_campaigns, 1)) * 100,
                'click_rate': (total_clicks / max(total_campaigns, 1)) * 100,
                'provider': 'mailchimp'
            }
            
            logger.info(f"✅ Retrieved Mailchimp analytics")
            return analytics
            
        except Exception as e:
            logger.error("Failed to get Mailchimp analytics: %s", e)
            return {}
    
    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error("Failed to verify Mailchimp webhook: %s", e)
            return False
    
    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self.authenticated
    
    def get_service_capabilities(self) -> Dict[str, Any]:
        """Get service capabilities."""
        return {
            'email_marketing': True,
            'marketing_automation': True,
            'audience_management': True,
            'campaign_management': True,
            'analytics_reporting': True,
            'a_b_testing': True,
            'landing_pages': True,
            'ecommerce_integration': True,
            'api_type': 'REST',
            'rate_limits': '10 requests per second',
            'webhook_support': True
        }

# Configuration template for Mailchimp API
MAILCHIMP_CONFIG_TEMPLATE = {
    'api_key': 'your_mailchimp_api_key',
    'server_prefix': 'us1',  # Extract from API key or account settings
    'list_id': 'your_default_list_id',
    'webhook_secret': 'your_webhook_secret'
}

if __name__ == "__main__":
    # Test Mailchimp provider
    config = {
        'api_key': os.getenv('MAILCHIMP_API_KEY'),
        'server_prefix': os.getenv('MAILCHIMP_SERVER_PREFIX'),
        'list_id': os.getenv('MAILCHIMP_LIST_ID'),
        'webhook_secret': os.getenv('MAILCHIMP_WEBHOOK_SECRET')
    }
    
    provider = MailchimpProvider(config)
    
    # Test authentication
    if provider.authenticate():
        logger.info("✅ Mailchimp provider authenticated successfully")
        
        # Test getting account info
        account_info = provider.get_account_info()
        logger.info(f"Account: {account_info.get('account_name')} ({account_info.get('email')})")
        
        # Test getting lists
        lists = provider.get_lists()
        logger.info(f"Retrieved {len(lists)} lists")
        
        # Test getting subscribers
        subscribers = provider.get_subscribers(5)
        logger.info(f"Retrieved {len(subscribers)} subscribers")
        
        # Test getting campaigns
        campaigns = provider.get_campaigns(5)
        logger.info(f"Retrieved {len(campaigns)} campaigns")
        
        # Test getting automations
        automations = provider.get_automations(5)
        logger.info(f"Retrieved {len(automations)} automations")
        
        # Test getting analytics
        analytics = provider.get_analytics()
        logger.info(f"Analytics: {analytics.get('total_subscribers')} subscribers")
        
    else:
        logger.error("Mailchimp provider authentication failed. Check configuration and try again.")
