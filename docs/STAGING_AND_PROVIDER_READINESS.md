# Staging E2E Validation & Provider-Backed Readiness

Three focus areas implemented in software: end-to-end staging validation, UI visibility for automation failures, and provider-backed readiness.

## 1. End-to-end staging validation

**Goal:** Use a real test site, real API key, real CRM flow, and verify:  
widget load → lead capture → CRM record → dashboard visibility → automation log.

**Script:** `scripts/validate_staging_e2e.py`

**What it does:**
- POSTs to `{STAGING_URL}/api/webhooks/leads/capture` with a unique test email (simulates widget → webhook).
- Optionally logs in with `STAGING_LOGIN_EMAIL` / `STAGING_LOGIN_PASSWORD`, then:
  - GETs `/api/crm/leads` and asserts the new lead is present (dashboard/CRM visibility).
  - GETs `/api/automation/logs` and reports recent runs (automation log visibility).

**Usage:**
```bash
export STAGING_URL=https://api.staging.example.com
export WEBHOOK_API_KEY=fik_xxx
export STAGING_LOGIN_EMAIL=test@example.com
export STAGING_LOGIN_PASSWORD=your_password
python3 scripts/validate_staging_e2e.py
```

- `--skip-login`: only run webhook capture; skip CRM and automation log checks (no auth needed).
- `--verbose`: print response snippets.
- Widget load is not automated; run manually on a real test site or use Playwright separately. The script validates backend: lead capture → CRM → logs.

## 2. UI visibility for automation failures

**Goal:** Surface a simple “Recent automation runs” view so users are not blind when something fails.

**Implemented:**
- **Dashboard:** New “Recent automation runs” card showing the last 8 runs with:
  - ✓ success (green) / ✗ failure (red) icon
  - Rule name, message or error text, and timestamp
  - Banner when there are failed runs: “X failed runs — check details below or on Automations”
  - “View all” link to `/automations`
- **Automations page:** Existing “Recent executions” panel (with success/fail and `error_message`) is unchanged; the dashboard card gives at-a-glance visibility without opening Automations.

**Backend:** `GET /api/automation/logs` (existing) returns execution history; frontend uses `apiClient.getAutomationLogs()`.

## 3. Provider-backed readiness

**Goal:** Run the readiness flow with actual configured providers: OpenAI, Gmail/Outlook, Stripe, and Twilio (if you plan to sell SMS).

**Script:** `scripts/run_provider_readiness.py`

**What it does:**
- Loads `.env` and reports which providers are **configured** vs **missing** (env vars only):
  - **OpenAI:** `OPENAI_API_KEY`
  - **Gmail:** `GMAIL_CONTRACT_ACCESS_TOKEN` or `GMAIL_OAUTH_CLIENT_ID` + `GMAIL_OAUTH_CLIENT_SECRET` + `GMAIL_REFRESH_TOKEN` (or `GOOGLE_*` equivalents)
  - **Outlook:** `MICROSOFT_CLIENT_ID` / `OUTLOOK_CLIENT_ID` + client secret (connect in app; no contract test in repo)
  - **Stripe:** `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
  - **Twilio:** `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN`
- With `--run-contract-tests`: runs pytest contract tests for Gmail and Stripe when configured, and reports **pass** / **fail** / **skip** per provider.
- With `--summary`: also runs `scripts/automation_readiness.py --summary` for the full per-service sellability table.

**Usage:**
```bash
# Env check only
python3 scripts/run_provider_readiness.py

# Env + contract tests (Gmail, Stripe)
python3 scripts/run_provider_readiness.py --run-contract-tests

# Full automation readiness summary as well
python3 scripts/run_provider_readiness.py --run-contract-tests --summary
```

**Contract tests:**
- Gmail: `tests/contract/test_gmail_contract.py` (requires sandbox OAuth or access token).
- Stripe: `tests/contract/test_stripe_contract.py` (requires `STRIPE_SECRET_KEY`; checkout test also needs `STRIPE_TEST_PRICE_ID`).
- Outlook: no contract test in repo; configure in app and confirm via dashboard or manual checks.
- Twilio: no contract test in repo; env check only.

**Exit code:** 0 if all run contract tests pass or were skipped; 1 if any contract test failed.

## Quick reference

| Focus area              | Artifact                          | Command / location |
|-------------------------|-----------------------------------|--------------------|
| E2E staging validation  | `scripts/validate_staging_e2e.py` | Set `STAGING_URL`, `WEBHOOK_API_KEY`, then optional login env; run script |
| UI: automation failures | Dashboard + Automations           | Dashboard → “Recent automation runs” card; Automations → “Recent executions” |
| Provider-backed readiness | `scripts/run_provider_readiness.py` | `python3 scripts/run_provider_readiness.py [--run-contract-tests] [--summary]` |
