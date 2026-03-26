# SQLite: comparing stored timestamps

## Problem

Python often stores datetimes with `datetime.isoformat()`, which looks like:

`2026-03-19T12:00:17`

SQLite’s `datetime('now')` returns:

`2026-03-19 12:00:17` (space, no `T`)

If you compare **raw strings**:

```sql
WHERE expires_at > datetime('now')
```

then lexicographic ordering can be wrong because **`'T'` (ASCII 84) > `' '` (ASCII 32)**. A future-looking `expires_at` can sort **after** `now` even when it should be before, or vice versa depending on direction.

Symptoms:

- Sessions / refresh tokens / idempotency keys never match as “valid”
- Email jobs never become eligible to send (fixed in `email_automation/jobs.py`)

## Rule

When comparing **TEXT/DATETIME columns** that may contain ISO-8601 from Python against `datetime('now')` or each other, wrap columns (and bound ISO parameters when needed) in SQLite’s `datetime()` so values are parsed as datetimes:

```sql
WHERE datetime(expires_at) > datetime('now')
WHERE datetime(scheduled_at) <= datetime('now')
WHERE datetime(updated_at) >= datetime(?)
```

## References (codebase)

Audit pattern: any column filled with Python `isoformat()` (often contains `T`) compared to `datetime('now'…)` must use `datetime(column)` on the left (and `datetime(?)` when comparing to a bound ISO string).

Updated modules include (non-exhaustive):

- `email_automation/jobs.py` — `scheduled_at`
- `email_automation/gmail_sync_jobs.py` — `synced_emails.date`
- `core/idempotency_manager.py` — `expires_at`
- `core/user_auth.py` — `user_sessions.expires_at`
- `core/secure_sessions.py` — `expires_at`
- `core/jwt_auth.py` — `refresh_tokens.expires_at`
- `core/kpi_tracker.py` — `subscriptions.updated_at`
- `core/rate_limiter.py` — `rate_limit_violations.last_violation`
- `core/automation_safety.py` — `automation_action_log.created_at`, `oauth_failure_log.created_at`
- `core/oauth_token_manager.py` — `oauth_refresh_failures.created_at`
- `core/database_optimization.py` — view `recent_leads` (`leads.created_at`)
- `core/automation_engine.py`, `services/automation_engine.py` — `lead_activities.timestamp`
- `services/automation_queue.py` — `automation_jobs.created_at`
- `analytics/dashboard_api.py` — `leads.created_at`
- `routes/monitoring.py` — `synced_emails.created_at`
- `crm/service.py` — `lead_activities.timestamp`

When adding new queries, grep for `datetime('now')` and verify any compared column isn’t compared as a raw ISO string.
