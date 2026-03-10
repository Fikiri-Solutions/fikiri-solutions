# Twilio webhooks – number configuration

Use these Fikiri endpoints when configuring your Twilio phone number **(855) 389-4992** (or any number in **My New Notifications Service**).

Replace `https://your-api-domain.com` with your real API base URL:

- **Running locally** (`python3 app.py`): Twilio can’t reach `localhost`. Use [ngrok](https://ngrok.com) — run `ngrok http 5000` and use the HTTPS URL (e.g. `https://abc123.ngrok.io`).
- **Deployed (production):** Use your public backend URL, e.g. `https://api.fikirisolutions.com` or `https://fikiri-xxx.onrender.com` — use the host only, no path (no `/api`).

---

## Messaging configuration

**A message comes in**

- **Configure with:** Webhook  
- **URL:** `https://your-api-domain.com/api/webhooks/twilio/sms`  
- **HTTP:** `POST`  

Twilio will send inbound SMS to this URL (form-urlencoded: `From`, `To`, `Body`, `MessageSid`, etc.). Fikiri logs the message and returns `200`. Requests are validated with `X-Twilio-Signature` when `TWILIO_AUTH_TOKEN` is set.

**Primary handler fails** (optional)

- **URL:** Leave empty or point to a fallback (e.g. TwiML Bin that replies “Service unavailable”).

---

## Voice configuration

**A call comes in**

- **Configure with:** Webhook  
- **URL:** `https://your-api-domain.com/api/webhooks/twilio/voice`  
- **HTTP:** `POST`  

Fikiri returns TwiML that says: “Thanks for calling Fikiri. Please contact us by email or the website.” and then hangs up. Signature validation applies when `TWILIO_AUTH_TOKEN` is set.

**Primary handler fails** / **Call status changes** (optional)

- Leave empty unless you have a specific fallback or status-callback URL.

---

## Summary

| Twilio setting        | Fikiri URL                                      | Method |
|-----------------------|--------------------------------------------------|--------|
| A message comes in    | `/api/webhooks/twilio/sms`                       | POST   |
| A call comes in       | `/api/webhooks/twilio/voice`                     | POST   |

After setting the URLs, click **Save configuration** and **Return to Active Numbers**.

**Note:** Toll-free verification (“Toll-Free Number Has Not Been Verified”) is separate from webhook configuration. Complete that in the Twilio console when you’re ready to send from a toll-free number. Your **(855)** number and **My New Notifications Service** can use these webhooks as soon as the app is reachable at the URL you set.
