# Fikiri Shopify Integration Guide

Integrate Fikiri chatbot, lead capture, and CRM features into your Shopify store.

---

## 🎯 Integration Methods

### Method 1: Theme Integration (Easiest - No App Required)

Add Fikiri SDK directly to your Shopify theme. Works immediately without app store approval.

#### Step 1: Add SDK to Theme

1. Go to **Online Store** → **Themes** → **Actions** → **Edit code**
2. Open `theme.liquid` (or your main layout file)
3. Add before `</head>`:

```liquid
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: 'fik_your_api_key_here',
    features: ['chatbot', 'leadCapture']
  });
  
  // Show chatbot after page load
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>
```

#### Step 2: Add Lead Capture Form (Optional)

Add to any page template (e.g., `page.contact.liquid`):

```liquid
<div id="fikiri-lead-capture">
  <h2>Get in Touch</h2>
  <form id="fikiri-lead-form">
    <div>
      <label>Name:</label>
      <input type="text" name="name" required>
    </div>
    <div>
      <label>Email:</label>
      <input type="email" name="email" required>
    </div>
    <div>
      <label>Phone:</label>
      <input type="tel" name="phone">
    </div>
    <button type="submit">Submit</button>
    <div id="fikiri-form-message"></div>
  </form>
</div>

<script>
  document.getElementById('fikiri-lead-form').addEventListener('submit', function(e) {
    e.preventDefault();
    var formData = new FormData(this);
    
    Fikiri.LeadCapture.capture({
      email: formData.get('email'),
      name: formData.get('name'),
      phone: formData.get('phone'),
      source: 'shopify_store',
      metadata: {
        page_url: window.location.href,
        shop_domain: '{{ shop.domain }}'
      }
    }).then(function(result) {
      var msg = document.getElementById('fikiri-form-message');
      if (result.success) {
        msg.innerHTML = '<p style="color: green;">Thank you! We\'ll be in touch soon.</p>';
        this.reset();
      } else {
        msg.innerHTML = '<p style="color: red;">Error: ' + (result.error || 'Unknown error') + '</p>';
      }
    }.bind(this));
  });
</script>
```

---

### Method 2: Shopify App (Full Integration)

Create a Shopify app for deeper integration (requires app store approval or private app).

#### App Structure

```
shopify-app/
├── app/
│   ├── app.js              # Main app logic
│   ├── webhooks.js         # Webhook handlers
│   └── routes.js           # App routes
├── shopify.app.toml        # App configuration
└── package.json
```

#### Example: Shopify App with Fikiri

```javascript
// app/app.js
import '@shopify/shopify-app/remix';
import { authenticate } from '@shopify/shopify-app/remix/server';

export async function loader({ request }) {
  const { admin } = await authenticate.admin(request);
  
  // Initialize Fikiri SDK for this shop
  return {
    apiKey: process.env.FIKIRI_API_KEY,
    shopDomain: admin.graphql.getShop().domain
  };
}
```

#### Webhook Integration

Subscribe to Shopify webhooks and forward to Fikiri:

```javascript
// app/webhooks.js
import { DeliveryMethod } from '@shopify/shopify-app/remix/server';

export const webhooks = {
  CUSTOMERS_CREATE: {
    deliveryMethod: DeliveryMethod.Http,
    callbackUrl: '/api/webhooks/customers/create',
    callback: async (topic, shop, body, webhookId) => {
      // Forward customer data to Fikiri
      await fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.FIKIRI_API_KEY
        },
        body: JSON.stringify({
          email: body.email,
          name: `${body.first_name} ${body.last_name}`,
          phone: body.phone,
          source: 'shopify_customer',
          metadata: {
            shop_domain: shop,
            customer_id: body.id,
            total_spent: body.total_spent
          }
        })
      });
    }
  },
  
  ORDERS_CREATE: {
    deliveryMethod: DeliveryMethod.Http,
    callbackUrl: '/api/webhooks/orders/create',
    callback: async (topic, shop, body, webhookId) => {
      // Create lead from order
      await fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.FIKIRI_API_KEY
        },
        body: JSON.stringify({
          email: body.email,
          name: `${body.customer.first_name} ${body.customer.last_name}`,
          source: 'shopify_order',
          metadata: {
            shop_domain: shop,
            order_id: body.id,
            order_total: body.total_price,
            order_items: body.line_items.map(item => ({
              product_id: item.product_id,
              quantity: item.quantity,
              price: item.price
            }))
          }
        })
      });
    }
  }
};
```

---

### Method 3: Script Tags (For Storefront)

Add Fikiri SDK via Script Tags API (requires app with script tag permission).

```javascript
// Add script tag via Shopify Admin API
const scriptTag = {
  event: 'onload',
  src: 'https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js'
};

await admin.rest.resources.ScriptTag.create({
  session: session,
  event: scriptTag.event,
  src: scriptTag.src
});
```

Then initialize in theme:

```liquid
<script>
  // Wait for SDK to load
  if (typeof Fikiri !== 'undefined') {
    Fikiri.init({
      apiKey: 'fik_your_api_key_here',
      features: ['chatbot', 'leadCapture']
    });
    Fikiri.Chatbot.show();
  } else {
    window.addEventListener('load', function() {
      if (typeof Fikiri !== 'undefined') {
        Fikiri.init({ apiKey: 'fik_your_api_key_here' });
        Fikiri.Chatbot.show();
      }
    });
  }
</script>
```

---

## 🔐 Security Best Practices

### 1. Use API Keys with Origin Restrictions

When creating your Fikiri API key, restrict it to your Shopify domain:

```python
# In Fikiri dashboard or via API
api_key_manager.generate_api_key(
    user_id=user_id,
    name="Shopify Store Integration",
    allowed_origins=[
        'https://your-store.myshopify.com',
        'https://your-store.com'
    ],
    scopes=['webhooks:leads', 'leads:create']
)
```

### 2. Validate Webhook Signatures

If using Shopify webhooks, validate signatures:

```javascript
import crypto from 'crypto';

function verifyShopifyWebhook(data, hmacHeader) {
  const hash = crypto
    .createHmac('sha256', process.env.SHOPIFY_WEBHOOK_SECRET)
    .update(data, 'utf8')
    .digest('base64');
  
  return hash === hmacHeader;
}
```

---

## 📊 Use Cases

### 1. Customer Support Chatbot

Add AI chatbot to help customers:
- Answer product questions
- Provide shipping information
- Handle returns/exchanges
- Escalate to human support

### 2. Lead Capture from Abandoned Carts

Capture leads when customers abandon carts:

```javascript
// In Shopify theme
document.addEventListener('DOMContentLoaded', function() {
  // Track cart abandonment
  if (window.Shopify && window.Shopify.checkout) {
    window.addEventListener('beforeunload', function() {
      if (cart.item_count > 0) {
        Fikiri.LeadCapture.capture({
          email: checkout.email,
          source: 'shopify_abandoned_cart',
          metadata: {
            cart_value: cart.total_price,
            items: cart.items
          }
        });
      }
    });
  }
});
```

### 3. Post-Purchase Lead Enrichment

Enrich customer data after purchase:

```javascript
// In order confirmation page
if (typeof Fikiri !== 'undefined') {
  Fikiri.Forms.submit({
    form_id: 'shopify_order',
    fields: {
      email: '{{ order.email }}',
      name: '{{ order.customer.name }}',
      phone: '{{ order.customer.phone }}',
      order_total: '{{ order.total_price }}',
      order_items: {{ order.line_items | json }}
    },
    source: 'shopify_order_confirmation'
  });
}
```

---

## 🛠️ Shopify-Specific Features

### Customer Data Sync

Sync Shopify customers to Fikiri CRM:

```javascript
// Via Shopify Admin API
const customers = await admin.rest.resources.Customer.all({
  session: session
});

for (const customer of customers.data) {
  await fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': process.env.FIKIRI_API_KEY
    },
    body: JSON.stringify({
      email: customer.email,
      name: `${customer.first_name} ${customer.last_name}`,
      phone: customer.phone,
      source: 'shopify_customer_sync',
      metadata: {
        shopify_customer_id: customer.id,
        total_orders: customer.orders_count,
        total_spent: customer.total_spent
      }
    })
  });
}
```

### Order Tracking Integration

Track orders and create leads:

```javascript
// Webhook handler for order creation
app.post('/api/webhooks/shopify/orders/create', async (req, res) => {
  const order = req.body;
  
  // Create lead in Fikiri
  const response = await fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': process.env.FIKIRI_API_KEY
    },
    body: JSON.stringify({
      email: order.email,
      name: `${order.customer.first_name} ${order.customer.last_name}`,
      source: 'shopify_order',
      metadata: {
        order_id: order.id,
        order_number: order.order_number,
        total: order.total_price,
        currency: order.currency,
        items: order.line_items
      }
    })
  });
  
  res.status(200).send('OK');
});
```

---

## 📝 Quick Start Checklist

- [ ] Get Fikiri API key from dashboard
- [ ] Choose integration method (Theme, App, or Script Tag)
- [ ] Add SDK to Shopify theme or app
- [ ] Configure API key with origin restrictions
- [ ] Test chatbot on storefront
- [ ] Test lead capture form
- [ ] Set up webhooks (optional, for app integration)
- [ ] Verify leads appear in Fikiri CRM

---

## 🔗 Resources

- [Shopify Theme Development](https://shopify.dev/docs/themes)
- [Shopify App Development](https://shopify.dev/docs/apps)
- [Shopify Webhooks](https://shopify.dev/docs/api/webhooks)
- [Fikiri API Documentation](https://docs.fikirisolutions.com)

---

## 💡 Tips

1. **Theme Integration** is fastest - no app approval needed
2. **App Integration** provides deeper access but requires development
3. **Use Origin Restrictions** on API keys for security
4. **Test in Development Store** before going live
5. **Monitor Webhook Delivery** if using app integration

---

*Need help? Contact support@fikirisolutions.com*
