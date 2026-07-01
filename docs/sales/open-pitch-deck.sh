#!/usr/bin/env bash
# Open the Florida SMB pitch deck locally (file or docs folder HTTP server).

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DECK="${DIR}/FLORIDA_SMB_WORKFLOW_AUDIT_PITCH_DECK.html"
PORT="${PITCH_DECK_PORT:-8765}"
URL="http://127.0.0.1:${PORT}/FLORIDA_SMB_WORKFLOW_AUDIT_PITCH_DECK.html"

open_url() {
  open "$1" 2>/dev/null || xdg-open "$1" 2>/dev/null || echo "Open in browser: $1"
}

if [[ ! -f "$DECK" ]]; then
  echo "Deck not found: $DECK"
  exit 1
fi

# Optional: local HTTP server (some browsers handle swipe/nav better than file://)
if [[ "${1:-}" == "--serve" ]]; then
  if ! curl -sf -o /dev/null "$URL" 2>/dev/null; then
    echo "Starting local server on port ${PORT}..."
    python3 -m http.server "$PORT" --directory "$DIR" >/dev/null 2>&1 &
    SERVER_PID=$!
    sleep 1
    trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
  fi
  echo "Opening: $URL"
  open_url "$URL"
  exit 0
fi

echo "Opening: $DECK"
open_url "file://${DECK}"
echo ""
echo "Tip: ./open-pitch-deck.sh --serve  for http://127.0.0.1:${PORT}/..."
echo "Cloud: upload this .html to iCloud Drive or Google Drive; open in Safari/Chrome (not Drive preview)."
