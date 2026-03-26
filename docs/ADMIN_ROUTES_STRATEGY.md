# Admin Routes Strategy — Lean, In-App, RBAC-First

Use this doc when building admin functionality. **Do not build a separate admin portal** at the current stage.

---

## Principles

- **One app.** Admin lives inside the existing app as an `/admin` section.
- **RBAC with strict server-side checks.** Hide admin UI for non-admins, but **never rely on frontend hiding alone** — enforce every admin action on the backend.
- **Audit logs** for all admin actions.
- **Permission model** = capabilities (e.g. `budget.approve`, `users.manage_roles`, `billing.manage`), not just role strings.

---

## Recommended Minimal Roles

| Role       | Scope |
|-----------|--------|
| **owner** | Billing, team/roles, plan overrides, AI budget approvals, destructive actions, ownership transfer |
| **admin** | Operational controls (rate limits, budgets, support tools). No ownership transfer. |
| **member** | Normal product use only |
| **support** (optional) | Read-only diagnostics + limited tenant-assist actions |

---

## What to Build (Lean + Safe)

### 1. Permission model

- Define **permissions as capabilities**, e.g.:
  - `budget.approve`, `budget.revoke`
  - `users.manage_roles`, `users.invite`, `users.remove`
  - `billing.manage`, `billing.plan_override`
  - `admin.rate_limits`, `admin.tenant_diagnostics`
- Map roles → sets of permissions.
- Backend checks: **always** use something like `require_permission("budget.approve")` (decorator or middleware). Never trust frontend-only checks.

### 2. Backend enforcement first

- Add decorators/middleware: e.g. `@require_permission("budget.approve")`.
- Every admin endpoint must verify the caller's role/permissions on the server.

### 3. Admin surface inside existing app

- **`/admin`** section rendered only for allowed roles (frontend route guard).
- Start with **3 pages**:
  1. **AI Budget Approvals** — approve/revoke monthly soft-stop overrides.
  2. **Tenant Usage / Health** — usage and health per tenant.
  3. **Role Management** — assign/revoke roles (owner/admin/member/support).

### 4. Audit trail

- Log for every admin action:
  - **Actor** (user id, role)
  - **Action** (e.g. `budget.approve`, `role.assign`)
  - **Target** (tenant id, user id)
  - **Before/after** (e.g. previous vs new role, or previous vs new override)
  - **Timestamp**, **IP** (and optionally user agent)
- Store in DB or logging pipeline; queryable for compliance and support.

### 5. Safety controls

- **Step-up / re-auth** for sensitive actions: role changes, approvals, billing, destructive actions.
- Consider: require password or MFA again before executing.

---

## Immediate Need: AI Budget Approvals

- **One admin endpoint:** approve/revoke monthly soft-stop override (per tenant or globally, as needed).
- **One simple UI:** `/admin/budgets` — list pending approvals, approve/revoke.
- Gives operational control without new infrastructure.

---

## When to Split Into a Separate Admin Portal

Only consider a **separate** admin app when you need:

- SSO/SAML for internal staff
- Stricter network isolation / compliance
- Separate deployment or security boundaries
- Large internal ops workflows that don't fit the main app

Until then, a separate portal is extra overhead with little ROI.

---

## Implementation Checklist (When You Start)

- [ ] Define capability strings and role → permissions mapping (config or DB).
- [ ] Add backend `require_permission(capability)` (or equivalent) and use on all admin routes.
- [ ] Add `/admin` route(s) in the existing app; guard with role/permission check (and still enforce on API).
- [ ] Implement audit logging (actor, action, target, before/after, timestamp, IP).
- [ ] Build first admin endpoint: approve/revoke budget soft-stop override.
- [ ] Build first admin page: `/admin/budgets` for pending approvals.
- [ ] Add step-up auth for sensitive admin actions (role changes, approvals, billing).
