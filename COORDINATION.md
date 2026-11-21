# Cursor + Codex

Cursor loads `.cursorrules` and `AGENTS.md` on its own. Codex does not. Codex reads the files below only when the session is told to.

## Read first

| File | Role |
|---|---|
| `.cursorrules` | Always-on core: boundaries, security, production Postgres, the rules that stay true before a subsystem file is open |
| `AGENTS.md` | Ports, WSGI, Fernet, SMTP, local SQLite, the unit-gate command |
| `docs/REGRESSION_TESTING.md` | Which tests to run for a quick fix, a feature, a critical change, and a release |
| `.cursor/rules/<area>.mdc` | The subsystem file named in `.cursorrules` for the area being edited |

`SIMPLICITY_RULE.md` points at `.cursorrules`. It is not a second style guide.

## Subsystem files

Read the one that matches the edit. Do not read the whole directory.

| File | Read it before editing |
|---|---|
| `auth-onboarding.mdc` | JWT, login, signup, whoami, onboarding steps |
| `api-and-data.mdc` | Route handlers and Redis keys |
| `frontend-client.mdc` | `frontend/src` React code |
| `database.mdc` | Schema, Postgres, migrations |
| `ai-pipeline.mdc` | `core/ai` model calls |
| `email.mdc` | Mail sync, classification, replies |
| `crm.mdc` | Contact create and update |
| `logging.mdc` | New log lines |
| `deploy-config.mdc` | `render.yaml`, `wsgi.py` |
| `admin.mdc` | Admin routes and admin UI |
| `quality-gate.mdc` | Queues and workflow state |
| `task-routing.mdc` | How large the task is |
| `regression-testing.mdc` | Short copy of the testing policy |

Cursor attaches a file that has `globs` when a matching file is open. That is not a substitute for reading it first. Codex has no glob attach. Name the file in the prompt.

## Before an edit

1. `git status` and `git diff`, so one tool does not overwrite the other.
2. Read the existing file and follow it.
3. Stay inside the task. API shape changes need both tools aware.

Either tool may edit backend or frontend. Coordinate on a new endpoint, a shared config file, or a contract change.

## User rules Cursor may also load

These live outside the repo and apply to other workspaces too: `cost-control`, `fikiri-git-main`, `fikiri-client-ship`, `fikiri-engineering`, and `higgsfield-credit-efficiency`, plus `/Users/mac/AGENTS.md`. This repo does not switch them off.
