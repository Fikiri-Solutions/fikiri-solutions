#!/bin/bash
# Simple MCP server using shell script

PROJECT_DIR="/Users/mac/Downloads/Fikiri"
cd "$PROJECT_DIR"

# Simple JSON-RPC handler
while read -r line; do
    if [[ -z "$line" ]]; then
        continue
    fi
    
    # Parse the request
    method=$(echo "$line" | jq -r '.method // empty')
    id=$(echo "$line" | jq -r '.id // empty')
    
    if [[ "$method" == "initialize" ]]; then
        echo "{\"jsonrpc\": \"2.0\", \"id\": $id, \"result\": {\"protocolVersion\": \"2024-11-05\", \"capabilities\": {\"tools\": {}}, \"serverInfo\": {\"name\": \"fikiri-solutions\", \"version\": \"1.0.0\"}}}"
    elif [[ "$method" == "tools/list" ]]; then
        echo "{\"jsonrpc\": \"2.0\", \"id\": $id, \"result\": {\"tools\": [{\"name\": \"check_status\", \"description\": \"Check system status\", \"inputSchema\": {\"type\": \"object\", \"properties\": {}}}, {\"name\": \"crm_stats\", \"description\": \"Show CRM stats\", \"inputSchema\": {\"type\": \"object\", \"properties\": {}}}]}}"
    elif [[ "$method" == "tools/call" ]]; then
        tool_name=$(echo "$line" | jq -r '.params.name // empty')
        if [[ "$tool_name" == "check_status" ]]; then
            result=$(/opt/anaconda3/bin/python main_minimal.py status 2>&1)
            echo "{\"jsonrpc\": \"2.0\", \"id\": $id, \"result\": {\"content\": [{\"type\": \"text\", \"text\": \"$result\"}]}}"
        elif [[ "$tool_name" == "crm_stats" ]]; then
            result=$(/opt/anaconda3/bin/python main_minimal.py crm 2>&1)
            echo "{\"jsonrpc\": \"2.0\", \"id\": $id, \"result\": {\"content\": [{\"type\": \"text\", \"text\": \"$result\"}]}}"
        fi
    fi
done

