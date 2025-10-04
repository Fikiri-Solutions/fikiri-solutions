#!/usr/bin/env python3
"""
Fikiri Solutions - AI Email Assistant
Lightweight AI-powered email responses with production enhancements.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

class MinimalAIEmailAssistant:
    """Minimal AI email assistant with production enhancements."""
    
    def __init__(self, api_key: Optional[str] = None, services: Dict[str, Any] = None):
        """Initialize AI email assistant with enhanced features."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.enabled = bool(self.api_key)
        self.services = services or {}
        
        # Redis client for analytics
        self.redis_client = None
        self._initialize_redis()
        
        # CRM service for auto-lead capture
        self.crm_service = None
        self._initialize_crm()
        
        if self.enabled:
            try:
                import openai
                
                # OpenAI version compatibility
                if hasattr(openai, 'OpenAI'):
                    # OpenAI >= 1.0.0
                    self.client = openai.OpenAI(api_key=self.api_key)
                    logger.info("✅ OpenAI client initialized (v1.0+)")
                else:
                    # Legacy OpenAI < 1.0.0
                    openai.api_key = self.api_key
                    self.client = openai
                    logger.info("✅ OpenAI client initialized (legacy v0.x)")
                
            except ImportError:
                logger.warning("⚠️ OpenAI not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️ No OpenAI API key found. Set OPENAI_API_KEY environment variable")
    
    def _initialize_redis(self):
        """Initialize Redis client for analytics."""
        try:
            import redis
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
            self.redis_client.ping()
            logger.info("✅ Redis initialized for AI analytics")
        except Exception as e:
            logger.info(f"ℹ️ Redis not available for AI analytics: {e}")
            self.redis_client = None
    
    def _initialize_crm(self):
        """Initialize CRM service for auto-lead capture."""
        try:
            if 'crm' in self.services:
                self.crm_service = self.services['crm']
                logger.info("✅ CRM service initialized for auto-lead capture")
            else:
                logger.info("ℹ️ CRM service not available for auto-lead capture")
        except Exception as e:
            logger.warning(f"CRM initialization failed: {e}")
    
    def is_enabled(self) -> bool:
        """Check if AI assistant is enabled."""
        return self.enabled and self.client is not None
    
    def _track_ai_usage(self, operation: str, success: bool, tokens_used: int = 0):
        """Track AI usage for analytics."""
        if not self.redis_client:
            return
        
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            usage_data = {
                'operation': operation,
                'success': success,
                'tokens_used': tokens_used,
                'timestamp': timestamp
            }
            
            # Store in Redis with TTL
            self.redis_client.lpush("fikiri:ai:usage", json.dumps(usage_data))
            self.redis_client.ltrim("fikiri:ai:usage", 0, 999)  # Keep last 1000 records
            self.redis_client.expire("fikiri:ai:usage", 86400 * 7)  # 7 days TTL
            
        except Exception as e:
            logger.warning(f"Failed to track AI usage: {e}")
    
    def classify_email_intent(self, email_content: str, subject: str = "") -> Dict[str, Any]:
        """Classify email intent using AI with enhanced tracking."""
        if not self.is_enabled():
            return self._fallback_classification(email_content, subject)
        
        try:
            prompt = f"""
            Classify this email into one of these categories:
            - lead_inquiry: Someone interested in services/products
            - support_request: Technical help or issue
            - general_info: General information request
            - complaint: Complaint or negative feedback
            - spam: Spam or irrelevant content
            
            Email Subject: {subject}
            Email Content: {email_content[:500]}
            
            Respond with JSON format:
            {{
                "intent": "category",
                "confidence": 0.0-1.0,
                "urgency": "low|medium|high",
                "suggested_action": "action_to_take"
            }}
            """
            
            # OpenAI version compatibility
            if hasattr(self.client, 'chat'):
                # OpenAI >= 1.0.0
                response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
                result_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
            else:
                # Legacy OpenAI < 1.0.0
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.1
                )
                result_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
            
            result = json.loads(result_text)
            
            # Track usage
            self._track_ai_usage("classify_intent", True, tokens_used)
            
            # Auto-lead capture for lead inquiries
            if result.get("intent") == "lead_inquiry" and self.crm_service:
                self._auto_capture_lead(email_content, subject)
            
            logger.info(f"✅ Email classified as: {result.get('intent')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI classification failed: {e}")
            self._track_ai_usage("classify_intent", False)
            return self._fallback_classification(email_content, subject)
    
    def _auto_capture_lead(self, email_content: str, subject: str):
        """Automatically capture lead information."""
        try:
            # Extract basic info from email
            sender_email = self._extract_email_from_content(email_content)
            sender_name = self._extract_name_from_content(email_content)
            
            if sender_email:
                # Create lead in CRM
                lead = self.crm_service.add_lead(
                    email=sender_email,
                    name=sender_name,
                    source="ai_classification",
                    metadata={
                        "ai_classified": True,
                        "email_subject": subject,
                        "classification_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                # Add note about AI classification
                self.crm_service.add_note(lead.id, f"Auto-captured from AI classification: {subject}")
                
                logger.info(f"✅ Auto-captured lead: {sender_email}")
                
        except Exception as e:
            logger.error(f"❌ Auto-lead capture failed: {e}")
    
    def _extract_email_from_content(self, content: str) -> Optional[str]:
        """Extract email address from content."""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, content)
        return matches[0] if matches else None
    
    def _extract_name_from_content(self, content: str) -> str:
        """Extract name from content."""
        # Simple name extraction - could be enhanced with AI
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            if 'from:' in line.lower() or 'name:' in line.lower():
                return line.split(':')[1].strip() if ':' in line else ""
        return ""
    
    def generate_response(self, email_content: str, sender_name: str, subject: str, intent: str = "general") -> str:
        """Generate AI-powered email response with enhanced features."""
        if not self.is_enabled():
            return self._fallback_response(sender_name, subject)
        
        try:
            # Load business context
            business_context = self._load_business_context()
            
            prompt = f"""
            You are a professional email assistant for {business_context['company_name']}.
            
            Business Context:
            - Company: {business_context['company_name']}
            - Services: {business_context['services']}
            - Tone: {business_context['tone']}
            
            Email Details:
            - From: {sender_name}
            - Subject: {subject}
            - Content: {email_content[:300]}
            - Intent: {intent}
            
            Generate a professional, helpful response that:
            1. Acknowledges their message
            2. Addresses their specific needs
            3. Maintains professional tone
            4. Includes next steps if appropriate
            5. Keeps it concise (2-3 paragraphs max)
            
            Don't include signature - that will be added separately.
            """
            
            # OpenAI version compatibility
            if hasattr(self.client, 'chat'):
                # OpenAI >= 1.0.0
                response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
                generated_response = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0
            else:
                # Legacy OpenAI < 1.0.0
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.7
                )
                generated_response = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Track usage
            self._track_ai_usage("generate_response", True, tokens_used)
            
            logger.info(f"✅ AI response generated for {sender_name}")
            return generated_response
            
        except Exception as e:
            logger.error(f"❌ AI response generation failed: {e}")
            self._track_ai_usage("generate_response", False)
            return self._fallback_response(sender_name, subject)
    
    def extract_contact_info(self, email_content: str) -> Dict[str, Any]:
        """Extract contact information from email with enhanced tracking."""
        if not self.is_enabled():
            return self._fallback_contact_extraction(email_content)
        
        try:
            prompt = f"""
            Extract contact information from this email:
            
            {email_content[:500]}
            
            Return JSON format:
            {{
                "phone": "phone_number_or_null",
                "company": "company_name_or_null",
                "website": "website_or_null",
                "location": "location_or_null",
                "budget": "budget_info_or_null",
                "timeline": "timeline_info_or_null"
            }}
            """
            
            # OpenAI version compatibility
            if hasattr(self.client, 'chat'):
                # OpenAI >= 1.0.0
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1
            )
                result_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
            else:
                # Legacy OpenAI < 1.0.0
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.1
                )
                result_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
            
            result = json.loads(result_text)
            
            # Track usage
            self._track_ai_usage("extract_contact", True, tokens_used)
            
            logger.info(f"✅ Contact info extracted")
            return result
            
        except Exception as e:
            logger.error(f"❌ Contact extraction failed: {e}")
            self._track_ai_usage("extract_contact", False)
            return self._fallback_contact_extraction(email_content)
    
    def summarize_email_thread(self, emails: List[Dict[str, Any]]) -> str:
        """Summarize an email thread with enhanced tracking."""
        if not self.is_enabled() or len(emails) < 2:
            return "Email thread summary not available"
        
        try:
            thread_content = ""
            for email in emails[-5:]:  # Last 5 emails
                thread_content += f"From: {email.get('sender', 'Unknown')}\n"
                thread_content += f"Subject: {email.get('subject', 'No subject')}\n"
                thread_content += f"Content: {email.get('content', '')[:200]}\n\n"
            
            prompt = f"""
            Summarize this email thread in 2-3 sentences:
            
            {thread_content}
            
            Focus on:
            - Main topic/discussion
            - Key decisions made
            - Next steps or action items
            """
            
            # OpenAI version compatibility
            if hasattr(self.client, 'chat'):
                # OpenAI >= 1.0.0
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
                summary = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0
            else:
                # Legacy OpenAI < 1.0.0
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Track usage
            self._track_ai_usage("summarize_thread", True, tokens_used)
            
            logger.info(f"✅ Email thread summarized")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Thread summarization failed: {e}")
            self._track_ai_usage("summarize_thread", False)
            return "Email thread summary not available"
    
    async def generate_response_async(self, email_content: str, sender_name: str, subject: str, intent: str = "general") -> str:
        """Async version of generate_response for FastAPI compatibility."""
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_response, email_content, sender_name, subject, intent)
    
    async def classify_email_intent_async(self, email_content: str, subject: str = "") -> Dict[str, Any]:
        """Async version of classify_email_intent for FastAPI compatibility."""
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.classify_email_intent, email_content, subject)
    
    def get_ai_stats(self) -> Dict[str, Any]:
        """Get AI usage statistics."""
        stats = {
            "enabled": self.is_enabled(),
            "openai_version": "unknown",
            "redis_available": self.redis_client is not None,
            "crm_integration": self.crm_service is not None,
            "total_operations": 0,
            "successful_operations": 0,
            "total_tokens": 0
        }
        
        # Get OpenAI version
        try:
            import openai
            if hasattr(openai, 'OpenAI'):
                stats["openai_version"] = "1.0+"
            else:
                stats["openai_version"] = "0.x"
        except ImportError:
            stats["openai_version"] = "not_installed"
        
        # Get usage stats from Redis
        if self.redis_client:
            try:
                usage_records = self.redis_client.lrange("fikiri:ai:usage", 0, -1)
                stats["total_operations"] = len(usage_records)
                
                successful_count = 0
                total_tokens = 0
                
                for record in usage_records:
                    try:
                        data = json.loads(record)
                        if data.get("success"):
                            successful_count += 1
                        total_tokens += data.get("tokens_used", 0)
                    except:
                        continue
                
                stats["successful_operations"] = successful_count
                stats["total_tokens"] = total_tokens
                
            except Exception as e:
                logger.warning(f"Failed to get AI stats from Redis: {e}")
        
        return stats
    
    def _load_business_context(self) -> Dict[str, str]:
        """Load business context from file or use defaults."""
        try:
            business_file = Path("data/business_profile.json")
            if business_file.exists():
                with open(business_file, 'r') as f:
                    context = json.load(f)
                    logger.info("✅ Business context loaded from file")
                    return context
        except Exception as e:
            logger.warning(f"Failed to load business context: {e}")
        
        # Default business context
        return {
            "company_name": "Fikiri Solutions",
            "services": "Gmail automation and lead management",
            "tone": "professional and helpful"
        }
    
    def _fallback_classification(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Fallback classification when AI is not available."""
        content_lower = email_content.lower()
        subject_lower = subject.lower()
        
        # Simple keyword-based classification
        if any(word in content_lower for word in ['price', 'cost', 'quote', 'buy', 'purchase', 'interested']):
            return {
                "intent": "lead_inquiry",
                "confidence": 0.7,
                "urgency": "medium",
                "suggested_action": "send_pricing_info"
            }
        elif any(word in content_lower for word in ['help', 'support', 'issue', 'problem', 'bug']):
            return {
                "intent": "support_request",
                "confidence": 0.8,
                "urgency": "high",
                "suggested_action": "escalate_to_support"
            }
        elif any(word in content_lower for word in ['complaint', 'angry', 'upset', 'disappointed']):
            return {
                "intent": "complaint",
                "confidence": 0.9,
                "urgency": "high",
                "suggested_action": "escalate_to_manager"
            }
        else:
            return {
                "intent": "general_info",
                "confidence": 0.6,
                "urgency": "low",
                "suggested_action": "send_general_info"
            }
    
    def _fallback_response(self, sender_name: str, subject: str) -> str:
        """Fallback response when AI is not available."""
        return f"""Dear {sender_name},

Thank you for your email regarding "{subject}".

We have received your message and will review it carefully. Our team will get back to you within 24 hours with a detailed response.

If this is an urgent matter, please don't hesitate to call us directly.

Best regards,
Fikiri Solutions Team"""
    
    def _fallback_contact_extraction(self, email_content: str) -> Dict[str, Any]:
        """Fallback contact extraction when AI is not available."""
        import re
        
        # Simple regex-based extraction
        phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_match = re.search(phone_pattern, email_content)
        
        website_pattern = r'https?://[^\s]+'
        website_match = re.search(website_pattern, email_content)
        
        return {
            "phone": phone_match.group(0) if phone_match else None,
            "company": None,
            "website": website_match.group(0) if website_match else None,
            "location": None,
            "budget": None,
            "timeline": None
        }
    
def create_ai_assistant(api_key: Optional[str] = None, services: Dict[str, Any] = None) -> MinimalAIEmailAssistant:
    """Create and return an AI assistant instance."""
    return MinimalAIEmailAssistant(api_key, services)

if __name__ == "__main__":
    # Test the AI assistant
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    logger.info("🧪 Testing Enhanced AI Email Assistant")
    logger.info("=" * 50)
    
    # Test with mock services
    mock_services = {
        'crm': type('MockCRM', (), {
            'add_lead': lambda self, **kwargs: type('MockLead', (), {'id': 'test123'})(),
            'add_note': lambda self, lead_id, note: True
        })()
    }
    
    ai = MinimalAIEmailAssistant(services=mock_services)
    
    # Test classification
    logger.info("Testing email classification...")
    test_email = """
    Hi there,
    
    I'm interested in your Gmail automation services. Could you please send me pricing information?
    
    Best regards,
    John Doe
    john.doe@example.com
    """
    
    classification = ai.classify_email_intent(test_email, "Inquiry about services")
    logger.info(f"✅ Classification: {classification}")
    
    # Test response generation
    logger.info("Testing response generation...")
    response = ai.generate_response(test_email, "John Doe", "Inquiry about services", "lead_inquiry")
    logger.info(f"✅ Response generated: {len(response)} characters")
    
    # Test contact extraction
    logger.info("Testing contact extraction...")
    contact_info = ai.extract_contact_info(test_email)
    logger.info(f"✅ Contact info: {contact_info}")
    
    # Test stats
    logger.info("Testing AI stats...")
    stats = ai.get_ai_stats()
    logger.info(f"✅ AI Stats: {stats}")
    
    logger.info("🎉 All AI assistant tests completed!")