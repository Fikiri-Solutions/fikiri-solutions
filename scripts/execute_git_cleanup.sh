#!/bin/bash
# Execute Git History Cleanup
# Removes .env files from entire Git history

set -e

echo "🔍 Git History Cleanup - Removing Sensitive Files"
echo "=================================================="
echo ""
echo "⚠️  WARNING: This will rewrite Git history!"
echo "⚠️  All collaborators must re-clone after this operation."
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

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  WARNING: You have uncommitted changes!"
    echo "   These will NOT be affected, but make sure you've committed"
    echo "   or stashed important work before proceeding."
    echo ""
    read -p "Continue anyway? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    echo ""
fi

# Verify remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo "❌ No remote 'origin' found"
    exit 1
fi

echo "🌐 Remote: $REMOTE_URL"
echo ""

# Confirm before proceeding
echo "This will remove the following files from ALL Git history:"
echo "  - .env"
echo "  - .env.local"
echo "  - .env.production"
echo ""
read -p "Are you sure you want to proceed? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🧹 Starting cleanup..."
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
echo "📋 Next steps:"
echo "   1. Verify cleanup: git log --all --full-history --source --oneline -- '.env'"
echo "   2. Force push to remote: git push origin --force --all"
echo "   3. Notify all collaborators to re-clone the repository"
echo ""

