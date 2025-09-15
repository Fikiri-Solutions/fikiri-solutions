#!/usr/bin/env python3
"""
Fikiri Solutions - Python Code Quality Tools
Black formatting, Flake8 linting, and automated code quality checks.
"""

import subprocess
import sys
import os
from pathlib import Path

class CodeQualityChecker:
    """Python code quality checker using Black and Flake8."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.python_files = self._find_python_files()
        
    def _find_python_files(self) -> list:
        """Find all Python files in the project."""
        python_files = []
        
        # Directories to check
        check_dirs = ['core', 'scripts', 'tests']
        
        for dir_name in check_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                python_files.extend(dir_path.glob('**/*.py'))
        
        # Also check root Python files
        python_files.extend(self.project_root.glob('*.py'))
        
        return python_files
    
    def run_black_format_check(self) -> bool:
        """Run Black format check (dry run)."""
        print("🎨 Running Black format check...")
        
        try:
            cmd = ['black', '--check', '--diff'] + [str(f) for f in self.python_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ All files are properly formatted with Black")
                return True
            else:
                print("❌ Black formatting issues found:")
                print(result.stdout)
                return False
                
        except FileNotFoundError:
            print("⚠️  Black not installed. Install with: pip install black")
            return False
        except Exception as e:
            print(f"❌ Error running Black: {e}")
            return False
    
    def run_black_format(self) -> bool:
        """Run Black formatting (modify files)."""
        print("🎨 Running Black formatting...")
        
        try:
            cmd = ['black'] + [str(f) for f in self.python_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Files formatted with Black")
                print(result.stdout)
                return True
            else:
                print("❌ Black formatting failed:")
                print(result.stderr)
                return False
                
        except FileNotFoundError:
            print("⚠️  Black not installed. Install with: pip install black")
            return False
        except Exception as e:
            print(f"❌ Error running Black: {e}")
            return False
    
    def run_flake8_lint(self) -> bool:
        """Run Flake8 linting."""
        print("🔍 Running Flake8 linting...")
        
        try:
            cmd = ['flake8'] + [str(f) for f in self.python_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ No Flake8 issues found")
                return True
            else:
                print("❌ Flake8 issues found:")
                print(result.stdout)
                return False
                
        except FileNotFoundError:
            print("⚠️  Flake8 not installed. Install with: pip install flake8")
            return False
        except Exception as e:
            print(f"❌ Error running Flake8: {e}")
            return False
    
    def run_mypy_type_check(self) -> bool:
        """Run MyPy type checking."""
        print("🔬 Running MyPy type checking...")
        
        try:
            cmd = ['mypy'] + [str(f) for f in self.python_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ No MyPy type issues found")
                return True
            else:
                print("❌ MyPy type issues found:")
                print(result.stdout)
                return False
                
        except FileNotFoundError:
            print("⚠️  MyPy not installed. Install with: pip install mypy")
            return False
        except Exception as e:
            print(f"❌ Error running MyPy: {e}")
            return False
    
    def run_bandit_security_check(self) -> bool:
        """Run Bandit security check."""
        print("🔒 Running Bandit security check...")
        
        try:
            cmd = ['bandit', '-r'] + [str(f) for f in self.python_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ No Bandit security issues found")
                return True
            else:
                print("❌ Bandit security issues found:")
                print(result.stdout)
                return False
                
        except FileNotFoundError:
            print("⚠️  Bandit not installed. Install with: pip install bandit")
            return False
        except Exception as e:
            print(f"❌ Error running Bandit: {e}")
            return False
    
    def run_all_checks(self, fix_formatting: bool = False) -> bool:
        """Run all code quality checks."""
        print("🧪 Running All Code Quality Checks...")
        print("=" * 50)
        
        all_passed = True
        
        # Format check/format
        if fix_formatting:
            if not self.run_black_format():
                all_passed = False
        else:
            if not self.run_black_format_check():
                all_passed = False
        
        # Linting
        if not self.run_flake8_lint():
            all_passed = False
        
        # Type checking
        if not self.run_mypy_type_check():
            all_passed = False
        
        # Security check
        if not self.run_bandit_security_check():
            all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All code quality checks passed!")
        else:
            print("❌ Some code quality checks failed!")
        
        return all_passed
    
    def install_tools(self):
        """Install required code quality tools."""
        print("📦 Installing Python code quality tools...")
        
        tools = [
            'black',
            'flake8',
            'mypy',
            'bandit',
            'isort'
        ]
        
        for tool in tools:
            try:
                print(f"Installing {tool}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', tool], 
                             check=True, capture_output=True)
                print(f"✅ {tool} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {tool}: {e}")

def create_flake8_config():
    """Create .flake8 configuration file."""
    config = """[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    .env,
    build,
    dist,
    *.egg-info
per-file-ignores =
    __init__.py:F401
"""
    
    with open('.flake8', 'w') as f:
        f.write(config)
    
    print("✅ Created .flake8 configuration file")

def create_mypy_config():
    """Create mypy.ini configuration file."""
    config = """[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-tests.*]
disallow_untyped_defs = False
"""
    
    with open('mypy.ini', 'w') as f:
        f.write(config)
    
    print("✅ Created mypy.ini configuration file")

def create_pyproject_toml():
    """Create pyproject.toml for Black configuration."""
    config = """[tool.black]
line-length = 88
target-version = ['py38']
include = '\\.pyi?$'
extend-exclude = '''
/(
  # directories
  \\.eggs
  | \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
"""
    
    with open('pyproject.toml', 'w') as f:
        f.write(config)
    
    print("✅ Created pyproject.toml configuration file")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fikiri Solutions Code Quality Checker")
    parser.add_argument("--check", action="store_true", help="Run format check only")
    parser.add_argument("--format", action="store_true", help="Format code with Black")
    parser.add_argument("--lint", action="store_true", help="Run Flake8 linting")
    parser.add_argument("--type-check", action="store_true", help="Run MyPy type checking")
    parser.add_argument("--security", action="store_true", help="Run Bandit security check")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--install", action="store_true", help="Install required tools")
    parser.add_argument("--setup", action="store_true", help="Setup configuration files")
    
    args = parser.parse_args()
    
    checker = CodeQualityChecker()
    
    if args.setup:
        create_flake8_config()
        create_mypy_config()
        create_pyproject_toml()
        return
    
    if args.install:
        checker.install_tools()
        return
    
    if args.all:
        success = checker.run_all_checks()
    elif args.format:
        success = checker.run_black_format()
    elif args.check:
        success = checker.run_black_format_check()
    elif args.lint:
        success = checker.run_flake8_lint()
    elif args.type_check:
        success = checker.run_mypy_type_check()
    elif args.security:
        success = checker.run_bandit_security_check()
    else:
        # Default: run all checks
        success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
