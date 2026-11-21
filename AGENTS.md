# AGENTS.md

Operational facts for this repo. Boundaries and safeguards are in `.cursorrules`. Test tiers are in `docs/REGRESSION_TESTING.md`.

## Services

| Service | Port | Start |
|---|---|---|
| Flask API | 5000 | `PORT=5000 FLASK_ENV=development python3 app.py`. A non-TTY needs `script -qefc "python3 app.py" /dev/null` so Flask-SocketIO will start. |
| Vite | 5174 | `cd frontend && npx vite --host 0.0.0.0 --port 5174` |

The frontend proxies `http://localhost:5000`.

## Runtime

- Gunicorn uses `geventwebsocket.gunicorn.workers.GeventWebSocketWorker` and `SOCKETIO_ASYNC_MODE=gevent`. The entry is `wsgi:wsgi_app`. `wsgi.py` patches gevent before importing the app. `app:wsgi_app` or an `eventlet` worker means the Render start command is overriding `render.yaml`.
- `.env` needs a Fernet key or `integrations/gmail/gmail_client.py` fails on import. Generate one with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. `python-dotenv` is installed with requirements; it is not listed in `requirements.txt`.
- Redis is optional. Comment out `DATABASE_URL` locally so SQLite (`data/fikiri.db`) is used.
- Signup returns tokens from `get_jwt_manager().generate_tokens()`.
- Transactional mail is stored in `email_jobs` and sends that new job only. Delivery needs `SMTP_USERNAME` and `SMTP_PASSWORD` (`SMTP_SERVER` aliases `SMTP_HOST`). Gmail needs an app password. `example.com`, `example.net`, `example.org`, `.test`, and `.invalid` are not sent through SMTP. Pending rows stay until they are sent or marked failed.
- Compare SQLite datetimes with `datetime(column)`. See `docs/SQLITE_DATETIME_COMPARISONS.md`.
- `FIKIRI_EMAIL_PIPELINE_AI_GATE=1` applies AI tier caps on `email_automation.pipeline.orchestrate_incoming`. Unset keeps the old path. Accounting errors fail open.
- E2E signup is rate limited to 3/hour per IP unless `FLASK_ENV=development` or `FIKIRI_TEST_MODE=1`. Default user: `test@example.com` / `TestPassword123!`. See `docs/E2E_TEST_PLAN.md`.

## Checks

Policy: `docs/REGRESSION_TESTING.md`.

- Unit gate, for a critical change or a release: `pytest tests/ -m "not contract and not integration" -q` and `cd frontend && npx vitest run`
- Lint: `flake8 app.py --max-line-length=120`, `black --check .`, `isort --check .`, `cd frontend && npx eslint .`
- Types: `cd frontend && npx tsc --noEmit` (known existing errors in `Dashboard.tsx`)
- Build: `cd frontend && npm run build`
- Known existing Vitest failures in Toast tests

Admin edits: `.cursor/rules/admin.mdc`. Queue or workflow edits: `.cursor/rules/quality-gate.mdc`.

@AGENTS.wmill.md
