# Regression testing policy

CI still runs the full unit gate on every pipeline (`docs/CI_CD_STRATEGY.md`). Local agent work follows the risk of the change.

## Unit gate

From the repo root:

```bash
pytest tests/ -m "not contract and not integration" -q
cd frontend && npx vitest run
```

`pytest.ini` marks `contract` (sandbox provider credentials, including `tests/contract`) and `integration` (staging DB or Redis, including `tests/integration`). The marker expression is the unit gate.

`pytest tests/ -v --ignore=tests/integration` is not the gate. It still runs `tests/contract`.

Run `pytest tests/ -m integration` only when DB and Redis are available. Run `pytest tests/ -m contract` only when sandbox credentials are available.

## Quick fix

Copy, styles, comments, or a localized bug outside the critical list.

- Run the nearest test, or the linter for the files touched.
- A behavior bug gets a regression test in the same change.
- A typo does not need a new test.
- Do not start the unit gate.

## Feature

One subsystem, and not a critical change.

- Run the test module for that change.
- Include a success path and one failure path.
- Do not start the unit gate.

## Critical change

Run the unit gate once, plus the test module for the area. A bug fix adds a regression test.

Critical means any of: authentication, payments, permissions, admin actions, migrations, CRM uniqueness or merge, outbound email, queues, workflow state, or the production SQLite guard.

The label "quick fix" does not apply if the diff touches that list.

Queues and workflows also follow `docs/CURSOR_QUALITY_GATE.md`.

## Release

Run the unit gate. Run integration and contract tests when that environment is available.

## When a test fails

Fix that failure. Do not rerun a suite that already passed. Do not claim a test passed unless the command ran.
