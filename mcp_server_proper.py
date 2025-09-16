#!/usr/bin/env python3
"""
Fikiri Solutions - MCP Server
Implements the Model Context Protocol for Cursor integration.
"""

import sys
import json
import subprocess
import asyncio
from pathlib import Path

class FikiriMCPServer:
    """MCP Server for Fikiri Solutions."""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.tools = {
            "setup_auth": {
                "name": "setup_auth",
                "description": "Setup Gmail OAuth authentication for the first time.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            "check_status": {
                "name": "check_status", 
                "description": "Check system status and authentication.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            "test_services": {
                "name": "test_services",
                "description": "Test all core services and functionality.",
                "inputSchema": {
                    "type": "object", 
                    "properties": {}
                }
            },
            "crm_stats": {
                "name": "crm_stats",
                "description": "Show CRM statistics and lead information.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            "process_emails": {
                "name": "process_emails",
                "description": "Process email queue with AI responses and CRM updates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_emails": {
                            "type": "integer",
                            "description": "Maximum number of emails to process",
                            "default": 5
                        }
                    }
                }
            }
        }
    
    async def run_command(self, command, args=None):
        """Run a command using main_minimal.py."""
        try:
            cmd_args = ["/opt/anaconda3/bin/python", "main_minimal.py", command]
            if args:
                cmd_args.extend(args)
            
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    async def handle_request(self, request):
        """Handle MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
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
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": list(self.tools.values())
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "setup_auth":
                result = await self.run_command("setup")
            elif tool_name == "check_status":
                result = await self.run_command("status")
            elif tool_name == "test_services":
                result = await self.run_command("test")
            elif tool_name == "crm_stats":
                result = await self.run_command("crm")
            elif tool_name == "process_emails":
                max_emails = arguments.get("max_emails", 5)
                result = await self.run_command("process", ["--max", str(max_emails)])
            else:
                result = {"stdout": f"Unknown tool: {tool_name}", "stderr": "", "returncode": 1}
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
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
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def run(self):
        """Run the MCP server."""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                print(json.dumps(response))
                sys.stdout.flush()
                
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

async def main():
    """Main entry point."""
    server = FikiriMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())



