#!/bin/bash
# Fikiri Solutions - Production startup (local / bare metal)
# Never put credentials in this file — use .env (gitignored) or your secret manager.

set -euo pipefail
cd "$(dirname "$0")"

echo "🚀 Starting Fikiri Solutions..."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  echo "✅ Loaded environment from .env"
fi

if [ -z "${REDIS_URL:-}" ]; then
  echo "❌ REDIS_URL is not set. Add it to .env (see env.template) or export it before running."
  exit 1
fi

export FLASK_ENV="${FLASK_ENV:-production}"
export FLASK_DEBUG="${FLASK_DEBUG:-False}"

echo "✅ Core environment configured"

# Activate virtual environment
# shellcheck disable=SC1091
source venv_local/bin/activate

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
  echo "❌ Failed to activate virtual environment (venv_local)"
  exit 1
fi

echo "🔍 Testing Redis connection..."
python -c "
import redis
import os
try:
    client = redis.from_url(os.getenv('REDIS_URL'), decode_responses=True)
    client.ping()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

echo "🚀 Starting Fikiri Solutions application..."
python start_app.py
