#!/bin/bash
# Check Git history for potential secret leaks

echo "🔍 Checking Git history for secrets..."
echo ""

# Check if .env files were ever committed
echo "1. Checking if .env files were committed:"
git log --all --full-history --source --oneline -- ".env" ".env.local" ".env.production" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "   ⚠️  WARNING: .env files found in Git history!"
else
    echo "   ✅ No .env files found in Git history"
fi

echo ""

# Check for common secret patterns in commits
echo "2. Checking for secret patterns in commit messages:"
git log --all --grep="secret\|key\|token\|password\|api" --oneline 2>/dev/null | head -10

echo ""

# Check for large files that might contain secrets
echo "3. Checking for large files in history:"
git rev-list --objects --all | \
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
    awk '/^blob/ {print substr($0,6)}' | \
    sort --numeric-sort --key=2 | \
    tail -10

echo ""

# Check current tracked files
echo "4. Checking currently tracked files for secrets:"
git ls-files | grep -E "\.env$|secret|key|token" | grep -v node_modules

echo ""
echo "✅ Git history check complete!"
echo ""
echo "If secrets were found, follow SECURITY_ROTATION_PLAN.md"

