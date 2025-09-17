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
        # Initialize OpenAI client only if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("⚠️  OpenAI API key not found - AI features will be disabled")
        
        self.industry_prompts = self._load_industry_prompts()
        self.usage_metrics = []
        
    def _load_industry_prompts(self) -> Dict[str, IndustryPrompt]:
        """Load industry-specific prompt configurations"""
        return {
            # Food & Beverage
            'restaurant': IndustryPrompt(
                industry='restaurant',
                prompt_id='pmpt_restaurant_v1',
                tone='warm, conversational, upsell-focused',
                focus_areas=['reservation management', 'special promotions', 'customer feedback', 'menu recommendations'],
                tools=['crm.add_customer', 'reservations.book', 'email.send_promo', 'menu.suggest'],
                pricing_tier='premium'
            ),
            'cafe': IndustryPrompt(
                industry='cafe',
                prompt_id='pmpt_cafe_v1',
                tone='friendly, casual, community-focused',
                focus_areas=['loyalty programs', 'daily specials', 'event hosting', 'catering orders'],
                tools=['crm.add_customer', 'loyalty.track', 'catering.book', 'events.schedule'],
                pricing_tier='professional'
            ),
            'food_truck': IndustryPrompt(
                industry='food_truck',
                prompt_id='pmpt_food_truck_v1',
                tone='energetic, mobile-focused, location-aware',
                focus_areas=['location updates', 'daily menus', 'event bookings', 'social media integration'],
                tools=['location.update', 'menu.publish', 'events.book', 'social.post'],
                pricing_tier='professional'
            ),
            
            # Real Estate
            'real_estate': IndustryPrompt(
                industry='real_estate',
                prompt_id='pmpt_real_estate_v1',
                tone='professional, trustworthy, market-savvy',
                focus_areas=['property listings', 'client consultations', 'market analysis', 'transaction management'],
                tools=['crm.add_client', 'properties.list', 'appointments.schedule', 'contracts.track'],
                pricing_tier='enterprise'
            ),
            'property_management': IndustryPrompt(
                industry='property_management',
                prompt_id='pmpt_property_mgmt_v1',
                tone='efficient, maintenance-focused, tenant-oriented',
                focus_areas=['maintenance requests', 'tenant communication', 'rent collection', 'property inspections'],
                tools=['maintenance.request', 'tenants.notify', 'rent.collect', 'inspections.schedule'],
                pricing_tier='premium'
            ),
            
            # Medical & Healthcare
            'medical_practice': IndustryPrompt(
                industry='medical_practice',
                prompt_id='pmpt_medical_v1',
                tone='professional, empathetic, compliance-focused',
                focus_areas=['appointment scheduling', 'patient reminders', 'HIPAA compliance', 'insurance verification'],
                tools=['appointments.schedule', 'patients.remind', 'compliance.check', 'insurance.verify'],
                pricing_tier='enterprise'
            ),
            'dental_clinic': IndustryPrompt(
                industry='dental_clinic',
                prompt_id='pmpt_dental_v1',
                tone='caring, professional, preventive-focused',
                focus_areas=['appointment scheduling', 'treatment plans', 'insurance claims', 'patient education'],
                tools=['appointments.schedule', 'treatments.plan', 'insurance.process', 'education.send'],
                pricing_tier='premium'
            ),
            'veterinary': IndustryPrompt(
                industry='veterinary',
                prompt_id='pmpt_veterinary_v1',
                tone='caring, compassionate, pet-focused',
                focus_areas=['appointment scheduling', 'vaccination reminders', 'emergency protocols', 'pet records'],
                tools=['appointments.schedule', 'vaccines.remind', 'emergency.alert', 'records.update'],
                pricing_tier='professional'
            ),
            
            # Labor & Trades
            'landscaping': IndustryPrompt(
                industry='landscaping',
                prompt_id='pmpt_landscaping_v1',
                tone='professional, concise, scheduling-focused',
                focus_areas=['appointment scheduling', 'service quotes', 'follow-up reminders', 'seasonal planning'],
                tools=['crm.add_lead', 'calendar.schedule', 'email.send_quote', 'seasonal.plan'],
                pricing_tier='professional'
            ),
            'painting': IndustryPrompt(
                industry='painting',
                prompt_id='pmpt_painting_v1',
                tone='creative, detail-oriented, color-focused',
                focus_areas=['color consultations', 'project estimates', 'weather scheduling', 'material calculations'],
                tools=['consultations.schedule', 'estimates.generate', 'weather.check', 'materials.calculate'],
                pricing_tier='professional'
            ),
            'carpenter': IndustryPrompt(
                industry='carpenter',
                prompt_id='pmpt_carpenter_v1',
                tone='skilled, precision-focused, craftsmanship-oriented',
                focus_areas=['custom designs', 'project timelines', 'material sourcing', 'quality assurance'],
                tools=['designs.create', 'timelines.plan', 'materials.source', 'quality.check'],
                pricing_tier='professional'
            ),
            'drywall': IndustryPrompt(
                industry='drywall',
                prompt_id='pmpt_drywall_v1',
                tone='efficient, repair-focused, texture-oriented',
                focus_areas=['repair estimates', 'texture matching', 'project scheduling', 'cleanup coordination'],
                tools=['repairs.estimate', 'textures.match', 'scheduling.coordinate', 'cleanup.schedule'],
                pricing_tier='professional'
            ),
            'plumber': IndustryPrompt(
                industry='plumber',
                prompt_id='pmpt_plumber_v1',
                tone='urgent, problem-solving, emergency-ready',
                focus_areas=['emergency calls', 'repair estimates', 'preventive maintenance', 'compliance checks'],
                tools=['emergency.dispatch', 'repairs.estimate', 'maintenance.schedule', 'compliance.verify'],
                pricing_tier='professional'
            ),
            'roofer': IndustryPrompt(
                industry='roofer',
                prompt_id='pmpt_roofer_v1',
                tone='weather-aware, safety-focused, inspection-oriented',
                focus_areas=['weather scheduling', 'safety protocols', 'inspection reports', 'insurance claims'],
                tools=['weather.monitor', 'safety.check', 'inspections.report', 'insurance.process'],
                pricing_tier='professional'
            ),
            
            # Transportation & Services
            'car_rental': IndustryPrompt(
                industry='car_rental',
                prompt_id='pmpt_car_rental_v1',
                tone='efficient, service-oriented, availability-focused',
                focus_areas=['reservation management', 'vehicle availability', 'customer service', 'fleet maintenance'],
                tools=['reservations.manage', 'vehicles.track', 'customers.service', 'maintenance.schedule'],
                pricing_tier='premium'
            ),
            'ride_share': IndustryPrompt(
                industry='ride_share',
                prompt_id='pmpt_ride_share_v1',
                tone='dynamic, location-aware, driver-focused',
                focus_areas=['driver support', 'route optimization', 'earnings tracking', 'customer service'],
                tools=['drivers.support', 'routes.optimize', 'earnings.track', 'service.handle'],
                pricing_tier='premium'
            ),
            
            # Creative & Marketing
            'content_creation': IndustryPrompt(
                industry='content_creation',
                prompt_id='pmpt_content_v1',
                tone='creative, trend-aware, engagement-focused',
                focus_areas=['content planning', 'social media strategy', 'brand consistency', 'audience engagement'],
                tools=['content.plan', 'social.schedule', 'brands.manage', 'engagement.track'],
                pricing_tier='premium'
            ),
            'marketing_agency': IndustryPrompt(
                industry='marketing_agency',
                prompt_id='pmpt_marketing_v1',
                tone='strategic, data-driven, results-focused',
                focus_areas=['campaign management', 'client reporting', 'ROI tracking', 'lead generation'],
                tools=['campaigns.manage', 'reports.generate', 'roi.track', 'leads.generate'],
                pricing_tier='enterprise'
            ),
            'photography': IndustryPrompt(
                industry='photography',
                prompt_id='pmpt_photography_v1',
                tone='artistic, client-focused, session-oriented',
                focus_areas=['session booking', 'portfolio management', 'client galleries', 'editing workflows'],
                tools=['sessions.book', 'portfolios.manage', 'galleries.share', 'editing.track'],
                pricing_tier='professional'
            ),
            
            # Professional Services
            'tax_services': IndustryPrompt(
                industry='tax_services',
                prompt_id='pmpt_tax_v1',
                tone='precise, deadline-focused, compliance-oriented',
                focus_areas=['tax preparation', 'deadline management', 'client documentation', 'IRS compliance'],
                tools=['taxes.prepare', 'deadlines.track', 'documents.collect', 'compliance.verify'],
                pricing_tier='enterprise'
            ),
            'accounting': IndustryPrompt(
                industry='accounting',
                prompt_id='pmpt_accounting_v1',
                tone='analytical, detail-oriented, financial-focused',
                focus_areas=['bookkeeping', 'financial reporting', 'audit preparation', 'client consultation'],
                tools=['books.maintain', 'reports.generate', 'audits.prepare', 'consultations.schedule'],
                pricing_tier='enterprise'
            ),
            'legal_services': IndustryPrompt(
                industry='legal_services',
                prompt_id='pmpt_legal_v1',
                tone='professional, confidential, case-focused',
                focus_areas=['case management', 'client intake', 'document preparation', 'court scheduling'],
                tools=['cases.manage', 'intake.process', 'documents.prepare', 'court.schedule'],
                pricing_tier='enterprise'
            ),
            
            # Retail & E-commerce
            'retail_store': IndustryPrompt(
                industry='retail_store',
                prompt_id='pmpt_retail_v1',
                tone='customer-focused, inventory-aware, sales-oriented',
                focus_areas=['inventory management', 'customer service', 'sales tracking', 'promotional campaigns'],
                tools=['inventory.track', 'customers.service', 'sales.analyze', 'promotions.run'],
                pricing_tier='professional'
            ),
            'ecommerce': IndustryPrompt(
                industry='ecommerce',
                prompt_id='pmpt_ecommerce_v1',
                tone='conversion-focused, data-driven, customer-centric',
                focus_areas=['order management', 'customer support', 'inventory sync', 'marketing automation'],
                tools=['orders.process', 'support.handle', 'inventory.sync', 'marketing.automate'],
                pricing_tier='premium'
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
            # CRM & Customer Management
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
            'crm.add_customer': {
                "type": "function",
                "function": {
                    "name": "add_customer",
                    "description": "Add a new customer to CRM system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Customer name"},
                            "email": {"type": "string", "description": "Customer email"},
                            "phone": {"type": "string", "description": "Customer phone"},
                            "preferences": {"type": "string", "description": "Customer preferences"},
                            "notes": {"type": "string", "description": "Additional notes"}
                        },
                        "required": ["name", "email"]
                    }
                }
            },
            'crm.add_client': {
                "type": "function",
                "function": {
                    "name": "add_client",
                    "description": "Add a new client to CRM system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Client name"},
                            "email": {"type": "string", "description": "Client email"},
                            "phone": {"type": "string", "description": "Client phone"},
                            "business_type": {"type": "string", "description": "Type of business"},
                            "notes": {"type": "string", "description": "Additional notes"}
                        },
                        "required": ["name", "email"]
                    }
                }
            },
            
            # Scheduling & Appointments
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
            'appointments.schedule': {
                "type": "function",
                "function": {
                    "name": "schedule_appointment",
                    "description": "Schedule a medical appointment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_name": {"type": "string", "description": "Patient name"},
                            "date": {"type": "string", "description": "Appointment date"},
                            "time": {"type": "string", "description": "Appointment time"},
                            "appointment_type": {"type": "string", "description": "Type of appointment"},
                            "provider": {"type": "string", "description": "Healthcare provider"}
                        },
                        "required": ["patient_name", "date", "time"]
                    }
                }
            },
            'reservations.book': {
                "type": "function",
                "function": {
                    "name": "book_reservation",
                    "description": "Book a restaurant reservation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string", "description": "Customer name"},
                            "date": {"type": "string", "description": "Reservation date"},
                            "time": {"type": "string", "description": "Reservation time"},
                            "party_size": {"type": "integer", "description": "Number of guests"},
                            "special_requests": {"type": "string", "description": "Special requests"}
                        },
                        "required": ["customer_name", "date", "time", "party_size"]
                    }
                }
            },
            
            # Email & Communication
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
            },
            'email.send_promo': {
                "type": "function",
                "function": {
                    "name": "send_promotion",
                    "description": "Send promotional email to customers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_email": {"type": "string", "description": "Customer email"},
                            "promotion_type": {"type": "string", "description": "Type of promotion"},
                            "discount": {"type": "string", "description": "Discount amount"},
                            "expiry_date": {"type": "string", "description": "Promotion expiry date"}
                        },
                        "required": ["customer_email", "promotion_type"]
                    }
                }
            },
            
            # Industry-Specific Tools
            'menu.suggest': {
                "type": "function",
                "function": {
                    "name": "suggest_menu_item",
                    "description": "Suggest menu items based on preferences",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_preferences": {"type": "string", "description": "Customer preferences"},
                            "dietary_restrictions": {"type": "string", "description": "Dietary restrictions"},
                            "price_range": {"type": "string", "description": "Price range"}
                        },
                        "required": ["customer_preferences"]
                    }
                }
            },
            'loyalty.track': {
                "type": "function",
                "function": {
                    "name": "track_loyalty_points",
                    "description": "Track customer loyalty points",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Customer ID"},
                            "points_earned": {"type": "integer", "description": "Points earned"},
                            "transaction_amount": {"type": "number", "description": "Transaction amount"}
                        },
                        "required": ["customer_id", "points_earned"]
                    }
                }
            },
            'properties.list': {
                "type": "function",
                "function": {
                    "name": "list_properties",
                    "description": "List available properties",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Property location"},
                            "price_range": {"type": "string", "description": "Price range"},
                            "property_type": {"type": "string", "description": "Type of property"},
                            "bedrooms": {"type": "integer", "description": "Number of bedrooms"}
                        },
                        "required": ["location"]
                    }
                }
            },
            'maintenance.request': {
                "type": "function",
                "function": {
                    "name": "create_maintenance_request",
                    "description": "Create a maintenance request",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tenant_name": {"type": "string", "description": "Tenant name"},
                            "property_address": {"type": "string", "description": "Property address"},
                            "issue_description": {"type": "string", "description": "Issue description"},
                            "urgency": {"type": "string", "description": "Urgency level"},
                            "contact_phone": {"type": "string", "description": "Contact phone"}
                        },
                        "required": ["tenant_name", "property_address", "issue_description"]
                    }
                }
            },
            'patients.remind': {
                "type": "function",
                "function": {
                    "name": "send_patient_reminder",
                    "description": "Send appointment reminder to patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_name": {"type": "string", "description": "Patient name"},
                            "appointment_date": {"type": "string", "description": "Appointment date"},
                            "appointment_time": {"type": "string", "description": "Appointment time"},
                            "reminder_type": {"type": "string", "description": "Type of reminder"},
                            "contact_method": {"type": "string", "description": "Contact method"}
                        },
                        "required": ["patient_name", "appointment_date", "appointment_time"]
                    }
                }
            },
            'emergency.dispatch': {
                "type": "function",
                "function": {
                    "name": "dispatch_emergency_service",
                    "description": "Dispatch emergency plumbing service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string", "description": "Customer name"},
                            "address": {"type": "string", "description": "Service address"},
                            "issue_description": {"type": "string", "description": "Emergency description"},
                            "contact_phone": {"type": "string", "description": "Contact phone"},
                            "urgency": {"type": "string", "description": "Urgency level"}
                        },
                        "required": ["customer_name", "address", "issue_description", "contact_phone"]
                    }
                }
            },
            'estimates.generate': {
                "type": "function",
                "function": {
                    "name": "generate_project_estimate",
                    "description": "Generate project estimate",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_type": {"type": "string", "description": "Type of project"},
                            "scope": {"type": "string", "description": "Project scope"},
                            "materials": {"type": "string", "description": "Required materials"},
                            "timeline": {"type": "string", "description": "Project timeline"},
                            "client_budget": {"type": "number", "description": "Client budget"}
                        },
                        "required": ["project_type", "scope"]
                    }
                }
            },
            'weather.check': {
                "type": "function",
                "function": {
                    "name": "check_weather_conditions",
                    "description": "Check weather conditions for outdoor work",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Work location"},
                            "date": {"type": "string", "description": "Work date"},
                            "work_type": {"type": "string", "description": "Type of outdoor work"}
                        },
                        "required": ["location", "date"]
                    }
                }
            },
            'reservations.manage': {
                "type": "function",
                "function": {
                    "name": "manage_car_reservation",
                    "description": "Manage car rental reservation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string", "description": "Customer name"},
                            "pickup_date": {"type": "string", "description": "Pickup date"},
                            "return_date": {"type": "string", "description": "Return date"},
                            "vehicle_type": {"type": "string", "description": "Vehicle type"},
                            "pickup_location": {"type": "string", "description": "Pickup location"}
                        },
                        "required": ["customer_name", "pickup_date", "return_date"]
                    }
                }
            },
            'content.plan': {
                "type": "function",
                "function": {
                    "name": "plan_content_calendar",
                    "description": "Plan content calendar",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string", "description": "Social media platform"},
                            "content_type": {"type": "string", "description": "Type of content"},
                            "target_audience": {"type": "string", "description": "Target audience"},
                            "posting_schedule": {"type": "string", "description": "Posting schedule"},
                            "campaign_goals": {"type": "string", "description": "Campaign goals"}
                        },
                        "required": ["platform", "content_type"]
                    }
                }
            },
            'campaigns.manage': {
                "type": "function",
                "function": {
                    "name": "manage_marketing_campaign",
                    "description": "Manage marketing campaign",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campaign_name": {"type": "string", "description": "Campaign name"},
                            "budget": {"type": "number", "description": "Campaign budget"},
                            "target_audience": {"type": "string", "description": "Target audience"},
                            "channels": {"type": "string", "description": "Marketing channels"},
                            "duration": {"type": "string", "description": "Campaign duration"}
                        },
                        "required": ["campaign_name", "budget"]
                    }
                }
            },
            'taxes.prepare': {
                "type": "function",
                "function": {
                    "name": "prepare_tax_documents",
                    "description": "Prepare tax documents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Client name"},
                            "tax_year": {"type": "string", "description": "Tax year"},
                            "document_types": {"type": "string", "description": "Types of documents needed"},
                            "deadline": {"type": "string", "description": "Filing deadline"},
                            "complexity": {"type": "string", "description": "Tax complexity level"}
                        },
                        "required": ["client_name", "tax_year"]
                    }
                }
            },
            'inventory.track': {
                "type": "function",
                "function": {
                    "name": "track_inventory",
                    "description": "Track retail inventory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "Product name"},
                            "quantity": {"type": "integer", "description": "Quantity in stock"},
                            "reorder_level": {"type": "integer", "description": "Reorder level"},
                            "supplier": {"type": "string", "description": "Supplier name"},
                            "category": {"type": "string", "description": "Product category"}
                        },
                        "required": ["product_name", "quantity"]
                    }
                }
            }
        }
        
        return [tool_definitions[tool] for tool in tools if tool in tool_definitions]
    
    def process_industry_request(self, industry: str, client_id: str, user_message: str) -> Dict[str, Any]:
        """Process request using industry-specific prompt and tools"""
        try:
            # Check if OpenAI client is available
            if not self.client:
                return self._fallback_response(user_message)
            
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
            # Check if OpenAI client is available
            if not self.client:
                return {
                    'response': 'AI Assistant is currently unavailable. Please check your OpenAI API key configuration.',
                    'success': False,
                    'error': 'OpenAI client not initialized'
                }
            
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
