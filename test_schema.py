#!/usr/bin/env python3
"""
Lightweight tests to catch MCP schema regressions.
"""

import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import build_tools_list
from validate import validate_tools


def test_tools_are_mcp_shaped():
    """Test that all tools conform to MCP spec requirements."""
    tools = build_tools_list()

    print(f"Testing {len(tools)} tools for MCP compliance...")

    # Validate using our validator
    try:
        validated_tools = validate_tools(tools)
        print("✅ All tools passed validation")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
        return False

    # Additional checks
    for i, tool in enumerate(tools):
        tool_name = tool.get("name", f"tool_{i}")

        # Check camelCase keys
        if "input_schema" in tool:
            print(f"❌ Tool '{tool_name}' uses snake_case 'input_schema' instead of 'inputSchema'")
            return False

        if "output_schema" in tool:
            print(f"❌ Tool '{tool_name}' uses snake_case 'output_schema' instead of 'outputSchema'")
            return False

        # Check required keys
        required_keys = ["name", "description", "inputSchema", "outputSchema"]
        for key in required_keys:
            if key not in tool:
                print(f"❌ Tool '{tool_name}' missing required key: {key}")
                return False

        # Check outputSchema structure
        oschema = tool["outputSchema"]
        if not isinstance(oschema, dict):
            print(f"❌ Tool '{tool_name}' outputSchema must be an object")
            return False

        if "properties" not in oschema:
            print(f"❌ Tool '{tool_name}' outputSchema missing 'properties'")
            return False

        if "content" not in oschema["properties"]:
            print(f"❌ Tool '{tool_name}' outputSchema.properties missing 'content'")
            return False

        content_schema = oschema["properties"]["content"]
        if content_schema.get("type") != "array":
            print(f"❌ Tool '{tool_name}' outputSchema.properties.content must be an array")
            return False

    print("✅ All tools conform to MCP spec")
    return True


def test_tool_names():
    """Test that tool names are valid."""
    tools = build_tools_list()
    expected_tools = ["create_data_auth_link", "exchange_code", "get_accounts", "get_transactions"]

    actual_names = [tool["name"] for tool in tools]

    for expected in expected_tools:
        if expected not in actual_names:
            print(f"❌ Missing expected tool: {expected}")
            return False

    print(f"✅ Found all expected tools: {actual_names}")
    return True


if __name__ == "__main__":
    print("🧪 Running MCP schema compliance tests...\n")

    all_passed = True
    all_passed &= test_tools_are_mcp_shaped()
    all_passed &= test_tool_names()

    if all_passed:
        print("\n🎉 All tests passed! MCP server is ready for Cursor.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Fix the issues above.")
        sys.exit(1)
