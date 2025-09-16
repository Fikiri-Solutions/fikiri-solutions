#!/usr/bin/env python3
"""
Fikiri Solutions - Simple MCP Server
Simplified MCP server for Cursor integration.
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
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Call a tool."""
    project_dir = Path(__file__).parent
    
    try:
        if name == "check_status":
            result = await run_command("status", project_dir)
        elif name == "test_services":
            result = await run_command("test", project_dir)
        elif name == "crm_stats":
            result = await run_command("crm", project_dir)
        else:
            result = {"stdout": f"Unknown tool: {name}", "stderr": "", "returncode": 1}
        
        return [TextContent(type="text", text=result["stdout"])]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def run_command(command: str, project_dir: Path):
    """Run a command using main_minimal.py."""
    try:
        process = await asyncio.create_subprocess_exec(
            "/opt/anaconda3/bin/python", "main_minimal.py", command,
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
                capabilities=server.get_capabilities()
            )
        )

if __name__ == "__main__":
    asyncio.run(main())



