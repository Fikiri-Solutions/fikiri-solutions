# Security Cost-Control Playbook (CASA + OAuth Scope)

This playbook keeps security assessment cost under control by using free/open-source scanning first, scoped only to OAuth in-scope components, and enforcing a strict severity gate before any paid/lab submission.

> Note: CASA self-scanning verification is deprecated, but this workflow remains useful for readiness and reducing assessor rework cycles.

## Objective

- Run local/open-source checks first: OWASP ZAP, Semgrep, gitleaks, dependency scanners.
- Scan only OAuth in-scope surfaces for CASA-relevant flows.
- Do not submit to the lab until **zero critical/high** findings remain for required CWEs.

## CASA Requirement Focus (Cost-First)

Your dashboard shows the highest concentration in high/medium findings. For cost control, clear likely OAuth-relevant high-risk controls first:

- Access control on trusted server layers: `1.4.1`, `4.1.1`, `4.1.3`, `4.2.1`, `13.1.4`
- Session/token security: `3.3.1`, `3.4.1`, `3.4.2`, `3.4.3`, `3.5.3`
- Input/injection defenses: `5.1.1`, `5.1.5`, `5.2.6`, `5.3.3`, `5.3.4`, `5.3.8`
- Data/API leakage controls: `13.1.3`, `8.2.2`, `8.3.1`, `7.1.1`
- Build/deploy and debug hardening: `14.1.1`, `14.1.4`, `14.3.2`

Treat the above as your pre-lab blocker set when release changes touch OAuth/login/session/integration flows.

## Scanner-to-CASA Evidence Map

- `gitleaks` -> secret exposure and accidental credential leaks (supports `13.1.3`, `7.1.1`)
- `semgrep` -> authz/injection/security anti-patterns (supports `1.4.1`, `4.x`, `5.x`, `13.1.4`)
- `pip-audit` / `npm audit` / `osv-scanner` -> vulnerable dependencies impacting OAuth surface (supports `14.1.1`, `14.1.4`)
- `OWASP ZAP` -> runtime authn/authz/session/input issues on exposed OAuth endpoints (supports `3.x`, `4.x`, `5.x`, `13.x`)

## Submission Rule (Hard Gate)

Do not submit until all OAuth-in-scope requirement IDs in the blocker set above have:

- scan evidence attached (tool report),
- triage notes (affected endpoint/component),
- fix validation evidence (rerun report),
- no unresolved critical/high finding.

Tier-2-aligned hard gate for readiness:

- no failed mapped CWEs in `security-reports/casa-failed-mapped-cwes.json`.

## One-Command Gate (Recommended)

Run the pre-lab gate script:

```bash
./scripts/security_pre_lab_gate.sh
```

For lab-style evidence packaging and requirement mapping, run:

```bash
python3 scripts/casa_workbench.py --run-zap
```

Authenticated full ZAP scan (staging/dev only), with context + user:

```bash
ZAP_MODE=full \
ZAP_TARGET=https://staging.example.com \
ZAP_CONFIG=zap-casa-config.conf \
ZAP_CONTEXT_FILE=example.context \
ZAP_USER=test@example.com \
python3 scripts/casa_workbench.py --run-zap
```

API ZAP scan mode:

```bash
ZAP_MODE=api \
ZAP_TARGET=https://staging.example.com/openapi.json \
ZAP_CONFIG=zap-casa-api-config.conf \
ZAP_API_FORMAT=openapi \
python3 scripts/casa_workbench.py --run-zap
```

Custom-tools strict mode (enforces OWASP Benchmark evidence presence):

```bash
python3 scripts/casa_workbench.py --skip-scans --custom-tools-mode
```

Portal-ready evidence bundle with deadline tracking:

```bash
python3 scripts/casa_workbench.py --skip-scans --bundle --initiated-date 2026-04-27
```

This generates:

- `security-reports/casa-evidence-report.md`
- `security-reports/casa-evidence-matrix.csv`
- `security-reports/casa-required-cwes.txt` (scan policy input list)
- `security-reports/casa-required-cwes.csv` (CWE -> requirement ID mapping)
- `security-reports/casa-failed-mapped-cwes.json` (hard gate signal)
- `security-reports/casa-framework-evidence-template.csv` (accepted framework evidence manifest)
- `security-reports/casa-framework-evidence-guide.md` (what artifact type to upload per framework)
- `security-reports/casa-custom-scan-policy.json` (custom tool policy + required CWEs)
- `security-reports/casa-cwe-pass-fail.csv` (CWE mapped PASS/FAIL)
- `security-reports/casa-cwe-pass-fail.xml` (CWE mapped PASS/FAIL)
- `security-reports/casa-assessor-upload-checklist.md` (portal upload checklist)
- `security-reports/fluidattacks-quickstart.md` (optional preconfigured SAST procedure)
- `security-reports/owasp-benchmark-quickstart.md` (custom-tool benchmark run instructions)
- `security-reports/owasp-benchmark-evidence-status.json` (benchmark evidence gate status)
- `security-reports/casa-portal-submission-template.md` (portal metadata + upload checklist template)
- `security-reports/casa-deadline-tracker.json` (30-day submission window tracker)
- `security-reports/casa-submission-bundle.zip` (when `--bundle` is used)
- `security-reports/zap-results-full.xml` or `security-reports/zap-results-api.xml` (when ZAP full/api mode is used)
- refreshed scanner artifacts in `security-reports/`

Useful options:

```bash
# Skip ZAP when doing quick local triage
RUN_ZAP=0 ./scripts/security_pre_lab_gate.sh

# Override target and report directory
ZAP_TARGET=http://localhost:5000 REPORT_DIR=security-reports ./scripts/security_pre_lab_gate.sh
```

```bash
# Use existing scanner artifacts only (no new scans)
python3 scripts/casa_workbench.py --skip-scans
```

## Scope: OAuth In-Scope Components Only

Use this baseline scope unless your current release changes additional OAuth paths:

- Backend routes and auth flows: `routes/auth.py`, `routes/integrations.py`, `routes/google_risc.py`, `routes/user.py`
- OAuth/session/security core: `core/app_oauth.py`, `core/oauth_token_manager.py`, `core/jwt_auth.py`, `core/secure_sessions.py`, `core/security.py`, `core/google_risc.py`
- OAuth providers: `integrations/gmail/`, `integrations/outlook/`
- OAuth-related frontend flows: `frontend/src/pages/GmailConnect.tsx`, `frontend/src/components/GmailConnection.tsx`, `frontend/src/components/OutlookConnection.tsx`, `frontend/src/services/apiClient.ts`
- OAuth test coverage: `tests/test_app_oauth.py`, `tests/test_oauth_token_manager.py`

If a release does not touch a file in this list, keep it in passive review but prioritize active scanning on changed OAuth files first.

## Pre-Scan Setup

From repo root:

```bash
mkdir -p security-reports
python3 -m pip install --upgrade pip pip-audit
pip install semgrep
```

Install tooling not already available on your machine:

```bash
brew install gitleaks osv-scanner
```

Notes:

- `pip-audit`, `semgrep`, and `gitleaks` can also be installed with `pipx` if you prefer isolated CLI tools.
- ZAP baseline run in this repo uses Docker (`docker` required unless `RUN_ZAP=0`).
- For JS/TS applications, prefer custom SAST tools that support JS/TS (for this repo: `semgrep`).
- Run active/authenticated ZAP scans against staging/dev only, never unauthorized targets.
- OWASP Benchmark evidence can come from Java and/or Python benchmark tracks; keep outputs and scorecards in the expected `security-reports/owasp-benchmark-*` folders.
- For Python Benchmark evidence, include benchmark version metadata in filenames and reconcile against `expectedresults-VERSION#.csv`.

## 1) Secrets Scan (gitleaks)

Run on the repo:

```bash
gitleaks detect --source . --report-format json --report-path security-reports/gitleaks.json
```

Fail gate:

- Any verified secret in OAuth paths blocks lab submission.
- Rotate/revoke leaked credentials before continuing.

## 2) SAST (Semgrep) with OAuth Scope

Run Semgrep on in-scope backend/frontend paths only:

```bash
semgrep scan \
  --config p/owasp-top-ten \
  --config p/secrets \
  --json \
  --output security-reports/semgrep.json \
  routes/auth.py routes/integrations.py routes/google_risc.py routes/user.py \
  core/app_oauth.py core/oauth_token_manager.py core/jwt_auth.py core/secure_sessions.py core/security.py core/google_risc.py \
  integrations/gmail integrations/outlook \
  frontend/src/pages/GmailConnect.tsx frontend/src/components/GmailConnection.tsx frontend/src/components/OutlookConnection.tsx frontend/src/services/apiClient.ts
```

Fail gate:

- No unresolved critical/high findings on required CWEs.
- Add narrowly scoped suppressions only with explicit justification in PR notes.

## 3) Dependency Risk (pip-audit, npm audit, osv-scanner)

Backend Python dependencies:

```bash
pip-audit -r requirements.txt -f json -o security-reports/pip-audit.json
```

Frontend dependencies:

```bash
npm --prefix frontend audit --json > security-reports/npm-audit.json || true
```

Cross-ecosystem OSS vulnerability pass:

```bash
osv-scanner --format json --output security-reports/osv-scanner.json .
```

Fail gate:

- Zero critical/high vulnerabilities with a reachable path in OAuth-in-scope components.
- If finding is non-reachable, document evidence in the release security note.

## 4) DAST (OWASP ZAP) Focused OAuth Flow

Target only OAuth-relevant endpoints and pages in local/staging:

- OAuth connect/login pages and callbacks
- Token exchange/refresh and integration status endpoints
- Session/authenticated user flows that expose OAuth-connected data

Recommended approach:

- Use ZAP Baseline or API scan against a pre-authenticated context.
- Exclude unrelated routes to reduce noise and fix cycles.

Example baseline run:

```bash
docker run --rm -t \
  -v "$(pwd)/security-reports:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t http://host.docker.internal:5000 -r zap-report.html -J zap-report.json
```

Fail gate:

- Zero critical/high alerts affecting OAuth authn/authz/session/token handling.

## Required Severity Gate Before Lab

Do not submit to CASA lab until all are true:

- gitleaks: no active secret exposure in scope
- semgrep: zero critical/high on required CWEs
- dependency scans: zero critical/high reachable in scope
- ZAP: zero critical/high affecting OAuth in-scope attack surface

## Rework Loop Control (Cost Guardrail)

Use this loop to avoid expensive re-submissions:

1. Run all free scans locally/staging.
2. Triage by severity and exploitability (OAuth scope first).
3. Fix and rerun only impacted scanners.
4. Repeat until severity gate is clean.
5. Submit once, with artifacts attached from `security-reports/`.

## Lightweight Release Checklist

- [ ] OAuth-scope file list reviewed for this release
- [ ] `gitleaks` report generated and triaged
- [ ] `semgrep` report generated and triaged
- [ ] `pip-audit`, `npm audit`, `osv-scanner` reports generated and triaged
- [ ] ZAP OAuth-focused run completed
- [ ] Zero critical/high on required CWEs
- [ ] Evidence bundle saved under `security-reports/`

## Notes for CASA Mapping

- Keep each finding mapped to the relevant CWE and OAuth flow (login, consent, callback, token storage, token refresh, session).
- When using suppressions or risk acceptance, include explicit technical rationale and expiration date.
- Prefer fix evidence with before/after scan artifacts to prevent back-and-forth with the lab.
