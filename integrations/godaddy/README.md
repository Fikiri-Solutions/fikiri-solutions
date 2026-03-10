# Fikiri GoDaddy Website Builder Integration Guide

Integrate Fikiri chatbot, lead capture, and CRM features into your GoDaddy website.

---

## 🎯 Integration Methods

### Method 1: Custom HTML Block (Easiest)

**Best for:** Quick integration without code

#### Step 1: Add Custom HTML Block

1. Go to **Website** → **Edit Site**
2. Click **Add Section** → **Custom HTML**
3. Paste this code:

```html
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: 'fik_your_api_key_here',
        features: ['chatbot', 'leadCapture']
      });
      
      // Show chatbot
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>
```

#### Step 2: Position the Block

- For chatbot: Place in footer or use absolute positioning
- For forms: Place where you want the form to appear

---

### Method 2: Site-Wide Integration

**Best for:** Adding chatbot to all pages

#### Step 1: Add to Site Header/Footer

1. Go to **Settings** → **Site Settings** → **Code**
2. Add to **Header Code** or **Footer Code**:

```html
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: 'fik_your_api_key_here',
        features: ['chatbot', 'leadCapture']
      });
      
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>
```

---

### Method 3: Contact Form Integration

**Best for:** Replacing GoDaddy contact form with Fikiri lead capture

#### Step 1: Create Custom Contact Form

1. Add **Custom HTML** block to your contact page
2. Add this form HTML:

```html
<div id="fikiri-contact-form" style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2>Contact Us</h2>
  <form id="contact-form">
    <div style="margin-bottom: 15px;">
      <label for="name" style="display: block; margin-bottom: 5px;">Name *</label>
      <input type="text" id="name" name="name" required 
             style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
    </div>
    
    <div style="margin-bottom: 15px;">
      <label for="email" style="display: block; margin-bottom: 5px;">Email *</label>
      <input type="email" id="email" name="email" required 
             style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
    </div>
    
    <div style="margin-bottom: 15px;">
      <label for="phone" style="display: block; margin-bottom: 5px;">Phone</label>
      <input type="tel" id="phone" name="phone" 
             style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
    </div>
    
    <div style="margin-bottom: 15px;">
      <label for="message" style="display: block; margin-bottom: 5px;">Message *</label>
      <textarea id="message" name="message" rows="5" required 
                style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"></textarea>
    </div>
    
    <button type="submit" 
            style="width: 100%; padding: 12px; background: #0f766e; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;">
      Send Message
    </button>
    
    <div id="form-message" style="margin-top: 15px;"></div>
  </form>
</div>

<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  document.getElementById('contact-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    var formData = new FormData(this);
    var messageDiv = document.getElementById('form-message');
    messageDiv.innerHTML = '<p style="color: #666;">Sending...</p>';
    
    if (typeof Fikiri !== 'undefined') {
      Fikiri.Forms.submit({
        form_id: 'godaddy_contact_form',
        fields: {
          email: formData.get('email'),
          name: formData.get('name'),
          phone: formData.get('phone'),
          message: formData.get('message')
        },
        source: 'godaddy_contact_page',
        metadata: {
          page_url: window.location.href,
          site_domain: window.location.hostname
        }
      }).then(function(result) {
        if (result.success) {
          messageDiv.innerHTML = '<p style="color: green; font-weight: bold;">Thank you! We\'ll be in touch soon.</p>';
          this.reset();
        } else {
          messageDiv.innerHTML = '<p style="color: red;">Error: ' + (result.error || 'Unknown error') + '</p>';
        }
      }.bind(this)).catch(function(error) {
        messageDiv.innerHTML = '<p style="color: red;">Error submitting form. Please try again.</p>';
      });
    }
  });
</script>
```

---

## 📋 Use Cases

### 1. Lead Capture on Product Pages

Add to product/service pages:

```html
<div id="product-lead-capture" style="margin: 20px 0;">
  <h3>Interested? Get a Quote</h3>
  <form id="quote-form">
    <input type="email" id="quote-email" placeholder="Your email" required>
    <input type="text" id="quote-name" placeholder="Your name" required>
    <button type="submit">Get Quote</button>
  </form>
</div>

<script>
  document.getElementById('quote-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    if (typeof Fikiri !== 'undefined') {
      Fikiri.LeadCapture.capture({
        email: document.getElementById('quote-email').value,
        name: document.getElementById('quote-name').value,
        source: 'godaddy_product_page',
        metadata: {
          page_url: window.location.href,
          product_name: document.querySelector('h1')?.textContent || 'Unknown'
        }
      }).then(function(result) {
        if (result.success) {
          alert('Thank you! We\'ll contact you soon.');
          this.reset();
        }
      }.bind(this));
    }
  });
</script>
```

### 2. Newsletter Signup Integration

Replace GoDaddy email marketing with Fikiri:

```html
<div id="newsletter-signup">
  <h3>Subscribe to Our Newsletter</h3>
  <form id="newsletter-form">
    <input type="email" id="newsletter-email" placeholder="Enter your email" required>
    <button type="submit">Subscribe</button>
  </form>
</div>

<script>
  document.getElementById('newsletter-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    if (typeof Fikiri !== 'undefined') {
      Fikiri.LeadCapture.capture({
        email: document.getElementById('newsletter-email').value,
        source: 'godaddy_newsletter',
        metadata: {
          subscription_type: 'newsletter',
          page_url: window.location.href
        }
      }).then(function(result) {
        if (result.success) {
          alert('Thanks for subscribing!');
          this.reset();
        }
      }.bind(this));
    }
  });
</script>
```

---

## 🔐 Security Best Practices

### 1. Use API Keys with Origin Restrictions

When creating your Fikiri API key, restrict it to your GoDaddy domain:

```python
# In Fikiri dashboard or via API
api_key_manager.generate_api_key(
    user_id=user_id,
    name="GoDaddy Site Integration",
    allowed_origins=[
        'https://your-site.godaddysites.com',
        'https://your-domain.com'
    ],
    scopes=['webhooks:leads', 'leads:create']
)
```

### 2. Keep API Key Secure

- **Don't** hardcode API key in visible HTML
- **Do** use environment variables if possible (GoDaddy Website Builder has limited support)
- **Do** restrict API key origins to your specific domain
- **Do** use scoped API keys (only necessary permissions)

---

## 🎨 Customization

### Custom Chatbot Styling

```javascript
Fikiri.Chatbot.show({
  theme: 'light',  // or 'dark'
  position: 'bottom-right',  // or 'bottom-left', 'top-right', 'top-left'
  title: 'Chat with Us',
  primaryColor: '#0f766e',  // Your brand color
  borderRadius: '12px'
});
```

### Custom Form Styling

Add custom CSS in **Settings** → **Site Settings** → **Code** → **Header Code**:

```html
<style>
  #fikiri-contact-form {
    font-family: 'Your Font', sans-serif;
  }
  
  #fikiri-contact-form input,
  #fikiri-contact-form textarea {
    border: 2px solid #your-color;
  }
  
  #fikiri-contact-form button {
    background: #your-brand-color;
  }
</style>
```

---

## 📝 Quick Start Checklist

- [ ] Get Fikiri API key from dashboard
- [ ] Choose integration method (HTML Block or Site-Wide)
- [ ] Add SDK script to your GoDaddy site
- [ ] Configure API key with origin restrictions
- [ ] Test chatbot on your site
- [ ] Test lead capture form
- [ ] Verify leads appear in Fikiri CRM
- [ ] Customize styling to match your brand

---

## 🔗 Resources

- [GoDaddy Website Builder Help](https://www.godaddy.com/help)
- [GoDaddy Custom HTML Guide](https://www.godaddy.com/help/add-custom-html-to-your-website-40847)
- [Fikiri API Documentation](https://docs.fikirisolutions.com)

---

## 💡 Tips

1. **Use Custom HTML Block** - Easiest method for most users
2. **Site-Wide Integration** - Best for chatbot on all pages
3. **Test in Preview Mode** - Before publishing changes
4. **Monitor Lead Capture** - Check Fikiri dashboard regularly
5. **Customize Styling** - Match your brand colors and fonts

---

## 🆘 Troubleshooting

### SDK Not Loading
- Check browser console for errors
- Verify script URL is correct
- Ensure script loads before initialization
- Try adding script to footer instead of header

### API Key Errors
- Verify API key is correct
- Check origin restrictions match your GoDaddy domain
- Verify API key has required scopes

### Form Not Submitting
- Check form event handlers are attached
- Verify Fikiri SDK is loaded
- Check browser console for errors
- Ensure form has `preventDefault()` on submit

---

*Need help? Contact support@fikirisolutions.com*
