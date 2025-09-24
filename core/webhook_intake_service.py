"""
Webhook Intake Service for Fikiri Solutions
Handles webhook data from Tally, Typeform, Jotform and other form services
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
from flask import request, jsonify
from core.minimal_config import get_config
from core.database_optimization import db_optimizer
from core.google_sheets_connector import get_sheets_connector
from core.notion_connector import get_notion_connector

logger = logging.getLogger(__name__)

@dataclass
class WebhookConfig:
    """Webhook configuration"""
    secret_key: str
    allowed_origins: List[str]
    enable_verification: bool = True

class WebhookIntakeService:
    """Service for handling webhook data from form services"""
    
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.sheets_connector = get_sheets_connector()
        self.notion_connector = get_notion_connector()
    
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature for security"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"❌ Webhook signature verification failed: {e}")
            return False
    
    def process_tally_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from Tally forms"""
        try:
            # Extract lead data from Tally webhook
            form_data = data.get('data', {})
            
            lead_data = {
                'name': form_data.get('name', ''),
                'email': form_data.get('email', ''),
                'phone': form_data.get('phone', ''),
                'company': form_data.get('company', ''),
                'source': 'tally',
                'status': 'new',
                'score': self._calculate_lead_score(form_data),
                'notes': form_data.get('message', ''),
                'tags': ['webhook', 'tally'],
                'metadata': {
                    'form_id': data.get('formId'),
                    'submission_id': data.get('submissionId'),
                    'created_at': data.get('createdAt'),
                    'raw_data': form_data
                }
            }
            
            return self._process_lead(lead_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to process Tally webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def process_typeform_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from Typeform"""
        try:
            # Extract lead data from Typeform webhook
            form_response = data.get('form_response', {})
            answers = form_response.get('answers', [])
            
            # Map Typeform answers to lead fields
            lead_data = {
                'name': '',
                'email': '',
                'phone': '',
                'company': '',
                'source': 'typeform',
                'status': 'new',
                'score': 0,
                'notes': '',
                'tags': ['webhook', 'typeform'],
                'metadata': {
                    'form_id': data.get('form', {}).get('id'),
                    'submission_id': form_response.get('token'),
                    'created_at': form_response.get('submitted_at'),
                    'raw_data': data
                }
            }
            
            # Extract answers based on field references
            for answer in answers:
                field_ref = answer.get('field', {}).get('ref', '')
                field_type = answer.get('type', '')
                
                if field_type == 'email' and not lead_data['email']:
                    lead_data['email'] = answer.get('email', '')
                elif field_type == 'text' and 'name' in field_ref.lower():
                    lead_data['name'] = answer.get('text', '')
                elif field_type == 'phone_number':
                    lead_data['phone'] = answer.get('phone_number', '')
                elif field_type == 'text' and 'company' in field_ref.lower():
                    lead_data['company'] = answer.get('text', '')
                elif field_type == 'long_text':
                    lead_data['notes'] = answer.get('text', '')
            
            lead_data['score'] = self._calculate_lead_score(lead_data)
            
            return self._process_lead(lead_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to process Typeform webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def process_jotform_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from Jotform"""
        try:
            # Extract lead data from Jotform webhook
            submission = data.get('submission', {})
            answers = submission.get('answers', {})
            
            lead_data = {
                'name': '',
                'email': '',
                'phone': '',
                'company': '',
                'source': 'jotform',
                'status': 'new',
                'score': 0,
                'notes': '',
                'tags': ['webhook', 'jotform'],
                'metadata': {
                    'form_id': data.get('formID'),
                    'submission_id': submission.get('id'),
                    'created_at': submission.get('created_at'),
                    'raw_data': data
                }
            }
            
            # Extract answers based on field names
            for field_id, answer_data in answers.items():
                field_name = answer_data.get('name', '').lower()
                answer_value = answer_data.get('answer', '')
                
                if 'email' in field_name and not lead_data['email']:
                    lead_data['email'] = answer_value
                elif 'name' in field_name and not lead_data['name']:
                    lead_data['name'] = answer_value
                elif 'phone' in field_name:
                    lead_data['phone'] = answer_value
                elif 'company' in field_name:
                    lead_data['company'] = answer_value
                elif 'message' in field_name or 'comment' in field_name:
                    lead_data['notes'] = answer_value
            
            lead_data['score'] = self._calculate_lead_score(lead_data)
            
            return self._process_lead(lead_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to process Jotform webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def process_generic_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic webhook data"""
        try:
            # Try to extract common fields
            lead_data = {
                'name': data.get('name', data.get('full_name', '')),
                'email': data.get('email', ''),
                'phone': data.get('phone', data.get('phone_number', '')),
                'company': data.get('company', data.get('organization', '')),
                'source': data.get('source', 'webhook'),
                'status': 'new',
                'score': 0,
                'notes': data.get('message', data.get('notes', data.get('comments', ''))),
                'tags': ['webhook', 'generic'],
                'metadata': {
                    'raw_data': data,
                    'received_at': datetime.now().isoformat()
                }
            }
            
            lead_data['score'] = self._calculate_lead_score(lead_data)
            
            return self._process_lead(lead_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to process generic webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and store lead data across all systems"""
        try:
            # Validate required fields
            if not lead_data.get('email'):
                return {"success": False, "error": "Email is required"}
            
            # Generate unique lead ID
            lead_id = f"lead_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(lead_data['email'].encode()).hexdigest()[:8]}"
            lead_data['id'] = lead_id
            lead_data['created_at'] = datetime.now().isoformat()
            
            # Store in database
            db_result = self._store_lead_in_db(lead_data)
            if not db_result['success']:
                return db_result
            
            # Sync to Google Sheets
            if self.sheets_connector:
                sheets_result = self.sheets_connector.add_lead(lead_data)
                if not sheets_result['success']:
                    logger.warning(f"⚠️ Failed to sync to Google Sheets: {sheets_result.get('error')}")
            
            # Sync to Notion
            if self.notion_connector:
                notion_result = self.notion_connector.create_customer_profile(lead_data)
                if not notion_result['success']:
                    logger.warning(f"⚠️ Failed to sync to Notion: {notion_result.get('error')}")
            
            logger.info(f"✅ Successfully processed lead: {lead_data['email']}")
            return {
                "success": True,
                "lead_id": lead_id,
                "message": "Lead processed successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process lead: {e}")
            return {"success": False, "error": str(e)}
    
    def _store_lead_in_db(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store lead data in the database"""
        try:
            # Insert lead into database
            query = """
                INSERT INTO leads (
                    user_id, email, name, phone, company, source, 
                    status, score, notes, tags, meta, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                lead_data.get('user_id', 1),
                lead_data['email'],
                lead_data['name'],
                lead_data['phone'],
                lead_data['company'],
                lead_data['source'],
                lead_data['status'],
                lead_data['score'],
                lead_data['notes'],
                json.dumps(lead_data['tags']),
                json.dumps(lead_data['metadata']),
                lead_data['created_at'],
                lead_data['created_at']
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
            return {"success": True, "lead_id": lead_data['id']}
            
        except Exception as e:
            logger.error(f"❌ Failed to store lead in database: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
        """Calculate lead score based on available data"""
        score = 0
        
        # Base score
        score += 10
        
        # Email present
        if lead_data.get('email'):
            score += 20
        
        # Name present
        if lead_data.get('name'):
            score += 15
        
        # Phone present
        if lead_data.get('phone'):
            score += 15
        
        # Company present
        if lead_data.get('company'):
            score += 20
        
        # Notes/message present
        if lead_data.get('notes'):
            score += 10
        
        # Source bonus
        source = lead_data.get('source', '').lower()
        if source in ['referral', 'partner']:
            score += 25
        elif source in ['website', 'landing']:
            score += 15
        
        return min(score, 100)  # Cap at 100

# Global instance
webhook_service = None

def get_webhook_service() -> Optional[WebhookIntakeService]:
    """Get the global webhook service instance"""
    global webhook_service
    
    if webhook_service is None:
        config = get_config()
        webhook_config = WebhookConfig(
            secret_key=getattr(config, 'webhook_secret_key', ''),
            allowed_origins=getattr(config, 'webhook_allowed_origins', '').split(','),
            enable_verification=getattr(config, 'webhook_verify_signature', True)
        )
        
        webhook_service = WebhookIntakeService(webhook_config)
    
    return webhook_service
