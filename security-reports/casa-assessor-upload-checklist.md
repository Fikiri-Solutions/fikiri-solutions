# CASA Assessor Upload Checklist

Use this checklist before uploading evidence to the portal.

## Required core files

- [ ] `casa-cwe-pass-fail.csv`
- [ ] `casa-cwe-pass-fail.xml`
- [ ] `casa-custom-scan-policy.json` (if using custom tools)
- [ ] AST plain text summaries (`ast-*-results.txt`) for portal compatibility
- [ ] DAST result artifact(s): `zap-report.json` (+ CSV/XML export if available)
- [ ] If full web/mobile DAST was run: `zap-results-full.xml`
- [ ] If API DAST was run: `zap-results-api.xml`
- [ ] SAST result artifact(s): `semgrep.json` (+ CSV/XML export if available)
- [ ] Optional preconfigured SAST result: `fluidattacks-results.csv`
- [ ] If using custom tools: OWASP Benchmark scan output in `owasp-benchmark-results/`
- [ ] If using custom tools: OWASP Benchmark scorecard in `owasp-benchmark-scorecards/`

## Supporting evidence (recommended)

- [ ] `casa-evidence-report.md`
- [ ] `casa-evidence-matrix.csv`
- [ ] `casa-required-cwes.txt`
- [ ] `casa-required-cwes.csv`
- [ ] `casa-failed-mapped-cwes.json`
- [ ] `casa-framework-evidence-template.csv`
- [ ] `casa-framework-evidence-guide.md`

## Optional (if requested by assessor)

- [ ] OWASP Benchmark scorecard output from selected DAST/SAST tool

## Gate

- [ ] No failed mapped CWEs before submission
