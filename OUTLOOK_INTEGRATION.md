# Microsoft Outlook Integration for Fikiri Solutions

## 🔧 Technical Implementation

### Microsoft Graph API Setup
```python
# core/microsoft_outlook_integration.py
import requests
from datetime import datetime, timedelta
import json

class MicrosoftOutlookIntegration:
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
    
    def authenticate(self, auth_code=None, refresh_token=None):
        """Authenticate with Microsoft Graph API"""
        if refresh_token:
            # Use refresh token to get new access token
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
        else:
            # Initial authentication with auth code
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': 'https://fikirisolutions.com/auth/outlook/callback'
            }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data['expires_in']
            }
        return None
    
    def get_emails(self, folder='inbox', limit=50):
        """Fetch emails from Outlook"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/me/mailFolders/{folder}/messages"
        params = {
            '$top': limit,
            '$orderby': 'receivedDateTime desc',
            '$select': 'id,subject,from,receivedDateTime,body,hasAttachments'
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get('value', [])
        return []
    
    def parse_email_content(self, email):
        """Parse email content for landscaping business context"""
        subject = email.get('subject', '')
        body = email.get('body', {}).get('content', '')
        from_email = email.get('from', {}).get('emailAddress', {}).get('address', '')
        
        # Extract landscaping-specific information
        parsed_data = {
            'email_id': email.get('id'),
            'subject': subject,
            'from_email': from_email,
            'received_date': email.get('receivedDateTime'),
            'body': body,
            'has_attachments': email.get('hasAttachments', False)
        }
        
        # AI-powered content analysis
        parsed_data.update(self._analyze_landscaping_content(subject, body))
        
        return parsed_data
    
    def _analyze_landscaping_content(self, subject, body):
        """Analyze email content for landscaping business context"""
        content = f"{subject} {body}".lower()
        
        # Service type detection
        services = {
            'mowing': ['mow', 'lawn', 'grass', 'cutting'],
            'tree_trimming': ['tree', 'trim', 'prune', 'branch'],
            'landscaping': ['landscape', 'design', 'plant', 'garden'],
            'maintenance': ['maintain', 'cleanup', 'seasonal'],
            'irrigation': ['sprinkler', 'irrigation', 'water', 'system']
        }
        
        detected_services = []
        for service, keywords in services.items():
            if any(keyword in content for keyword in keywords):
                detected_services.append(service)
        
        # Urgency detection
        urgency_keywords = ['urgent', 'asap', 'emergency', 'immediately', 'today']
        is_urgent = any(keyword in content for keyword in urgency_keywords)
        
        # Address extraction (basic pattern matching)
        import re
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd)'
        addresses = re.findall(address_pattern, body, re.IGNORECASE)
        
        return {
            'detected_services': detected_services,
            'is_urgent': is_urgent,
            'addresses': addresses,
            'service_type': detected_services[0] if detected_services else 'general'
        }
    
    def send_reply(self, email_id, reply_content):
        """Send a reply to an email"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get original email to reply to
        original_email = self._get_email_by_id(email_id)
        if not original_email:
            return False
        
        reply_data = {
            'message': {
                'subject': f"Re: {original_email.get('subject', '')}",
                'body': {
                    'contentType': 'HTML',
                    'content': reply_content
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': original_email.get('from', {}).get('emailAddress', {}).get('address', '')
                        }
                    }
                ]
            }
        }
        
        url = f"{self.base_url}/me/sendMail"
        response = requests.post(url, headers=headers, json=reply_data)
        return response.status_code == 202
    
    def _get_email_by_id(self, email_id):
        """Get specific email by ID"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/me/messages/{email_id}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

## 🔐 Authentication Flow

### Step 1: OAuth2 Authorization
```python
def get_outlook_auth_url(client_id, redirect_uri):
    """Generate Microsoft OAuth2 authorization URL"""
    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': 'https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send',
        'response_mode': 'query'
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{auth_url}?{query_string}"
```

### Step 2: Token Exchange
```python
def exchange_code_for_token(auth_code, client_id, client_secret, redirect_uri):
    """Exchange authorization code for access token"""
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    response = requests.post(token_url, data=data)
    return response.json()
```

## 📊 CRM Integration

### Landscaping-Specific CRM Fields
```python
# core/landscaping_crm.py
class LandscapingCRM:
    def __init__(self):
        self.client_fields = [
            'name', 'email', 'phone', 'address',
            'service_type', 'property_size', 'frequency',
            'last_service_date', 'next_service_date',
            'special_requests', 'notes', 'status'
        ]
    
    def create_client_from_email(self, parsed_email):
        """Create CRM client record from parsed email"""
        client_data = {
            'name': self._extract_name_from_email(parsed_email['from_email']),
            'email': parsed_email['from_email'],
            'service_type': parsed_email['service_type'],
            'address': parsed_email['addresses'][0] if parsed_email['addresses'] else '',
            'status': 'new_inquiry',
            'source': 'email',
            'inquiry_date': parsed_email['received_date'],
            'notes': f"Initial inquiry: {parsed_email['subject']}"
        }
        
        return self._save_client(client_data)
    
    def _extract_name_from_email(self, email):
        """Extract name from email address"""
        # Basic implementation - could be enhanced with AI
        local_part = email.split('@')[0]
        return local_part.replace('.', ' ').replace('_', ' ').title()
```

## 🤖 AI Assistant Integration

### Landscaping-Specific AI Responses
```python
# core/landscaping_ai_assistant.py
class LandscapingAIAssistant:
    def __init__(self):
        self.service_templates = {
            'mowing': {
                'greeting': 'Thank you for your lawn mowing inquiry!',
                'pricing': 'Our lawn mowing service starts at $35 for small yards.',
                'scheduling': 'We typically schedule mowing services weekly or bi-weekly.',
                'follow_up': 'Would you like to schedule a consultation?'
            },
            'tree_trimming': {
                'greeting': 'Thank you for your tree trimming inquiry!',
                'pricing': 'Tree trimming services start at $150 depending on tree size.',
                'scheduling': 'We can provide a free estimate within 24 hours.',
                'follow_up': 'Would you like us to schedule an estimate visit?'
            }
        }
    
    def generate_response(self, parsed_email, client_info=None):
        """Generate AI response for landscaping inquiry"""
        service_type = parsed_email['service_type']
        template = self.service_templates.get(service_type, self.service_templates['mowing'])
        
        response = f"""
        {template['greeting']}
        
        {template['pricing']}
        
        {template['scheduling']}
        
        {template['follow_up']}
        
        Best regards,
        [Landscaping Business Name]
        """
        
        return response.strip()
```

## 🔄 Workflow Integration

### Complete Landscaping Workflow
```python
# core/landscaping_workflow.py
class LandscapingWorkflow:
    def __init__(self):
        self.outlook = MicrosoftOutlookIntegration()
        self.crm = LandscapingCRM()
        self.ai = LandscapingAIAssistant()
    
    def process_new_emails(self):
        """Main workflow for processing new emails"""
        # 1. Fetch new emails
        emails = self.outlook.get_emails()
        
        for email in emails:
            # 2. Parse email content
            parsed_email = self.outlook.parse_email_content(email)
            
            # 3. Create/update CRM record
            client = self.crm.create_client_from_email(parsed_email)
            
            # 4. Generate AI response
            ai_response = self.ai.generate_response(parsed_email, client)
            
            # 5. Send reply (if auto-reply enabled)
            if client.get('auto_reply_enabled', False):
                self.outlook.send_reply(email['id'], ai_response)
            
            # 6. Log activity
            self._log_activity(email, client, ai_response)
    
    def _log_activity(self, email, client, response):
        """Log the email processing activity"""
        activity = {
            'timestamp': datetime.now(),
            'email_id': email['id'],
            'client_id': client['id'],
            'action': 'email_processed',
            'service_type': client['service_type'],
            'response_sent': bool(response)
        }
        
        # Save to activity log
        self._save_activity(activity)
```

## 📱 Frontend Integration

### Outlook Connection UI
```typescript
// frontend/src/components/OutlookIntegration.tsx
import React, { useState } from 'react';
import { Button } from './ui/Button';

export const OutlookIntegration: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    
    try {
      // Redirect to Microsoft OAuth
      const authUrl = await fetch('/api/outlook/auth-url').then(r => r.text());
      window.location.href = authUrl;
    } catch (error) {
      console.error('Failed to initiate Outlook connection:', error);
    }
  };

  const handleDisconnect = async () => {
    try {
      await fetch('/api/outlook/disconnect', { method: 'POST' });
      setIsConnected(false);
    } catch (error) {
      console.error('Failed to disconnect Outlook:', error);
    }
  };

  return (
    <div className="fikiri-card p-6">
      <h3 className="text-lg font-semibold mb-4">Microsoft Outlook Integration</h3>
      
      {isConnected ? (
        <div className="space-y-4">
          <div className="flex items-center text-green-600">
            <CheckCircle className="w-5 h-5 mr-2" />
            <span>Outlook connected successfully</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium">Emails Processed:</span>
              <span className="ml-2">24 today</span>
            </div>
            <div>
              <span className="font-medium">New Leads:</span>
              <span className="ml-2">8 today</span>
            </div>
          </div>
          
          <Button onClick={handleDisconnect} variant="outline">
            Disconnect Outlook
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-gray-600">
            Connect your Microsoft Outlook account to automatically process 
            landscaping inquiries and create client records.
          </p>
          
          <Button 
            onClick={handleConnect} 
            disabled={isConnecting}
            className="w-full"
          >
            {isConnecting ? 'Connecting...' : 'Connect Outlook'}
          </Button>
        </div>
      )}
    </div>
  );
};
```

## 🚀 Deployment Configuration

### Environment Variables
```bash
# .env.production
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=your_tenant_id
OUTLOOK_REDIRECT_URI=https://fikirisolutions.com/auth/outlook/callback
```

### Flask Routes
```python
# app.py - Add these routes
@app.route('/api/outlook/auth-url', methods=['GET'])
def get_outlook_auth_url():
    auth_url = get_outlook_auth_url(
        client_id=os.getenv('MICROSOFT_CLIENT_ID'),
        redirect_uri=os.getenv('OUTLOOK_REDIRECT_URI')
    )
    return auth_url

@app.route('/auth/outlook/callback', methods=['GET'])
def outlook_callback():
    auth_code = request.args.get('code')
    if auth_code:
        # Exchange code for token
        token_data = exchange_code_for_token(
            auth_code,
            os.getenv('MICROSOFT_CLIENT_ID'),
            os.getenv('MICROSOFT_CLIENT_SECRET'),
            os.getenv('OUTLOOK_REDIRECT_URI')
        )
        
        # Save token to database
        save_outlook_token(token_data)
        
        return redirect('https://fikirisolutions.com/services?connected=outlook')
    
    return redirect('https://fikirisolutions.com/services?error=outlook_auth')
```

This implementation provides a complete foundation for integrating Microsoft Outlook with Fikiri Solutions for landscaping businesses. The system will automatically parse emails, create CRM records, and generate AI responses tailored to landscaping services.
