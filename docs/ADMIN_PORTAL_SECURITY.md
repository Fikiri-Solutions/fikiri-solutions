# Platform Admin Portal — Security Standard

**Status:** Binding for all admin portal work  
**Audience:** Engineers shipping `/admin` and `/api/admin/*`  
**Classification:** High-risk privileged system (not a normal product dashboard)

This document supersedes informal “OWASP compliant” claims. Controls are mapped to
named frameworks and must ship with **acceptance tests**. No destructive admin
capability may ship until **Phase 1.5** exit criteria are met.

Related: [ADMIN_ROUTES_STRATEGY.md](./ADMIN_ROUTES_STRATEGY.md)

---

## 1. Threat model (summary)

| Threat | Example | Primary controls |
|--------|---------|------------------|
| Privilege escalation | Tenant user hits `/api/admin/*` | Deny-by-default capabilities; server-side checks; priv-esc tests |
| Impersonation abuse | Nested / silent / long-lived view-as | Step-up + MFA; banner; short TTL; no nesting; kill switch; audit |
| Session hijack / fixation | Stolen admin JWT | Short TTL; rotation; revocation; secure cookies; inactivity timeout |
| Authn failure | Credential stuffing on operator login | Throttling; breached-password checks; MFA; alerts |
| CSRF / XSS | Browser forged admin POST | CSRF tokens; CSP; SameSite; no secrets in frontend |
| Audit evasion | Delete/alter audit rows | Append-only app path; no UPDATE/DELETE API; alert on anomalies |
| Mass exfil | Bulk export / search scraping | Rate limits; step-up; capability; audit + alerts |
| Insider / compromised operator | Malicious ops actions | Least privilege; lockdown; session revoke; incident logging |

---

## 2. Security principles (non-negotiable)

1. **Privileged by design** — every admin feature assumes compromise is catastrophic.
2. **Deny by default** — missing capability ⇒ 403; unknown action ⇒ denied.
3. **Least privilege** — operators get the minimum capability set for their role.
4. **Server-side enforcement** — UI hiding is never authorization.
5. **Step-up for impact** — MFA + recent re-auth before sensitive actions (see §4).
6. **Immutable actor** — under impersonation, `actor_user_id` never becomes the tenant.
7. **Audit everything** — success **and** denial; never log passwords, tokens, or OAuth secrets.
8. **Security before power** — Phase 1.5 gates Phase 2+ destructive controls.

---

## 3. Revised roadmap

| Phase | Name | Allowed scope | Exit gate |
|-------|------|---------------|-----------|
| **1** | Read-mostly foundation | Tenant directory, infra summary, audit **read**, impersonation **scaffolding** | Capability checks + basic audit (done) |
| **1.5** | **Security hardening (GATE)** | Step-up/MFA, session controls, CSRF, rate limits, lockdown, denied-action audit, priv-esc tests | Checklist §8 all green |
| **2** | Ops controls | Job cancel/retry, suspend, OAuth disconnect | Phase 1.5 complete |
| **3** | Billing overrides | Plan/budget soft-stop | Phase 1.5 + billing step-up |
| **4** | Deep infra | Queues, breakers, external ops links | Read-heavy + rate limits |
| **5** | Continuous assurance | SAST, secret scan, dependency scan, monitoring alerts | CI + runbooks |

**Hard rule:** Do not merge `platform.ops.write`, billing override, account suspend,
OAuth disconnect, role mutation, or export endpoints until Phase 1.5 exit criteria pass.

---

## 4. Sensitive actions (mandatory MFA + step-up)

These actions **must** require:

1. Platform capability (server-side)
2. Valid short-lived **step-up** proof (`X-Admin-Step-Up` token)
3. MFA enrollment + verification for the operator (when `ADMIN_MFA_REQUIRED=1`, default in production)
4. Audit of success **and** denial

| Action key | Examples |
|------------|----------|
| `impersonate` | Start view-as-user |
| `billing.change` | Plan override, budget approve/revoke |
| `account.suspend` | Deactivate / reactivate tenant |
| `oauth.disconnect` | Force-remove Gmail/Outlook tokens |
| `role.change` | Assign/revoke operator or tenant roles |
| `export` | Bulk tenant/data export |
| `destructive` | Delete data, wipe queues, hard revoke |

Password re-auth alone is **not** sufficient for production operators once MFA is required;
password step-up is the interim second factor only while MFA enrollment ships in 1.5.

---

## 5. Framework mapping (measurable — not “all OWASP”)

### 5.1 OWASP Top 10 (2021) — admin portal

| ID | Risk | Portal control | Acceptance test id |
|----|------|----------------|--------------------|
| A01 | Broken Access Control | `require_platform_capability`; deny-by-default; no nested impersonation | `AT-AUTHZ-01..05` |
| A02 | Cryptographic Failures | TLS in transit; hashed passwords; no secrets in logs/bundles | `AT-CRYPTO-01..03` |
| A03 | Injection | Parameterized SQL; validated JSON; no string-built queries | `AT-INJECT-01..02` |
| A04 | Insecure Design | Phase 1.5 gate; sensitive-action registry; lockdown | `AT-DESIGN-01..02` |
| A05 | Security Misconfiguration | Secure headers (CSP, HSTS, XFO, nosniff, Referrer-Policy) | `AT-CONFIG-01` |
| A06 | Vulnerable Components | Dependency scanning in CI | `AT-DEPS-01` |
| A07 | Identification & Auth Failures | MFA/step-up; throttling; short sessions | `AT-AUTHN-01..04` |
| A08 | Software & Data Integrity | Append-only audit path; no client-supplied actor id | `AT-AUDIT-01..03` |
| A09 | Logging & Monitoring Failures | Denied+success audit; correlation id; alert hooks | `AT-LOG-01..03` |
| A10 | SSRF | No operator-supplied URL fetch in admin APIs (v1) | `AT-SSRF-01` |

### 5.2 OWASP API Security Top 10 (2023)

| ID | Risk | Portal control | Test id |
|----|------|----------------|---------|
| API1 | BOLA | Tenant id from path never elevates without capability | `AT-API-01` |
| API2 | Broken Auth | JWT + step-up; no refresh for impersonation tokens | `AT-API-02` |
| API3 | Broken Object Property | Explicit serializers; no raw `users.*` dump | `AT-API-03` |
| API4 | Unrestricted Resource | Paginated lists; admin search rate limit | `AT-API-04` |
| API5 | BFLA | Capability ≠ tenant `role=admin` | `AT-API-05` |
| API6 | Unrestricted Business Flow | Step-up + rate limit on impersonate | `AT-API-06` |
| API7 | SSRF | See A10 | `AT-SSRF-01` |
| API8 | Misconfig | Secure headers / CORS | `AT-CONFIG-01` |
| API9 | Improper Inventory | Documented `/api/admin/platform/*` only | `AT-API-09` |
| API10 | Unsafe Consumption | No trusting client `actor_user_id` | `AT-API-10` |

### 5.3 ASVS (privileged app — selected)

| ASVS area | Requirement (paraphrased) | Test id |
|-----------|---------------------------|---------|
| V2 Authn | MFA for privileged users; step-up for sensitive ops | `AT-AUTHN-01..03` |
| V3 Session | Short TTL; revoke; no fixation; inactivity | `AT-SESS-01..04` |
| V4 Access | Deny-by-default; least privilege; server enforcement | `AT-AUTHZ-01..05` |
| V7 Error/Log | No secrets in logs; security events recorded | `AT-LOG-01..02` |
| V8 Data | Encrypt in transit; restrict DB creds | `AT-CRYPTO-01` |
| V9 Comms | HSTS / TLS | `AT-CONFIG-01` |
| V14 Config | Hardened headers; no debug in prod | `AT-CONFIG-01` |

### 5.4 Authentication & session guidance

Aligned with OWASP Authentication Cheat Sheet + Session Management Cheat Sheet:

- Operator login: throttle + lockout + breached-password policy (shared auth stack)
- Admin / impersonation sessions: shorter than normal user sessions
- Impersonation tokens: **no refresh token**; limited lifetime; kill switch
- Visible persistent banner; exit restores operator session from secure backup
- Session revocation API for emergencies

---

## 6. Acceptance tests (contract)

Tests live under `tests/test_admin_platform_security.py` (and related). Each id must have
**code evidence** before marking Phase 1.5 complete.

| ID | Claim | Expected |
|----|-------|----------|
| `AT-AUTHZ-01` | Non-operator cannot list tenants | 403 |
| `AT-AUTHZ-02` | Tenant `role=admin` ≠ platform operator | 403 on `/api/admin/platform/*` |
| `AT-AUTHZ-03` | Missing capability denied | 403 |
| `AT-AUTHZ-04` | Nested impersonation rejected | 400/403 + audit denied |
| `AT-AUTHZ-05` | Client cannot set `actor_user_id` | Ignored; actor from token only |
| `AT-AUTHN-01` | Impersonate without step-up rejected | 401/403 `STEP_UP_REQUIRED` |
| `AT-AUTHN-02` | Step-up token expires | Rejected after TTL |
| `AT-AUTHN-03` | MFA required when enrolled/flag on | Rejected without MFA proof |
| `AT-AUTHN-04` | Impersonation rate limited | 429 after threshold |
| `AT-SESS-01` | Impersonation TTL ≤ configured max | Claim `exp` bounded |
| `AT-SESS-02` | Impersonation token has no refresh | Response has no refresh_token |
| `AT-SESS-03` | Impersonation kill switch blocks start | 403 `IMPERSONATION_DISABLED` |
| `AT-SESS-04` | Global admin lockdown blocks admin API | 503 `ADMIN_LOCKDOWN` |
| `AT-AUDIT-01` | Successful impersonate audited | Row with outcome=success |
| `AT-AUDIT-02` | Denied impersonate audited | Row with outcome=denied |
| `AT-AUDIT-03` | Audit never stores password/token | Redaction / absence |
| `AT-API-01` | BOLA: guess other tenant id still needs capability | 403 without platform read |
| `AT-API-04` | Tenant search paginated + capped | limit ≤ 100 |
| `AT-API-05` | BFLA: ops.write not callable until gate | 403 or feature disabled |
| `AT-DESIGN-01` | Destructive capability gated by Phase 1.5 flag | `ADMIN_DESTRUCTIVE_ENABLED` |
| `AT-CONFIG-01` | Security headers present on API responses | CSP / XFO / nosniff (app-wide) |

---

## 7. Emergency controls

| Control | Env / API | Behavior |
|---------|-----------|----------|
| Global admin lockdown | `ADMIN_LOCKDOWN=1` | All `/api/admin/platform/*` → 503 except health/status if any |
| Impersonation shutdown | `IMPERSONATION_ENABLED` unset/false | Block start impersonation (stop still works) |
| Session revocation | Operator revoke + JWT blacklist | Invalidate access |
| Operator removal | Remove id from `ADMIN_USER_IDS` | Immediate capability loss |
| Incident logging | Audit `platform.emergency.*` | Always recorded |

---

## 8. Phase 1.5 / 1.6 exit checklist

- [x] Session-bound step-up + `require_admin_step_up` (shared store in 1.6)
- [x] MFA enrollment + TOTP verify + recovery codes (`ADMIN_MFA_VERIFIER_ENABLED`)
- [x] Nested impersonation blocked
- [x] Impersonation TTL + no refresh + kill switch (`IMPERSONATION_ENABLED`)
- [x] Admin lockdown + impersonation shutdown
- [x] CSRF for cookie-authenticated admin mutations; hardened impersonation stop
- [x] Rate limits in shared store: reauth, impersonate, tenant search, MFA
- [x] Audit events for step-up, MFA, store outage, session rotate/revoke
- [x] Privilege-escalation + tenant-boundary tests green
- [x] Secure headers + admin `Cache-Control: no-store`
- [x] Idle/absolute windows + invalidate on logout / password change / deactivate
- [x] Session rotation after successful step-up
- [x] `ADMIN_DESTRUCTIVE_ENABLED` remains off until ops explicitly enable after gate review

---

## 9. Explicit non-goals (this phase)

- Claiming blanket “OWASP compliance”
- Shipping job cancel / billing override / suspend before §8
- Separate admin SPA (still in-app `/admin` unless isolation requirements force a split later)

---

## 10. Implementation pointers

| Concern | Module |
|---------|--------|
| Capabilities | `core/platform_admin.py` |
| Step-up / lockdown / sensitive registry | `core/admin_security.py` |
| Audit | `core/admin_audit.py` |
| Admin API | `routes/admin_platform_api.py` |
| Impersonation JWT | `core/jwt_auth.py` |
| Security tests | `tests/test_admin_platform_security.py` |
