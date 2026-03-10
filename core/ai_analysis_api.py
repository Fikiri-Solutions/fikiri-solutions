"""
AI Analysis API Endpoints
Schema-validated endpoints for contacts, leads, and business summary analysis
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from marshmallow import Schema, fields, ValidationError, validate

from core.api_key_manager import api_key_manager
from core.public_chatbot_api import require_api_key, record_api_usage
from core.api_validation import handle_api_errors, create_error_response
from core.ai.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# Create Blueprint
ai_analysis_bp = Blueprint('ai_analysis', __name__, url_prefix='/api/public/ai')

# Initialize LLM router
try:
    llm_router = LLMRouter()
except Exception as e:
    logger.warning(f"LLM router not available: {e}")
    llm_router = None


def _call_llm_json(prompt: str, max_tokens: int = 500) -> Optional[Dict[str, Any]]:
    """Call LLM router and parse JSON response if possible."""
    if not llm_router or not llm_router.client or not llm_router.client.is_enabled():
        return None

    result = llm_router.process(
        input_data=prompt,
        intent='extraction',
        context={'max_tokens': max_tokens}
    )

    if not result.get('success'):
        logger.error("AI analysis LLM failed: %s", result.get('error'))
        return None

    try:
        return json.loads(result.get('content', '') or '{}')
    except Exception:
        return None


# Schema Definitions for Request Validation

class ContactAnalysisSchema(Schema):
    """Schema for contact analysis request"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    email = fields.Email(required=True)
    company = fields.Str(validate=validate.Length(max=255), allow_none=True)
    phone = fields.Str(validate=validate.Length(max=50), allow_none=True)
    job_title = fields.Str(validate=validate.Length(max=255), allow_none=True)
    notes = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class LeadAnalysisSchema(Schema):
    """Schema for lead analysis request"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    email = fields.Email(required=True)
    company = fields.Str(validate=validate.Length(max=255), allow_none=True)
    phone = fields.Str(validate=validate.Length(max=50), allow_none=True)
    source = fields.Str(validate=validate.Length(max=100), allow_none=True)
    status = fields.Str(validate=validate.OneOf(['new', 'contacted', 'qualified', 'converted', 'lost']), allow_none=True)
    notes = fields.Str(allow_none=True)
    metadata = fields.Dict(allow_none=True)


class BusinessSummarySchema(Schema):
    """Schema for business summary request"""
    business_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    industry = fields.Str(validate=validate.Length(max=100), allow_none=True)
    description = fields.Str(allow_none=True)
    website = fields.Url(allow_none=True)
    employee_count = fields.Int(validate=validate.Range(min=0), allow_none=True)
    revenue_range = fields.Str(validate=validate.Length(max=50), allow_none=True)
    location = fields.Str(validate=validate.Length(max=255), allow_none=True)
    metadata = fields.Dict(allow_none=True)


# Response Schemas

class ContactAnalysisResponse:
    """Structured response for contact analysis"""
    def __init__(self, contact_data: Dict[str, Any]):
        self.contact_data = contact_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with schema validation"""
        return {
            "success": True,
            "analysis": {
                "contact_score": self.contact_data.get("score", 0),
                "engagement_level": self.contact_data.get("engagement_level", "unknown"),
                "recommended_actions": self.contact_data.get("recommended_actions", []),
                "insights": self.contact_data.get("insights", []),
                "risk_factors": self.contact_data.get("risk_factors", []),
                "opportunities": self.contact_data.get("opportunities", [])
            },
            "metadata": {
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "model_version": "gpt-4"
            }
        }


class LeadAnalysisResponse:
    """Structured response for lead analysis"""
    def __init__(self, lead_data: Dict[str, Any]):
        self.lead_data = lead_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with schema validation"""
        return {
            "success": True,
            "analysis": {
                "lead_score": self.lead_data.get("score", 0),
                "conversion_probability": self.lead_data.get("conversion_probability", 0.0),
                "priority": self.lead_data.get("priority", "medium"),
                "recommended_actions": self.lead_data.get("recommended_actions", []),
                "insights": self.lead_data.get("insights", []),
                "next_steps": self.lead_data.get("next_steps", []),
                "estimated_value": self.lead_data.get("estimated_value", 0)
            },
            "metadata": {
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "model_version": "gpt-4"
            }
        }


class BusinessSummaryResponse:
    """Structured response for business summary"""
    def __init__(self, business_data: Dict[str, Any]):
        self.business_data = business_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with schema validation"""
        return {
            "success": True,
            "summary": {
                "business_name": self.business_data.get("business_name", ""),
                "industry": self.business_data.get("industry", ""),
                "size_category": self.business_data.get("size_category", "unknown"),
                "key_insights": self.business_data.get("key_insights", []),
                "market_position": self.business_data.get("market_position", ""),
                "growth_potential": self.business_data.get("growth_potential", "unknown"),
                "recommendations": self.business_data.get("recommendations", [])
            },
            "metadata": {
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "model_version": "gpt-4"
            }
        }


# AI Analysis Functions

def analyze_contact(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze contact using AI"""
    if not llm_router:
        raise ValueError("AI assistant not available")
    
    # Build prompt for contact analysis
    prompt = f"""
    Analyze the following contact information and provide insights:
    
    Name: {contact_data.get('name', 'N/A')}
    Email: {contact_data.get('email', 'N/A')}
    Company: {contact_data.get('company', 'N/A')}
    Job Title: {contact_data.get('job_title', 'N/A')}
    Phone: {contact_data.get('phone', 'N/A')}
    Notes: {contact_data.get('notes', 'N/A')}
    
    Provide analysis in JSON format with:
    - score: integer 0-100 (contact quality score)
    - engagement_level: string (high/medium/low)
    - recommended_actions: array of strings
    - insights: array of strings
    - risk_factors: array of strings
    - opportunities: array of strings
    """
    
    try:
        analysis = _call_llm_json(prompt, max_tokens=500)
        if analysis is None:
            analysis = {
                "score": 50,
                "engagement_level": "medium",
                "recommended_actions": ["Follow up via email"],
                "insights": ["AI response unavailable; please retry."],
                "risk_factors": [],
                "opportunities": []
            }
        return analysis
        
    except Exception as e:
        logger.error(f"Contact analysis failed: {e}")
        raise


def analyze_lead(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze lead using AI"""
    if not llm_router:
        raise ValueError("AI assistant not available")
    
    prompt = f"""
    Analyze the following lead and provide conversion insights:
    
    Name: {lead_data.get('name', 'N/A')}
    Email: {lead_data.get('email', 'N/A')}
    Company: {lead_data.get('company', 'N/A')}
    Source: {lead_data.get('source', 'N/A')}
    Status: {lead_data.get('status', 'new')}
    Notes: {lead_data.get('notes', 'N/A')}
    
    Provide analysis in JSON format with:
    - score: integer 0-100 (lead score)
    - conversion_probability: float 0.0-1.0
    - priority: string (high/medium/low)
    - recommended_actions: array of strings
    - insights: array of strings
    - next_steps: array of strings
    - estimated_value: integer (estimated deal value)
    """
    
    try:
        analysis = _call_llm_json(prompt, max_tokens=500)
        if analysis is None:
            analysis = {
                "score": 50,
                "conversion_probability": 0.5,
                "priority": "medium",
                "recommended_actions": ["Qualify lead"],
                "insights": ["AI response unavailable; please retry."],
                "next_steps": ["Schedule discovery call"],
                "estimated_value": 0
            }
        return analysis
        
    except Exception as e:
        logger.error(f"Lead analysis failed: {e}")
        raise


def analyze_business(business_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze business using AI"""
    if not llm_router:
        raise ValueError("AI assistant not available")
    
    prompt = f"""
    Analyze the following business and provide a comprehensive summary:
    
    Business Name: {business_data.get('business_name', 'N/A')}
    Industry: {business_data.get('industry', 'N/A')}
    Description: {business_data.get('description', 'N/A')}
    Website: {business_data.get('website', 'N/A')}
    Employee Count: {business_data.get('employee_count', 'N/A')}
    Revenue Range: {business_data.get('revenue_range', 'N/A')}
    Location: {business_data.get('location', 'N/A')}
    
    Provide analysis in JSON format with:
    - business_name: string
    - industry: string
    - size_category: string (startup/small/medium/large/enterprise)
    - key_insights: array of strings
    - market_position: string
    - growth_potential: string (high/medium/low)
    - recommendations: array of strings
    """
    
    try:
        analysis = _call_llm_json(prompt, max_tokens=800)
        if analysis is None:
            analysis = {
                "business_name": business_data.get('business_name', ''),
                "industry": business_data.get('industry', ''),
                "size_category": "unknown",
                "key_insights": ["AI response unavailable; please retry."],
                "market_position": "unknown",
                "growth_potential": "unknown",
                "recommendations": []
            }
        return analysis
        
    except Exception as e:
        logger.error(f"Business analysis failed: {e}")
        raise


# API Endpoints

@ai_analysis_bp.route('/analyze/contact', methods=['POST', 'OPTIONS'])
@handle_api_errors
@require_api_key
def analyze_contact_endpoint():
    """
    Analyze a contact using AI
    
    Request:
        POST /api/public/ai/analyze/contact
        Headers:
            X-API-Key: fik_...
        Body:
            {
                "name": "John Doe",
                "email": "john@example.com",
                "company": "Acme Corp",
                "phone": "+1234567890",
                "job_title": "CEO",
                "notes": "Interested in our product"
            }
    
    Response:
        {
            "success": true,
            "analysis": {
                "contact_score": 85,
                "engagement_level": "high",
                "recommended_actions": [...],
                "insights": [...],
                "risk_factors": [...],
                "opportunities": [...]
            }
        }
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate request schema
        schema = ContactAnalysisSchema()
        try:
            validated_data = schema.load(request.json)
        except ValidationError as err:
            record_api_usage(response_status=400)
            return jsonify({
                "success": False,
                "error": "Validation error",
                "errors": err.messages
            }), 400
        
        # Perform AI analysis
        analysis_result = analyze_contact(validated_data)
        
        # Build response
        response_obj = ContactAnalysisResponse(analysis_result)
        response_data = response_obj.to_dict()
        
        # Record usage
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        
        return jsonify(response_data)
        
    except ValueError as e:
        record_api_usage(response_status=503)
        return create_error_response(str(e), 503, 'AI_SERVICE_UNAVAILABLE')
    except Exception as e:
        logger.error(f"❌ Contact analysis failed: {e}", exc_info=True)
        record_api_usage(response_status=500)
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


@ai_analysis_bp.route('/analyze/lead', methods=['POST', 'OPTIONS'])
@handle_api_errors
@require_api_key
def analyze_lead_endpoint():
    """
    Analyze a lead using AI
    
    Request:
        POST /api/public/ai/analyze/lead
        Headers:
            X-API-Key: fik_...
        Body:
            {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "company": "Tech Corp",
                "source": "website",
                "status": "new",
                "notes": "Requested demo"
            }
    
    Response:
        {
            "success": true,
            "analysis": {
                "lead_score": 75,
                "conversion_probability": 0.75,
                "priority": "high",
                "recommended_actions": [...],
                "insights": [...],
                "next_steps": [...],
                "estimated_value": 50000
            }
        }
    """
    start_time = datetime.utcnow()
    
    try:
        schema = LeadAnalysisSchema()
        try:
            validated_data = schema.load(request.json)
        except ValidationError as err:
            record_api_usage(response_status=400)
            return jsonify({
                "success": False,
                "error": "Validation error",
                "errors": err.messages
            }), 400
        
        analysis_result = analyze_lead(validated_data)
        response_obj = LeadAnalysisResponse(analysis_result)
        response_data = response_obj.to_dict()
        
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        
        return jsonify(response_data)
        
    except ValueError as e:
        record_api_usage(response_status=503)
        return create_error_response(str(e), 503, 'AI_SERVICE_UNAVAILABLE')
    except Exception as e:
        logger.error(f"❌ Lead analysis failed: {e}", exc_info=True)
        record_api_usage(response_status=500)
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


@ai_analysis_bp.route('/analyze/business', methods=['POST', 'OPTIONS'])
@handle_api_errors
@require_api_key
def analyze_business_endpoint():
    """
    Analyze a business using AI
    
    Request:
        POST /api/public/ai/analyze/business
        Headers:
            X-API-Key: fik_...
        Body:
            {
                "business_name": "Acme Corporation",
                "industry": "Technology",
                "description": "SaaS platform",
                "website": "https://acme.com",
                "employee_count": 100,
                "revenue_range": "$10M-$50M"
            }
    
    Response:
        {
            "success": true,
            "summary": {
                "business_name": "Acme Corporation",
                "industry": "Technology",
                "size_category": "medium",
                "key_insights": [...],
                "market_position": "...",
                "growth_potential": "high",
                "recommendations": [...]
            }
        }
    """
    start_time = datetime.utcnow()
    
    try:
        schema = BusinessSummarySchema()
        try:
            validated_data = schema.load(request.json)
        except ValidationError as err:
            record_api_usage(response_status=400)
            return jsonify({
                "success": False,
                "error": "Validation error",
                "errors": err.messages
            }), 400
        
        analysis_result = analyze_business(validated_data)
        response_obj = BusinessSummaryResponse(analysis_result)
        response_data = response_obj.to_dict()
        
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        record_api_usage(response_status=200, response_time_ms=response_time_ms)
        
        return jsonify(response_data)
        
    except ValueError as e:
        record_api_usage(response_status=503)
        return create_error_response(str(e), 503, 'AI_SERVICE_UNAVAILABLE')
    except Exception as e:
        logger.error(f"❌ Business analysis failed: {e}", exc_info=True)
        record_api_usage(response_status=500)
        return create_error_response("Internal server error", 500, 'INTERNAL_ERROR')


@ai_analysis_bp.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    
    return response
