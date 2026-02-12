# Google APIs Required for Fikiri

## Summary

You need **1 Google API** enabled (Gmail API is required).

Optional APIs:
- **Google Sheets API** (only if using "Email → Sheets" automation)
- **Google Calendar API** (NOT currently used - calendar events stored locally only)

## Required APIs

### 1. Gmail API ✅ **REQUIRED**

**What it does:**
- Read emails from Gmail inbox
- Send emails on behalf of users
- Manage email labels and archiving
- Sync email data to CRM

**OAuth Scopes Needed:**
```
https://www.googleapis.com/auth/gmail.readonly    # Read emails
https://www.googleapis.com/auth/gmail.send        # Send emails
https://www.googleapis.com/auth/gmail.modify      # Manage emails (labels, archive)
```

**Enable in Google Cloud Console:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **APIs & Services** → **Library**
3. Search "Gmail API"
4. Click **Enable**

---

### 2. Google Sheets API ⚠️ **OPTIONAL**

**What it does:**
- Write lead data to Google Sheets
- Used by "Email → Sheets" automation preset

**OAuth Scope Needed:**
```
https://www.googleapis.com/auth/spreadsheets
```

**Enable in Google Cloud Console:**
1. **APIs & Services** → **Library**
2. Search "Google Sheets API"
3. Click **Enable**

**Note:** Only needed if users want to sync data to Google Sheets. If using webhooks instead, this is not required.

---

### 3. Google Calendar API ❌ **NOT NEEDED** (Currently)

**Status:** Calendar events are stored in local database only, not synced to Google Calendar.

**Current Implementation:**
- "Calendar follow-ups" automation stores events in `calendar_events` table
- Events are NOT created in Google Calendar
- This is a local reminder system

**If you want real Google Calendar integration:**
- Would need to enable **Google Calendar API**
- Would need scope: `https://www.googleapis.com/auth/calendar`
- Would need to implement actual Calendar API calls

**For now:** Local storage is sufficient for reminder functionality.

---

## OAuth Setup

### Required OAuth Scopes (in OAuth Consent Screen):

```
# Gmail (Required)
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify

# User Info (Required for authentication)
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile

# Google Sheets (Optional)
https://www.googleapis.com/auth/spreadsheets
```

### Environment Variables Needed:

```bash
# Required
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/auth/google/callback

# Optional (for token encryption)
FERNET_KEY=your-encryption-key
```

---

## Quick Setup Checklist

- [ ] Create Google Cloud Project
- [ ] Enable **Gmail API**
- [ ] Enable **Google Sheets API** (optional)
- [ ] Configure OAuth Consent Screen
- [ ] Add required scopes
- [ ] Create OAuth 2.0 Client ID
- [ ] Set redirect URIs
- [ ] Add environment variables to `.env`
- [ ] Test Gmail connection

---

## What Works Without Google APIs?

**Without Gmail API:**
- ❌ Email sync won't work
- ❌ Email automation won't work
- ✅ CRM still works (manual entry)
- ✅ Dashboard still works
- ✅ Other features work

**Without Google Sheets API:**
- ✅ Everything works
- ❌ "Email → Sheets" automation won't work
- ✅ Webhooks still work (can use Zapier/Make instead)

---

## Cost

- **Gmail API**: Free (within quota limits)
- **Google Sheets API**: Free (within quota limits)
- **Quota**: 1 billion quota units per day (very generous)

---

## Documentation

See `docs/GOOGLE_OAUTH_SETUP.md` for detailed setup instructions.

