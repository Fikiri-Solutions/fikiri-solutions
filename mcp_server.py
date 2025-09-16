#!/usr/bin/env python3
"""
Fikiri Solutions - MCP Server Wrapper
Simple wrapper to make main_minimal.py work as an MCP server.
"""

import sys
import json
import subprocess
from pathlib import Path

def main():
    """Main MCP server entry point."""
    try:
        # Get the project directory
        project_dir = Path(__file__).parent
        
        # Change to project directory
        import os
        os.chdir(project_dir)
        
        # If no arguments provided, show help
        if len(sys.argv) == 1:
            print("Fikiri Solutions MCP Server")
            print("Available commands: setup, status, test, config, crm, process")
            print("Usage: python mcp_server.py <command>")
            return 0
        
        # Get the command
        command = sys.argv[1]
        
        # Run the command using main_minimal.py
        result = subprocess.run([
            "/opt/anaconda3/bin/python", 
            "main_minimal.py", 
            command
        ], capture_output=True, text=True)
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())



