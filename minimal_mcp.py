#!/usr/bin/env python3
"""
Minimal MCP server for testing Cursor integration
"""
import json
import sys

def main():
    print("🚀 Minimal MCP server starting...", file=sys.stderr)
    
    # Read from stdin line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            
            print(f"📥 Received request: {method}", file=sys.stderr)
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "minimal-mcp", "version": "1.0.0"}
                    }
                }
            elif method == "notifications/initialized":
                # No response needed for notifications
                continue
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "hello_world",
                                "description": "A simple hello world tool",
                                "input_schema": {
                                    "type": "object",
                                    "properties": {},
                                    "additionalProperties": False
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                tool_name = request.get("params", {}).get("name")
                if tool_name == "hello_world":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Hello from minimal MCP server! 🎉"
                                }
                            ]
                        }
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
            
            print(f"📤 Sending response: {json.dumps(response, indent=2)}", file=sys.stderr)
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}", file=sys.stderr)
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {e}"}
            }
            print(json.dumps(response), flush=True)

if __name__ == "__main__":
    main()
