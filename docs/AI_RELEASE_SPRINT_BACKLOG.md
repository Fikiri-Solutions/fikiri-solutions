# AI Release Sprint Backlog (Implementation-Ready)

Scope: first AI product release for inbound email triage + CRM action recommendation, aligned with Fikiri architecture and quality-gate rules.

## Epic 1: Evaluation foundation and baselines

### Story 1.1 - Define metric dictionary and thresholds
- Why this choice: avoid subjective quality claims; enforce launch gates.
- What to measure: macro-F1, urgency F1, schema pass rate, unsafe rate, p95 latency, cost/request.
- Acceptance criteria:
  - Metrics and formulas documented in `docs/FOUNDATION_MODEL_PROMPT_PACK_EXECUTION.md`.
  - Threshold constants centralized in one config module.
  - CI fails when required thresholds are missing.
- Dependencies: none.

### Story 1.2 - Build golden/adversarial/drift datasets
- Why this choice: establish reliable offline evaluation loop before rollout.
- What to measure: dataset coverage by intent and risk class.
- Acceptance criteria:
  - Dataset snapshots exist with version IDs (`email-triage-v1` etc.).
  - At least 2k labeled golden samples and 300 adversarial samples.
  - Drift set sampling job created with weekly cadence.
- Dependencies: Story 1.1.

### Story 1.3 - Add repeatable eval runner
- Why this choice: prevent one-off manual eval and inconsistent comparisons.
- What to measure: run frequency, reproducibility, and pass/fail outcome.
- Acceptance criteria:
  - Command exists under `scripts/` to run offline eval end-to-end.
  - Outputs include aggregate metrics and per-intent breakdown.
  - Eval summary persisted for trend comparison.
- Dependencies: Stories 1.1, 1.2.

## Epic 2: Prompt/policy hardening for email triage

### Story 2.1 - Promote prompt spec to executable templates
- Why this choice: keep prompt behavior deterministic and auditable.
- What to measure: schema failure rate and prompt regression rate.
- Acceptance criteria:
  - Prompt template + output schema references live in `core/ai/`.
  - Unit tests verify required fields and refusal behavior.
  - Prompt version tagged in logs/metadata.
- Dependencies: Epic 1 baseline.

### Story 2.2 - Enforce risk policy before any send action
- Why this choice: no unsafe auto-send incidents.
- What to measure: % actions routed to human review, unsafe send rate.
- Acceptance criteria:
  - `core/ai/policies/*` gates every outbound action decision.
  - Fail-closed behavior when policy checks fail.
  - Tests cover low-risk auto-send and high-risk forced review branches.
- Dependencies: Story 2.1.

### Story 2.3 - Context normalization contract
- Why this choice: remove prompt variability and cross-feature drift.
- What to measure: missing-context error rate and recommendation usefulness.
- Acceptance criteria:
  - All triage entry points call shared context builder contract.
  - Duplicate context injection prevented.
  - Tests verify thread history + CRM context inclusion.
- Dependencies: Story 2.1.

## Epic 3: Observability and reliability controls

### Story 3.1 - Add AI pipeline dashboard metrics
- Why this choice: make rollout decisions from live evidence.
- What to measure: latency, cost, fallback rate, schema-fail rate, unsafe rate.
- Acceptance criteria:
  - Metrics endpoint exposes required AI KPIs.
  - Dashboard spec in docs with owners.
  - Alert thresholds mapped to severity levels.
- Dependencies: Epic 1 metrics definitions.

### Story 3.2 - Add rollback switches and degraded mode
- Why this choice: controlled failure handling during alpha/beta.
- What to measure: rollback activation time and incident containment.
- Acceptance criteria:
  - Feature flag disables auto-send immediately.
  - Fallback model route available for degraded mode.
  - Runbook includes step-by-step rollback procedure.
- Dependencies: Story 2.2.

### Story 3.3 - Queue + idempotency contract checks
- Why this choice: prevent duplicate actions and inconsistent job states.
- What to measure: duplicate-action rate and job state transition correctness.
- Acceptance criteria:
  - Contract table added for queue states and side effects.
  - Tests cover partial failure, retry, dead-letter, and duplicate idempotency key.
  - Quality gate passes per `docs/CURSOR_QUALITY_GATE.md`.
- Dependencies: existing queue implementation.

## Epic 4: Launch execution (shadow -> alpha -> beta)

### Story 4.1 - Shadow mode deployment
- Why this choice: measure quality without user-facing risk.
- What to measure: offline vs shadow parity, recommendation match rate.
- Acceptance criteria:
  - AI recommendations logged but not auto-applied.
  - Sample review workflow active for product/ops.
  - Exit criteria report generated after 2 weeks.
- Dependencies: Epics 1-3.

### Story 4.2 - Internal alpha with feedback capture
- Why this choice: calibrate utility and safety with real operators.
- What to measure: accept/edit/reject rates and edit distance.
- Acceptance criteria:
  - UI supports accept/edit/reject capture.
  - Human rubric scoring process documented and assigned.
  - Weekly review cadence active.
- Dependencies: Story 4.1.

### Story 4.3 - Limited beta and GA decision packet
- Why this choice: enforce disciplined release and leadership signoff.
- What to measure: 30-day stability against all launch gates.
- Acceptance criteria:
  - Beta cohort is tenant-scoped and reversible.
  - GA packet includes KPI trends, incidents, and residual risks.
  - Leadership decisions logged and approved.
- Dependencies: Story 4.2.

---

## Sprint plan (5 sprints)

### Sprint 1
- 1.1, 1.2 (dataset bootstrap), 2.1 (prompt skeleton), 3.1 (metric plumbing start)
- Done when:
  - first offline eval run completes and metrics are visible.

### Sprint 2
- 1.3, 2.1 complete, 2.2, 2.3
- Done when:
  - policy-gated decisioning runs with branch-complete tests.

### Sprint 3
- 3.1 complete, 3.2, 3.3, 4.1
- Done when:
  - shadow mode active and rollback switch validated.

### Sprint 4
- 4.2 + remediation loops from shadow/alpha findings
- Done when:
  - acceptance rate and safety targets hit for internal users.

### Sprint 5
- 4.3 + GA readiness review
- Done when:
  - 30-day beta passes launch gates with no critical safety incidents.

---

## Critical path

1. Metric/threshold definitions -> dataset and eval runner
2. Prompt schema reliability -> policy gating
3. Observability + rollback controls
4. Shadow -> alpha -> beta progression

Anything bypassing this path is non-blocking for first release.

---

## Milestone definitions of done

### Milestone M1 (Baseline)
- Offline eval is automated and reproducible.
- Core thresholds and fail conditions are enforced.
- Dataset versioning in place.

### Milestone M2 (Safe assistant)
- Every outbound recommendation/action passes policy gate.
- High-risk intents require human review.
- Red-team suite completed with no critical unresolved issues.

### Milestone M3 (Beta-ready)
- p95 latency and cost targets met.
- Rollback switches tested in staging.
- Ops runbook approved by engineering + product + security owner.

---

## Risk-adjusted plan

- Primary risk: unsafe action recommendation in ambiguous cases.
  - Mitigation: force human review and conservative defaults.
- Secondary risk: quality drift over tenant segments.
  - Mitigation: weekly drift runs and threshold alerts.
- Tertiary risk: model cost spikes.
  - Mitigation: routing policy and migration trigger thresholds.

