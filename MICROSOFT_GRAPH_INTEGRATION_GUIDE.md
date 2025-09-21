# 🔗 **MICROSOFT GRAPH API INTEGRATION GUIDE**

## ✅ **IMPLEMENTATION STATUS**

### **Completed:**
- ✅ Microsoft Graph client service (`core/microsoft_graph.py`)
- ✅ Backend authentication endpoints (`/api/auth/microsoft/*`)
- ✅ Frontend Microsoft login button (`Login.tsx`)
- ✅ Email management endpoints (`/api/microsoft/emails`)
- ✅ Calendar integration endpoints (`/api/microsoft/calendar`)
- ✅ User profile endpoints (`/api/microsoft/user/profile`)

### **Ready for Configuration:**
- 🔧 Microsoft App Registration setup
- 🔧 Environment variables configuration
- 🔧 OAuth callback URL setup

---

## 🚀 **SETUP INSTRUCTIONS**

### **Step 1: Microsoft App Registration**

1. **Go to Azure Portal:**
   - Visit: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
   - Sign in with your Microsoft 365 admin account

2. **Create New App Registration:**
   ```
   Name: Fikiri Solutions Microsoft Integration
   Supported account types: Accounts in this organizational directory only
   Redirect URI: https://fikirisolutions.onrender.com/api/auth/microsoft/callback
   ```

3. **Configure API Permissions:**
   - Go to "API permissions" → "Add a permission" → "Microsoft Graph"
   - Add these **Delegated permissions**:
     - `User.Read` (Sign in and read user profile)
     - `Mail.Read` (Read user mail)
     - `Mail.Send` (Send mail as user)
     - `Calendars.Read` (Read user calendars)
     - `Calendars.ReadWrite` (Have full access to user calendars)
     - `offline_access` (Maintain access to data)

4. **Grant Admin Consent:**
   - Click "Grant admin consent for [Your Organization]"
   - Confirm the consent

5. **Create Client Secret:**
   - Go to "Certificates & secrets" → "New client secret"
   - Description: "Fikiri Production Secret"
   - Expires: 24 months (recommended)
   - **Copy the secret value immediately** (you won't see it again)

6. **Copy Configuration Values:**
   ```
   Application (client) ID: [Copy this]
   Directory (tenant) ID: [Copy this]
   Client secret value: [Copy this]
   ```

### **Step 2: Environment Configuration**

Update your environment variables:

```bash
# Microsoft Graph API Configuration
MICROSOFT_CLIENT_ID=your_application_client_id_here
MICROSOFT_CLIENT_SECRET=your_client_secret_value_here
MICROSOFT_TENANT_ID=your_directory_tenant_id_here
MICROSOFT_REDIRECT_URI=https://fikirisolutions.onrender.com/api/auth/microsoft/callback
```

### **Step 3: Test the Integration**

1. **Start your application:**
   ```bash
   # Backend
   cd /Users/mac/Downloads/Fikiri
   python app.py
   
   # Frontend (in another terminal)
   cd frontend
   npm start
   ```

2. **Test Microsoft Login:**
   - Go to http://localhost:3000/login
   - Click the "Microsoft" button
   - Complete OAuth flow
   - Verify redirect to onboarding

---

## 📧 **MICROSOFT EMAIL INTEGRATION**

### **Available Endpoints:**

```javascript
// Get user emails
GET /api/microsoft/emails?user_id=123&limit=50

// Send email
POST /api/microsoft/send-email
{
  "user_id": "123",
  "to": "client@example.com",
  "subject": "Your landscaping quote",
  "body": "<h1>Thank you for your inquiry!</h1>"
}

// Get user profile
GET /api/microsoft/user/profile?user_id=123
```

### **Frontend Integration Example:**

```typescript
// Get Microsoft emails
const fetchMicrosoftEmails = async (userId: string) => {
  const response = await fetch(
    `https://fikirisolutions.onrender.com/api/microsoft/emails?user_id=${userId}&limit=20`
  );
  const data = await response.json();
  return data.data; // Array of MicrosoftEmail objects
};

// Send email via Microsoft
const sendMicrosoftEmail = async (userId: string, to: string, subject: string, body: string) => {
  const response = await fetch(
    'https://fikirisolutions.onrender.com/api/microsoft/send-email',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, to, subject, body })
    }
  );
  return response.json();
};
```

---

## 📅 **MICROSOFT CALENDAR INTEGRATION**

### **Available Endpoints:**

```javascript
// Get calendar events
GET /api/microsoft/calendar?user_id=123&days_ahead=7

// Create calendar event
POST /api/microsoft/create-event
{
  "user_id": "123",
  "subject": "Landscaping Consultation",
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T11:00:00Z",
  "attendees": ["client@example.com"],
  "body": "Meeting to discuss landscaping needs"
}
```

### **Frontend Integration Example:**

```typescript
// Get calendar events
const fetchMicrosoftCalendar = async (userId: string, daysAhead: number = 7) => {
  const response = await fetch(
    `https://fikirisolutions.onrender.com/api/microsoft/calendar?user_id=${userId}&days_ahead=${daysAhead}`
  );
  const data = await response.json();
  return data.data; // Calendar events
};

// Create calendar event
const createMicrosoftEvent = async (
  userId: string,
  subject: string,
  startTime: string,
  endTime: string,
  attendees: string[] = []
) => {
  const response = await fetch(
    'https://fikirisolutions.onrender.com/api/microsoft/create-event',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        subject,
        start_time: startTime,
        end_time: endTime,
        attendees
      })
    }
  );
  return response.json();
};
```

---

## 🔧 **ADVANCED CONFIGURATION**

### **App-Only Authentication (Optional)**

For background services that need to access data for all users:

1. **Add Application Permissions:**
   - `User.Read.All` (Read all users' profiles)
   - `Mail.Read` (Read mail in all mailboxes)
   - `Calendars.Read` (Read calendars of all users)

2. **Use Confidential Client:**
   ```python
   from core.microsoft_graph import MicrosoftGraphClient, MicrosoftGraphConfig
   
   config = MicrosoftGraphConfig()
   client = MicrosoftGraphClient(config)
   
   # For app-only auth, use client credentials flow
   result = client.acquire_token_silent(scopes=['https://graph.microsoft.com/.default'])
   ```

### **Error Handling**

The Microsoft Graph service includes comprehensive error handling:

```python
# Example error handling
try:
    result = microsoft_graph_service.get_user_emails()
    if result['success']:
        emails = result['emails']
    else:
        logger.error(f"Graph API error: {result['error']}")
except Exception as e:
    logger.error(f"Service error: {e}")
```

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues:**

1. **"Microsoft Graph not configured"**
   - Check environment variables are set correctly
   - Verify MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID

2. **"Invalid redirect URI"**
   - Ensure redirect URI in Azure matches exactly: `https://fikirisolutions.onrender.com/api/auth/microsoft/callback`
   - Check for trailing slashes or HTTP vs HTTPS

3. **"Insufficient privileges"**
   - Verify admin consent has been granted
   - Check that all required permissions are added

4. **"Token expired"**
   - The service automatically refreshes tokens
   - If persistent, check refresh token is being stored correctly

### **Debug Mode:**

Enable debug logging in your environment:

```bash
LOG_LEVEL=DEBUG
MICROSOFT_DEBUG=true
```

---

## 📊 **MONITORING & ANALYTICS**

### **Track Microsoft Integration Usage:**

```python
# Track Microsoft login events
business_analytics.track_event('microsoft_login', {
    'user_id': user_id,
    'login_method': 'oauth',
    'timestamp': datetime.now().isoformat()
});

# Track email operations
business_analytics.track_event('microsoft_email_sent', {
    'user_id': user_id,
    'recipient_domain': email.split('@')[1],
    'email_type': 'automated_response'
});
```

---

## 🔐 **SECURITY CONSIDERATIONS**

1. **Token Storage:**
   - Tokens are stored in Flask sessions (server-side)
   - Consider moving to Redis for production scalability

2. **Scope Limitation:**
   - Only request necessary permissions
   - Regularly audit granted permissions

3. **Token Expiration:**
   - Implement proper token refresh logic
   - Handle token expiration gracefully

4. **Rate Limiting:**
   - Microsoft Graph has rate limits
   - Implement exponential backoff for retries

---

## 🎯 **NEXT STEPS**

1. **Complete Microsoft App Registration** following Step 1 above
2. **Update environment variables** with your Microsoft credentials
3. **Test the integration** using the provided endpoints
4. **Integrate with your CRM** to sync Microsoft contacts
5. **Add calendar scheduling** to your landscaping workflow
6. **Implement email automation** using Microsoft Graph

---

## 📚 **ADDITIONAL RESOURCES**

- [Microsoft Graph Documentation](https://learn.microsoft.com/en-us/graph/)
- [Python Microsoft Graph SDK](https://github.com/microsoftgraph/msgraph-sdk-python)
- [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
- [Azure App Registration Guide](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

---

**🎉 Your Microsoft Graph integration is ready! Follow the setup steps above to start using Microsoft 365 services in your Fikiri application.**
