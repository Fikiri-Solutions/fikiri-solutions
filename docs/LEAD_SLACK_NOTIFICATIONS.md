# Lead Slack notifications

Hot-route Slack alerts for potential customers. Operational health alerts stay on `SLACK_WEBHOOK_URL` via `core/monitoring.py` and are unchanged.

## Channels

| Env var | Purpose |
|---------|---------|
| `LEAD_SLACK_WEBHOOK_URL` | **Preferred.** Incoming webhook created for `#leads` (or equivalent). |
| `SLACK_WEBHOOK_URL` | Ops / monitoring. Used as **fallback** for leads if the dedicated URL is unset. |
| `FIKIRI_LEAD_SLACK_DEDUPE_SECONDS` | In-process retry suppression window (default `900`). |

Do **not** put webhook URLs in frontend code or git. Set them only in Render (or local `.env`).

Incoming webhooks are bound to a channel. Create a dedicated Slack incoming webhook for `#leads` and set `LEAD_SLACK_WEBHOOK_URL` to that URL. Do not rely on payload `channel` overrides when the dedicated webhook is configured.

Optional legacy (only when falling back to the ops webhook): `LEAD_SLACK_CHANNEL` / `SLACK_CHANNEL`.

## Sources that notify

1. Public contact form (`core/contact_api.py`)
2. Consultation intake (`core/consultation_intake_service.py`)
3. Explicit site-chat human handoffs (`company_chatbot/handoff_notify.py`) — guard handoff, contact mode, or completed intake with email. Ordinary answers do **not** notify.
4. External form webhooks after successful lead persistence (`core/webhook_intake_service.py`) — Tally / Typeform / Jotform / generic

## Delivery semantics

- CRM / DB persistence, email, and Slack are independent.
- Slack posts run on a daemon thread by default so visitor requests are not blocked by Slack latency.
- `send_lead_slack_notification(...) -> True` means the alert was **accepted** (webhook configured + not deduped), not that HTTP delivery is confirmed when non-blocking.
- Delivery confirmation: Render logs contain `Lead Slack notification sent: ...` or `Lead Slack notification failed: ...`.
- Retries with the same `dedupe_key` are suppressed for the TTL window. Monitoring cooldown is never applied to leads.

## Render setup

1. Slack → Incoming Webhooks → add to `#leads` → copy URL.
2. Render → `fikirisolutions` (and staging if desired) → Environment → add:
   - `LEAD_SLACK_WEBHOOK_URL` = that URL
3. Keep existing `SLACK_WEBHOOK_URL` for ops alerts.
4. Redeploy or restart so workers pick up the env var.

## Production smoke test (safe)

Use a clearly marked test identity (e.g. `slack-smoke+YYYYMMDD@example.test`).

1. **Contact:** submit `/contact` with the test email. Expect a `#leads` message titled `New contact form: ...`. Confirm Render log `Lead Slack notification sent`.
2. **Intake:** submit `/intake` once. Expect `Consultation intake: ...`. Retry the same browser submit quickly — Slack should not duplicate (dedupe / persistence).
3. **Site chat:** start a session, send `I want to talk to someone`. Expect `Site chat handoff: contact`. Send a normal product question — no Slack.
4. **Ops control:** confirm a health alert (if any) still lands on the ops webhook/channel, not mixed into leads once `LEAD_SLACK_WEBHOOK_URL` is set.

Do not claim production delivery until these checks show Slack messages and matching logs.
