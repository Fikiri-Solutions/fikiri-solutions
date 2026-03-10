# How to Get Gmail & Outlook Tokens Into the DB

The readiness gate marks **mailbox_automation** and **workflows** as BETA until Gmail and/or Outlook are "connected." That means the app needs **OAuth tokens in the database** (from you connecting your account in the app).

---

## What You Need To Do

**Connect Gmail and/or Outlook inside the Fikiri app.** The app will open Google/Microsoft login, you approve, and it stores the tokens in the DB. No manual DB or script step required.

---

## Step-by-Step

### 1. Run the app

- **Backend:** `python3 app.py` (or your usual run)
- **Frontend:** `npm run dev` (e.g. Vite on port 5174)

### 2. Log in

- Open the app in the browser (e.g. `http://localhost:5174`).
- Sign in with your Fikiri user (the one you want to attach Gmail/Outlook to).

### 3. Connect Gmail

- Go to **Integrations** (or **Settings** → Integrations), or the **Onboarding** step that says "Connect your email."
- Click **Connect Gmail** (or similar).
- You’ll be sent to Google; sign in and approve the requested permissions.
- You’re redirected back; the app stores the tokens in the `gmail_tokens` table.

### 4. Connect Outlook (optional)

- In the same Integrations / Onboarding area, click **Connect Outlook**.
- Sign in with Microsoft and approve.
- The app stores the tokens in the `outlook_tokens` table.

### 5. Re-run the readiness gate

```bash
python3 scripts/automation_readiness.py --summary
```

The gate now treats **both** `oauth_tokens` and the app tables (`gmail_tokens`, `outlook_tokens`) as valid. So after connecting in the app, you should see `gmail: connected` and/or `outlook: connected`, and mailbox_automation/workflows can move from BETA toward SELLABLE.

---

## If You Don’t See “Connect Gmail” / “Connect Outlook”

- Check the **Onboarding** flow (e.g. step 2 often is “Connect email”).
- Or look under **Integrations** / **Settings** for “Gmail” / “Outlook” or “Email” and use the connect button there.
- The backend routes are:
  - Gmail: `GET /api/oauth/gmail/start` (returns a URL; frontend opens it), then `GET /api/oauth/gmail/callback` (Google redirects here).
  - Outlook: `GET /api/oauth/outlook/start` and `GET /api/oauth/outlook/callback`.

---

## Summary

| Goal                         | Action                                      |
|-----------------------------|---------------------------------------------|
| Get Gmail tokens in the DB  | Log in to Fikiri → Connect Gmail in the app |
| Get Outlook tokens in the DB| Log in to Fikiri → Connect Outlook in the app |
| Make the gate see them     | Re-run `automation_readiness.py --summary`  |

No scripts or manual DB edits are required; the app’s Connect flow does everything.
