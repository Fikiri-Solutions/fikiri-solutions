# Sentry Logging Integration Guide

## 📊 **OVERVIEW**

This guide explains how to use Sentry's logging capabilities in the Fikiri Solutions application. With `enable_logs=True` configured, you can send logs directly to Sentry for better error tracking and debugging.

---

## 🚀 **QUICK START**

### ✅ **Sentry SDK Logger**
```python
import sentry_sdk

# Send logs directly to Sentry
sentry_sdk.logger.info('This is an info log message')
sentry_sdk.logger.warning('This is a warning message')
sentry_sdk.logger.error('This is an error message')
```

### ✅ **Python Built-in Logging**
```python
import logging

# Your existing logging setup
logger = logging.getLogger(__name__)

# These logs will be automatically sent to Sentry
logger.info('This will be sent to Sentry')
logger.warning('User login failed')
logger.error('Something went wrong')
```

---

## 🔧 **CONFIGURATION**

### ✅ **Current Sentry Configuration**
```python
sentry_sdk.init(
    dsn="https://05d4170350ee081a3bfee0dda0220df6@o4510053728845824.ingest.us.sentry.io/4510053767249920",
    integrations=[
        FlaskIntegration(),
        RedisIntegration(),
        SqlalchemyIntegration(),
        LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
    ],
    # Enable logs to be sent to Sentry
    enable_logs=True,
    send_default_pii=True,
    traces_sample_rate=0.1,
    environment=os.getenv('FLASK_ENV', 'production'),
    release=os.getenv('GITHUB_SHA', 'unknown'),
)
```

---

## 📝 **LOGGING EXAMPLES**

### ✅ **Basic Logging**
```python
import sentry_sdk
import logging

# Method 1: Direct Sentry logging
sentry_sdk.logger.info('User logged in successfully')
sentry_sdk.logger.warning('API rate limit approaching')
sentry_sdk.logger.error('Database connection failed')

# Method 2: Python logging (automatically forwarded)
logger = logging.getLogger(__name__)
logger.info('Processing user request')
logger.warning('High memory usage detected')
logger.error('Payment processing failed')
```

### ✅ **Structured Logging with Context**
```python
import sentry_sdk
from sentry_sdk import set_context, set_tag, set_user

# Add context to logs
set_user({"id": "user123", "email": "user@example.com"})
set_tag("service", "payment")
set_context("payment", {
    "amount": 100.00,
    "currency": "USD",
    "method": "credit_card"
})

# Log with context
sentry_sdk.logger.info('Payment processing started')
sentry_sdk.logger.error('Payment failed - insufficient funds')
```

### ✅ **Error Logging with Stack Traces**
```python
import sentry_sdk
import traceback

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    # Log error with stack trace
    sentry_sdk.logger.error(f'Operation failed: {str(e)}')
    sentry_sdk.logger.error(f'Stack trace: {traceback.format_exc()}')
    
    # Or capture exception directly
    sentry_sdk.capture_exception(e)
```

### ✅ **Performance Logging**
```python
import sentry_sdk
import time

# Log performance metrics
start_time = time.time()
# ... perform operation ...
duration = time.time() - start_time

sentry_sdk.logger.info(f'Operation completed in {duration:.2f} seconds')
```

---

## 🎯 **USE CASES**

### ✅ **API Endpoint Logging**
```python
from flask import request
import sentry_sdk

@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        # Log request start
        sentry_sdk.logger.info(f'Creating user: {request.json.get("email")}')
        
        # Process request
        user = create_user_service(request.json)
        
        # Log success
        sentry_sdk.logger.info(f'User created successfully: {user.id}')
        return jsonify(user), 201
        
    except Exception as e:
        # Log error
        sentry_sdk.logger.error(f'User creation failed: {str(e)}')
        return jsonify({'error': str(e)}), 400
```

### ✅ **Database Operation Logging**
```python
import sentry_sdk
from core.minimal_crm_service import MinimalCRMService

def log_database_operations():
    crm_service = MinimalCRMService()
    
    try:
        # Log database query
        sentry_sdk.logger.info('Fetching leads from database')
        leads = crm_service.get_leads()
        
        # Log results
        sentry_sdk.logger.info(f'Retrieved {len(leads)} leads')
        
    except Exception as e:
        # Log database error
        sentry_sdk.logger.error(f'Database operation failed: {str(e)}')
```

### ✅ **External API Logging**
```python
import sentry_sdk
import requests

def call_external_api():
    try:
        # Log API call
        sentry_sdk.logger.info('Calling external API: Gmail')
        
        response = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages')
        
        # Log response
        sentry_sdk.logger.info(f'API call successful: {response.status_code}')
        
    except requests.RequestException as e:
        # Log API error
        sentry_sdk.logger.error(f'External API call failed: {str(e)}')
```

### ✅ **Authentication Logging**
```python
import sentry_sdk
from core.minimal_auth import MinimalAuthenticator

def log_authentication():
    auth = MinimalAuthenticator()
    
    try:
        # Log authentication attempt
        sentry_sdk.logger.info('User authentication attempt')
        
        if auth.is_authenticated():
            sentry_sdk.logger.info('User authenticated successfully')
        else:
            sentry_sdk.logger.warning('User authentication failed')
            
    except Exception as e:
        # Log authentication error
        sentry_sdk.logger.error(f'Authentication error: {str(e)}')
```

---

## 🔍 **LOGGING LEVELS**

### ✅ **Available Log Levels**
```python
import sentry_sdk

# Debug level (most verbose)
sentry_sdk.logger.debug('Debug information')

# Info level (general information)
sentry_sdk.logger.info('General information')

# Warning level (potential issues)
sentry_sdk.logger.warning('Warning message')

# Error level (errors that don't stop execution)
sentry_sdk.logger.error('Error message')

# Critical level (serious errors)
sentry_sdk.logger.critical('Critical error')
```

### ✅ **Log Level Configuration**
```python
# In monitoring.py
LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)
```

---

## 📊 **MONITORING & ALERTING**

### ✅ **Log-Based Alerts**
```python
import sentry_sdk
from core.monitoring import alert_manager

def log_with_alerting():
    try:
        # Normal operation
        sentry_sdk.logger.info('Processing user request')
        
    except Exception as e:
        # Log error
        sentry_sdk.logger.error(f'Request processing failed: {str(e)}')
        
        # Send alert
        alert_manager.alert_error(
            f'Request processing failed: {str(e)}',
            {'error': str(e), 'endpoint': 'user_request'}
        )
```

### ✅ **Performance Monitoring**
```python
import sentry_sdk
import time
from core.monitoring import performance_monitor

def log_performance():
    start_time = time.time()
    
    try:
        # Perform operation
        result = expensive_operation()
        
        # Log performance
        duration = time.time() - start_time
        sentry_sdk.logger.info(f'Operation completed in {duration:.2f}s')
        
        # Check performance thresholds
        performance_monitor.check_performance({
            'response_time_ms': duration * 1000,
            'operation': 'expensive_operation'
        })
        
    except Exception as e:
        # Log error
        sentry_sdk.logger.error(f'Operation failed: {str(e)}')
```

---

## 🛠️ **BEST PRACTICES**

### ✅ **Logging Best Practices**
1. **Use appropriate log levels**
   - `DEBUG`: Detailed information for debugging
   - `INFO`: General information about program execution
   - `WARNING`: Potential issues that don't stop execution
   - `ERROR`: Errors that don't stop execution
   - `CRITICAL`: Serious errors that might stop execution

2. **Include relevant context**
   ```python
   # Good: Include context
   sentry_sdk.logger.info(f'User {user_id} logged in from {ip_address}')
   
   # Bad: No context
   sentry_sdk.logger.info('User logged in')
   ```

3. **Use structured logging**
   ```python
   # Good: Structured data
   sentry_sdk.logger.info('Payment processed', extra={
       'user_id': user_id,
       'amount': amount,
       'currency': currency,
       'method': payment_method
   })
   ```

4. **Don't log sensitive information**
   ```python
   # Good: Don't log passwords
   sentry_sdk.logger.info(f'User {user_id} authentication attempt')
   
   # Bad: Logging sensitive data
   sentry_sdk.logger.info(f'User login: {email} password: {password}')
   ```

### ✅ **Error Handling**
```python
import sentry_sdk
import traceback

def safe_operation():
    try:
        # Perform operation
        result = risky_operation()
        sentry_sdk.logger.info('Operation completed successfully')
        return result
        
    except ValueError as e:
        # Log specific error type
        sentry_sdk.logger.error(f'Validation error: {str(e)}')
        return None
        
    except Exception as e:
        # Log unexpected errors
        sentry_sdk.logger.error(f'Unexpected error: {str(e)}')
        sentry_sdk.logger.error(f'Stack trace: {traceback.format_exc()}')
        return None
```

---

## 🔧 **INTEGRATION WITH EXISTING CODE**

### ✅ **Update Existing Logging**
```python
# Before: Basic logging
logger.info('User created')

# After: Enhanced logging with Sentry
sentry_sdk.logger.info('User created successfully', extra={
    'user_id': user.id,
    'email': user.email,
    'created_at': user.created_at.isoformat()
})
```

### ✅ **Add Logging to Core Services**
```python
# In core/minimal_crm_service.py
import sentry_sdk

class MinimalCRMService:
    def get_leads(self):
        try:
            sentry_sdk.logger.info('Fetching leads from CRM')
            leads = self._fetch_leads_from_db()
            sentry_sdk.logger.info(f'Retrieved {len(leads)} leads')
            return leads
        except Exception as e:
            sentry_sdk.logger.error(f'Failed to fetch leads: {str(e)}')
            raise
```

---

## 📈 **MONITORING DASHBOARD**

### ✅ **Sentry Dashboard Features**
- **Logs**: View all application logs in real-time
- **Errors**: Track and analyze error patterns
- **Performance**: Monitor application performance
- **Alerts**: Set up alerts based on log patterns
- **Releases**: Track logs across different releases

### ✅ **Log Analysis**
- **Search**: Search logs by message, level, or context
- **Filter**: Filter logs by time range, user, or service
- **Aggregate**: View log statistics and trends
- **Correlate**: Correlate logs with errors and performance issues

---

## 🎯 **SUMMARY**

### ✅ **Key Benefits**
1. **Centralized Logging**: All logs in one place
2. **Real-time Monitoring**: See logs as they happen
3. **Error Correlation**: Link logs to errors and performance issues
4. **Alerting**: Get notified of important events
5. **Debugging**: Easier debugging with structured logs

### ✅ **Implementation Status**
- ✅ Sentry SDK upgraded to 2.38.0
- ✅ `enable_logs=True` configured
- ✅ LoggingIntegration added
- ✅ Examples and best practices documented
- ✅ Integration with existing monitoring system

### 🚀 **Ready for Production**
The Sentry logging integration is fully configured and ready for production use. All logs will be automatically sent to Sentry for monitoring and analysis.

---

**Guide Generated:** December 2024  
**Sentry SDK Version:** 2.38.0  
**Status:** ✅ **PRODUCTION READY**
