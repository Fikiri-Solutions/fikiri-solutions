#!/bin/bash
# Git History Cleanup Script for Fikiri Solutions
# Removes .env files and secrets from Git history

set -e

echo "🔍 Git History Cleanup for Fikiri Solutions"
echo "============================================"
echo ""
echo "⚠️  WARNING: This will rewrite Git history!"
echo "⚠️  Make sure you have:"
echo "   1. Rotated all secrets (see NEW_SECRETS.txt)"
echo "   2. Updated Render environment variables"
echo "   3. Backed up your repository"
echo "   4. Coordinated with your team"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Checking for cleanup tools..."

# Check for BFG
if command -v bfg &> /dev/null; then
    echo "✅ BFG found - using BFG method"
    METHOD="bfg"
elif command -v git-filter-repo &> /dev/null; then
    echo "✅ git-filter-repo found - using git-filter-repo method"
    METHOD="filter-repo"
else
    echo "❌ No cleanup tools found"
    echo ""
    echo "Please install one of:"
    echo "  - BFG: brew install bfg"
    echo "  - git-filter-repo: pip install git-filter-repo"
    exit 1
fi

echo ""
echo "Step 1: Creating backup..."
BACKUP_DIR="../fikiri-backup-$(date +%Y%m%d-%H%M%S)"
git clone --mirror . "$BACKUP_DIR" 2>/dev/null || echo "Backup created"

echo ""
echo "Step 2: Checking current state..."
ENV_COMMITS=$(git log --all --full-history --source --oneline -- ".env" ".env.local" ".env.production" 2>/dev/null | wc -l | tr -d ' ')
echo "Found $ENV_COMMITS commits with .env files"

if [ "$ENV_COMMITS" -eq 0 ]; then
    echo "✅ No .env files found in history - nothing to clean!"
    exit 0
fi

echo ""
echo "Step 3: Cleaning history using $METHOD..."

if [ "$METHOD" = "bfg" ]; then
    # BFG method
    echo "Creating mirror clone for BFG..."
    MIRROR_DIR="/tmp/fikiri-mirror-$$"
    git clone --mirror . "$MIRROR_DIR"
    cd "$MIRROR_DIR"
    
    echo "Removing .env files from history..."
    bfg --delete-files .env
    bfg --delete-files .env.local
    bfg --delete-files .env.production
    
    echo "Cleaning up..."
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
    
    echo "✅ BFG cleanup complete"
    echo "⚠️  Next steps:"
    echo "   1. Review the cleaned repository in $MIRROR_DIR"
    echo "   2. If satisfied, push: cd $MIRROR_DIR && git push --force"
    echo "   3. Then update your local repo: git fetch && git reset --hard origin/main"
    
elif [ "$METHOD" = "filter-repo" ]; then
    # git-filter-repo method
    echo "Removing .env files from history..."
    git filter-repo --invert-paths --path .env --path .env.local --path .env.production --force
    
    echo "✅ git-filter-repo cleanup complete"
    echo "⚠️  Next steps:"
    echo "   1. Review the changes: git log --oneline"
    echo "   2. If satisfied, push: git push origin --force --all"
    echo "   3. Notify team members to re-clone"
fi

echo ""
echo "Step 4: Verifying cleanup..."
REMAINING=$(git log --all --full-history --source --oneline -- ".env" ".env.local" ".env.production" 2>/dev/null | wc -l | tr -d ' ')

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Verification passed - no .env files in history"
else
    echo "⚠️  Warning: $REMAINING commits still contain .env files"
    echo "   You may need to manually review and clean"
fi

echo ""
echo "============================================"
echo "✅ Cleanup process complete!"
echo ""
echo "📋 Final checklist:"
echo "   [ ] Secrets rotated in all environments"
echo "   [ ] Render environment variables updated"
echo "   [ ] Git history cleaned and verified"
echo "   [ ] Team notified to re-clone repository"
echo "   [ ] Pre-commit hooks installed (optional)"
echo ""

