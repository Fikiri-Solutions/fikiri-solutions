# Site marketing analytics (intake + chatbot)

Minimal first-party funnel telemetry for the public marketing site.

## Why first-party

**Vercel Web Analytics is disabled** — on Pro, page views/custom events are usage-billed and can increase the bill.

**Vercel Speed Insights (free tier) stays enabled** — 10k events / team / 30 days; collection pauses at the limit with **no overage charges**. Do not enable Speed Insights Plus.

Funnel telemetry is first-party only (`POST /api/site/events`). GA4 is **not** wired.

## Events

| Event | Properties (bounded) |
|-------|----------------------|
| `intake_started` | `source_kind` |
| `intake_step_viewed` | `step_id` |
| `intake_submitted` | `source_kind`, `preferred_next_step`, `priority_band` |
| `booking_clicked` | `surface` |
| `chatbot_opened` | `path_bucket` |
| `chatbot_first_message` | — |
| `chatbot_fallback` | `mode` |
| `chatbot_handoff` | `handoff_type` |

Never send names, emails, phones, free-text answers, or chat transcripts.

Abandonment is **inferred** from `intake_started` vs `intake_submitted` over a lookback window.

CRM / `customer_contact_submissions` (`form_type=consultation_intake`) remain authoritative for who converted.

## API

- `POST /api/site/events` — public, rate-limited, anonymous `session_ref`
- `GET /api/admin/platform/marketing-funnel?lookback_days=7` — requires `platform.ops.read`

## Flags

```bash
SITE_MARKETING_EVENTS_ENABLED=true   # default on
SITE_MARKETING_EVENTS_RETENTION_DAYS=90
```

## Schema

Apply `scripts/migrations/011_site_marketing_events.sql` on Postgres. Local/SQLite creates the table via `ensure_site_marketing_event_tables()`.

## Admin UI

`/admin/marketing` — starts, completions, step drop-off, chatbot open/active/fallback/handoff, CRM source + priority bands.

Page-view / referrer dashboards from Vercel Web Analytics are not used. Speed Insights (free tier) remains for performance only.
