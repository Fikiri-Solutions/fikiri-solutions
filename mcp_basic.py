#!/usr/bin/env python3
"""
Fikiri Solutions - Basic MCP Server
Simple working MCP server for Cursor.
"""

import sys
import json
import subprocess
from pathlib import Path

def main():
    """Basic MCP server that responds to Cursor."""
    project_dir = Path(__file__).parent
    
    # Simple JSON-RPC handler
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
                
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                request_id = request.get("id")
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "fikiri-solutions",
                                "version": "1.0.0"
                            }
                        }
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "check_status",
                                    "description": "Check system status and authentication.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                },
                                {
                                    "name": "test_services",
                                    "description": "Test all core services and functionality.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                },
                                {
                                    "name": "crm_stats",
                                    "description": "Show CRM statistics and lead information.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                }
                            ]
                        }
                    }
                elif method == "tools/call":
                    tool_name = request.get("params", {}).get("name")
                    
                    if tool_name == "check_status":
                        result = run_command("status", project_dir)
                    elif tool_name == "test_services":
                        result = run_command("test", project_dir)
                    elif tool_name == "crm_stats":
                        result = run_command("crm", project_dir)
                    else:
                        result = {"stdout": f"Unknown tool: {tool_name}", "returncode": 1}
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result["stdout"]
                                }
                            ]
                        }
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        pass

def run_command(command: str, project_dir: Path):
    """Run a command using main_minimal.py."""
    try:
        result = subprocess.run([
            "/opt/anaconda3/bin/python", 
            "main_minimal.py", 
            command
        ], cwd=project_dir, capture_output=True, text=True)
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": 1
        }

if __name__ == "__main__":
    main()



