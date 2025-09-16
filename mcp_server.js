const { spawn } = require('child_process');
const path = require('path');

// Simple MCP server
let requestId = 0;

process.stdin.on('data', (data) => {
    const lines = data.toString().split('\n');
    
    for (const line of lines) {
        if (!line.trim()) continue;
        
        try {
            const request = JSON.parse(line);
            const method = request.method;
            const id = request.id || ++requestId;
            
            if (method === 'initialize') {
                const response = {
                    jsonrpc: '2.0',
                    id: id,
                    result: {
                        protocolVersion: '2024-11-05',
                        capabilities: {
                            tools: {}
                        },
                        serverInfo: {
                            name: 'fikiri-solutions',
                            version: '1.0.0'
                        }
                    }
                };
                console.log(JSON.stringify(response));
            } else if (method === 'tools/list') {
                const response = {
                    jsonrpc: '2.0',
                    id: id,
                    result: {
                        tools: [
                            {
                                name: 'check_status',
                                description: 'Check system status and authentication',
                                inputSchema: {
                                    type: 'object',
                                    properties: {}
                                }
                            },
                            {
                                name: 'crm_stats',
                                description: 'Show CRM statistics and lead information',
                                inputSchema: {
                                    type: 'object',
                                    properties: {}
                                }
                            }
                        ]
                    }
                };
                console.log(JSON.stringify(response));
            } else if (method === 'tools/call') {
                const toolName = request.params.name;
                const projectDir = path.dirname(__filename);
                
                let command, args;
                if (toolName === 'check_status') {
                    command = '/opt/anaconda3/bin/python';
                    args = ['main_minimal.py', 'status'];
                } else if (toolName === 'crm_stats') {
                    command = '/opt/anaconda3/bin/python';
                    args = ['main_minimal.py', 'crm'];
                } else {
                    const response = {
                        jsonrpc: '2.0',
                        id: id,
                        result: {
                            content: [{
                                type: 'text',
                                text: `Unknown tool: ${toolName}`
                            }]
                        }
                    };
                    console.log(JSON.stringify(response));
                    continue;
                }
                
                const child = spawn(command, args, {
                    cwd: projectDir,
                    stdio: ['ignore', 'pipe', 'pipe']
                });
                
                let stdout = '';
                let stderr = '';
                
                child.stdout.on('data', (data) => {
                    stdout += data.toString();
                });
                
                child.stderr.on('data', (data) => {
                    stderr += data.toString();
                });
                
                child.on('close', (code) => {
                    const response = {
                        jsonrpc: '2.0',
                        id: id,
                        result: {
                            content: [{
                                type: 'text',
                                text: stdout || stderr
                            }]
                        }
                    };
                    console.log(JSON.stringify(response));
                });
            }
        } catch (error) {
            const response = {
                jsonrpc: '2.0',
                id: null,
                error: {
                    code: -32603,
                    message: `Internal error: ${error.message}`
                }
            };
            console.log(JSON.stringify(response));
        }
    }
});

