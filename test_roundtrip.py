#!/usr/bin/env python3
"""
Round-trip smoke tests for MCP server.
"""

import json
import subprocess
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def rpc(req: dict) -> dict:
    """Send RPC request to server and return response."""
    p = subprocess.run(
        [sys.executable, "-m", "server"],
        input=json.dumps(req).encode(),
        capture_output=True,
        check=True
    )
    line = p.stdout.decode().splitlines()[0]
    return json.loads(line)


def test_tools_list_has_tools():
    """Test that tools/list returns a list with tools."""
    res = rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    tools = res["result"]["tools"]
    assert isinstance(tools, list) and len(tools) >= 2
    print("✅ tools/list returns tools")


def test_create_auth_link_returns_content():
    """Test that create_data_auth_link returns proper content format."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "create_data_auth_link",
            "arguments": {}
        }
    })
    content = res["result"]["content"]
    assert isinstance(content, list) and content and content[0]["type"] == "text"
    print("✅ create_data_auth_link returns content")


def test_get_accounts_returns_content():
    """Test that get_accounts returns proper content format."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_accounts",
            "arguments": {}
        }
    })
    content = res["result"]["content"]
    assert isinstance(content, list) and content and content[0]["type"] == "text"
    print("✅ get_accounts returns content")


def test_get_transactions_returns_content():
    """Test that get_transactions returns proper content format."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        }
    })
    content = res["result"]["content"]
    assert isinstance(content, list) and content and content[0]["type"] == "text"
    print("✅ get_transactions returns content")


def test_error_handling():
    """Test that invalid requests return proper error format."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool",
            "arguments": {}
        }
    })
    assert "error" in res
    print("✅ Error handling works")


if __name__ == "__main__":
    print("🧪 Running round-trip smoke tests...\n")

    try:
        test_tools_list_has_tools()
        test_create_auth_link_returns_content()
        test_get_accounts_returns_content()
        test_get_transactions_returns_content()
        test_error_handling()

        print("\n🎉 All round-trip tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)
