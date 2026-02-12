#!/bin/bash
# Quick syntax check for all Python files
# Usage: ./scripts/check_all.sh

echo "🔍 Checking Python syntax and logic..."
python3 scripts/check_syntax.py --all

echo ""
echo "🔍 Checking TypeScript syntax..."
cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -30
cd ..

echo ""
echo "✅ All checks complete"

