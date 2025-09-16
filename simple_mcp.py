#!/usr/bin/env python3
"""
Simple MCP Server for Fikiri Solutions
"""

import sys
import json
import subprocess
from pathlib import Path

def main():
    """Simple MCP server that just runs commands."""
    project_dir = Path(__file__).parent
    
    # Simple test - just run status command
    try:
        result = subprocess.run([
            "/opt/anaconda3/bin/python", 
            "main_minimal.py", 
            "status"
        ], cwd=project_dir, capture_output=True, text=True)
        
        print("MCP Server running...")
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())



