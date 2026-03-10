# Quality Gate: How Errors Were Caught and How to Prevent Them

This doc explains how a reviewer (Codex) found correctness and reliability gaps in the Automation Studio work, and turns that into a **reusable protocol** so Cursor (or any implementer) can catch similar issues before shipping.

---

## 1. How the Errors Were Caught

### Claim-vs-code diff

- The implementation summary was treated as a **spec**.
- Each stated claim was checked **directly in the code** (engine, queue, routes, worker, frontend).
- Where behavior diverged from the stated contract, it was marked as a finding.

Example: Summary said "job success/failed/retrying/dead" and "execution correctness." Code only failed the job when `error_code == 'NOT_IMPLEMENTED'`; other action failures still led to `AUTOMATION_JOB_SUCCESS`. That’s a **contract mismatch**.

### State-machine tracing

- For queue/workflow features, the full lifecycle was traced: `queued → running → success | failed | retrying | dead`.
- For each transition, the reviewer checked: Is the state updated in the DB? Is there a side effect (e.g. re-enqueue) when the label says "retrying"?

This showed that `status: 'retrying'` was set in the job row but **nothing ever re-enqueued** the job, so "retrying" was a dead label.

### Semantic mismatches, not just syntax

- "Fail if any rule fails" was compared to code that only treated `NOT_IMPLEMENTED` as failure.
- "Retrying" was compared to code that had no requeue.
- "Idempotency prevents duplicate run" was compared to code that only skipped when a **previous success** existed for the key—so a duplicate while the first run was still queued or failed could start a second run.

Focus was on **meaning**, not only "does it run."

### Tests as baseline + coverage gaps

- The existing test suite was run to confirm baseline (e.g. 31 passed).
- Then the reviewer asked: Is there a test for **one rule fails (non–NOT_IMPLEMENTED)**? For **retry then success**? For **retry then dead**? For **duplicate idempotency key**? Gaps there indicated risky, untested branches.

---

## 2. What Cursor Should Do Differently (The Protocol)

Use this **before** considering a feature "done."

### Step 1: Build a contract table first

Before or while coding, maintain a table:

| Claim | Expected behavior | Code location | Status (pass/fail) | Evidence |
|-------|-------------------|---------------|--------------------|----------|
| Job fails when any rule fails | Job status = failed if any execution_result has success=False | automation_queue.process_automation_job | fail | Only NOT_IMPLEMENTED branch sets failed |
| Retrying implies future attempt | Re-enqueue or schedule next run | automation_queue + worker | fail | No enqueue on retrying |
| … | … | … | … | … |

**Rule:** Do not report "done" until every major claim has a row and either **pass** or an explicit fix.

### Step 2: Model state transitions explicitly

For queues, workflows, or jobs, require a **transition table**:

| Event | From state | To state | Side effects |
|-------|------------|----------|--------------|
| Worker picks job | queued | running | started_at set |
| All rules succeed | running | success | completed_at, result_json |
| Any rule fails (non-stub) | running | failed | completed_at, error_message |
| Exception, attempts left | running | retrying | error_message, **re-enqueue** |
| Exception, no attempts left | running | dead | completed_at, error_message |

**Rule:** Reject designs where a non-terminal label (e.g. `retrying`) has **no transition trigger** (no re-enqueue, no scheduler, no worker that re-processes it).

### Step 3: Check negative paths first

Before signing off, verify:

- **Partial failures:** e.g. 3 rules, 1 fails → job outcome and status correct?
- **Retries exhausted:** after max_attempts, state becomes `dead` and no further run.
- **Dependency down:** Redis down, webhook timeout, external API 5xx → handled without false success.
- **Duplicate requests / idempotency:** second request with same key does not create duplicate side effects (define: block on any recent run with that key, or only after success?).
- **Auth / tenant scope:** job status and metrics scoped to current user; no cross-tenant leakage.

Most production bugs are in these paths, not the happy path.

### Step 4: Require invariants

Write down invariants and ensure code enforces them. Examples:

- **Job is success only if all targeted rules succeeded.** (So: if any rule returns success=False and not NOT_IMPLEMENTED, job must be failed.)
- **`retrying` always implies a scheduled future attempt.** (So: set status to retrying only when you also re-enqueue or schedule.)
- **Duplicate idempotency key does not produce duplicate side effects within TTL.** (So: define "duplicate" and enforce it—e.g. block if a run with that key exists in queued/running/success in the window.)
- **Every route outcome maps to a stable HTTP contract.** (So: 200/201/400/401/404/501/409 have clear meanings and response shapes.)

### Step 5: Force branch-complete tests

At least one test per critical branch:

- All rules succeed → job success.
- One rule fails (non–NOT_IMPLEMENTED) → job failed.
- One rule NOT_IMPLEMENTED → job failed (or 501 at API boundary).
- Retry then success → job eventually success.
- Retry then dead → job dead after max_attempts.
- Duplicate idempotency key → no second job / 409.
- Unauthorized access to job status → 404 or 403.

Avoid "green suite, broken behavior" by covering both success and failure branches.

### Step 6: Return findings by severity

When reviewing, classify findings:

- **Critical:** Correctness, data loss, security (e.g. job marked success when rules failed).
- **High:** Contract mismatch, reliability (e.g. retry never re-enqueues).
- **Medium:** Observability, maintainability (e.g. missing log fields).
- **Low:** Polish, wording, minor UX.

Report in that order so the most important issues are fixed first.

---

## 3. Prompt to Paste into Cursor (Quality Gate)

Use this at the **start** of a feature or before marking it done:

```
Before writing code, create a contract-vs-implementation checklist for this feature. Then implement with explicit state-transition guarantees. After coding, run a failure-first review: partial failure handling, retries, idempotency, auth scoping, and HTTP contract consistency. Do not report success until each claim has code evidence and test coverage for success + failure branches.
```

Shorter variant for follow-up reviews:

```
Run a failure-first review on [feature/module]: partial failure handling, retries, idempotency, auth scoping, and HTTP contract consistency. For each claim in the summary/spec, show code location and status (pass/fail). Report findings by severity (critical/high/medium/low). Do not mark done until critical/high are resolved or explicitly accepted.
```

---

## 4. Reference: Automation Findings (Examples)

| Finding | Severity | Status | Fix |
|---------|----------|--------|-----|
| Job marked success when one or more rules failed | Critical | **Fixed** | In rule_ids and trigger mode: if any rule failed (success=False or failed_rules non-empty), set job status to failed. |
| Retrying jobs never re-enqueued | High | **Fixed** | On status=retrying, re-enqueue via get_automation_queue().enqueue_job('process_automation_run', {job_id}, delay=backoff_sec). |
| Idempotency only after prior success | High | **Fixed** | Block when any recent job with same key has status in (queued, running, success). |
| Capabilities endpoint unauthenticated | Medium | **Fixed** | GET /api/automation/capabilities now requires get_current_user_id(); returns 401 if missing. |

---

## 5. Where This Lives

- **This file:** `docs/CURSOR_QUALITY_GATE.md` — methodology, protocol, prompt, and example findings.
- **Automation-specific:** `docs/AUTOMATION_RELIABILITY.md` — what was implemented; update with fixes when the above issues are addressed.
- **Cursor rules:** You can add a short pointer in `.cursorrules` or a Cursor rule: "For queue/workflow/automation features, follow the contract table and failure-first review in docs/CURSOR_QUALITY_GATE.md before marking done."

---

*Summary: Treat the spec as a contract, trace state machines, check negative paths and invariants, add branch-complete tests, and report by severity. Use the prompt so Cursor applies this protocol and avoids "green tests, broken behavior."*
