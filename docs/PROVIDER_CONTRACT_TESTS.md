# Provider Contract Tests

Run provider contract checks (Gmail + Stripe) with real sandbox credentials.

## Quick start

```bash
scripts/run-provider-contract-checks.sh
```

This writes JSON results to:

- `reports/provider_contract.json` (default)
- or `PROVIDER_CONTRACT_RESULTS=/path.json`

## Required environment variables

### Gmail
- `GMAIL_OAUTH_CLIENT_ID` or `GOOGLE_CLIENT_ID`
- `GMAIL_OAUTH_CLIENT_SECRET` or `GOOGLE_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN` or `GOOGLE_REFRESH_TOKEN`

To obtain a refresh token: run `python scripts/obtain_gmail_refresh_token.py` (stop the main app first if it uses port 5000). Sign in in the browser, then add the printed line to `.env`.

Alternative:
- `GMAIL_CONTRACT_ACCESS_TOKEN` (short-lived access token)

Optional:
- `GMAIL_CONTRACT_QUERY` (filter for list messages)
- `GMAIL_CONTRACT_MESSAGE_ID` (force a specific message)

### Stripe
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

Optional:
- `STRIPE_TEST_PRICE_ID` (needed for checkout session test)

## How readiness uses results

`scripts/automation_readiness.py` reads `reports/provider_contract.json` and sets:

- `details.providers.gmail`
- `details.providers.stripe`

If a provider contract fails, services that depend on that provider remain **BETA** even if unit tests pass.
