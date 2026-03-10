# Universal Integration Strategy for B2B SaaS Platforms

**Date:** February 2026  
**Goal:** Enable clients to integrate Fikiri features (chatbot, CRM, email automation, lead capture) into any website platform (WordPress, SquareSpace, Replit, custom sites)

---

## 🎯 Core Integration Methods

### 1. **Universal JavaScript SDK** (Primary Method)
- Single JavaScript file that works on any website
- Handles authentication, API calls, widget rendering
- Works with WordPress, SquareSpace, Replit, custom HTML sites

### 2. **Embeddable Widgets**
- Pre-built UI components (chatbot, lead capture forms, contact forms)
- Customizable styling and behavior
- Zero-code integration

### 3. **REST API** (For Custom Integrations)
- Full-featured REST API for developers
- Webhook support for real-time events
- API key authentication

### 4. **Platform-Specific Plugins**
- WordPress plugin (PHP)
- SquareSpace widget/block
- Replit package

---

## 🏗️ Architecture: Universal Integration Layer

```
integrations/
├── universal/
│   ├── fikiri-sdk.js          # Universal JavaScript SDK
│   ├── widgets/
│   │   ├── chatbot-widget.js  # Chatbot widget
│   │   ├── lead-capture.js    # Lead capture form
│   │   └── contact-form.js    # Contact form widget
│   └── styles/
│       └── fikiri-widgets.css # Default widget styles
├── wordpress/
│   ├── fikiri-plugin.php      # WordPress plugin
│   └── admin/
│       └── settings.php       # Plugin settings UI
├── squarespace/
│   └── fikiri-block.json      # SquareSpace block definition
├── replit/
│   └── fikiri-replit.py       # Replit integration package
└── webhooks/
    ├── form_submission.py     # Handle form submissions
    └── lead_capture.py        # Lead capture webhooks
```

---

## 📦 Feature Integration Matrix

| Feature | JavaScript SDK | Widget | REST API | WordPress | SquareSpace | Replit |
|---------|---------------|--------|----------|-----------|-------------|--------|
| **Chatbot** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Lead Capture** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Contact Forms** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Email Automation** | ⚠️ (via webhooks) | ❌ | ✅ | ⚠️ (via plugin) | ⚠️ (via widget) | ✅ |
| **CRM Sync** | ⚠️ (via webhooks) | ❌ | ✅ | ⚠️ (via plugin) | ⚠️ (via widget) | ✅ |
| **Appointment Booking** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🚀 Implementation Plan

### Phase 1: Universal JavaScript SDK (Week 1-2)

**Goal:** Create a single JavaScript SDK that works everywhere

**Features:**
- API key management
- Chatbot integration
- Lead capture
- Form submission handling
- Error handling with exponential backoff retry logic
- Request timeout handling

**Usage Example:**
```html
<!-- Include SDK -->
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>

<!-- Initialize -->
<script>
  Fikiri.init({
    apiKey: 'fik_your_api_key_here',
    tenantId: 'optional_tenant_id',
    features: ['chatbot', 'leadCapture']
  });

  // Use chatbot
  Fikiri.Chatbot.show();
  
  // Capture lead
  Fikiri.LeadCapture.capture({
    email: 'user@example.com',
    name: 'John Doe',
    source: 'website'
  });
</script>
```

### Phase 2: Embeddable Widgets (Week 2-3) ⚠️ **PLANNED**

**Goal:** Pre-built UI components for zero-code integration

**Status:** Widgets are documented but not yet implemented. The SDK includes basic chatbot widget class structure.

**Planned Widgets:**
1. **Chatbot Widget** (Basic structure exists in SDK)
   - Floating chat button
   - Conversation interface
   - Customizable styling
   - Mobile-responsive

2. **Lead Capture Form** (Basic structure exists in SDK)
   - Email/name capture
   - Custom fields support
   - Auto-submit to CRM
   - Success/error handling

3. **Contact Form** (Not yet implemented)
   - Full contact form
   - File uploads
   - Spam protection
   - Email notifications

**Usage Example:**
```html
<!-- Chatbot Widget -->
<div id="fikiri-chatbot" 
     data-api-key="fik_xxx"
     data-theme="light"
     data-position="bottom-right">
</div>

<!-- Lead Capture Form -->
<div id="fikiri-lead-capture"
     data-api-key="fik_xxx"
     data-fields="email,name,phone"
     data-submit-to-crm="true">
</div>
```

### Phase 3: WordPress Plugin (Week 3-4) ⚠️ **PLANNED**

**Goal:** Native WordPress integration

**Status:** Not yet implemented. Clients can use the JavaScript SDK directly in WordPress.

**Planned Features:**
- Admin dashboard for API key management
- Shortcodes for widgets
- Gutenberg blocks
- Settings page
- Auto-updates

**Current Workaround:**
WordPress users can add the SDK script directly to their theme or use a custom HTML block.

### Phase 4: SquareSpace Widget (Week 4) ⚠️ **PLANNED**

**Goal:** SquareSpace block/widget

**Status:** Not yet implemented. Clients can use the JavaScript SDK directly in SquareSpace Code blocks.

**Planned Features:**
- Custom block in SquareSpace editor
- Drag-and-drop integration
- Visual settings panel
- Preview mode

**Current Workaround:**
SquareSpace users can add the SDK script via a Code block.

### Phase 5: Replit Package (Week 4) ⚠️ **PLANNED**

**Goal:** Python package for Replit projects

**Status:** Not yet implemented. Clients can use the REST API directly.

**Planned Features:**
- Python SDK
- Flask/FastAPI helpers
- Example templates
- Documentation

**Current Workaround:**
Replit users can make HTTP requests directly to the REST API endpoints.

### Phase 6: Webhook Integration Layer (Week 5)

**Goal:** Handle form submissions from any platform

**Endpoints:**
- `POST /api/webhooks/forms/submit` - Generic form submission
- `POST /api/webhooks/leads/capture` - Lead capture
- `POST /api/webhooks/contacts/create` - Contact creation

**Features:**
- Signature verification
- Rate limiting
- Retry logic
- Event logging

---

## 🔌 Integration Patterns

### Pattern 1: Chatbot Integration

**For any website:**
```html
<!-- Option 1: Widget (easiest) -->
<script src="https://cdn.fikirisolutions.com/widgets/chatbot.js"
        data-api-key="fik_xxx"
        data-theme="light"></script>

<!-- Option 2: SDK (more control) -->
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({ apiKey: 'fik_xxx' });
  Fikiri.Chatbot.show();
</script>
```

### Pattern 2: Lead Capture

**For any website:**
```html
<!-- Option 1: Widget -->
<div id="fikiri-lead-capture"
     data-api-key="fik_xxx"
     data-fields="email,name"
     data-auto-submit="true">
</div>

<!-- Option 2: Custom form with SDK -->
<form id="my-form">
  <input type="email" id="email" />
  <input type="text" id="name" />
  <button onclick="captureLead()">Submit</button>
</form>

<script>
  function captureLead() {
    Fikiri.LeadCapture.capture({
      email: document.getElementById('email').value,
      name: document.getElementById('name').value,
      source: 'website'
    }).then(result => {
      alert('Thank you!');
    });
  }
</script>
```

### Pattern 3: Form Submission Webhook

**For WordPress/SquareSpace/Replit forms:**
```javascript
// Send form data to Fikiri webhook
fetch('https://api.fikirisolutions.com/api/webhooks/forms/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'fik_xxx'
  },
  body: JSON.stringify({
    form_id: 'contact-form',
    fields: {
      email: 'user@example.com',
      name: 'John Doe',
      message: 'Hello'
    },
    source: 'wordpress'
  })
});
```

---

## 🔐 Authentication & Security

### API Key Management
- Clients get API keys from Fikiri dashboard
- Keys are tenant-scoped (multi-tenant isolation)
- Rate limiting per API key
- Key rotation support

### Webhook Security
- HMAC signature verification
- Timestamp validation (prevent replay attacks)
- IP whitelisting (optional)
- Rate limiting

### CORS Configuration
- Configurable allowed origins per tenant
- Preflight request handling
- Credentials support

---

## 📊 Features Available for Integration

### 1. **Chatbot** ✅
- Natural language Q&A
- Knowledge base search
- Expert escalation
- Multi-turn conversations
- Feedback collection

### 2. **Lead Capture** ✅
- Email/name capture
- Custom fields
- Auto-create CRM leads
- Source tracking
- Duplicate detection

### 3. **Contact Forms** ✅
- Full contact forms
- File uploads
- Email notifications
- CRM integration
- Spam protection

### 4. **Email Automation** ⚠️ (Via Webhooks)
- Trigger automations from website events
- Send automated emails
- Follow-up sequences
- Requires webhook setup

### 5. **CRM Sync** ⚠️ (Via API)
- Create/update leads
- Track activities
- Pipeline management
- Requires API integration

### 6. **Appointment Booking** ✅ (Future)
- Calendar integration
- Availability checking
- Booking confirmation
- Reminders

---

## 🎨 Customization Options

### Widget Styling
- Theme (light/dark/custom)
- Colors (accent, background, text)
- Position (bottom-right, bottom-left, etc.)
- Size and animations

### Behavior
- Auto-show chatbot after delay
- Show on specific pages
- Trigger on exit intent
- Custom triggers

### Data Collection
- Custom fields
- Field validation
- Conditional fields
- Multi-step forms

---

## 📚 Documentation Requirements

### For Each Platform:
1. **Quick Start Guide** (5-minute setup)
2. **API Reference** (full documentation)
3. **Examples** (common use cases)
4. **Troubleshooting** (common issues)
5. **Video Tutorials** (visual guides)

### Integration Guides:
- WordPress: Plugin installation + configuration
- SquareSpace: Block/widget setup
- Replit: Package installation + examples
- Custom Sites: JavaScript SDK usage

---

## 🚦 Implementation Status

### **Phase 1 (Weeks 1-2): Foundation** ✅ **COMPLETE**
- ✅ Universal JavaScript SDK (`integrations/universal/fikiri-sdk.js`)
- ✅ Basic chatbot widget class (in SDK)
- ✅ Basic lead capture widget class (in SDK)
- ✅ Webhook endpoints (`/api/webhooks/forms/submit`, `/api/webhooks/leads/capture`)
- ✅ Integration documentation

### **Phase 2 (Weeks 3-4): Platform Plugins** ⚠️ **PLANNED**
- ⚠️ WordPress plugin (not yet implemented)
- ⚠️ SquareSpace widget (not yet implemented)
- ⚠️ Replit package (not yet implemented)
- ⚠️ Platform-specific docs (basic docs exist, platform-specific guides pending)

### **Phase 3 (Week 5): Advanced Features** ⚠️ **PARTIAL**
- ✅ Webhook integration layer
- ✅ Form submission handling
- ⚠️ Advanced customization (basic customization exists)
- ⚠️ Analytics & tracking (not yet implemented)

---

## 🎯 Success Metrics

- **Adoption:** % of clients using integrations
- **Platforms:** Number of platforms supported
- **Ease of Use:** Time to integrate (target: < 10 minutes)
- **Reliability:** Uptime and error rates
- **Support:** Integration-related support tickets

---

*Last updated: February 2026*
