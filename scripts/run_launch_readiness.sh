#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Launch Readiness: Backend critical-path tests =="
python3 -m pytest -q \
  tests/test_auth_routes.py \
  tests/test_business_routes.py \
  tests/test_revenue_billing_security.py \
  tests/test_automation_queue.py \
  tests/test_automation_safety.py

if [[ "${RUN_INTEGRATION_TESTS:-0}" == "1" ]]; then
  echo "== Launch Readiness: Integration tests =="
  python3 -m pytest -q tests/integration/test_auth_crm_smoke.py tests/integration/test_queue_jobs_integration.py tests/integration/test_automation_launch.py
else
  echo "== Launch Readiness: Integration tests skipped (set RUN_INTEGRATION_TESTS=1) =="
fi

if [[ "${RUN_E2E_TESTS:-0}" == "1" ]]; then
  echo "== Launch Readiness: Frontend E2E tests =="
  (
    cd frontend
    npx playwright test tests/e2e.auth.spec.ts tests/e2e.onboarding.spec.ts tests/e2e.automations.spec.ts
  )
else
  echo "== Launch Readiness: E2E tests skipped (set RUN_E2E_TESTS=1) =="
fi

echo "== Launch readiness test run complete =="
