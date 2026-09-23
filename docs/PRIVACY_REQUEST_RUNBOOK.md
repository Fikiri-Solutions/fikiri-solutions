# Privacy / Data Request Runbook (Internal)

**Audience:** Fikiri operators handling privacy requests  
**Status:** Operational procedure — not a customer-facing legal promise  
**Last updated:** 2026-09-23  
**Related:** [MARKETING_EMAIL_STATUS.md](./MARKETING_EMAIL_STATUS.md), Privacy Policy (`/privacy`)

## Request channels

| Channel | Use for |
|---------|---------|
| `info@fikirisolutions.com` | Access, correction, deletion, marketing opt-out (public Privacy Policy) |
| In-app **Privacy & Data Management** | Authenticated export / delete (`POST /privacy/delete`) |
| In-app **Account** | Account deactivation (`POST /user/delete-account`) |

## Identity verification

1. Prefer authenticated in-app actions (already session/JWT scoped to the user).
2. For email-only requests: confirm control of the account email (reply from that address or one-time confirmation). Do not process deletion solely on an unverified third-party email claiming to be the user.
3. Log request date, requester email, request type, systems touched, and outcome (no passwords/tokens).

## Request types

### Access

- **In-app:** Privacy settings → Export Data (`privacy_manager.export_user_data` / related APIs).
- **Email:** Export account profile + CRM leads owned by that user where practical; deliver securely.

### Correction

- User can edit profile/settings in-app.
- Email: update the named fields in `users` / related profile metadata after verification.

### Marketing opt-out

- See [MARKETING_EMAIL_STATUS.md](./MARKETING_EMAIL_STATUS.md).
- Today: no active Fikiri marketing campaign sender. If `marketing_consent` is true in user metadata / `privacy_consents` (`consent_type=marketing_email`), set `granted=false` (record revoke) and set `marketing_consent=false` in metadata before any future ESP send.
- Do not treat contact/intake submissions as marketing opt-in.

### Account deletion / erasure

1. Prefer in-app delete with confirmation phrase where available.
2. Or operator runs authenticated delete path / support-assisted delete after verification.
3. Walk the systems checklist below.

## Systems checklist

| System | What may exist | Fikiri can delete directly? | Notes |
|--------|----------------|----------------------------|--------|
| App DB (`users`, profile metadata) | Account, consents metadata | Yes | `privacy_manager.delete_user_data` / account deactivate |
| CRM `leads` owned by user | Contacts the tenant stored | Yes (cascade with user delete) | Tenant CRM ≠ public contact form rows |
| Contact / intake submissions | Name, email, phone, message, intake fields | Yes (manual SQL/admin after verify) | May not be tied to a user account |
| Site chat transcripts | Free-text chat, intake slots | Yes (purge scripts / admin site-chat tools) | May contain typed PII |
| Stripe | Customer, subscriptions, invoices | Partial — via Stripe Dashboard / API | Retain invoices as required for accounting |
| Vercel Analytics / Speed Insights | Aggregated page metrics | Limited — provider tools | Typically no named user export |
| SMTP / transactional email logs | Welcome, verification, resets | Partial | Job rows / provider logs; not a marketing list |
| Mailchimp | Audience members | N/A in production | **Not enabled in prod** (owner confirmation 2026-09-23). Ignore unless `MAILCHIMP_API_KEY` is later set. |
| Application logs | IPs, request metadata | Retention / redaction policy | Do not promise instant log erasure |
| Backups | Snapshots of DB | Expiry of backup cycle | Document retention window with infra owner |

## Legitimate retention (do not over-delete)

- Stripe payment/invoice records needed for tax/accounting.
- Security / fraud logs for a limited window.
- Records subject to legal hold (rare — escalate).

## Distinctions

- **Directly deletable:** Fikiri app DB account + owned CRM data; contact/intake rows; site-chat transcripts (with ops access).
- **Third-party:** Stripe, Vercel analytics, optional Mailchimp, email provider logs.
- **Not marketing:** Password reset, verification, billing receipts, security alerts — do not attach marketing unsubscribe UX to these.

## Owner follow-ups (not blocking this runbook)

- Confirm backup retention window with hosting provider.
- ~~Confirm whether production Mailchimp is ever enabled.~~ **Confirmed 2026-09-23: Mailchimp is not enabled in production.**
- Counsel review of Privacy Policy marketing unsubscribe wording vs current send posture.
