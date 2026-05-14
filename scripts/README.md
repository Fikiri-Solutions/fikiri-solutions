# Scripts

Operational, security, and quality scripts for this repository. **Application runtime** does not import these modules; they are CLI / CI helpers.

## Ad-hoc analysis (not required for app or tests)

| Script | Purpose |
|--------|---------|
| [monte_carlo_saas_fpna.py](monte_carlo_saas_fpna.py) | Monte Carlo FP&A scenarios (optional `numpy`) |
| [plot_revenue_investor_projection.py](plot_revenue_investor_projection.py) | Revenue / payout charts → `docs/plots/` (gitignored PNGs) |
| [extract_pdf_text.py](extract_pdf_text.py) | Extract text from PDFs for one-off review |

## CLI entrypoints (run from repo root)

| Script | Purpose |
|--------|---------|
| [init_database.py](init_database.py) | Bootstrap DB tables: `python3 scripts/init_database.py` |

Gmail and Outlook OAuth run through the **Flask app** (`core/app_oauth.py`, in-app Integrations). See [docs/CONNECT_GMAIL_OUTLOOK.md](../docs/CONNECT_GMAIL_OUTLOOK.md).

---

# Code Quality Checks

Simple syntax and logic checking scripts.

## Quick Check

```bash
# Check specific files
python3 scripts/check_syntax.py file1.py file2.py

# Check all Python files
python3 scripts/check_syntax.py --all

# Check recently modified files
./scripts/check_recent.sh
```

## What It Checks

✅ **Syntax Errors** - Python syntax validation  
✅ **Logic Issues** - Unmatched try/except blocks  
✅ **File Existence** - Missing files  

## Usage After Writing Code

After writing any Python file, run:

```bash
python3 scripts/check_syntax.py path/to/file.py
```

Or check all files:

```bash
python3 scripts/check_syntax.py --all
```

## TypeScript Checks

For frontend files:

```bash
cd frontend && npx tsc --noEmit --skipLibCheck
```

## Integration

These checks run automatically in CI/CD, but you can also run them manually before committing.

## Security Pre-Lab Gate (Cost Control)

For CASA/OAuth security readiness with strict critical/high blocking:

```bash
./scripts/security_pre_lab_gate.sh
```

Quick local run without ZAP:

```bash
RUN_ZAP=0 ./scripts/security_pre_lab_gate.sh
```

## CASA Workbench (Heavy-Lift Automation)

Runs OAuth-scoped scans, maps findings to prioritized CASA requirement IDs/CWEs,
and outputs lab-ready evidence artifacts.

```bash
python3 scripts/casa_workbench.py --run-zap
```

Authenticated ZAP full scan mode (staging/dev):

```bash
ZAP_MODE=full ZAP_TARGET=https://staging.example.com ZAP_CONFIG=zap-casa-config.conf ZAP_CONTEXT_FILE=example.context ZAP_USER=test@example.com python3 scripts/casa_workbench.py --run-zap
```

ZAP API scan mode:

```bash
ZAP_MODE=api ZAP_TARGET=https://staging.example.com/openapi.json ZAP_CONFIG=zap-casa-api-config.conf ZAP_API_FORMAT=openapi python3 scripts/casa_workbench.py --run-zap
```

Use existing artifacts only:

```bash
python3 scripts/casa_workbench.py --skip-scans
```

Enable strict custom-tool evidence gate (requires OWASP Benchmark outputs + scorecards):

```bash
python3 scripts/casa_workbench.py --skip-scans --custom-tools-mode
```

Create a portal-ready evidence bundle with 30-day tracker:

```bash
python3 scripts/casa_workbench.py --skip-scans --bundle --initiated-date 2026-04-27
```

Outputs include:

- `security-reports/casa-evidence-report.md`
- `security-reports/casa-evidence-matrix.csv`
- `security-reports/casa-required-cwes.txt`
- `security-reports/casa-required-cwes.csv`
- `security-reports/casa-failed-mapped-cwes.json`
- `security-reports/casa-framework-evidence-template.csv`
- `security-reports/casa-framework-evidence-guide.md`
- `security-reports/casa-custom-scan-policy.json`
- `security-reports/casa-cwe-pass-fail.csv`
- `security-reports/casa-cwe-pass-fail.xml`
- `security-reports/casa-assessor-upload-checklist.md`
- `security-reports/fluidattacks-quickstart.md`
- `security-reports/owasp-benchmark-quickstart.md`
- `security-reports/owasp-benchmark-evidence-status.json`
- `security-reports/casa-portal-submission-template.md`
- `security-reports/casa-deadline-tracker.json`
- `security-reports/casa-submission-bundle.zip` (with `--bundle`)

