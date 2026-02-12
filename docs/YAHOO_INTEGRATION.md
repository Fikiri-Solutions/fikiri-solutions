# Yahoo Mail Integration Guide

## Overview

Yahoo Mail integration requires OAuth2 authentication via IMAP/SMTP. Access to Yahoo's Mail services requires approval from Yahoo.

## Access Requirements

### Approval Process

1. **Request Access**: Fill out Yahoo's access request form
   - Contact: mail-api@yahooinc.com
   - Form: [Yahoo Developer Access Request](https://developer.yahoo.com/mail)

2. **Provide Information**:
   - Application/service description
   - How you'll use Yahoo Mail data
   - Security and privacy measures
   - Compliance with Yahoo's policies

3. **Wait for Approval**: Yahoo reviews requests and grants access to approved developers

### Policy Compliance

Our implementation complies with Yahoo's requirements:

- ✅ **OAuth2 Only**: Uses OAuth2, not password authentication
- ✅ **Direct User Service**: Provides services directly to Yahoo customers
- ✅ **Data Usage**: Only uses data for user-facing email functionality
- ✅ **Privacy**: Clear privacy policy and user consent
- ✅ **Security**: Encrypted token storage and secure handling

## Configuration

### Environment Variables

```bash
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
YAHOO_REDIRECT_URI=https://yourdomain.com/api/oauth/yahoo/callback
```

### OAuth2 Scopes

Required scopes (require Yahoo approval):
- `mail-r`: Read mail via IMAP
- `mail-w`: Write mail via SMTP
- `mail-d`: Delete mail

## Implementation

### IMAP/SMTP Servers

- **IMAP**: `imap.mail.yahoo.com:993` (SSL)
- **SMTP**: `smtp.mail.yahoo.com:587` (TLS)

### Authentication

Uses OAuth2 XOAUTH2 mechanism for IMAP/SMTP authentication.

## Support

- **Yahoo Developer Support**: mail-api@yahooinc.com
- **Documentation**: https://developer.yahoo.com/mail

