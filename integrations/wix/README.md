# Fikiri Wix Integration Guide

Integrate Fikiri chatbot, lead capture, and CRM features into your Wix site.

---

## 🎯 Integration Methods

### Method 1: Wix Velo (Corvid) - Recommended

**Best for:** Full control and customization

#### Step 1: Add SDK Script

1. Go to **Dev Mode** → **Site Structure** → **Public** → **masterPage.js**
2. Add SDK script in the `onReady` function:

```javascript
import wixWindow from 'wix-window';

$w.onReady(function () {
  // Load Fikiri SDK
  const script = document.createElement('script');
  script.src = 'https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js';
  script.onload = function() {
    // Initialize Fikiri
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
  };
  document.head.appendChild(script);
});
```

#### Step 2: Add Lead Capture Form

Create a form in Wix and add this code to handle submission:

```javascript
import wixData from 'wix-data';

export function button1_click(event) {
  // Get form data
  const email = $w('#inputEmail').value;
  const name = $w('#inputName').value;
  const phone = $w('#inputPhone').value;
  
  // Capture lead via Fikiri SDK
  if (typeof Fikiri !== 'undefined') {
    Fikiri.LeadCapture.capture({
      email: email,
      name: name,
      phone: phone,
      source: 'wix_site',
      metadata: {
        page_url: wixWindow.location.url,
        site_name: wixWindow.location.hostname
      }
    }).then(function(result) {
      if (result.success) {
        $w('#successMessage').show();
        $w('#inputEmail').value = '';
        $w('#inputName').value = '';
        $w('#inputPhone').value = '';
      } else {
        $w('#errorMessage').text = 'Error: ' + (result.error || 'Unknown error');
        $w('#errorMessage').show();
      }
    });
  }
}
```

---

### Method 2: HTML Embed - Easiest

**Best for:** Quick integration without Dev Mode

#### Step 1: Add HTML Embed Element

1. Go to **Add** → **Embed** → **HTML Code**
2. Add this code:

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

#### Step 2: Position the Embed

- Drag the HTML embed element to your desired location
- For chatbot: Place in footer or use absolute positioning
- For forms: Place where you want the form

---

### Method 3: Wix App Market (Coming Soon)

**Best for:** Native integration with app store approval

**Status:** Planned - Native Wix app for deeper integration

**Features (Planned):**
- App settings panel
- Native Wix components
- Wix Data integration
- Wix Stores integration

---

## 📋 Use Cases

### 1. Contact Form Integration

Replace Wix contact form with Fikiri lead capture:

```javascript
import wixData from 'wix-data';

export function contactForm_submit(event) {
  event.preventDefault();
  
  const formData = event.detail;
  
  if (typeof Fikiri !== 'undefined') {
    Fikiri.Forms.submit({
      form_id: 'wix_contact_form',
      fields: {
        email: formData.email,
        name: formData.name,
        phone: formData.phone,
        message: formData.message
      },
      source: 'wix_contact_page',
      metadata: {
        page_url: wixWindow.location.url,
        form_id: 'contact-form'
      }
    }).then(function(result) {
      if (result.success) {
        // Show success message
        $w('#successMessage').show();
      }
    });
  }
}
```

### 2. Wix Stores Integration

Capture leads from product pages:

```javascript
import wixStores from 'wix-stores-frontend';

$w.onReady(function () {
  // Track product views
  if (typeof Fikiri !== 'undefined' && Fikiri.track) {
    const product = wixStores.getCurrentProduct();
    
    Fikiri.track('product_view', {
      product_id: product.id,
      product_name: product.name,
      product_price: product.price
    });
  }
  
  // Capture lead on "Contact Us" button click
  $w('#contactButton').onClick(function() {
    Fikiri.LeadCapture.capture({
      email: $w('#emailInput').value,
      source: 'wix_product_page',
      metadata: {
        product_id: product.id,
        product_name: product.name
      }
    });
  });
});
```

### 3. Wix Bookings Integration

Capture leads from booking forms:

```javascript
import wixBookings from 'wix-bookings-frontend';

$w.onReady(function () {
  // Capture lead when booking form is submitted
  $w('#bookingForm').onSubmit(function(event) {
    const bookingData = event.detail;
    
    if (typeof Fikiri !== 'undefined') {
      Fikiri.LeadCapture.capture({
        email: bookingData.email,
        name: bookingData.name,
        phone: bookingData.phone,
        source: 'wix_booking',
        metadata: {
          service_id: bookingData.serviceId,
          booking_date: bookingData.date,
          booking_time: bookingData.time
        }
      });
    }
  });
});
```

---

## 🔐 Security Best Practices

### 1. Use API Keys with Origin Restrictions

When creating your Fikiri API key, restrict it to your Wix domain:

```python
# In Fikiri dashboard or via API
api_key_manager.generate_api_key(
    user_id=user_id,
    name="Wix Site Integration",
    allowed_origins=[
        'https://your-site.wixsite.com',
        'https://your-domain.com'
    ],
    scopes=['webhooks:leads', 'leads:create']
)
```

### 2. Store API Key Securely

**Option 1: Environment Variable (Recommended)**
```javascript
// In Wix Velo, use Secrets Manager
import wixSecrets from 'wix-secrets-backend';

const apiKey = await wixSecrets.getSecret('FIKIRI_API_KEY');
```

**Option 2: Wix Secrets Manager**
1. Go to **Settings** → **Secrets Manager**
2. Add secret: `FIKIRI_API_KEY` = `fik_your_key_here`
3. Use in code:

```javascript
import wixSecrets from 'wix-secrets-backend';

$w.onReady(async function () {
  const apiKey = await wixSecrets.getSecret('FIKIRI_API_KEY');
  Fikiri.init({ apiKey: apiKey });
});
```

---

## 🎨 Customization

### Custom Chatbot Styling

```javascript
Fikiri.Chatbot.show({
  theme: 'light',  // or 'dark'
  position: 'bottom-right',  // or 'bottom-left', 'top-right', 'top-left'
  title: 'Chat with Us',
  primaryColor: '#0f766e',  // Your brand color
  borderRadius: '12px',
  width: '380px',
  height: '600px'
});
```

### Custom Form Fields

```javascript
Fikiri.Forms.submit({
  form_id: 'custom_wix_form',
  fields: {
    email: email,
    name: name,
    phone: phone,
    custom_field_1: customValue1,
    custom_field_2: customValue2
  },
  source: 'wix_custom_form'
});
```

---

## 📝 Quick Start Checklist

- [ ] Get Fikiri API key from dashboard
- [ ] Choose integration method (Velo or HTML Embed)
- [ ] Add SDK script to your Wix site
- [ ] Configure API key (use Secrets Manager for security)
- [ ] Test chatbot on your site
- [ ] Test lead capture form
- [ ] Verify leads appear in Fikiri CRM
- [ ] Customize styling to match your brand

---

## 🔗 Resources

- [Wix Velo Documentation](https://www.wix.com/velo)
- [Wix HTML Embed Guide](https://support.wix.com/en/article/adding-html-code-to-your-site)
- [Wix Secrets Manager](https://support.wix.com/en/article/velo-using-secrets)
- [Fikiri API Documentation](https://docs.fikirisolutions.com)

---

## 💡 Tips

1. **Use Velo for Production** - More control and better performance
2. **Use HTML Embed for Quick Tests** - Faster to set up
3. **Store API Keys Securely** - Use Wix Secrets Manager
4. **Test in Preview Mode** - Before publishing changes
5. **Monitor Lead Capture** - Check Fikiri dashboard regularly

---

## 🆘 Troubleshooting

### SDK Not Loading
- Check browser console for errors
- Verify script URL is correct
- Ensure script loads before initialization

### API Key Errors
- Verify API key is correct
- Check origin restrictions match your Wix domain
- Verify API key has required scopes

### Form Not Submitting
- Check form event handlers are attached
- Verify Fikiri SDK is loaded
- Check browser console for errors

---

*Need help? Contact support@fikirisolutions.com*
