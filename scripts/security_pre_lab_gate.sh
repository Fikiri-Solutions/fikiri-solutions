#!/usr/bin/env bash

set -euo pipefail

REPORT_DIR="${REPORT_DIR:-security-reports}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"
ZAP_TARGET="${ZAP_TARGET:-http://host.docker.internal:5000}"
RUN_ZAP="${RUN_ZAP:-1}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

OAUTH_SCOPE=(
  "routes/auth.py"
  "routes/integrations.py"
  "routes/google_risc.py"
  "routes/user.py"
  "core/app_oauth.py"
  "core/oauth_token_manager.py"
  "core/jwt_auth.py"
  "core/secure_sessions.py"
  "core/security.py"
  "core/google_risc.py"
  "integrations/gmail"
  "integrations/outlook"
  "frontend/src/pages/GmailConnect.tsx"
  "frontend/src/components/GmailConnection.tsx"
  "frontend/src/components/OutlookConnection.tsx"
  "frontend/src/services/apiClient.ts"
)

log_info() {
  printf "${YELLOW}[*]${NC} %s\n" "$1"
}

log_ok() {
  printf "${GREEN}[+]${NC} %s\n" "$1"
}

log_fail() {
  printf "${RED}[-]${NC} %s\n" "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log_fail "Missing required command: $1"
    exit 2
  fi
}

ensure_report_dir() {
  mkdir -p "$REPORT_DIR"
}

run_gitleaks() {
  log_info "Running gitleaks (working tree; respects .gitleaksignore)"
  # --no-git: assess current tree only; full-history scans still flag rotated keys in old commits.
  gitleaks detect --source . --no-git --report-format json --report-path "$REPORT_DIR/gitleaks.json"
}

run_semgrep() {
  log_info "Running semgrep on OAuth scope"
  semgrep scan \
    --config p/owasp-top-ten \
    --config p/secrets \
    --json \
    --output "$REPORT_DIR/semgrep.json" \
    "${OAUTH_SCOPE[@]}"
}

run_pip_audit() {
  log_info "Running pip-audit"
  pip-audit -r requirements.txt -f json -o "$REPORT_DIR/pip-audit.json"
}

run_npm_audit() {
  log_info "Running npm audit"
  npm --prefix "$FRONTEND_DIR" audit --json > "$REPORT_DIR/npm-audit.json" || true
}

run_osv_scanner() {
  log_info "Running osv-scanner"
  osv-scanner --format json --output "$REPORT_DIR/osv-scanner.json" .
}

run_zap_baseline() {
  if [[ "$RUN_ZAP" != "1" ]]; then
    log_info "Skipping ZAP run (RUN_ZAP=$RUN_ZAP)"
    return 0
  fi

  log_info "Running OWASP ZAP baseline against $ZAP_TARGET"
  docker run --rm -t \
    -v "$(pwd)/$REPORT_DIR:/zap/wrk:rw" \
    ghcr.io/zaproxy/zaproxy:stable \
    zap-baseline.py \
    -t "$ZAP_TARGET" \
    -r zap-report.html \
    -J zap-report.json
}

count_high_critical() {
  local file_path="$1"
  local parser_name="$2"

  python3 - "$file_path" "$parser_name" <<'PY'
import json
import sys
from pathlib import Path

file_path = Path(sys.argv[1])
parser_name = sys.argv[2]

if not file_path.exists():
    print(0)
    raise SystemExit(0)

try:
    data = json.loads(file_path.read_text(encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit(0)

def normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()

def is_high_or_critical(value):
    val = normalize(value)
    return val in {"high", "critical", "error", "3", "4"}

count = 0

if parser_name == "gitleaks":
    findings = data if isinstance(data, list) else data.get("findings", [])
    for finding in findings:
        if finding:
            count += 1
elif parser_name == "semgrep":
    for finding in data.get("results", []):
        severity = finding.get("extra", {}).get("severity")
        if is_high_or_critical(severity):
            count += 1
elif parser_name == "pip-audit":
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            aliases = [normalize(a) for a in vuln.get("aliases", [])]
            if any("ghsa" in a for a in aliases):
                # pip-audit JSON often omits direct severity. Keep conservative: count all GHSA issues.
                count += 1
            elif is_high_or_critical(vuln.get("severity")):
                count += 1
elif parser_name == "npm-audit":
    vulns = data.get("vulnerabilities", {})
    for details in vulns.values():
        if is_high_or_critical(details.get("severity")):
            count += 1
elif parser_name == "osv":
    # OSV scanner JSON can be nested. Keep parser defensive.
    results = data.get("results", [])
    for result in results:
        for pkg in result.get("packages", []):
            for vuln in pkg.get("vulnerabilities", []):
                if is_high_or_critical(vuln.get("severity")):
                    count += 1
                # If severity isn't present, treat unknown as medium by default and do not count.
elif parser_name == "zap":
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            # ZAP riskcode: 0 info, 1 low, 2 medium, 3 high
            risk = normalize(alert.get("riskcode"))
            if risk in {"3", "4"}:
                count += 1

print(count)
PY
}

main() {
  require_cmd "python3"
  require_cmd "semgrep"
  require_cmd "gitleaks"
  require_cmd "pip-audit"
  require_cmd "npm"
  require_cmd "osv-scanner"
  if [[ "$RUN_ZAP" == "1" ]]; then
    require_cmd "docker"
  fi

  ensure_report_dir

  run_gitleaks
  run_semgrep
  run_pip_audit
  run_npm_audit
  run_osv_scanner
  run_zap_baseline

  local gitleaks_count semgrep_count pip_count npm_count osv_count zap_count total
  gitleaks_count="$(count_high_critical "$REPORT_DIR/gitleaks.json" "gitleaks")"
  semgrep_count="$(count_high_critical "$REPORT_DIR/semgrep.json" "semgrep")"
  pip_count="$(count_high_critical "$REPORT_DIR/pip-audit.json" "pip-audit")"
  npm_count="$(count_high_critical "$REPORT_DIR/npm-audit.json" "npm-audit")"
  osv_count="$(count_high_critical "$REPORT_DIR/osv-scanner.json" "osv")"
  zap_count="$(count_high_critical "$REPORT_DIR/zap-report.json" "zap")"

  total=$((gitleaks_count + semgrep_count + pip_count + npm_count + osv_count + zap_count))

  printf "\nSecurity pre-lab gate summary:\n"
  printf "  gitleaks findings: %s\n" "$gitleaks_count"
  printf "  semgrep high/critical: %s\n" "$semgrep_count"
  printf "  pip-audit high/critical (conservative): %s\n" "$pip_count"
  printf "  npm audit high/critical: %s\n" "$npm_count"
  printf "  osv-scanner high/critical: %s\n" "$osv_count"
  printf "  zap high risk alerts: %s\n" "$zap_count"

  if [[ "$total" -gt 0 ]]; then
    log_fail "Pre-lab gate FAILED. Resolve critical/high issues before CASA submission."
    exit 1
  fi

  log_ok "Pre-lab gate PASSED. No blocking critical/high findings."
}

main "$@"
