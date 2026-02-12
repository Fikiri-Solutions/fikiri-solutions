#!/bin/bash
# Execute Git History Cleanup (Non-Interactive)
# Removes .env files from entire Git history
# USE WITH CAUTION - This rewrites history!

set -e

echo "🔍 Git History Cleanup - Removing Sensitive Files"
echo "=================================================="
echo ""

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a Git repository"
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"
echo ""

# Verify remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo "❌ No remote 'origin' found"
    exit 1
fi

echo "🌐 Remote: $REMOTE_URL"
echo ""

echo "🧹 Starting cleanup..."
echo "Removing from ALL Git history:"
echo "  - .env"
echo "  - .env.local"
echo "  - .env.production"
echo ""

# Use git-filter-repo to remove the files
git filter-repo --invert-paths \
    --path .env \
    --path .env.local \
    --path .env.production \
    --force

echo ""
echo "✅ Cleanup complete!"
echo ""

