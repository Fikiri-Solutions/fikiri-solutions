# Domain and SSL Configuration Guide
# Complete setup for fikirisolutions.com domain and SSL certificates

## 🎯 **DOMAIN CONFIGURATION**

### **Current Domain Status**
- **Domain**: fikirisolutions.com
- **Registrar**: [Your domain registrar]
- **DNS Provider**: [Your DNS provider]
- **SSL Status**: [Current SSL status]

---

## 🔧 **DNS CONFIGURATION**

### **Required DNS Records**

#### **A Records (IPv4)**
```bash
# Production Frontend (Vercel)
fikirisolutions.com.          A    76.76.19.61
www.fikirisolutions.com.      A    76.76.19.61

# Production Backend (Render)
api.fikirisolutions.com.      A    167.99.123.45

# Staging Environment
staging.fikirisolutions.com.  A    76.76.19.62
api-staging.fikirisolutions.com. A 167.99.123.46
```

#### **CNAME Records**
```bash
# Vercel Frontend
fikirisolutions.com.          CNAME cname.vercel-dns.com.
www.fikirisolutions.com.      CNAME cname.vercel-dns.com.

# Render Backend
api.fikirisolutions.com.      CNAME fikirisolutions.onrender.com.
api-staging.fikirisolutions.com. CNAME fikirisolutions-staging.onrender.com.
```

#### **MX Records (Email)**
```bash
# Primary Email Server
fikirisolutions.com.          MX   10 mail.fikirisolutions.com.

# Backup Email Server
fikirisolutions.com.          MX   20 mail2.fikirisolutions.com.
```

#### **TXT Records**
```bash
# Domain Verification
fikirisolutions.com.          TXT  "v=spf1 include:_spf.google.com ~all"

# DMARC Policy
_dmarc.fikirisolutions.com.   TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@fikirisolutions.com"

# Domain Verification (Vercel)
fikirisolutions.com.          TXT  "vercel-domain-verify=your-verification-code"
```

---

## 🔒 **SSL CERTIFICATE CONFIGURATION**

### **Vercel SSL (Frontend)**
```bash
# Automatic SSL
- Vercel provides free SSL certificates
- Automatically renewed
- Supports wildcard domains
- HTTP/2 enabled
- HSTS enabled

# Configuration
1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings > Domains
4. Add fikirisolutions.com
5. Add www.fikirisolutions.com
6. Verify domain ownership
7. SSL will be automatically provisioned
```

### **Render SSL (Backend)**
```bash
# Automatic SSL
- Render provides free SSL certificates
- Automatically renewed
- Supports custom domains
- HTTP/2 enabled

# Configuration
1. Go to Render Dashboard
2. Select your service
3. Go to Settings > Custom Domains
4. Add api.fikirisolutions.com
5. Add api-staging.fikirisolutions.com
6. Verify domain ownership
7. SSL will be automatically provisioned
```

### **Custom SSL (Optional)**
```bash
# Let's Encrypt (Free)
- Free SSL certificates
- 90-day validity
- Automatic renewal
- Wildcard support

# Installation
sudo apt-get install certbot
sudo certbot certonly --manual -d fikirisolutions.com -d www.fikirisolutions.com
sudo certbot certonly --manual -d api.fikirisolutions.com

# Auto-renewal
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 🔧 **VERCEL DOMAIN SETUP**

### **Step 1: Add Domain to Vercel**
```bash
# 1. Go to Vercel Dashboard
# 2. Select your project
# 3. Go to Settings > Domains
# 4. Click "Add Domain"
# 5. Enter: fikirisolutions.com
# 6. Click "Add"
```

### **Step 2: Configure DNS**
```bash
# Vercel will provide DNS instructions
# Typically requires CNAME record:
fikirisolutions.com.          CNAME cname.vercel-dns.com.
www.fikirisolutions.com.      CNAME cname.vercel-dns.com.
```

### **Step 3: Verify Domain**
```bash
# Vercel will provide verification methods:
# 1. DNS TXT record
# 2. HTML file upload
# 3. Meta tag verification

# Recommended: DNS TXT record
fikirisolutions.com.          TXT  "vercel-domain-verify=your-verification-code"
```

### **Step 4: SSL Configuration**
```bash
# SSL is automatically enabled
# Check SSL status in Vercel dashboard
# Ensure HTTPS redirect is enabled
# Configure HSTS headers
```

---

## 🔧 **RENDER DOMAIN SETUP**

### **Step 1: Add Domain to Render**
```bash
# 1. Go to Render Dashboard
# 2. Select your service
# 3. Go to Settings > Custom Domains
# 4. Click "Add Custom Domain"
# 5. Enter: api.fikirisolutions.com
# 6. Click "Add"
```

### **Step 2: Configure DNS**
```bash
# Render will provide DNS instructions
# Typically requires A record:
api.fikirisolutions.com.      A    167.99.123.45

# Or CNAME record:
api.fikirisolutions.com.      CNAME fikirisolutions.onrender.com.
```

### **Step 3: SSL Configuration**
```bash
# SSL is automatically enabled
# Check SSL status in Render dashboard
# Ensure HTTPS redirect is enabled
# Configure security headers
```

---

## 🔧 **STAGING ENVIRONMENT SETUP**

### **Staging Domains**
```bash
# Frontend Staging
staging.fikirisolutions.com

# Backend Staging
api-staging.fikirisolutions.com
```

### **DNS Configuration**
```bash
# Staging Frontend
staging.fikirisolutions.com.  CNAME cname.vercel-dns.com.

# Staging Backend
api-staging.fikirisolutions.com. CNAME fikirisolutions-staging.onrender.com.
```

---

## 🔧 **SECURITY HEADERS CONFIGURATION**

### **Vercel Security Headers**
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        },
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=31536000; includeSubDomains; preload"
        }
      ]
    }
  ]
}
```

### **Render Security Headers**
```python
# In your Flask app
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    return response
```

---

## 🔧 **HTTPS REDIRECT CONFIGURATION**

### **Vercel HTTPS Redirect**
```json
{
  "redirects": [
    {
      "source": "http://fikirisolutions.com/(.*)",
      "destination": "https://fikirisolutions.com/$1",
      "permanent": true
    },
    {
      "source": "http://www.fikirisolutions.com/(.*)",
      "destination": "https://www.fikirisolutions.com/$1",
      "permanent": true
    }
  ]
}
```

### **Render HTTPS Redirect**
```python
# In your Flask app
@app.before_request
def force_https():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://'), code=301)
```

---

## 🔧 **DOMAIN VERIFICATION**

### **Google Search Console**
```bash
# 1. Go to Google Search Console
# 2. Add property: fikirisolutions.com
# 3. Verify ownership using:
#    - HTML file upload
#    - DNS TXT record
#    - Google Analytics
#    - Google Tag Manager

# DNS TXT record method:
fikirisolutions.com.          TXT  "google-site-verification=your-verification-code"
```

### **Bing Webmaster Tools**
```bash
# 1. Go to Bing Webmaster Tools
# 2. Add site: fikirisolutions.com
# 3. Verify ownership using:
#    - HTML file upload
#    - DNS TXT record
#    - Meta tag verification

# DNS TXT record method:
fikirisolutions.com.          TXT  "ms-domain-verification=your-verification-code"
```

---

## 🔧 **EMAIL CONFIGURATION**

### **Google Workspace Setup**
```bash
# 1. Go to Google Workspace
# 2. Add domain: fikirisolutions.com
# 3. Verify domain ownership
# 4. Configure MX records
# 5. Set up email accounts

# MX Records:
fikirisolutions.com.          MX   10 aspmx.l.google.com.
fikirisolutions.com.          MX   20 alt1.aspmx.l.google.com.
fikirisolutions.com.          MX   20 alt2.aspmx.l.google.com.
fikirisolutions.com.          MX   20 alt3.aspmx.l.google.com.
fikirisolutions.com.          MX   20 alt4.aspmx.l.google.com.
```

### **SPF Record**
```bash
# SPF Record
fikirisolutions.com.          TXT  "v=spf1 include:_spf.google.com ~all"
```

### **DKIM Record**
```bash
# DKIM Record (provided by Google)
google._domainkey.fikirisolutions.com. TXT "v=DKIM1; k=rsa; p=your-public-key"
```

### **DMARC Record**
```bash
# DMARC Record
_dmarc.fikirisolutions.com.   TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@fikirisolutions.com"
```

---

## 🔧 **MONITORING CONFIGURATION**

### **SSL Certificate Monitoring**
```bash
# Use SSL monitoring services:
# 1. SSL Labs (https://www.ssllabs.com/ssltest/)
# 2. SSL Checker (https://www.sslchecker.com/)
# 3. SSL Monitor (https://sslmonitor.com/)

# Monitor these domains:
# - fikirisolutions.com
# - www.fikirisolutions.com
# - api.fikirisolutions.com
# - staging.fikirisolutions.com
# - api-staging.fikirisolutions.com
```

### **DNS Monitoring**
```bash
# Use DNS monitoring services:
# 1. DNS Checker (https://dnschecker.org/)
# 2. DNS Monitor (https://dnsmonitor.com/)
# 3. Pingdom DNS monitoring

# Monitor DNS propagation
# Check DNS response times
# Monitor DNS record changes
```

---

## 🔧 **TROUBLESHOOTING**

### **Common DNS Issues**
```bash
# Issue: Domain not resolving
# Solution: Check DNS propagation
# Command: nslookup fikirisolutions.com

# Issue: SSL certificate not working
# Solution: Check certificate status
# Command: openssl s_client -connect fikirisolutions.com:443

# Issue: HTTPS redirect not working
# Solution: Check redirect configuration
# Command: curl -I http://fikirisolutions.com
```

### **SSL Certificate Issues**
```bash
# Issue: Certificate not trusted
# Solution: Check certificate chain
# Command: openssl s_client -connect fikirisolutions.com:443 -showcerts

# Issue: Certificate expired
# Solution: Renew certificate
# Command: Check renewal status in Vercel/Render dashboard

# Issue: Mixed content warnings
# Solution: Ensure all resources use HTTPS
# Command: Check browser console for mixed content errors
```

---

## 🔧 **DEPLOYMENT CHECKLIST**

### **Pre-Deployment**
- [ ] Domain registered and configured
- [ ] DNS records configured
- [ ] SSL certificates provisioned
- [ ] Security headers configured
- [ ] HTTPS redirect enabled
- [ ] Email configuration complete

### **Post-Deployment**
- [ ] Domain resolves correctly
- [ ] SSL certificate valid
- [ ] HTTPS redirect working
- [ ] Security headers present
- [ ] Email delivery working
- [ ] Monitoring configured

---

## 🚀 **NEXT STEPS**

1. **Configure DNS records** (A, CNAME, MX, TXT)
2. **Set up Vercel domain** (frontend)
3. **Set up Render domain** (backend)
4. **Verify SSL certificates** (automatic)
5. **Configure security headers**
6. **Set up email** (Google Workspace)
7. **Test domain resolution**
8. **Monitor SSL status**

---

## 📞 **SUPPORT**

- **Vercel Support**: https://vercel.com/support
- **Render Support**: https://render.com/support
- **Domain Registrar**: [Your registrar support]
- **DNS Provider**: [Your DNS provider support]
