#!/usr/bin/env python3
"""
Fikiri Solutions - AI Email Assistant
Lightweight AI-powered email responses with production enhancements.
"""

import os
import json
import logging
import asyncio
import uuid
import re
import html
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from core.ai.llm_router import LLMRouter
from core.ai.schemas import BusinessEmailAnalysisSchema
from core.ai.email_intent_taxonomy import intent_labels_for_prompt, normalize_intent
from core.client_email_config import load_client_email_config
from core.domain.schemas import normalize_extracted_contact
from email_automation.email_classification import (
    SOURCE_LEGACY_WRAPPER,
    SOURCE_MAILBOX_SYNC,
    SOURCE_MANUAL_API,
    SOURCE_V2_AI,
    SOURCE_V2_FALLBACK,
    finalize_email_analysis,
)
from email_automation.email_intent_classifier import (
    build_rule_hints,
    classify_with_fallback,
    normalize_business_analysis,
    preprocess_email_metadata,
)

logger = logging.getLogger(__name__)
EMAIL_ANALYSIS_SCHEMA_VERSION = "2026-05-email-analysis-v2"

# Contact extraction: keep local until Phase 2 (ExtractedContact in core/domain/schemas.py)
CONTACT_SCHEMA = {
    "type": "object",
    # LLMs often omit or null fields; normalize_extracted_contact handles downstream
    "required": [],
    "properties": {
        "phone": {"type": "string"},
        "company": {"type": "string"},
        "website": {"type": "string"},
        "location": {"type": "string"},
        "budget": {"type": "string"},
        "timeline": {"type": "string"},
    },
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


_HTML_TAG_RE = re.compile(
    r"<\s*(?:html|body|div|p|table|tr|td|th|span|a|img|style|meta|head|!DOCTYPE|center|font|br\s*/?)",
    re.IGNORECASE,
)


def _strip_html_for_ai(text: str) -> str:
    """Strip marketing/newsletter HTML before LLM analysis; preserve angle-bracket emails."""
    if not text:
        return ""
    t = str(text).strip()
    if "<" not in t or not _HTML_TAG_RE.search(t):
        return t
    t = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def _truncate_email_body_for_analysis(body: str, max_chars: int = 6000) -> str:
    if not body:
        return ""
    if len(body) <= max_chars:
        return body
    return body[: max(0, max_chars - 22)] + "\n...[body truncated]"


def _compact_thread_history_for_prompt(rows: List[Any], *, max_rows: int = 5, preview_chars: int = 360) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows[:max_rows]:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        bp = item.get("body_preview")
        if isinstance(bp, str) and len(bp) > preview_chars:
            item["body_preview"] = bp[: max(0, preview_chars - 3)] + "..."
        out.append(item)
    return out


class MinimalAIEmailAssistant:
    """Minimal AI email assistant with production enhancements."""
    
    def __init__(self, api_key: Optional[str] = None, services: Dict[str, Any] = None):
        """Initialize AI email assistant with enhanced features."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.services = services or {}
        test_mode = os.getenv("FIKIRI_TEST_MODE") == "1"
        
        # Initialize LLM router (required by rulepack - all LLM calls go through router)
        self.router = LLMRouter(api_key=self.api_key)
        self.enabled = self.router.client.is_enabled()
        
        # Redis client for analytics
        self.redis_client = None
        self._initialize_redis()
        
        # CRM service for auto-lead capture
        self.crm_service = None
        self._initialize_crm()
        self._last_reply_generation_mode: Optional[str] = None
        
        if self.enabled:
            logger.info("✅ AI assistant initialized with LLM router")
        else:
            if not test_mode:
                logger.warning("⚠️ AI assistant disabled - no OpenAI API key found")
    
    def _initialize_redis(self):
        """Initialize Redis client for analytics."""
        try:
            from core.redis_connection_helper import get_redis_client
            self.redis_client = get_redis_client(decode_responses=True, db=int(os.getenv('REDIS_DB', 0)))
            if self.redis_client:
                logger.info("✅ Redis initialized for AI analytics")
            else:
                logger.info("ℹ️ Redis not available for AI analytics (using database fallback)")
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
        return self.enabled and self.router.client.is_enabled()

    def _llm_context(self, **kwargs: Any) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {
            "source": "email_automation",
            "correlation_id": str(uuid.uuid4()),
        }
        ctx.update(kwargs)
        return ctx
    
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
    
    def classify_email_intent(
        self,
        email_content: str,
        subject: str = "",
        *,
        user_id: Optional[int] = None,
        sender_email: str = "",
        sender_name: str = "",
    ) -> Dict[str, Any]:
        """
        Legacy-compatible wrapper — delegates to v2 ``analyze_incoming_email``.

        Returns the full v2 analysis object (with legacy alias keys). No separate
        5-intent LLM prompt is used.
        """
        safe_email = _clean_text(sender_email) or self._extract_email_from_content(email_content) or ""
        safe_name = _clean_text(sender_name) or self._extract_name_from_content(email_content) or ""
        analysis = self.analyze_incoming_email(
            sender_email=safe_email,
            sender_name=safe_name,
            subject=subject,
            body=email_content,
            user_id=user_id,
            classification_source=SOURCE_LEGACY_WRAPPER,
        )
        if analysis.get("legacy_intent") == "lead_inquiry" and self.crm_service:
            self._auto_capture_lead(email_content, subject)
        self._track_ai_usage("classify_intent", True)
        return analysis

    def analyze_incoming_email(
        self,
        *,
        sender_email: str,
        sender_name: str,
        subject: str,
        body: str,
        thread_history: Optional[List[Dict[str, Any]]] = None,
        crm_lead_data: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        classification_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze inbound email with business context and return a structured, validated payload.
        """
        safe_subject = _clean_text(subject)
        safe_body = _strip_html_for_ai(_clean_text(body))
        safe_sender_email = _clean_text(sender_email)
        safe_sender_name = _clean_text(sender_name)
        safe_thread = thread_history if isinstance(thread_history, list) else []
        safe_crm = crm_lead_data if isinstance(crm_lead_data, dict) else {}
        client_cfg = load_client_email_config(user_id)
        safe_business = (
            business_context
            if isinstance(business_context, dict)
            else self._load_business_context(user_id=user_id)
        )

        compact_thread = _compact_thread_history_for_prompt(safe_thread)
        analysis_body = _truncate_email_body_for_analysis(safe_body)
        pre_meta = preprocess_email_metadata(
            subject=safe_subject,
            body=safe_body,
            sender_email=safe_sender_email,
            sender_name=safe_sender_name,
        )
        rule_hints = build_rule_hints(
            subject=safe_subject, body=safe_body, client_config=client_cfg
        )
        intent_labels = intent_labels_for_prompt(client_cfg.get("custom_intent_labels"))

        source = classification_source or SOURCE_V2_AI

        if not self.is_enabled():
            return self._fallback_business_analysis(
                sender_email=safe_sender_email,
                sender_name=safe_sender_name,
                subject=safe_subject,
                body=safe_body,
                crm_lead_data=safe_crm,
                user_id=user_id,
                classification_source=source if source != SOURCE_V2_AI else SOURCE_V2_FALLBACK,
            )

        prompt = f"""
        Analyze this inbound business email and return JSON only.

        BUSINESS PROFILE (client-specific):
        {json.dumps({**safe_business, **client_cfg}, default=str)}

        ALLOWED PRIMARY INTENTS (choose exactly one):
        {json.dumps(intent_labels)}

        RULE HINTS (advisory, may override if email clearly differs):
        {json.dumps(rule_hints, default=str)}

        PREPROCESS METADATA:
        {json.dumps(pre_meta, default=str)}

        SENDER:
        {json.dumps({"email": safe_sender_email, "name": safe_sender_name}, default=str)}

        EMAIL:
        {json.dumps({"subject": safe_subject, "body": analysis_body}, default=str)}

        THREAD HISTORY (latest first, may be empty):
        {json.dumps(compact_thread, default=str)}

        CRM LEAD CONTEXT (may be empty):
        {json.dumps(safe_crm, default=str)}

        Return JSON with:
        - schema_version: "{EMAIL_ANALYSIS_SCHEMA_VERSION}"
        - intent: one allowed primary intent
        - secondary_intents: array of other applicable intents
        - confidence / confidence_score: 0-1
        - lead_score, urgency_score, business_value_score: 0-100 integers
        - urgency, business_value: high|medium|low labels
        - summary: one paragraph
        - recommended_action: short action label
        - recommended_action_detail: {{next_best_action, crm_action, workflow}}
        - tone, reply_guidance: {{tone, should_auto_draft, should_auto_send}}
        - sender: {{name, email, company, phone}}
        - extracted_details: {{requested_service, budget_signal, timeline_signal, pain_points[]}}
        - crm_updates: {{stage, tags[], follow_up_needed, priority}}
        - suggested_reply: draft text
        - should_auto_send: false by default
        - needs_human_review: true if complaint, legal, payment dispute, or confidence < 0.7
        - reason_for_recommendation: brief explanation (no chain-of-thought)
        - reasoning_summary: same text as reason_for_recommendation (optional duplicate)

        Safety: never auto-send complaints, legal, or low-confidence mail.
        """
        try:
            result = self.router.process(
                input_data=prompt,
                intent="business_email_analysis",
                output_schema=BusinessEmailAnalysisSchema,
                context=self._llm_context(
                    operation="business_email_analysis",
                    correlation_id=correlation_id or str(uuid.uuid4()),
                    user_id=user_id,
                    sender_email=safe_sender_email,
                    subject=safe_subject,
                ),
            )
            if result.get("success") and result.get("validated"):
                try:
                    parsed = json.loads(result.get("content") or "{}")
                    normalized = normalize_business_analysis(
                        parsed,
                        rule_hints=rule_hints,
                        sender_email=safe_sender_email,
                        sender_name=safe_sender_name,
                        client_config=client_cfg,
                    )
                    finalized = finalize_email_analysis(
                        normalized, classification_source=source
                    )
                    self._log_classification_result(
                        user_id=user_id,
                        correlation_id=correlation_id,
                        analysis=finalized,
                    )
                    return finalized
                except json.JSONDecodeError:
                    logger.warning("Business email analysis JSON parse failed; using fallback")
            elif result.get("success"):
                logger.warning(
                    "Business email analysis schema validation failed (trace_id=%s); using fallback",
                    result.get("trace_id"),
                )
        except Exception as e:
            logger.error("Business email analysis failed: %s", e)

        return self._fallback_business_analysis(
            sender_email=safe_sender_email,
            sender_name=safe_sender_name,
            subject=safe_subject,
            body=safe_body,
            crm_lead_data=safe_crm,
            user_id=user_id,
            classification_source=SOURCE_V2_FALLBACK,
        )

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
    
    def _log_reply_generation(
        self,
        mode: str,
        *,
        user_id: Optional[int] = None,
        intent: Optional[str] = None,
        llm_called: bool = False,
    ) -> None:
        try:
            logger.info(
                "reply_generation.completed",
                extra={
                    "event": "reply_generation.completed",
                    "service": "email",
                    "severity": "INFO",
                    "user_id": user_id,
                    "metadata": {
                        "reply_generation_mode": mode,
                        "llm_called": llm_called,
                        "intent": intent,
                    },
                },
            )
        except Exception:
            pass

    def generate_response(
        self,
        email_content: str,
        sender_name: str,
        subject: str,
        intent: str = "general",
        *,
        analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """Generate AI-powered email response using v2 analysis when provided."""
        if not self.is_enabled():
            self._last_reply_generation_mode = "assistant_disabled"
            self._log_reply_generation(
                "assistant_disabled",
                user_id=user_id,
                intent=intent,
                llm_called=False,
            )
            return self._fallback_response(sender_name, subject)

        suggested = (analysis or {}).get("suggested_reply") if analysis else None
        if suggested and str(suggested).strip():
            self._last_reply_generation_mode = "reused_suggested_reply"
            self._log_reply_generation(
                "reused_suggested_reply",
                user_id=user_id,
                intent=(analysis or {}).get("intent"),
                llm_called=False,
            )
            return str(suggested).strip()

        try:
            business_context = self._load_business_context(user_id=user_id)
            client_cfg = load_client_email_config(user_id)

            v2_intent = intent
            tone = business_context.get("tone", "professional_warm")
            requested_service = ""
            pain_points: List[str] = []
            next_action = "draft_reply"
            urgency = "medium"

            if analysis:
                v2_intent = analysis.get("intent") or intent
                tone = (
                    (analysis.get("reply_guidance") or {}).get("tone")
                    or analysis.get("tone")
                    or tone
                )
                extracted = analysis.get("extracted_details") or {}
                requested_service = extracted.get("requested_service") or ""
                pain_points = extracted.get("pain_points") or []
                rad = analysis.get("recommended_action_detail") or {}
                next_action = rad.get("next_best_action") or analysis.get("recommended_action") or next_action
                urgency = analysis.get("urgency") or urgency

            prompt = f"""
            You are a professional email assistant for {business_context['company_name']}.

            Business / client config:
            {json.dumps({**business_context, **client_cfg}, default=str)}

            Classification (v2):
            - Intent: {v2_intent}
            - Urgency: {urgency}
            - Requested service: {requested_service or 'not specified'}
            - Pain points: {json.dumps(pain_points, default=str)}
            - Next best action: {next_action}
            - Reply tone: {tone}

            Email:
            - From: {sender_name}
            - Subject: {subject}
            - Content: {email_content[:1200]}

            Write a concise professional reply (2-3 short paragraphs). No signature block.
            """
            
            # Use LLM router (required by rulepack)
            result = self.router.process(
                input_data=prompt,
                intent='email_reply',
                context=self._llm_context(
                    operation='email_reply',
                    sender=sender_name,
                    subject=subject,
                    intent_label=v2_intent,
                    user_id=user_id,
                ),
            )
            
            mode = "llm_with_analysis_context" if analysis else "llm_no_analysis"
            if result['success']:
                self._last_reply_generation_mode = mode
                self._track_ai_usage("generate_response", True, result.get('tokens_used', 0))
                self._log_reply_generation(
                    mode,
                    user_id=user_id,
                    intent=v2_intent,
                    llm_called=True,
                )
                logger.info("AI response generated for %s via LLM router", sender_name)
                return result['content']
            logger.error("AI response generation failed: %s", result.get('error'))
            self._track_ai_usage("generate_response", False)
            self._last_reply_generation_mode = "template_fallback"
            self._log_reply_generation(
                "template_fallback",
                user_id=user_id,
                intent=v2_intent,
                llm_called=False,
            )
            return self._fallback_response(sender_name, subject)

        except Exception as e:
            logger.error("AI response generation failed: %s", e)
            self._track_ai_usage("generate_response", False)
            self._last_reply_generation_mode = "template_fallback"
            self._log_reply_generation(
                "template_fallback",
                user_id=user_id,
                intent=intent,
                llm_called=False,
            )
            return self._fallback_response(sender_name, subject)

    def generate_reply_with_metadata(
        self,
        sender_name: str,
        subject: str,
        email_content: str = "",
        email_body: str = "",
        *,
        analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> tuple:
        """
        Generate reply text and return (reply, reply_generation_mode).

        Does not call classify_email_intent; uses ``analysis`` from mailbox sync when set.
        """
        combined = "\n".join([part for part in [email_content, email_body] if part])
        intent_label = (analysis or {}).get("intent") or "email_reply"
        text = self.generate_response(
            combined,
            sender_name,
            subject,
            intent=intent_label,
            analysis=analysis,
            user_id=user_id,
        )
        mode = self._last_reply_generation_mode or (
            "reused_suggested_reply"
            if analysis and (analysis.get("suggested_reply") or "").strip()
            else "llm_no_analysis"
        )
        return text, mode

    def generate_reply(
        self,
        sender_name: str,
        subject: str,
        email_content: str = "",
        email_body: str = "",
        *,
        analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """Generate a reply for email automation actions."""
        text, _mode = self.generate_reply_with_metadata(
            sender_name,
            subject,
            email_content=email_content,
            email_body=email_body,
            analysis=analysis,
            user_id=user_id,
        )
        return text
    
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
            
            # Use LLM router (required by rulepack)
            result = self.router.process(
                input_data=prompt,
                intent='extraction',
                output_schema=CONTACT_SCHEMA,
                context={'operation': 'contact_extraction'}
            )
            
            if result['success'] and result.get('validated'):
                try:
                    parsed_result = json.loads(result['content'])
                    # Track usage
                    self._track_ai_usage("extract_contact", True, result.get('tokens_used', 0))
                    logger.info(f"✅ Contact info extracted via LLM router")
                    return normalize_extracted_contact(parsed_result)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse contact info as JSON, using fallback")
                    return normalize_extracted_contact(self._fallback_contact_extraction(email_content))
            else:
                err_msg = result.get('error') or 'Schema validation failed or empty error'
                logger.error(f"❌ Contact extraction failed: {err_msg}")
                self._track_ai_usage("extract_contact", False)
                return normalize_extracted_contact(self._fallback_contact_extraction(email_content))

        except Exception as e:
            logger.error(f"❌ Contact extraction failed: {e}")
            self._track_ai_usage("extract_contact", False)
            return normalize_extracted_contact(self._fallback_contact_extraction(email_content))

    def summarize_email(self, email_content: str, subject: str = "") -> str:
        """Summarize a single email with enhanced tracking."""
        if not self.is_enabled():
            return self._fallback_summary(email_content)

        try:
            prompt = f"""
            Summarize this email in 2-3 concise sentences:

            Subject: {subject}
            Content: {email_content[:800]}

            Focus on the main request, key details, and any next steps.
            """

            result = self.router.process(
                input_data=prompt,
                intent='summarization',
                context=self._llm_context(operation='email_summary', subject=subject),
            )

            if result['success']:
                self._track_ai_usage("summarize_email", True, result.get('tokens_used', 0))
                logger.info("✅ Email summarized via LLM router")
                return result['content']

            logger.error(f"❌ Email summarization failed: {result.get('error')}")
            self._track_ai_usage("summarize_email", False)
            return self._fallback_summary(email_content)

        except Exception as e:
            logger.error(f"❌ Email summarization failed: {e}")
            self._track_ai_usage("summarize_email", False)
            return self._fallback_summary(email_content)
    
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
            
            # Use LLM router (required by rulepack)
            result = self.router.process(
                input_data=prompt,
                intent='summarization',
                context=self._llm_context(operation='thread_summarization', email_count=len(emails)),
            )
            
            if result['success']:
                # Track usage
                self._track_ai_usage("summarize_thread", True, result.get('tokens_used', 0))
                logger.info(f"✅ Email thread summarized via LLM router")
                return result['content']
            else:
                logger.error(f"❌ Thread summarization failed: {result.get('error')}")
                self._track_ai_usage("summarize_thread", False)
                return "Email thread summary not available"
            
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
            "llm_provider": "openai" if self.router.client.is_enabled() else "missing",
            "redis_available": self.redis_client is not None,
            "crm_integration": self.crm_service is not None,
            "total_operations": 0,
            "successful_operations": 0,
            "total_tokens": 0
        }
        
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
                    except Exception as parse_error:
                        logger.debug("Failed to parse AI usage record: %s", parse_error)
                        continue
                
                stats["successful_operations"] = successful_count
                stats["total_tokens"] = total_tokens
                
            except Exception as e:
                logger.warning(f"Failed to get AI stats from Redis: {e}")
        
        return stats
    
    def _load_business_context(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Load business context from client config (per-user) or file defaults."""
        cfg = load_client_email_config(user_id)
        services = cfg.get("services_offered") or cfg.get("services") or []
        if isinstance(services, list):
            services_str = ", ".join(str(s) for s in services if s)
        else:
            services_str = str(services)
        return {
            "company_name": cfg.get("company_name") or "Fikiri Solutions",
            "services": services_str or "Business services",
            "tone": cfg.get("preferred_tone") or "professional and helpful",
            "business_type": cfg.get("business_type") or "",
            "target_customer_types": cfg.get("target_customer_types") or [],
        }

    def _log_classification_result(
        self,
        *,
        user_id: Optional[int],
        correlation_id: Optional[str],
        analysis: Dict[str, Any],
    ) -> None:
        try:
            logger.info(
                "email.classification.routed",
                extra={
                    "event": "email.classification.routed",
                    "service": "email",
                    "severity": "INFO",
                    "user_id": user_id,
                    "metadata": {
                        "correlation_id": correlation_id,
                        "intent": analysis.get("intent"),
                        "legacy_intent": analysis.get("legacy_intent"),
                        "confidence_score": analysis.get("confidence_score"),
                        "lead_score": analysis.get("lead_score"),
                        "urgency_score": analysis.get("urgency_score"),
                        "recommended_action_type": analysis.get("recommended_action_type"),
                        "needs_human_review": analysis.get("needs_human_review"),
                        "workflow": (analysis.get("recommended_action_detail") or {}).get("workflow"),
                        "classification_source": analysis.get("classification_source"),
                    },
                },
            )
        except Exception:
            pass
    
    def _fallback_classification(
        self,
        email_content: str,
        subject: str,
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Deprecated — delegates to v2 heuristic classifier."""
        return classify_with_fallback(
            subject=subject,
            body=email_content,
            user_id=user_id,
        )
    
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
        
        return normalize_extracted_contact({
            "phone": phone_match.group(0) if phone_match else None,
            "company": None,
            "website": website_match.group(0) if website_match else None,
            "location": None,
            "budget": None,
            "timeline": None
        })

    def _fallback_summary(self, email_content: str) -> str:
        """Fallback summary when AI is not available."""
        if not email_content:
            return ""
        return email_content[:200] + "..." if len(email_content) > 200 else email_content

    def _normalize_business_analysis(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """Delegate to shared classifier normalizer (backward-compatible wrapper)."""
        return normalize_business_analysis(data if isinstance(data, dict) else {}, **kwargs)

    def _fallback_business_analysis(
        self,
        *,
        sender_email: str = "",
        sender_name: str = "",
        subject: str = "",
        body: str = "",
        crm_lead_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        classification_source: str = SOURCE_V2_FALLBACK,
    ) -> Dict[str, Any]:
        result = classify_with_fallback(
            subject=subject,
            body=body,
            sender_email=sender_email,
            sender_name=sender_name,
            user_id=user_id,
        )
        if crm_lead_data and crm_lead_data.get("id"):
            tags = result.get("crm_updates", {}).get("tags") or []
            if "existing_lead" not in tags:
                tags.append("existing_lead")
                result["crm_updates"]["tags"] = tags
        if not result.get("suggested_reply"):
            result["suggested_reply"] = self._fallback_response(
                sender_name or "there", subject or "your message"
            )
        return finalize_email_analysis(result, classification_source=classification_source)
    
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
