"""
Fikiri Solutions - Responses API Migration Module
Implements industry-specific AI automation with structured workflows
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from openai import OpenAI

@dataclass
class IndustryPrompt:
    """Industry-specific prompt configuration"""
    industry: str
    prompt_id: str
    tone: str
    focus_areas: List[str]
    tools: List[str]
    pricing_tier: str

@dataclass
class UsageMetrics:
    """Usage tracking for pricing tiers"""
    client_id: str
    responses_count: int
    tool_calls_count: int
    tokens_used: int
    date: datetime
    industry: str

class ResponsesAPIManager:
    """Manages Responses API with industry-specific prompts and workflows"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.industry_prompts = self._load_industry_prompts()
        self.usage_metrics = []
        
    def _load_industry_prompts(self) -> Dict[str, IndustryPrompt]:
        """Load industry-specific prompt configurations"""
        return {
            'landscaping': IndustryPrompt(
                industry='landscaping',
                prompt_id='pmpt_landscaping_v1',  # You'll create this
                tone='professional, concise, scheduling-focused',
                focus_areas=['appointment scheduling', 'service quotes', 'follow-up reminders'],
                tools=['crm.add_lead', 'calendar.schedule', 'email.send_quote'],
                pricing_tier='professional'
            ),
            'restaurant': IndustryPrompt(
                industry='restaurant',
                prompt_id='pmpt_restaurant_v1',  # You'll create this
                tone='warm, conversational, upsell-focused',
                focus_areas=['reservation management', 'special promotions', 'customer feedback'],
                tools=['crm.add_customer', 'reservations.book', 'email.send_promo'],
                pricing_tier='premium'
            ),
            'contractor': IndustryPrompt(
                industry='contractor',
                prompt_id='pmpt_contractor_v1',  # You'll create this
                tone='technical, detailed, project-focused',
                focus_areas=['project estimates', 'material quotes', 'timeline planning'],
                tools=['crm.add_project', 'estimates.generate', 'email.send_proposal'],
                pricing_tier='enterprise'
            )
        }
    
    def create_industry_prompt(self, industry: str, client_id: str) -> str:
        """Create a new industry-specific prompt in OpenAI dashboard"""
        prompt_config = self.industry_prompts.get(industry)
        if not prompt_config:
            raise ValueError(f"Unknown industry: {industry}")
        
        # This would be done in OpenAI dashboard, but we'll simulate the structure
        prompt_spec = {
            "name": f"Fikiri Solutions - {industry.title()} Assistant",
            "model": "gpt-4.1",
            "instructions": f"""You are Fikiri Solutions AI Assistant specialized for {industry} businesses.

Tone: {prompt_config.tone}
Focus Areas: {', '.join(prompt_config.focus_areas)}

Guidelines:
- Be helpful, professional, and industry-specific
- Focus on {prompt_config.focus_areas[0]} as primary concern
- Use available tools to execute structured workflows
- Always suggest concrete next steps
- Maintain {prompt_config.tone} communication style

Available Tools: {', '.join(prompt_config.tools)}
""",
            "tools": self._get_tool_definitions(prompt_config.tools),
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        return f"pmpt_{industry}_{client_id}_v1"
    
    def _get_tool_definitions(self, tools: List[str]) -> List[Dict]:
        """Define available tools for each industry"""
        tool_definitions = {
            'crm.add_lead': {
                "type": "function",
                "function": {
                    "name": "add_lead",
                    "description": "Add a new lead to CRM system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Lead name"},
                            "email": {"type": "string", "description": "Lead email"},
                            "phone": {"type": "string", "description": "Lead phone"},
                            "company": {"type": "string", "description": "Company name"},
                            "source": {"type": "string", "description": "Lead source"},
                            "notes": {"type": "string", "description": "Additional notes"}
                        },
                        "required": ["name", "email"]
                    }
                }
            },
            'calendar.schedule': {
                "type": "function",
                "function": {
                    "name": "schedule_appointment",
                    "description": "Schedule an appointment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Appointment date"},
                            "time": {"type": "string", "description": "Appointment time"},
                            "duration": {"type": "integer", "description": "Duration in minutes"},
                            "client_name": {"type": "string", "description": "Client name"},
                            "service_type": {"type": "string", "description": "Type of service"}
                        },
                        "required": ["date", "time", "client_name"]
                    }
                }
            },
            'email.send_quote': {
                "type": "function",
                "function": {
                    "name": "send_quote",
                    "description": "Send service quote to client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_email": {"type": "string", "description": "Client email"},
                            "service_type": {"type": "string", "description": "Service type"},
                            "price": {"type": "number", "description": "Quote price"},
                            "valid_until": {"type": "string", "description": "Quote expiration date"}
                        },
                        "required": ["client_email", "service_type", "price"]
                    }
                }
            }
        }
        
        return [tool_definitions[tool] for tool in tools if tool in tool_definitions]
    
    def process_industry_request(self, industry: str, client_id: str, user_message: str) -> Dict[str, Any]:
        """Process request using industry-specific prompt and tools"""
        try:
            prompt_config = self.industry_prompts.get(industry)
            if not prompt_config:
                return self._fallback_response(user_message)
            
            # Create conversation with industry context
            conversation = self.client.conversations.create(
                items=[{"role": "user", "content": user_message}],
                metadata={
                    "client_id": client_id,
                    "industry": industry,
                    "pricing_tier": prompt_config.pricing_tier
                }
            )
            
            # Generate response using industry-specific prompt
            response = self.client.responses.create(
                prompt={"id": prompt_config.prompt_id, "version": "1"},
                input=[{"role": "user", "content": user_message}],
                conversation=conversation.id,
                tools=self._get_tool_definitions(prompt_config.tools),
                tool_choice="auto"
            )
            
            # Track usage metrics
            self._track_usage(client_id, industry, response)
            
            return {
                "response": response.output[0].content[0].text,
                "conversation_id": conversation.id,
                "industry": industry,
                "tools_used": self._extract_tool_calls(response),
                "usage_metrics": self._get_usage_summary(client_id),
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Industry request failed: {e}")
            return self._fallback_response(user_message)
    
    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from response for analytics"""
        tool_calls = []
        for item in response.output:
            if item.type == "tool_call":
                tool_calls.append({
                    "tool": item.function.name,
                    "arguments": item.function.arguments,
                    "status": item.status
                })
        return tool_calls
    
    def _track_usage(self, client_id: str, industry: str, response):
        """Track usage metrics for pricing tiers"""
        metrics = UsageMetrics(
            client_id=client_id,
            responses_count=1,
            tool_calls_count=len(self._extract_tool_calls(response)),
            tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else 0,
            date=datetime.now(),
            industry=industry
        )
        self.usage_metrics.append(metrics)
    
    def _get_usage_summary(self, client_id: str) -> Dict[str, Any]:
        """Get usage summary for client pricing tier"""
        client_metrics = [m for m in self.usage_metrics if m.client_id == client_id]
        
        if not client_metrics:
            return {"tier": "starter", "responses": 0, "tool_calls": 0, "tokens": 0}
        
        total_responses = sum(m.responses_count for m in client_metrics)
        total_tool_calls = sum(m.tool_calls_count for m in client_metrics)
        total_tokens = sum(m.tokens_used for m in client_metrics)
        
        # Determine pricing tier based on usage
        if total_responses < 100:
            tier = "starter"
        elif total_responses < 1000:
            tier = "professional"
        elif total_responses < 5000:
            tier = "premium"
        else:
            tier = "enterprise"
        
        return {
            "tier": tier,
            "responses": total_responses,
            "tool_calls": total_tool_calls,
            "tokens": total_tokens,
            "monthly_cost": self._calculate_monthly_cost(tier, total_responses)
        }
    
    def _calculate_monthly_cost(self, tier: str, responses: int) -> float:
        """Calculate monthly cost based on tier and usage"""
        pricing = {
            "starter": 29.00,
            "professional": 99.00,
            "premium": 249.00,
            "enterprise": 499.00
        }
        return pricing.get(tier, 29.00)
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback to ChatGPT 3.5 Turbo if industry prompt fails"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Fikiri Solutions AI Assistant. Be helpful and professional."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return {
                "response": response.choices[0].message.content,
                "fallback": True,
                "success": True
            }
        except Exception as e:
            return {
                "response": "I'm experiencing technical difficulties. Please try again later.",
                "error": str(e),
                "success": False
            }
    
    def get_client_analytics(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for client reporting"""
        client_metrics = [m for m in self.usage_metrics if m.client_id == client_id]
        
        if not client_metrics:
            return {"error": "No data found for client"}
        
        # Group by industry
        industry_breakdown = {}
        for metric in client_metrics:
            industry = metric.industry
            if industry not in industry_breakdown:
                industry_breakdown[industry] = {
                    "responses": 0,
                    "tool_calls": 0,
                    "tokens": 0
                }
            industry_breakdown[industry]["responses"] += metric.responses_count
            industry_breakdown[industry]["tool_calls"] += metric.tool_calls_count
            industry_breakdown[industry]["tokens"] += metric.tokens_used
        
        return {
            "client_id": client_id,
            "total_responses": sum(m.responses_count for m in client_metrics),
            "total_tool_calls": sum(m.tool_calls_count for m in client_metrics),
            "total_tokens": sum(m.tokens_used for m in client_metrics),
            "industry_breakdown": industry_breakdown,
            "current_tier": self._get_usage_summary(client_id)["tier"],
            "monthly_cost": self._get_usage_summary(client_id)["monthly_cost"]
        }

# Global instance
responses_manager = ResponsesAPIManager()
