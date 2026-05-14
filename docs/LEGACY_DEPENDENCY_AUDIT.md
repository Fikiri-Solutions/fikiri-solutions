# Legacy Dependency Audit (May 2026)

This audit identifies legacy/older code dependencies that are still part of active runtime paths, so removal can be done safely.

## Executive view

- **Good news:** legacy CRM modules (`crm/minimal_service.py`, `core/minimal_crm_service.py`) are already removed and not imported.
- **Current risk:** several modules with `minimal_*` names are still wired into production code paths.
- **Recommendation:** do a **phased deprecation** (compatibility wrappers first), not hard deletes.

## Findings by area

### 1) CRM legacy status

- `crm/minimal_service.py` -> **not present**
- `core/minimal_crm_service.py` -> **not present**
- Import scan for these modules -> **no matches**
- Canonical usage of `crm/service.py` (`enhanced_crm_service`) is widespread across routes and services.

Conclusion: CRM has already consolidated to canonical service layer. No blocker from old CRM files.

### 2) Older-named modules still in live use

#### `core/minimal_config.py` (active)

Imported by many runtime modules, including:
- `app.py`
- `core/webhook_api.py`
- `core/knowledge_base_system.py`
- `core/smart_faq_system.py`
- `core/redis_sessions.py`
- `core/redis_queues.py`
- `core/multi_channel_support.py`
- `core/form_automation_system.py`
- `core/context_aware_responses.py`
- `core/document_templates_system.py`
- `core/document_analytics_system.py`
- `services/email_action_handlers.py`

Risk if deleted now: high startup/runtime breakage across backend features.

#### `core/minimal_vector_search.py` (active)

Used by live chatbot/KB APIs:
- `core/public_chatbot_api.py` (`get_vector_search`)
- `core/chatbot_smart_faq_api.py` (`MinimalVectorSearch`, `get_vector_search`)
- `core/knowledge_base_system.py` (lazy vector search fetch)
- Also imported by `app.py`

Risk if deleted now: breaks vector retrieval and chatbot/KB flows.

#### `core/minimal_ml_scoring.py` (partially active)

Used at app initialization:
- `app.py` creates `services['ml_scoring'] = MinimalMLScoring(...)`

Also referenced in:
- `routes/test.py` diagnostics endpoint usage

Risk if deleted now: app bootstrap failure unless init path is replaced.

### 3) Legacy frontend payload utility status

- `frontend/src/lib/automationGmailCrmPayload.ts` appears removed.
- Active references now point to `frontend/src/lib/automationInboundCrmPayload.ts`.

Conclusion: frontend payload migration appears complete for this path.

### 4) ~~`scripts/main_minimal.py`~~ (removed)

- It imported a non-existent `core.auth_service` and duplicated the browser OAuth flow in `core/app_oauth.py`.
- **Canonical path:** in-app Integrations + `/api/oauth/gmail/*`. See `docs/CONNECT_GMAIL_OUTLOOK.md`.
- Credential helper scripts now tell operators to reconnect via the app.

## Safe deprecation plan

### Phase 1 (no behavior change, low risk)

1. Create new canonical modules:
   - `core/config.py` (or `core/runtime_config.py`)
   - `core/ml_scoring.py`
   - `core/vector_search.py`
2. Re-export from old modules:
   - Keep `core/minimal_config.py`, `core/minimal_ml_scoring.py`, `core/minimal_vector_search.py` as compatibility wrappers.
3. Add deprecation warnings in wrappers (logged once).

### Phase 2 (migration)

1. Update imports across codebase to new canonical names.
2. Keep wrappers for one release cycle.
3. Add/expand tests for:
   - app startup
   - chatbot retrieval
   - knowledge base import/search
   - webhook + automation routes that rely on config

### Phase 3 (removal)

1. Remove wrappers only after:
   - zero remaining imports from `minimal_*` modules
   - test suite green for critical paths
2. ~~Remove/rename `scripts/main_minimal.py` after script/docs migration.~~ **Done** — script removed; use in-app Gmail connect.

## Immediate “do not delete yet” list

- `core/minimal_config.py`
- `core/minimal_vector_search.py`
- `core/minimal_ml_scoring.py`

## Immediate “safe cleanup candidate” list

- old CRM minimal modules are already absent; no action needed
- legacy docs/scripts can be migrated incrementally without runtime risk

## Reclassification matrix

| File | Real status | Action |
|---|---|---|
| `core/minimal_config.py` | active dependency | wrap + migrate imports to `core.config` |
| `core/minimal_vector_search.py` | active dependency | wrap + migrate imports to `core.vector_search` |
| `core/minimal_ml_scoring.py` | active dependency | wrap + migrate imports to `core.ml_scoring` |
| `crm/minimal_service.py` | gone | no action |
| `core/minimal_crm_service.py` | gone | no action |
| ~~`scripts/main_minimal.py`~~ | removed | was broken CLI; use `app_oauth` + Integrations |

## Deprecation policy

- Canonical modules are the only supported import surface:
  - `core.config`
  - `core.vector_search`
  - `core.ml_scoring`
- `core/minimal_config.py`, `core/minimal_vector_search.py`, and `core/minimal_ml_scoring.py` are deprecated compatibility adapters only.
- New code must not introduce `minimal_*` imports.
- Wrappers remain for one release cycle to preserve compatibility and reduce rollout risk.
- Wrapper removal is allowed only after:
  - import scan returns zero runtime references (excluding intentional archived references/tests),
  - docs are canonical,
  - CI is green across critical paths.

