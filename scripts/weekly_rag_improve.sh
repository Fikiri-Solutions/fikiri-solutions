#!/usr/bin/env bash
#
# Weekly RAG improvement workflow:
#   1) Build eval sets from chatbot_feedback
#   2) Run eval metrics (report_*.json)
#   3) Dump top 50 incorrect/needs-review questions for review
#   4) Optionally re-index KB docs (--reindex; requires API_URL and API key)
#
# Usage:
#   ./scripts/weekly_rag_improve.sh
#   ./scripts/weekly_rag_improve.sh --reindex
#
# Env (optional):
#   EVALS_DIR     default: project/data/evals
#   API_URL       required for --reindex (e.g. https://app.example.com)
#   CHATBOT_API_KEY or API_KEY   required for --reindex (chatbot scope)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVALS_DIR="${EVALS_DIR:-$PROJECT_ROOT/data/evals}"
LIMIT="${LIMIT:-50}"

cd "$PROJECT_ROOT"

echo "=== 1) Build eval sets ==="
python scripts/build_eval_sets.py

echo ""
echo "=== 2) Run eval metrics ==="
python scripts/run_eval.py "$EVALS_DIR"

echo ""
echo "=== 3) Dump top ${LIMIT} incorrect questions for review ==="
python scripts/dump_incorrect_for_review.py "$EVALS_DIR" "$LIMIT"

REINDEX=false
for arg in "$@"; do
  if [ "$arg" = "--reindex" ]; then
    REINDEX=true
    break
  fi
done

if [ "$REINDEX" = true ]; then
  echo ""
  echo "=== 4) Re-index KB documents ==="
  API_URL="${API_URL:-}"
  API_KEY="${CHATBOT_API_KEY:-$API_KEY}"
  if [ -z "$API_URL" ] || [ -z "$API_KEY" ]; then
    echo "Reindex skipped: set API_URL and CHATBOT_API_KEY (or API_KEY) to call revectorize." >&2
    echo "Example: API_URL=http://localhost:5000 CHATBOT_API_KEY=fik_xxx ./scripts/weekly_rag_improve.sh --reindex" >&2
    exit 1
  fi
  URL="${API_URL%/}/api/chatbot/knowledge/revectorize"
  HTTP_CODE=$(curl -s -o /tmp/revectorize.json -w "%{http_code}" -X POST "$URL" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY")
  if [ "$HTTP_CODE" = "200" ]; then
    echo "Revectorize succeeded: $(cat /tmp/revectorize.json)"
  else
    echo "Revectorize failed (HTTP $HTTP_CODE): $(cat /tmp/revectorize.json)" >&2
    exit 1
  fi
else
  echo ""
  echo "=== 4) Re-index skipped (use --reindex to run; requires API_URL and CHATBOT_API_KEY) ==="
fi

echo ""
echo "Done. Reports and incorrect list in: $EVALS_DIR"
