# Automation Studio – Execution Correctness & Reliability

This doc tracks the reliability pass for Automation Studio: truth-first behavior, real connectors, queue isolation, and observability.

## Engine ownership (anti-drift)

- **Source of truth for runtime automation execution:** `services/automation_engine.py`
- **Queue/worker execution path:** `services/automation_queue.py` -> `services/automation_engine.py`
- **Scheduler time-based execution path:** `core/cleanup_scheduler.py` -> `services.automation_engine.run_due_time_based_automations()`
- `core/automation_engine.py` is now a **compatibility shim** that re-exports `services/automation_engine.py` so legacy imports cannot diverge behavior.

## Done (Week 1 – Truth first + real webhook)

### 1. Action capability registry
- **Backend**: `services/automation_engine.py`
  - `ActionCapability` enum: `implemented` | `partial` | `stub`
  - `ACTION_CAPABILITIES` maps each `ActionType` to a capability
  - `get_action_capabilities()` returns list of `{ action_type, capability, description }`
- **API**: `GET /api/automation/capabilities` returns per-action capability flags
- **UI**: `frontend/src/pages/Automations.tsx` shows “Not implemented yet” / “Partial” badges per preset and surfaces 501 message on Run Test

### 2. No fake success for stubs
- Stub handlers return `success: False`, `error_code: 'NOT_IMPLEMENTED'`, and a clear `error` message
- **API**: Execution endpoints return **501 Not Implemented** when any executed rule uses a stub action:
  - `POST /api/automation/execute` (by rule IDs)
  - `POST /api/automation/test` (single rule)
  - `POST /api/automation/test/preset` (preset by slug)
- Failed-rule payload includes `error_code` so the route can distinguish NOT_IMPLEMENTED from other failures

### 3. Stub vs implemented actions (current)
| Action | Capability | Notes |
|--------|------------|--------|
| send_email | stub | Gmail send not integrated |
| apply_label | stub | Gmail label API not integrated |
| archive_email | stub | Gmail archive API not integrated |
| create_task | stub | Task system not integrated |
| send_notification | **partial** | Slack when webhook URL set |
| trigger_webhook | **implemented** | Real HTTP POST, timeout, retries, optional HMAC |
| update_lead_stage, add_lead_activity | implemented | CRM service |
| schedule_follow_up, create_calendar_event | implemented | DB + optional integrations |
| update_crm_field, create_invoice, assign_team_member | implemented | DB |
| send_sms | partial | Works when Twilio configured |
| generate_document | partial | Depends on document templates |

### 4. Real webhook delivery
- **Implemented in**: `services/automation_engine.py` – `_execute_trigger_webhook`
- **Behavior**:
  - HTTP POST with JSON body (no fake success)
  - Timeout: configurable 5–30s via `timeout_seconds` in action_parameters (default 10)
  - Retries: up to 2 retries (3 attempts total) with exponential backoff
  - Optional signature: if `webhook_secret` is set in action_parameters, request includes `X-Fikiri-Signature: sha256=<hmac_sha256(body)>` for verification on receiver side
- **Errors**: `WEBHOOK_DELIVERY_FAILED` / `WEBHOOK_ERROR` with message; no 501 for webhook (action is implemented)

### 5. Missing engine methods (fixed)
- `execute_rules(user_id, rule_ids)` – used by `POST /api/automation/execute`; runs each rule with synthetic trigger data
- `test_rule(rule_id, test_data, user_id)` – used by `POST /api/automation/test`
- `_synthetic_trigger_data_for_rule(rule)` – builds minimal trigger payload for one-shot runs

---

## Next (Weeks 1–4)

### Reliable execution core (queue + job states) — **DONE**
- **Automation job queue**: `services/automation_queue.py` – `AutomationJobManager`
  - **DB table** `automation_jobs`: job_id, user_id, payload_type, payload_json, idempotency_key, status, attempt, max_attempts, created_at, started_at, completed_at, error_message, result_json
  - **Job states**: `queued` | `running` | `success` | `failed` | `retrying` | `dead`
  - **queue_automation_job(user_id, rule_ids=…|trigger_type=…, trigger_data=…, idempotency_key=…)** – creates job; returns job_id or None (duplicate)
  - **process_automation_job(job_id)** – loads job, runs engine (execute_rules or execute_automation_rules), updates state; used by worker or sync fallback
  - **Retries**: attempt/max_attempts; on exception, status set to retrying then dead after max
  - **Idempotency**: optional idempotency_key; if a recent job with same key completed successfully, queue_automation_job returns None
- **Redis**: `core/redis_queues.py` – `automation_queue` and `get_automation_queue()`; task `process_automation_run(job_id)`
- **Routes**:
  - `POST /api/automation/execute` – creates job, enqueues to Redis when connected (returns `{ job_id, status: 'queued' }`), else runs sync and returns `{ job_id, status: 'completed', execution_results }`; optional body `idempotency_key`
  - `GET /api/automation/jobs/<job_id>` – job status and result
  - `GET /api/automation/queue-stats` – queue depth (queued, running, success, failed, retrying, dead) for last 7 days
- **Worker**: `scripts/rq_worker.py` – register `process_automation_run`, add `automation` queue; run with `python scripts/rq_worker.py automation` or all queues

### Real Slack / notifications — **DONE**
- **send_notification** is **PARTIAL**: when **slack_webhook_url** is set (in action parameters or `SLACK_WEBHOOK_URL` env), the engine POSTs to Slack Incoming Webhooks; otherwise returns **501 NOT_IMPLEMENTED**.
- Preset **Slack summaries** has config field **Slack webhook URL**; optional **channel** in payload.

### Observability — **DONE**
- **GET /api/automation/metrics?hours=24**: queue depth, success_rate_24h, p95_duration_seconds. User-scoped.
- **Queue health panel** on Automation Studio: Queued, Running, Success, Failed, Dead, Success rate (24h), p95.
- Alerts (future): failure-rate spike, queue backlog age.

### Stress readiness
- Load-test: burst lead creation, webhook failures, Gmail outages
- SLOs: e.g. 99% success for healthy dependencies, p95 &lt; 5s processing start time

---

## References
- Execution correctness and reliability plan: user request (stress tuning + execution correctness + reliability architecture)
- Admin / safety: [docs/ADMIN_ROUTES_STRATEGY.md](ADMIN_ROUTES_STRATEGY.md)
- Financial / rate limiting: [docs/FINANCIAL_MODEL_AND_RATE_LIMITING.md](FINANCIAL_MODEL_AND_RATE_LIMITING.md)
