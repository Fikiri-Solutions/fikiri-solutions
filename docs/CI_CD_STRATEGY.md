# CI/CD Strategy and Test Gate

How we structure pipelines so most commits get a clear pass/fail without flakiness, and when to tighten or relax.

---

## 1. Why most commits were failing

- **Six workflows** run on push/PR to `main` (and some on `develop`): `ci-cd.yml`, `backend.yml`, `smoke-test.yml`, `test.yml`, `testing.yml`, `frontend.yml`. Overlap and different triggers cause confusion.
- **Backend “unit” runs included everything**: `pytest tests/` was run without excluding `integration` or `contract`. So integration/contract tests (Redis, DB, optional secrets) ran in the main gate and failed when env wasn’t set or tests were flaky.
- **Smoke test starts the full app**: Any missing import (e.g. `core.ai_budget_guardrails` before it was committed or stubbed) failed the job. That’s correct behavior for “does the app start?” but it runs on every push/PR, so a single missing file broke the pipeline.
- **Path filters differed**: `backend.yml` only runs when `core/**`, `app.py`, or `requirements.txt` change—so changes in `routes/` didn’t trigger it, but `ci-cd.yml` did and ran full pytest including integration.
- **Result**: The guardrails were catching real issues (missing module, import errors) but the gate was also running heavy/flaky tests and multiple overlapping workflows, so “most commits fail” was a mix of real bugs and pipeline design.

---

## 2. Principle: one clear gate, then optional heavy checks

- **Gate (required for every push/PR)**  
  Fast, deterministic, no external services (or only Redis in a service container):
  - Backend: lint + **unit tests only** (`pytest tests/ -m "not contract and not integration"`).
  - Frontend: lint + type-check (optional) + unit tests + build.
  - Same as local “fast” run in [TESTING.md](TESTING.md).

- **Secondary (optional or main-only)**  
  Run after gate or only on `main`:
  - **Smoke test**: “Does the app start and can we log in?” — run on `main` or after deploy; optional on PR (or allow failure until stable).
  - **Integration tests**: `pytest tests/integration/` with Redis + SQLite; can run in a separate job, only on `main`, or with `continue-on-error: true` until stable.
  - **Contract tests**: Require sandbox secrets; run manually or in a separate workflow, not in the PR gate.
  - **Security / performance**: After gate passes; don’t block the gate on Trivy/npm audit unless you explicitly want that.

---

## 3. Current layout (after restructuring)

| Workflow        | Purpose | When it runs | Must pass for merge? |
|----------------|--------|--------------|----------------------|
| **ci-cd.yml**  | Main gate: backend unit (with markers), frontend lint/unit/build; security + optional perf; deploy on main/develop | Push/PR to main, develop | **Yes** (backend + frontend jobs) |
| **backend.yml**| Backend-only path filter: same unit test gate when only backend code changes | Push/PR when `core/**`, `app.py`, `requirements.txt` change | Yes when triggered |
| **frontend.yml**| Frontend-only path filter: lint, unit, build | Push/PR when `frontend/**` changes | Yes when triggered |
| **smoke-test.yml** | App start + auth smoke | Push/PR to main (or main only — see below) | Prefer **main only** or allow failure on PR |
| **test.yml**     | Frontend tests + live health checks to production URLs | Push/PR | Consider deprecating or run only on main |
| **testing.yml**  | Broad suite + integration + perf + security | Push/PR + daily | Consider consolidating into ci-cd or run nightly only |

Recommendation: **Gate = ci-cd (backend + frontend jobs).** Smoke runs on `main` only so PRs don’t depend on “app starts” until merge. Integration/contract stay out of the gate.

---

## 4. What we changed

- **Backend in ci-cd and backend.yml**: Use `pytest tests/ -m "not contract and not integration"` so only unit/route tests run in the gate. Integration and contract run separately or on demand.
- **Smoke**: Option A — run only on `main` (e.g. `push: branches: [main]`). Option B — run on PR but with `continue-on-error: true` until app-start is stable. Option C — keep on both but document that smoke is the “app starts” canary; we already made `routes/business` resilient to missing `ai_budget_guardrails`.
- **Single source of truth for “fast backend tests”**: Same command as in TESTING.md:  
  `pytest tests/ -m "not contract and not integration" -v`

---

## 5. Local = CI

Before pushing, run what the gate runs:

```bash
# Backend (gate)
pytest tests/ -m "not contract and not integration" -q

# Frontend (gate)
cd frontend && npm run lint && npm run test:unit && npm run build
```

If these pass locally, the gate should pass. If the gate fails and local passes, check markers and that integration/contract are excluded in CI.

---

## 6. When to tighten or relax

- **Tighten (fail more)**  
  - Add integration to the gate and provide Redis + env in CI.  
  - Run smoke on every PR and fix any app-start flakiness.  
  - Make type-check or security (e.g. Trivy) required.

- **Relax (fail less)**  
  - Keep smoke main-only.  
  - Run integration/contract only on main or nightly.  
  - Use `continue-on-error` for non-blocking jobs and fix failures over time.

---

## 7. Summary

- **Root cause of “most commits fail”**: Gate ran full test suite (including integration/contract), multiple overlapping workflows, and smoke required app start on every push. Mix of real bugs (e.g. missing module) and pipeline design.
- **Fix**: One clear gate (unit-only backend + frontend lint/unit/build). Smoke and integration secondary or main-only. Use pytest markers consistently so CI matches TESTING.md.
