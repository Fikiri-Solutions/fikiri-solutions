# 🔌 Critical Integrations Implementation Plan

**Date:** January 2026  
**Priority:** High - These integrations unlock full business management capabilities

---

## 🎯 **Integration Priority Matrix**

| Integration | Priority | Impact | Effort | Revenue Impact | Timeline |
|------------|----------|--------|--------|----------------|----------|
| **Google Calendar** | 🔴 Critical | Very High | Medium | High | Week 1-2 |
| **Outlook Calendar** | 🔴 Critical | Very High | Medium | High | Week 1-2 |
| **Stripe Payments** | 🔴 Critical | Very High | Low | Very High | Week 2-3 |
| **HubSpot CRM** | 🟡 High | High | Medium | Medium | Week 3-4 |
| **SMS (Twilio)** | 🟡 High | Medium | Low | Medium | Week 4-5 |
| **Salesforce** | 🟢 Medium | High | High | Medium | Week 5-6 |
| **WhatsApp** | 🟢 Medium | Medium | Medium | Low | Week 6-7 |
| **QuickBooks** | 🟢 Low | Medium | High | Low | Week 8+ |
| **Xero** | 🟢 Low | Medium | High | Low | Week 8+ |

---

## 🔴 **Priority 1: Calendar Integrations (Weeks 1-2)**

### **Why Critical:**
- Unlocks appointment scheduling (needed for most industries)
- Enables reminders and notifications
- Required for "building a business" through the app

### **1. Google Calendar Integration**

**Implementation:**

```python
# core/integrations/calendar/google_calendar.py
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarClient:
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build('calendar', 'v3', credentials=credentials)
    
    def create_event(self, summary, start, end, description=None, attendees=None):
        """Create calendar event"""
        event = {
            'summary': summary,
            'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
            'description': description,
            'attendees': attendees or []
        }
        return self.service.events().insert(calendarId='primary', body=event).execute()
    
    def list_events(self, time_min=None, time_max=None, max_results=10):
        """List calendar events"""
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() if time_min else None,
            timeMax=time_max.isoformat() if time_max else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    
    def update_event(self, event_id, updates):
        """Update calendar event"""
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        event.update(updates)
        return self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    
    def delete_event(self, event_id):
        """Delete calendar event"""
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
```

**OAuth Scopes Needed:**
```
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/calendar.events
```

**Database Schema:**
```sql
CREATE TABLE calendar_integrations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    provider TEXT NOT NULL,  -- 'google', 'outlook'
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    calendar_id TEXT DEFAULT 'primary',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    integration_id INTEGER,
    external_event_id TEXT,  -- Google/Outlook event ID
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    location TEXT,
    attendees TEXT,  -- JSON array
    status TEXT DEFAULT 'confirmed',  -- confirmed, tentative, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (integration_id) REFERENCES calendar_integrations(id)
);
```

**API Endpoints:**
```python
# routes/calendar.py
@calendar_bp.route('/api/calendar/connect', methods=['POST'])
@jwt_required
def connect_calendar():
    """Connect Google/Outlook calendar"""
    provider = request.json.get('provider')  # 'google' or 'outlook'
    # OAuth flow
    pass

@calendar_bp.route('/api/calendar/events', methods=['GET'])
@jwt_required
def list_events():
    """List calendar events"""
    pass

@calendar_bp.route('/api/calendar/events', methods=['POST'])
@jwt_required
def create_event():
    """Create calendar event"""
    pass

@calendar_bp.route('/api/calendar/events/<event_id>', methods=['PUT'])
@jwt_required
def update_event():
    """Update calendar event"""
    pass

@calendar_bp.route('/api/calendar/events/<event_id>', methods=['DELETE'])
@jwt_required
def delete_event():
    """Delete calendar event"""
    pass
```

**Frontend:**
```typescript
// frontend/src/pages/Calendar.tsx
// Calendar view with Google/Outlook sync
// Create/edit/delete events
// View availability

// frontend/src/components/CalendarIntegration.tsx
// Connect Google/Outlook calendar
// OAuth flow
// Status display
```

**Time Estimate:** 1-2 weeks  
**Dependencies:** Google Calendar API enabled, OAuth credentials

---

### **2. Outlook Calendar Integration**

**Implementation:**

```python
# core/integrations/calendar/outlook_calendar.py
import requests
from datetime import datetime

class OutlookCalendarClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'https://graph.microsoft.com/v1.0'
    
    def create_event(self, subject, start, end, body=None, attendees=None):
        """Create calendar event"""
        event = {
            'subject': subject,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'UTC'
            },
            'body': {
                'contentType': 'HTML',
                'content': body or ''
            },
            'attendees': attendees or []
        }
        response = requests.post(
            f'{self.base_url}/me/events',
            headers={'Authorization': f'Bearer {self.access_token}'},
            json=event
        )
        return response.json()
    
    def list_events(self, start_date=None, end_date=None):
        """List calendar events"""
        params = {}
        if start_date:
            params['$filter'] = f"start/dateTime ge '{start_date.isoformat()}'"
        if end_date:
            params['$filter'] = f"{params.get('$filter', '')} and end/dateTime le '{end_date.isoformat()}'"
        
        response = requests.get(
            f'{self.base_url}/me/events',
            headers={'Authorization': f'Bearer {self.access_token}'},
            params=params
        )
        return response.json().get('value', [])
```

**OAuth Scopes Needed:**
```
Calendars.ReadWrite
Calendars.ReadWrite.Shared
```

**Time Estimate:** 1 week (can be done in parallel with Google Calendar)  
**Dependencies:** Microsoft Graph API, existing Outlook OAuth setup

---

## 🔴 **Priority 2: Payment Processing (Week 2-3)**

### **Why Critical:**
- Enables invoicing and payment collection
- Required for "building a business"
- High revenue impact (transaction fees)

### **Stripe Payments Integration**

**Current State:** Stripe is integrated for billing/subscriptions only

**What's Needed:** Full Stripe Payments integration

**Implementation:**

```python
# core/integrations/payments/stripe_payments.py
import stripe
from datetime import datetime

class StripePaymentsClient:
    def __init__(self):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    
    def create_invoice(self, customer_id, amount, currency='usd', description=None, line_items=None):
        """Create invoice"""
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=True,  # Auto-finalize
            collection_method='charge_automatically'
        )
        
        if line_items:
            for item in line_items:
                stripe.InvoiceItem.create(
                    customer=customer_id,
                    invoice=invoice.id,
                    amount=int(item['amount'] * 100),  # Convert to cents
                    currency=currency,
                    description=item.get('description')
                )
        
        invoice.finalize_invoice()
        invoice.send_invoice()
        return invoice
    
    def create_payment_intent(self, amount, currency='usd', customer_id=None, metadata=None):
        """Create payment intent for one-time payment"""
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency,
            customer=customer_id,
            metadata=metadata or {},
            automatic_payment_methods={'enabled': True}
        )
        return intent
    
    def create_payment_link(self, amount, currency='usd', description=None):
        """Create payment link (no customer needed)"""
        price = stripe.Price.create(
            unit_amount=int(amount * 100),
            currency=currency,
            product_data={'name': description or 'Payment'}
        )
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price.id, 'quantity': 1}],
            mode='payment',
            success_url=f"{os.getenv('FRONTEND_URL')}/payments/success",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/payments/cancel"
        )
        return session
    
    def get_payment_methods(self, customer_id):
        """Get customer payment methods"""
        return stripe.PaymentMethod.list(customer=customer_id, type='card')
    
    def charge_customer(self, customer_id, amount, currency='usd', description=None):
        """Charge customer's default payment method"""
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            customer=customer_id,
            description=description,
            confirm=True,
            off_session=True
        )
        return payment_intent
```

**Database Schema:**
```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    invoice_number TEXT UNIQUE,
    stripe_invoice_id TEXT,
    amount DECIMAL(10, 2),
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft',  -- draft, sent, paid, overdue, cancelled
    due_date DATE,
    paid_at TIMESTAMP,
    line_items TEXT,  -- JSON
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    invoice_id INTEGER,
    stripe_payment_intent_id TEXT,
    amount DECIMAL(10, 2),
    currency TEXT DEFAULT 'USD',
    status TEXT,  -- succeeded, pending, failed, refunded
    payment_method TEXT,  -- card, ach, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
```

**API Endpoints:**
```python
# routes/payments.py
@payments_bp.route('/api/payments/invoices', methods=['POST'])
@jwt_required
def create_invoice():
    """Create invoice"""
    pass

@payments_bp.route('/api/payments/invoices/<invoice_id>/send', methods=['POST'])
@jwt_required
def send_invoice():
    """Send invoice to customer"""
    pass

@payments_bp.route('/api/payments/payment-link', methods=['POST'])
@jwt_required
def create_payment_link():
    """Create payment link"""
    pass

@payments_bp.route('/api/payments/charge', methods=['POST'])
@jwt_required
def charge_customer():
    """Charge customer"""
    pass
```

**Time Estimate:** 1 week  
**Dependencies:** Stripe account (already have), Stripe API key

---

## 🟡 **Priority 3: CRM Integrations (Weeks 3-4)**

### **HubSpot CRM Integration**

**Implementation:**

```python
# core/integrations/crm/hubspot_client.py
import requests
from typing import Dict, List, Optional

class HubSpotCRMClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'https://api.hubapi.com'
    
    def create_contact(self, email, first_name=None, last_name=None, properties=None):
        """Create contact in HubSpot"""
        contact_data = {
            'properties': {
                'email': email,
                'firstname': first_name,
                'lastname': last_name,
                **(properties or {})
            }
        }
        response = requests.post(
            f'{self.base_url}/crm/v3/objects/contacts',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            },
            json=contact_data
        )
        return response.json()
    
    def create_deal(self, deal_name, amount, pipeline_id, stage_id, associated_contact_id=None):
        """Create deal in HubSpot"""
        deal_data = {
            'properties': {
                'dealname': deal_name,
                'amount': str(amount),
                'pipeline': pipeline_id,
                'dealstage': stage_id
            },
            'associations': []
        }
        if associated_contact_id:
            deal_data['associations'].append({
                'to': {'id': associated_contact_id},
                'types': [{'associationCategory': 'HUBSPOT_DEFINED', 'associationTypeId': 3}]
            })
        
        response = requests.post(
            f'{self.base_url}/crm/v3/objects/deals',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            },
            json=deal_data
        )
        return response.json()
    
    def sync_contact(self, fikiri_lead_id, hubspot_contact_id=None):
        """Sync Fikiri lead to HubSpot contact"""
        # Get lead from Fikiri
        lead = get_lead_from_fikiri(fikiri_lead_id)
        
        if hubspot_contact_id:
            # Update existing contact
            return self.update_contact(hubspot_contact_id, lead)
        else:
            # Create new contact
            return self.create_contact(
                email=lead['email'],
                first_name=lead.get('name', '').split()[0] if lead.get('name') else None,
                last_name=' '.join(lead.get('name', '').split()[1:]) if lead.get('name') else None,
                properties=self.map_fikiri_to_hubspot(lead)
            )
    
    def sync_deal(self, fikiri_lead_id, deal_amount, hubspot_deal_id=None):
        """Sync Fikiri lead to HubSpot deal"""
        # Implementation
        pass
```

**OAuth Flow:**
```
1. User clicks "Connect HubSpot"
2. Redirect to HubSpot OAuth
3. User authorizes
4. Receive access_token + refresh_token
5. Store tokens
6. Enable sync
```

**Database Schema:**
```sql
CREATE TABLE crm_integrations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    provider TEXT NOT NULL,  -- 'hubspot', 'salesforce'
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    sync_direction TEXT DEFAULT 'bidirectional',  -- 'fikiri_to_crm', 'crm_to_fikiri', 'bidirectional'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE crm_sync_mappings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    integration_id INTEGER NOT NULL,
    fikiri_entity_type TEXT,  -- 'lead', 'contact'
    fikiri_entity_id INTEGER,
    crm_entity_type TEXT,  -- 'contact', 'deal'
    crm_entity_id TEXT,  -- External ID
    last_synced_at TIMESTAMP,
    sync_status TEXT,  -- 'synced', 'pending', 'error'
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (integration_id) REFERENCES crm_integrations(id)
);
```

**Time Estimate:** 1-2 weeks  
**Dependencies:** HubSpot developer account, OAuth app setup

---

## 🟡 **Priority 4: SMS Integration (Week 4-5)**

### **Twilio SMS Integration**

**Implementation:**

```python
# core/integrations/communication/twilio_client.py
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class TwilioSMSClient:
    def __init__(self):
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.client = Client(account_sid, auth_token)
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    def send_sms(self, to_number, message, from_number=None):
        """Send SMS"""
        try:
            message = self.client.messages.create(
                body=message,
                from_=from_number or self.from_number,
                to=to_number
            )
            return {
                'success': True,
                'message_sid': message.sid,
                'status': message.status
            }
        except TwilioRestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_bulk_sms(self, recipients, message_template, variables=None):
        """Send SMS to multiple recipients"""
        results = []
        for recipient in recipients:
            # Replace variables in template
            message = message_template
            if variables:
                for key, value in variables.items():
                    message = message.replace(f'{{{{{key}}}}}', str(value))
            
            result = self.send_sms(recipient['phone'], message)
            results.append({
                'recipient': recipient,
                'result': result
            })
        return results
```

**Database Schema:**
```sql
CREATE TABLE sms_integrations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    provider TEXT DEFAULT 'twilio',
    account_sid TEXT,
    auth_token_encrypted TEXT,  -- Encrypted
    phone_number TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE sms_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    to_number TEXT NOT NULL,
    from_number TEXT,
    message TEXT NOT NULL,
    status TEXT,  -- sent, delivered, failed
    twilio_sid TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);
```

**Time Estimate:** 3-5 days  
**Dependencies:** Twilio account, phone number

---

## 🟢 **Priority 5: Salesforce (Week 5-6)**

**Similar to HubSpot but more complex:**
- More API endpoints
- Custom objects support
- More complex OAuth flow
- Higher implementation effort

**Time Estimate:** 1-2 weeks  
**Dependencies:** Salesforce developer account, OAuth app setup

---

## 🟢 **Priority 6: WhatsApp (Week 6-7)**

**Implementation Options:**
1. **WhatsApp Business API** (Official, requires approval)
2. **Twilio WhatsApp** (Easier, uses Twilio)

**Recommendation:** Start with Twilio WhatsApp (easier, faster)

**Time Estimate:** 1 week  
**Dependencies:** Twilio account (can reuse from SMS)

---

## 🟢 **Priority 7: Accounting (Week 8+)**

### **QuickBooks Integration**

**Complexity:** High (many API endpoints, complex data model)

**Time Estimate:** 2-3 weeks  
**Dependencies:** QuickBooks developer account, OAuth setup

**Recommendation:** Lower priority unless specific customer demand

---

## 🚀 **Recommended Implementation Order**

### **Weeks 1-2: Calendar (Critical)**
- [ ] Google Calendar integration
- [ ] Outlook Calendar integration
- [ ] Calendar sync
- [ ] Event creation/updates

**Result:** Appointment scheduling unlocked

---

### **Week 2-3: Payments (Critical)**
- [ ] Stripe Payments integration
- [ ] Invoice generation
- [ ] Payment links
- [ ] Payment tracking

**Result:** Invoicing and payments unlocked

---

### **Weeks 3-4: CRM (High Priority)**
- [ ] HubSpot integration
- [ ] Two-way sync
- [ ] Contact/Deal mapping

**Result:** CRM integration for existing users

---

### **Week 4-5: SMS (High Priority)**
- [ ] Twilio integration
- [ ] SMS sending
- [ ] Bulk SMS
- [ ] SMS in workflows

**Result:** SMS reminders and notifications

---

### **Weeks 5-6: Salesforce (Medium)**
- [ ] Salesforce integration
- [ ] Two-way sync
- [ ] Custom objects support

**Result:** Enterprise CRM support

---

### **Week 6-7: WhatsApp (Medium)**
- [ ] Twilio WhatsApp
- [ ] WhatsApp messaging
- [ ] WhatsApp in workflows

**Result:** Multi-channel communication

---

### **Week 8+: Accounting (Low Priority)**
- [ ] QuickBooks integration
- [ ] Xero integration
- [ ] Financial sync

**Result:** Accounting integration (if needed)

---

## 💰 **Cost Analysis**

| Integration | Setup Cost | Per-Use Cost | Monthly Cost (Est.) |
|------------|------------|--------------|---------------------|
| Google Calendar | Free | Free | $0 |
| Outlook Calendar | Free | Free | $0 |
| Stripe Payments | Free | 2.9% + $0.30 | Transaction-based |
| HubSpot CRM | Free | Free (up to limit) | $0-50/user |
| Twilio SMS | Free | $0.0075/SMS | ~$0.01 per message |
| Salesforce | Free | Free (dev) | $0-150/user |
| WhatsApp (Twilio) | Free | $0.005/message | ~$0.01 per message |
| QuickBooks | Free | Free (API) | $0 |

**Total Monthly Cost:** Mostly transaction-based (Stripe fees, SMS costs)

---

## ✅ **Quick Wins (Can Start Immediately)**

1. **Stripe Payments** (1 week) - Already have Stripe, just need to extend
2. **Google Calendar** (1 week) - Similar to Gmail OAuth
3. **Twilio SMS** (3-5 days) - Simple API

**These 3 integrations unlock:**
- ✅ Appointment scheduling
- ✅ Invoicing and payments
- ✅ SMS reminders

**Total Time:** 2-3 weeks  
**Impact:** Very High

---

## 🎯 **Next Steps**

1. **This Week:**
   - Start Google Calendar integration (reuse Gmail OAuth pattern)
   - Start Stripe Payments extension (already have Stripe)

2. **Next Week:**
   - Complete Calendar integrations
   - Complete Stripe Payments
   - Start Twilio SMS

3. **Week 3:**
   - Start HubSpot CRM integration
   - Test all integrations

**Result:** Core integrations ready in 3 weeks

---

**Status:** ✅ **Ready to Implement**

Should I start with Google Calendar integration? It's the highest priority and unlocks appointment scheduling.
