# AI Week 1 Execution Checklist (Do the Work)

This is the operational checklist for immediate execution of the first prompt-pack phase in Fikiri.

## Objective for Week 1

Stand up baseline evaluation, policy-safe triage plumbing, and evidence collection for shadow-mode readiness.

## Day 1 - Lock contracts and metrics

- [ ] Confirm first-use-case scope: inbound email triage + CRM recommendation.
- [ ] Freeze metric dictionary and thresholds from `docs/FOUNDATION_MODEL_PROMPT_PACK_EXECUTION.md`.
- [ ] Create config constants for launch gates (quality, safety, latency, cost).
- [ ] Add contract table for queue/workflow state transitions per `docs/CURSOR_QUALITY_GATE.md`.

Files to touch:
- `core/ai/schemas.py`
- `core/ai/llm_router.py`
- `docs/FOUNDATION_MODEL_PROMPT_PACK_EXECUTION.md`
- `docs/CURSOR_QUALITY_GATE.md` (reference updates only if needed)

## Day 2 - Dataset and eval runner scaffold

- [ ] Create dataset version manifest (`email-triage-v1`) with golden/adversarial split metadata.
- [ ] Add evaluation runner script under `scripts/` (offline pass).
- [ ] Add placeholder report output path under `docs/` or `security-reports/` style folder for eval artifacts.
- [ ] Add owner + cadence metadata in script output.

Files to touch:
- `scripts/` (new eval runner)
- `tests/` (new eval tests)
- `docs/` (eval runbook/report index)

## Day 3 - Prompt and policy wiring

- [ ] Convert prompt spec to executable template constants and enforce strict output schema.
- [ ] Wire risk policy check into email action path before send decisions.
- [ ] Ensure fail-closed behavior when policy service errors.
- [ ] Add tests for low-risk allow vs high-risk human-review required.

Files to touch:
- `email_automation/pipeline.py`
- `core/ai/policies/auto_send_policy.py`
- `core/ai/policies/email_action_policy.py`
- `core/ai/policies/risk_policy.py`
- `services/email_action_handlers.py`
- `tests/test_email_action_handlers.py`
- `tests/test_ai_email_analysis.py`

## Day 4 - Observability and rollback controls

- [ ] Add/verify AI KPI logging fields: model, intent, tokens, cost, latency, policy decision.
- [ ] Add fallback/degraded mode toggle for AI recommendation path.
- [ ] Add auto-send global kill switch (feature flag/env gate).
- [ ] Document rollback procedure in runbook.

Files to touch:
- `core/ai/llm_router.py`
- `core/ai/llm_client.py`
- `core/structured_logging.py` (if needed)
- `docs/SLOs.md`
- `docs/WORKFLOW_DIAGNOSTIC_PLAYBOOK.md`

## Day 5 - Validate with failure-first quality gate

- [ ] Run branch-complete tests (success + failure + retry/idempotency branches).
- [ ] Run readiness/test commands and capture outputs.
- [ ] Produce Week 1 status note: pass/fail by contract claim.
- [ ] Block any "done" claim until critical/high issues are resolved or accepted explicitly.

Required commands:
- `pytest tests/ -m "not contract and not integration" -q --disable-warnings --maxfail=1`
- `python3 scripts/automation_readiness.py --summary`
- Optional repeatability check:
  - `for i in 1 2 3; do pytest -q tests -m "not contract and not integration" || break; done`

## Definition of done for Week 1

- [ ] Offline eval runner exists and executes.
- [ ] Prompt + schema + policy path is enforced in code.
- [ ] Safety gate is fail-closed for uncertain/high-risk actions.
- [ ] Observability captures required AI metrics.
- [ ] Tests include critical failure branches.
- [ ] Status report includes unresolved risks and owners.

## Non-negotiable guardrails

- Do not bypass `core/ai/llm_router.py` or `core/ai/llm_client.py`.
- Do not auto-send on high-risk or uncertain intent classes.
- Do not mark retrying jobs without a concrete re-execution mechanism.
- Do not ship without launch gate evidence (quality + safety + ops).

