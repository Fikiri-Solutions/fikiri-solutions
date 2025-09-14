#!/usr/bin/env python3
"""
Fikiri Solutions - Simple Chatbot Service
Lightweight chatbot using OpenAI API and local FAQ data.
"""

import json
import logging
import openai
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

class SimpleChatbot:
    """Simple chatbot using OpenAI API and FAQ data."""
    
    def __init__(self, faq_file: str = "data/faq_knowledge.json", 
                 business_profile_file: str = "data/business_profile.json"):
        """Initialize the chatbot."""
        self.faq_file = Path(faq_file)
        self.business_profile_file = Path(business_profile_file)
        self.logger = logging.getLogger(__name__)
        
        # Load FAQ data
        self.faq_data = self._load_faq_data()
        
        # Load business profile
        self.business_profile = self._load_business_info()
        
        # Initialize OpenAI client
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
                self.logger.info("✅ OpenAI client initialized")
            else:
                self.logger.warning("⚠️ OPENAI_API_KEY not found, using fallback responses")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize OpenAI: {e}")
    
    def _load_faq_data(self) -> Dict[str, Any]:
        """Load FAQ data from JSON file."""
        try:
            if self.faq_file.exists():
                with open(self.faq_file, 'r') as f:
                    data = json.load(f)
                self.logger.info(f"📁 Loaded {len(data.get('faqs', []))} FAQs")
                return data
            else:
                self.logger.warning(f"⚠️ FAQ file not found: {self.faq_file}")
                return {'faqs': []}
        except Exception as e:
            self.logger.error(f"❌ Failed to load FAQ data: {e}")
            return {'faqs': []}
    
    def _load_business_info(self) -> Dict[str, Any]:
        """Load business profile information."""
        try:
            if self.business_profile_file.exists():
                with open(self.business_profile_file, 'r') as f:
                    data = json.load(f)
                self.logger.info("📁 Loaded business profile")
                return data
            else:
                self.logger.warning(f"⚠️ Business profile not found: {self.business_profile_file}")
                return {
                    'business_name': 'Fikiri Solutions',
                    'business_type': 'Business Automation',
                    'description': 'We help businesses streamline their operations with intelligent automation.'
                }
        except Exception as e:
            self.logger.error(f"❌ Failed to load business profile: {e}")
            return {
                'business_name': 'Fikiri Solutions',
                'business_type': 'Business Automation',
                'description': 'We help businesses streamline their operations with intelligent automation.'
            }
    
    def _create_context_prompt(self, user_query: str) -> str:
        """Create context prompt for OpenAI."""
        business_name = self.business_profile.get('business_name', 'Fikiri Solutions')
        business_type = self.business_profile.get('business_type', 'Business Automation')
        description = self.business_profile.get('description', '')
        
        # Get relevant FAQs
        relevant_faqs = self._get_relevant_faqs(user_query)
        
        context = f"""You are a helpful assistant for {business_name}, a {business_type} company.

Company Description: {description}

Relevant FAQ Information:
"""
        
        for faq in relevant_faqs[:3]:  # Limit to top 3 FAQs
            context += f"Q: {faq['question']}\nA: {faq['answer']}\n\n"
        
        context += f"""
User Query: {user_query}

Please provide a helpful, professional response based on the company information and FAQs above. 
If the query is not related to our services, politely redirect to our main offerings.
Keep responses concise and helpful.
"""
        
        return context
    
    def _get_relevant_faqs(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant FAQs based on query."""
        query_lower = query.lower()
        relevant_faqs = []
        
        for faq in self.faq_data.get('faqs', []):
            question = faq.get('question', '').lower()
            answer = faq.get('answer', '').lower()
            keywords = faq.get('keywords', [])
            
            # Simple keyword matching
            relevance_score = 0
            
            # Check question similarity
            if any(word in question for word in query_lower.split()):
                relevance_score += 2
            
            # Check answer similarity
            if any(word in answer for word in query_lower.split()):
                relevance_score += 1
            
            # Check keywords
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    relevance_score += 3
            
            if relevance_score > 0:
                faq_copy = faq.copy()
                faq_copy['relevance_score'] = relevance_score
                relevant_faqs.append(faq_copy)
        
        # Sort by relevance score
        relevant_faqs.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_faqs
    
    def generate_response(self, user_query: str) -> Dict[str, Any]:
        """Generate response to user query."""
        try:
            if not user_query.strip():
                return {
                    'answer': 'Hello! How can I help you today?',
                    'confidence': 1.0,
                    'source': 'fallback',
                    'suggestions': self._get_suggestions()
                }
            
            # Try OpenAI first if available
            if self.openai_client:
                try:
                    response = self._generate_openai_response(user_query)
                    if response:
                        return response
                except Exception as e:
                    self.logger.warning(f"⚠️ OpenAI generation failed: {e}")
            
            # Fallback to FAQ matching
            return self._generate_faq_response(user_query)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate response: {e}")
            return self._fallback_response()
    
    def _generate_openai_response(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Generate response using OpenAI API."""
        try:
            context_prompt = self._create_context_prompt(user_query)
            
            response = self.openai_client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful business assistant."},
                    {"role": "user", "content": context_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                'answer': answer,
                'confidence': 0.9,
                'source': 'openai',
                'suggestions': self._get_suggestions()
            }
            
        except Exception as e:
            self.logger.error(f"❌ OpenAI API error: {e}")
            return None
    
    def _generate_faq_response(self, user_query: str) -> Dict[str, Any]:
        """Generate response using FAQ matching."""
        relevant_faqs = self._get_relevant_faqs(user_query)
        
        if relevant_faqs:
            best_faq = relevant_faqs[0]
            return {
                'answer': best_faq['answer'],
                'confidence': min(0.8, best_faq['relevance_score'] / 5.0),
                'source': 'faq',
                'suggestions': self._get_suggestions()
            }
        else:
            return self._fallback_response()
    
    def _fallback_response(self) -> Dict[str, Any]:
        """Generate fallback response."""
        return {
            'answer': f"Thank you for your question! I'd be happy to help you learn more about {self.business_profile.get('business_name', 'our services')}. Please feel free to ask about our offerings or contact us directly for more information.",
            'confidence': 0.5,
            'source': 'fallback',
            'suggestions': self._get_suggestions()
        }
    
    def _get_suggestions(self) -> List[str]:
        """Get suggested questions."""
        suggestions = []
        for faq in self.faq_data.get('faqs', [])[:5]:
            suggestions.append(faq.get('question', ''))
        return suggestions
    
    def add_faq(self, question: str, answer: str, keywords: List[str] = None) -> bool:
        """Add a new FAQ."""
        try:
            if keywords is None:
                keywords = []
            
            new_faq = {
                'id': f"faq_{len(self.faq_data.get('faqs', [])) + 1:03d}",
                'question': question,
                'answer': answer,
                'keywords': keywords,
                'category': 'general',
                'priority': 1,
                'created_at': datetime.now().isoformat()
            }
            
            if 'faqs' not in self.faq_data:
                self.faq_data['faqs'] = []
            
            self.faq_data['faqs'].append(new_faq)
            
            # Save to file
            with open(self.faq_file, 'w') as f:
                json.dump(self.faq_data, f, indent=2)
            
            self.logger.info(f"✅ Added FAQ: {question}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add FAQ: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics."""
        return {
            'total_faqs': len(self.faq_data.get('faqs', [])),
            'business_name': self.business_profile.get('business_name', 'Unknown'),
            'openai_available': self.openai_client is not None,
            'faq_file_exists': self.faq_file.exists(),
            'business_profile_exists': self.business_profile_file.exists()
        }

# Global chatbot instance
chatbot_engine = SimpleChatbot()
