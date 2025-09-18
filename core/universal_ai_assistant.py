"""
Enhanced AI Assistant - Universal Interface Layer
Acts as the central hub connecting natural language queries to all backend services
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from core.database_optimization import db_optimizer
from core.user_auth import user_auth_manager
from core.gmail_oauth import gmail_oauth_manager, gmail_sync_manager
from core.privacy_manager import privacy_manager

logger = logging.getLogger(__name__)

@dataclass
class ServiceQuery:
    """Service query data structure"""
    service: str
    action: str
    parameters: Dict[str, Any]
    user_id: int
    timestamp: datetime

@dataclass
class AIResponse:
    """AI response data structure"""
    response: str
    service_queries: List[ServiceQuery]
    suggested_actions: List[str]
    confidence: float
    success: bool

class UniversalAIAssistant:
    """AI Assistant that acts as universal interface to all services"""
    
    def __init__(self):
        self.service_handlers = {
            'email_parser': self._handle_email_parser_query,
            'crm_service': self._handle_crm_query,
            'automation_engine': self._handle_automation_query,
            'analytics': self._handle_analytics_query,
            'privacy_manager': self._handle_privacy_query,
            'gmail_sync': self._handle_gmail_sync_query
        }
        
        # Intent patterns for natural language understanding
        self.intent_patterns = {
            'email_queries': [
                'who emailed me', 'recent emails', 'unread emails', 'email from',
                'last email', 'emails today', 'email activity', 'inbox'
            ],
            'lead_queries': [
                'how many leads', 'new leads', 'lead status', 'contacted leads',
                'leads this week', 'potential clients', 'prospects', 'customers'
            ],
            'automation_queries': [
                'set up automation', 'create rule', 'auto reply', 'automatic response',
                'email automation', 'workflow', 'trigger', 'when email arrives'
            ],
            'analytics_queries': [
                'how am i doing', 'performance', 'statistics', 'metrics',
                'dashboard', 'reports', 'analytics', 'insights'
            ],
            'privacy_queries': [
                'privacy settings', 'data retention', 'export data', 'delete data',
                'consent', 'gdpr', 'my data', 'privacy policy'
            ]
        }
    
    def process_query(self, user_message: str, user_id: int, context: Dict[str, Any] = None) -> AIResponse:
        """Process natural language query and route to appropriate services"""
        try:
            # Analyze intent and extract service requirements
            intent_analysis = self._analyze_intent(user_message)
            
            # Generate service queries based on intent
            service_queries = self._generate_service_queries(intent_analysis, user_id, context)
            
            # Execute service queries
            query_results = []
            for query in service_queries:
                result = self._execute_service_query(query)
                query_results.append(result)
            
            # Generate natural language response
            response = self._generate_response(user_message, query_results, intent_analysis)
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(intent_analysis, query_results)
            
            return AIResponse(
                response=response,
                service_queries=service_queries,
                suggested_actions=suggested_actions,
                confidence=intent_analysis.get('confidence', 0.8),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error processing AI query: {e}")
            return AIResponse(
                response="I apologize, but I encountered an issue processing your request. Please try again.",
                service_queries=[],
                suggested_actions=["Try rephrasing your question", "Check if Gmail is connected"],
                confidence=0.0,
                success=False
            )
    
    def _analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user message to determine intent and required services"""
        message_lower = user_message.lower()
        
        # Determine primary intent
        primary_intent = None
        confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    primary_intent = intent
                    confidence = 0.9
                    break
            if primary_intent:
                break
        
        # Extract entities and parameters
        entities = self._extract_entities(user_message)
        
        # Determine required services
        required_services = self._determine_required_services(primary_intent, entities)
        
        return {
            'primary_intent': primary_intent,
            'confidence': confidence,
            'entities': entities,
            'required_services': required_services,
            'original_message': user_message
        }
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from user message"""
        entities = {
            'time_period': None,
            'email_address': None,
            'company_name': None,
            'lead_stage': None,
            'automation_type': None
        }
        
        message_lower = message.lower()
        
        # Extract time periods
        time_patterns = {
            'today': 'today',
            'yesterday': 'yesterday',
            'this week': 'this_week',
            'last week': 'last_week',
            'this month': 'this_month',
            'last month': 'last_month'
        }
        
        for pattern, value in time_patterns.items():
            if pattern in message_lower:
                entities['time_period'] = value
                break
        
        # Extract email addresses (simple pattern)
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, message)
        if emails:
            entities['email_address'] = emails[0]
        
        # Extract lead stages
        stage_patterns = {
            'new': ['new', 'fresh', 'recent'],
            'contacted': ['contacted', 'reached out', 'called'],
            'replied': ['replied', 'responded', 'answered'],
            'qualified': ['qualified', 'hot', 'interested'],
            'closed': ['closed', 'won', 'sold', 'converted']
        }
        
        for stage, patterns in stage_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    entities['lead_stage'] = stage
                    break
            if entities['lead_stage']:
                break
        
        return entities
    
    def _determine_required_services(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Determine which services are needed based on intent"""
        service_mapping = {
            'email_queries': ['email_parser', 'gmail_sync'],
            'lead_queries': ['crm_service', 'email_parser'],
            'automation_queries': ['automation_engine', 'email_parser'],
            'analytics_queries': ['analytics', 'crm_service'],
            'privacy_queries': ['privacy_manager']
        }
        
        return service_mapping.get(intent, [])
    
    def _generate_service_queries(self, intent_analysis: Dict[str, Any], user_id: int, context: Dict[str, Any]) -> List[ServiceQuery]:
        """Generate specific service queries based on intent analysis"""
        queries = []
        intent = intent_analysis['primary_intent']
        entities = intent_analysis['entities']
        
        if intent == 'email_queries':
            queries.append(ServiceQuery(
                service='email_parser',
                action='get_recent_emails',
                parameters={
                    'user_id': user_id,
                    'time_period': entities.get('time_period', 'today'),
                    'limit': 10
                },
                user_id=user_id,
                timestamp=datetime.now()
            ))
        
        elif intent == 'lead_queries':
            queries.append(ServiceQuery(
                service='crm_service',
                action='get_leads_summary',
                parameters={
                    'user_id': user_id,
                    'stage': entities.get('lead_stage'),
                    'time_period': entities.get('time_period')
                },
                user_id=user_id,
                timestamp=datetime.now()
            ))
        
        elif intent == 'automation_queries':
            queries.append(ServiceQuery(
                service='automation_engine',
                action='get_automation_suggestions',
                parameters={
                    'user_id': user_id,
                    'automation_type': entities.get('automation_type', 'email_reply')
                },
                user_id=user_id,
                timestamp=datetime.now()
            ))
        
        elif intent == 'analytics_queries':
            queries.append(ServiceQuery(
                service='analytics',
                action='get_performance_metrics',
                parameters={
                    'user_id': user_id,
                    'time_period': entities.get('time_period', 'this_week')
                },
                user_id=user_id,
                timestamp=datetime.now()
            ))
        
        elif intent == 'privacy_queries':
            queries.append(ServiceQuery(
                service='privacy_manager',
                action='get_data_summary',
                parameters={
                    'user_id': user_id
                },
                user_id=user_id,
                timestamp=datetime.now()
            ))
        
        return queries
    
    def _execute_service_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Execute a service query"""
        try:
            handler = self.service_handlers.get(query.service)
            if handler:
                return handler(query)
            else:
                return {
                    'success': False,
                    'error': f'Service {query.service} not available',
                    'data': None
                }
        except Exception as e:
            logger.error(f"Error executing service query: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _handle_email_parser_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle email parser service queries"""
        try:
            if query.action == 'get_recent_emails':
                # Get recent emails from database
                emails = db_optimizer.execute_query(
                    """SELECT l.email, l.name, l.company, la.activity_type, la.timestamp
                       FROM leads l
                       LEFT JOIN lead_activities la ON l.id = la.lead_id
                       WHERE l.user_id = ? AND la.activity_type = 'email_received'
                       ORDER BY la.timestamp DESC
                       LIMIT ?""",
                    (query.parameters['user_id'], query.parameters.get('limit', 10))
                )
                
                return {
                    'success': True,
                    'data': {
                        'emails': [dict(email) for email in emails],
                        'count': len(emails)
                    }
                }
            
            return {'success': False, 'error': 'Unknown email parser action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _handle_crm_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle CRM service queries"""
        try:
            if query.action == 'get_leads_summary':
                # Get leads summary
                leads_data = db_optimizer.execute_query(
                    """SELECT stage, COUNT(*) as count
                       FROM leads
                       WHERE user_id = ?
                       GROUP BY stage""",
                    (query.parameters['user_id'],)
                )
                
                total_leads = db_optimizer.execute_query(
                    "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                    (query.parameters['user_id'],)
                )[0]['count']
                
                return {
                    'success': True,
                    'data': {
                        'leads_by_stage': [dict(lead) for lead in leads_data],
                        'total_leads': total_leads
                    }
                }
            
            return {'success': False, 'error': 'Unknown CRM action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _handle_automation_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle automation engine queries"""
        try:
            if query.action == 'get_automation_suggestions':
                # Get automation suggestions based on user's email patterns
                suggestions = [
                    {
                        'name': 'Auto-reply to new leads',
                        'description': 'Send a welcome message to new email contacts',
                        'trigger': 'New email from unknown sender',
                        'action': 'Send welcome email'
                    },
                    {
                        'name': 'Follow up on quotes',
                        'description': 'Send follow-up emails for quote requests',
                        'trigger': 'Email contains "quote" or "pricing"',
                        'action': 'Send quote follow-up'
                    },
                    {
                        'name': 'Mark important emails',
                        'description': 'Automatically label high-priority emails',
                        'trigger': 'Email from known clients',
                        'action': 'Apply "Important" label'
                    }
                ]
                
                return {
                    'success': True,
                    'data': {
                        'suggestions': suggestions
                    }
                }
            
            return {'success': False, 'error': 'Unknown automation action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _handle_analytics_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle analytics queries"""
        try:
            if query.action == 'get_performance_metrics':
                # Get performance metrics
                metrics = {}
                
                # Get leads count
                leads_count = db_optimizer.execute_query(
                    "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                    (query.parameters['user_id'],)
                )[0]['count']
                
                # Get activities count
                activities_count = db_optimizer.execute_query(
                    """SELECT COUNT(*) as count FROM lead_activities la
                       JOIN leads l ON la.lead_id = l.id
                       WHERE l.user_id = ?""",
                    (query.parameters['user_id'],)
                )[0]['count']
                
                # Get email sync status
                sync_status = gmail_sync_manager.get_sync_status(query.parameters['user_id'])
                
                metrics = {
                    'leads_count': leads_count,
                    'activities_count': activities_count,
                    'last_sync': sync_status.completed_at.isoformat() if sync_status and sync_status.completed_at else None,
                    'gmail_connected': gmail_oauth_manager.is_gmail_connected(query.parameters['user_id'])
                }
                
                return {
                    'success': True,
                    'data': metrics
                }
            
            return {'success': False, 'error': 'Unknown analytics action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _handle_privacy_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle privacy manager queries"""
        try:
            if query.action == 'get_data_summary':
                result = privacy_manager.get_data_summary(query.parameters['user_id'])
                return result
            
            return {'success': False, 'error': 'Unknown privacy action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _handle_gmail_sync_query(self, query: ServiceQuery) -> Dict[str, Any]:
        """Handle Gmail sync queries"""
        try:
            if query.action == 'get_sync_status':
                sync_status = gmail_sync_manager.get_sync_status(query.parameters['user_id'])
                return {
                    'success': True,
                    'data': {
                        'status': sync_status.status if sync_status else 'no_sync',
                        'emails_processed': sync_status.emails_processed if sync_status else 0,
                        'last_sync': sync_status.completed_at.isoformat() if sync_status and sync_status.completed_at else None
                    }
                }
            
            return {'success': False, 'error': 'Unknown Gmail sync action', 'data': None}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}
    
    def _generate_response(self, user_message: str, query_results: List[Dict[str, Any]], intent_analysis: Dict[str, Any]) -> str:
        """Generate natural language response based on query results"""
        intent = intent_analysis['primary_intent']
        
        if intent == 'email_queries':
            for result in query_results:
                if result['success'] and result['data']:
                    emails = result['data'].get('emails', [])
                    count = result['data'].get('count', 0)
                    
                    if count > 0:
                        response = f"I found {count} recent emails:\n\n"
                        for email in emails[:5]:  # Show first 5
                            response += f"• {email['name']} ({email['email']}) - {email['company'] or 'No company'}\n"
                        if count > 5:
                            response += f"\n... and {count - 5} more emails."
                        return response
                    else:
                        return "I don't see any recent emails in your system. Make sure Gmail is connected and synced."
            
            return "I couldn't retrieve your recent emails. Please check if Gmail is connected."
        
        elif intent == 'lead_queries':
            for result in query_results:
                if result['success'] and result['data']:
                    data = result['data']
                    total_leads = data.get('total_leads', 0)
                    leads_by_stage = data.get('leads_by_stage', [])
                    
                    response = f"You have {total_leads} total leads:\n\n"
                    for stage_data in leads_by_stage:
                        response += f"• {stage_data['stage'].title()}: {stage_data['count']} leads\n"
                    
                    return response
            
            return "I couldn't retrieve your leads information. Please check if Gmail is connected and synced."
        
        elif intent == 'automation_queries':
            for result in query_results:
                if result['success'] and result['data']:
                    suggestions = result['data'].get('suggestions', [])
                    
                    response = "Here are some automation suggestions for your business:\n\n"
                    for i, suggestion in enumerate(suggestions, 1):
                        response += f"{i}. **{suggestion['name']}**\n"
                        response += f"   {suggestion['description']}\n"
                        response += f"   Trigger: {suggestion['trigger']}\n"
                        response += f"   Action: {suggestion['action']}\n\n"
                    
                    return response
            
            return "I can help you set up automations! Let me suggest some common workflows for your business."
        
        elif intent == 'analytics_queries':
            for result in query_results:
                if result['success'] and result['data']:
                    metrics = result['data']
                    
                    response = "Here's your current performance:\n\n"
                    response += f"• Total Leads: {metrics.get('leads_count', 0)}\n"
                    response += f"• Total Activities: {metrics.get('activities_count', 0)}\n"
                    response += f"• Gmail Connected: {'Yes' if metrics.get('gmail_connected') else 'No'}\n"
                    
                    if metrics.get('last_sync'):
                        response += f"• Last Email Sync: {metrics['last_sync']}\n"
                    
                    return response
            
            return "I can provide insights about your business performance. Let me gather some metrics for you."
        
        elif intent == 'privacy_queries':
            for result in query_results:
                if result['success'] and result['data']:
                    data = result['data']
                    
                    response = "Here's your privacy and data summary:\n\n"
                    response += f"• Leads: {data.get('leads_count', 0)}\n"
                    response += f"• Activities: {data.get('activities_count', 0)}\n"
                    response += f"• Sync Records: {data.get('sync_records_count', 0)}\n\n"
                    
                    consents = data.get('consents', {})
                    response += "Your current consents:\n"
                    for consent_type, granted in consents.items():
                        response += f"• {consent_type.replace('_', ' ').title()}: {'Granted' if granted else 'Not granted'}\n"
                    
                    return response
            
            return "I can help you manage your privacy settings and data. Let me show you what information we have."
        
        # Default response
        return "I'm here to help! You can ask me about your emails, leads, automations, or privacy settings. What would you like to know?"
    
    def _generate_suggested_actions(self, intent_analysis: Dict[str, Any], query_results: List[Dict[str, Any]]) -> List[str]:
        """Generate suggested follow-up actions"""
        intent = intent_analysis['primary_intent']
        suggestions = []
        
        if intent == 'email_queries':
            suggestions.extend([
                "Show me emails from this week",
                "Who are my most active contacts?",
                "Set up email automation"
            ])
        
        elif intent == 'lead_queries':
            suggestions.extend([
                "Show me new leads this week",
                "Update lead statuses",
                "Create lead automation"
            ])
        
        elif intent == 'automation_queries':
            suggestions.extend([
                "Set up auto-reply for new leads",
                "Create follow-up automation",
                "Show me current automations"
            ])
        
        elif intent == 'analytics_queries':
            suggestions.extend([
                "Show me this week's performance",
                "Compare with last month",
                "Export my data"
            ])
        
        elif intent == 'privacy_queries':
            suggestions.extend([
                "Update my privacy settings",
                "Export my data",
                "Show me my consent history"
            ])
        
        # Add general suggestions
        suggestions.extend([
            "What can you help me with?",
            "Show me my dashboard",
            "Set up Gmail integration"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions

# Global universal AI assistant instance
universal_ai_assistant = UniversalAIAssistant()

# Export the universal AI assistant
__all__ = ['UniversalAIAssistant', 'universal_ai_assistant', 'ServiceQuery', 'AIResponse']
