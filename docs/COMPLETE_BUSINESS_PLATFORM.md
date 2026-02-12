# 🏢 Complete Business Platform: Core Features Implementation

**Date:** January 2026  
**Goal:** Build a complete business management platform where users can run their entire business

---

## 🎯 **Core Business Features Needed**

### **Missing Features:**
1. ✅ Appointment scheduling (with calendar sync)
2. ✅ Quote/invoice generation
3. ✅ Payment processing (accept payments)
4. ✅ Customer portal
5. ✅ Service management (work orders, job tracking)
6. ✅ Team management
7. ✅ Advanced reporting

---

## 🏗️ **Architecture: Unified Business Platform**

### **Core Principle:**
All features use the **flexible entity system** + **AI guidance** + **integrations**

---

## 1. 📅 **Appointment Scheduling (Weeks 1-2)**

### **What It Does:**
- Create/manage appointments
- Sync with Google/Outlook Calendar
- Send reminders (email + SMS)
- Check availability
- Handle cancellations/rescheduling

### **Implementation:**

#### **Database Schema:**
```sql
CREATE TABLE appointments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    appointment_type TEXT,  -- consultation, service, follow_up, etc.
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP,
    duration_minutes INTEGER,
    location TEXT,
    status TEXT DEFAULT 'scheduled',  -- scheduled, confirmed, completed, canceled, no_show
    calendar_event_id TEXT,  -- Google/Outlook event ID
    calendar_provider TEXT,  -- google, outlook
    reminder_sent_24h BOOLEAN DEFAULT 0,
    reminder_sent_2h BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE INDEX idx_appointments_user ON appointments(user_id);
CREATE INDEX idx_appointments_starts_at ON appointments(starts_at);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_contact ON appointments(contact_id);
```

#### **Backend Implementation:**
```python
# core/platform/appointments/appointment_manager.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from core.integrations.calendar.google_calendar import GoogleCalendarClient
from core.integrations.calendar.outlook_calendar import OutlookCalendarClient

class AppointmentManager:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.calendar_client = self._get_calendar_client()
    
    def create_appointment(self, contact_id: int, title: str, starts_at: datetime, 
                          duration_minutes: int = 60, description: str = None,
                          location: str = None, sync_to_calendar: bool = True) -> Dict:
        """Create appointment with optional calendar sync"""
        # 1. Create in database
        appointment_id = db_optimizer.execute_query(
            """INSERT INTO appointments 
               (user_id, contact_id, title, description, starts_at, ends_at, 
                duration_minutes, location, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.user_id, contact_id, title, description, starts_at,
             starts_at + timedelta(minutes=duration_minutes), duration_minutes,
             location, 'scheduled'),
            fetch=False
        )
        
        # 2. Sync to calendar if enabled
        calendar_event_id = None
        if sync_to_calendar and self.calendar_client:
            try:
                event = self.calendar_client.create_event(
                    summary=title,
                    start=starts_at,
                    end=starts_at + timedelta(minutes=duration_minutes),
                    description=description,
                    location=location
                )
                calendar_event_id = event.get('id')
                
                # Update appointment with calendar event ID
                db_optimizer.execute_query(
                    "UPDATE appointments SET calendar_event_id = ?, calendar_provider = ? WHERE id = ?",
                    (calendar_event_id, self.calendar_client.provider, appointment_id),
                    fetch=False
                )
            except Exception as e:
                logger.error(f"Failed to sync appointment to calendar: {e}")
        
        # 3. Schedule reminders
        self._schedule_reminders(appointment_id, starts_at)
        
        return {'id': appointment_id, 'calendar_event_id': calendar_event_id}
    
    def send_reminders(self, hours_before: int = 24):
        """Send appointment reminders"""
        # Get appointments in next X hours
        reminder_time = datetime.now() + timedelta(hours=hours_before)
        
        appointments = db_optimizer.execute_query(
            """SELECT * FROM appointments 
               WHERE user_id = ? 
               AND starts_at BETWEEN ? AND ?
               AND status = 'scheduled'
               AND reminder_sent_24h = 0""",
            (self.user_id, datetime.now(), reminder_time)
        )
        
        for appointment in appointments:
            # Send email reminder
            self._send_email_reminder(appointment)
            
            # Send SMS reminder if enabled
            if self._has_sms_enabled():
                self._send_sms_reminder(appointment)
            
            # Mark reminder as sent
            db_optimizer.execute_query(
                "UPDATE appointments SET reminder_sent_24h = 1 WHERE id = ?",
                (appointment['id'],),
                fetch=False
            )
```

#### **API Endpoints:**
```python
# routes/appointments.py
@appointments_bp.route('/api/appointments', methods=['POST'])
@jwt_required
def create_appointment():
    """Create appointment"""
    data = request.json
    manager = AppointmentManager(get_current_user()['id'])
    result = manager.create_appointment(
        contact_id=data['contact_id'],
        title=data['title'],
        starts_at=datetime.fromisoformat(data['starts_at']),
        duration_minutes=data.get('duration_minutes', 60),
        sync_to_calendar=data.get('sync_to_calendar', True)
    )
    return jsonify({'success': True, 'appointment': result})

@appointments_bp.route('/api/appointments', methods=['GET'])
@jwt_required
def list_appointments():
    """List appointments with filters"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    manager = AppointmentManager(get_current_user()['id'])
    appointments = manager.list_appointments(start_date, end_date, status)
    return jsonify({'success': True, 'appointments': appointments})

@appointments_bp.route('/api/appointments/<appointment_id>', methods=['PUT'])
@jwt_required
def update_appointment():
    """Update appointment (reschedule, cancel, etc.)"""
    pass

@appointments_bp.route('/api/appointments/<appointment_id>/remind', methods=['POST'])
@jwt_required
def send_reminder():
    """Manually send appointment reminder"""
    pass
```

#### **Frontend:**
```typescript
// frontend/src/pages/Appointments.tsx
// Calendar view
// List view
// Create/edit appointments
// Sync status indicator

// frontend/src/components/AppointmentForm.tsx
// Form to create/edit appointments
// Date/time picker
// Contact selector
// Calendar sync toggle
```

#### **AI Guidance:**
```python
# core/ai_guidance/appointment_assistant.py
class AppointmentAssistant:
    def create_appointment_from_conversation(self, user_input, user_id):
        """AI helps create appointment from natural language"""
        # "Schedule a consultation with John for next Tuesday at 2pm"
        # → Extracts: contact="John", date="next Tuesday", time="2pm", type="consultation"
        
        parsed = self.llm.parse_appointment_request(user_input)
        
        # Find contact
        contact = self.find_contact(parsed['contact_name'], user_id)
        
        # Parse date/time
        starts_at = self.parse_datetime(parsed['date'], parsed['time'])
        
        # Suggest duration based on type
        duration = self.suggest_duration(parsed['type'])
        
        # Create appointment
        manager = AppointmentManager(user_id)
        appointment = manager.create_appointment(
            contact_id=contact['id'],
            title=parsed.get('title', f"{parsed['type']} with {contact['name']}"),
            starts_at=starts_at,
            duration_minutes=duration
        )
        
        return appointment
```

**Time Estimate:** 1-2 weeks  
**Dependencies:** Calendar integrations (Google/Outlook)

---

## 2. 💰 **Quote/Invoice Generation (Week 2-3)**

### **What It Does:**
- Generate professional quotes
- Convert quotes to invoices
- Track quote status (sent, viewed, accepted, rejected)
- Send quotes via email
- Generate PDF invoices

### **Implementation:**

#### **Database Schema:**
```sql
CREATE TABLE quotes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    quote_number TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    line_items TEXT,  -- JSON: [{"description": "...", "quantity": 1, "unit_price": 100, "total": 100}]
    subtotal DECIMAL(10, 2),
    tax_rate DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft',  -- draft, sent, viewed, accepted, rejected, expired
    valid_until DATE,
    notes TEXT,
    terms TEXT,  -- Payment terms, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    viewed_at TIMESTAMP,
    accepted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    quote_id INTEGER,  -- If converted from quote
    invoice_number TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    line_items TEXT,  -- JSON
    subtotal DECIMAL(10, 2),
    tax_amount DECIMAL(10, 2),
    total DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft',  -- draft, sent, viewed, paid, overdue, cancelled
    due_date DATE,
    paid_at TIMESTAMP,
    payment_method TEXT,
    notes TEXT,
    terms TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id),
    FOREIGN KEY (quote_id) REFERENCES quotes(id)
);
```

#### **Backend Implementation:**
```python
# core/platform/quotes/quote_manager.py
from decimal import Decimal
import json

class QuoteManager:
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def create_quote(self, contact_id: int, line_items: List[Dict], 
                    tax_rate: float = 0, discount: float = 0,
                    valid_days: int = 30) -> Dict:
        """Create quote from line items"""
        # Calculate totals
        subtotal = sum(item['quantity'] * item['unit_price'] for item in line_items)
        discount_amount = subtotal * (discount / 100) if discount else 0
        subtotal_after_discount = subtotal - discount_amount
        tax_amount = subtotal_after_discount * (tax_rate / 100) if tax_rate else 0
        total = subtotal_after_discount + tax_amount
        
        # Generate quote number
        quote_number = self._generate_quote_number()
        
        # Create quote
        quote_id = db_optimizer.execute_query(
            """INSERT INTO quotes 
               (user_id, contact_id, quote_number, line_items, subtotal, 
                tax_rate, tax_amount, discount_amount, total, valid_until)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.user_id, contact_id, quote_number, json.dumps(line_items),
             subtotal, tax_rate, tax_amount, discount_amount, total,
             datetime.now() + timedelta(days=valid_days)),
            fetch=False
        )
        
        return {'id': quote_id, 'quote_number': quote_number}
    
    def send_quote(self, quote_id: int, email_template: str = None) -> Dict:
        """Send quote to customer via email"""
        quote = self.get_quote(quote_id)
        contact = self.get_contact(quote['contact_id'])
        
        # Generate PDF (optional)
        pdf_url = self._generate_quote_pdf(quote_id)
        
        # Send email
        email_body = self._render_quote_email(quote, contact, email_template)
        
        email_service.send_email(
            to=contact['email'],
            subject=f"Quote #{quote['quote_number']} from {self.get_user_name()}",
            body=email_body,
            attachments=[pdf_url] if pdf_url else []
        )
        
        # Update status
        db_optimizer.execute_query(
            "UPDATE quotes SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (quote_id,),
            fetch=False
        )
        
        return {'success': True}
    
    def convert_to_invoice(self, quote_id: int) -> Dict:
        """Convert quote to invoice"""
        quote = self.get_quote(quote_id)
        
        # Create invoice from quote
        invoice_id = db_optimizer.execute_query(
            """INSERT INTO invoices 
               (user_id, contact_id, quote_id, invoice_number, line_items,
                subtotal, tax_amount, total, due_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.user_id, quote['contact_id'], quote_id,
             self._generate_invoice_number(), quote['line_items'],
             quote['subtotal'], quote['tax_amount'], quote['total'],
             datetime.now() + timedelta(days=30)),  # 30 days payment terms
            fetch=False
        )
        
        return {'invoice_id': invoice_id}
```

#### **PDF Generation:**
```python
# core/platform/quotes/pdf_generator.py
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

class QuotePDFGenerator:
    def generate_quote_pdf(self, quote: Dict, contact: Dict, user: Dict) -> str:
        """Generate professional quote PDF"""
        filename = f"quotes/quote_{quote['quote_number']}.pdf"
        
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, f"QUOTE #{quote['quote_number']}")
        
        # Company info
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 100, user['business_name'])
        c.drawString(50, height - 115, user['email'])
        
        # Contact info
        c.drawString(400, height - 100, "Bill To:")
        c.drawString(400, height - 115, contact['name'])
        c.drawString(400, height - 130, contact['email'])
        
        # Line items
        y = height - 200
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Description")
        c.drawString(350, y, "Quantity")
        c.drawString(400, y, "Price")
        c.drawString(500, y, "Total")
        
        y -= 20
        c.setFont("Helvetica", 10)
        line_items = json.loads(quote['line_items'])
        for item in line_items:
            c.drawString(50, y, item['description'])
            c.drawString(350, y, str(item['quantity']))
            c.drawString(400, y, f"${item['unit_price']:.2f}")
            c.drawString(500, y, f"${item['total']:.2f}")
            y -= 15
        
        # Totals
        y -= 20
        c.drawString(400, y, f"Subtotal: ${quote['subtotal']:.2f}")
        y -= 15
        if quote['tax_amount'] > 0:
            c.drawString(400, y, f"Tax: ${quote['tax_amount']:.2f}")
            y -= 15
        c.setFont("Helvetica-Bold", 12)
        c.drawString(400, y, f"Total: ${quote['total']:.2f}")
        
        # Footer
        c.setFont("Helvetica", 9)
        c.drawString(50, 50, f"Valid until: {quote['valid_until']}")
        
        c.save()
        return filename
```

#### **AI Guidance:**
```python
# core/ai_guidance/quote_assistant.py
class QuoteAssistant:
    def generate_quote_from_email(self, email_content, user_id):
        """AI extracts quote request from email and generates quote"""
        # Parse email for service requests
        services = self.llm.extract_services_from_email(email_content)
        
        # Get pricing from user's service catalog
        line_items = []
        for service in services:
            price = self.get_service_price(service, user_id)
            line_items.append({
                'description': service,
                'quantity': 1,
                'unit_price': price,
                'total': price
            })
        
        # Create quote
        manager = QuoteManager(user_id)
        quote = manager.create_quote(
            contact_id=self.get_contact_from_email(email_content),
            line_items=line_items
        )
        
        return quote
```

**Time Estimate:** 1 week  
**Dependencies:** None (can use existing email system)

---

## 3. 💳 **Payment Processing (Week 2-3)**

### **What It Does:**
- Accept payments for invoices
- Generate payment links
- Process card payments
- Track payment status
- Send payment receipts

### **Implementation:**

**Already have Stripe for billing, extend for payments:**

```python
# core/integrations/payments/stripe_payments.py (extend existing)
class StripePaymentsClient:
    def create_invoice_payment_link(self, invoice_id: int) -> Dict:
        """Create Stripe payment link for invoice"""
        invoice = self.get_invoice(invoice_id)
        
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'us_bank_account'],  # Cards + ACH
            line_items=[{
                'price_data': {
                    'currency': invoice['currency'],
                    'product_data': {
                        'name': f"Invoice #{invoice['invoice_number']}"
                    },
                    'unit_amount': int(invoice['total'] * 100)  # Convert to cents
                },
                'quantity': 1
            }],
            mode='payment',
            success_url=f"{os.getenv('FRONTEND_URL')}/payments/success?invoice_id={invoice_id}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/invoices/{invoice_id}",
            metadata={'invoice_id': invoice_id, 'user_id': invoice['user_id']}
        )
        
        return {'payment_url': session.url, 'session_id': session.id}
    
    def handle_webhook(self, event):
        """Handle Stripe webhook for payment events"""
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            invoice_id = session['metadata'].get('invoice_id')
            
            if invoice_id:
                # Mark invoice as paid
                db_optimizer.execute_query(
                    """UPDATE invoices 
                       SET status = 'paid', paid_at = CURRENT_TIMESTAMP,
                           payment_method = ?
                       WHERE id = ?""",
                    (session['payment_method_types'][0], invoice_id),
                    fetch=False
                )
                
                # Create payment record
                db_optimizer.execute_query(
                    """INSERT INTO payments 
                       (user_id, invoice_id, stripe_payment_intent_id, amount, status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (session['metadata']['user_id'], invoice_id,
                     session['payment_intent'], session['amount_total'] / 100,
                     'succeeded'),
                    fetch=False
                )
                
                # Send receipt
                self._send_payment_receipt(invoice_id)
```

**Time Estimate:** 1 week (extend existing Stripe integration)  
**Dependencies:** Stripe account (already have)

---

## 4. 🌐 **Customer Portal (Week 3-4)**

### **What It Does:**
- Customers can view their invoices
- Customers can pay invoices online
- Customers can view appointment history
- Customers can request services
- Customers can view account information

### **Implementation:**

#### **Frontend:**
```typescript
// frontend/src/pages/CustomerPortal.tsx
// Public-facing customer portal
// No authentication required (uses secure token)

// frontend/src/pages/CustomerPortal/InvoiceView.tsx
// View invoice
// Pay invoice button
// Download PDF

// frontend/src/pages/CustomerPortal/Appointments.tsx
// View upcoming appointments
// Request reschedule
// Cancel appointment
```

#### **Backend:**
```python
# routes/customer_portal.py
@portal_bp.route('/portal/invoice/<token>', methods=['GET'])
def view_invoice(token):
    """View invoice with secure token (no login required)"""
    invoice = verify_portal_token(token)
    if not invoice:
        return jsonify({'error': 'Invalid token'}), 404
    
    return jsonify({
        'success': True,
        'invoice': {
            'invoice_number': invoice['invoice_number'],
            'total': invoice['total'],
            'due_date': invoice['due_date'],
            'status': invoice['status'],
            'line_items': json.loads(invoice['line_items'])
        }
    })

@portal_bp.route('/portal/invoice/<token>/pay', methods=['POST'])
def pay_invoice(token):
    """Create payment link for invoice"""
    invoice = verify_portal_token(token)
    if not invoice:
        return jsonify({'error': 'Invalid token'}), 404
    
    payments_client = StripePaymentsClient()
    payment_link = payments_client.create_invoice_payment_link(invoice['id'])
    
    return jsonify({'success': True, 'payment_url': payment_link['payment_url']})
```

#### **Secure Token System:**
```python
# core/platform/portal/portal_tokens.py
import secrets
import hashlib
from datetime import datetime, timedelta

class PortalTokenManager:
    def generate_invoice_token(self, invoice_id: int) -> str:
        """Generate secure token for invoice access"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=90)  # 90 days validity
        
        db_optimizer.execute_query(
            """INSERT INTO portal_tokens 
               (token_hash, entity_type, entity_id, expires_at)
               VALUES (?, ?, ?, ?)""",
            (hashlib.sha256(token.encode()).hexdigest(), 'invoice', invoice_id, expires_at),
            fetch=False
        )
        
        return token
    
    def verify_token(self, token: str) -> Dict:
        """Verify portal token and return entity"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = db_optimizer.execute_query(
            """SELECT * FROM portal_tokens 
               WHERE token_hash = ? AND expires_at > ?""",
            (token_hash, datetime.now())
        )
        
        if result:
            return {'entity_type': result[0]['entity_type'], 'entity_id': result[0]['entity_id']}
        return None
```

**Time Estimate:** 1-2 weeks  
**Dependencies:** Payment processing, invoice system

---

## 5. 🔧 **Service Management (Week 4-5)**

### **What It Does:**
- Create work orders/service requests
- Track job status
- Assign to team members
- Track time and materials
- Link to appointments and invoices

### **Implementation:**

#### **Database Schema:**
```sql
CREATE TABLE service_requests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    appointment_id INTEGER,  -- If created from appointment
    request_number TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,  -- maintenance, repair, installation, etc.
    priority TEXT DEFAULT 'normal',  -- low, normal, high, urgent, emergency
    status TEXT DEFAULT 'open',  -- open, assigned, in_progress, completed, cancelled
    assigned_to INTEGER,  -- user_id (team member)
    estimated_hours DECIMAL(5, 2),
    actual_hours DECIMAL(5, 2),
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    materials TEXT,  -- JSON: materials used
    notes TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE TABLE work_logs (
    id INTEGER PRIMARY KEY,
    service_request_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,  -- Team member who logged
    hours_worked DECIMAL(5, 2),
    description TEXT,
    materials_used TEXT,  -- JSON
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_request_id) REFERENCES service_requests(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### **Backend:**
```python
# core/platform/services/service_manager.py
class ServiceManager:
    def create_service_request(self, contact_id: int, title: str, 
                              category: str, priority: str = 'normal') -> Dict:
        """Create service request"""
        request_number = self._generate_request_number()
        
        request_id = db_optimizer.execute_query(
            """INSERT INTO service_requests 
               (user_id, contact_id, request_number, title, category, priority)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.user_id, contact_id, request_number, title, category, priority),
            fetch=False
        )
        
        # Auto-assign if rules exist
        assigned_to = self._auto_assign_request(request_id, category, priority)
        
        # Notify team member if assigned
        if assigned_to:
            self._notify_assignment(assigned_to, request_id)
        
        return {'id': request_id, 'request_number': request_number}
    
    def log_work(self, service_request_id: int, hours: float, 
                 description: str, materials: List[Dict] = None):
        """Log work hours and materials"""
        db_optimizer.execute_query(
            """INSERT INTO work_logs 
               (service_request_id, user_id, hours_worked, description, materials_used)
               VALUES (?, ?, ?, ?, ?)""",
            (service_request_id, self.user_id, hours, description,
             json.dumps(materials) if materials else None),
            fetch=False
        )
        
        # Update service request totals
        self._update_request_totals(service_request_id)
```

**Time Estimate:** 1 week  
**Dependencies:** Team management (for assignment)

---

## 6. 👥 **Team Management (Week 5-6)**

### **What It Does:**
- Add team members
- Assign roles and permissions
- Assign work to team members
- Track team performance
- Team notifications

### **Implementation:**

#### **Database Schema:**
```sql
CREATE TABLE team_members (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,  -- Business owner
    member_email TEXT NOT NULL,
    member_name TEXT,
    role TEXT DEFAULT 'member',  -- owner, admin, member, viewer
    permissions TEXT,  -- JSON: specific permissions
    is_active BOOLEAN DEFAULT 1,
    invited_at TIMESTAMP,
    joined_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE team_assignments (
    id INTEGER PRIMARY KEY,
    service_request_id INTEGER,
    appointment_id INTEGER,
    assigned_to INTEGER NOT NULL,  -- team_member id
    assigned_by INTEGER,  -- user_id
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_request_id) REFERENCES service_requests(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (assigned_to) REFERENCES team_members(id)
);
```

#### **Backend:**
```python
# core/platform/team/team_manager.py
class TeamManager:
    def invite_team_member(self, email: str, name: str, role: str = 'member'):
        """Invite team member"""
        # Create invitation
        invitation_token = secrets.token_urlsafe(32)
        
        db_optimizer.execute_query(
            """INSERT INTO team_members 
               (user_id, member_email, member_name, role, invited_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (self.user_id, email, name, role),
            fetch=False
        )
        
        # Send invitation email
        self._send_invitation_email(email, name, invitation_token)
        
        return {'success': True}
    
    def assign_to_team_member(self, entity_type: str, entity_id: int, 
                             team_member_id: int):
        """Assign work to team member"""
        if entity_type == 'service_request':
            db_optimizer.execute_query(
                """INSERT INTO team_assignments 
                   (service_request_id, assigned_to, assigned_by)
                   VALUES (?, ?, ?)""",
                (entity_id, team_member_id, self.user_id),
                fetch=False
            )
            
            # Update service request
            db_optimizer.execute_query(
                "UPDATE service_requests SET assigned_to = ?, status = 'assigned' WHERE id = ?",
                (team_member_id, entity_id),
                fetch=False
            )
```

**Time Estimate:** 1 week  
**Dependencies:** None

---

## 7. 📊 **Advanced Reporting (Week 6-7)**

### **What It Does:**
- Revenue reports
- Appointment analytics
- Team performance
- Customer analytics
- Custom reports

### **Implementation:**

```python
# core/platform/analytics/reporting_engine.py
class ReportingEngine:
    def generate_revenue_report(self, user_id: int, start_date: datetime, 
                               end_date: datetime) -> Dict:
        """Generate revenue report"""
        # Get all paid invoices in date range
        invoices = db_optimizer.execute_query(
            """SELECT * FROM invoices 
               WHERE user_id = ? 
               AND status = 'paid'
               AND paid_at BETWEEN ? AND ?""",
            (user_id, start_date, end_date)
        )
        
        total_revenue = sum(invoice['total'] for invoice in invoices)
        invoice_count = len(invoices)
        average_invoice = total_revenue / invoice_count if invoice_count > 0 else 0
        
        # Group by month
        monthly_revenue = {}
        for invoice in invoices:
            month = invoice['paid_at'].strftime('%Y-%m')
            monthly_revenue[month] = monthly_revenue.get(month, 0) + invoice['total']
        
        return {
            'total_revenue': total_revenue,
            'invoice_count': invoice_count,
            'average_invoice': average_invoice,
            'monthly_breakdown': monthly_revenue,
            'top_customers': self._get_top_customers(user_id, start_date, end_date)
        }
    
    def generate_appointment_report(self, user_id: int, start_date: datetime,
                                  end_date: datetime) -> Dict:
        """Generate appointment analytics"""
        appointments = db_optimizer.execute_query(
            """SELECT * FROM appointments 
               WHERE user_id = ? 
               AND starts_at BETWEEN ? AND ?""",
            (user_id, start_date, end_date)
        )
        
        total = len(appointments)
        completed = len([a for a in appointments if a['status'] == 'completed'])
        no_shows = len([a for a in appointments if a['status'] == 'no_show'])
        canceled = len([a for a in appointments if a['status'] == 'canceled'])
        
        return {
            'total_appointments': total,
            'completed': completed,
            'no_shows': no_shows,
            'canceled': canceled,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'no_show_rate': (no_shows / total * 100) if total > 0 else 0
        }
```

**Time Estimate:** 1 week  
**Dependencies:** All other features (to have data to report on)

---

## 📅 **Implementation Timeline**

### **Weeks 1-2: Core Features**
- [ ] Appointment scheduling (with calendar sync)
- [ ] Quote/invoice generation
- [ ] Payment processing (Stripe Payments)

### **Week 3: Customer Portal**
- [ ] Customer portal (view invoices, pay online)
- [ ] Secure token system

### **Week 4: Service Management**
- [ ] Work orders/service requests
- [ ] Job tracking
- [ ] Time and materials logging

### **Week 5: Team Management**
- [ ] Team member invitations
- [ ] Role and permissions
- [ ] Work assignment

### **Week 6-7: Advanced Reporting**
- [ ] Revenue reports
- [ ] Appointment analytics
- [ ] Team performance
- [ ] Custom reports

**Total: 6-7 weeks for complete business platform**

---

## 🎯 **AI Guidance Integration**

**All features will have AI assistance:**

1. **Appointment Scheduling:** "Schedule consultation with John next Tuesday" → AI creates appointment
2. **Quote Generation:** "Create quote for cleaning service" → AI generates quote
3. **Service Requests:** "Create work order for plumbing repair" → AI creates request
4. **Team Assignment:** "Assign this to Sarah" → AI assigns and notifies
5. **Reporting:** "Show me revenue this month" → AI generates report

---

## ✅ **Result: Complete Business Platform**

After 6-7 weeks, users can:
- ✅ Schedule appointments (with calendar sync)
- ✅ Generate quotes and invoices
- ✅ Accept payments online
- ✅ Provide customer portal
- ✅ Manage service requests/work orders
- ✅ Manage team members
- ✅ View advanced analytics

**All with AI guidance at every step.**

---

**Status:** ✅ **Ready to Implement**

Should I start with appointment scheduling? It's the foundation for most business operations.
