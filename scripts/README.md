# Code Quality Checks

Simple syntax and logic checking scripts.

## Quick Check

```bash
# Check specific files
python3 scripts/check_syntax.py file1.py file2.py

# Check all Python files
python3 scripts/check_syntax.py --all

# Check recently modified files
./scripts/check_recent.sh
```

## What It Checks

✅ **Syntax Errors** - Python syntax validation  
✅ **Logic Issues** - Unmatched try/except blocks  
✅ **File Existence** - Missing files  

## Usage After Writing Code

After writing any Python file, run:

```bash
python3 scripts/check_syntax.py path/to/file.py
```

Or check all files:

```bash
python3 scripts/check_syntax.py --all
```

## TypeScript Checks

For frontend files:

```bash
cd frontend && npx tsc --noEmit --skipLibCheck
```

## Integration

These checks run automatically in CI/CD, but you can also run them manually before committing.

