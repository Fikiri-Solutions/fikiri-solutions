#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORTS_DIR="${REPORTS_DIR:-$ROOT_DIR/reports}"
RESULTS_PATH="${PROVIDER_CONTRACT_RESULTS:-$REPORTS_DIR/provider_contract.json}"

mkdir -p "$REPORTS_DIR"

echo "▶ Running provider contract tests"
PYTEST_BIN="${PYTEST_BIN:-$ROOT_DIR/venv/bin/pytest}"

if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "❌ pytest not found at $PYTEST_BIN"
  exit 1
fi

PROVIDER_CONTRACT_RESULTS="$RESULTS_PATH" \
  "$PYTEST_BIN" -q -m contract || true

echo "▶ Contract results: $RESULTS_PATH"
if [[ -f "$RESULTS_PATH" ]]; then
  cat "$RESULTS_PATH"
else
  echo "❌ No results file produced."
  exit 2
fi
