"""
Smart FAQ System for Fikiri Solutions
Intelligent FAQ matching, responses, and conversation handling
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid
from difflib import SequenceMatcher
import math

from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class FAQCategory(Enum):
    """FAQ categories"""
    GENERAL = "general"
    PRICING = "pricing"
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURES = "features"
    INTEGRATION = "integration"
    SUPPORT = "support"
    LANDSCAPING = "landscaping"
    AUTOMATION = "automation"

class MatchConfidence(Enum):
    """FAQ match confidence levels"""
    EXACT = "exact"           # 95-100%
    HIGH = "high"            # 80-94%
    MEDIUM = "medium"        # 60-79%
    LOW = "low"             # 40-59%
    NONE = "none"           # 0-39%

@dataclass
class FAQEntry:
    """FAQ entry structure"""
    id: str
    question: str
    answer: str
    category: FAQCategory
    keywords: List[str]
    variations: List[str]  # Alternative ways to ask the same question
    priority: int = 1  # Higher priority = more likely to match
    created_at: datetime = None
    updated_at: datetime = None
    usage_count: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0

@dataclass
class FAQMatch:
    """FAQ match result"""
    faq_entry: FAQEntry
    confidence: float
    match_type: str  # "exact", "keyword", "semantic", "variation"
    matched_text: str
    explanation: str

@dataclass
class FAQResponse:
    """FAQ response structure"""
    success: bool
    matches: List[FAQMatch]
    best_match: Optional[FAQMatch]
    suggested_questions: List[str]
    fallback_response: Optional[str]
    processing_time: float

class SmartFAQSystem:
    """Smart FAQ system with intelligent matching and responses"""
    
    def __init__(self):
        self.config = get_config()
        self.faq_entries = self._load_default_faqs()
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'what', 'how', 'when', 'where', 'why',
            'can', 'could', 'would', 'should', 'do', 'does', 'did', 'i', 'you',
            'we', 'they', 'my', 'your', 'our', 'their'
        }
        # Optimized: Build inverted index for O(1) keyword lookups instead of O(n) scans
        self._keyword_index: Dict[str, List[str]] = {}
        self._build_keyword_index()
        
        logger.info("🤖 Smart FAQ system initialized")
    
    def _build_keyword_index(self):
        """Build inverted index mapping keywords to FAQ IDs for O(1) lookups"""
        self._keyword_index = {}
        for faq_id, faq in self.faq_entries.items():
            # Combine all keywords from FAQ
            all_keywords = set(faq.keywords)
            # Add words from question and answer
            faq_text = f"{faq.question} {faq.answer}".lower()
            text_keywords = self._extract_keywords(faq_text)
            all_keywords.update(text_keywords)
            
            # Add to inverted index
            for keyword in all_keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = []
                self._keyword_index[keyword].append(faq_id)
    
    def _load_default_faqs(self) -> Dict[str, FAQEntry]:
        """Load default FAQ entries"""
        faqs = {}
        
        # General FAQs
        general_faqs = [
            FAQEntry(
                id="general_what_is_fikiri",
                question="What is Fikiri Solutions?",
                answer="Fikiri Solutions is an AI-powered business automation platform that helps companies streamline their email management, CRM processes, document handling, and customer interactions. We use advanced AI to automate repetitive tasks and improve business efficiency.",
                category=FAQCategory.GENERAL,
                keywords=["fikiri", "solutions", "what", "company", "business", "platform"],
                variations=[
                    "What does Fikiri Solutions do?",
                    "Tell me about Fikiri",
                    "What is your company about?",
                    "What services does Fikiri offer?"
                ],
                priority=5,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="general_how_it_works",
                question="How does Fikiri Solutions work?",
                answer="Fikiri Solutions works by connecting to your existing business tools (email, CRM, documents) and using AI to automate routine tasks. Our platform learns from your business patterns and provides intelligent responses, lead scoring, document processing, and workflow automation.",
                category=FAQCategory.GENERAL,
                keywords=["how", "works", "process", "automation", "ai", "integration"],
                variations=[
                    "How does the platform work?",
                    "What's the process?",
                    "How do you automate tasks?",
                    "Explain how it works"
                ],
                priority=4,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="general_getting_started",
                question="How do I get started with Fikiri Solutions?",
                answer="Getting started is easy! Sign up for a free account, connect your email and business tools, and our onboarding wizard will guide you through setting up your first automations. You can start with our templates or create custom workflows.",
                category=FAQCategory.GENERAL,
                keywords=["getting", "started", "begin", "start", "setup", "onboarding"],
                variations=[
                    "How to get started?",
                    "Where do I begin?",
                    "How to set up my account?",
                    "Getting started guide"
                ],
                priority=5,
                created_at=datetime.now()
            )
        ]
        
        # Pricing FAQs
        pricing_faqs = [
            FAQEntry(
                id="pricing_plans",
                question="What are your pricing plans?",
                answer="We offer four pricing tiers: Starter ($29/month), Growth ($79/month), Business ($199/month), and Enterprise (custom pricing). Each plan includes different limits for emails, leads, AI responses, and features. Visit our pricing page for detailed comparisons.",
                category=FAQCategory.PRICING,
                keywords=["pricing", "plans", "cost", "price", "subscription", "tiers"],
                variations=[
                    "How much does it cost?",
                    "What are your prices?",
                    "Pricing information",
                    "Cost of subscription"
                ],
                priority=5,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="pricing_free_trial",
                question="Do you offer a free trial?",
                answer="Yes! We offer a 14-day free trial with full access to all features. No credit card required to start. You can explore the platform and see how it works for your business before committing to a paid plan.",
                category=FAQCategory.PRICING,
                keywords=["free", "trial", "demo", "test", "try"],
                variations=[
                    "Is there a free trial?",
                    "Can I try it for free?",
                    "Free version available?",
                    "Demo account"
                ],
                priority=4,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="pricing_refund",
                question="What is your refund policy?",
                answer="We offer a 30-day money-back guarantee. If you're not satisfied with our service within the first 30 days, we'll provide a full refund. For annual subscriptions, refunds are prorated for unused months.",
                category=FAQCategory.PRICING,
                keywords=["refund", "money", "back", "guarantee", "cancel", "return"],
                variations=[
                    "Can I get a refund?",
                    "Money back guarantee?",
                    "Refund policy",
                    "Return policy"
                ],
                priority=3,
                created_at=datetime.now()
            )
        ]
        
        # Technical FAQs
        technical_faqs = [
            FAQEntry(
                id="technical_integrations",
                question="What integrations do you support?",
                answer="We support Gmail, Outlook, Yahoo Mail, Google Sheets, Notion, Stripe, Shopify, Microsoft Teams, Slack, and many more. We're constantly adding new integrations. If you need a specific integration, let us know!",
                category=FAQCategory.TECHNICAL,
                keywords=["integrations", "connect", "gmail", "outlook", "google", "sheets", "notion"],
                variations=[
                    "What can you integrate with?",
                    "Supported platforms",
                    "Available integrations",
                    "Can you connect to Gmail?"
                ],
                priority=4,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="technical_security",
                question="Is my data secure?",
                answer="Absolutely! We use enterprise-grade security including SSL encryption, secure data centers, regular security audits, and strict access controls. We're GDPR compliant and never sell your data to third parties.",
                category=FAQCategory.TECHNICAL,
                keywords=["security", "secure", "data", "privacy", "encryption", "gdpr"],
                variations=[
                    "How secure is my data?",
                    "Data privacy",
                    "Is it safe?",
                    "Security measures"
                ],
                priority=5,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="technical_api",
                question="Do you have an API?",
                answer="Yes! We provide a comprehensive REST API that allows you to integrate Fikiri Solutions with your existing systems. Our API includes endpoints for CRM, email automation, document processing, and analytics.",
                category=FAQCategory.TECHNICAL,
                keywords=["api", "rest", "integration", "developer", "webhook"],
                variations=[
                    "API documentation",
                    "Developer API",
                    "REST API available?",
                    "Can I integrate via API?"
                ],
                priority=3,
                created_at=datetime.now()
            )
        ]
        
        # Features FAQs
        features_faqs = [
            FAQEntry(
                id="features_ai_responses",
                question="How accurate are the AI responses?",
                answer="Our AI responses are highly accurate, with over 95% accuracy for common business scenarios. The AI learns from your business context and improves over time. You can always review and customize responses before they're sent.",
                category=FAQCategory.FEATURES,
                keywords=["ai", "responses", "accurate", "accuracy", "quality", "smart"],
                variations=[
                    "How good is the AI?",
                    "AI response quality",
                    "Are AI responses reliable?",
                    "AI accuracy rate"
                ],
                priority=4,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="features_document_processing",
                question="What document formats can you process?",
                answer="We can process PDFs, Word documents (DOCX), Excel spreadsheets (XLSX), images (JPG, PNG), and text files. Our OCR technology can extract text from images and scanned documents with high accuracy.",
                category=FAQCategory.FEATURES,
                keywords=["document", "processing", "pdf", "word", "excel", "ocr", "formats"],
                variations=[
                    "Supported document types",
                    "Can you process PDFs?",
                    "Document formats supported",
                    "OCR capabilities"
                ],
                priority=3,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="features_crm",
                question="What CRM features do you offer?",
                answer="Our CRM includes lead management, contact tracking, pipeline stages, automated follow-ups, lead scoring, activity logging, and integration with popular CRM platforms. Everything is powered by AI for intelligent insights.",
                category=FAQCategory.FEATURES,
                keywords=["crm", "leads", "contacts", "pipeline", "management", "tracking"],
                variations=[
                    "CRM capabilities",
                    "Lead management features",
                    "Contact management",
                    "CRM functionality"
                ],
                priority=4,
                created_at=datetime.now()
            )
        ]
        
        # Landscaping-specific FAQs
        landscaping_faqs = [
            FAQEntry(
                id="landscaping_services",
                question="What landscaping services do you help automate?",
                answer="We help automate quote requests, client communication, project scheduling, contract generation, follow-up sequences, and customer feedback collection for landscaping businesses. Our AI understands landscaping terminology and seasonal workflows.",
                category=FAQCategory.LANDSCAPING,
                keywords=["landscaping", "services", "quotes", "projects", "scheduling", "contracts"],
                variations=[
                    "Landscaping automation",
                    "Services for landscapers",
                    "Landscaping business features",
                    "Garden services automation"
                ],
                priority=3,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="landscaping_seasonal",
                question="Can you handle seasonal landscaping workflows?",
                answer="Yes! Our system understands seasonal landscaping patterns and can automatically adjust communications, service offerings, and scheduling based on the time of year. Perfect for managing spring cleanups, summer maintenance, and winter preparations.",
                category=FAQCategory.LANDSCAPING,
                keywords=["seasonal", "landscaping", "workflows", "spring", "summer", "winter"],
                variations=[
                    "Seasonal automation",
                    "Year-round landscaping",
                    "Seasonal workflows",
                    "Weather-based automation"
                ],
                priority=2,
                created_at=datetime.now()
            )
        ]
        
        # Support FAQs
        support_faqs = [
            FAQEntry(
                id="support_contact",
                question="How can I contact support?",
                answer="You can reach our support team via email at support@fikirisolutions.com, through our in-app chat, or by scheduling a call. Our support hours are Monday-Friday 9AM-6PM EST. Enterprise customers get priority 24/7 support.",
                category=FAQCategory.SUPPORT,
                keywords=["support", "contact", "help", "assistance", "email", "chat"],
                variations=[
                    "Contact support",
                    "Get help",
                    "Support hours",
                    "Customer service"
                ],
                priority=5,
                created_at=datetime.now()
            ),
            FAQEntry(
                id="support_training",
                question="Do you provide training?",
                answer="Yes! We offer comprehensive onboarding, video tutorials, documentation, and live training sessions. Enterprise customers get dedicated training and success management to ensure maximum value from the platform.",
                category=FAQCategory.SUPPORT,
                keywords=["training", "onboarding", "tutorials", "documentation", "learning"],
                variations=[
                    "Training available?",
                    "How to learn the system?",
                    "Onboarding process",
                    "Educational resources"
                ],
                priority=3,
                created_at=datetime.now()
            )
        ]
        
        # Combine all FAQs
        all_faqs = general_faqs + pricing_faqs + technical_faqs + features_faqs + landscaping_faqs + support_faqs
        
        for faq in all_faqs:
            faqs[faq.id] = faq
        
        return faqs
    
    def search_faqs(self, query: str, max_results: int = 5) -> FAQResponse:
        """Search FAQs with intelligent matching"""
        start_time = datetime.now()
        
        try:
            # Clean and prepare query
            cleaned_query = self._clean_query(query)
            query_keywords = self._extract_keywords(cleaned_query)
            
            # Find matches using multiple strategies
            matches = []
            
            # 1. Exact question matching
            exact_matches = self._find_exact_matches(cleaned_query)
            matches.extend(exact_matches)
            
            # 2. Variation matching
            variation_matches = self._find_variation_matches(cleaned_query)
            matches.extend(variation_matches)
            
            # 3. Keyword matching
            keyword_matches = self._find_keyword_matches(query_keywords)
            matches.extend(keyword_matches)
            
            # 4. Semantic matching (simplified)
            semantic_matches = self._find_semantic_matches(cleaned_query)
            matches.extend(semantic_matches)
            
            # Remove duplicates and sort by confidence
            unique_matches = self._deduplicate_matches(matches)
            sorted_matches = sorted(unique_matches, key=lambda m: m.confidence, reverse=True)
            
            # Limit results
            final_matches = sorted_matches[:max_results]
            
            # Determine best match
            best_match = final_matches[0] if final_matches else None
            
            # Generate suggested questions
            suggested_questions = self._generate_suggested_questions(query_keywords, final_matches)
            
            # Generate fallback response if no good matches
            fallback_response = None
            if not final_matches or (best_match and best_match.confidence < 0.4):
                fallback_response = self._generate_fallback_response(query)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return FAQResponse(
                success=True,
                matches=final_matches,
                best_match=best_match,
                suggested_questions=suggested_questions,
                fallback_response=fallback_response,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ FAQ search failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return FAQResponse(
                success=False,
                matches=[],
                best_match=None,
                suggested_questions=[],
                fallback_response=f"I'm sorry, I encountered an error while searching for answers. Please try rephrasing your question or contact support.",
                processing_time=processing_time
            )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query text"""
        # Convert to lowercase
        cleaned = query.lower().strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove punctuation except question marks
        cleaned = re.sub(r'[^\w\s?]', '', cleaned)
        
        return cleaned
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        words = query.split()
        keywords = []
        
        for word in words:
            # Skip stop words and very short words
            if word not in self.stop_words and len(word) > 2:
                keywords.append(word)
        
        return keywords
    
    def _find_exact_matches(self, query: str) -> List[FAQMatch]:
        """Find exact question matches"""
        matches = []
        
        for faq in self.faq_entries.values():
            cleaned_question = self._clean_query(faq.question)
            
            # Calculate similarity
            similarity = SequenceMatcher(None, query, cleaned_question).ratio()
            
            if similarity >= 0.9:  # 90% similarity threshold
                matches.append(FAQMatch(
                    faq_entry=faq,
                    confidence=similarity,
                    match_type="exact",
                    matched_text=faq.question,
                    explanation=f"Exact match with question: '{faq.question}'"
                ))
        
        return matches
    
    def _find_variation_matches(self, query: str) -> List[FAQMatch]:
        """Find matches in question variations"""
        matches = []
        
        for faq in self.faq_entries.values():
            for variation in faq.variations:
                cleaned_variation = self._clean_query(variation)
                similarity = SequenceMatcher(None, query, cleaned_variation).ratio()
                
                if similarity >= 0.8:  # 80% similarity threshold
                    matches.append(FAQMatch(
                        faq_entry=faq,
                        confidence=similarity * 0.95,  # Slightly lower than exact matches
                        match_type="variation",
                        matched_text=variation,
                        explanation=f"Matched variation: '{variation}'"
                    ))
        
        return matches
    
    def _find_keyword_matches(self, query_keywords: List[str]) -> List[FAQMatch]:
        """Find matches based on keyword overlap - optimized with inverted index"""
        matches = []
        query_set = set(query_keywords)
        
        # Use inverted index for O(k) lookup instead of O(n) scan where k = unique keywords
        faq_matches: Dict[str, set] = {}  # FAQ ID -> set of matched keywords
        
        for keyword in query_set:
            if keyword in self._keyword_index:
                for faq_id in self._keyword_index[keyword]:
                    if faq_id not in faq_matches:
                        faq_matches[faq_id] = set()
                    faq_matches[faq_id].add(keyword)
        
        # Calculate confidence for matched FAQs
        for faq_id, matched_keywords in faq_matches.items():
            faq = self.faq_entries[faq_id]
            overlap = matched_keywords
            
            # Calculate confidence based on overlap ratio and FAQ priority
            overlap_ratio = len(overlap) / len(query_set) if query_set else 0
            priority_boost = faq.priority * 0.05  # Small boost for higher priority
            confidence = min(overlap_ratio + priority_boost, 0.85)  # Cap at 85%
            
            if confidence >= 0.3:  # 30% threshold
                matches.append(FAQMatch(
                    faq_entry=faq,
                    confidence=confidence,
                    match_type="keyword",
                    matched_text=", ".join(overlap),
                    explanation=f"Matched keywords: {', '.join(overlap)}"
                ))
        
        return matches
    
    def _find_semantic_matches(self, query: str) -> List[FAQMatch]:
        """Find semantic matches (simplified approach)"""
        matches = []
        
        # Simple semantic patterns
        semantic_patterns = {
            "cost|price|pricing|expensive|cheap|money": ["pricing_plans", "pricing_free_trial"],
            "start|begin|setup|getting started|onboard": ["general_getting_started"],
            "secure|security|safe|privacy|data protection": ["technical_security"],
            "integrate|integration|connect|api": ["technical_integrations", "technical_api"],
            "refund|money back|cancel|return": ["pricing_refund"],
            "support|help|contact|assistance": ["support_contact"],
            "train|training|learn|tutorial": ["support_training"],
            "ai|artificial intelligence|smart|accuracy": ["features_ai_responses"],
            "document|pdf|file|process|ocr": ["features_document_processing"],
            "crm|lead|contact|customer": ["features_crm"],
            "landscaping|garden|lawn|outdoor": ["landscaping_services", "landscaping_seasonal"]
        }
        
        for pattern, faq_ids in semantic_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                for faq_id in faq_ids:
                    if faq_id in self.faq_entries:
                        faq = self.faq_entries[faq_id]
                        matches.append(FAQMatch(
                            faq_entry=faq,
                            confidence=0.6,  # Medium confidence for semantic matches
                            match_type="semantic",
                            matched_text=pattern.split("|")[0],
                            explanation=f"Semantic match for pattern: {pattern.split('|')[0]}"
                        ))
        
        return matches
    
    def _deduplicate_matches(self, matches: List[FAQMatch]) -> List[FAQMatch]:
        """Remove duplicate matches, keeping the highest confidence"""
        seen_faqs = {}
        
        for match in matches:
            faq_id = match.faq_entry.id
            if faq_id not in seen_faqs or match.confidence > seen_faqs[faq_id].confidence:
                seen_faqs[faq_id] = match
        
        return list(seen_faqs.values())
    
    def _generate_suggested_questions(self, query_keywords: List[str], matches: List[FAQMatch]) -> List[str]:
        """Generate suggested questions based on query and matches"""
        suggestions = []
        
        # Add popular questions from same categories as matches
        if matches:
            categories = set(match.faq_entry.category for match in matches)
            for category in categories:
                category_faqs = [faq for faq in self.faq_entries.values() 
                               if faq.category == category and faq.priority >= 4]
                category_faqs.sort(key=lambda f: f.priority, reverse=True)
                
                for faq in category_faqs[:2]:  # Top 2 from each category
                    if faq.question not in suggestions:
                        suggestions.append(faq.question)
        
        # Add general popular questions if no matches
        if not suggestions:
            popular_faqs = [faq for faq in self.faq_entries.values() if faq.priority >= 4]
            popular_faqs.sort(key=lambda f: f.priority, reverse=True)
            
            for faq in popular_faqs[:3]:
                suggestions.append(faq.question)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _generate_fallback_response(self, query: str) -> str:
        """Generate fallback response when no good matches found"""
        fallback_responses = [
            "I don't have a specific answer for that question, but I'd be happy to help! Could you try rephrasing your question or contact our support team?",
            "I'm not sure about that specific topic. Our support team would be better equipped to help you with this question.",
            "That's a great question! While I don't have that information readily available, please reach out to our support team for detailed assistance.",
            "I couldn't find a specific answer to your question. Would you like me to connect you with our support team, or could you try asking in a different way?"
        ]
        
        # Simple query analysis for better fallback
        if any(word in query.lower() for word in ["price", "cost", "pricing"]):
            return "For specific pricing information, please visit our pricing page or contact our sales team for a custom quote."
        elif any(word in query.lower() for word in ["technical", "api", "integration"]):
            return "For technical questions and integration details, please check our API documentation or contact our technical support team."
        elif any(word in query.lower() for word in ["help", "support", "problem"]):
            return "I'd be happy to help! Please contact our support team at support@fikirisolutions.com or use our in-app chat for immediate assistance."
        
        return fallback_responses[0]  # Default fallback
    
    def add_faq(self, question: str, answer: str, category: FAQCategory, 
                keywords: List[str], variations: List[str] = None, priority: int = 1) -> str:
        """Add a new FAQ entry"""
        try:
            faq_id = str(uuid.uuid4())
            
            faq = FAQEntry(
                id=faq_id,
                question=question,
                answer=answer,
                category=category,
                keywords=keywords,
                variations=variations or [],
                priority=priority,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.faq_entries[faq_id] = faq
            logger.info(f"✅ Added FAQ: {faq_id}")
            
            return faq_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add FAQ: {e}")
            raise
    
    def update_faq(self, faq_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing FAQ entry"""
        try:
            if faq_id not in self.faq_entries:
                return False
            
            faq = self.faq_entries[faq_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(faq, field):
                    setattr(faq, field, value)
            
            faq.updated_at = datetime.now()
            logger.info(f"✅ Updated FAQ: {faq_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update FAQ: {e}")
            return False
    
    def delete_faq(self, faq_id: str) -> bool:
        """Delete an FAQ entry"""
        try:
            if faq_id in self.faq_entries:
                del self.faq_entries[faq_id]
                logger.info(f"✅ Deleted FAQ: {faq_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete FAQ: {e}")
            return False
    
    def record_faq_usage(self, faq_id: str, helpful: bool = True):
        """Record FAQ usage and helpfulness"""
        try:
            if faq_id in self.faq_entries:
                faq = self.faq_entries[faq_id]
                faq.usage_count += 1
                
                if helpful:
                    faq.helpful_votes += 1
                else:
                    faq.unhelpful_votes += 1
                
                logger.debug(f"📊 Recorded FAQ usage: {faq_id} (helpful: {helpful})")
                
        except Exception as e:
            logger.error(f"❌ Failed to record FAQ usage: {e}")
    
    def get_faq_statistics(self) -> Dict[str, Any]:
        """Get FAQ system statistics"""
        try:
            total_faqs = len(self.faq_entries)
            categories = {}
            total_usage = 0
            total_helpful = 0
            total_unhelpful = 0
            
            for faq in self.faq_entries.values():
                # Count by category
                category = faq.category.value
                categories[category] = categories.get(category, 0) + 1
                
                # Usage statistics
                total_usage += faq.usage_count
                total_helpful += faq.helpful_votes
                total_unhelpful += faq.unhelpful_votes
            
            # Most popular FAQ
            most_popular = max(self.faq_entries.values(), key=lambda f: f.usage_count) if self.faq_entries else None
            
            # Helpfulness rate
            helpfulness_rate = (total_helpful / (total_helpful + total_unhelpful)) * 100 if (total_helpful + total_unhelpful) > 0 else 0
            
            return {
                "total_faqs": total_faqs,
                "categories": categories,
                "total_usage": total_usage,
                "helpfulness_rate": round(helpfulness_rate, 2),
                "most_popular_faq": {
                    "id": most_popular.id,
                    "question": most_popular.question,
                    "usage_count": most_popular.usage_count
                } if most_popular else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get FAQ statistics: {e}")
            return {}
    
    def export_faqs(self) -> List[Dict[str, Any]]:
        """Export all FAQs"""
        try:
            return [asdict(faq) for faq in self.faq_entries.values()]
        except Exception as e:
            logger.error(f"❌ Failed to export FAQs: {e}")
            return []
    
    def import_faqs(self, faq_data: List[Dict[str, Any]]) -> int:
        """Import FAQs from data"""
        try:
            imported_count = 0
            
            for data in faq_data:
                try:
                    # Convert data to FAQEntry
                    if 'created_at' in data and isinstance(data['created_at'], str):
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    if 'updated_at' in data and isinstance(data['updated_at'], str):
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    if 'category' in data and isinstance(data['category'], str):
                        data['category'] = FAQCategory(data['category'])
                    
                    faq = FAQEntry(**data)
                    self.faq_entries[faq.id] = faq
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to import FAQ: {e}")
                    continue
            
            logger.info(f"✅ Imported {imported_count} FAQs")
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ Failed to import FAQs: {e}")
            return 0

# Global instance
smart_faq = SmartFAQSystem()

def get_smart_faq() -> SmartFAQSystem:
    """Get the global smart FAQ instance"""
    return smart_faq
