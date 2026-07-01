# Security & Environment Setup

How to configure Fikiri without committing or leaking secrets.

**Do not** paste your local `.env` into Cursor, Slack, email, or issue comments. Use this doc and placeholder templates instead.

---

## Immediate action after exposure

If credentials may have appeared in chat, logs, or git history:

1. **Rotate/revoke** each affected provider (new keys invalidate old ones).
2. **Update hosted env** (Render dashboard, Vercel env, Upstash, Supabase, Stripe, OAuth consoles).
3. **Update local `.env` only on your machine** — never commit it.
4. Re-run the [secret scan](#local-secret-scan) below.

### Credential groups to rotate

| Group | Typical env vars | Where to rotate |
|-------|------------------|-----------------|
| OpenAI | `OPENAI_API_KEY` | OpenAI platform → API keys |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, webhook endpoints | Stripe Dashboard |
| Postgres / Supabase | `DATABASE_URL`, pooler password | Supabase → Database → reset password |
| Redis / Upstash | `REDIS_URL` | Upstash console |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google Cloud Console |
| Microsoft OAuth | `MICROSOFT_CLIENT_*` | Azure App Registration |
| Yahoo OAuth | `YAHOO_CLIENT_*` | Yahoo Developer Network |
| SMTP | `SMTP_PASSWORD` | Email provider app password |
| Slack | `SLACK_WEBHOOK_URL` | Slack app → regenerate webhook |
| Pinecone | `PINECONE_API_KEY` | Pinecone console |
| Twilio | `TWILIO_AUTH_TOKEN`, `TWILIO_ACCOUNT_SID` | Twilio console |
| Notion | `NOTION_API_KEY` | Notion integrations |
| App crypto | `SECRET_KEY`, `JWT_SECRET_KEY`, `FERNET_KEY` | Generate locally (see below) |
| Supabase browser | `VITE_SUPABASE_ANON_KEY` | Supabase → API → anon key (rotate if repo/context is public) |

Generate new app secrets locally (prints to your terminal only):

```bash
python3 scripts/generate_new_secrets.py
```

---

## Local setup (safe)

```bash
# Backend — pick one:
cp env.template .env          # full reference
cp .env.example .env          # curated starter

# Frontend
cp frontend/env.example frontend/.env.local
```

Edit `.env` and `frontend/.env.local` with **real** values locally. Both paths are gitignored.

For local SQLite dev, **leave `DATABASE_URL` unset or commented** in `.env` (see `AGENTS.md`).

---

## Production env placement

| Surface | Set vars in |
|---------|-------------|
| Flask API (Render) | Render → `fikiri-backend` / `fikiri-worker` → Environment |
| React (Vercel) | Vercel → Project → Settings → Environment Variables |
| Postgres | Supabase connection string → Render `DATABASE_URL` only |
| Redis | Upstash → `REDIS_URL` on Render |

`render.yaml` uses `sync: false` for secrets — values live in the dashboard, not in git.

---

## Files that must never contain live secrets

Tracked templates (placeholders only):

- `env.template`
- `.env.example`
- `frontend/env.example`

Gitignored (local only):

- `.env`, `.env.local`, `.env.production`, `.env.*` (except `.env.example`)
- `frontend/.env`, `frontend/.env.local`
- `credentials.json`, `auth/credentials.json`, `*.pem`, `*.key`
- `security-reports/gitleaks.json`

CI workflows generate **ephemeral** `JWT_SECRET_KEY` / `FERNET_KEY` per run (`openssl rand`, `os.urandom`) — no static secrets in workflow YAML.

---

## Local secret scan

Before pushing or after rotating:

```bash
git status
git diff --cached
git diff

# Working tree (should report no findings when clean):
gitleaks detect --source . --no-git --verbose

# Full history (may flag old commits — rotate keys even if current tree is clean):
gitleaks detect --source . --verbose
```

Optional: `trufflehog filesystem . --no-update` if installed.

Report output paths and rule IDs only — **do not** paste detected secret values into tickets or chat.

---

## Git history note

Gitleaks may still report secrets in **old commits** (removed shell scripts, legacy workflow echo lines). Rotating credentials limits blast radius. Scrubbing history (`git filter-repo`, BFG) is optional and requires force-push coordination — not required if all keys are rotated.

---

## Cursor / agent safety

When asking an agent for help:

```text
Security cleanup task. Do not print, copy, or expose secret values.
Use env.template / .env.example placeholders only. Do not read .env.
```

Never attach or `@`-reference your `.env` file in Cursor.

---

## Related docs

- [ENVIRONMENT_CONFIG.md](./ENVIRONMENT_CONFIG.md) — variable reference by feature
- [FIKIRI_SITE_BOT_PHASE_5_SPEC.md](./FIKIRI_SITE_BOT_PHASE_5_SPEC.md) — site bot production flags (Phase 5)
