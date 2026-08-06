# Windmill CE — internal execution development pilot (Fikiri)

This stack is **opt-in** and for **trusted internal Fikiri operators only**.
n8n is deferred and is not part of this pilot.

## Architecture

Trusted operator manually runs a Windmill job → pure Python normalization.
Optionally, the operator (or a Windmill script) sends a single test callback to Flask:

`POST /api/internal/automation/events`

Flask remains authoritative for authentication, authorization, tenant scope,
idempotency, correlation, and **audit**. Windmill job logs are for developer
troubleshooting only.

Flask → Windmill outbound API triggering is **out of scope** for this slice.

## Community Edition limitations

- The pilot is for **trusted internal Fikiri users only**.
- Windmill’s SOC 2 / Trust Center coverage applies to **Enterprise Edition**, not this Community Edition pilot. Do not claim CE is SOC 2 covered.
- Direct client access, managed-service use, white-labeling, and commercial redistribution require a **separate Windmill licensing review**.
- Production use for regulated or highly sensitive workflows requires a **separate security and compliance assessment**.
- Platform execution logs **do not replace** Fikiri application audit logs (`admin_audit_log` via Flask).
- Paid seats and Compute Units may apply if Fikiri later adopts Windmill Pro or Enterprise.
- This deployment does **not** provide: enterprise side-effect audit logs, SSO/SAML/SCIM, external JWT auth, autoscaling, dedicated-worker controls, critical alerts, enterprise Git promotion, enterprise object-storage / distributed cache, or a support SLA.

## Prerequisites

- Docker + Docker Compose
- Local Flask app for callback tests (`PORT=5000`)
- Migration `008_automation_event_receipts.sql` applied to the Fikiri app database
- An API key with exact scope `automation:ingress` (scopes are exact strings in a JSON list)

## Environment setup

```bash
cp .env.automation-dev.example .env.automation-dev
# Set WINDMILL_DB_PASSWORD to a local-only secret
```

Fikiri `.env.example` notes the ingress scope; do not invent a parallel shared-secret auth system.

## Start / stop automation services

```bash
docker compose -f docker-compose.automation-dev.yml --env-file .env.automation-dev up -d
docker compose -f docker-compose.automation-dev.yml --env-file .env.automation-dev ps
docker compose -f docker-compose.automation-dev.yml --env-file .env.automation-dev down
# Remove volume only when intentionally wiping Windmill local state:
# docker compose -f docker-compose.automation-dev.yml --env-file .env.automation-dev down -v
```

Pinned image: `ghcr.io/windmill-labs/windmill:1.775.2`  
Immutable digest (recorded 2026-08-02 after `docker pull`):

`ghcr.io/windmill-labs/windmill@sha256:d9f4c66790be88bf64b70f44255ca113d3b586938d96e7819ea3c5cfdc5b4fcf`

Re-check after pull: `docker image inspect ghcr.io/windmill-labs/windmill:1.775.2 --format '{{index .RepoDigests 0}}'`

## Network exposure

| Surface | Binding | Meaning |
|---------|---------|---------|
| Host UI | `127.0.0.1:8000` | Not published on LAN/public interfaces |
| Compose network | worker ↔ server | Expected internal access |
| Public deploy | none | Not this pilot |

## Create local Windmill owner

1. Open http://127.0.0.1:8000
2. Sign in with the CE bootstrap credentials from Windmill docs (`admin@windmill.dev` / `changeme` unless you changed them)
3. **Change the password immediately**
4. Create a development workspace for Fikiri internal use only

## Scoped Windmill development token + CLI

```bash
npm install -g windmill-cli
wmill workspace add fikiri-dev http://127.0.0.1:8000 --token <development-token>
cd automation/windmill
wmill sync pull   # or wmill init / sync push as appropriate
```

Do not configure MCP, GitHub deploy automation, or production sync.

## Apply Fikiri receipts migration

Postgres (production-shaped):

```bash
psql "$DATABASE_URL" -f scripts/migrations/008_automation_event_receipts.sql
```

Rollback (manual only — see below):

```bash
psql "$DATABASE_URL" -f scripts/migrations/rollback/008_automation_event_receipts.sql
```

### Migration discovery / `.down.sql` safety

Forward migrations in this repo are **manual / ops-applied SQL files**, not an auto-runner that executes every `*.sql` in `scripts/migrations/`.

CI does **not** reference `008` or any `.down.sql` file.

To prevent accidental inclusion by a naive `glob("*.sql")`, the rollback script lives under:

`scripts/migrations/rollback/008_automation_event_receipts.sql`

It is a **manual rollback reference**, not supported automated rollback tooling. Do not place forward DDL in `rollback/`.

## PostgreSQL concurrency validation

SQLite unit tests prove ownership logic but are **not** production concurrency verification.

Genuine concurrent claim test (requires a disposable Postgres):

```bash
export FIKIRI_PG_CONCURRENCY_TEST_URL='postgresql://USER:PASS@127.0.0.1:PORT/DB'
pytest tests/test_automation_event_receipts_pg_concurrency.py -v
```

This test asserts exactly one of two concurrent `INSERT`s owns `(source, event_id)`.

## Create Fikiri API key for callbacks

Generate a key whose scopes JSON list includes exactly `automation:ingress` (no admin role). Use that key only on localhost.

## Run the normalization job (manual)

- Import or sync `automation/windmill/f/normalize_leads/normalize_leads.py`
- Ensure `FIKIRI_ROOT` or `PYTHONPATH` points at the Fikiri repo when the worker executes
- Run with a small sample lead list in the Windmill UI

Pure logic tests (no Windmill required):

```bash
pytest tests/test_automation_normalize_leads.py -v
```

## Optional Flask callback smoke test

```bash
curl -sS -X POST http://127.0.0.1:5000/api/internal/automation/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_YOUR_DEV_KEY" \
  --data-binary @automation/contracts/automation_event_v1.example.json
```

Repeat with the same `event_id` to observe idempotent duplicate behavior.

## Flask → Windmill trigger (opt-in)

Disabled unless `FIKIRI_WINDMILL_TRIGGER_ENABLED=1`. Requires `WINDMILL_DEV_TOKEN`,
`WINDMILL_BASE_URL=http://127.0.0.1:8000`, and workspace `fikiri-dev`.

```bash
curl -sS -X POST http://127.0.0.1:5000/api/internal/automation/jobs/normalize-leads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_YOUR_DEV_KEY" \
  -d '{
    "trigger_id": "trig_dev_001",
    "correlation_id": "corr_dev_001",
    "records": [
      {"email": "Ada@Example.COM", "name": " Ada Lovelace ", "company": "Analytical"},
      {"email": "ada@example.com", "name": "Ada", "company": "Analytical Engines"}
    ]
  }'
```

Async by default (HTTP 202 + `job_id`). Set `"wait": true` only for local debugging.
Reuse the same `trigger_id` for idempotency (payload conflicts → 409).

## Ingress tests

```bash
pytest tests/test_automation_event_ingress.py tests/test_automation_normalize_leads.py -v
```

## Rotating development secrets

1. Rotate `WINDMILL_DB_PASSWORD` (recreate volume if needed)
2. Change Windmill owner password (`POST /api/users/setpassword`) and revoke old workspace tokens
3. Revoke/reissue Fikiri `automation:ingress` API keys
4. Never commit tokens, passwords, or API keys

Local secret files (gitignored): `.env.automation-dev`, `.windmill-dev-session`, `.windmill-dev-cli-token`

## Script install notes (operational)

- `wmill workspace add fikiri-dev http://127.0.0.1:8000 --token <token>`
- Prefer `wmill sync pull --yes` (interactive prompts can crash)
- Worker scripts must be self-contained (no `from __future__` if Windmill prepends wrappers; no Fikiri `PYTHONPATH` required)
- Source-of-truth for pytest remains `core/automation_normalize_leads.py`

## Licensing warning

This pilot is **Fikiri internal use only**. Do not expose the Windmill editor, workflows, apps, or workspaces to clients. Managed-service, white-label, resale, or embedded client access requires a separate Windmill commercial licensing review.
