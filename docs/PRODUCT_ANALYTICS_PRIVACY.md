# Product Analytics Privacy

Privacy and governance for Fikiri product / customer-success analytics.

## Business purposes

- Understand whether clients receive value
- See which features are used
- Detect friction and stuck workflows
- Support operators with explainable, read-only insights
- Aggregate founder-level trends (future slice)

Not for: employee productivity scoring, disability inference, content surveillance, session replay, or third-party ad profiling.

## Legal / policy context

The public Privacy Policy already describes usage analytics and feature usage. Accessibility signals remain **disabled** until privacy notice and implementation review are complete.

## Approved events

See [PRODUCT_ANALYTICS_EVENTS.md](PRODUCT_ANALYTICS_EVENTS.md). Registry in `core/product_analytics_registry.py` is authoritative at runtime.

## Prohibited data

Passwords, MFA/recovery codes, JWTs, cookies, OAuth tokens, email/CRM content, free-text customer input, payment data, clipboard, keystrokes, screenshots, raw DOM, mouse paths, precise GPS, full IP in product analytics, raw user-agent when family is enough, health/disability/political/religious/racial/sexual inferences.

## Retention

| Category | Default | Env |
|----------|---------|-----|
| Raw product events | 90 days | `PRODUCT_ANALYTICS_RAW_RETENTION_DAYS` |
| Daily tenant aggregates | 395 days (~13 months) | `PRODUCT_ANALYTICS_AGGREGATE_RETENTION_DAYS` |
| Security / admin audit | Existing security policy | n/a |

Cleanup uses dialect-safe bounded deletes (select IDs, then delete). No indefinite raw retention by default.

## Tenant deletion

Associated `product_events` and `tenant_daily_metrics` rows for that `tenant_id` must be deleted or irreversibly anonymized per account-deletion policy. Helper provided; wire into existing deletion path when present.

## Operator access

Platform operators with `platform.tenants.read`, non-impersonating. Admin analytics responses use `Cache-Control: no-store`. No unrestricted export in this slice.

## Founder aggregates

Deferred. When added: minimum cohort sizes; no small-group sensitive breakdowns; no raw per-user drill-down from aggregate charts.

## Accessibility-data interpretation

- Interface patterns only (e.g. reduced motion, keyboard-first)
- Never label a user as disabled or infer medical status
- Prefer tenant-level aggregates
- **Do not include in customer-health scoring**
- Suppress percentages with tiny denominators; show denominator when shown
- Kill switch: `PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED=false`

## Kill switches

- `PRODUCT_ANALYTICS_ENABLED=false` — no writes; no expensive queries; dossier shows disabled/unavailable, **not** zero activity
- Accessibility switch separate (above)

Frontend receives safe booleans from authorized APIs only — never raw env.

## Security controls

- Identity from authenticated session only
- Impersonation and platform-admin browsing excluded from organic customer metrics
- Strict allowlists; reject entire event on prohibited keys
- Rate limits and request-size limits
- Parameterized SQL
- Analytics failures must not roll back core product transactions

## Future legal / privacy review points

- Enabling accessibility signals
- Expanding event set beyond this slice
- Founder aggregate page
- Any cross-tenant cohort reporting
- Retention changes beyond documented defaults
