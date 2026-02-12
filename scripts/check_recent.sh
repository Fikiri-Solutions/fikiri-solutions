#!/bin/bash
# Check recently modified files
# Usage: ./scripts/check_recent.sh

echo "🔍 Checking recently modified Python files..."

# Find Python files modified in last hour
find . -name "*.py" -type f -mmin -60 ! -path "*/venv/*" ! -path "*/.venv/*" ! -path "*/__pycache__/*" ! -path "*/.git/*" | while read file; do
    python3 scripts/check_syntax.py "$file"
done

echo ""
echo "✅ Recent file checks complete"

