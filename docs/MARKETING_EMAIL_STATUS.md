# Marketing Email Status (Internal)

**Last updated:** 2026-09-23  
**Related:** [PRIVACY_REQUEST_RUNBOOK.md](./PRIVACY_REQUEST_RUNBOOK.md)

## Current posture

Fikiri does **not** currently operate an active first-party marketing email campaign sender in production code paths reviewed for Pass 2B.

| Flow | Type | Unsubscribe required? | Status |
|------|------|----------------------|--------|
| Welcome | Transactional | No | Active (`email_automation/jobs.py`) |
| Email verification | Transactional | No | Active when queued |
| Password reset | Transactional | No | Active |
| Onboarding progress | Transactional / product | No | Active when queued |
| Stripe-related notices | Transactional / billing | No | Via Stripe / app |
| Newsletter / promotions | Marketing | Yes, if sending | **Not actively sent** |

## Consent capture (signup)

- UI: newsletter checkbox **unchecked by default** (`Signup.tsx`).
- Server: `marketing_consent` persisted to user metadata (`marketing_consent`, `marketing_consent_at`, `marketing_consent_source=signup`) and `privacy_consents` row with `consent_type=marketing_email` (`routes/auth.py`).
- SMS consent remains separate (`sms_alerts` / account SMS metadata).

## Suppression / opt-out (when marketing is enabled later)

1. Record revoke in `privacy_consents` for `marketing_email` (`granted=false` / `revoked_at`).
2. Set user metadata `marketing_consent=false`.
3. If an ESP (e.g. Mailchimp) is configured, unsubscribe there and do not re-import opted-out addresses.
4. Do **not** auto-resubscribe from contact/intake forms.

## What not to build yet

- Do not add List-Unsubscribe headers to transactional mail solely for checklist optics.
- Do not stand up Mailchimp/ESP infrastructure until there is a real marketing send use case. **Mailchimp is not enabled in production** (owner confirmation 2026-09-23).
- Privacy Policy language about “unsubscribe link in emails” should be reviewed by counsel against this posture (legal change — out of scope for Pass 2B code).
