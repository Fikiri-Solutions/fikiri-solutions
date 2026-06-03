# PR 1 Bugfix and Regression Report

**Report date:** 2026-06-03  
**Fix commit:** `6deedab` (`2026-06-03 17:26:00 +0000`)  
**PR title:** Harden contact intake, security headers & rate limiting, CRM normalization, UI tweaks, and tests  
**Scope:** Public contact intake, security middleware/rate limiting, CRM pipeline/normalization, CRM automation field updates, Gmail sync route behavior, and frontend wiring/UX adjustments.

This report is the formal audit trail for the first remediation PR. It records each issue class, the observed problem, root cause, fix, regression coverage, and when it was fixed.

## Regression check summary

| Check | Result | Notes |
|---|---:|---|
| `pytest tests/test_crm_service.py tests/test_automation_engine.py tests/test_business_routes.py tests/test_crm_events.py tests/test_crm_pipeline_api.py -q` | Pass | `120 passed, 1 warning, 2 subtests passed`. Covers the CRM and route changes added in the final PR 1 slice. |
| `python -m py_compile crm/service.py services/automation_actions/crm_action.py routes/business.py tests/test_crm_service.py tests/test_automation_engine.py tests/test_business_routes.py` | Pass | Syntax/import-level compile check for touched CRM route/service/action/test files. |
| `pytest tests/ -q --ignore=tests/integration` | Warning | Full non-integration backend suite was run; it reported `4 failed, 1311 passed, 31 skipped, 66 warnings, 16 subtests passed`. The failures were in pre-existing/unrelated Gmail contract and integration-framework tests, not in the files changed for PR 1. |

## Bug ledger

| ID | Area | Bug / risk | Root cause | Fix | Regression evidence | Fixed when |
|---|---|---|---|---|---|---|
| PR1-001 | Licensing / repository governance | Repo had no explicit proprietary license, leaving ownership/usage terms unclear. | No `LICENSE` file was present before the audit remediation. | Added a proprietary, all-rights-reserved `LICENSE` for Fikiri Solutions. | File presence and PR diff. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-002 | Public contact intake | Contact form was vulnerable to bot submissions because there was no silent honeypot suppression path. | Public contact endpoint trusted normal visible form fields only. | Added hidden `leave_blank` honeypot handling in frontend/API and silent-success suppression server-side. | `tests/test_contact_api.py` honeypot regression tests. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-003 | Public contact emails / XSS risk | User-supplied contact fields could be inserted into HTML email bodies without sufficient escaping. | Email body composition did not consistently HTML-escape all user-controlled fields. | Escaped contact fields with `html.escape`, preserved message line breaks safely, and added truncation/content limits. | `tests/test_contact_api.py` HTML escaping assertions. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-004 | Contact persistence | Contact submissions were not consistently persisted as best-effort records. | Send path and persistence path were loosely coupled. | Kept submission persistence best-effort while preserving email send behavior. | Contact API tests for success/failure paths. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-005 | Security headers | API responses could miss baseline security headers such as CSP and related browser hardening headers. | Security middleware primarily focused on selected response types/paths instead of applying a consistent baseline. | Applied CSP/security headers consistently to responses and expanded `SECURITY_CONFIG`. | `tests/test_security.py` header assertions. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-006 | Rate limiting response consistency | Rate-limit decorators did not always return standardized JSON/error tuple responses. | Decorator utilities had inconsistent return handling. | Added/standardized `rate_limit_by_user` and `rate_limit_by_ip` helpers returning consistent API-style responses. | `tests/test_security.py` decorator behavior checks. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-007 | Frontend contact wiring | Frontend contact form did not send the honeypot value expected by backend suppression. | Client API type/payload did not include `leave_blank`. | Added the hidden field in `Contact.tsx` and allowed/sent it through `apiClient.submitContact`. | Contact API regression tests plus frontend payload wiring in PR diff. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-008 | Account/security UX | 2FA UI implied availability even though the feature was not available. | Frontend toggle state did not reflect backend/feature readiness. | Disabled unavailable 2FA control and adjusted save behavior/copy. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-009 | Password reset contract | Reset flow could miss tokens in URL hash and used a payload key that did not match the expected backend contract. | Frontend reset parser/payload naming drifted from backend expectations. | Added token-from-hash support and changed reset payload to `new_password`. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-010 | CRM pipeline route/service mismatch | `/crm/pipeline` route called `get_pipeline`, but CRM service only exposed `get_lead_pipeline`. | Route/service API naming drift. | Added `EnhancedCRMService.get_pipeline()` alias and made the route unwrap service-style success payloads consistently. | `tests/test_crm_service.py::test_get_pipeline_alias_delegates_to_lead_pipeline` and `tests/test_business_routes.py::test_get_pipeline_unwraps_service_result`. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-011 | CRM email duplicates | CRM create/import paths could treat whitespace/case variants of the same email as different leads. | Email normalization was not applied consistently before duplicate checks/inserts/import updates. | Added `normalize_lead_email`, trimmed names, and used case-insensitive duplicate lookup in create/import paths. | `tests/test_crm_service.py::test_create_lead_normalizes_email_before_lookup_and_insert`. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-012 | CRM automation update safety | Generic `update_crm_field` automation could update arbitrary field names through dynamic SQL formatting. | Automation accepted untrusted `field_name` without an allowlist and constructed the SQL field expression directly. | Added `CRM_AUTOMATION_UPDATE_FIELDS` allowlist and delegated valid writes through `enhanced_crm_service.update_lead`. | `tests/test_automation_engine.py::test_update_crm_field_generic_uses_service_allowlist` and `tests/test_automation_engine.py::test_update_crm_field_rejects_disallowed_field_name`. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-013 | Gmail sync request latency / duplicate work | Successful queued Gmail sync requests could continue into synchronous CRM lead sync work in the same API request. | Route did not return immediately after queueing the background job. | Added early success return when `sync_job_queued` is true; kept direct CRM sync only as fallback when queueing fails. | `tests/test_business_routes.py` asserts `sync_gmail_leads` is not called after queued sync. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-014 | Billing/legal link duplication | Billing page repeated legal links already provided in the global footer. | Page-level legal links duplicated footer navigation. | Removed redundant billing-page terms/privacy links. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-015 | Landing footer year drift | Landing page footer had a hardcoded copyright year. | Static year was embedded in the component. | Replaced hardcoded year with dynamic current-year rendering. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-016 | Public-page business info | About page did not expose the business email as requested by audit feedback. | Business information block lacked the contact email. | Added company email information to the About page. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |
| PR1-017 | Pricing CTA navigation | Pricing page consultation CTA routed to an internal/support destination instead of the public contact path. | CTA path did not match the expected user journey. | Updated Pricing CTA navigation to `/contact`. | Frontend diff review. | `6deedab`, 2026-06-03 17:26 UTC |

## Contract-vs-implementation checklist for queue/automation changes

| Claim | Expected behavior | Evidence | Status |
|---|---|---|---:|
| Queued Gmail sync should not block on CRM lead sync in the request path. | Once the background sync job is queued, API returns queued success and does not call synchronous CRM sync. | `routes/business.py` early return and `tests/test_business_routes.py` `sync_gmail_leads.assert_not_called()`. | Pass |
| CRM pipeline endpoint should return usable pipeline data. | Route should call a real service method and return the service `data` payload rather than nesting the service envelope. | `EnhancedCRMService.get_pipeline()` alias and route unwrapping test. | Pass |
| CRM automation field updates should be constrained. | Automation can update only approved fields and must not format arbitrary SQL field names. | Allowlist plus service-level `update_lead` delegation; allowed/disallowed tests. | Pass |
| CRM lead identity should be normalized. | Create/import paths lower/trim emails before duplicate checks and persistence. | `normalize_lead_email` and normalization regression test. | Pass |

## Known follow-ups outside PR 1

These were observed while running checks but were not caused by PR 1 and remain outside this remediation scope:

1. `tests/contract/test_gmail_contract.py::test_gmail_invalid_token_returns_401` attempted an external Gmail API path with an invalid token and failed in the contract suite path.
2. `tests/test_integration_framework.py::TestIntegrationFramework::test_2_concurrent_refresh_single_call` remains failing.
3. `tests/test_integration_framework.py::TestIntegrationFramework::test_3_disconnect_during_refresh` remains failing.
4. `tests/test_integration_framework.py::TestIntegrationFramework::test_4_expires_at_normalization` remains failing.

## Documentation policy going forward

For future remediation PRs, include this same ledger structure before closing the PR:

1. Bug/risk.
2. Root cause.
3. Fix summary.
4. Files changed.
5. Regression test or verification command.
6. Fixed commit/date.
7. Known remaining failures, if any, clearly marked as unrelated/pre-existing or newly introduced.
