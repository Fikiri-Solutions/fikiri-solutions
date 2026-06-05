# PR 2 Email Worker Cost and Scale Report

**Report date:** 2026-06-03
**Scope:** Gmail sync worker cost controls for the recommended deployment shape: one web service, one worker service, and shared database/Redis where needed.

## Goal

Keep email sync work in the worker and reduce avoidable database churn while preserving user-visible progress and mailbox automation behavior.

## High-impact change shipped

| ID | Area | Issue / cost driver | Root cause | Fix | Regression evidence |
|---|---|---|---|---|---|
| PR2-001 | Gmail sync worker progress writes | A 50-message sync could write job progress after every message and update user sync status frequently, creating unnecessary database load when multiple inboxes sync at once. | `_sync_emails` performed per-message progress writes and repeated status count queries. | Added `GMAIL_SYNC_PROGRESS_UPDATE_EVERY` with a default of `10`; intermediate progress/status writes now happen on the first message, every N messages, and the final message. Final completion still writes 100%. | `tests/test_gmail_sync_jobs.py::TestGmailSyncCostControls::test_sync_throttles_progress_writes_and_reuses_owner_email`. |
| PR2-002 | Gmail sync owner lookup | The worker queried the mailbox owner email inside the message loop even though it is job-level data. | Owner email was resolved per message before `orchestrate_incoming`. | Resolve owner email once before the loop and reuse it for all messages in the job. | Same regression test asserts one owner-email query for 25 messages. |

## Expected impact

For a 50-message batch with default settings:

- Previous intermediate progress writes: up to 50 job-progress updates, plus frequent status/count updates.
- New intermediate progress writes: first message, every 10 messages, and final message — about 6 progress/status update points.
- Owner email queries: reduced from one per message to one per job.

This is intentionally a low-risk worker-internal optimization. It does not change Gmail fetching, stored email content, mailbox automation decisions, or final job completion metadata.

## Contract-vs-implementation checklist

| Claim | Expected behavior | Evidence | Status |
|---|---|---|---:|
| Worker remains the place for sync processing. | `_sync_emails` is still invoked from `process_sync_job`; web requests queue jobs and return early from the prior PR. | `email_automation/gmail_sync_jobs.py` worker path unchanged. | Pass |
| Progress remains visible without per-message DB churn. | Initial progress and final completion still write, while intermediate writes are throttled. | `progress_update_every` and progress throttling in `_sync_emails`. | Pass |
| Owner email is job-level state. | Query once before the loop and pass the cached value to `orchestrate_incoming`. | Owner lookup moved before the message loop. | Pass |
| Existing mailbox automation runtime reuse remains intact. | Runtime context is still created once per job when automation is enabled. | Existing mailbox context tests continue to pass. | Pass |

## Follow-up candidates

1. Return `synced_emails.id` from the Gmail upsert path to remove the post-upsert `SELECT id` per message.
2. Batch Gmail message fetches using Gmail batch HTTP or parallel bounded fetches, if the Google client version supports it cleanly.
3. Add queue retry/backoff policy tests around durable job retry and Redis worker failure paths.
4. Batch email event inserts where event ordering does not need immediate per-message persistence.
5. Add AI skip telemetry so we can measure how often `run_mailbox_ai=False` avoids LLM work.
