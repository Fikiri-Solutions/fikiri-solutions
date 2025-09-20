# 🎯 Fikiri Solutions - Stripe API Integration Guide

## 📚 **Using Stripe API with Your Fikiri Billing System**

Based on the Stripe API documentation you're viewing, here's how to use the key endpoints with your Fikiri Solutions implementation:

---

## 🚀 **Core API Endpoints for Fikiri**

### **1. Products & Pricing Management**

#### **Create Fikiri Products**
```bash
# Create Starter product
curl https://api.stripe.com/v1/products \
  -u sk_test_your-secret-key: \
  -d name="Fikiri Starter" \
  -d description="Perfect for solo entrepreneurs and growing small businesses" \
  -d type="service" \
  -d "metadata[tier]=starter"

# Create Growth product  
curl https://api.stripe.com/v1/products \
  -u sk_test_your-secret-key: \
  -d name="Fikiri Growth" \
  -d description="Scale your operations with advanced AI and integrations" \
  -d type="service" \
  -d "metadata[tier]=growth"
```

#### **Create Pricing**
```bash
# Create monthly price for Starter ($39/month)
curl https://api.stripe.com/v1/prices \
  -u sk_test_your-secret-key: \
  -d product="prod_starter_id" \
  -d unit_amount=3900 \
  -d currency=usd \
  -d "recurring[interval]=month"

# Create annual price for Starter ($390/year)
curl https://api.stripe.com/v1/prices \
  -u sk_test_your-secret-key: \
  -d product="prod_starter_id" \
  -d unit_amount=39000 \
  -d currency=usd \
  -d "recurring[interval]=year"
```

### **2. Customer Management**

#### **Create Customers**
```bash
# Create new customer
curl https://api.stripe.com/v1/customers \
  -u sk_test_your-secret-key: \
  -d email="customer@example.com" \
  -d name="John Doe" \
  -d "metadata[user_id]=12345" \
  -d "metadata[source]=fikiri_signup"
```

#### **Get Customer Details**
```bash
# Get customer information
curl https://api.stripe.com/v1/customers/cus_customer_id \
  -u sk_test_your-secret-key:
```

### **3. Subscription Management**

#### **Create Subscription with Free Trial**
```bash
# Create subscription with 14-day trial
curl https://api.stripe.com/v1/subscriptions \
  -u sk_test_your-secret-key: \
  -d customer="cus_customer_id" \
  -d "items[0][price]=price_starter_monthly" \
  -d trial_period_days=14 \
  -d payment_behavior=default_incomplete \
  -d "payment_settings[save_default_payment_method]=on_subscription"
```

#### **Get Subscription Details**
```bash
# Get subscription information
curl https://api.stripe.com/v1/subscriptions/sub_subscription_id \
  -u sk_test_your-secret-key:
```

#### **Cancel Subscription**
```bash
# Cancel subscription at period end
curl https://api.stripe.com/v1/subscriptions/sub_subscription_id \
  -u sk_test_your-secret-key: \
  -d cancel_at_period_end=true
```

### **4. Checkout Sessions**

#### **Create Checkout Session with Trial**
```bash
# Create checkout session with free trial
curl https://api.stripe.com/v1/checkout/sessions \
  -u sk_test_your-secret-key: \
  -d "line_items[0][price]=price_starter_monthly" \
  -d "line_items[0][quantity]=1" \
  -d mode=subscription \
  -d success_url="https://fikirisolutions.com/dashboard?success=true" \
  -d cancel_url="https://fikirisolutions.com/pricing?canceled=true" \
  -d trial_period_days=14 \
  -d allow_promotion_codes=true \
  -d billing_address_collection=required \
  -d customer_creation=always
```

### **5. Webhook Configuration**

#### **Create Webhook Endpoint**
```bash
# Create webhook endpoint for your server
curl https://api.stripe.com/v1/webhook_endpoints \
  -u sk_test_your-secret-key: \
  -d url="https://your-domain.com/api/billing/webhook" \
  -d "enabled_events[]=customer.subscription.created" \
  -d "enabled_events[]=customer.subscription.updated" \
  -d "enabled_events[]=customer.subscription.deleted" \
  -d "enabled_events[]=customer.subscription.trial_will_end" \
  -d "enabled_events[]=invoice.payment_succeeded" \
  -d "enabled_events[]=invoice.payment_failed" \
  -d "enabled_events[]=checkout.session.completed"
```

---

## 🛠️ **Python Integration Examples**

### **Using Your FikiriStripeManager**

```python
from core.fikiri_stripe_manager import FikiriStripeManager

# Initialize manager
stripe_manager = FikiriStripeManager()

# Create customer
customer = stripe_manager.create_customer(
    email="user@example.com",
    name="John Doe",
    metadata={"user_id": "12345"}
)

# Create subscription with trial
subscription = stripe_manager.create_subscription(
    customer_id=customer['id'],
    price_id="price_starter_monthly",
    trial_days=14
)

# Create checkout session
session = stripe_manager.create_checkout_session(
    price_id="price_starter_monthly",
    success_url="https://fikirisolutions.com/dashboard?success=true",
    cancel_url="https://fikirisolutions.com/pricing?canceled=true"
)
```

### **Using Stripe Python Library Directly**

```python
import stripe

# Set your secret key
stripe.api_key = "sk_test_your-secret-key"

# Create customer
customer = stripe.Customer.create(
    email="customer@example.com",
    name="John Doe",
    metadata={"user_id": "12345"}
)

# Create subscription with trial
subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[{'price': 'price_starter_monthly'}],
    trial_period_days=14,
    payment_behavior='default_incomplete',
    payment_settings={
        'save_default_payment_method': 'on_subscription'
    }
)

# Create checkout session
session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    line_items=[{
        'price': 'price_starter_monthly',
        'quantity': 1,
    }],
    mode='subscription',
    success_url='https://fikirisolutions.com/dashboard?success=true',
    cancel_url='https://fikirisolutions.com/pricing?canceled=true',
    trial_period_days=14,
    allow_promotion_codes=True,
    billing_address_collection='required',
    customer_creation='always'
)
```

---

## 📊 **Key Stripe Objects for Fikiri**

### **1. Products**
- **Fikiri Starter**: Basic AI automation
- **Fikiri Growth**: Advanced AI + integrations  
- **Fikiri Business**: White-label + custom integrations
- **Fikiri Enterprise**: Custom AI + dedicated support

### **2. Prices**
- **Monthly**: $39, $79, $199, $399
- **Annual**: $390, $790, $1990, $3990 (10% discount)

### **3. Features (Entitlements)**
- `basic_ai`: Basic AI responses
- `advanced_ai`: Advanced AI with context
- `custom_ai`: Custom AI training
- `email_parsing`: Email parsing
- `basic_crm`: Basic CRM
- `advanced_crm`: Advanced CRM
- `white_label`: White-label options
- `custom_integrations`: Custom integrations

### **4. Usage Limits**
- **Email Processing**: 500, 2000, 10000, unlimited
- **Lead Storage**: 100, 1000, 5000, unlimited
- **AI Responses**: 200, 800, 4000, unlimited
- **Users**: 1, 3, unlimited, unlimited

---

## 🔧 **Testing Your Integration**

### **1. Test Mode Setup**
```bash
# Use test API keys
export STRIPE_SECRET_KEY="sk_test_your-test-key"
export STRIPE_PUBLISHABLE_KEY="pk_test_your-test-key"
```

### **2. Test Cards**
```bash
# Successful payment
4242424242424242

# Declined payment  
4000000000000002

# Requires authentication
4000002500003155
```

### **3. Test Webhooks**
```bash
# Install Stripe CLI
stripe listen --forward-to localhost:5000/api/billing/webhook

# Trigger test events
stripe trigger customer.subscription.created
stripe trigger invoice.payment_succeeded
```

---

## 🎯 **Next Steps**

### **1. Run Setup Scripts**
```bash
# Set up complete billing system
python setup_stripe_billing.py

# Configure free trials
python configure_free_trials.py
```

### **2. Test Integration**
```bash
# Start your Flask app
python app.py

# Test API endpoints
curl http://localhost:5000/api/billing/pricing
curl -X POST http://localhost:5000/api/billing/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"price_id": "price_starter_monthly"}'
```

### **3. Configure Webhooks**
1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://your-domain.com/api/billing/webhook`
3. Select events: `customer.subscription.*`, `invoice.*`, `checkout.session.*`
4. Copy webhook secret to your environment variables

---

## 🚀 **You're Ready to Launch!**

Your Fikiri Solutions billing system is now fully integrated with Stripe's API. You can:

- ✅ **Create subscriptions** with 14-day free trials
- ✅ **Handle payments** automatically
- ✅ **Track usage** for overage billing
- ✅ **Manage features** with entitlements
- ✅ **Process webhooks** for real-time updates

**Start generating recurring revenue with your AI-powered business automation platform!** 🎉
