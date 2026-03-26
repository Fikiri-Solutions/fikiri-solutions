# Correlation ID and domain events

## Correlation spine

- **Edge:** `X-Correlation-ID` header or JSON `correlation_id`, else a new UUID (`core/request_correlation.py`).
- **API responses:** The **canonical** place for clients is the **top-level** `correlation_id` on `create_success_response` / `create_error_response` envelopes.
- **Nested `data.correlation_id`:** Used only where legacy or convenience duplicates it (e.g. some AI chat payloads). Prefer reading **top-level** first; nested may be removed over time.

## event_type prefixes (append-only logs)

| Domain | Table | `event_type` pattern | Notes |
|--------|--------|----------------------|--------|
| CRM | `crm_events` | `lead.*`, `contact.*` | e.g. `lead.created`, `lead.updated` |
| Email | `email_events` | `email.*` | e.g. `email.parsed`, `email.failed` |
| Automations | `automation_run_events` | `automation.*` | e.g. `automation.step_started`, `automation.completed` |
| AI router | `ai_events` | `ai.*` | e.g. `ai.response.generated`, `ai.response.failed` |
| Chatbot / KB | `chatbot_content_events` | `faq.*`, `kb.*`, `chatbot.*` | e.g. `faq.created`, `chatbot.response_generated` |

## Status vocabulary (by domain)

Use consistently for **new** code; existing rows may vary until backfilled.

| Value | Use |
|-------|-----|
| `applied` | Side effect recorded successfully (email pipeline, content events) |
| `completed` | AI / long-running step finished OK |
| `ok` | Automation step succeeded |
| `failed` | Error; set `error_message` |
| `skipped` | Automation rule skipped (conditions, etc.) |
| `cancelled` | User/system cancelled run or withdraw |
| `running` | Step in progress (automation) |
| **Intake (HTTP / rows)** | `received`, `completed`, `failed`, `deduplicated`, `honeypot_filled`, `updated`, `cancelled` on form/lead capture submissions |

## Internal trace API

Authenticated: `GET /api/debug/correlation/<correlation_id>` returns matching rows per domain for **the current user only** (tenant-safe). Disable in production with `FIKIRI_CORRELATION_TRACE=0`.

**App UI:** Logged-in users can open **`/debug/correlation`** (protected route; not linked from marketing pages). Optional query: `?id=<correlation_id>`. Last preset-test correlation is stored in `sessionStorage` under `fikiri-last-automation-correlation-id` for the “Use last preset run ID” helper.

**Limits:** Form intake rows do not yet store `correlation_id` in SQL; traces start where the ID was written (CRM, email, AI, automations, chatbot content events, automation job payload).
