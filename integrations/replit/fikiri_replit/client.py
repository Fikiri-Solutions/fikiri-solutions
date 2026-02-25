"""
Fikiri Client for Replit
Main client class for interacting with Fikiri API
"""

import requests
from typing import Dict, Any, Optional


class FikiriClient:
    """Client for Fikiri API integration"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.fikirisolutions.com"):
        """
        Initialize Fikiri client
        
        Args:
            api_key: Your Fikiri API key (starts with 'fik_')
            api_url: Fikiri API base URL (default: production)
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        })
        
        # Initialize sub-clients
        self.leads = self.Leads(self)
        self.chatbot = self.Chatbot(self)
        self.forms = self.Forms(self)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.api_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    class Leads:
        """Lead management operations"""
        
        def __init__(self, client: 'FikiriClient'):
            self.client = client
        
        def create(self, email: str, name: Optional[str] = None, 
                   phone: Optional[str] = None, source: str = "replit_app",
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """
            Create a lead
            
            Args:
                email: Lead email address
                name: Lead name (optional)
                phone: Lead phone number (optional)
                source: Lead source (default: 'replit_app')
                metadata: Additional metadata (optional)
            
            Returns:
                Dict with success status and lead_id
            """
            data = {
                "email": email,
                "source": source
            }
            if name:
                data["name"] = name
            if phone:
                data["phone"] = phone
            if metadata:
                data["metadata"] = metadata
            
            return self.client._request(
                'POST',
                '/api/webhooks/leads/capture',
                json=data
            )
        
        def capture(self, **kwargs) -> Dict[str, Any]:
            """Alias for create()"""
            return self.create(**kwargs)
    
    class Chatbot:
        """Chatbot operations"""
        
        def __init__(self, client: 'FikiriClient'):
            self.client = client
        
        def query(self, query: str, conversation_id: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None,
                  lead: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """
            Query the chatbot
            
            Args:
                query: User's question
                conversation_id: Conversation ID for context (optional)
                context: Additional context (optional)
                lead: Lead information (optional)
            
            Returns:
                Dict with chatbot response
            """
            data = {"query": query}
            if conversation_id:
                data["conversation_id"] = conversation_id
            if context:
                data["context"] = context
            if lead:
                data["lead"] = lead
            
            return self.client._request(
                'POST',
                '/api/public/chatbot/query',
                json=data
            )
    
    class Forms:
        """Form submission operations"""
        
        def __init__(self, client: 'FikiriClient'):
            self.client = client
        
        def submit(self, fields: Dict[str, Any],
                   form_id: str = "custom-form",
                   source: str = "replit_app",
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """
            Submit a form
            
            Args:
                form_id: Form identifier
                fields: Form field values
                source: Form source (default: 'replit_app')
                metadata: Additional metadata (optional)
            
            Returns:
                Dict with success status and lead_id
            """
            data = {
                "form_id": form_id,
                "fields": fields,
                "source": source
            }
            if metadata:
                data["metadata"] = metadata
            
            return self.client._request(
                'POST',
                '/api/webhooks/forms/submit',
                json=data
            )
