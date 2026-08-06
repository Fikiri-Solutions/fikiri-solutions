# Product Analytics Events

Governance for Fikiri customer-success / product analytics.

Kill switches (default **off**):

- `PRODUCT_ANALYTICS_ENABLED=false`
- `PRODUCT_ANALYTICS_ACCESSIBILITY_SIGNALS_ENABLED=false`

## Tenant identity

Analytics stores separate `tenant_id` and `actor_user_id`. Today tenant ownership maps to the account user ID; both fields may equal that ID. Interfaces preserve a separate tenant concept for future organization support.

## Event source

Controlled values: `client` | `server` | `derived`.

When a business outcome exists in an authoritative database or backend workflow, emit or derive it **server-side**. Client completion events are supplementary and must not double-count.

## Ingestion audience

Authenticated application users may submit events for their own tenant (including in-product organization admins).

Excluded from organic customer analytics:

- Platform-operator browsing `/admin`
- Impersonated sessions (support traffic must not inflate adoption)

## Prohibited properties

Presence of secret-like or content keys rejects the **entire** event (no partial store). Never log rejected values — reason codes / key names only.

Examples: `password`, `token`, `authorization`, `cookie`, `secret`, `code`, `email_body`, `message`, `notes`, `card`, `clipboard`.

Client-supplied `tenant_id` / `user_id` / `actor_user_id` are rejected.

## Approved events (this slice)

| Event | Purpose | Typical source | Health? | Retention |
|-------|---------|----------------|---------|-----------|
| `session.started` | Coarse session begin | client/server | no | raw 90d |
| `feature.opened` | Major feature navigation | client | no | raw 90d |
| `workflow.started` | Controlled workflow begin | client/server | no | raw 90d |
| `workflow.failed` | Controlled workflow failure | client/server/derived | yes | raw 90d |
| `onboarding.step_completed` | Onboarding step advanced | client/server/derived | yes | raw 90d |
| `error.category` | Controlled error category | client/server | yes | raw 90d |
| `outcome.lead_captured` | Lead durably created | **server only** | yes | raw 90d |
| `outcome.sync_completed` | Gmail sync job completed | **server only** | yes | raw 90d |
| `outcome.integration_connected` | Integration connected | **server/derived only** | yes | raw 90d |
| `outcome.onboarding_completed` | Onboarding complete | **server/derived only** | yes | raw 90d |
| `accessibility.*` | Interface preferences | client | **never** | raw 90d; kill-switched |

### Server emission (post-commit)

Helper: `core/product_analytics_emit.emit_server_product_event` (no HTTP).

- `event_source=server`; dedupe key `{short_event}:{object_type}:{object_id}` unique per tenant
- Kill switches: `PRODUCT_ANALYTICS_ENABLED`, optional `PRODUCT_ANALYTICS_TENANT_ALLOWLIST`
- Skips impersonation; never rolls back CRM/sync on analytics failure
- Lead props: `source_category`, `creation_channel`, `feature_key`, `workflow_key`, `outcome`, `completed`, `schema_version`
- Sync props: `provider`, `sync_type`, `result_category`, `processed_count_bucket` (+ controlled feature/workflow fields)
- No PII, OAuth, or email content

### Failure contract (narrow)

Business operations must still succeed. Analytics failures are **classified**, not silently swallowed:

| Condition | Result `reason` | Telemetry |
|-----------|-----------------|-----------|
| Storage unavailable / timeout | `STORAGE_UNAVAILABLE` / `STORAGE_TIMEOUT` | warning: exception class + correlation_id |
| Duplicate outcome | `DUPLICATE` | none (expected) |
| Registry misuse / prohibited props / invalid construction | reject code (e.g. `PROHIBITED_PROPERTY`) | warning `product_analytics.programmer_reject` (reason + event_name + correlation_id; **never** property values) |
| Unexpected (schema mismatch, programming error) | `UNEXPECTED_ERROR` | error `product_analytics.server_unexpected` (exception class + correlation_id + phase; **never** properties) |

Do not use a broad `except Exception: pass` at call sites to hide defects. Call-site boundaries may only catch import/boundary failures and must log `exception_class` + `correlation_id`.

### Canonical aggregation sources (do not double-count)

Keep this division. Future developers must not add the same outcome from both raw tables and emitted events into one metric:

| Information | Canonical source |
|-------------|------------------|
| Total leads | `leads` table |
| Total completed syncs | `gmail_sync_jobs` completed rows |
| Meaningful activity | Server product events → `tenant_daily_metrics` |
| Time to first value | Earliest authoritative server `outcome.*` in `product_events` |
| Historical period before tracking | **Partial** coverage (no silent backfill) |

### Pre-rollout checks (staging)

Before enabling outcomes in staging:

1. Apply `scripts/migrations/009_product_analytics.sql`.
2. Apply `scripts/migrations/010_product_analytics_ops.sql` (ops counters).
3. Confirm unique index `idx_product_events_outcome_dedupe` exists on PostgreSQL.
4. Enable analytics for **one internal tenant only** (`PRODUCT_ANALYTICS_TENANT_ALLOWLIST`).
5. Create one real internal test lead → verify exactly one `outcome.lead_captured` for that lead id.
6. Complete one sanitized Gmail sync → verify exactly one `outcome.sync_completed` for that job id.
7. Replay both operations → confirm no duplicate rows.
8. Inspect `properties_json` for prohibited or unexpected fields.
9. Verify tenant dossier shows partial coverage and a sensible first-value timestamp.
10. Temporarily interrupt analytics storage → confirm CRM lead create and Gmail sync still complete normally.
11. Run the manual ops check (below) and confirm missing counts are explained (pre-tracking history or known gap), not silently backfilled.

### Manual ops check (read-only)

Answers: “Is analytics working, and are these numbers believable?”

- **HTTP:** `GET /api/admin/platform/tenants/<id>/analytics-ops?lookback_days=7|30&reconcile=1`
  - Requires `platform.tenants.read`. No mutations.
- **CLI:** `python3 scripts/report_product_analytics_ops.py --tenant-id <id> --lookback-days 7`

Report includes: enabled flag, allowlist, analytics state (`disabled|collecting|available|stale|unavailable`), last event / aggregate times, storage-failure and rejected-event counts, and a bounded reconciliation of recent leads / completed Gmail syncs vs emitted outcomes (report-only, **no backfill**).

### Deferred (registered concepts only / not authoritative this slice)

- `session.ended` (unreliable)
- Client-declared successful business outcomes
- Generalized `workflow.abandoned` / inferred abandonment (prefer later; **not next**)
- Exact active-time / estimated time saved
- Full founder aggregates
- Sophisticated continuous reconciliation engines, automatic repairs, historical backfills, or a major new admin dashboard

## Allowlisted property families

`feature_key`, `workflow_key`, `step_id`, `outcome`, `duration_bucket`, `device_class`, `browser_family`, `os_family`, `viewport_category`, `correlation_id`, `error_category`, `status_code_category`, `retry_count`, `completed`, `session_id_hash`, `source_category`, `creation_channel`, `provider`, `sync_type`, `result_category`, `processed_count_bucket`, `schema_version`.

Unknown properties reject the event in this slice.

## Operator visibility

Platform operators with `platform.tenants.read` may see **aggregated** tenant metrics and controlled friction codes on the tenant dossier. Raw event JSON is not shown in the admin UI.
