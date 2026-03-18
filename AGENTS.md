# AGENTS.md

## Cursor Cloud specific instructions

### Services overview

| Service | Port | Start command |
|---|---|---|
| Flask backend (API) | 5000 | `cd /workspace && PORT=5000 FLASK_ENV=development script -qefc "python3 app.py" /dev/null &` |
| Vite frontend (React) | 5174 | `cd /workspace/frontend && npx vite --host 0.0.0.0 --port 5174 &` |

### Gotchas

- **Backend port must be 5000**: The frontend's Vite proxy and `config.ts` hardcode the backend at `http://localhost:5000`. Always start the backend with `PORT=5000`.
- **SocketIO + non-TTY**: Flask-SocketIO 5.6+ refuses to start with Werkzeug in non-TTY environments. Wrap the backend start with `script -qefc "..." /dev/null` to provide a pseudo-TTY.
- **Fernet key**: The `.env` must contain a valid Fernet key (32 url-safe base64-encoded bytes). Generate with: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Without it, backend imports fail at `integrations/gmail/gmail_client.py`.
- **`python-dotenv`**: Not in `requirements.txt` but needed for `.env` loading. The update script installs it alongside `requirements.txt`.
- **Redis is optional**: The backend gracefully degrades to in-memory/SQLite fallbacks if Redis is unavailable. No need to install Redis for local dev.
- **DATABASE_URL**: Must be commented out in `.env` for local dev; otherwise the backend attempts a PostgreSQL connection. SQLite (`data/fikiri.db`) is used automatically.
- **Signup**: `/api/auth/signup` uses `get_jwt_manager().generate_tokens()` and returns access/refresh tokens. Confirm with `pytest tests/test_auth_routes.py -v -k signup` (or full auth test run). If token generation ever fails, create the user via signup then use `/api/auth/login` to get tokens.

### E2E tests (Playwright)

- **Run the backend with `FLASK_ENV=development`** (or `FIKIRI_TEST_MODE=1`) when running E2E locally so signup isn’t rate limited (signup is 3/hour per IP otherwise; setup creates users every run).
- If you can’t change the backend env, the 429 fallback in auth setup (log in as default test user and save that state) still avoids failing the run when the limit is hit.
- Auth env: set `TEST_USER_EMAIL` and `TEST_USER_PASSWORD` to a valid user, or unset them to use defaults (`test@example.com` / `TestPassword123!`). See [docs/E2E_TEST_PLAN.md](docs/E2E_TEST_PLAN.md).

### Lint / Test / Build commands

See `README.md` for canonical commands. Quick reference:
- **Backend lint**: `flake8 app.py --max-line-length=120` / `black --check .` / `isort --check .`
- **Backend tests**: `pytest tests/ -v --ignore=tests/integration` (unit tests; integration tests require a running backend)
- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend type-check**: `cd frontend && npx tsc --noEmit` (3 pre-existing errors in `Dashboard.tsx`)
- **Frontend tests**: `cd frontend && npx vitest run` (some pre-existing Toast test failures)
- **Frontend build**: `cd frontend && npm run build`

### Admin routes (when building)

- **No separate admin portal.** Keep one app; add an `/admin` section with role-based access.
- **RBAC + server-side enforcement:** Use capability-based permissions (e.g. `budget.approve`, `users.manage_roles`); backend decorators/middleware must enforce every admin action. Never rely on frontend hiding alone.
- **Audit log** all admin actions (actor, action, target, before/after, timestamp, IP).
- **First lean slice:** One admin endpoint for approve/revoke budget soft-stop override + one `/admin/budgets` UI for pending approvals.
- Full strategy: [docs/ADMIN_ROUTES_STRATEGY.md](docs/ADMIN_ROUTES_STRATEGY.md).

### Quality gate (automation, queues, workflows)

Before marking queue/workflow/automation features "done", follow the protocol in [docs/CURSOR_QUALITY_GATE.md](docs/CURSOR_QUALITY_GATE.md):

- Build a **contract table** (claim → expected behavior → code location → pass/fail).
- Model **state transitions** explicitly (event → from_state → to_state → side effects); reject labels like `retrying` with no re-enqueue or scheduler.
- Run a **failure-first review**: partial failures, retries exhausted, idempotency, auth scoping, HTTP contract.
- Require **branch-complete tests** (success + at least one failure/retry/idempotency branch per critical path).
- Report findings by **severity** (critical / high / medium / low).

Prompt to use: *"Before writing code, create a contract-vs-implementation checklist for this feature. Then implement with explicit state-transition guarantees. After coding, run a failure-first review: partial failure handling, retries, idempotency, auth scoping, and HTTP contract consistency. Do not report success until each claim has code evidence and test coverage for success + failure branches."*
