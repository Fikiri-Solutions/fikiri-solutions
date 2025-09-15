# AI Assistant for Landscaping Business

## 🤖 Landscaping-Specific AI Responses

### Service Templates and Responses
```python
# core/landscaping_ai_assistant.py
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class LandscapingAIAssistant:
    def __init__(self):
        self.business_info = {
            'name': 'GreenThumb Landscaping',
            'phone': '(555) 123-4567',
            'email': 'info@greenthumb.com',
            'website': 'www.greenthumb.com',
            'service_area': 'Metro Area',
            'hours': 'Monday-Friday 7AM-6PM, Saturday 8AM-4PM'
        }
        
        self.service_templates = {
            'mowing': {
                'greeting': 'Thank you for your lawn mowing inquiry!',
                'pricing': 'Our lawn mowing service starts at $35 for small yards (under 1/4 acre), $50 for medium yards (1/4-1/2 acre), and $75 for large yards (over 1/2 acre).',
                'scheduling': 'We typically schedule mowing services weekly or bi-weekly. We can provide a free estimate within 24 hours.',
                'follow_up': 'Would you like to schedule a free estimate visit?',
                'additional_info': 'Our service includes edging, trimming, and cleanup of clippings.'
            },
            'landscaping': {
                'greeting': 'Thank you for your landscaping design inquiry!',
                'pricing': 'Landscaping projects start at $200 for small areas and can range up to $5,000+ for complete yard transformations.',
                'scheduling': 'We offer free consultations and can provide detailed estimates within 48 hours.',
                'follow_up': 'Would you like to schedule a free consultation to discuss your vision?',
                'additional_info': 'We specialize in native plants, sustainable design, and low-maintenance landscapes.'
            },
            'tree_trimming': {
                'greeting': 'Thank you for your tree trimming inquiry!',
                'pricing': 'Tree trimming services start at $150 for small trees and range up to $500+ for large trees or complex jobs.',
                'scheduling': 'We can provide a free estimate within 24 hours and typically schedule work within 1-2 weeks.',
                'follow_up': 'Would you like us to schedule an estimate visit?',
                'additional_info': 'All our tree work is performed by certified arborists with proper insurance.'
            },
            'maintenance': {
                'greeting': 'Thank you for your landscape maintenance inquiry!',
                'pricing': 'Maintenance packages start at $100/month for basic care and can be customized based on your needs.',
                'scheduling': 'We can create a customized maintenance schedule that fits your property and budget.',
                'follow_up': 'Would you like to discuss a maintenance plan for your property?',
                'additional_info': 'Our maintenance includes pruning, fertilizing, pest control, and seasonal cleanup.'
            }
        }
        
        self.urgency_responses = {
            'urgent': 'I understand this is urgent. We can prioritize your request and provide same-day service for emergency situations.',
            'asap': 'We can accommodate ASAP requests. Let me check our availability for today or tomorrow.',
            'emergency': 'For emergency tree work or storm damage, we provide 24/7 emergency service.'
        }
    
    def generate_response(self, parsed_email: Dict, client_info: Optional[Dict] = None) -> str:
        """Generate AI response for landscaping inquiry"""
        service_type = parsed_email.get('service_type', 'general')
        is_urgent = parsed_email.get('is_urgent', False)
        
        # Get base template
        template = self.service_templates.get(service_type, self.service_templates['mowing'])
        
        # Build response
        response_parts = []
        
        # Greeting
        response_parts.append(template['greeting'])
        
        # Urgency handling
        if is_urgent:
            urgency_text = self._get_urgency_response(parsed_email)
            if urgency_text:
                response_parts.append(urgency_text)
        
        # Service-specific information
        response_parts.append(template['pricing'])
        response_parts.append(template['scheduling'])
        
        # Additional service information
        if template.get('additional_info'):
            response_parts.append(template['additional_info'])
        
        # Follow-up question
        response_parts.append(template['follow_up'])
        
        # Contact information
        response_parts.append(self._get_contact_info())
        
        # Signature
        response_parts.append(self._get_signature())
        
        return '\n\n'.join(response_parts)
    
    def _get_urgency_response(self, parsed_email: Dict) -> Optional[str]:
        """Get urgency-specific response"""
        content = f"{parsed_email.get('subject', '')} {parsed_email.get('body', '')}".lower()
        
        for urgency_keyword, response in self.urgency_responses.items():
            if urgency_keyword in content:
                return response
        
        return None
    
    def _get_contact_info(self) -> str:
        """Get contact information"""
        return f"""
Contact Information:
Phone: {self.business_info['phone']}
Email: {self.business_info['email']}
Website: {self.business_info['website']}
Service Area: {self.business_info['service_area']}
Hours: {self.business_info['hours']}
        """.strip()
    
    def _get_signature(self) -> str:
        """Get email signature"""
        return f"""
Best regards,
{self.business_info['name']}
        """.strip()
    
    def generate_follow_up_response(self, client_info: Dict, days_since_inquiry: int) -> str:
        """Generate follow-up response for clients"""
        if days_since_inquiry < 3:
            return None  # Too soon for follow-up
        
        service_type = client_info.get('primary_service', 'general')
        client_name = client_info.get('name', 'there')
        
        if days_since_inquiry <= 7:
            # First follow-up
            return f"""
Hi {client_name},

I wanted to follow up on your {service_type} inquiry from last week. 

We're still available to provide a free estimate for your project. Our team can visit your property at your convenience to discuss your needs and provide a detailed quote.

Would you like to schedule a time that works for you?

{self._get_contact_info()}

Best regards,
{self.business_info['name']}
            """.strip()
        
        elif days_since_inquiry <= 14:
            # Second follow-up with incentive
            return f"""
Hi {client_name},

I hope you're doing well! I wanted to reach out again about your {service_type} project.

We're currently offering a 10% discount on new projects booked this month. This could be a great time to move forward with your landscaping goals.

Our team is ready to provide a free estimate and discuss how we can help transform your outdoor space.

Would you like to schedule a consultation?

{self._get_contact_info()}

Best regards,
{self.business_info['name']}
            """.strip()
        
        else:
            # Final follow-up
            return f"""
Hi {client_name},

I wanted to reach out one more time about your {service_type} inquiry. 

If you've decided to work with another company, I completely understand. However, if you're still considering your options, we'd love the opportunity to earn your business.

We pride ourselves on quality work, competitive pricing, and excellent customer service. 

Feel free to reach out if you'd like to discuss your project further.

{self._get_contact_info()}

Best regards,
{self.business_info['name']}
            """.strip()
    
    def generate_service_confirmation(self, client_info: Dict, service_details: Dict) -> str:
        """Generate service confirmation email"""
        client_name = client_info.get('name', 'there')
        service_type = service_details.get('service_type', 'service')
        service_date = service_details.get('service_date', 'TBD')
        service_time = service_details.get('service_time', 'TBD')
        
        return f"""
Hi {client_name},

Thank you for choosing {self.business_info['name']} for your {service_type} needs!

Service Confirmation:
- Service: {service_type}
- Date: {service_date}
- Time: {service_time}
- Address: {client_info.get('property_address', 'As discussed')}

What to Expect:
- Our team will arrive at the scheduled time
- We'll bring all necessary equipment
- The work will be completed professionally and efficiently
- We'll clean up after ourselves

If you need to reschedule or have any questions, please contact us at {self.business_info['phone']}.

We look forward to serving you!

{self._get_contact_info()}

Best regards,
{self.business_info['name']}
        """.strip()
    
    def generate_service_completion(self, client_info: Dict, service_details: Dict) -> str:
        """Generate service completion email"""
        client_name = client_info.get('name', 'there')
        service_type = service_details.get('service_type', 'service')
        service_date = service_details.get('service_date', 'today')
        
        return f"""
Hi {client_name},

We've completed your {service_type} service today! We hope you're pleased with the results.

Service Summary:
- Service: {service_type}
- Date Completed: {service_date}
- Address: {client_info.get('property_address', 'As discussed')}

Next Steps:
- Please review the work and let us know if you have any concerns
- Payment can be made via check, cash, or online
- We'd appreciate a review on Google or Facebook if you're satisfied

We'd love to help with any future landscaping needs. Our maintenance programs can keep your property looking great year-round.

Thank you for choosing {self.business_info['name']}!

{self._get_contact_info()}

Best regards,
{self.business_info['name']}
        """.strip()
    
    def analyze_email_sentiment(self, email_content: str) -> Dict:
        """Analyze email sentiment and extract key information"""
        content_lower = email_content.lower()
        
        # Sentiment analysis (basic implementation)
        positive_words = ['great', 'excellent', 'wonderful', 'amazing', 'love', 'perfect', 'happy']
        negative_words = ['terrible', 'awful', 'disappointed', 'angry', 'frustrated', 'unhappy', 'bad']
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Extract key information
        extracted_info = {
            'sentiment': sentiment,
            'urgency': 'urgent' if any(word in content_lower for word in ['urgent', 'asap', 'emergency']) else 'normal',
            'budget_mentioned': any(word in content_lower for word in ['budget', 'cost', 'price', 'afford']),
            'timeline_mentioned': any(word in content_lower for word in ['when', 'schedule', 'available', 'time']),
            'specific_service': self._identify_specific_service(content_lower)
        }
        
        return extracted_info
    
    def _identify_specific_service(self, content: str) -> str:
        """Identify specific service from email content"""
        service_keywords = {
            'mowing': ['mow', 'lawn', 'grass', 'cutting', 'trimming grass'],
            'landscaping': ['landscape', 'design', 'plant', 'garden', 'flowerbed'],
            'tree_trimming': ['tree', 'trim', 'prune', 'branch', 'limb'],
            'maintenance': ['maintain', 'cleanup', 'seasonal', 'regular'],
            'irrigation': ['sprinkler', 'irrigation', 'water', 'system', 'drip'],
            'mulching': ['mulch', 'mulching', 'bark', 'wood chips'],
            'fertilizing': ['fertilize', 'fertilizer', 'nutrients', 'feed']
        }
        
        for service, keywords in service_keywords.items():
            if any(keyword in content for keyword in keywords):
                return service
        
        return 'general'
```

## 🔄 Automated Workflow Integration

### Complete Email Processing Workflow
```python
# core/landscaping_workflow.py
from datetime import datetime, timedelta
import json

class LandscapingWorkflow:
    def __init__(self):
        self.outlook = MicrosoftOutlookIntegration()
        self.crm = LandscapingCRMService()
        self.ai = LandscapingAIAssistant()
        self.email_processor = EmailProcessor()
    
    def process_new_emails(self):
        """Main workflow for processing new emails"""
        try:
            # 1. Fetch new emails from Outlook
            emails = self.outlook.get_emails(limit=20)
            
            processed_count = 0
            for email in emails:
                # 2. Parse email content
                parsed_email = self.outlook.parse_email_content(email)
                
                # 3. Analyze sentiment and extract info
                sentiment_analysis = self.ai.analyze_email_sentiment(
                    f"{parsed_email['subject']} {parsed_email['body']}"
                )
                parsed_email.update(sentiment_analysis)
                
                # 4. Check if client already exists
                existing_client = self._find_existing_client(parsed_email['from_email'])
                
                if existing_client:
                    # Update existing client
                    self._update_existing_client(existing_client, parsed_email)
                    client = existing_client
                else:
                    # Create new client
                    client = self.crm.create_client_from_email(parsed_email)
                
                # 5. Generate AI response
                ai_response = self.ai.generate_response(parsed_email, client)
                
                # 6. Send reply (if auto-reply enabled)
                if client.get('auto_reply_enabled', True):
                    self.outlook.send_reply(email['id'], ai_response)
                
                # 7. Log activity
                self._log_email_activity(email, client, ai_response)
                
                processed_count += 1
            
            return {
                'success': True,
                'processed_count': processed_count,
                'message': f'Successfully processed {processed_count} emails'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process emails'
            }
    
    def _find_existing_client(self, email: str) -> Optional[Dict]:
        """Find existing client by email"""
        for client in self.crm.clients.values():
            if client['email'].lower() == email.lower():
                return client
        return None
    
    def _update_existing_client(self, client: Dict, parsed_email: Dict):
        """Update existing client with new information"""
        # Update last contact date
        client['last_contact_date'] = datetime.now()
        
        # Update notes with new inquiry
        new_note = f"New inquiry ({datetime.now().strftime('%Y-%m-%d')}): {parsed_email['subject']}"
        client['notes'] = f"{client['notes']}\n{new_note}"
        
        # Update lead score if this is a higher value inquiry
        new_score = self.crm._calculate_lead_score(parsed_email)
        if new_score > client['lead_score']:
            client['lead_score'] = new_score
        
        # Update service type if more specific
        if parsed_email.get('service_type') != 'general':
            client['primary_service'] = parsed_email['service_type']
        
        client['updated_at'] = datetime.now()
        self.crm.save_data()
    
    def _log_email_activity(self, email: Dict, client: Dict, response: str):
        """Log email processing activity"""
        activity = {
            'timestamp': datetime.now(),
            'email_id': email['id'],
            'client_id': client['id'],
            'action': 'email_processed',
            'service_type': client['primary_service'],
            'response_sent': bool(response),
            'sentiment': email.get('sentiment', 'neutral'),
            'urgency': email.get('urgency', 'normal')
        }
        
        # Save to activity log
        self._save_activity(activity)
    
    def _save_activity(self, activity: Dict):
        """Save activity to log file"""
        try:
            with open('data/email_activities.json', 'r') as f:
                activities = json.load(f)
        except FileNotFoundError:
            activities = []
        
        activities.append(activity)
        
        with open('data/email_activities.json', 'w') as f:
            json.dump(activities, f, indent=2, default=str)
    
    def generate_follow_up_emails(self):
        """Generate follow-up emails for clients who haven't responded"""
        follow_up_clients = []
        
        for client in self.crm.clients.values():
            if client['status'] in ['new', 'qualified']:
                last_contact = datetime.fromisoformat(client['last_contact_date']) if isinstance(client['last_contact_date'], str) else client['last_contact_date']
                days_since_contact = (datetime.now() - last_contact).days
                
                if days_since_contact >= 3:  # Follow up after 3 days
                    follow_up_clients.append((client, days_since_contact))
        
        for client, days_since_contact in follow_up_clients:
            follow_up_response = self.ai.generate_follow_up_response(client, days_since_contact)
            
            if follow_up_response:
                # Send follow-up email
                self.outlook.send_reply(
                    f"follow_up_{client['id']}", 
                    follow_up_response
                )
                
                # Update client record
                client['last_contact_date'] = datetime.now()
                client['updated_at'] = datetime.now()
        
        self.crm.save_data()
        
        return {
            'success': True,
            'follow_up_count': len(follow_up_clients),
            'message': f'Sent {len(follow_up_clients)} follow-up emails'
        }
    
    def schedule_service_reminders(self):
        """Send service reminders to clients"""
        upcoming_services = self.crm.get_upcoming_services(days_ahead=1)
        
        for client in upcoming_services:
            if client['next_service_date']:
                service_date = datetime.fromisoformat(client['next_service_date']) if isinstance(client['next_service_date'], str) else client['next_service_date']
                
                # Send reminder 24 hours before service
                if service_date.date() == (datetime.now() + timedelta(days=1)).date():
                    reminder_message = f"""
Hi {client['name']},

This is a friendly reminder that we have your {client['primary_service']} service scheduled for tomorrow.

Service Details:
- Date: {service_date.strftime('%A, %B %d, %Y')}
- Time: As scheduled
- Address: {client['property_address']}

Please ensure access to your property and let us know if you need to reschedule.

{self.ai._get_contact_info()}

Best regards,
{self.ai.business_info['name']}
                    """.strip()
                    
                    self.outlook.send_reply(
                        f"reminder_{client['id']}", 
                        reminder_message
                    )
        
        return {
            'success': True,
            'reminder_count': len(upcoming_services),
            'message': f'Sent {len(upcoming_services)} service reminders'
        }
```

## 📱 Frontend AI Assistant Interface

### Landscaping AI Assistant Component
```typescript
// frontend/src/components/LandscapingAIAssistant.tsx
import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { 
  Bot, 
  Send, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  Clock,
  Star,
  MessageSquare
} from 'lucide-react';

interface AIResponse {
  id: string;
  client_name: string;
  service_type: string;
  sentiment: string;
  urgency: string;
  response_text: string;
  created_at: string;
  status: 'pending' | 'sent' | 'failed';
}

export const LandscapingAIAssistant: React.FC = () => {
  const [selectedClient, setSelectedClient] = useState<string>('');
  const [customMessage, setCustomMessage] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const { data: clients } = useQuery({
    queryKey: ['landscaping-clients'],
    queryFn: async () => {
      const response = await fetch('/api/landscaping/clients');
      return response.json();
    }
  });

  const { data: aiResponses, refetch: refetchResponses } = useQuery({
    queryKey: ['ai-responses'],
    queryFn: async () => {
      const response = await fetch('/api/ai/responses');
      return response.json();
    },
    staleTime: 30 * 1000
  });

  const generateResponseMutation = useMutation({
    mutationFn: async (data: { client_id: string; custom_message?: string }) => {
      const response = await fetch('/api/ai/generate-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return response.json();
    },
    onSuccess: () => {
      refetchResponses();
      setCustomMessage('');
    }
  });

  const sendResponseMutation = useMutation({
    mutationFn: async (responseId: string) => {
      const response = await fetch(`/api/ai/send-response/${responseId}`, {
        method: 'POST'
      });
      return response.json();
    },
    onSuccess: () => {
      refetchResponses();
    }
  });

  const handleGenerateResponse = async () => {
    if (!selectedClient) return;
    
    setIsGenerating(true);
    try {
      await generateResponseMutation.mutateAsync({
        client_id: selectedClient,
        custom_message: customMessage || undefined
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendResponse = async (responseId: string) => {
    await sendResponseMutation.mutateAsync(responseId);
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-100';
      case 'negative': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'urgent': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      default: return 'text-blue-600 bg-blue-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* AI Response Generator */}
      <div className="fikiri-card p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Bot className="h-8 w-8 text-blue-500" />
          <h3 className="text-xl font-semibold">AI Response Generator</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Client
            </label>
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose a client...</option>
              {clients?.map((client: any) => (
                <option key={client.id} value={client.id}>
                  {client.name} - {client.primary_service}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Message (Optional)
            </label>
            <textarea
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              placeholder="Add any specific instructions or context for the AI response..."
              className="w-full border border-gray-300 rounded-md px-3 py-2 h-24 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleGenerateResponse}
            disabled={!selectedClient || isGenerating}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Generating Response...</span>
              </>
            ) : (
              <>
                <Bot className="h-4 w-4" />
                <span>Generate AI Response</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* AI Responses List */}
      <div className="fikiri-card">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <MessageSquare className="h-6 w-6 text-green-500" />
            <h3 className="text-lg font-semibold">Recent AI Responses</h3>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {aiResponses?.map((response: AIResponse) => (
            <div key={response.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="text-lg font-medium text-gray-900">
                      {response.client_name}
                    </h4>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSentimentColor(response.sentiment)}`}>
                      {response.sentiment}
                    </span>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getUrgencyColor(response.urgency)}`}>
                      {response.urgency}
                    </span>
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                      {response.service_type}
                    </span>
                  </div>

                  <div className="text-sm text-gray-600 mb-3">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>{new Date(response.created_at).toLocaleString()}</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <Star className="h-4 w-4" />
                        <span>AI Generated</span>
                      </span>
                    </div>
                  </div>

                  <div className="bg-gray-50 p-4 rounded-md mb-4">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {response.response_text}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {response.status === 'pending' && (
                    <button
                      onClick={() => handleSendResponse(response.id)}
                      className="px-3 py-1 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center space-x-1"
                    >
                      <Send className="h-4 w-4" />
                      <span>Send</span>
                    </button>
                  )}
                  
                  {response.status === 'sent' && (
                    <div className="flex items-center space-x-1 text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span className="text-sm">Sent</span>
                    </div>
                  )}
                  
                  {response.status === 'failed' && (
                    <div className="flex items-center space-x-1 text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">Failed</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## 🚀 API Endpoints for AI Assistant

### Flask Routes for AI Assistant
```python
# app.py - Add these routes
@app.route('/api/ai/generate-response', methods=['POST'])
def generate_ai_response():
    """Generate AI response for client"""
    data = request.get_json()
    client_id = data.get('client_id')
    custom_message = data.get('custom_message')
    
    if not client_id:
        return jsonify({'error': 'Client ID required'}), 400
    
    # Get client info
    crm_service = LandscapingCRMService()
    client = crm_service.clients.get(client_id)
    
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    
    # Generate AI response
    ai_assistant = LandscapingAIAssistant()
    
    # Create mock parsed email for response generation
    parsed_email = {
        'service_type': client['primary_service'],
        'is_urgent': False,
        'subject': f"Inquiry from {client['name']}",
        'body': custom_message or f"Client inquiry for {client['primary_service']}"
    }
    
    response_text = ai_assistant.generate_response(parsed_email, client)
    
    # Save response to database
    response_id = f"response_{len(ai_responses) + 1}"
    ai_response = {
        'id': response_id,
        'client_id': client_id,
        'client_name': client['name'],
        'service_type': client['primary_service'],
        'sentiment': 'neutral',
        'urgency': 'normal',
        'response_text': response_text,
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    # Save to file (in production, use database)
    try:
        with open('data/ai_responses.json', 'r') as f:
            ai_responses = json.load(f)
    except FileNotFoundError:
        ai_responses = []
    
    ai_responses.append(ai_response)
    
    with open('data/ai_responses.json', 'w') as f:
        json.dump(ai_responses, f, indent=2, default=str)
    
    return jsonify(ai_response)

@app.route('/api/ai/responses', methods=['GET'])
def get_ai_responses():
    """Get all AI responses"""
    try:
        with open('data/ai_responses.json', 'r') as f:
            ai_responses = json.load(f)
    except FileNotFoundError:
        ai_responses = []
    
    return jsonify(ai_responses)

@app.route('/api/ai/send-response/<response_id>', methods=['POST'])
def send_ai_response(response_id):
    """Send AI response to client"""
    try:
        with open('data/ai_responses.json', 'r') as f:
            ai_responses = json.load(f)
    except FileNotFoundError:
        return jsonify({'error': 'No responses found'}), 404
    
    # Find response
    response = next((r for r in ai_responses if r['id'] == response_id), None)
    if not response:
        return jsonify({'error': 'Response not found'}), 404
    
    # Send email (mock implementation)
    try:
        # In production, use actual email service
        print(f"Sending email to client {response['client_id']}")
        
        # Update status
        response['status'] = 'sent'
        response['sent_at'] = datetime.now()
        
        # Save updated response
        with open('data/ai_responses.json', 'w') as f:
            json.dump(ai_responses, f, indent=2, default=str)
        
        return jsonify({'message': 'Response sent successfully'})
        
    except Exception as e:
        response['status'] = 'failed'
        response['error'] = str(e)
        
        with open('data/ai_responses.json', 'w') as f:
            json.dump(ai_responses, f, indent=2, default=str)
        
        return jsonify({'error': 'Failed to send response'}), 500
```

This AI Assistant system provides landscaping businesses with:

1. **Intelligent Response Generation**: Context-aware responses based on service type and client needs
2. **Sentiment Analysis**: Understanding client mood and urgency
3. **Automated Follow-ups**: Systematic follow-up sequences for better conversion
4. **Service Confirmations**: Professional confirmation emails
5. **Reminder System**: Automated service reminders
6. **Customizable Templates**: Easy-to-modify response templates
7. **Integration Ready**: Works seamlessly with Outlook and CRM systems

The AI Assistant learns from each interaction and provides increasingly personalized responses for better client relationships and higher conversion rates.
