#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Launch Readiness: Backend critical-path tests =="
backend_tests=(
  tests/test_auth_routes.py
  tests/test_business_routes.py
  tests/test_revenue_billing_security.py
  tests/test_automation_safety.py
)

if [[ -f tests/test_automation_queue.py ]]; then
  backend_tests+=(tests/test_automation_queue.py)
else
  echo "== Launch Readiness: tests/test_automation_queue.py missing; skipping =="
fi

python3 -m pytest -q "${backend_tests[@]}"

if [[ "${RUN_INTEGRATION_TESTS:-0}" == "1" ]]; then
  echo "== Launch Readiness: Integration tests =="
  export INTEGRATION_BACKEND_URL="${INTEGRATION_BACKEND_URL:-http://localhost:5000}"
  export INTEGRATION_LOGIN_EMAIL="${INTEGRATION_LOGIN_EMAIL:-test@example.com}"
  export INTEGRATION_LOGIN_PASSWORD="${INTEGRATION_LOGIN_PASSWORD:-TestPassword123!}"
  export INTEGRATION_GMAIL_SYNC_EXPECT="${INTEGRATION_GMAIL_SYNC_EXPECT:-oauth_required}"
  python3 scripts/ensure_test_user.py
  python3 -m pytest -q tests/integration/test_auth_crm_smoke.py tests/integration/test_queue_jobs_integration.py tests/integration/test_automation_launch.py
else
  echo "== Launch Readiness: Integration tests skipped (set RUN_INTEGRATION_TESTS=1) =="
fi

if [[ "${RUN_E2E_TESTS:-0}" == "1" ]]; then
  echo "== Launch Readiness: Frontend E2E tests =="
  (
    cd frontend
    # setup+e2e: main app smoke (completed-onboarding storage)
    npx playwright test tests/e2e.auth.spec.ts tests/e2e.automations.spec.ts --project=setup --project=e2e
    # setup+onboarding-e2e: onboarding uses new-user storage + distinct Playwright config
    npx playwright test tests/e2e.onboarding.spec.ts --project=setup --project=onboarding-e2e
  )
else
  echo "== Launch Readiness: E2E tests skipped (set RUN_E2E_TESTS=1) =="
fi

echo "== Launch readiness test run complete =="
