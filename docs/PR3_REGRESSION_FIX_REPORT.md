# PR 3 Regression Fix Report

**Report date:** 2026-06-03  
**Scope:** Regression cleanup for the failed test set reported after PR 2, with emphasis on distinguishing true regressions from environment-only failures.

## Failures investigated

| ID | Failing area | Observed failure | Root cause | Fix | Regression evidence |
|---|---|---|---|---|---|
| PR3-001 | Gmail sync mailbox context tests | In a minimal worker/test environment without Flask installed, Gmail sync mailbox tests failed before the patched `orchestrate_incoming` mock was reached. | `_sync_emails` imported `core.trace_context` unconditionally; that module imports Flask globals. A background worker should not require Flask request-context dependencies just to process synced mail. | Made trace-context import tolerant inside the worker path and fallback to `None` when Flask trace context is unavailable. | `pytest tests/test_gmail_sync_jobs.py tests/test_gmail_sync_mailbox_context.py -q` passed. |
| PR3-002 | Gmail contract invalid-token test | Full backend test run made an external Gmail API call even when Gmail contract credentials were not configured. | `test_gmail_invalid_token_returns_401` only skipped when `requests` was absent, unlike the other Gmail contract tests that require configured contract credentials. | Reused the existing Gmail contract credential skip gate for the invalid-token test. | `pytest tests/contract/test_gmail_contract.py::test_gmail_invalid_token_returns_401 -q` skipped cleanly without credentials. |
| PR3-003 | Google Calendar provider import | Integration framework tests could fail at import time in a minimal environment without `requests`, even when tests only need a provider spec/mock. | `google_calendar_provider.py` imported `requests` as a hard dependency at module import time. | Made `requests` optional at import time and raise/return gracefully only when provider methods actually need network calls. | `pytest tests/test_integration_framework.py -q` collected and ran; encryption-dependent tests skip when cryptography is unavailable. |
| PR3-004 | Integration token refresh lock | Token refresh could be skipped by the lock holder itself because `_refresh_token_safely` updated status to `refreshing`, then read that same status and treated it as another in-flight refresh. | Lock acquisition was inferred from the post-update status instead of the atomic update rowcount. | Use the `UPDATE ... WHERE status = 'idle'` rowcount as the lock-acquired signal. If no row was updated, return existing token because another refresh is in progress. | `tests/test_integration_framework.py::TestIntegrationFramework::test_refresh_lock_holder_uses_rowcount_and_calls_provider` covers the rowcount lock-holder path without requiring cryptography. |

## Checks run

| Check | Result | Notes |
|---|---:|---|
| `pytest tests/test_gmail_sync_jobs.py tests/test_gmail_sync_mailbox_context.py -q` | Pass | `29 passed`. |
| `pytest tests/contract/test_gmail_contract.py::test_gmail_invalid_token_returns_401 -q` | Pass/skip | Skips cleanly when Gmail contract credentials are not configured. |
| `pytest tests/test_integration_framework.py -q` | Pass/skip | `2 passed, 3 skipped` in the minimal environment because cryptography is unavailable for encryption-dependent tests. |
| Combined targeted command | Pass/skip | `31 passed, 4 skipped`. |
| `python -m py_compile ...` | Pass | Compile check for touched modules/tests. |
| `pytest tests/ -q --ignore=tests/integration` | Warning | Blocked by this environment missing Flask and other app dependencies, causing collection errors unrelated to this PR. |

## Follow-ups

1. Re-run the full backend suite in the normal dependency-complete environment.
2. Add a CI marker expression that excludes `contract` tests from default non-integration runs unless contract credentials are present.
3. Add a dedicated integration-framework unit test around `_refresh_token_safely` rowcount-based lock acquisition once cryptography dependencies are available in CI.
