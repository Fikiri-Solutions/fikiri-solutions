# External Uptime Monitoring Configuration
# Pingdom, Healthchecks.io, and custom monitoring setup

## 🎯 **RECOMMENDED MONITORING SERVICES**

### **1. Healthchecks.io (Recommended - Free Tier)**
- **Free Plan**: 20 checks, 1-minute intervals
- **Setup**: https://healthchecks.io
- **Perfect for**: Small to medium applications

### **2. Pingdom (Enterprise)**
- **Paid Service**: $10-50/month per check
- **Features**: Advanced monitoring, detailed reports
- **Perfect for**: Enterprise applications

### **3. UptimeRobot (Free Tier)**
- **Free Plan**: 50 monitors, 5-minute intervals
- **Setup**: https://uptimerobot.com
- **Perfect for**: Multiple endpoints monitoring

---

## 🔧 **HEALTHCHECK.IO SETUP**

### **Step 1: Create Account**
1. Go to https://healthchecks.io
2. Sign up for free account
3. Verify email address

### **Step 2: Create Health Checks**

#### **Backend Health Check**
```bash
# Check URL
https://api.fikirisolutions.com/health

# Expected Response
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "email_service": "healthy"
  }
}

# Check Interval: 1 minute
# Timeout: 30 seconds
# Retry: 3 times
```

#### **Frontend Health Check**
```bash
# Check URL
https://fikirisolutions.com

# Expected Response
HTTP 200 OK

# Check Interval: 1 minute
# Timeout: 30 seconds
# Retry: 3 times
```

#### **API Health Check**
```bash
# Check URL
https://api.fikirisolutions.com/api/health

# Expected Response
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}

# Check Interval: 1 minute
# Timeout: 30 seconds
# Retry: 3 times
```

### **Step 3: Configure Notifications**
```bash
# Email Notifications
- Primary: admin@fikirisolutions.com
- Secondary: support@fikirisolutions.com

# Slack Notifications
- Webhook: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
- Channel: #alerts

# SMS Notifications (Optional)
- Phone: +1-555-0123
```

---

## 🔧 **PINGDOM SETUP**

### **Step 1: Create Account**
1. Go to https://www.pingdom.com
2. Sign up for paid account
3. Choose plan (Basic: $10/month)

### **Step 2: Create Monitors**

#### **Backend Monitor**
```bash
# Monitor Type: HTTP
# URL: https://api.fikirisolutions.com/health
# Check Interval: 1 minute
# Locations: Multiple (US, EU, Asia)
# Alert Threshold: 2 failures
# Recovery Threshold: 1 success
```

#### **Frontend Monitor**
```bash
# Monitor Type: HTTP
# URL: https://fikirisolutions.com
# Check Interval: 1 minute
# Locations: Multiple (US, EU, Asia)
# Alert Threshold: 2 failures
# Recovery Threshold: 1 success
```

#### **API Performance Monitor**
```bash
# Monitor Type: HTTP
# URL: https://api.fikirisolutions.com/api/health
# Check Interval: 1 minute
# Locations: Multiple (US, EU, Asia)
# Alert Threshold: 2 failures
# Recovery Threshold: 1 success
# Performance Threshold: 2 seconds
```

### **Step 3: Configure Alerts**
```bash
# Email Alerts
- Primary: admin@fikirisolutions.com
- Secondary: support@fikirisolutions.com

# Slack Alerts
- Webhook: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
- Channel: #alerts

# SMS Alerts
- Phone: +1-555-0123
- Only for critical outages
```

---

## 🔧 **UPTIMEROBOT SETUP**

### **Step 1: Create Account**
1. Go to https://uptimerobot.com
2. Sign up for free account
3. Verify email address

### **Step 2: Create Monitors**

#### **Backend Monitor**
```bash
# Monitor Type: HTTP(s)
# URL: https://api.fikirisolutions.com/health
# Check Interval: 5 minutes
# Monitor Timeout: 30 seconds
# Alert Contacts: Email + Slack
```

#### **Frontend Monitor**
```bash
# Monitor Type: HTTP(s)
# URL: https://fikirisolutions.com
# Check Interval: 5 minutes
# Monitor Timeout: 30 seconds
# Alert Contacts: Email + Slack
```

#### **API Monitor**
```bash
# Monitor Type: HTTP(s)
# URL: https://api.fikirisolutions.com/api/health
# Check Interval: 5 minutes
# Monitor Timeout: 30 seconds
# Alert Contacts: Email + Slack
```

---

## 🔧 **CUSTOM MONITORING SETUP**

### **Health Check Endpoints**

#### **Basic Health Check**
```python
# URL: /health
# Method: GET
# Response: 200 OK
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

#### **Detailed Health Check**
```python
# URL: /health/detailed
# Method: GET
# Response: 200 OK
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2
    },
    "external_services": {
      "gmail_api": "healthy",
      "openai_api": "healthy",
      "stripe_api": "healthy"
    }
  }
}
```

#### **Readiness Check**
```python
# URL: /health/ready
# Method: GET
# Response: 200 OK
{
  "status": "ready",
  "timestamp": "2024-01-01T00:00:00Z",
  "checks": {
    "database": "ready",
    "redis": "ready",
    "external_services": "ready"
  }
}
```

#### **Liveness Check**
```python
# URL: /health/live
# Method: GET
# Response: 200 OK
{
  "status": "alive",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 🔧 **MONITORING CONFIGURATION**

### **Environment Variables**
```bash
# Health Check Configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=60
HEALTH_CHECK_TIMEOUT=30

# Monitoring Services
PINGDOM_API_KEY=your-pingdom-api-key
UPTIMEROBOT_API_KEY=your-uptimerobot-api-key
HEALTHCHECKS_IO_API_KEY=your-healthchecks-io-api-key

# Alert Configuration
ALERT_EMAIL_PRIMARY=admin@fikirisolutions.com
ALERT_EMAIL_SECONDARY=support@fikirisolutions.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
ALERT_SMS_PHONE=+1-555-0123
```

### **Monitoring Script**
```python
#!/usr/bin/env python3
"""
External Monitoring Script
Checks health endpoints and sends alerts
"""

import requests
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExternalMonitor:
    def __init__(self):
        self.endpoints = [
            {
                'name': 'Backend Health',
                'url': 'https://api.fikirisolutions.com/health',
                'timeout': 30,
                'expected_status': 200
            },
            {
                'name': 'Frontend Health',
                'url': 'https://fikirisolutions.com',
                'timeout': 30,
                'expected_status': 200
            },
            {
                'name': 'API Health',
                'url': 'https://api.fikirisolutions.com/api/health',
                'timeout': 30,
                'expected_status': 200
            }
        ]
    
    def check_endpoint(self, endpoint):
        """Check a single endpoint"""
        try:
            response = requests.get(
                endpoint['url'],
                timeout=endpoint['timeout']
            )
            
            if response.status_code == endpoint['expected_status']:
                logger.info(f"✅ {endpoint['name']}: OK")
                return True
            else:
                logger.error(f"❌ {endpoint['name']}: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ {endpoint['name']}: Timeout")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ {endpoint['name']}: Connection Error")
            return False
        except Exception as e:
            logger.error(f"❌ {endpoint['name']}: {e}")
            return False
    
    def run_checks(self):
        """Run all health checks"""
        logger.info(f"Running health checks at {datetime.now()}")
        
        results = {}
        for endpoint in self.endpoints:
            results[endpoint['name']] = self.check_endpoint(endpoint)
        
        # Check if all endpoints are healthy
        all_healthy = all(results.values())
        
        if all_healthy:
            logger.info("🎉 All endpoints are healthy!")
        else:
            logger.error("🚨 Some endpoints are unhealthy!")
            # Send alert here
        
        return results

def main():
    monitor = ExternalMonitor()
    
    # Run checks every 5 minutes
    while True:
        monitor.run_checks()
        time.sleep(300)  # 5 minutes

if __name__ == '__main__':
    main()
```

---

## 🔧 **DEPLOYMENT CONFIGURATION**

### **Render.com Configuration**
```yaml
# render.yaml
services:
  - type: web
    name: fikiri-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
    healthCheckPath: /health
    healthCheckGracePeriod: 30
    envVars:
      - key: HEALTH_CHECK_ENABLED
        value: true
      - key: HEALTH_CHECK_INTERVAL
        value: 60
```

### **Vercel Configuration**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/frontend/dist/$1"
    }
  ],
  "functions": {
    "frontend/dist/index.html": {
      "maxDuration": 30
    }
  }
}
```

---

## 🔧 **ALERTING CONFIGURATION**

### **Slack Webhook Setup**
```bash
# 1. Go to https://api.slack.com/apps
# 2. Create new app
# 3. Add Incoming Webhooks
# 4. Create webhook for #alerts channel
# 5. Copy webhook URL
```

### **Email Alert Setup**
```bash
# 1. Configure SMTP settings
# 2. Set up email templates
# 3. Configure alert recipients
# 4. Test email delivery
```

### **SMS Alert Setup**
```bash
# 1. Use Twilio or similar service
# 2. Configure phone numbers
# 3. Set up SMS templates
# 4. Test SMS delivery
```

---

## 🔧 **MONITORING DASHBOARD**

### **Health Check Dashboard**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Fikiri Solutions - Health Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .healthy { background-color: #d4edda; color: #155724; }
        .unhealthy { background-color: #f8d7da; color: #721c24; }
        .endpoint { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>Fikiri Solutions - Health Dashboard</h1>
    <div id="status"></div>
    <div id="endpoints"></div>
    
    <script>
        async function checkHealth() {
            try {
                const response = await fetch('/health/detailed');
                const data = await response.json();
                
                document.getElementById('status').innerHTML = `
                    <div class="status ${data.status === 'healthy' ? 'healthy' : 'unhealthy'}">
                        Overall Status: ${data.status.toUpperCase()}
                    </div>
                `;
                
                let endpointsHtml = '';
                for (const [service, status] of Object.entries(data.services)) {
                    endpointsHtml += `
                        <div class="endpoint">
                            <strong>${service}:</strong> 
                            <span class="${status === 'healthy' ? 'healthy' : 'unhealthy'}">
                                ${status}
                            </span>
                        </div>
                    `;
                }
                
                document.getElementById('endpoints').innerHTML = endpointsHtml;
                
            } catch (error) {
                document.getElementById('status').innerHTML = `
                    <div class="status unhealthy">
                        Error: ${error.message}
                    </div>
                `;
            }
        }
        
        checkHealth();
        setInterval(checkHealth, 30000); // Check every 30 seconds
    </script>
</body>
</html>
```

---

## 🎯 **RECOMMENDED SETUP**

### **For Production:**
1. **Primary**: Healthchecks.io (free tier)
2. **Secondary**: UptimeRobot (free tier)
3. **Backup**: Custom monitoring script

### **For Enterprise:**
1. **Primary**: Pingdom (paid)
2. **Secondary**: Healthchecks.io (paid)
3. **Backup**: Custom monitoring script

### **Alert Configuration:**
1. **Email**: Primary and secondary contacts
2. **Slack**: #alerts channel
3. **SMS**: Critical outages only

---

## 🚀 **NEXT STEPS**

1. **Choose monitoring service** (recommend Healthchecks.io)
2. **Set up health check endpoints**
3. **Configure alerts** (email + Slack)
4. **Test monitoring** (simulate outages)
5. **Set up dashboard** (optional)
6. **Document procedures** (incident response)

---

## 📞 **SUPPORT**

- **Healthchecks.io**: https://healthchecks.io/docs/
- **Pingdom**: https://www.pingdom.com/support/
- **UptimeRobot**: https://uptimerobot.com/support/
