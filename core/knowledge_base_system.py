"""
Knowledge Base Integration System for Fikiri Solutions
Searchable knowledge repository with document indexing and retrieval
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid
import hashlib
from pathlib import Path

from core.minimal_config import get_config

logger = logging.getLogger(__name__)


def _get_vector_search():
    """Lazy import to avoid circular import and heavy startup (sentence_transformers/Pinecone)."""
    from core.minimal_vector_search import get_vector_search
    return get_vector_search()

class DocumentType(Enum):
    """Knowledge base document types"""
    ARTICLE = "article"
    GUIDE = "guide"
    TUTORIAL = "tutorial"
    FAQ = "faq"
    API_DOC = "api_doc"
    TROUBLESHOOTING = "troubleshooting"
    FEATURE_DOC = "feature_doc"
    INTEGRATION_GUIDE = "integration_guide"

class ContentFormat(Enum):
    """Content format types"""
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"
    JSON = "json"

@dataclass
class KnowledgeDocument:
    """Knowledge base document structure"""
    id: str
    title: str
    content: str
    summary: str
    document_type: DocumentType
    format: ContentFormat
    tags: List[str]
    keywords: List[str]
    category: str
    author: str
    version: str
    created_at: datetime
    updated_at: datetime
    view_count: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    search_rank: float = 1.0
    metadata: Dict[str, Any] = None

@dataclass
class SearchResult:
    """Knowledge base search result"""
    document: KnowledgeDocument
    relevance_score: float
    matched_sections: List[str]
    highlighted_content: str
    match_explanation: str

@dataclass
class SearchResponse:
    """Knowledge base search response"""
    success: bool
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: float
    suggestions: List[str]
    filters_applied: Dict[str, Any]

class KnowledgeBaseSystem:
    """Knowledge base with intelligent search and document management"""
    
    def __init__(self):
        self.config = get_config()
        self.documents = self._load_default_documents()
        self.search_index = self._build_search_index()
        
        logger.info("📚 Knowledge base system initialized")
    
    def _load_default_documents(self) -> Dict[str, KnowledgeDocument]:
        """Load default knowledge base documents"""
        documents = {}
        
        # Getting Started Guide
        getting_started = KnowledgeDocument(
            id="guide_getting_started",
            title="Getting Started with Fikiri Solutions",
            content="""# Getting Started with Fikiri Solutions

Welcome to Fikiri Solutions! This guide will help you set up your account and start automating your business processes.

## Step 1: Create Your Account

1. Visit [fikirisolutions.com](https://fikirisolutions.com)
2. Click "Sign Up" and enter your details
3. Verify your email address
4. Complete the onboarding wizard

## Step 2: Connect Your Tools

### Gmail Integration
1. Go to Settings > Integrations
2. Click "Connect Gmail"
3. Authorize Fikiri to access your email
4. Configure email filters and rules

### CRM Setup
1. Navigate to CRM > Settings
2. Import your existing contacts
3. Set up pipeline stages
4. Configure lead scoring rules

## Step 3: Create Your First Automation

1. Go to Automations > Create New
2. Choose a trigger (e.g., "New Email Received")
3. Add actions (e.g., "Classify Email", "Generate Response")
4. Test and activate your automation

## Step 4: Monitor and Optimize

- Check your Dashboard for performance metrics
- Review AI-generated responses before sending
- Adjust automation rules based on results
- Use Analytics to identify improvement opportunities

## Next Steps

- Explore our Templates library
- Set up additional integrations
- Join our community forum for tips and tricks
- Schedule a training session with our team

Need help? Contact support@fikirisolutions.com or use our in-app chat.""",
            summary="Complete guide to setting up and using Fikiri Solutions, from account creation to your first automation.",
            document_type=DocumentType.GUIDE,
            format=ContentFormat.MARKDOWN,
            tags=["getting-started", "setup", "onboarding", "tutorial"],
            keywords=["setup", "account", "gmail", "crm", "automation", "integration"],
            category="Getting Started",
            author="Fikiri Team",
            version="1.0",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            search_rank=5.0,
            metadata={"difficulty": "beginner", "estimated_time": "30 minutes"}
        )
        documents[getting_started.id] = getting_started
        
        # Email Automation Guide
        email_automation = KnowledgeDocument(
            id="guide_email_automation",
            title="Email Automation Best Practices",
            content="""# Email Automation Best Practices

Learn how to create effective email automations that save time and improve customer engagement.

## Understanding Email Automation

Email automation uses AI to automatically handle your email communications. This includes:
- Classifying incoming emails by intent and priority
- Generating appropriate responses
- Scheduling follow-ups
- Managing email workflows

## Setting Up Email Rules

### 1. Classification Rules
Configure how emails are categorized:
- **Lead Inquiries**: Potential customers asking about services
- **Support Requests**: Existing customers needing help
- **Billing Questions**: Payment and invoice related emails
- **General Information**: Basic questions about your business

### 2. Response Templates
Create templates for common scenarios:
- Quote request acknowledgments
- Appointment scheduling
- Service information
- Follow-up sequences

### 3. Approval Workflows
Set up review processes:
- Require approval for high-value responses
- Auto-send for routine inquiries
- Flag sensitive content for manual review

## Advanced Features

### Smart Scheduling
- Send emails at optimal times based on recipient behavior
- Respect time zones and business hours
- Avoid sending during holidays or weekends

### Personalization
- Use customer data to personalize responses
- Include relevant service information
- Reference previous interactions

### A/B Testing
- Test different subject lines
- Compare response templates
- Optimize send times

## Best Practices

1. **Start Simple**: Begin with basic rules and expand gradually
2. **Monitor Performance**: Regular review response quality and engagement
3. **Maintain Human Touch**: Don't automate everything - some emails need personal attention
4. **Keep Learning**: AI improves with feedback, so review and rate responses
5. **Stay Compliant**: Ensure automated emails follow regulations (CAN-SPAM, GDPR)

## Common Mistakes to Avoid

- Over-automating personal communications
- Not reviewing AI responses before sending
- Ignoring customer feedback about automated responses
- Setting up too many complex rules initially
- Forgetting to update templates regularly

## Troubleshooting

### Emails Not Being Classified
- Check your classification rules
- Ensure keywords are properly configured
- Review email content for clarity

### Poor Response Quality
- Update your templates
- Provide more context to the AI
- Review and rate responses to improve learning

### Low Engagement Rates
- Test different subject lines
- Personalize content more
- Check send times and frequency

Need more help? Check our FAQ section or contact support.""",
            summary="Comprehensive guide to setting up and optimizing email automation workflows.",
            document_type=DocumentType.GUIDE,
            format=ContentFormat.MARKDOWN,
            tags=["email", "automation", "best-practices", "workflows"],
            keywords=["email", "automation", "rules", "templates", "classification"],
            category="Email Management",
            author="Fikiri Team",
            version="1.2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            search_rank=4.5,
            metadata={"difficulty": "intermediate", "estimated_time": "45 minutes"}
        )
        documents[email_automation.id] = email_automation
        
        # API Documentation
        api_docs = KnowledgeDocument(
            id="api_documentation",
            title="Fikiri Solutions API Documentation",
            content="""# Fikiri Solutions API Documentation

Complete reference for integrating with Fikiri Solutions via our REST API.

## Authentication

All API requests require authentication using API keys.

### Getting Your API Key
1. Log into your Fikiri dashboard
2. Go to Settings > API Keys
3. Click "Generate New Key"
4. Copy and securely store your key

### Using API Keys
Include your API key in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY
```

## Base URL
All API endpoints are relative to: `https://api.fikirisolutions.com/v1`

## Endpoints

### CRM Endpoints

#### Get Leads
```
GET /crm/leads
```
Retrieve all leads for your account.

**Parameters:**
- `limit` (optional): Number of results (default: 50, max: 200)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by lead status

**Response:**
```json
{
  "success": true,
  "leads": [
    {
      "id": "lead_123",
      "name": "John Doe",
      "email": "john@example.com",
      "status": "new",
      "score": 85,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 150,
  "has_more": true
}
```

#### Create Lead
```
POST /crm/leads
```
Create a new lead.

**Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "555-123-4567",
  "company": "Example Corp",
  "source": "website"
}
```

### Email Automation Endpoints

#### Send Email
```
POST /email/send
```
Send an automated email.

**Body:**
```json
{
  "to": "recipient@example.com",
  "subject": "Your Subject",
  "template_id": "template_123",
  "variables": {
    "name": "John",
    "company": "Example Corp"
  }
}
```

#### Get Email Templates
```
GET /email/templates
```
Retrieve available email templates.

### Document Processing Endpoints

#### Process Document
```
POST /documents/process
```
Process a document using AI.

**Body (multipart/form-data):**
- `file`: Document file
- `options`: Processing options (JSON)

### Analytics Endpoints

#### Get Metrics
```
GET /analytics/metrics
```
Retrieve account metrics and analytics.

**Parameters:**
- `period` (optional): Time period (7d, 30d, 90d)
- `metrics` (optional): Specific metrics to retrieve

## Rate Limits

- **Free Plan**: 100 requests per hour
- **Starter Plan**: 1,000 requests per hour
- **Growth Plan**: 5,000 requests per hour
- **Business Plan**: 20,000 requests per hour
- **Enterprise Plan**: Unlimited

## Error Handling

The API uses standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Invalid or missing API key
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

Error responses include details:
```json
{
  "success": false,
  "error": "Invalid email address",
  "code": "INVALID_EMAIL"
}
```

## SDKs and Libraries

We provide official SDKs for:
- Python
- Node.js
- PHP
- Ruby

## Webhooks

Configure webhooks to receive real-time notifications:

1. Go to Settings > Webhooks
2. Add your endpoint URL
3. Select events to receive
4. Verify webhook signature for security

## Support

For API support:
- Email: api-support@fikirisolutions.com
- Documentation: docs.fikirisolutions.com
- Community: community.fikirisolutions.com""",
            summary="Complete API documentation with endpoints, authentication, and examples.",
            document_type=DocumentType.API_DOC,
            format=ContentFormat.MARKDOWN,
            tags=["api", "documentation", "integration", "developers"],
            keywords=["api", "rest", "endpoints", "authentication", "integration"],
            category="Developer Resources",
            author="Fikiri Engineering",
            version="1.1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            search_rank=4.0,
            metadata={"difficulty": "advanced", "audience": "developers"}
        )
        documents[api_docs.id] = api_docs
        
        # Troubleshooting Guide
        troubleshooting = KnowledgeDocument(
            id="troubleshooting_guide",
            title="Common Issues and Solutions",
            content="""# Common Issues and Solutions

Quick solutions to frequently encountered problems.

## Email Integration Issues

### Gmail Connection Problems
**Problem**: Can't connect Gmail account
**Solutions**:
1. Check that IMAP is enabled in Gmail settings
2. Ensure 2-factor authentication is set up
3. Generate an app-specific password
4. Clear browser cache and try again

### Emails Not Being Processed
**Problem**: Incoming emails aren't being automated
**Solutions**:
1. Check email filters and rules
2. Verify Gmail labels are set correctly
3. Ensure automation rules are active
4. Check for quota limits

## CRM Issues

### Leads Not Syncing
**Problem**: New leads aren't appearing in CRM
**Solutions**:
1. Check integration settings
2. Verify API credentials
3. Review data mapping configuration
4. Check for duplicate detection rules

### Incorrect Lead Scoring
**Problem**: Lead scores seem inaccurate
**Solutions**:
1. Review scoring criteria
2. Update lead scoring rules
3. Retrain AI model with feedback
4. Check data quality

## AI Response Issues

### Poor Response Quality
**Problem**: AI responses are not helpful
**Solutions**:
1. Provide more context in templates
2. Review and rate responses to improve AI
3. Update knowledge base content
4. Adjust response tone settings

### Responses Too Generic
**Problem**: Responses lack personalization
**Solutions**:
1. Add more customer data fields
2. Use dynamic variables in templates
3. Enable conversation context
4. Review personalization settings

## Document Processing Issues

### OCR Accuracy Problems
**Problem**: Text extraction from images is poor
**Solutions**:
1. Use higher resolution images
2. Ensure good contrast and lighting
3. Try different file formats
4. Manually review and correct results

### Slow Processing
**Problem**: Document processing takes too long
**Solutions**:
1. Reduce file size before upload
2. Use supported file formats
3. Check internet connection
4. Contact support for large files

## Integration Issues

### API Errors
**Problem**: Getting API error responses
**Solutions**:
1. Check API key validity
2. Verify endpoint URLs
3. Review request format
4. Check rate limits

### Webhook Failures
**Problem**: Webhooks not being received
**Solutions**:
1. Verify webhook URL is accessible
2. Check SSL certificate
3. Review webhook signature validation
4. Test with webhook testing tools

## Performance Issues

### Slow Dashboard Loading
**Problem**: Dashboard takes too long to load
**Solutions**:
1. Clear browser cache
2. Check internet connection
3. Try different browser
4. Contact support if persistent

### High Memory Usage
**Problem**: Browser using too much memory
**Solutions**:
1. Close unused tabs
2. Restart browser
3. Clear cache and cookies
4. Update browser to latest version

## Account Issues

### Login Problems
**Problem**: Can't log into account
**Solutions**:
1. Reset password
2. Clear browser cache
3. Check email for security alerts
4. Contact support if account locked

### Billing Issues
**Problem**: Payment or billing questions
**Solutions**:
1. Check payment method on file
2. Review billing history
3. Contact billing support
4. Update payment information

## Getting More Help

If these solutions don't resolve your issue:

1. **Search Knowledge Base**: Use the search function for specific topics
2. **Contact Support**: Email support@fikirisolutions.com
3. **Live Chat**: Use in-app chat for immediate help
4. **Community Forum**: Ask questions in our community
5. **Schedule Call**: Book a call with our support team

## Reporting Bugs

When reporting bugs, please include:
- Detailed description of the issue
- Steps to reproduce
- Browser and version
- Screenshots if applicable
- Error messages (if any)

This helps us resolve issues faster!""",
            summary="Solutions to common problems and troubleshooting steps for Fikiri Solutions.",
            document_type=DocumentType.TROUBLESHOOTING,
            format=ContentFormat.MARKDOWN,
            tags=["troubleshooting", "problems", "solutions", "support"],
            keywords=["troubleshooting", "issues", "problems", "solutions", "help"],
            category="Support",
            author="Fikiri Support",
            version="1.3",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            search_rank=4.8,
            metadata={"difficulty": "beginner", "type": "troubleshooting"}
        )
        documents[troubleshooting.id] = troubleshooting
        
        # Landscaping Business Guide
        landscaping_guide = KnowledgeDocument(
            id="landscaping_business_guide",
            title="Fikiri for Landscaping Businesses",
            content="""# Fikiri Solutions for Landscaping Businesses

Specialized guide for landscaping companies to maximize automation benefits.

## Why Landscaping Businesses Love Fikiri

Landscaping is a seasonal, relationship-driven business with unique challenges:
- Managing seasonal workflows
- Handling quote requests efficiently  
- Following up with prospects
- Scheduling seasonal services
- Managing customer communications

Fikiri understands these challenges and provides specialized automation.

## Key Features for Landscapers

### Smart Quote Management
- Automatically classify quote requests
- Generate professional estimates
- Follow up with prospects
- Track quote-to-customer conversion

### Seasonal Workflow Automation
- **Spring**: Cleanup reminders, new service offerings
- **Summer**: Maintenance scheduling, watering reminders
- **Fall**: Leaf removal, winterization services
- **Winter**: Snow removal, planning for next season

### Customer Communication
- Automated appointment confirmations
- Weather-related service updates
- Seasonal service reminders
- Post-service follow-ups

## Setting Up Your Landscaping Automation

### Step 1: Import Your Contacts
1. Upload existing customer list
2. Categorize by service type (residential, commercial)
3. Tag seasonal preferences
4. Set up customer segments

### Step 2: Configure Service Templates
Create templates for:
- **Lawn Care**: Mowing, edging, fertilizing
- **Design Services**: Consultations, installations
- **Maintenance**: Pruning, weeding, cleanup
- **Seasonal**: Spring cleanup, fall preparation

### Step 3: Set Up Quote Automation
1. Create quote request forms
2. Set up automatic acknowledgments
3. Configure follow-up sequences
4. Track conversion metrics

### Step 4: Seasonal Reminders
- Schedule service reminders based on season
- Set up weather-triggered communications
- Automate seasonal service offerings
- Plan ahead for busy seasons

## Best Practices for Landscapers

### Customer Segmentation
- **Residential Regular**: Weekly/bi-weekly service
- **Residential Seasonal**: Spring/fall only
- **Commercial Contracts**: Year-round maintenance
- **Design Clients**: One-time projects

### Timing Communications
- **Best Times**: Tuesday-Thursday, 9AM-11AM or 2PM-4PM
- **Avoid**: Early mornings, late evenings, weekends
- **Seasonal Adjustments**: Earlier in summer, later in winter

### Personalization Tips
- Reference property characteristics
- Mention previous services
- Include seasonal recommendations
- Use local weather information

## Sample Automations

### New Quote Request
1. **Trigger**: Quote form submission
2. **Actions**:
   - Send immediate acknowledgment
   - Create lead in CRM
   - Schedule site visit reminder
   - Add to follow-up sequence

### Seasonal Service Reminder
1. **Trigger**: Date-based (seasonal)
2. **Actions**:
   - Send service reminder email
   - Include seasonal tips
   - Offer scheduling link
   - Track response rates

### Post-Service Follow-up
1. **Trigger**: Service completion
2. **Actions**:
   - Send satisfaction survey
   - Request photos/testimonials
   - Schedule next service
   - Offer additional services

## Measuring Success

### Key Metrics to Track
- **Quote Response Rate**: % of quotes that get responses
- **Conversion Rate**: Quotes that become customers
- **Customer Retention**: Year-over-year retention
- **Service Efficiency**: Time saved on communications
- **Revenue Growth**: Increase in bookings

### Monthly Review Process
1. Review automation performance
2. Analyze seasonal trends
3. Update templates and messaging
4. Plan for upcoming season
5. Gather customer feedback

## Advanced Features

### Weather Integration
- Automatically reschedule during bad weather
- Send weather-related service updates
- Offer emergency services during storms
- Adjust seasonal timing based on weather patterns

### Photo Documentation
- Request before/after photos
- Build portfolio automatically
- Use for marketing materials
- Track service quality

### Referral Automation
- Automatically request referrals after successful projects
- Send thank-you messages for referrals
- Track referral sources
- Reward loyal customers

## Common Landscaping Scenarios

### Spring Rush Management
- Automate cleanup service offerings
- Schedule consultations efficiently
- Manage high volume of inquiries
- Set expectations for response times

### Summer Maintenance
- Automate weekly service confirmations
- Handle vacation scheduling
- Manage watering reminders
- Track service completion

### Fall Preparation
- Promote leaf removal services
- Schedule winterization services
- Offer snow removal contracts
- Plan for next year's projects

## Integration with Other Tools

### Scheduling Software
- Sync with popular scheduling tools
- Automate appointment confirmations
- Handle rescheduling requests
- Track technician availability

### Accounting Systems
- Sync customer information
- Automate invoice generation
- Track payment status
- Generate financial reports

### Marketing Platforms
- Sync customer lists
- Automate email campaigns
- Track marketing ROI
- Segment audiences

## Getting Started Checklist

- [ ] Set up customer segments
- [ ] Create service templates
- [ ] Configure quote automation
- [ ] Set up seasonal reminders
- [ ] Test all automations
- [ ] Train team on new processes
- [ ] Monitor performance metrics
- [ ] Gather customer feedback

Need help setting up? Contact our landscaping specialists at landscaping@fikirisolutions.com""",
            summary="Complete guide for landscaping businesses to use Fikiri Solutions effectively.",
            document_type=DocumentType.GUIDE,
            format=ContentFormat.MARKDOWN,
            tags=["landscaping", "business", "seasonal", "automation"],
            keywords=["landscaping", "seasonal", "quotes", "customers", "lawn", "garden"],
            category="Industry Guides",
            author="Fikiri Industry Team",
            version="1.0",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            search_rank=3.5,
            metadata={"industry": "landscaping", "difficulty": "intermediate"}
        )
        documents[landscaping_guide.id] = landscaping_guide
        
        return documents
    
    def _build_search_index(self) -> Dict[str, List[str]]:
        """Build search index for fast text search"""
        index = {}
        
        for doc_id, document in self.documents.items():
            # Index title, content, tags, and keywords
            text_content = f"{document.title} {document.content} {' '.join(document.tags)} {' '.join(document.keywords)}"
            
            # Tokenize and index
            words = self._tokenize_text(text_content)
            for word in words:
                if word not in index:
                    index[word] = []
                if doc_id not in index[word]:
                    index[word].append(doc_id)
        
        return index
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for search indexing"""
        # Convert to lowercase and remove special characters
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words and filter short words
        words = [word.strip() for word in cleaned.split() if len(word.strip()) > 2]
        
        return words
    
    def search(self, query: str, filters: Dict[str, Any] = None, 
               limit: int = 10) -> SearchResponse:
        """Search knowledge base with intelligent ranking"""
        start_time = datetime.now()
        
        try:
            # Clean and tokenize query
            query_words = self._tokenize_text(query)
            
            if not query_words:
                return SearchResponse(
                    success=False,
                    query=query,
                    results=[],
                    total_results=0,
                    search_time=0,
                    suggestions=[],
                    filters_applied=filters or {}
                )
            
            # Find matching documents
            candidate_docs = self._find_candidate_documents(query_words)
            
            # Score and rank results
            scored_results = []
            for doc_id in candidate_docs:
                document = self.documents[doc_id]
                
                # Apply filters
                if filters and not self._matches_filters(document, filters):
                    continue
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(document, query, query_words)
                
                if relevance_score > 0.1:  # Minimum relevance threshold
                    # Find matched sections
                    matched_sections = self._find_matched_sections(document, query_words)
                    
                    # Generate highlighted content
                    highlighted_content = self._highlight_content(document, query_words)
                    
                    # Generate match explanation
                    match_explanation = self._generate_match_explanation(document, query_words, relevance_score)
                    
                    result = SearchResult(
                        document=document,
                        relevance_score=relevance_score,
                        matched_sections=matched_sections,
                        highlighted_content=highlighted_content,
                        match_explanation=match_explanation
                    )
                    scored_results.append(result)
            
            # Sort by relevance score
            scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Limit results
            final_results = scored_results[:limit]
            
            # Generate search suggestions
            suggestions = self._generate_search_suggestions(query, final_results)
            
            # Update view counts
            for result in final_results:
                result.document.view_count += 1
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            return SearchResponse(
                success=True,
                query=query,
                results=final_results,
                total_results=len(scored_results),
                search_time=search_time,
                suggestions=suggestions,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            logger.error(f"❌ Knowledge base search failed: {e}")
            search_time = (datetime.now() - start_time).total_seconds()
            
            return SearchResponse(
                success=False,
                query=query,
                results=[],
                total_results=0,
                search_time=search_time,
                suggestions=[],
                filters_applied=filters or {}
            )
    
    def _find_candidate_documents(self, query_words: List[str]) -> List[str]:
        """Find candidate documents that match query words"""
        candidates = set()
        
        for word in query_words:
            if word in self.search_index:
                candidates.update(self.search_index[word])
        
        return list(candidates)
    
    def _matches_filters(self, document: KnowledgeDocument, filters: Dict[str, Any]) -> bool:
        """Check if document matches search filters"""
        # Tenant isolation (highest priority - security critical)
        if 'tenant_id' in filters:
            doc_tenant_id = document.metadata.get('tenant_id')
            if doc_tenant_id != filters['tenant_id']:
                return False  # Reject documents from other tenants
        
        if 'document_type' in filters:
            if document.document_type.value != filters['document_type']:
                return False
        
        if 'category' in filters:
            if document.category.lower() != filters['category'].lower():
                return False
        
        if 'tags' in filters:
            filter_tags = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            if not any(tag in document.tags for tag in filter_tags):
                return False
        
        if 'author' in filters:
            if document.author.lower() != filters['author'].lower():
                return False
        
        return True
    
    def _calculate_relevance_score(self, document: KnowledgeDocument, 
                                  query: str, query_words: List[str]) -> float:
        """Calculate relevance score for document"""
        score = 0.0
        
        # Title matching (high weight)
        title_words = self._tokenize_text(document.title)
        title_matches = len(set(query_words) & set(title_words))
        score += title_matches * 3.0
        
        # Content matching (medium weight)
        content_words = self._tokenize_text(document.content)
        content_matches = len(set(query_words) & set(content_words))
        score += content_matches * 1.0
        
        # Tag matching (high weight)
        tag_words = self._tokenize_text(' '.join(document.tags))
        tag_matches = len(set(query_words) & set(tag_words))
        score += tag_matches * 2.5
        
        # Keyword matching (high weight)
        keyword_words = self._tokenize_text(' '.join(document.keywords))
        keyword_matches = len(set(query_words) & set(keyword_words))
        score += keyword_matches * 2.5
        
        # Summary matching (medium weight)
        summary_words = self._tokenize_text(document.summary)
        summary_matches = len(set(query_words) & set(summary_words))
        score += summary_matches * 1.5
        
        # Apply document-specific boosts
        score *= document.search_rank  # Document importance
        
        # Popularity boost (based on view count and helpful votes)
        popularity_score = (document.view_count * 0.1) + (document.helpful_votes * 0.2)
        score += popularity_score
        
        # Normalize by query length
        if query_words:
            score = score / len(query_words)
        
        return min(score, 10.0)  # Cap at 10.0
    
    def _find_matched_sections(self, document: KnowledgeDocument, 
                              query_words: List[str]) -> List[str]:
        """Find sections of document that match query"""
        sections = []
        
        # Split content into sections (by headers)
        content_sections = re.split(r'\n#+\s+', document.content)
        
        for section in content_sections:
            section_words = self._tokenize_text(section)
            if any(word in section_words for word in query_words):
                # Get first sentence or paragraph
                first_paragraph = section.split('\n\n')[0].strip()
                if first_paragraph and len(first_paragraph) > 20:
                    sections.append(first_paragraph[:200] + "..." if len(first_paragraph) > 200 else first_paragraph)
        
        return sections[:3]  # Return top 3 matched sections
    
    def _highlight_content(self, document: KnowledgeDocument, 
                          query_words: List[str]) -> str:
        """Generate highlighted content snippet"""
        content = document.content
        
        # Find best snippet (containing most query words)
        best_snippet = ""
        max_matches = 0
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph_words = self._tokenize_text(paragraph)
            matches = len(set(query_words) & set(paragraph_words))
            
            if matches > max_matches:
                max_matches = matches
                best_snippet = paragraph.strip()
        
        # If no good snippet found, use summary
        if not best_snippet:
            best_snippet = document.summary
        
        # Truncate if too long
        if len(best_snippet) > 300:
            best_snippet = best_snippet[:300] + "..."
        
        # Simple highlighting (wrap matched words)
        for word in query_words:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            best_snippet = pattern.sub(f"**{word}**", best_snippet)
        
        return best_snippet
    
    def _generate_match_explanation(self, document: KnowledgeDocument, 
                                   query_words: List[str], relevance_score: float) -> str:
        """Generate explanation of why document matches"""
        explanations = []
        
        # Check title matches
        title_words = self._tokenize_text(document.title)
        title_matches = set(query_words) & set(title_words)
        if title_matches:
            explanations.append(f"Title contains: {', '.join(title_matches)}")
        
        # Check tag matches
        tag_words = self._tokenize_text(' '.join(document.tags))
        tag_matches = set(query_words) & set(tag_words)
        if tag_matches:
            explanations.append(f"Tagged with: {', '.join(tag_matches)}")
        
        # Check keyword matches
        keyword_words = self._tokenize_text(' '.join(document.keywords))
        keyword_matches = set(query_words) & set(keyword_words)
        if keyword_matches:
            explanations.append(f"Keywords: {', '.join(keyword_matches)}")
        
        # Add relevance score
        explanations.append(f"Relevance: {relevance_score:.1f}/10")
        
        return " | ".join(explanations) if explanations else "Content match"
    
    def _generate_search_suggestions(self, query: str, results: List[SearchResult]) -> List[str]:
        """Generate search suggestions based on query and results"""
        suggestions = []
        
        # Suggest related tags from results
        all_tags = set()
        for result in results[:3]:  # Top 3 results
            all_tags.update(result.document.tags)
        
        # Convert tags to search suggestions
        for tag in list(all_tags)[:3]:
            if tag.lower() not in query.lower():
                suggestions.append(f"{query} {tag}")
        
        # Suggest related categories
        categories = set(result.document.category for result in results[:3])
        for category in categories:
            if category.lower() not in query.lower():
                suggestions.append(f"{category} guide")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def add_document(self, title: str, content: str, summary: Optional[str] = None,
                    document_type: DocumentType = None, tags: List[str] = None,
                    keywords: List[str] = None, category: str = "general", author: Optional[str] = None,
                    metadata: Dict[str, Any] = None) -> str:
        """Add new document to knowledge base."""
        if summary is None:
            summary = (content or "")[:500] or ""
        if author is None:
            author = ""
        if document_type is None:
            document_type = DocumentType.FAQ
        if tags is None:
            tags = []
        if keywords is None:
            keywords = []
        try:
            doc_id = str(uuid.uuid4())
            
            document = KnowledgeDocument(
                id=doc_id,
                title=title,
                content=content,
                summary=summary,
                document_type=document_type,
                format=ContentFormat.MARKDOWN,
                tags=tags,
                keywords=keywords,
                category=category,
                author=author,
                version="1.0",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=metadata or {}
            )
            
            self.documents[doc_id] = document
            
            # Update search index
            self._update_search_index(doc_id, document)
            
            logger.info(f"✅ Added knowledge document: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add document: {e}")
            raise
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing document and sync to vector index when vector_id is present."""
        try:
            if doc_id not in self.documents:
                return False

            document = self.documents[doc_id]

            # Update fields
            for field, value in updates.items():
                if hasattr(document, field):
                    setattr(document, field, value)

            document.updated_at = datetime.now()

            # Update search index
            self._update_search_index(doc_id, document)

            # Sync to vector index (see docs/CRUD_RAG_ARCHITECTURE.md)
            new_text = f"Title: {document.title}\n{document.content}"
            if getattr(document, "summary", None):
                new_text = f"{document.summary}\n\n{new_text}"
            vector_meta = {
                "type": "knowledge_base",
                "document_id": doc_id,
                "title": getattr(document, "title", ""),
                "category": getattr(document, "category", ""),
                "tags": getattr(document, "tags", []) or [],
                "author": getattr(document, "author", ""),
            }
            # Preserve tenant_id and user_id from document metadata for multi-tenant isolation
            meta = getattr(document, "metadata", None)
            if isinstance(meta, dict):
                vector_id = meta.get("vector_id")
                # Preserve tenant isolation fields
                if "tenant_id" in meta:
                    vector_meta["tenant_id"] = meta["tenant_id"]
                if "user_id" in meta:
                    vector_meta["user_id"] = meta["user_id"]
            else:
                vector_id = None
            if vector_id is not None:
                try:
                    vs = _get_vector_search()
                    if getattr(vs, "use_pinecone", False) is True:
                        vs.upsert_document(str(vector_id), new_text, vector_meta)
                    else:
                        vs.update_document(int(vector_id), new_text, vector_meta)
                    logger.info(f"✅ Synced knowledge document {doc_id} to vector index")
                except Exception as ve:
                    logger.warning("Vector index update failed for doc %s: %s", doc_id, ve)
            else:
                # Self-heal: re-add to vector and store vector_id so future updates/deletes stay in sync
                try:
                    vs = _get_vector_search()
                    # Ensure tenant_id is preserved when self-healing
                    if isinstance(meta, dict) and "tenant_id" in meta:
                        vector_meta["tenant_id"] = meta["tenant_id"]
                    if isinstance(meta, dict) and "user_id" in meta:
                        vector_meta["user_id"] = meta["user_id"]
                    if getattr(vs, "use_pinecone", False) is True:
                        vs.upsert_document(doc_id, new_text, vector_meta)
                        new_vid = doc_id
                    else:
                        new_vid = vs.add_document(new_text, vector_meta)
                    if new_vid is not None and (new_vid >= 0 if isinstance(new_vid, int) else True):
                        new_meta = dict(meta) if isinstance(meta, dict) else {}
                        new_meta["vector_id"] = new_vid
                        setattr(document, "metadata", new_meta)
                        logger.info("✅ Self-healed vector_id for knowledge document %s (was missing)", doc_id)
                except Exception as ve:
                    logger.warning("Vector self-heal (re-add) failed for doc %s: %s", doc_id, ve)

            logger.info(f"✅ Updated knowledge document: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update document: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document from knowledge base and remove from vector index when vector_id is present."""
        try:
            if doc_id not in self.documents:
                return False

            document = self.documents[doc_id]
            vector_id = None
            meta = getattr(document, "metadata", None)
            if isinstance(meta, dict):
                vector_id = meta.get("vector_id")

            if vector_id is not None:
                try:
                    vs = _get_vector_search()
                    if getattr(vs, "use_pinecone", False) is True:
                        vs.delete_document_by_id(str(vector_id))
                    else:
                        vs.delete_document(int(vector_id))
                    logger.info(f"✅ Removed knowledge document {doc_id} from vector index")
                except Exception as ve:
                    logger.warning("Vector index delete failed for doc %s: %s", doc_id, ve)

            del self.documents[doc_id]
            self._remove_from_search_index(doc_id)
            logger.info(f"✅ Deleted knowledge document: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete document: {e}")
            return False
    
    def _update_search_index(self, doc_id: str, document: KnowledgeDocument):
        """Update search index for document"""
        # Remove old entries
        self._remove_from_search_index(doc_id)
        
        # Add new entries
        text_content = f"{document.title} {document.content} {' '.join(document.tags)} {' '.join(document.keywords)}"
        words = self._tokenize_text(text_content)
        
        for word in words:
            if word not in self.search_index:
                self.search_index[word] = []
            if doc_id not in self.search_index[word]:
                self.search_index[word].append(doc_id)
    
    def _remove_from_search_index(self, doc_id: str):
        """Remove document from search index"""
        for word, doc_list in self.search_index.items():
            if doc_id in doc_list:
                doc_list.remove(doc_id)
    
    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)

    def list_documents(self, tenant_id: Optional[str] = None) -> List[KnowledgeDocument]:
        """List all documents, optionally filtered by tenant_id (from metadata)."""
        docs = list(self.documents.values())
        if tenant_id is not None:
            docs = [d for d in docs if (d.metadata or {}).get("tenant_id") == tenant_id]
        return docs

    def get_popular_documents(self, limit: int = 10) -> List[KnowledgeDocument]:
        """Get most popular documents by view count"""
        sorted_docs = sorted(self.documents.values(), 
                           key=lambda d: d.view_count + (d.helpful_votes * 2), 
                           reverse=True)
        return sorted_docs[:limit]
    
    def get_recent_documents(self, limit: int = 10) -> List[KnowledgeDocument]:
        """Get most recently added/updated documents"""
        sorted_docs = sorted(self.documents.values(), 
                           key=lambda d: d.updated_at, 
                           reverse=True)
        return sorted_docs[:limit]
    
    def get_categories(self) -> List[str]:
        """Get all document categories"""
        categories = set(doc.category for doc in self.documents.values())
        return sorted(list(categories))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            total_docs = len(self.documents)
            total_views = sum(doc.view_count for doc in self.documents.values())
            total_votes = sum(doc.helpful_votes + doc.unhelpful_votes for doc in self.documents.values())
            
            # Most popular document
            most_popular = max(self.documents.values(), key=lambda d: d.view_count) if self.documents else None
            
            # Document types
            doc_types = {}
            for doc in self.documents.values():
                doc_type = doc.document_type.value
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Categories
            categories = {}
            for doc in self.documents.values():
                category = doc.category
                categories[category] = categories.get(category, 0) + 1
            
            return {
                "total_documents": total_docs,
                "total_views": total_views,
                "total_votes": total_votes,
                "document_types": doc_types,
                "categories": categories,
                "most_popular": {
                    "title": most_popular.title,
                    "views": most_popular.view_count
                } if most_popular else None,
                "search_index_size": len(self.search_index)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {}

# Global instance
knowledge_base = KnowledgeBaseSystem()

def get_knowledge_base() -> KnowledgeBaseSystem:
    """Get the global knowledge base instance"""
    return knowledge_base
