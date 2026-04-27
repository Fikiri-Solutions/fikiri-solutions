# Integration Quick Start Guide

**Get Fikiri features working on your website in under 10 minutes**

---

## 🚀 Quick Integration (3 Methods)

### Method 1: JavaScript SDK (Recommended)

**Works on:** WordPress, SquareSpace, Shopify, Replit, Custom Sites

```html
<!-- Add to your website's <head> or before </body> -->
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: 'fik_your_api_key_here',
    features: ['chatbot', 'leadCapture']
  });
  
  // Show chatbot
  Fikiri.Chatbot.show();
</script>
```

### Method 2: Widget Script (Coming Soon)

**Status:** Standalone widget scripts are planned but not yet available. Use Method 1 (SDK) instead.

**Planned Usage:**
```html
<!-- Chatbot Widget (Planned) -->
<script src="https://cdn.fikirisolutions.com/widgets/chatbot.js"
        data-api-key="fik_your_api_key_here"
        data-theme="light"
        data-position="bottom-right"></script>

<!-- Lead Capture Form (Planned) -->
<div id="fikiri-lead-capture"
     data-api-key="fik_your_api_key_here"
     data-fields="email,name"
     data-auto-submit="true">
</div>
```

**Current Workaround:** Use Method 1 (SDK) which includes widget functionality.

### Method 3: REST API (For Developers)

**Works on:** Any platform with HTTP support

```javascript
// Capture a lead
fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'fik_your_api_key_here'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    name: 'John Doe',
    source: 'website'
  })
});
```

---

## 📋 Platform-Specific Guides

### WordPress

**Current Method:** Use the JavaScript SDK directly

1. **Add SDK Script**
   - Go to Appearance → Theme Editor (or use a plugin like "Insert Headers and Footers")
   - Add the SDK script before `</body>` tag:
   ```html
   <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
   <script>
     Fikiri.init({ apiKey: 'fik_your_api_key_here' });
     Fikiri.Chatbot.show();
   </script>
   ```

2. **Or Use Custom HTML Block**
   - Add a Custom HTML block to any page
   - Paste the SDK code above

**WordPress Plugin** (Available in repo)
- See `integrations/wordpress/fikiri-plugin.php`
- Includes plugin settings + shortcode support

### SquareSpace

1. **Add Code Block**
   - Edit page → Add Block → Code
   - Paste SDK script (Method 1 above):
   ```html
   <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
   <script>
     Fikiri.init({ apiKey: 'fik_your_api_key_here' });
     Fikiri.Chatbot.show();
   </script>
   ```
   - Save

**SquareSpace Widget** (Planned - Coming Soon)
- Native block/widget in SquareSpace editor

### Shopify

**Method 1: Theme Integration (Easiest - No App Required)**

1. **Add SDK to Theme**
   - Go to **Online Store** → **Themes** → **Actions** → **Edit code**
   - Open `theme.liquid`
   - Add before `</head>`:
   ```liquid
   <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
   <script>
     Fikiri.init({ apiKey: 'fik_your_api_key_here' });
     window.addEventListener('load', function() {
       Fikiri.Chatbot.show({ theme: 'light', position: 'bottom-right' });
     });
   </script>
   ```
   - Save and preview

2. **Add Contact Form** (Optional)
   - Use `integrations/shopify/contact-form.liquid` template
   - Add to your contact page

**Method 2: Shopify App (Full Integration)**
- See `integrations/shopify/app-example.js` for complete app integration
- Supports webhooks for customers, orders, abandoned carts
- Requires Shopify app development

**Full Guide:** See `integrations/shopify/README.md` for detailed instructions

### Replit

**Current Method:** Use REST API directly

1. **Make HTTP Requests**
   ```python
   import requests
   
   # Capture lead
   response = requests.post(
       'https://api.fikirisolutions.com/api/webhooks/leads/capture',
       headers={'X-API-Key': 'fik_your_api_key_here'},
       json={
           'email': 'user@example.com',
           'name': 'John Doe',
           'source': 'replit_app'
       }
   )
   ```

**Replit Examples** (Available in repo)
- See `integrations/replit/README.md`
- Includes Flask/FastAPI/basic integration examples

### Custom HTML Site

Use Method 1 or Method 2 above - works on any HTML page!

---

## 🔑 Getting Your API Key

1. Log into Fikiri dashboard
2. Go to Settings → API Keys
3. Click "Create API Key"
4. Copy the key (starts with `fik_`)
5. Use it in your integration

---

## ✅ Features Available

- ✅ **Chatbot** - AI-powered Q&A
- ✅ **Lead Capture** - Email/name capture forms
- ✅ **Contact Forms** - Full contact forms
- ⚠️ **Email Automation** - Via webhooks
- ⚠️ **CRM Sync** - Via API

---

## 🆘 Need Help?

- **Documentation:** [docs/INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) (API contracts and status)
- **API Reference:** [docs/PUBLIC_API_DOCUMENTATION.md](PUBLIC_API_DOCUMENTATION.md)
- **Support:** info@fikirisolutions.com

---

*Last updated: February 2026*
