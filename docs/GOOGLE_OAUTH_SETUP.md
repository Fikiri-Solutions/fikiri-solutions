# 🔐 Google OAuth Setup Guide for Fikiri

## Overview

This guide walks you through configuring Google OAuth scopes for your Fikiri application, enabling seamless Gmail integration and user authentication.

## 🎯 Required OAuth Scopes

Based on your application's needs, configure these scopes in Google Cloud Console:

### **Gmail API Scopes**
```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send  
https://www.googleapis.com/auth/gmail.modify
```

### **User Info Scopes**
```
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
```

## 📋 Step-by-Step Configuration

### 1. Access Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** → **Credentials**

### 2. Configure OAuth Consent Screen

1. Go to **OAuth consent screen**
2. Configure the following:
   - **User Type**: External (unless you have Google Workspace)
   - **App name**: Fikiri Solutions
   - **User support email**: Your business email
   - **App logo**: Upload your logo (optional)
   - **App domain**: fikirisolutions.com
   - **Authorized domains**: fikirisolutions.com
   - **Developer contact**: Your business email

### 3. Add OAuth Scopes

1. In **OAuth consent screen** → **Scopes**
2. Click **Add or Remove Scopes**
3. Search and add each scope with these descriptions:

#### Gmail Readonly Scope
- **Scope**: `https://www.googleapis.com/auth/gmail.readonly`
- **Description**: "View and read your Gmail messages"
- **Category**: Sensitive

#### Gmail Send Scope  
- **Scope**: `https://www.googleapis.com/auth/gmail.send`
- **Description**: "Send emails on your behalf"
- **Category**: Sensitive

#### Gmail Modify Scope
- **Scope**: `https://www.googleapis.com/auth/gmail.modify`
- **Description**: "Manage your Gmail messages"
- **Category**: Sensitive

#### User Info Email Scope
- **Scope**: `https://www.googleapis.com/auth/userinfo.email`
- **Description**: "Access your email address"
- **Category**: Not sensitive

#### User Info Profile Scope
- **Scope**: `https://www.googleapis.com/auth/userinfo.profile`
- **Description**: "Access your basic profile information"  
- **Category**: Not sensitive

### 4. Configure OAuth Client

1. Go to **Credentials** → **OAuth 2.0 Client IDs**
2. Create new OAuth client (if not exists):
   - **Application type**: Web application
   - **Name**: Fikiri Web Client
   - **Authorized redirect URIs**:
     ```
     http://localhost:5000/api/auth/google/callback
     http://localhost:5000/api/auth/gmail/callback
     https://fikirisolutions.com/api/auth/google/callback
     https://fikirisolutions.com/api/auth/gmail/callback
     ```

### 5. Environment Configuration

Update your `.env` file with credentials:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-from-step-4
GOOGLE_CLIENT_SECRET=your-client-secret-from-step-4
GOOGLE_REDIRECT_URI=https://fikirisolutions.com/api/auth/google/callback

# Legacy naming for compatibility
GMAIL_CLIENT_ID=your-client-id-from-step-4
GMAIL_CLIENT_SECRET=your-client-secret-from-step-4
GMAIL_REDIRECT_URI=https://fikirisolutions.com/api/auth/gmail/callback
```

## 🔄 Application Flow

Your application implements a sophisticated OAuth flow:

1. **User initiates connection** → `/api/auth/google/authorize`
2. **Google authorization** → User sees consent screen with requested scopes
3. **OAuth callback** → `/api/auth/google/callback` 
4. **Token storage** → Secure storage in database with encryption
5. **Gmail integration** → Automatic token refresh, email reading/sending

## 🔧 Technical Details

### Database Tables Created

Your OAuth implementation creates these tables:
- `oauth_states` - CSRF protection with state parameters
- `google_oauth_tokens` - Secure token storage
- User metadata updated with Google connection status

### Security Features

- **State parameter** for CSRF protection
- **Token encryption** with Fernet encryption
- **Automatic refresh** before token expiry
- **Secure revocation** when user disconnects
- **Session management** with IP tracking

## 🧪 Testing Your Setup

### 1. Test Authorization Flow

```bash
curl -X GET "http://localhost:5000/api/auth/google/authorize?user_id=1"
```

### 2. Verify Environment Variables

Check that all Google OAuth variables are set:
```bash
grep -E "GOOGLE_|GMAIL_" .env
```

### 3. Test Gmail Connection

In your application, navigate to the Gmail connection page and verify:
- Authorization URL loads correctly
- Callback processes tokens successfully  
- Gmail API calls work

## 🚀 Production Deployment

### Render Deployment

Update `render.yaml` with environment variables:
```yaml
envVars:
  - key: GOOGLE_CLIENT_ID
    value: your-production-client-id
  - key: GOOGLE_CLIENT_SECRET  
    value: your-production-client-secret
  - key: GOOGLE_REDIRECT_URI
    value: https://your-app.onrender.com/api/auth/google/callback
```

### Domain Verification

1. Add your production domain to **Authorized domains**
2. Update redirect URIs with HTTPS URLs
3. Test OAuth flow in production

## 📊 Monitoring & Troubleshooting

### Common Issues

**Issue**: "redirect_uri_mismatch"
- **Solution**: Ensure redirect URI exactly matches configured URI

**Issue**: "access_denied" 
- **Solution**: Verify scopes are properly configured and app is public

**Issue**: Token refresh fails
- **Solution**: Check client credentials and expired refresh token

### Monitoring Scopes Usage

- **Google Cloud Console** → **APIs & Services** → **Quotas**
- **Application logs** in your Fikiri dashboard
- **Gmail API**: Monitor API usage and rate limits

## 📝 Compliance Notes

### Privacy Considerations

- Inform users about email data access
- Provide clear terms of service
- Implement data retention policies
- Enable audit logs for sensitive operations

### Security Best Practices

- Regularly rotate client secrets
- Monitor for suspicious OAuth activity  
- Implement rate limiting on auth endpoints
- Use HTTPS in production always

## 🎉 Success!

Once configured, your Fikiri application will have:

✅ **Seamless Gmail Integration** - Read, send, and manage emails
✅ **User Authentication** - Google OAuth login flow  
✅ **Automatic Token Management** - Refresh tokens without user intervention
✅ **Secure Storage** - Encrypted credential storage
✅ **Production Ready** - Handles errors and edge cases

Your Google OAuth setup is complete! 🚀
