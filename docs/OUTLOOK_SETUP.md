# Outlook Integration Setup Guide

## Quick Setup (5 minutes)

### Step 1: Register App in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill in:
   - **Name**: `Fikiri Solutions`
   - **Supported account types**: `Accounts in any organizational directory and personal Microsoft accounts`
   - **Redirect URI**: 
     - Type: `Web`
     - URI: `http://localhost:5000/api/oauth/outlook/callback` (for local dev)
     - Add production URI: `https://yourdomain.com/api/oauth/outlook/callback`

5. Click **Register**

### Step 2: Get Credentials

After registration, you'll see:
- **Application (client) ID** → This is your `MICROSOFT_CLIENT_ID`
- **Directory (tenant) ID** → This is your `MICROSOFT_TENANT_ID`

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** (left sidebar)
2. Click **New client secret**
3. Add description: `Fikiri Production Secret`
4. Set expiration (recommend 24 months)
5. Click **Add**
6. **Copy the secret value immediately** → This is your `MICROSOFT_CLIENT_SECRET`
   - ⚠️ You can only see it once!

### Step 4: Configure API Permissions

1. Go to **API permissions** (left sidebar)
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add these permissions:
   - `Mail.ReadWrite` - Read and write mail
   - `User.Read` - Read user profile
   - `Calendars.ReadWrite` - Read and write calendars
   - `offline_access` - Maintain access to data (for refresh tokens)

6. Click **Add permissions**
7. Click **Grant admin consent** (if you're an admin)

### Step 5: Add Environment Variables

Add to your `.env` file:

```bash
# Microsoft/Outlook OAuth
MICROSOFT_CLIENT_ID=your_client_id_here
MICROSOFT_CLIENT_SECRET=your_client_secret_here
MICROSOFT_TENANT_ID=common  # Use 'common' for multi-tenant, or your tenant ID
OUTLOOK_REDIRECT_URI=http://localhost:5000/api/oauth/outlook/callback
```

### Step 6: Test Connection

1. Start your backend: `python app.py`
2. Visit: `http://localhost:5000/api/oauth/outlook/start?redirect=/dashboard`
3. You should be redirected to Microsoft login
4. After login, you'll be redirected back with tokens stored

## Production Setup

For production, update:
- `OUTLOOK_REDIRECT_URI` to your production domain
- Add production redirect URI in Azure Portal
- Use your actual tenant ID (not 'common') for better security

## Troubleshooting

**Error: "redirect_uri_mismatch"**
- Make sure redirect URI in Azure Portal matches exactly (including http/https, trailing slashes)

**Error: "invalid_client"**
- Check that `MICROSOFT_CLIENT_ID` and `MICROSOFT_CLIENT_SECRET` are correct
- Make sure client secret hasn't expired

**Error: "insufficient_privileges"**
- Make sure you granted admin consent for API permissions
- Check that all required permissions are added

## What's Already Built

✅ OAuth routes (`/api/oauth/outlook/start`, `/api/oauth/outlook/callback`)
✅ Token storage with encryption
✅ Status endpoint (`/api/auth/outlook/status`)
✅ Database schema (`outlook_tokens` table)

## Next Steps

After Azure setup:
1. Test OAuth flow
2. Build email sync functionality
3. Add frontend UI for Outlook connection

