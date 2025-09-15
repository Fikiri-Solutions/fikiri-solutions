# Production Guardrails & Security

## 🛡️ Frontend Security

### Environment Variables
```bash
# .env.production
VITE_API_URL=https://fikirisolutions.onrender.com/api
VITE_SENTRY_DSN=your_sentry_dsn_here
VITE_ANALYTICS_ID=your_analytics_id_here
```

### Feature Flags for Risky UI
```typescript
// config.ts - Feature flags for gradual rollout
export const features = {
  // Stable features
  dashboard: true,
  services: true,
  crm: true,
  
  // Beta features (gradual rollout)
  newCharts: false,        // New chart types
  templates: false,        // Email templates
  advancedSettings: false, // Complex configurations
  
  // Experimental features
  realTimeUpdates: false,  // WebSocket features
  aiInsights: false,      // AI-powered insights
}
```

### Error Boundary Implementation
```typescript
// ErrorBoundary.tsx
import React from 'react';
import { ErrorPage } from './pages/ErrorPages';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Send to monitoring service
  }

  render() {
    if (this.state.hasError) {
      return <ErrorPage />;
    }

    return this.props.children;
  }
}
```

## 🔒 Backend Security

### Rate Limiting
```python
# Add to app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to specific endpoints
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    pass

@app.route('/api/test/<service>', methods=['POST'])
@limiter.limit("10 per minute")
def api_test_service(service):
    pass
```

### CORS Configuration
```python
# Enhanced CORS security
CORS(app, origins=[
    'https://fikirisolutions.com',
    'https://www.fikirisolutions.com',
    'https://fikirisolutions.vercel.app',
    'http://localhost:3000'  # Development only
], supports_credentials=True)
```

### Security Headers
```python
# Add security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

## 📊 Monitoring & Alerting

### Uptime Monitoring
```bash
# Pingdom/UptimeRobot configuration
# Monitor these endpoints:
# - https://fikirisolutions.onrender.com/api/health
# - https://fikirisolutions.vercel.app/
# - https://fikirisolutions.com/

# Alert thresholds:
# - Response time > 2s
# - Uptime < 99.9%
# - Error rate > 1%
```

### Error Tracking
```python
# Add to Flask app
import logging
from datetime import datetime

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500
```

### Performance Monitoring
```python
# Add response time tracking
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        logging.info(f"Response time: {response_time:.3f}s")
        
        # Alert if response time > 1s
        if response_time > 1.0:
            logging.warning(f"Slow response: {response_time:.3f}s")
    
    return response
```

## 🔐 API Key Management

### Key Rotation Schedule
```python
# Quarterly key rotation
# 1. Generate new API keys
# 2. Update environment variables
# 3. Deploy with new keys
# 4. Monitor for errors
# 5. Remove old keys after 24h

# Key validation
def validate_api_key(key):
    if not key or len(key) < 20:
        raise ValueError("Invalid API key format")
    return True
```

### PII Logging Redaction
```python
import re

def redact_pii(data):
    """Redact personally identifiable information from logs"""
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            if any(pii_field in key.lower() for pii_field in ['email', 'phone', 'ssn', 'password']):
                redacted[key] = '[REDACTED]'
            else:
                redacted[key] = redact_pii(value)
        return redacted
    elif isinstance(data, str):
        # Redact email addresses
        data = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', data)
        # Redact phone numbers
        data = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', data)
        return data
    return data
```

## 🚨 Incident Response

### Alert Escalation
```python
# Alert levels and responses
ALERT_LEVELS = {
    'critical': {
        'threshold': 'uptime < 95%',
        'response_time': '5 minutes',
        'escalation': 'immediate'
    },
    'warning': {
        'threshold': 'response_time > 2s',
        'response_time': '30 minutes',
        'escalation': 'email'
    },
    'info': {
        'threshold': 'new deployment',
        'response_time': 'next business day',
        'escalation': 'slack'
    }
}
```

### Rollback Procedures
```bash
# Quick rollback commands
# Frontend (Vercel)
vercel rollback [deployment-url]

# Backend (Render)
# Use Render dashboard to rollback to previous deployment

# Database
# Restore from latest backup if needed
```

## 📋 Security Checklist

### Pre-deployment
- [ ] **Environment Variables**: No secrets in code
- [ ] **API Keys**: Rotated and validated
- [ ] **Dependencies**: Updated and scanned
- [ ] **CORS**: Restricted to production domains
- [ ] **Rate Limiting**: Configured for all endpoints
- [ ] **Security Headers**: Implemented
- [ ] **Error Handling**: No sensitive data in errors
- [ ] **Logging**: PII redaction enabled

### Post-deployment
- [ ] **Health Checks**: All endpoints responding
- [ ] **Monitoring**: Alerts configured
- [ ] **Performance**: Within budget limits
- [ ] **Security Scan**: No vulnerabilities
- [ ] **Backup**: Database backed up
- [ ] **Documentation**: Updated
- [ ] **Team Notification**: Deployment complete
