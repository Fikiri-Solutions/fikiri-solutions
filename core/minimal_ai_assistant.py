#!/usr/bin/env python3
"""
Fikiri Solutions - AI Email Assistant
Lightweight AI-powered email responses using OpenAI API.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

class MinimalAIEmailAssistant:
    """Minimal AI email assistant - lightweight version."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI email assistant."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                print("✅ OpenAI client initialized")
            except ImportError:
                print("⚠️  OpenAI not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                print(f"⚠️  OpenAI initialization failed: {e}")
                self.enabled = False
        else:
            print("⚠️  No OpenAI API key found. Set OPENAI_API_KEY environment variable")
    
    def is_enabled(self) -> bool:
        """Check if AI assistant is enabled."""
        return self.enabled and self.client is not None
    
    def classify_email_intent(self, email_content: str, subject: str = "") -> Dict[str, Any]:
        """Classify email intent using AI."""
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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"✅ Email classified as: {result['intent']}")
            return result
            
        except Exception as e:
            print(f"❌ AI classification failed: {e}")
            return self._fallback_classification(email_content, subject)
    
    def generate_response(self, email_content: str, sender_name: str, subject: str, intent: str = "general") -> str:
        """Generate AI-powered email response."""
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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            generated_response = response.choices[0].message.content.strip()
            print(f"✅ AI response generated for {sender_name}")
            return generated_response
            
        except Exception as e:
            print(f"❌ AI response generation failed: {e}")
            return self._fallback_response(sender_name, subject)
    
    def extract_contact_info(self, email_content: str) -> Dict[str, Any]:
        """Extract contact information from email."""
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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"✅ Contact info extracted")
            return result
            
        except Exception as e:
            print(f"❌ Contact extraction failed: {e}")
            return self._fallback_contact_extraction(email_content)
    
    def summarize_email_thread(self, emails: List[Dict[str, Any]]) -> str:
        """Summarize an email thread."""
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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            print(f"✅ Email thread summarized")
            return summary
            
        except Exception as e:
            print(f"❌ Thread summarization failed: {e}")
            return "Email thread summary not available"
    
    def _fallback_classification(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Fallback classification without AI."""
        content_lower = (email_content + " " + subject).lower()
        
        if any(word in content_lower for word in ["support", "help", "issue", "problem", "bug"]):
            return {"intent": "support_request", "confidence": 0.8, "urgency": "medium", "suggested_action": "escalate_to_support"}
        elif any(word in content_lower for word in ["quote", "price", "cost", "service", "product"]):
            return {"intent": "lead_inquiry", "confidence": 0.8, "urgency": "high", "suggested_action": "send_to_sales"}
        elif any(word in content_lower for word in ["complaint", "angry", "disappointed", "terrible"]):
            return {"intent": "complaint", "confidence": 0.7, "urgency": "high", "suggested_action": "escalate_to_manager"}
        else:
            return {"intent": "general_info", "confidence": 0.6, "urgency": "low", "suggested_action": "standard_response"}
    
    def _fallback_response(self, sender_name: str, subject: str) -> str:
        """Fallback response without AI."""
        return f"""Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team"""
    
    def _fallback_contact_extraction(self, email_content: str) -> Dict[str, Any]:
        """Fallback contact extraction without AI."""
        import re
        
        # Simple regex patterns
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        website_pattern = r'https?://[^\s]+'
        
        return {
            "phone": re.search(phone_pattern, email_content).group() if re.search(phone_pattern, email_content) else None,
            "company": None,
            "website": re.search(website_pattern, email_content).group() if re.search(website_pattern, email_content) else None,
            "location": None,
            "budget": None,
            "timeline": None
        }
    
    def _load_business_context(self) -> Dict[str, Any]:
        """Load business context from config."""
        try:
            with open("data/business_profile.json", "r") as f:
                return json.load(f)
        except:
            return {
                "company_name": "Fikiri Solutions",
                "services": "Gmail automation and lead management",
                "tone": "professional and helpful"
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get AI usage statistics."""
        return {
            "enabled": self.is_enabled(),
            "api_key_configured": bool(self.api_key),
            "client_initialized": self.client is not None
        }
    
    def generate_chat_response(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """Generate AI response for chat interface."""
        if not self.is_enabled():
            return self._enhanced_fallback_response(user_message)
        
        try:
            # Build conversation context
            messages = []
            
            # Add system context with more specific instructions
            messages.append({
                "role": "system", 
                "content": """You are Fikiri Solutions AI Assistant. You help businesses with:
                - Email automation and responses
                - Lead management and CRM
                - Business process optimization
                - Customer communication strategies
                
                Be helpful, professional, and concise. When users ask about specific data (like "how many emails do I have"), provide helpful guidance about setting up integrations. Always suggest actionable next steps."""
            })
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-6:]:  # Last 6 messages for context
                    messages.append({
                        "role": "user" if msg.get('type') == 'user' else "assistant",
                        "content": msg.get('content', '')
                    })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=400,
                temperature=0.7
            )
            
            generated_response = response.choices[0].message.content.strip()
            print(f"✅ Chat response generated")
            return generated_response
            
        except Exception as e:
            print(f"❌ Chat response generation failed: {e}")
            return self._enhanced_fallback_response(user_message)
    
    def _enhanced_fallback_response(self, user_message: str) -> str:
        """Enhanced fallback response with system integration."""
        message_lower = user_message.lower()
        
        # Email-related queries
        if any(word in message_lower for word in ["email", "emails", "inbox", "message", "messages", "received", "unread"]):
            if "how many" in message_lower or "count" in message_lower:
                return "I can help you check your email count! To get the exact number of emails in your inbox, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section, and I'll be able to show you real-time email statistics."
            elif "last" in message_lower or "recent" in message_lower:
                return "I'd be happy to show you your most recent emails! To access your latest messages, I need to connect to your email service (Gmail, Outlook, etc.). Please set up your email integration in the Services section."
            else:
                return "I can help you manage your emails! To access your inbox, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section."
        
        # Lead/Customer queries - try to get real data
        elif any(word in message_lower for word in ["lead", "leads", "customer", "customers", "client", "clients", "prospect", "prospects"]):
            if "how many" in message_lower or "count" in message_lower:
                # Try to get actual lead count from CRM if available
                try:
                    from core.minimal_crm_service import MinimalCRMService
                    crm = MinimalCRMService()
                    leads = crm.get_all_leads()
                    lead_count = len(leads)
                    return f"Great question! I can see you currently have {lead_count} leads in your CRM system. You can view and manage all your leads in the CRM section. I can also help automate lead scoring and follow-ups once your email integration is set up."
                except:
                    return "I can help you check your lead count! To get the exact number of leads in your CRM, please visit the CRM section. I can also help automate lead scoring and follow-ups once your email integration is set up."
            elif "last" in message_lower or "recent" in message_lower:
                return "I can help you find your most recent leads! Check out the CRM section to view and manage your contacts. I can also help automate lead scoring and follow-ups."
            else:
                return "I can help you manage leads and customers! Check out the CRM section to view and manage your contacts. I can also help automate lead scoring and follow-ups."
        
        # Service/System queries
        elif any(word in message_lower for word in ["service", "services", "system", "status", "working", "down"]):
            return "I can help you check your service status! Visit the Services section to see the status of all your integrations (Gmail, Outlook, AI Assistant, CRM). You can also test each service to ensure everything is working properly."
        
        # Help/Support queries
        elif any(word in message_lower for word in ["help", "support", "assistance", "how to", "how do i"]):
            return "I'm here to help! I can assist with email automation, lead management, customer communication, and business process optimization. What specific area would you like help with? You can also check the Services section to set up integrations."
        
        # Greeting queries
        elif any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return "Hello! I'm your Fikiri Solutions AI Assistant. I can help you with email automation, lead management, and customer communication. To get started, you can set up your email integration in the Services section."
        
        # Default response with more context
        else:
            return "I'm Fikiri Solutions AI Assistant! I can help you with email automation, lead management, and customer communication. To provide more specific assistance, please set up your email integration in the Services section. How can I assist you today?"
    
    def _fallback_chat_response(self, user_message: str) -> str:
        """Enhanced fallback chat response without AI."""
        message_lower = user_message.lower()
        
        # Email-related queries
        if any(word in message_lower for word in ["email", "emails", "inbox", "message", "messages", "received", "unread"]):
            if "how many" in message_lower or "count" in message_lower:
                return "I can help you check your email count! To get the exact number of emails in your inbox, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section, and I'll be able to show you real-time email statistics."
            elif "last" in message_lower or "recent" in message_lower:
                return "I'd be happy to show you your most recent emails! To access your latest messages, I need to connect to your email service (Gmail, Outlook, etc.). Please set up your email integration in the Services section."
            else:
                return "I can help you manage your emails! To access your inbox, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section."
        
        # Lead/Customer queries
        elif any(word in message_lower for word in ["lead", "leads", "customer", "customers", "client", "clients", "prospect", "prospects"]):
            if "how many" in message_lower or "count" in message_lower:
                return "I can help you check your lead count! To get the exact number of leads in your CRM, please visit the CRM section. I can also help automate lead scoring and follow-ups once your email integration is set up."
            elif "last" in message_lower or "recent" in message_lower:
                return "I can help you find your most recent leads! Check out the CRM section to view and manage your contacts. I can also help automate lead scoring and follow-ups."
            else:
                return "I can help you manage leads and customers! Check out the CRM section to view and manage your contacts. I can also help automate lead scoring and follow-ups."
        
        # Service/System queries
        elif any(word in message_lower for word in ["service", "services", "system", "status", "working", "down"]):
            return "I can help you check your service status! Visit the Services section to see the status of all your integrations (Gmail, Outlook, AI Assistant, CRM). You can also test each service to ensure everything is working properly."
        
        # Help/Support queries
        elif any(word in message_lower for word in ["help", "support", "assistance", "how to", "how do i"]):
            return "I'm here to help! I can assist with email automation, lead management, customer communication, and business process optimization. What specific area would you like help with? You can also check the Services section to set up integrations."
        
        # Greeting queries
        elif any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return "Hello! I'm your Fikiri Solutions AI Assistant. I can help you with email automation, lead management, and customer communication. To get started, you can set up your email integration in the Services section."
        
        # Default response with more context
        else:
            return "I'm Fikiri Solutions AI Assistant! I can help you with email automation, lead management, and customer communication. To provide more specific assistance, please set up your email integration in the Services section. How can I assist you today?"

def create_ai_assistant(api_key: Optional[str] = None) -> MinimalAIEmailAssistant:
    """Create and return an AI email assistant instance."""
    return MinimalAIEmailAssistant(api_key)

if __name__ == "__main__":
    # Test the AI email assistant
    print("🧪 Testing Minimal AI Email Assistant")
    print("=" * 50)
    
    assistant = MinimalAIEmailAssistant()
    
    print(f"✅ AI Assistant enabled: {assistant.is_enabled()}")
    
    # Test classification
    print("\nTesting email classification...")
    sample_email = "Hi, I'm interested in your services. Can you send me a quote for your premium package?"
    classification = assistant.classify_email_intent(sample_email, "Quote Request")
    print(f"✅ Classification: {classification['intent']} (confidence: {classification['confidence']})")
    
    # Test response generation
    print("\nTesting response generation...")
    response = assistant.generate_response(sample_email, "John Doe", "Quote Request", classification['intent'])
    print(f"✅ Response generated: {response[:100]}...")
    
    # Test contact extraction
    print("\nTesting contact extraction...")
    contact_info = assistant.extract_contact_info("My phone is 555-123-4567 and I work at ABC Corp")
    print(f"✅ Contact info: {contact_info}")
    
    # Test stats
    print("\nTesting stats...")
    stats = assistant.get_usage_stats()
    print(f"✅ Stats: {stats}")
    
    print("\n🎉 All AI assistant tests completed!")

