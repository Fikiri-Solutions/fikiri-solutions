# FluidAttacks SAST Quickstart (Readiness)

Use this only if you want to add FluidAttacks artifacts to your readiness evidence package.

## Minimal workflow

1. Create a scan workspace folder.
2. Place CASA scan Dockerfile in that folder.
3. Clone app repo into workspace and place `config.yaml` at repo root.
4. Build container:
   `docker build -t casascan /path/to/Dockerfile`
5. Run scan:
   `docker run casascan m gitlab:fluidattacks/universe@trunk /skims scan {AppRepo}/config.yaml`
6. Copy result CSV from container to host as `fluidattacks-results.csv`.
7. Place `fluidattacks-results.csv` into `security-reports/`.
8. Re-run workbench with `--skip-scans` to include it in mapping outputs.

## Notes

- Keep scan output in CSV format for portal compatibility.
- For JavaScript/TypeScript projects, Semgrep remains the primary custom SAST option.
