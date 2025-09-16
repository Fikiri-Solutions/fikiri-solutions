#!/usr/bin/env python3
"""
Fikiri Solutions - Official MCP Server
Using the official MCP library for proper Cursor integration.
"""

import asyncio
import subprocess
from pathlib import Path
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create the server
server = Server("fikiri-solutions")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="setup_auth",
            description="Setup Gmail OAuth authentication for the first time.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="check_status", 
            description="Check system status and authentication.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="test_services",
            description="Test all core services and functionality.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="crm_stats",
            description="Show CRM statistics and lead information.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="process_emails",
            description="Process email queue with AI responses and CRM updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_emails": {
                        "type": "integer",
                        "description": "Maximum number of emails to process",
                        "default": 5
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Call a tool."""
    project_dir = Path(__file__).parent
    
    try:
        if name == "setup_auth":
            result = await run_command("setup", project_dir)
        elif name == "check_status":
            result = await run_command("status", project_dir)
        elif name == "test_services":
            result = await run_command("test", project_dir)
        elif name == "crm_stats":
            result = await run_command("crm", project_dir)
        elif name == "process_emails":
            max_emails = arguments.get("max_emails", 5)
            result = await run_command("process", project_dir, ["--max", str(max_emails)])
        else:
            result = {"stdout": f"Unknown tool: {name}", "stderr": "", "returncode": 1}
        
        return [TextContent(type="text", text=result["stdout"])]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def run_command(command: str, project_dir: Path, extra_args: list = None):
    """Run a command using main_minimal.py."""
    try:
        args = ["/opt/anaconda3/bin/python", "main_minimal.py", command]
        if extra_args:
            args.extend(extra_args)
        
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=project_dir,
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

async def main():
    """Main entry point."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fikiri-solutions",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())



