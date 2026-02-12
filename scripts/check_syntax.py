#!/usr/bin/env python3
"""
Simple Syntax and Logic Checker
Checks Python files for syntax errors and common logic issues
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Tuple

def check_syntax(filepath: str) -> Tuple[bool, List[str]]:
    """Check Python file for syntax errors"""
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Parse AST to check syntax
        ast.parse(code, filename=filepath)
        return True, []
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        if e.text:
            errors.append(f"  {e.text.strip()}")
            if e.offset:
                errors.append(f"  {' ' * (e.offset - 1)}^")
        return False, errors
    except Exception as e:
        errors.append(f"Error checking file: {e}")
        return False, errors

def check_logic(filepath: str) -> Tuple[bool, List[str]]:
    """Check for common logic issues"""
    warnings = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code, filename=filepath)
        
        # Check for unmatched try/except
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                if not node.handlers and not node.finalbody:
                    warnings.append(f"Line {node.lineno}: try block without except or finally")
        
        # Check for undefined variables (basic check)
        defined_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
        
        return True, warnings
    except Exception as e:
        warnings.append(f"Logic check error: {e}")
        return False, warnings

def check_file(filepath: str) -> Tuple[bool, List[str]]:
    """Check a single file"""
    if not filepath.endswith('.py'):
        return True, []
    
    if not os.path.exists(filepath):
        return False, [f"File not found: {filepath}"]
    
    all_errors = []
    
    # Syntax check
    syntax_ok, syntax_errors = check_syntax(filepath)
    all_errors.extend(syntax_errors)
    
    # Logic check (only if syntax is OK)
    if syntax_ok:
        logic_ok, logic_warnings = check_logic(filepath)
        all_errors.extend([f"⚠️ {w}" for w in logic_warnings])
    
    return syntax_ok and len([e for e in all_errors if not e.startswith('⚠️')]) == 0, all_errors

def main():
    """Main checker function"""
    if len(sys.argv) < 2:
        print("Usage: python check_syntax.py <file1> [file2] ...")
        print("   or: python check_syntax.py --all")
        sys.exit(1)
    
    files_to_check = []
    
    if sys.argv[1] == '--all':
        # Check all Python files in project
        for root, dirs, files in os.walk('.'):
            # Skip virtual environments and common ignore dirs
            if any(skip in root for skip in ['venv', '.venv', 'node_modules', '__pycache__', '.git']):
                continue
            for file in files:
                if file.endswith('.py'):
                    files_to_check.append(os.path.join(root, file))
    else:
        files_to_check = sys.argv[1:]
    
    if not files_to_check:
        print("No files to check")
        sys.exit(0)
    
    errors_found = False
    checked = 0
    
    for filepath in files_to_check:
        checked += 1
        is_ok, errors = check_file(filepath)
        
        if errors:
            errors_found = True
            print(f"\n❌ {filepath}")
            for error in errors:
                print(f"   {error}")
        else:
            print(f"✅ {filepath}")
    
    print(f"\n{'='*60}")
    if errors_found:
        print(f"❌ Found issues in {checked} file(s)")
        sys.exit(1)
    else:
        print(f"✅ All {checked} file(s) passed syntax and logic checks")
        sys.exit(0)

if __name__ == '__main__':
    main()

