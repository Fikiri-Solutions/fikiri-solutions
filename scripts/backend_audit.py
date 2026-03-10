#!/usr/bin/env python3
"""
Backend Code Audit Script
Checks for common coding errors: missing imports, undefined variables, type issues
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Common typing imports that might be missing
TYPING_IMPORTS = {'List', 'Dict', 'Optional', 'Union', 'Tuple', 'Callable', 'Any', 'Set'}

# Standard library modules commonly used
STD_LIB_MODULES = {
    'json', 'datetime', 'logging', 'hashlib', 'secrets', 'time', 'os', 'sys',
    'uuid', 'base64', 'hmac', 'threading', 'collections', 'functools', 'contextlib'
}

class CodeAuditor:
    def __init__(self):
        self.errors: List[Dict[str, any]] = []
        self.warnings: List[Dict[str, any]] = []
        
    def audit_file(self, filepath: str) -> Tuple[List[Dict], List[Dict]]:
        """Audit a single Python file"""
        file_errors = []
        file_warnings = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=filepath)
        except SyntaxError as e:
            file_errors.append({
                'file': filepath,
                'line': e.lineno,
                'type': 'SyntaxError',
                'message': str(e)
            })
            return file_errors, file_warnings
        except Exception as e:
            file_warnings.append({
                'file': filepath,
                'type': 'ParseError',
                'message': f"Could not parse file: {e}"
            })
            return file_errors, file_warnings
        
        # Check imports
        imports = self._get_imports(tree)
        used_types = self._get_used_types(tree, content)
        used_modules = self._get_used_modules(content)
        
        # Check for missing typing imports
        missing_typing = used_types - imports.get('typing', set())
        if missing_typing:
            file_errors.append({
                'file': filepath,
                'line': 1,
                'type': 'MissingImport',
                'message': f"Missing typing imports: {', '.join(sorted(missing_typing))}",
                'fix': f"Add to imports: from typing import {', '.join(sorted(missing_typing))}"
            })
        
        # Check for missing standard library imports
        missing_stdlib = used_modules - imports.get('stdlib', set()) - {'builtins'}
        if missing_stdlib:
            for module in missing_stdlib:
                if module in STD_LIB_MODULES:
                    file_warnings.append({
                        'file': filepath,
                        'line': 1,
                        'type': 'PossibleMissingImport',
                        'message': f"Module '{module}' used but not imported",
                        'fix': f"Add: import {module}"
                    })
        
        # Check for undefined names (basic check)
        undefined = self._check_undefined_names(tree, imports)
        if undefined:
            for name, line in undefined:
                file_warnings.append({
                    'file': filepath,
                    'line': line,
                    'type': 'PossibleUndefined',
                    'message': f"Possible undefined name: {name}",
                })
        
        return file_errors, file_warnings
    
    def _get_imports(self, tree: ast.AST) -> Dict[str, Set[str]]:
        """Extract all imports from AST"""
        imports = {'typing': set(), 'stdlib': set(), 'third_party': set()}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports['stdlib'].add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name == 'typing':
                        for alias in node.names:
                            imports['typing'].add(alias.name)
                    elif module_name in STD_LIB_MODULES:
                        imports['stdlib'].add(module_name)
                    else:
                        imports['third_party'].add(module_name)
        
        return imports
    
    def _get_used_types(self, tree: ast.AST, content: str) -> Set[str]:
        """Find used type annotations"""
        used_types = set()
        
        # Check function annotations
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.returns:
                    used_types.update(self._extract_types_from_annotation(node.returns))
                for arg in node.args.args:
                    if arg.annotation:
                        used_types.update(self._extract_types_from_annotation(arg.annotation))
        
        # Check variable annotations
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                if node.annotation:
                    used_types.update(self._extract_types_from_annotation(node.annotation))
        
        return used_types & TYPING_IMPORTS
    
    def _extract_types_from_annotation(self, node: ast.AST) -> Set[str]:
        """Extract type names from annotation node"""
        types = set()
        
        if isinstance(node, ast.Name):
            types.add(node.id)
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                types.add(node.value.id)
            # Recursively check nested types
            if isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Tuple):
                for elt in node.slice.value.elts:
                    types.update(self._extract_types_from_annotation(elt))
            elif hasattr(node.slice, 'value'):
                types.update(self._extract_types_from_annotation(node.slice.value))
        
        return types
    
    def _get_used_modules(self, content: str) -> Set[str]:
        """Find modules used in code (basic pattern matching)"""
        used = set()
        
        # Pattern: module.function() or module.attribute
        patterns = [
            r'\b(json|datetime|logging|hashlib|secrets|time|os|sys|uuid|base64|hmac|threading|collections|functools|contextlib)\.',
            r'\b(datetime|timedelta|json|logging|hashlib|secrets)\.',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            used.update(matches)
        
        return used
    
    def _check_undefined_names(self, tree: ast.AST, imports: Dict[str, Set[str]]) -> List[Tuple[str, int]]:
        """Basic check for potentially undefined names"""
        undefined = []
        defined = set()
        
        # Collect defined names
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
        
        # Add imported names
        defined.update(imports['typing'])
        defined.update(imports['stdlib'])
        
        # Check for undefined names in function calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in defined and not node.func.id.startswith('_'):
                        # Skip common builtins
                        if node.func.id not in {'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple'}:
                            undefined.append((node.func.id, node.lineno))
        
        return undefined
    
    def audit_directory(self, directory: str) -> Dict[str, any]:
        """Audit all Python files in directory"""
        all_errors = []
        all_warnings = []
        
        for root, dirs, files in os.walk(directory):
            # Skip virtual environments and test directories
            if 'venv' in root or '.venv' in root or '__pycache__' in root:
                continue
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    errors, warnings = self.audit_file(filepath)
                    all_errors.extend(errors)
                    all_warnings.extend(warnings)
        
        return {
            'errors': all_errors,
            'warnings': all_warnings,
            'error_count': len(all_errors),
            'warning_count': len(all_warnings)
        }

def main():
    """Run audit on core, routes, services directories"""
    auditor = CodeAuditor()
    
    directories = ['core', 'routes', 'services', 'crm']
    results = {}
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"Auditing {directory}/...")
            results[directory] = auditor.audit_directory(directory)
    
    # Print summary
    print("\n" + "="*60)
    print("BACKEND CODE AUDIT SUMMARY")
    print("="*60)
    
    total_errors = 0
    total_warnings = 0
    
    for directory, result in results.items():
        errors = result['errors']
        warnings = result['warnings']
        total_errors += len(errors)
        total_warnings += len(warnings)
        
        print(f"\n{directory}/")
        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        
        if errors:
            print("\n  ERRORS:")
            for error in errors[:10]:  # Show first 10
                print(f"    {error['file']}:{error.get('line', '?')} - {error['type']}: {error['message']}")
                if 'fix' in error:
                    print(f"      Fix: {error['fix']}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more errors")
        
        if warnings:
            print("\n  WARNINGS:")
            for warning in warnings[:5]:  # Show first 5
                print(f"    {warning['file']}:{warning.get('line', '?')} - {warning['type']}: {warning['message']}")
            if len(warnings) > 5:
                print(f"    ... and {len(warnings) - 5} more warnings")
    
    print("\n" + "="*60)
    print(f"TOTAL: {total_errors} errors, {total_warnings} warnings")
    print("="*60)
    
    if total_errors > 0:
        print("\n⚠️  ERRORS FOUND - These need to be fixed!")
        sys.exit(1)
    else:
        print("\n✅ No critical errors found!")
        sys.exit(0)

if __name__ == '__main__':
    main()
