# Admin Routes Strategy — Lean, In-App, Security-Gated

Use this doc when building admin functionality. **Do not build a separate admin portal**
at the current stage.

**Binding security standard:** [ADMIN_PORTAL_SECURITY.md](./ADMIN_PORTAL_SECURITY.md)

The admin portal is a **high-risk privileged system**. Security is Phase **1.5** and
**gates** all destructive / override capabilities. Do not treat `/admin` as “just another dashboard.”

---

## Principles

- **One app.** Admin lives inside the existing app as an `/admin` section.
- **Capability-based auth (deny-by-default).** Server-side checks on every admin endpoint.
  Frontend hiding is never authorization.
- **Platform operator ≠ tenant org admin.** `ADMIN_USER_IDS` / platform capabilities are
  distinct from customer `role=admin`.
- **Audit logs** for successful **and** denied admin actions (no secrets).
- **Step-up + MFA** for impersonation, billing, suspend, OAuth disconnect, role changes,
  exports, and destructive actions — see security standard §4.

---

## Roles (two layers)

### Platform operators (Fikiri staff)

| Capability | Scope |
|------------|--------|
| `platform.tenants.read` | Directory + infra summary |
| `platform.tenants.impersonate` | View-as-user (step-up required) |
| `platform.audit.read` | Audit log |
| `platform.ops.read` | Read-only ops diagnostics |
| `platform.ops.retry_sync` | Retry **failed** Gmail sync for one tenant/job (step-up; not `ADMIN_DESTRUCTIVE_ENABLED`) |
| `platform.ops.write` | **Blocked until** explicit destructive enablement after gate review |
| `platform.emergency` | Lockdown / kill-switch related actions |

### Tenant org roles (customers)

| Role | Scope |
|------|--------|
| **owner** | Billing, team/roles, plan overrides within **their** tenant |
| **admin** | Operational controls within tenant. No ownership transfer. |
| **member** | Normal product use |
| **support** (optional) | Read-only diagnostics + limited assist |

---

## Roadmap (security-first)

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **1** | `/admin` shell, tenant directory, infra summary, audit read, impersonation scaffolding | Done (foundation) |
| **1.5** | MFA/step-up, session controls, CSRF stance, rate limits, lockdown, denied audit, priv-esc tests | **Required before Phase 2** |
| **2** | Ops: job cancel/retry, suspend, OAuth disconnect | Phase 1.5 complete |
| **3** | Billing overrides / AI budget approvals UI | Phase 1.5 + billing step-up |
| **4** | Deep infra views | Rate limits + read capabilities |
| **5** | Continuous assurance (SAST, deps, secret scan, alerts) | CI green |

**Hard rule:** No `platform.ops.write`, billing override, account suspension, OAuth force-disconnect,
role mutation, or bulk export until [ADMIN_PORTAL_SECURITY.md](./ADMIN_PORTAL_SECURITY.md) §8 is green
**and** the failed-sync retry pattern has been exercised in staging under multi-worker + Redis + MFA.

### Sync retry reference pattern (`platform.ops.retry_sync`)

- Step-up is **required but not consumed** — multiple retries allowed within TTL; each audited.
- Idempotency keys are bound to operator + tenant + job + action + payload hash (`IDEMPOTENCY_CONFLICT` on reuse with different dimensions).
- Claim uses conditional `UPDATE ... WHERE status IN ('failed','retrying')` with exactly-one-row verification.
- Server-side eligibility (OAuth present, tenant active, Gmail job, not permanently failed, not superseded by a newer completed sync).
- Replacement job uses a stable id for queue dedup; enqueue ambiguity after DB insert does **not** roll the original claim back to `failed`.

---

## What Phase 1 already provides

- Capability decorator: `require_platform_capability`
- APIs under `/api/admin/platform/*`
- Impersonation JWT with immutable `actor_user_id`
- Basic audit table + UI
- Frontend `/admin` + impersonation banner

---

## Phase 1.5 focus (current)

See security standard §6–§8. Implementation modules:

- `core/admin_security.py` — step-up, lockdown, sensitive-action registry
- Hardened `core/admin_audit.py` — outcome, capability, correlation_id
- `tests/test_admin_platform_security.py` — acceptance tests

---

## When to Split Into a Separate Admin Portal

Only consider a **separate** admin app when you need:

- SSO/SAML for internal staff
- Stricter network isolation / compliance
- Separate deployment or security boundaries
- Large internal ops workflows that don't fit the main app

Until then, a separate portal is extra overhead with little ROI — **provided** Phase 1.5
controls are enforced in-app.

---

## Implementation Checklist

### Foundation (Phase 1)

- [x] Platform capability strings + `require_platform_capability`
- [x] `/admin` routes with frontend guard + API enforcement
- [x] Audit logging (actor, action, target, timestamp, IP)
- [x] Impersonation scaffolding + banner

### Security gate (Phase 1.5) — blocking

- [ ] Step-up + MFA for §4 sensitive actions
- [ ] Nested impersonation blocked; kill switch; short TTL; no refresh
- [ ] Admin lockdown + impersonation shutdown
- [ ] Rate limits (impersonate, search, step-up)
- [ ] Denied-action audit + correlation id
- [ ] Privilege-escalation / tenant-boundary acceptance tests green
- [ ] `ADMIN_DESTRUCTIVE_ENABLED` remains off

### After gate (Phase 2+)

- [ ] Ops write endpoints (jobs, suspend, OAuth disconnect)
- [ ] Billing approvals UI (`/admin/budgets`)
- [ ] Continuous monitoring alerts
