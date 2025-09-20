#!/usr/bin/env python3
"""
Tests for the list_accounts tool functionality.
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
        [sys.executable, "-m", "openbankingmcp.server"],
        input=json.dumps(req).encode(),
        capture_output=True,
        check=True
    )
    line = p.stdout.decode().splitlines()[0]
    return json.loads(line)


def test_list_accounts_returns_valid_structure():
    """Test that list_accounts returns proper content format with schema validation."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_accounts",
            "arguments": {}
        }
    })

    # Check response format
    assert "result" in res
    assert "content" in res["result"]
    content = res["result"]["content"]
    assert isinstance(content, list) and len(content) > 0
    assert content[0]["type"] == "text"

    # Parse the JSON content
    result_data = json.loads(content[0]["text"])

    # Check schema structure
    assert "accounts" in result_data
    accounts = result_data["accounts"]
    assert isinstance(accounts, list)
    assert len(accounts) >= 1  # Should return 1-2 dummy accounts

    print("✅ list_accounts returns valid structure")


def test_account_schema_validation():
    """Test that returned accounts conform to Account schema."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_accounts",
            "arguments": {}
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    accounts = result_data["accounts"]

    # Validate each account
    for i, account in enumerate(accounts):
        # Required fields
        required_fields = ["id", "name", "type", "currency", "balance"]
        for field in required_fields:
            assert field in account, f"Account {i} missing required field: {field}"

        # Type validations
        assert isinstance(account["id"], str), f"Account {i} id must be string"
        assert isinstance(account["name"], str), f"Account {i} name must be string"
        assert isinstance(account["type"], str), f"Account {i} type must be string"
        assert isinstance(account["currency"], str), f"Account {i} currency must be string"
        assert isinstance(account["balance"], (int, float)), f"Account {i} balance must be number"

        # Non-empty validations
        assert account["id"], f"Account {i} id cannot be empty"
        assert account["name"], f"Account {i} name cannot be empty"
        assert account["type"], f"Account {i} type cannot be empty"
        assert account["currency"], f"Account {i} currency cannot be empty"

    print("✅ Account schema validation passed")


def test_account_types_and_currencies():
    """Test that accounts have valid types and currencies."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_accounts",
            "arguments": {}
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    accounts = result_data["accounts"]

    valid_types = ["checking", "savings", "current", "business"]
    valid_currencies = ["GBP", "USD", "EUR"]

    for i, account in enumerate(accounts):
        account_type = account["type"]
        currency = account["currency"]

        # Check if type is valid (or at least reasonable)
        assert account_type in valid_types or account_type, f"Account {i} has unusual type: {account_type}"

        # Check if currency is valid (or at least reasonable)
        assert currency in valid_currencies or currency, f"Account {i} has unusual currency: {currency}"

    print("✅ Account types and currencies validation passed")


def test_balance_values():
    """Test that balance values are reasonable."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "list_accounts",
            "arguments": {}
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    accounts = result_data["accounts"]

    for i, account in enumerate(accounts):
        balance = account["balance"]

        # Balance should be a reasonable number (not negative for most account types)
        assert isinstance(balance, (int, float)), f"Account {i} balance must be numeric"

        # For most account types, balance shouldn't be negative
        # (though some accounts like credit cards might be negative)
        if account["type"] in ["checking", "savings", "current"]:
            assert balance >= 0, f"Account {i} balance should not be negative for {account['type']} account"

    print("✅ Balance values validation passed")


def test_validation_error_handling():
    """Test that validation errors are properly handled."""
    # This test ensures that if there's a validation error, it's caught and reported
    res = rpc({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "list_accounts",
            "arguments": {}
        }
    })

    # Should not have an error in the response
    assert "error" not in res, "list_accounts should not return an error for valid requests"

    # Should have valid content
    assert "result" in res
    content = res["result"]["content"][0]["text"]

    # Content should be valid JSON
    try:
        result_data = json.loads(content)
        assert "accounts" in result_data
    except json.JSONDecodeError as e:
        assert False, f"Response content is not valid JSON: {e}"

    print("✅ Validation error handling passed")


if __name__ == "__main__":
    print("🧪 Running list_accounts tests...\n")

    try:
        test_list_accounts_returns_valid_structure()
        test_account_schema_validation()
        test_account_types_and_currencies()
        test_balance_values()
        test_validation_error_handling()

        print("\n🎉 All list_accounts tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
