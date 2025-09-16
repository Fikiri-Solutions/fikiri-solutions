#!/usr/bin/env python3
"""
Fikiri Solutions - Action Router
Maps intents to specific backend actions and generates responses.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

class ActionRouter:
    """Routes intents to specific backend actions."""
    
    def __init__(self, ai_assistant=None, crm_service=None, email_service=None):
        """Initialize action router with service dependencies."""
        self.ai_assistant = ai_assistant
        self.crm_service = crm_service
        self.email_service = email_service
    
    def route_action(self, intent: str, user_message: str, context: Dict = None) -> Dict[str, Any]:
        """Route intent to appropriate action and generate response."""
        context = context or {}
        
        try:
            if intent == "email_last_received":
                return self._handle_email_last_received(user_message)
            elif intent == "email_search":
                return self._handle_email_search(user_message, context)
            elif intent == "email_count":
                return self._handle_email_count(user_message)
            elif intent == "crm_new_lead":
                return self._handle_crm_new_lead(user_message, context)
            elif intent == "crm_lead_count":
                return self._handle_crm_lead_count(user_message)
            elif intent == "automation_setup":
                return self._handle_automation_setup(user_message)
            elif intent == "service_status":
                return self._handle_service_status(user_message)
            elif intent == "help_support":
                return self._handle_help_support(user_message)
            elif intent == "greeting":
                return self._handle_greeting(user_message)
            elif intent == "math_query":
                return self._handle_math_query(user_message)
            else:
                return self._handle_general_inquiry(user_message)
        
        except Exception as e:
            return self._handle_error_response(str(e))
    
    def _handle_email_last_received(self, user_message: str) -> Dict[str, Any]:
        """Handle request for last received email."""
        # Check if email service is connected
        if not self.email_service or not self.email_service.is_connected():
            return {
                "response": "📧 I'd love to show you your most recent email! To access your latest messages, I need to connect to your email service (Gmail, Outlook, etc.). Please set up your email integration in the Services section, and I'll be able to show you real-time email data.",
                "action_taken": "suggest_email_setup",
                "success": True,
                "requires_setup": True
            }
        
        # Mock email fetching - will be replaced with actual service integration
        return {
            "response": "📧 Your most recent email:\n\nFrom: Sarah Lee (slee@company.com)\nSubject: Project Update\nReceived: 3:57 PM\nSnippet: \"Just finished the report, attaching the draft...\"\n\nWould you like me to open it or draft a reply?",
            "action_taken": "fetch_last_email",
            "success": True,
            "data": {
                "sender": "Sarah Lee",
                "email": "slee@company.com",
                "subject": "Project Update",
                "time": "3:57 PM",
                "snippet": "Just finished the report, attaching the draft..."
            }
        }
    
    def _handle_email_search(self, user_message: str, context: Dict) -> Dict[str, Any]:
        """Handle email search requests."""
        if not self.email_service or not self.email_service.is_connected():
            return {
                "response": "🔍 I can help you search your emails! To find specific messages, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section.",
                "action_taken": "suggest_email_setup",
                "success": True,
                "requires_setup": True
            }
        
        # Extract search terms from message
        search_terms = self._extract_search_terms(user_message)
        
        return {
            "response": f"🔍 Searching for emails containing: {', '.join(search_terms)}\n\nFound 3 matching emails:\n\n1. From: John Smith - \"Project Proposal\" (2 hours ago)\n2. From: Jane Doe - \"Meeting Follow-up\" (1 day ago)\n3. From: Mike Johnson - \"Budget Review\" (3 days ago)\n\nWould you like me to show details for any of these?",
            "action_taken": "search_emails",
            "success": True,
            "search_terms": search_terms
        }
    
    def _handle_email_count(self, user_message: str) -> Dict[str, Any]:
        """Handle email count requests."""
        if not self.email_service or not self.email_service.is_connected():
            return {
                "response": "📊 I can help you check your email count! To get the exact number of emails in your inbox, I need to connect to your email service. Please set up your Gmail or Outlook integration in the Services section, and I'll be able to show you real-time email statistics.",
                "action_taken": "suggest_email_setup",
                "success": True,
                "requires_setup": True
            }
        
        return {
            "response": "📊 Your email statistics:\n\n• Total emails: 1,247\n• Unread: 23\n• Today: 8\n• This week: 45\n\nWould you like me to help you organize or prioritize any of these?",
            "action_taken": "get_email_count",
            "success": True,
            "data": {
                "total": 1247,
                "unread": 23,
                "today": 8,
                "this_week": 45
            }
        }
    
    def _handle_crm_new_lead(self, user_message: str, context: Dict) -> Dict[str, Any]:
        """Handle new lead creation requests."""
        if not self.crm_service:
            return {
                "response": "👥 I can help you add new leads! Please visit the CRM section to create and manage your contacts. You can also import leads from CSV files or connect your email to automatically capture new prospects.",
                "action_taken": "suggest_crm_setup",
                "success": True,
                "requires_setup": True
            }
        
        # Extract lead information from message
        lead_info = self._extract_lead_info(user_message)
        
        return {
            "response": f"👥 I'll help you add this new lead:\n\n• Name: {lead_info.get('name', 'Not specified')}\n• Email: {lead_info.get('email', 'Not specified')}\n• Company: {lead_info.get('company', 'Not specified')}\n• Phone: {lead_info.get('phone', 'Not specified')}\n\nWould you like me to save this lead to your CRM?",
            "action_taken": "create_lead",
            "success": True,
            "lead_data": lead_info
        }
    
    def _handle_crm_lead_count(self, user_message: str) -> Dict[str, Any]:
        """Handle lead count requests."""
        try:
            if self.crm_service:
                leads = self.crm_service.get_all_leads()
                lead_count = len(leads)
                
                return {
                    "response": f"👥 Great question! I can see you currently have {lead_count} leads in your CRM system. You can view and manage all your leads in the CRM section. I can also help automate lead scoring and follow-ups once your email integration is set up.",
                    "action_taken": "get_lead_count",
                    "success": True,
                    "data": {"lead_count": lead_count}
                }
            else:
                return {
                    "response": "👥 I can help you check your lead count! To get the exact number of leads in your CRM, please visit the CRM section. I can also help automate lead scoring and follow-ups once your email integration is set up.",
                    "action_taken": "suggest_crm_setup",
                    "success": True,
                    "requires_setup": True
                }
        except Exception as e:
            return {
                "response": "👥 I can help you check your lead count! Please visit the CRM section to view and manage your contacts.",
                "action_taken": "suggest_crm_setup",
                "success": True,
                "requires_setup": True
            }
    
    def _handle_automation_setup(self, user_message: str) -> Dict[str, Any]:
        """Handle automation setup requests."""
        return {
            "response": "⚙️ I can help you set up email automation! Here's what I can automate for you:\n\n• Auto-responses to common inquiries\n• Lead scoring and prioritization\n• Follow-up sequences\n• Email categorization\n\nTo get started, please set up your email integration in the Services section, then I can configure specific automation rules for your business.",
            "action_taken": "setup_automation",
            "success": True,
            "requires_setup": True
        }
    
    def _handle_service_status(self, user_message: str) -> Dict[str, Any]:
        """Handle service status requests."""
        services_status = {
            "ai_assistant": "✅ Active",
            "crm_service": "✅ Active", 
            "email_service": "⚠️ Not Connected",
            "automation": "⚠️ Not Configured"
        }
        
        status_text = "🔧 Your service status:\n\n"
        for service, status in services_status.items():
            status_text += f"• {service.replace('_', ' ').title()}: {status}\n"
        
        status_text += "\nVisit the Services section to connect and configure all integrations."
        
        return {
            "response": status_text,
            "action_taken": "check_services",
            "success": True,
            "services_status": services_status
        }
    
    def _handle_help_support(self, user_message: str) -> Dict[str, Any]:
        """Handle help and support requests - ALWAYS use ChatGPT 3.5 Turbo."""
        if self.ai_assistant and self.ai_assistant.is_enabled():
            try:
                ai_response = self.ai_assistant._generate_ai_response(f"As the Fikiri Solutions AI Assistant, provide helpful support for this request: {user_message}. Focus on email automation, lead management, CRM, and business communication.")
                return {
                    "response": ai_response,
                    "action_taken": "ai_help_support",
                    "success": True,
                    "ai_generated": True
                }
            except Exception as e:
                print(f"AI help support failed: {e}")
        
        # Fallback template
        return {
            "response": "🆘 I'm here to help! I can assist with:\n\n• Email automation and responses\n• Lead management and CRM\n• Customer communication strategies\n• Business process optimization\n\nWhat specific area would you like help with? You can also check the Services section to set up integrations.",
            "action_taken": "provide_help",
            "success": True,
            "ai_generated": False
        }
    
    def _handle_greeting(self, user_message: str) -> Dict[str, Any]:
        """Handle greeting messages - ALWAYS use ChatGPT 3.5 Turbo."""
        if self.ai_assistant and self.ai_assistant.is_enabled():
            try:
                ai_response = self.ai_assistant._generate_ai_response(f"Respond to this greeting in a friendly, professional way as the Fikiri Solutions AI Assistant: {user_message}")
                return {
                    "response": ai_response,
                    "action_taken": "ai_greeting",
                    "success": True,
                    "ai_generated": True
                }
            except Exception as e:
                print(f"AI greeting failed: {e}")
        
        # Fallback template
        return {
            "response": "👋 Hello! I'm your Fikiri Solutions AI Assistant. I can help you with email automation, lead management, and customer communication. To get started, you can set up your email integration in the Services section. How can I assist you today?",
            "action_taken": "greet_user",
            "success": True,
            "ai_generated": False
        }
    
    def _handle_math_query(self, user_message: str) -> Dict[str, Any]:
        """Handle mathematical calculations safely."""
        import re
        import ast
        
        try:
            # Extract mathematical expression from the message
            # Look for patterns like "2+2", "10 * 5", "100/4", etc.
            math_patterns = [
                r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)',  # Basic operations
                r'what.*is.*(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)',  # "What is 2+2?"
                r'calculate.*(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)',  # "Calculate 10*5"
            ]
            
            expression = None
            for pattern in math_patterns:
                match = re.search(pattern, user_message.lower())
                if match:
                    if len(match.groups()) == 3:
                        num1, op, num2 = match.groups()
                        expression = f"{num1} {op} {num2}"
                    else:
                        expression = match.group(1)
                    break
            
            if not expression:
                return {
                    "response": "🧮 I can help with basic math! Try asking something like:\n\n• What is 2+2?\n• Calculate 10 * 5\n• What's 100 divided by 4?\n\nI can handle addition (+), subtraction (-), multiplication (*), and division (/).",
                    "action_taken": "math_help",
                    "success": True
                }
            
            # Safe evaluation with limited operations
            allowed_ops = ['+', '-', '*', '/']
            if not any(op in expression for op in allowed_ops):
                return {
                    "response": "🧮 I can only handle basic arithmetic operations (+, -, *, /). Please ask something like 'What is 2+2?' or 'Calculate 10*5'.",
                    "action_taken": "math_help",
                    "success": True
                }
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, {})
            
            return {
                "response": f"🧮 {expression} = {result}",
                "action_taken": "calculate_math",
                "success": True,
                "calculation": {
                    "expression": expression,
                    "result": result
                }
            }
            
        except ZeroDivisionError:
            return {
                "response": "🧮 Error: Division by zero is not allowed.",
                "action_taken": "math_error",
                "success": False,
                "error": "division_by_zero"
            }
        except Exception as e:
            return {
                "response": f"🧮 I couldn't calculate that. Please try a simpler expression like '2+2' or '10*5'.",
                "action_taken": "math_error",
                "success": False,
                "error": str(e)
            }
    
    def _handle_general_inquiry(self, user_message: str) -> Dict[str, Any]:
        """Handle general inquiries with AI assistance - ALWAYS use ChatGPT 3.5 Turbo."""
        if self.ai_assistant and self.ai_assistant.is_enabled():
            try:
                # Force AI generation for ALL general inquiries
                ai_response = self.ai_assistant._generate_ai_response(user_message)
                return {
                    "response": ai_response,
                    "action_taken": "ai_response",
                    "success": True,
                    "ai_generated": True
                }
            except Exception as e:
                print(f"AI response failed: {e}")
                # Even if AI fails, try to generate a response
                try:
                    fallback_ai = self.ai_assistant._generate_ai_response(f"Please respond to this user message: {user_message}")
                    return {
                        "response": fallback_ai,
                        "action_taken": "ai_fallback_response",
                        "success": True,
                        "ai_generated": True
                    }
                except Exception as e2:
                    print(f"Fallback AI also failed: {e2}")
        
        # Only use template if AI is completely unavailable
        return {
            "response": "I'm Fikiri Solutions AI Assistant! I can help you with email automation, lead management, and customer communication. To provide more specific assistance, please set up your email integration in the Services section. How can I assist you today?",
            "action_taken": "provide_information",
            "success": True,
            "ai_generated": False
        }
    
    def _handle_error_response(self, error_message: str) -> Dict[str, Any]:
        """Handle error responses."""
        return {
            "response": "I apologize, but I encountered an issue processing your request. Please try again or contact support if the problem persists.",
            "action_taken": "error_handling",
            "success": False,
            "error": error_message
        }
    
    def _extract_search_terms(self, message: str) -> List[str]:
        """Extract search terms from user message."""
        # Simple extraction - look for quoted terms or key phrases
        import re
        
        # Find quoted terms
        quoted_terms = re.findall(r'"([^"]*)"', message)
        
        # Find terms after "from", "about", "containing"
        pattern_terms = re.findall(r'(?:from|about|containing|search for)\s+([a-zA-Z0-9@._-]+)', message.lower())
        
        return quoted_terms + pattern_terms
    
    def _extract_lead_info(self, message: str) -> Dict[str, str]:
        """Extract lead information from user message."""
        import re
        
        lead_info = {}
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
        if email_match:
            lead_info['email'] = str(email_match.group()).strip()
        
        # Extract phone
        phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', message)
        if phone_match:
            lead_info['phone'] = str(phone_match.group()).strip()
        
        # Extract company (look for "at" or "from")
        company_match = re.search(r'(?:at|from)\s+([A-Za-z0-9\s&.,-]+)', message)
        if company_match:
            lead_info['company'] = str(company_match.group(1)).strip()
        
        # Extract name (first word after "add" or "create")
        name_match = re.search(r'(?:add|create)\s+([A-Za-z\s]+)', message)
        if name_match:
            lead_info['name'] = str(name_match.group(1)).strip()
        
        # Ensure all values are strings and not None
        for key, value in lead_info.items():
            if value is None:
                lead_info[key] = ""
            elif not isinstance(value, str):
                lead_info[key] = str(value)
        
        return lead_info

def create_action_router(ai_assistant=None, crm_service=None, email_service=None) -> ActionRouter:
    """Create and return an action router instance."""
    return ActionRouter(ai_assistant, crm_service, email_service)

if __name__ == "__main__":
    # Test the action router
    print("🧪 Testing Action Router")
    print("=" * 50)
    
    router = ActionRouter()
    
    test_cases = [
        ("email_last_received", "Who emailed me last?"),
        ("crm_lead_count", "How many leads do I have?"),
        ("automation_setup", "Set up email automation"),
        ("service_status", "Is the service working?"),
        ("greeting", "Hello there")
    ]
    
    for intent, message in test_cases:
        result = router.route_action(intent, message)
        print(f"Intent: {intent}")
        print(f"Message: '{message}'")
        print(f"Response: {result['response'][:100]}...")
        print(f"Action: {result['action_taken']}")
        print("-" * 30)
    
    print("🎉 Action router tests completed!")
