"""
FastAPI helpers for Fikiri integration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from .client import FikiriClient


class ChatbotQuery(BaseModel):
    """Chatbot query request model"""
    query: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    lead: Optional[Dict[str, Any]] = None


class LeadCapture(BaseModel):
    """Lead capture request model"""
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    source: str = "replit_app"
    metadata: Optional[Dict[str, Any]] = None


class FormSubmit(BaseModel):
    """Form submission request model"""
    form_id: str = "custom-form"
    fields: Dict[str, Any]
    source: str = "replit_app"
    metadata: Optional[Dict[str, Any]] = None


class FikiriFastAPIHelper:
    """Helper class for FastAPI integration"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.fikirisolutions.com"):
        """
        Initialize FastAPI helper
        
        Args:
            api_key: Your Fikiri API key
            api_url: Fikiri API base URL
        """
        self.client = FikiriClient(api_key, api_url)
    
    def create_router(self, prefix: str = "/fikiri") -> APIRouter:
        """
        Create FastAPI router with Fikiri endpoints
        
        Args:
            prefix: URL prefix for routes (default: '/fikiri')
        
        Returns:
            FastAPI APIRouter
        """
        router = APIRouter(prefix=prefix, tags=["fikiri"])
        
        @router.post("/chatbot")
        async def chatbot_query(request: ChatbotQuery):
            """Chatbot query endpoint"""
            result = self.client.chatbot.query(
                query=request.query,
                conversation_id=request.conversation_id,
                context=request.context,
                lead=request.lead
            )
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error'))
            return result
        
        @router.post("/leads/capture")
        async def capture_lead(request: LeadCapture):
            """Lead capture endpoint"""
            result = self.client.leads.create(
                email=request.email,
                name=request.name,
                phone=request.phone,
                source=request.source,
                metadata=request.metadata
            )
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error'))
            return result
        
        @router.post("/forms/submit")
        async def submit_form(request: FormSubmit):
            """Form submission endpoint"""
            if 'email' not in request.fields:
                raise HTTPException(status_code=400, detail="Email is required in fields")
            
            result = self.client.forms.submit(
                form_id=request.form_id,
                fields=request.fields,
                source=request.source,
                metadata=request.metadata
            )
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error'))
            return result
        
        return router
