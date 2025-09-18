"""
Email Parser Service with Structured Data Extraction
Intelligently parses emails to extract leads, contacts, and actionable data
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from core.database_optimization import db_optimizer
from core.enhanced_crm_service import enhanced_crm_service

logger = logging.getLogger(__name__)

@dataclass
class ParsedEmail:
    """Parsed email data structure"""
    id: str
    thread_id: str
    sender_email: str
    sender_name: str
    recipient_email: str
    subject: str
    body_text: str
    body_html: str
    date: datetime
    labels: List[str]
    attachments: List[str]
    extracted_data: Dict[str, Any]
    lead_potential: int
    action_required: bool

@dataclass
class EmailInsight:
    """Email insight data structure"""
    email_id: str
    insight_type: str
    confidence: float
    data: Dict[str, Any]
    suggested_action: str

class EmailParserService:
    """Email parser service with intelligent data extraction"""
    
    def __init__(self):
        self.lead_indicators = [
            'quote', 'pricing', 'cost', 'estimate', 'proposal', 'inquiry',
            'interested', 'contact', 'information', 'demo', 'trial',
            'services', 'help', 'support', 'question', 'request'
        ]
        
        self.contact_patterns = {
            'phone': r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'website': r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            'address': r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)',
            'company': r'(?:Inc|LLC|Corp|Corporation|Ltd|Limited|Company|Co)\.?'
        }
        
        self.priority_keywords = [
            'urgent', 'asap', 'immediately', 'rush', 'emergency',
            'important', 'priority', 'deadline', 'due date'
        ]
        
        self.automation_triggers = {
            'quote_request': ['quote', 'pricing', 'cost', 'estimate'],
            'support_request': ['help', 'support', 'issue', 'problem', 'bug'],
            'demo_request': ['demo', 'trial', 'test', 'sample'],
            'meeting_request': ['meeting', 'call', 'schedule', 'appointment'],
            'follow_up': ['follow up', 'checking in', 'status update']
        }
    
    def parse_email(self, email_data: Dict[str, Any], user_id: int) -> ParsedEmail:
        """Parse email and extract structured data"""
        try:
            # Extract basic email information
            parsed_email = self._extract_basic_info(email_data)
            
            # Extract structured data
            extracted_data = self._extract_structured_data(parsed_email)
            
            # Calculate lead potential
            lead_potential = self._calculate_lead_potential(parsed_email, extracted_data)
            
            # Determine if action is required
            action_required = self._determine_action_required(parsed_email, extracted_data)
            
            # Update parsed email with extracted data
            parsed_email.extracted_data = extracted_data
            parsed_email.lead_potential = lead_potential
            parsed_email.action_required = action_required
            
            # Store parsed email
            self._store_parsed_email(parsed_email, user_id)
            
            # Create lead if high potential
            if lead_potential >= 70:
                self._create_lead_from_email(parsed_email, user_id)
            
            return parsed_email
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            raise
    
    def get_email_insights(self, user_id: int, time_period: str = 'today') -> List[EmailInsight]:
        """Get insights from parsed emails"""
        try:
            insights = []
            
            # Get parsed emails for time period
            emails = self._get_parsed_emails(user_id, time_period)
            
            # Generate insights
            insights.extend(self._generate_lead_insights(emails))
            insights.extend(self._generate_automation_insights(emails))
            insights.extend(self._generate_performance_insights(emails))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting email insights: {e}")
            return []
    
    def extract_contacts_from_email(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract contact information from email"""
        try:
            contacts = []
            
            # Combine email text sources
            text_sources = [
                email_data.get('subject', ''),
                email_data.get('body_text', ''),
                email_data.get('sender_name', ''),
                email_data.get('sender_email', '')
            ]
            
            full_text = ' '.join(text_sources)
            
            # Extract phone numbers
            phone_matches = re.findall(self.contact_patterns['phone'], full_text)
            for match in phone_matches:
                phone = ''.join(match)
                if len(phone.replace('-', '').replace('.', '').replace(' ', '')) >= 10:
                    contacts.append({
                        'type': 'phone',
                        'value': phone,
                        'confidence': 0.8
                    })
            
            # Extract email addresses
            email_matches = re.findall(self.contact_patterns['email'], full_text)
            for email in email_matches:
                if email != email_data.get('sender_email'):
                    contacts.append({
                        'type': 'email',
                        'value': email,
                        'confidence': 0.9
                    })
            
            # Extract websites
            website_matches = re.findall(self.contact_patterns['website'], full_text)
            for website in website_matches:
                contacts.append({
                    'type': 'website',
                    'value': f"https://{website}",
                    'confidence': 0.7
                })
            
            return contacts
            
        except Exception as e:
            logger.error(f"Error extracting contacts: {e}")
            return []
    
    def classify_email_intent(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify email intent and suggest actions"""
        try:
            # Combine text for analysis
            text_sources = [
                email_data.get('subject', ''),
                email_data.get('body_text', '')
            ]
            
            full_text = ' '.join(text_sources).lower()
            
            # Check for automation triggers
            detected_triggers = []
            for trigger_type, keywords in self.automation_triggers.items():
                for keyword in keywords:
                    if keyword in full_text:
                        detected_triggers.append(trigger_type)
                        break
            
            # Determine priority
            priority = 'normal'
            for keyword in self.priority_keywords:
                if keyword in full_text:
                    priority = 'high'
                    break
            
            # Determine if it's a lead
            is_lead = any(indicator in full_text for indicator in self.lead_indicators)
            
            # Suggest actions
            suggested_actions = []
            if is_lead:
                suggested_actions.append('add_to_crm')
            if 'quote' in full_text:
                suggested_actions.append('send_quote')
            if 'demo' in full_text:
                suggested_actions.append('schedule_demo')
            if 'support' in full_text or 'help' in full_text:
                suggested_actions.append('create_support_ticket')
            
            return {
                'intent': detected_triggers[0] if detected_triggers else 'general',
                'triggers': detected_triggers,
                'priority': priority,
                'is_lead': is_lead,
                'suggested_actions': suggested_actions,
                'confidence': 0.8 if detected_triggers else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error classifying email intent: {e}")
            return {
                'intent': 'general',
                'triggers': [],
                'priority': 'normal',
                'is_lead': False,
                'suggested_actions': [],
                'confidence': 0.0
            }
    
    def _extract_basic_info(self, email_data: Dict[str, Any]) -> ParsedEmail:
        """Extract basic email information"""
        payload = email_data.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract header values
        header_map = {}
        for header in headers:
            header_map[header['name'].lower()] = header['value']
        
        # Extract basic info
        sender_email = header_map.get('from', '')
        subject = header_map.get('subject', '')
        date_str = header_map.get('date', '')
        
        # Parse sender name and email
        if '<' in sender_email and '>' in sender_email:
            sender_name = sender_email.split('<')[0].strip().strip('"')
            email_addr = sender_email.split('<')[1].split('>')[0].strip()
        else:
            sender_name = sender_email
            email_addr = sender_email
        
        # Extract body
        body_text, body_html = self._extract_body(payload)
        
        # Extract labels
        labels = email_data.get('labelIds', [])
        
        # Extract attachments
        attachments = self._extract_attachments(payload)
        
        return ParsedEmail(
            id=email_data['id'],
            thread_id=email_data.get('threadId', ''),
            sender_email=email_addr,
            sender_name=sender_name,
            recipient_email=header_map.get('to', ''),
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            date=datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now(),
            labels=labels,
            attachments=attachments,
            extracted_data={},
            lead_potential=0,
            action_required=False
        )
    
    def _extract_structured_data(self, parsed_email: ParsedEmail) -> Dict[str, Any]:
        """Extract structured data from parsed email"""
        structured_data = {
            'contacts': [],
            'companies': [],
            'keywords': [],
            'intent': {},
            'entities': {}
        }
        
        # Extract contacts
        structured_data['contacts'] = self.extract_contacts_from_email({
            'subject': parsed_email.subject,
            'body_text': parsed_email.body_text,
            'sender_name': parsed_email.sender_name,
            'sender_email': parsed_email.sender_email
        })
        
        # Extract companies
        structured_data['companies'] = self._extract_companies(parsed_email)
        
        # Extract keywords
        structured_data['keywords'] = self._extract_keywords(parsed_email)
        
        # Classify intent
        structured_data['intent'] = self.classify_email_intent({
            'subject': parsed_email.subject,
            'body_text': parsed_email.body_text
        })
        
        # Extract entities
        structured_data['entities'] = self._extract_entities(parsed_email)
        
        return structured_data
    
    def _extract_body(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        """Extract text and HTML body from email payload"""
        body_text = ""
        body_html = ""
        
        def extract_from_part(part):
            nonlocal body_text, body_html
            
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    import base64
                    body_text += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    import base64
                    body_html += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            # Process nested parts
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_from_part(subpart)
        
        extract_from_part(payload)
        
        return body_text, body_html
    
    def _extract_attachments(self, payload: Dict[str, Any]) -> List[str]:
        """Extract attachment information"""
        attachments = []
        
        def extract_from_part(part):
            if part.get('filename'):
                attachments.append(part['filename'])
            
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_from_part(subpart)
        
        extract_from_part(payload)
        
        return attachments
    
    def _extract_companies(self, parsed_email: ParsedEmail) -> List[str]:
        """Extract company names from email"""
        companies = []
        
        # Check sender email domain
        if '@' in parsed_email.sender_email:
            domain = parsed_email.sender_email.split('@')[1]
            companies.append(domain)
        
        # Look for company indicators in text
        text = f"{parsed_email.subject} {parsed_email.body_text}"
        company_matches = re.findall(self.contact_patterns['company'], text, re.IGNORECASE)
        companies.extend(company_matches)
        
        return list(set(companies))  # Remove duplicates
    
    def _extract_keywords(self, parsed_email: ParsedEmail) -> List[str]:
        """Extract important keywords from email"""
        text = f"{parsed_email.subject} {parsed_email.body_text}".lower()
        
        # Define keyword categories
        keyword_categories = {
            'business': ['meeting', 'call', 'schedule', 'appointment', 'conference'],
            'sales': ['quote', 'pricing', 'cost', 'estimate', 'proposal', 'contract'],
            'support': ['help', 'support', 'issue', 'problem', 'bug', 'error'],
            'marketing': ['newsletter', 'promotion', 'offer', 'discount', 'deal']
        }
        
        found_keywords = []
        for category, keywords in keyword_categories.items():
            for keyword in keywords:
                if keyword in text:
                    found_keywords.append(keyword)
        
        return found_keywords
    
    def _extract_entities(self, parsed_email: ParsedEmail) -> Dict[str, Any]:
        """Extract named entities from email"""
        entities = {
            'dates': [],
            'amounts': [],
            'locations': [],
            'products': []
        }
        
        text = f"{parsed_email.subject} {parsed_email.body_text}"
        
        # Extract dates (simple pattern)
        date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        entities['dates'] = re.findall(date_pattern, text, re.IGNORECASE)
        
        # Extract amounts (simple pattern)
        amount_pattern = r'\$[\d,]+(?:\.\d{2})?'
        entities['amounts'] = re.findall(amount_pattern, text)
        
        return entities
    
    def _calculate_lead_potential(self, parsed_email: ParsedEmail, extracted_data: Dict[str, Any]) -> int:
        """Calculate lead potential score (0-100)"""
        score = 0
        
        # Base score
        score += 10
        
        # Subject line analysis
        subject_lower = parsed_email.subject.lower()
        for indicator in self.lead_indicators:
            if indicator in subject_lower:
                score += 15
        
        # Intent analysis
        intent = extracted_data.get('intent', {})
        if intent.get('is_lead'):
            score += 25
        
        if intent.get('priority') == 'high':
            score += 20
        
        # Contact information
        contacts = extracted_data.get('contacts', [])
        if contacts:
            score += 10
        
        # Company information
        companies = extracted_data.get('companies', [])
        if companies:
            score += 15
        
        # Keywords
        keywords = extracted_data.get('keywords', [])
        if 'quote' in keywords or 'pricing' in keywords:
            score += 20
        
        return min(score, 100)  # Cap at 100
    
    def _determine_action_required(self, parsed_email: ParsedEmail, extracted_data: Dict[str, Any]) -> bool:
        """Determine if immediate action is required"""
        # Check for high priority indicators
        text = f"{parsed_email.subject} {parsed_email.body_text}".lower()
        
        if any(keyword in text for keyword in self.priority_keywords):
            return True
        
        # Check for lead indicators
        if extracted_data.get('intent', {}).get('is_lead'):
            return True
        
        # Check for specific requests
        request_indicators = ['please', 'need', 'request', 'would like', 'can you']
        if any(indicator in text for indicator in request_indicators):
            return True
        
        return False
    
    def _store_parsed_email(self, parsed_email: ParsedEmail, user_id: int):
        """Store parsed email data"""
        try:
            # Store in database (you might want to create a parsed_emails table)
            # For now, we'll store the extracted data in the leads table metadata
            pass  # Implementation depends on your database schema
            
        except Exception as e:
            logger.error(f"Error storing parsed email: {e}")
    
    def _create_lead_from_email(self, parsed_email: ParsedEmail, user_id: int):
        """Create lead from high-potential email"""
        try:
            # Extract company from sender email domain
            company = ""
            if '@' in parsed_email.sender_email:
                domain = parsed_email.sender_email.split('@')[1]
                company = domain.split('.')[0].title()
            
            # Create lead data
            lead_data = {
                'email': parsed_email.sender_email,
                'name': parsed_email.sender_name,
                'company': company,
                'source': 'gmail',
                'stage': 'new',
                'notes': f"Auto-created from email: {parsed_email.subject}",
                'metadata': {
                    'email_id': parsed_email.id,
                    'thread_id': parsed_email.thread_id,
                    'lead_potential': parsed_email.lead_potential,
                    'extracted_data': parsed_email.extracted_data
                }
            }
            
            # Create lead using CRM service
            result = enhanced_crm_service.create_lead(user_id, lead_data)
            
            if result['success']:
                logger.info(f"Lead created from email: {parsed_email.sender_email}")
            
        except Exception as e:
            logger.error(f"Error creating lead from email: {e}")
    
    def _get_parsed_emails(self, user_id: int, time_period: str) -> List[ParsedEmail]:
        """Get parsed emails for time period"""
        # This would typically query a parsed_emails table
        # For now, return empty list
        return []
    
    def _generate_lead_insights(self, emails: List[ParsedEmail]) -> List[EmailInsight]:
        """Generate lead-related insights"""
        insights = []
        
        high_potential_emails = [e for e in emails if e.lead_potential >= 70]
        
        if high_potential_emails:
            insights.append(EmailInsight(
                email_id='summary',
                insight_type='lead_summary',
                confidence=0.9,
                data={
                    'high_potential_leads': len(high_potential_emails),
                    'total_emails': len(emails),
                    'conversion_rate': len(high_potential_emails) / len(emails) * 100 if emails else 0
                },
                suggested_action='Review high-potential leads in CRM'
            ))
        
        return insights
    
    def _generate_automation_insights(self, emails: List[ParsedEmail]) -> List[EmailInsight]:
        """Generate automation-related insights"""
        insights = []
        
        # Count automation triggers
        trigger_counts = {}
        for email in emails:
            intent = email.extracted_data.get('intent', {})
            triggers = intent.get('triggers', [])
            for trigger in triggers:
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        if trigger_counts:
            most_common_trigger = max(trigger_counts.items(), key=lambda x: x[1])
            insights.append(EmailInsight(
                email_id='automation_summary',
                insight_type='automation_opportunity',
                confidence=0.8,
                data={
                    'most_common_trigger': most_common_trigger[0],
                    'trigger_count': most_common_trigger[1],
                    'total_triggers': sum(trigger_counts.values())
                },
                suggested_action=f'Set up automation for {most_common_trigger[0]}'
            ))
        
        return insights
    
    def _generate_performance_insights(self, emails: List[ParsedEmail]) -> List[EmailInsight]:
        """Generate performance-related insights"""
        insights = []
        
        # Calculate response time insights
        action_required_emails = [e for e in emails if e.action_required]
        
        if action_required_emails:
            insights.append(EmailInsight(
                email_id='performance_summary',
                insight_type='action_required',
                confidence=0.9,
                data={
                    'emails_requiring_action': len(action_required_emails),
                    'total_emails': len(emails),
                    'action_rate': len(action_required_emails) / len(emails) * 100 if emails else 0
                },
                suggested_action='Review emails requiring immediate action'
            ))
        
        return insights

# Global email parser service instance
email_parser_service = EmailParserService()

# Export the email parser service
__all__ = ['EmailParserService', 'email_parser_service', 'ParsedEmail', 'EmailInsight']
