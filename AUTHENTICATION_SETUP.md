# Fikiri Solutions - Gmail Authentication Setup Guide

## ✅ Working Configuration

This document records the successful authentication setup for Fikiri Solutions Gmail Lead Responder.

### Google Cloud Console Setup

1. **Project**: "Project Fik" (logical-carver-471821-g3)
2. **OAuth Client Type**: Desktop Application (NOT Web Application)
3. **Client ID**: 372352843601-m2gsmmcm1nf6msi5c7odq1i0bqm1kc44.apps.googleusercontent.com
4. **Redirect URI**: `urn:ietf:wg:oauth:2.0:oob`

### Credentials File Structure

The `auth/credentials.json` file must have this exact structure:

```json
{
  "installed": {
    "client_id": "372352843601-m2gsmmcm1nf6msi5c7odq1i0bqm1kc44.apps.googleusercontent.com",
    "project_id": "logical-carver-471821-g3",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "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",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
  }
}
```

### Code Configuration

The authentication code must explicitly set the redirect URI:

```python
flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
```

### Authentication Flow

1. User runs `python3 main.py auth`
2. Browser opens with Google OAuth consent screen
3. User signs in with info@fikirisolutions.com
4. User grants permissions to Fikiri Solutions
5. Browser redirects to `urn:ietf:wg:oauth:2.0:oob` with authorization code
6. User copies code from browser and pastes in terminal
7. Authentication completes successfully

### Key Points

- **Desktop Application OAuth client** is required (not Web Application)
- **Redirect URI must be `urn:ietf:wg:oauth:2.0:oob`** for desktop apps
- **Explicitly set redirect URI in code** even if it's in credentials file
- **Manual code entry** is expected for desktop applications
- **Token is saved** in `auth/token.pkl` for future use

### Troubleshooting

If authentication fails with "Missing required parameter: redirect_uri":
1. Verify OAuth client is Desktop Application type
2. Check redirect URI is `urn:ietf:wg:oauth:2.0:oob`
3. Ensure code explicitly sets `flow.redirect_uri`
4. Verify credentials.json has correct redirect_uris array

### Success Indicators

- ✅ Authentication successful message
- ✅ Token saved to auth/token.pkl
- ✅ Can fetch emails with `python3 main.py fetch`
- ✅ Status shows authenticated (though CLI status detection may be buggy)

---
*Last updated: September 12, 2025*





