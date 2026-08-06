# Admin Security State Machine (Order-of-Operations)

**Status:** Binding for platform-admin authn/MFA/step-up/impersonation  
**Scope:** Existing architecture — documentation + guards + journey tests (not a workflow engine)  
**Hard rules:** No new privileged mutations. `ADMIN_DESTRUCTIVE_ENABLED` remains **off**.

Related: [ADMIN_PORTAL_SECURITY.md](./ADMIN_PORTAL_SECURITY.md)

---

## 1. Assurance levels (step-up)

Prefer these labels over ad-hoc booleans when reasoning about transitions:

| Level | Meaning | Unlocks |
|-------|---------|---------|
| `NONE` | No valid step-up for this session binding | Nothing privileged |
| `PASSWORD_BOOTSTRAP` | Recent password reauth while **unenrolled**; `mfa_completed=false` | MFA **enroll/confirm** only |
| `MFA_VERIFIED` | Recent password + TOTP/recovery; `mfa_completed=true` | Privileged mutations (when MFA required) |

Helpers: `step_up_assurance_level()` in `core/admin_security.py`.

---

## 2. Operator account states

| State | Source of truth | Fail-closed effect |
|-------|-----------------|--------------------|
| Active | `users.is_active` | Allowed if operator |
| Inactive / unusable | `operator_account_usable()` | Deny reauth, enroll, privileged |
| Platform operator | `ADMIN_USER_IDS` | Deny all `/api/admin/platform/*` ops APIs |
| Operator removed | ID absent from `ADMIN_USER_IDS` | Immediate deny (no wait for JWT expiry for capability checks) |
| Password changed / reset | DB hash + revoke path | Sessions revoked; refresh revoked; step-up invalidated |
| Session revoked | secure sessions + JWT blacklist / refresh revoke | Bearer/cookie rejected |

**Deleted** users are treated as unusable (no row / inactive).

---

## 3. MFA states

| State | Store | Notes |
|-------|-------|-------|
| Not enrolled | User metadata `platform_admin_mfa.enrolled` absent/false | Password bootstrap allowed when MFA required |
| Enrollment pending | Redis/shared `mfa:enroll:{uid}` | Single pending; new start **replaces** old |
| Enrollment expired | Pending TTL elapsed | Confirm → `ENROLLMENT_EXPIRED` |
| Enrolled | Metadata + secret_enc | Privileged needs `MFA_VERIFIED` |
| Replacement pending | New pending while enrolled | Confirm old secret must fail (pending replaced) |
| Recovery codes available | Hashed list in metadata | Plaintext shown once |
| Recovery codes exhausted | All `used_at` set | TOTP still works |
| MFA disabled | Metadata removed | Forbidden while `ADMIN_MFA_REQUIRED` |

---

## 4. Session / step-up states

| State | Binding | Notes |
|-------|---------|-------|
| Normally authenticated | JWT `jti` or cookie sid | Not privileged alone |
| Password bootstrap | Step-up key per binding | Auto-invalidated if operator becomes enrolled |
| MFA-completed step-up | Same | Must not be downgraded by password-only reauth |
| Step-up expired / idle / absolute | TTL / idle / absolute | Fail closed |
| Session rotated | New binding; rebind or recover step-up | Old binding must not keep elevation |
| Session revoked | Revocation epoch | All step-ups for user cleared |
| Impersonating | Impersonation JWT | No operator capabilities; MFA/enroll blocked |
| Restoring | Stop impersonation | Must not restore stale actor step-up unless still valid by design |

---

## 5. Infrastructure states

| State | Behavior |
|-------|----------|
| Shared store available | Normal |
| Shared store unavailable | Privileged + MFA enroll fail closed (`STORE_UNAVAILABLE` / 503) |
| Audit store unavailable | Prefer fail-closed on write paths that require audit; list may degrade |
| Redis MFA pending vs DB enrolled mismatch | Confirm idempotent path; enroll start replaces pending |
| DB enrolled vs Redis step-up missing | Operator must reauth |

---

## 6. Valid transitions (summary)

```
NONE --password (unenrolled, MFA required)--> PASSWORD_BOOTSTRAP
PASSWORD_BOOTSTRAP --enroll start--> pending secret (still PASSWORD_BOOTSTRAP)
PASSWORD_BOOTSTRAP --confirm TOTP--> MFA_VERIFIED (+ enrolled)
NONE --password+TOTP (enrolled)--> MFA_VERIFIED
MFA_VERIFIED --expiry/revoke--> NONE
PASSWORD_BOOTSTRAP --other session enrolls--> NONE (stale bootstrap cleared)
MFA_VERIFIED --password-only reauth (MFA required)--> DENY (no downgrade)
```

**Invalid / must fail closed**

- Password bootstrap unlocking impersonate / sync retry / recovery regenerate  
- Confirm of obsolete pending secret after replacement  
- Privileged action after capability removal, deactivation, or password reset  
- Using old binding after rotation  
- MFA disable while `ADMIN_MFA_REQUIRED`  
- Destructive admin (`ADMIN_DESTRUCTIVE_ENABLED`) under unsafe prerequisites  

---

## 7. Dual-write order (source of truth)

| Flow | Source of truth | Preferred order |
|------|-----------------|-----------------|
| MFA confirm | DB metadata (enrolled) | Verify TOTP → claim/delete pending → write DB → upgrade step-up → audit |
| Recovery consume | DB metadata hashes | Claim (store NX) → mark used in DB |
| Step-up create | Shared store | Bind to current session binding only |
| Session rotate | New JWT/cookie | Capture state → issue new binding → attach step-up → revoke old |
| Password reset | DB password | Update hash → revoke sessions → invalidate step-up → revoke refresh tokens |

Partial failure after durable activation must **not** mint a second recovery-code set (confirm idempotent / already-completed).

---

## 8. Journey regression coverage

See `tests/test_admin_security_state_machine.py` (Journeys A–G) and
`tests/test_admin_auth_session_version.py` (Journey H + `asv`).

### Auth session version (`users.auth_session_version` / JWT claim `asv`)

Increments on: password reset, password change, account deactivation, explicit
`revoke_all_user_tokens`. Validated on every access-token verify against the DB
row loaded in the same query. Impersonation tokens carry `asv` (target) and
`actor_asv` (actor). Never expose the version in API error bodies or UI.

---

## 9. Sources of truth & recovery

| Flow | Authoritative store | Shared Redis role | Recovery |
|------|---------------------|-------------------|----------|
| MFA enrollment pending | Redis (`mfa:enroll:{uid}`) | Source of truth for pending secret | TTL expiry; new enroll replaces |
| MFA enrollment confirmed | **DB** user metadata | Pending deleted after commit; step-up upgraded | Idempotent confirm; reauth if step-up missing |
| Recovery-code use | **DB** hashes + Redis claim NX | Claim prevents double-spend | Prefer burn over double-use; regenerate after MFA |
| Recovery-code regeneration | **DB** (new generation + hashes) | Old claim keys keyed by generation | Plaintext shown once |
| Password bootstrap | Redis step-up binding | Session-bound | Cleared if enrolled elsewhere |
| MFA-completed step-up | Redis step-up binding | Session-bound | Recreate via password+TOTP reauth |
| Session rotation | New JWT/cookie + rebind | Must attach or clear all privileged | Fail closed → reauth |
| Session revocation | **DB** `auth_session_version` + refresh revoke + step-up epoch | Cache invalidate | Immediate access reject |
| Impersonation start/stop | JWT claims + actor/target `asv` | Step-up not inherited | Actor/target version mismatch → revoke |
| Password reset | **DB** password + `auth_session_version` (one txn) | Post-commit refresh/step-up cleanup | Must not succeed if version bump fails |
| Operator removal | `ADMIN_USER_IDS` env (capability) | N/A | Admin APIs denied immediately; ordinary JWT may remain until version bump/expiry |

**Rule:** Correctness must not require perfect Redis↔DB sync. Durable security facts live in Postgres/SQLite; Redis holds ephemeral step-up/pending/claims with fail-closed reads.
