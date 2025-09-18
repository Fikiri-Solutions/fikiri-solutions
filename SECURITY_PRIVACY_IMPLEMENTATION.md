# 🔒 Security & Privacy Implementation Guide

## Content Security Policy (CSP)

### Implementation
Add CSP headers to all responses to prevent XSS attacks:

```python
# In app.py or middleware
@app.after_request
def add_security_headers(response):
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.openai.com https://gmail.googleapis.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # Additional security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
```

### Progressive Tightening
Start with permissive CSP and tighten over time:

```python
# Phase 1: Permissive (current)
CSP_PERMISSIVE = "script-src 'self' 'unsafe-inline'"

# Phase 2: Moderate (next release)
CSP_MODERATE = "script-src 'self' 'nonce-{nonce}'"

# Phase 3: Strict (future)
CSP_STRICT = "script-src 'self' 'nonce-{nonce}' https://trusted-cdn.com"
```

## Gmail Disconnect Flow

### Implementation
```python
@app.route('/api/oauth/disconnect', methods=['POST'])
@handle_api_errors
def api_disconnect_gmail():
    """Disconnect Gmail and offer data deletion."""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return create_error_response("User ID required", 400, "MISSING_USER_ID")
    
    # Revoke OAuth tokens
    result = oauth_token_manager.revoke_tokens(int(user_id), 'gmail')
    
    if result['success']:
        # Pause all automations
        automation_safety_manager.toggle_global_kill_switch(True)
        
        # Offer data deletion
        return create_success_response({
            'disconnected': True,
            'automations_paused': True,
            'data_deletion_offered': True,
            'deletion_url': f'/api/user/delete-data?user_id={user_id}'
        }, "Gmail disconnected. Automations paused.")
    
    return create_error_response(result['error'], 400, result['error_code'])

@app.route('/api/user/delete-data', methods=['POST'])
@handle_api_errors
def api_delete_user_data():
    """Delete all user data after confirmation."""
    data = request.get_json()
    user_id = data.get('user_id')
    confirmation = data.get('confirmation')
    
    if confirmation != 'DELETE_ALL_DATA':
        return create_error_response("Confirmation required", 400, "CONFIRMATION_REQUIRED")
    
    # Delete user data
    result = user_data_manager.delete_all_user_data(int(user_id))
    
    if result['success']:
        return create_success_response({
            'deleted': True,
            'data_types': result['deleted_types']
        }, "All user data deleted successfully.")
    
    return create_error_response(result['error'], 400, result['error_code'])
```

## Permission Tooltips

### Frontend Implementation
```tsx
// PermissionExplanation component
interface PermissionExplanationProps {
    permission: string;
    children: React.ReactNode;
}

const PermissionExplanation: React.FC<PermissionExplanationProps> = ({ permission, children }) => {
    const explanations = {
        'read_emails': 'We scan your emails to identify leads and opportunities. We never read personal emails.',
        'send_emails': 'We help you respond to leads automatically. You control all templates and timing.',
        'manage_labels': 'We organize your emails with smart labels to help you stay organized.',
        'modify_emails': 'We add labels and organize emails. We never delete or modify your content.'
    };
    
    return (
        <div className="permission-item">
            {children}
            <Tooltip content={explanations[permission]}>
                <InfoIcon className="info-icon" />
            </Tooltip>
        </div>
    );
};

// Usage in OAuth flow
<PermissionExplanation permission="read_emails">
    <Checkbox>Read emails</Checkbox>
</PermissionExplanation>
```

### Backend Permission Validation
```python
class PermissionValidator:
    """Validates OAuth permissions and explains usage."""
    
    PERMISSION_EXPLANATIONS = {
        'https://www.googleapis.com/auth/gmail.readonly': {
            'purpose': 'Read emails to identify leads',
            'scope': 'Email content analysis only',
            'retention': 'Encrypted storage, deleted on disconnect'
        },
        'https://www.googleapis.com/auth/gmail.send': {
            'purpose': 'Send automated responses to leads',
            'scope': 'Pre-approved templates only',
            'retention': 'No email content stored'
        },
        'https://www.googleapis.com/auth/gmail.modify': {
            'purpose': 'Organize emails with smart labels',
            'scope': 'Label management only',
            'retention': 'Label data only, no email content'
        }
    }
    
    def validate_permissions(self, scopes: List[str]) -> Dict[str, Any]:
        """Validate and explain OAuth permissions."""
        validated_scopes = []
        explanations = []
        
        for scope in scopes:
            if scope in self.PERMISSION_EXPLANATIONS:
                validated_scopes.append(scope)
                explanations.append(self.PERMISSION_EXPLANATIONS[scope])
            else:
                return {
                    'valid': False,
                    'error': f'Unknown permission: {scope}',
                    'error_code': 'UNKNOWN_PERMISSION'
                }
        
        return {
            'valid': True,
            'scopes': validated_scopes,
            'explanations': explanations
        }
```

## Log Redaction

### Implementation
```python
import re
import logging
from typing import Dict, Any

class LogRedactor:
    """Redacts sensitive information from logs."""
    
    # Patterns to redact
    REDACTION_PATTERNS = {
        'email_body': r'(?i)(body|content|message):\s*["\']?([^"\']{50,})["\']?',
        'api_keys': r'(?i)(api[_-]?key|secret[_-]?key|token):\s*["\']?([^"\']+)["\']?',
        'passwords': r'(?i)(password|passwd|pwd):\s*["\']?([^"\']+)["\']?',
        'tokens': r'(?i)(access[_-]?token|refresh[_-]?token):\s*["\']?([^"\']+)["\']?',
        'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    }
    
    def redact_log_entry(self, log_entry: str) -> str:
        """Redact sensitive information from log entry."""
        redacted = log_entry
        
        # Redact email bodies (keep metadata)
        redacted = re.sub(
            self.REDACTION_PATTERNS['email_body'],
            r'\1: [REDACTED_BODY]',
            redacted
        )
        
        # Redact API keys and tokens
        for pattern_name, pattern in self.REDACTION_PATTERNS.items():
            if pattern_name in ['api_keys', 'tokens']:
                redacted = re.sub(pattern, r'\1: [REDACTED]', redacted)
        
        # Redact passwords
        redacted = re.sub(
            self.REDACTION_PATTERNS['passwords'],
            r'\1: [REDACTED]',
            redacted
        )
        
        # Redact email addresses (keep domain for debugging)
        redacted = re.sub(
            self.REDACTION_PATTERNS['emails'],
            lambda m: f"[REDACTED]@{m.group(0).split('@')[1]}",
            redacted
        )
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from dictionary."""
        redacted = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact_log_entry(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self.redact_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                redacted[key] = value
        
        return redacted

# Custom logging formatter
class RedactingFormatter(logging.Formatter):
    """Logging formatter that redacts sensitive information."""
    
    def __init__(self):
        super().__init__()
        self.redactor = LogRedactor()
    
    def format(self, record):
        # Get the original formatted message
        original_message = super().format(record)
        
        # Redact sensitive information
        redacted_message = self.redactor.redact_log_entry(original_message)
        
        return redacted_message

# Configure logging with redaction
def setup_secure_logging():
    """Setup logging with sensitive information redaction."""
    
    # Create redacting formatter
    formatter = RedactingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure file handler
    file_handler = logging.FileHandler('logs/fikiri_secure.log')
    file_handler.setFormatter(formatter)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
```

## Privacy Controls

### Data Export
```python
@app.route('/api/user/export-data', methods=['GET'])
@handle_api_errors
def api_export_user_data():
    """Export all user data in JSON format."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return create_error_response("User ID required", 400, "MISSING_USER_ID")
    
    # Export user data
    result = user_data_manager.export_user_data(int(user_id))
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': result['data'],
            'exported_at': datetime.now().isoformat(),
            'data_types': result['data_types']
        })
    
    return create_error_response(result['error'], 400, result['error_code'])
```

### Data Retention Policy
```python
class DataRetentionManager:
    """Manages data retention and automatic deletion."""
    
    RETENTION_POLICIES = {
        'email_metadata': 365,  # 1 year
        'automation_logs': 90,   # 3 months
        'user_analytics': 730,   # 2 years
        'oauth_tokens': 0,      # Deleted on disconnect
        'email_content': 0      # Never stored
    }
    
    def cleanup_expired_data(self):
        """Clean up data that has exceeded retention period."""
        for data_type, days in self.RETENTION_POLICIES.items():
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                self._delete_expired_data(data_type, cutoff_date)
    
    def _delete_expired_data(self, data_type: str, cutoff_date: datetime):
        """Delete expired data of specific type."""
        # Implementation depends on data storage
        pass
```

## Security Monitoring

### Suspicious Activity Detection
```python
class SecurityMonitor:
    """Monitors for suspicious activity and security threats."""
    
    def detect_suspicious_activity(self, user_id: int, activity: Dict[str, Any]) -> bool:
        """Detect suspicious user activity."""
        
        # Check for unusual API usage patterns
        if self._check_api_usage_patterns(user_id, activity):
            return True
        
        # Check for unusual automation behavior
        if self._check_automation_patterns(user_id, activity):
            return True
        
        # Check for potential data exfiltration
        if self._check_data_access_patterns(user_id, activity):
            return True
        
        return False
    
    def _check_api_usage_patterns(self, user_id: int, activity: Dict[str, Any]) -> bool:
        """Check for unusual API usage patterns."""
        # Implementation for API usage monitoring
        pass
    
    def _check_automation_patterns(self, user_id: int, activity: Dict[str, Any]) -> bool:
        """Check for unusual automation behavior."""
        # Implementation for automation monitoring
        pass
    
    def _check_data_access_patterns(self, user_id: int, activity: Dict[str, Any]) -> bool:
        """Check for potential data exfiltration."""
        # Implementation for data access monitoring
        pass
```

## Implementation Checklist

### Security Headers
- [ ] Content Security Policy (CSP)
- [ ] X-Content-Type-Options
- [ ] X-Frame-Options
- [ ] X-XSS-Protection
- [ ] Strict-Transport-Security
- [ ] Referrer-Policy

### OAuth Security
- [ ] Permission explanations and tooltips
- [ ] Disconnect flow with data deletion
- [ ] Token encryption at rest
- [ ] Secure token refresh logic
- [ ] OAuth failure handling

### Logging Security
- [ ] Email body redaction
- [ ] API key redaction
- [ ] Password redaction
- [ ] Token redaction
- [ ] Email address redaction
- [ ] Secure logging formatter

### Privacy Controls
- [ ] Data export functionality
- [ ] Data deletion on disconnect
- [ ] Data retention policies
- [ ] User consent management
- [ ] Privacy policy integration

### Monitoring
- [ ] Suspicious activity detection
- [ ] Security event logging
- [ ] Automated threat response
- [ ] Security metrics dashboard
- [ ] Incident response procedures

---

**Remember**: Security is not a one-time implementation but an ongoing process. Regular security audits, penetration testing, and security training are essential for maintaining a secure system.
