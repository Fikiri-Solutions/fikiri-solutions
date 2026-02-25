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
- **Signup endpoint bug (pre-existing)**: The `/api/auth/signup` route uses a stale `jwt_auth_manager` import (always `None`). Login (`/api/auth/login`) works correctly because `user_auth_manager.authenticate_user()` calls `get_jwt_manager()` internally. To create test users, use the login endpoint after the user is created (signup creates the user but fails on token generation).

### Lint / Test / Build commands

See `README.md` for canonical commands. Quick reference:
- **Backend lint**: `flake8 app.py --max-line-length=120` / `black --check .` / `isort --check .`
- **Backend tests**: `pytest tests/ -v --ignore=tests/integration` (unit tests; integration tests require a running backend)
- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend type-check**: `cd frontend && npx tsc --noEmit` (3 pre-existing errors in `Dashboard.tsx`)
- **Frontend tests**: `cd frontend && npx vitest run` (some pre-existing Toast test failures)
- **Frontend build**: `cd frontend && npm run build`
