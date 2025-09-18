#!/bin/bash
# 🚀 Pre-Flight Checklist Script for Fikiri v1.0.0 Deployment
# Run this script before deploying to production

set -e

# Configuration
BACKEND_URL="https://fikirisolutions.onrender.com"
FRONTEND_URL="https://www.fikirisolutions.com"
LOG_FILE="/tmp/fikiri-preflight.log"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check function
check() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    log "🔍 Checking: $name"
    
    if eval "$command" >/dev/null 2>&1; then
        log "✅ $name: PASSED"
        return 0
    else
        log "❌ $name: FAILED"
        return 1
    fi
}

# Header
log "🚀 Starting Fikiri v1.0.0 Pre-Flight Checklist"
log "=============================================="

# 1. Release & Config Checks
log ""
log "📋 1. RELEASE & CONFIG CHECKS"
log "-----------------------------"

# Check if v1.0.0 tag exists
check "v1.0.0 tag exists" "git tag -l | grep -q '^v1.0.0$'"

# Check if release notes exist
check "Release notes exist" "test -f RELEASE_NOTES_v1.0.0.md"

# Check environment variables
log "🔍 Checking environment variables..."
if [ -f ".env" ]; then
    log "✅ .env file exists"
    
    # Check critical environment variables
    required_vars=("OPENAI_API_KEY" "SECRET_KEY" "GMAIL_CLIENT_ID" "GMAIL_CLIENT_SECRET")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env; then
            log "✅ $var is set"
        else
            log "❌ $var is missing or empty"
        fi
    done
else
    log "❌ .env file missing"
fi

# Check OAuth redirect URIs match
log "🔍 Checking OAuth redirect URIs..."
if grep -q "fikirisolutions.onrender.com" .env && grep -q "fikirisolutions.com" .env; then
    log "✅ OAuth redirect URIs configured"
else
    log "❌ OAuth redirect URIs mismatch"
fi

# Check database backup
log "🔍 Checking database backup..."
if [ -f "data/fikiri.db" ]; then
    backup_file="data/fikiri_backup_$(date +%Y%m%d).db"
    if [ -f "$backup_file" ]; then
        log "✅ Database backup exists: $backup_file"
    else
        log "⚠️  No backup for today, creating one..."
        cp data/fikiri.db "$backup_file"
        log "✅ Backup created: $backup_file"
    fi
else
    log "❌ Database file missing"
fi

# 2. Safety Rails Checks
log ""
log "🛡️  2. SAFETY RAILS CHECKS"
log "-------------------------"

# Check kill-switch default state
log "🔍 Checking kill-switch default state..."
if grep -q "global_kill_switch: bool = False" core/automation_safety.py; then
    log "✅ Kill-switch defaults to OFF"
else
    log "❌ Kill-switch default state unclear"
fi

# Check auto-reply throttle
log "🔍 Checking auto-reply throttle..."
if grep -q "max_auto_replies_per_contact_per_day: int = 2" core/automation_safety.py; then
    log "✅ Auto-reply throttle: ≤ 2 replies/contact/day"
else
    log "❌ Auto-reply throttle not configured"
fi

# Check burst cap
log "🔍 Checking burst cap..."
if grep -q "max_actions_per_user_per_5min: int = 50" core/automation_safety.py; then
    log "✅ Burst cap: ≤ 50 actions / 5 min / user"
else
    log "❌ Burst cap not configured"
fi

# Check idempotency keys
log "🔍 Checking idempotency keys..."
if grep -q "idempotency_key" core/automation_safety.py; then
    log "✅ Idempotency keys enabled"
else
    log "❌ Idempotency keys not implemented"
fi

# 3. Auth & Tokens Checks
log ""
log "🔐 3. AUTH & TOKENS CHECKS"
log "-------------------------"

# Check token encryption
log "🔍 Checking token encryption..."
if grep -q "Fernet" core/oauth_token_manager.py; then
    log "✅ Tokens encrypted at rest"
else
    log "❌ Token encryption not implemented"
fi

# Check refresh logic
log "🔍 Checking refresh logic..."
if grep -q "refresh_token" core/oauth_token_manager.py; then
    log "✅ Refresh logic implemented"
else
    log "❌ Refresh logic missing"
fi

# Check failure handling
log "🔍 Checking OAuth failure handling..."
if grep -q "oauth_failure_threshold" core/automation_safety.py; then
    log "✅ OAuth failure threshold configured"
else
    log "❌ OAuth failure handling missing"
fi

# 4. Caching Checks
log ""
log "💾 4. CACHING CHECKS"
log "------------------"

# Check if frontend has build process
log "🔍 Checking frontend build process..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    log "✅ Frontend build process exists"
    
    # Check for hashed assets
    if grep -q "hash" frontend/package.json || grep -q "chunk" frontend/package.json; then
        log "✅ Hashed asset filenames configured"
    else
        log "⚠️  Hashed assets not explicitly configured"
    fi
else
    log "❌ Frontend build process missing"
fi

# Check cache headers (would need to be implemented)
log "🔍 Checking cache headers..."
log "⚠️  Cache headers need to be implemented in production"

# Check Vercel cache clear path
log "🔍 Checking Vercel cache clear path..."
if grep -q "vercel.*force" RELEASE.md; then
    log "✅ Vercel cache clear path documented"
else
    log "❌ Vercel cache clear path not documented"
fi

# 5. Smoke Tests
log ""
log "🧪 5. SMOKE TESTS"
log "----------------"

# Test health endpoint
log "🔍 Testing health endpoint..."
if curl -fsSL "$BACKEND_URL/api/health" >/dev/null 2>&1; then
    log "✅ Health endpoint responding"
else
    log "❌ Health endpoint not responding"
fi

# Test frontend
log "🔍 Testing frontend..."
if curl -fsSL "$FRONTEND_URL" >/dev/null 2>&1; then
    log "✅ Frontend responding"
else
    log "❌ Frontend not responding"
fi

# Test OAuth endpoints (without auth)
log "🔍 Testing OAuth endpoints..."
if curl -fsSL "$BACKEND_URL/api/oauth/token-status" >/dev/null 2>&1; then
    log "✅ OAuth endpoints responding"
else
    log "❌ OAuth endpoints not responding"
fi

# Test automation safety endpoints
log "🔍 Testing automation safety endpoints..."
if curl -fsSL "$BACKEND_URL/api/automation/safety-status" >/dev/null 2>&1; then
    log "✅ Automation safety endpoints responding"
else
    log "❌ Automation safety endpoints not responding"
fi

# 6. Security Checks
log ""
log "🔒 6. SECURITY CHECKS"
log "--------------------"

# Check for secrets in code
log "🔍 Checking for secrets in code..."
if ! grep -r "sk-" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=__pycache__ >/dev/null 2>&1; then
    log "✅ No API keys found in code"
else
    log "❌ Potential API keys found in code"
fi

# Check file permissions
log "🔍 Checking file permissions..."
if find . -name "*.py" -not -perm 644 | wc -l | grep -q "^0$"; then
    log "✅ Python file permissions correct"
else
    log "❌ Some Python files have incorrect permissions"
fi

# Check for CSP headers (would need to be implemented)
log "🔍 Checking CSP headers..."
log "⚠️  CSP headers need to be implemented"

# Summary
log ""
log "📊 PRE-FLIGHT CHECKLIST SUMMARY"
log "==============================="

# Count passed checks
passed_checks=$(grep -c "✅" "$LOG_FILE" || echo "0")
total_checks=$(grep -c "🔍 Checking:" "$LOG_FILE" || echo "0")

log "Passed: $passed_checks / $total_checks checks"

if [ "$passed_checks" -eq "$total_checks" ]; then
    log "🎉 ALL CHECKS PASSED - READY FOR DEPLOYMENT!"
    exit 0
else
    log "❌ SOME CHECKS FAILED - REVIEW BEFORE DEPLOYMENT"
    exit 1
fi
