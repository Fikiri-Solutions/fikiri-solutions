# Dev: SMTP for email verification (Gmail App Password)

Transactional email (signup verification, resend, welcome, password reset) is sent by the **Flask backend** via **`email_automation/jobs.py`** using **SMTP** and these environment variables:

| Variable | Example | Notes |
|----------|---------|--------|
| `SMTP_HOST` | `smtp.gmail.com` | Default `smtp.gmail.com` if unset; **`SMTP_SERVER` is an alias** |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USERNAME` | `you@gmail.com` | **Full Gmail address** |
| `SMTP_PASSWORD` | 16-character app password | **Not** your normal Google password |
| `FROM_EMAIL` | `you@gmail.com` | For dev, match the Gmail you authenticate as |
| `FROM_NAME` | `Fikiri Solutions` | Display name |

After changing `.env`, **restart** `python app.py` (no hot reload for this).

## Gmail: create an App Password

1. Open Google Account → **Security**.
2. Enable **2-Step Verification** (required for app passwords).
3. Search **App passwords** (or: Security → How you sign in to Google → App passwords).
4. Create an app password for **Mail** / **Other** (e.g. name it `Fikiri local`).
5. Copy the **16-character** password into `SMTP_PASSWORD` in `.env`. Google may show it **with spaces** (four groups)—paste as-is; the backend **strips spaces** from `SMTP_PASSWORD` before login.

**If an app password was ever pasted in chat, a ticket, or git:** revoke it in **App passwords** and create a new one—treat it like a leaked password.

## `.env` snippet (local dev)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=abcdabcdabcdabcd
FROM_EMAIL=you@gmail.com
FROM_NAME=Fikiri Solutions
```

Use the **same** address for `SMTP_USERNAME` and `FROM_EMAIL` while testing with a personal Gmail account.

## Verify it works

1. Restart the backend (required after code or `.env` changes).
2. In the app, use **Resend verification email** (or sign up a test user).
3. Logs should show **`✅ Sent email: verify_...`** not `535` or `SMTP credentials not configured`.

If you still see **`535 BadCredentials`**: wrong app password, typo, or `SMTP_USERNAME` is not the full email.

### Queued but no `✅ Sent email` in logs

Jobs store `scheduled_at` in ISO-8601 form. The worker only picks rows where that time is due; SQLite compares times correctly when the query uses `datetime(scheduled_at)` (fixed in code). If you run an old server build without that fix, **restart** after pulling the latest `email_automation/jobs.py`.

## Frontend URL in the email

The verification link uses **`FRONTEND_URL`** (via `config.get_frontend_url()`). For local testing set e.g. `FRONTEND_URL=http://localhost:5174` (or your Vite port) so the link opens your dev app.

## Production

For production, prefer a **transactional provider** (SendGrid, Postmark, SES, Resend, etc.) with a **verified domain** and SPF/DKIM, then point `SMTP_*` at their SMTP relay or add an API-based sender later.
