# Cursor + Codex — Shared Coordination

**Purpose:** Both AI tools work on this codebase. Follow this doc so edits stay consistent and conflict-free.

## 0. Work Assignment (Interchangeable Roles)

**Note:** Roles are interchangeable - either Codex or Cursor can work on backend or frontend as needed.

**Backend Areas:**
- `routes/`, `core/`, `services/`, `crm/`, `integrations/`, `email_automation/`, `analytics/`
- API endpoints, database logic, business logic
- Backend tests

**Frontend Areas:**
- `frontend/src/` (all React components, pages, hooks, services)
- Frontend API client (`frontend/src/services/apiClient.ts`)
- UI/UX improvements, component styling
- Frontend tests

**Coordination Required:**
- Check `git status` and recent changes before editing
- Coordinate on API contract changes (request/response shapes)
- Coordinate on new endpoints or route changes
- Coordinate on shared configuration files

---

## 1. Source of Truth (Read First)

| File | Purpose |
|------|---------|
| `.cursorrules` | Full rulepack — architecture, AI pipelines, security, performance |
| `.cursor/rules` | Cursor-specific operational rules |
| `SIMPLICITY_RULE.md` | Code simplicity guidelines |

**Both tools must follow these rules.** No exceptions.

---

## 2. Before Every Edit

1. **Check recent changes** — `git status` and `git diff` to avoid overwriting in-progress work.
2. **Inspect the file** — Read the existing file before editing; follow its patterns.
3. **Minimal scope** — Change only what's needed. Avoid large refactors.

---

## 3. Conflict Avoidance

| Practice | Do | Don't |
|----------|-----|-------|
| **Scope** | Edit 1–3 files per task | Refactor whole modules |
| **Files** | Check git status before editing to see recent changes | Touch files that were recently modified by the other tool |
| **Patterns** | Match existing style | Introduce new patterns |
| **APIs** | Preserve contracts | Change request/response shapes without coordination |
| **Coordination** | Check git status before editing shared files | Make breaking API changes without notice |

---

## 4. Domain Boundaries (Don't Cross Unnecessarily)

```
core/           → shared utilities (ai, logging, config)
services/       → business logic
integrations/   → external connectors (Gmail, Outlook)
crm/            → CRM models, crm/service.py canonical
email_automation/ → email pipeline
frontend/       → React app; all API calls via apiClient
```

- `services/` calls `core/` and `integrations/`, not the reverse.
- Frontend never calls external APIs directly.

---

## 5. Shared Conventions

- **Naming:** `create_contact`, `validate_email` — verbs for functions; nouns for classes.
- **Error handling:** Simple try/except; log clearly; fail gracefully.
- **Secrets:** Env vars only; never hardcode.
- **API responses:** `{ success, message?, data? }` always.

---

## 6. Quick Reference

- **AI calls:** `core/ai/llm_router.py` → `llm_client.py` → `validators.py`
- **CRM mutations:** `crm/service.py` only
- **Auth:** JWT via `core/jwt_auth.py`; `AuthContext` on frontend
- **Onboarding:** Steps 1→2→3→4; no skipping; validate on backend

---

---

## 7. Work Assignment (Roles are Interchangeable)

**Either Codex or Cursor can work on:**

**Backend:**
- Python/Flask backend code
- Routes, services, core utilities
- Database operations
- API endpoints
- Backend testing

**Frontend:**
- React/TypeScript frontend code
- UI components and pages
- Frontend API client
- User interface and UX
- Frontend testing

**Always coordinate when:**
- API contract changes (request/response formats)
- New endpoints or route modifications
- Shared configuration updates
- Breaking changes that affect both frontend and backend
- Editing files that were recently modified (check `git status` first)

*Last updated: Feb 2026*
