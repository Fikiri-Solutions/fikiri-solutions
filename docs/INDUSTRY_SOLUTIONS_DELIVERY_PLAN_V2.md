# 🎯 Industry Solutions Delivery Plan V2
## Configuration-First, Capability-Module Architecture

**Date:** January 2026  
**Status:** 📋 **Revised Architecture - Ready for Execution**  
**Philosophy:** Industries are configuration + templates, not separate codebases

---

## 🎯 **Core Principle: You're Not Building 13 Apps**

### **The Reality:**
Most industries use the same 4 building blocks with different wording:

1. **Entities:** Contacts/Leads + Industry Objects (appointments, quotes, work orders, reservations, cases, properties)
2. **Intake:** Email + Forms + (later) SMS/Chat
3. **Workflow:** Trigger → Classify → Route → Action(s) → Log → Follow-up
4. **Knowledge:** Templates + KB/RAG + Business Profile Context

### **What Industries Actually Are:**
- ✅ Schema extension (extra fields / one extra table)
- ✅ Bundle of templates + workflows (YAML)
- ✅ UI pack (landing + dashboard widgets)
- ✅ ✅ Ruleset (routing + compliance constraints)

### **What Industries Are NOT:**
- ❌ Separate code modules per industry
- ❌ Duplicate implementations
- ❌ Industry-specific business logic (unless unavoidable)

---

## 🏗️ **New Architecture: Industry Packs (Declarative)**

### **Structure:**

```
core/industry_packs/
├── __init__.py
├── pack_loader.py          # Loads and validates packs
├── registry.py             # Industry registry
├── real_estate/
│   ├── pack.yaml           # Industry definition
│   ├── workflows.yaml      # Workflow definitions
│   ├── templates/          # Email templates
│   │   ├── consultation_request.md
│   │   ├── showing_confirmation.md
│   │   └── market_report.md
│   ├── forms/              # Form definitions (JSON)
│   │   └── property_inquiry.json
│   ├── ui.json             # UI configuration
│   └── compliance.yaml     # Compliance rules (if needed)
├── medical/
│   ├── pack.yaml
│   ├── workflows.yaml
│   ├── templates/
│   ├── compliance.yaml     # HIPAA rules
│   └── ui.json
└── cleaning_services/
    ├── pack.yaml
    ├── workflows.yaml
    ├── templates/
    └── ui.json
```

### **pack.yaml Structure:**

```yaml
# core/industry_packs/cleaning_services/pack.yaml
id: cleaning_services
name: Cleaning Services
tier: starter
pricing: $39/mo

# Enabled capabilities (from shared modules)
capabilities:
  - appointments
  - quotes
  - reminders
  - follow_ups

# Required integrations
required_integrations:
  - email: gmail  # Required
  - calendar: optional
  - sms: optional

# Entities used (maps to capability modules)
entities:
  - appointments
  - service_requests

# Default pipeline settings
pipeline:
  tone: professional
  response_sla_minutes: 60
  follow_up_days: [1, 3, 7]
  auto_classify: true

# CRM field mappings
crm_fields:
  lead_stages:
    - new
    - quote_requested
    - scheduled
    - completed
  tags:
    - residential
    - commercial
    - recurring
    - one_time

# Workflow files
workflows: workflows.yaml

# Template directory
templates: templates/

# UI configuration
ui: ui.json
```

### **workflows.yaml Structure:**

```yaml
# core/industry_packs/cleaning_services/workflows.yaml
workflows:
  - id: quote_request
    name: Quote Request Automation
    trigger:
      type: email_received
      conditions:
        keywords: [quote, estimate, cleaning, service]
        subject_contains: [quote, estimate]
    actions:
      - type: send_email
        template: quote_acknowledgment
        delay_minutes: 0
      - type: create_lead
        stage: quote_requested
        tags: [quote_request]
      - type: create_appointment
        type: consultation
        default_duration_minutes: 30
      - type: schedule_follow_up
        days: 3
        template: quote_follow_up

  - id: recurring_reminder
    name: Recurring Service Reminder
    trigger:
      type: time_based
      schedule: weekly
      day_of_week: monday
      time: 09:00
    actions:
      - type: send_email
        template: service_reminder
        filter: contacts_with_recurring_services
      - type: create_task
        title: Follow up on service reminders
        due_days: 2
```

---

## 🔧 **The 4 Capability Modules (Build Once, Use Everywhere)**

### **1. Appointments Module** 📅

**What it does:**
- Booking management
- Reminders (24h, 2h before)
- Cancellation handling
- Calendar integration (optional)

**Database Schema:**
```sql
CREATE TABLE appointments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP,
    status TEXT DEFAULT 'scheduled',  -- scheduled, confirmed, completed, canceled, no_show
    location TEXT,
    notes TEXT,
    reminder_sent_24h BOOLEAN DEFAULT 0,
    reminder_sent_2h BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE INDEX idx_appointments_user ON appointments(user_id);
CREATE INDEX idx_appointments_starts_at ON appointments(starts_at);
CREATE INDEX idx_appointments_status ON appointments(status);
```

**Files:**
```
core/capabilities/
├── appointments/
│   ├── __init__.py
│   ├── models.py          # Appointment model
│   ├── manager.py         # CRUD operations
│   ├── reminders.py       # Reminder automation
│   └── calendar_sync.py   # Calendar integration (optional)
```

**Used by industries:**
- Cleaning Services (service appointments)
- Auto Services (service appointments)
- Fitness & Wellness (class bookings, personal training)
- Beauty & Spa (appointment booking)
- Medical Practice (patient appointments)
- Real Estate (showings)
- Restaurant (reservations)
- Event Planning (consultations)

---

### **2. Quotes/Estimates Module** 💰

**What it does:**
- Quote generation
- Quote approval workflow
- Follow-up automation
- Conversion tracking

**Database Schema:**
```sql
CREATE TABLE quotes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    quote_number TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    items TEXT,  -- JSON array of line items
    subtotal DECIMAL(10, 2),
    tax DECIMAL(10, 2),
    total DECIMAL(10, 2),
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft',  -- draft, sent, viewed, accepted, rejected, expired
    valid_until DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE INDEX idx_quotes_user ON quotes(user_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_contact ON quotes(contact_id);
```

**Files:**
```
core/capabilities/
├── quotes/
│   ├── __init__.py
│   ├── models.py          # Quote model
│   ├── manager.py         # CRUD operations
│   ├── generator.py        # Quote generation from templates
│   └── follow_up.py       # Follow-up automation
```

**Used by industries:**
- Cleaning Services (service quotes)
- Auto Services (repair estimates)
- Construction (project quotes)
- Real Estate (consultation packages)
- Legal Services (service estimates)
- Accounting (service quotes)

---

### **3. Requests/Tickets Module** 🎫

**What it does:**
- Request intake (maintenance, support, intake forms)
- Categorization and routing
- Status tracking
- Assignment and escalation

**Database Schema:**
```sql
CREATE TABLE service_requests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    contact_id INTEGER,
    request_number TEXT UNIQUE,
    category TEXT NOT NULL,  -- maintenance, support, intake, inquiry
    urgency TEXT DEFAULT 'normal',  -- low, normal, high, urgent, emergency
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',  -- open, assigned, in_progress, resolved, closed
    assigned_to INTEGER,  -- user_id or null
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (contact_id) REFERENCES leads(id)
);

CREATE INDEX idx_requests_user ON service_requests(user_id);
CREATE INDEX idx_requests_status ON service_requests(status);
CREATE INDEX idx_requests_urgency ON service_requests(urgency);
```

**Files:**
```
core/capabilities/
├── requests/
│   ├── __init__.py
│   ├── models.py          # Request model
│   ├── manager.py         # CRUD operations
│   ├── router.py          # Auto-routing logic
│   └── escalation.py      # Escalation rules
```

**Used by industries:**
- Property Management (maintenance requests)
- Construction (project requests)
- Legal Services (client intake)
- Medical Practice (patient intake)
- Accounting (document requests)
- Cleaning Services (service requests)

---

### **4. Documents + KB Module** 📄

**What it does:**
- Document upload and storage
- Document linking to contacts/leads
- Knowledge base integration
- RAG-ready document indexing

**Database Schema:**
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    category TEXT,  -- contract, invoice, report, form, other
    linked_to_type TEXT,  -- lead, quote, appointment, request
    linked_to_id INTEGER,
    is_encrypted BOOLEAN DEFAULT 0,
    access_level TEXT DEFAULT 'private',  -- private, team, public
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_linked ON documents(linked_to_type, linked_to_id);
```

**Files:**
```
core/capabilities/
├── documents/
│   ├── __init__.py
│   ├── models.py          # Document model
│   ├── storage.py         # File storage (local/S3)
│   ├── encryption.py      # Encryption for sensitive docs
│   └── kb_indexer.py      # Knowledge base indexing
```

**Used by industries:**
- Legal Services (case documents)
- Accounting (tax documents, financial statements)
- Medical Practice (patient records - HIPAA)
- Real Estate (property documents)
- Construction (project documents)

---

## 🚧 **Week 0: Platform Unblockers (MUST DO FIRST)**

### **Critical Prerequisites Before Industry Packs:**

#### **1. Inbox: Attachments Display** ⚠️ **BLOCKER**
**Status:** Unknown - needs verification  
**Why:** Industries need to handle document attachments (quotes, contracts, photos)

**Tasks:**
- [ ] Verify attachment display in inbox
- [ ] Add attachment download functionality
- [ ] Add attachment preview (images, PDFs)
- [ ] Link attachments to documents module

#### **2. Services Configuration Persistence** ⚠️ **BLOCKER**
**Status:** Needs implementation  
**Why:** Users need to save industry selection and workflow settings

**Tasks:**
- [ ] Create `user_industry_settings` table
- [ ] Add API endpoints: `GET/POST /api/user/industry-settings`
- [ ] Persist selected industry per user
- [ ] Persist enabled workflows per user
- [ ] Persist workflow-specific settings (follow-up times, tone, etc.)

**Database Schema:**
```sql
CREATE TABLE user_industry_settings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    industry_id TEXT NOT NULL,
    enabled_workflows TEXT,  -- JSON array of workflow IDs
    workflow_settings TEXT,  -- JSON object: {workflow_id: {setting: value}}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### **3. Basic Retention Jobs** ⚠️ **IMPORTANT**
**Status:** Needs implementation  
**Why:** Prevent database bloat, maintain performance

**Tasks:**
- [ ] 90-day metrics cleanup job
- [ ] 30-day sync_jobs cleanup
- [ ] Archive old email metadata (keep last 6 months)
- [ ] Clean up expired sessions

#### **4. Basic Backups** ⚠️ **IMPORTANT**
**Status:** Needs implementation  
**Why:** Data protection, disaster recovery

**Tasks:**
- [ ] Nightly database dump script
- [ ] Backup retention (7 daily, 4 weekly, 12 monthly)
- [ ] Backup verification
- [ ] Restore procedure documentation

#### **5. Basic Integrations Page** ⚠️ **BLOCKER**
**Status:** Needs implementation  
**Why:** Users need to see/manage integrations before selecting industries

**Tasks:**
- [ ] Create `/integrations` page
- [ ] Show Gmail connection status
- [ ] Show calendar connection status (if integrated)
- [ ] Show other integrations (even if "coming soon")
- [ ] Add "Connect" buttons for each integration

---

## 📅 **Revised Timeline (Realistic)**

### **Week 0: Platform Unblockers (2-4 days)**
- [ ] Attachments display
- [ ] Services configuration persistence
- [ ] Basic retention jobs
- [ ] Basic backups
- [ ] Integrations page (basic)

**Result:** Platform is ready to support industry packs safely.

---

### **Phase 1: Industry Pack Engine (Weeks 1-2)**

**Deliverables:**

#### **1. Industry Registry + Pack Loader**
```python
# core/industry_packs/registry.py
class IndustryRegistry:
    def load_pack(self, industry_id: str) -> IndustryPack
    def list_packs(self) -> List[IndustryPack]
    def validate_pack(self, pack_path: str) -> bool
```

**API Endpoints:**
- `GET /api/industries` - List all available industries
- `GET /api/industries/{id}` - Get industry pack details
- `POST /api/industries/{id}/install` - Install industry pack for user

#### **2. Industry Settings Persistence**
- Store selected industry per user
- Store enabled workflows per user
- Store workflow-specific settings

**API Endpoints:**
- `GET /api/user/industry-settings` - Get user's industry settings
- `POST /api/user/industry-settings` - Update industry settings

#### **3. Workflow YAML Runner**
```python
# core/industry_packs/workflow_executor.py
class WorkflowExecutor:
    def execute_workflow(self, workflow_id: str, context: Dict) -> Dict
    def validate_workflow(self, workflow: Dict) -> bool
```

**Supported Triggers:**
- `email_received` - Email matches conditions
- `form_submitted` - Form submission
- `time_based` - Scheduled (daily, weekly, monthly)

**Supported Actions:**
- `send_email` - Send email template
- `create_lead` - Create CRM lead
- `create_task` - Create task
- `create_appointment` - Create appointment (if module exists)
- `create_quote` - Create quote (if module exists)
- `create_request` - Create service request (if module exists)
- `schedule_follow_up` - Schedule follow-up
- `log_activity` - Log activity to CRM

**Result:** You can "launch" new industries by adding YAML + templates (no code).

---

### **Phase 2: Build 4 Capability Modules (Weeks 3-4)**

**Build in order:**

1. **Appointments Module** (Week 3, Days 1-2)
   - Database schema
   - CRUD operations
   - Reminder automation
   - Basic calendar integration (optional)

2. **Quotes Module** (Week 3, Days 3-4)
   - Database schema
   - CRUD operations
   - Quote generation
   - Follow-up automation

3. **Requests Module** (Week 4, Days 1-2)
   - Database schema
   - CRUD operations
   - Auto-routing logic
   - Status tracking

4. **Documents Module** (Week 4, Days 3-4)
   - Database schema
   - File storage (start with local, S3 later)
   - Document linking
   - Basic encryption (for sensitive docs)

**Result:** All 4 capability modules ready. Industries can now use them.

---

### **Phase 3: Starter Tier Industries (Weeks 5-6)**

**Pick 2-3 first (not 4):**

**Best First Picks:**
1. ✅ **Cleaning Services** - Simple, clear ROI
2. ✅ **Beauty & Spa** - Similar to cleaning (appointments + reminders)
3. ✅ **Auto Services** - Similar pattern

**Why these:**
- Low compliance risk
- No external APIs required
- Clear ROI for customer
- Use appointments + quotes modules

**For Each Industry Pack:**

1. **Create Pack Structure:**
   ```
   core/industry_packs/cleaning_services/
   ├── pack.yaml
   ├── workflows.yaml
   ├── templates/
   │   ├── quote_acknowledgment.md
   │   ├── service_reminder.md
   │   └── follow_up.md
   └── ui.json
   ```

2. **Define Workflows:**
   - Quote request automation
   - Service reminder automation
   - Follow-up automation

3. **Create Templates:**
   - Quote acknowledgment email
   - Service reminder email
   - Follow-up email

4. **UI Configuration:**
   - Landing page content
   - Dashboard widgets
   - Settings page fields

5. **Test End-to-End:**
   - Install pack
   - Trigger workflow
   - Verify actions execute
   - Check CRM updates
   - Verify emails sent

**Result:** 2-3 billable industries shipped. Users can select industry and get working automations.

---

### **Phase 4: Add 2 More Starter Packs + Forms (Weeks 7-8)**

**Add:**
- Fitness & Wellness
- Event Planning (basic - calendar optional)

**New Capability:**
- **Forms Module** (if not already built)
  - Form builder (JSON schema)
  - Form submission handling
  - Form → Lead conversion
  - Form → Request conversion

**Result:** 5 starter industries + forms capability.

---

### **Phase 5: Growth Tier (Weeks 9-10)**

**Prerequisites:**
- Calendar integration stable (or mocked)
- Forms module working
- Task system working
- Better document handling

**Industries:**
- Restaurant (enhance existing)
- Property Management
- Construction

**New Requirements:**
- Calendar sync for appointments
- Task assignment
- Document upload/linking

---

### **Phase 6: Business Tier (Weeks 11-14)**

**One at a time, carefully:**

#### **Week 11: Real Estate**
- Property CRUD (new entity type)
- Showing scheduling (uses appointments module)
- Follow-ups + packets (templates)
- **Skip market analysis APIs** (too complex, paywalled)

#### **Week 12: Legal Services**
- Client intake (uses requests module)
- Document management (uses documents module)
- Case updates (workflow-based)
- **Add:** Secure document storage, audit logs

#### **Week 13: Accounting & Consulting**
- Client onboarding (workflow-based)
- Document requests (uses requests + documents)
- Tax reminders (time-based workflows)
- **Add:** Secure document encryption

#### **Week 14: Medical Practice (HIPAA)**
- Appointment scheduling (uses appointments module)
- Patient reminders (workflow-based)
- Follow-up care (workflow-based)
- **CRITICAL:** HIPAA compliance features:
  - Encryption at rest
  - Audit log table
  - Access control
  - Minimum necessary data handling
  - BAA capability

**⚠️ Don't market HIPAA until:**
- Encryption at rest implemented
- Audit logging working
- Access policies defined
- Clear statement of what you do/don't store

---

### **Phase 7: Enterprise (Weeks 15-16)**

**Only after:**
- Security foundations solid
- Analytics working
- Multi-industry support tested

**Features:**
- Custom workflows (visual builder)
- Multi-industry selection
- Advanced analytics
- White-label options

---

## ✅ **Definition of Done (Per Industry Pack)**

Each industry pack is only "shipped" when:

- [ ] **3-5 workflows** working end-to-end
- [ ] **Templates tested** (reply + follow-up emails)
- [ ] **CRM updates** working (lead stages / tags)
- [ ] **Activity logs** visible on dashboard
- [ ] **Onboarding path** selects industry and installs pack
- [ ] **Settings persist** + can toggle workflows
- [ ] **Docs page** exists (even short)
- [ ] **Landing page** exists
- [ ] **Support notes** exist

---

## 🎯 **Key Risks & Mitigations**

### **1. Support Burden**
**Risk:** 13 industries = 13 sets of "why didn't it do X?"  
**Mitigation:** Everything template-driven. Support team can edit YAML, not code.

### **2. Integrations Dependency**
**Risk:** Calendar/SMS/Sheets block "realistic" features  
**Mitigation:** Make integrations optional. Workflows degrade gracefully.

### **3. Compliance Marketing Risk**
**Risk:** HIPAA/legal/privacy claims create exposure  
**Mitigation:** Don't market compliance until controls are real. Clear disclaimers.

### **4. Data Model Sprawl**
**Risk:** Too many tables per industry → migrations + UI complexity  
**Mitigation:** Use 4 shared capability modules. Industries only add fields, not tables.

---

## 📊 **Industry → Capability Mapping**

| Industry | Appointments | Quotes | Requests | Documents |
|----------|-------------|--------|----------|-----------|
| Cleaning Services | ✅ | ✅ | ✅ | ❌ |
| Auto Services | ✅ | ✅ | ✅ | ❌ |
| Fitness & Wellness | ✅ | ❌ | ❌ | ❌ |
| Beauty & Spa | ✅ | ❌ | ❌ | ❌ |
| Event Planning | ✅ | ✅ | ❌ | ❌ |
| Restaurant | ✅ | ❌ | ❌ | ❌ |
| Property Management | ✅ | ❌ | ✅ | ❌ |
| Construction | ✅ | ✅ | ✅ | ✅ |
| Real Estate | ✅ | ✅ | ❌ | ✅ |
| Legal Services | ✅ | ✅ | ✅ | ✅ |
| Accounting | ✅ | ✅ | ✅ | ✅ |
| Medical Practice | ✅ | ❌ | ✅ | ✅ |
| Enterprise | All | All | All | All |

---

## 🚀 **Fastest Path to "All 13"**

**Strategy:** Build 4 capability modules once, map all industries to them.

**Timeline:**
- Weeks 0-2: Platform + Pack Engine
- Weeks 3-4: 4 Capability Modules
- Weeks 5-6: 3 Starter Industries (YAML only)
- Weeks 7-8: 2 More Starter + Forms
- Weeks 9-10: 3 Growth Industries
- Weeks 11-14: 4 Business Industries (one per week)
- Weeks 15-16: Enterprise

**Total: 16 weeks to all 13 industries**

**But:** Each phase is billable. You can start charging after Week 6.

---

## 📝 **Next Steps**

1. **This Week:**
   - Verify platform blockers (attachments, services persistence)
   - Create industry_packs directory structure
   - Design pack.yaml schema

2. **Next Week:**
   - Build industry registry + pack loader
   - Build workflow executor
   - Create first industry pack (Cleaning Services) as proof of concept

3. **Week 3:**
   - Build appointments module
   - Build quotes module
   - Test with Cleaning Services pack

---

**Status:** ✅ **Architecture Revised - Ready for Implementation**

This approach is **scalable, maintainable, and actually shippable**.
