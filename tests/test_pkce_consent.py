#!/usr/bin/env python3
"""
Tests for PKCE and consent ledger functionality.
"""

import json
import subprocess
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_list_consents_returns_content():
    """Test that list_consents returns proper content format."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_consents",
            "arguments": {}
        }
    })
    content = res["result"]["content"]
    assert isinstance(content, list) and content and content[0]["type"] == "text"
    print("✅ list_consents returns content")


def test_complete_code_exchange_state_mismatch():
    """Test that complete_code_exchange returns error for invalid state."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "complete_code_exchange",
            "arguments": {
                "code": "test_code",
                "state": "invalid_state"
            }
        }
    })

    # Should return error content for invalid state
    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)

    assert "error" in result_data
    assert result_data["code"] == -32602
    print("✅ complete_code_exchange handles state mismatch")


def test_create_auth_link_includes_pkce():
    """Test that create_data_auth_link includes PKCE parameters."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "create_data_auth_link",
            "arguments": {}
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)

    # Should include state and code_challenge
    if "auth_url" in result_data:
        assert "state" in result_data
        assert "code_challenge" in result_data.get("auth_url", "")
        print("✅ create_data_auth_link includes PKCE parameters")
    else:
        # Mock mode - just check it returns something
        assert "mock_url" in result_data
        print("✅ create_data_auth_link returns mock URL (no credentials)")


def test_tools_list_includes_new_tools():
    """Test that tools/list includes the new PKCE and consent tools."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/list",
        "params": {}
    })

    tools = res["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should include the new tools
    assert "complete_code_exchange" in tool_names
    assert "list_consents" in tool_names

    # Should still include legacy exchange_code
    assert "exchange_code" in tool_names

    print("✅ Tools list includes new PKCE and consent tools")


if __name__ == "__main__":
    print("🧪 Running PKCE and consent tests...\n")

    try:
        test_list_consents_returns_content()
        test_complete_code_exchange_state_mismatch()
        test_create_auth_link_includes_pkce()
        test_tools_list_includes_new_tools()

        print("\n🎉 All PKCE and consent tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
