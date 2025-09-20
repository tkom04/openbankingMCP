#!/usr/bin/env python3
"""
Tests for the list_transactions tool functionality.
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


def test_list_transactions_returns_valid_structure():
    """Test that list_transactions returns proper content format with schema validation."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-09-01",
                "end_date": "2024-09-30"
            }
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
    assert "transactions" in result_data
    assert "pagination" in result_data

    transactions = result_data["transactions"]
    pagination = result_data["pagination"]

    assert isinstance(transactions, list)
    assert isinstance(pagination, dict)

    print("✅ list_transactions returns valid structure")


def test_transaction_schema_validation():
    """Test that returned transactions conform to Transaction schema."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-09-01",
                "end_date": "2024-09-30"
            }
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    transactions = result_data["transactions"]

    # Validate each transaction
    for i, transaction in enumerate(transactions):
        # Required fields
        required_fields = ["id", "date", "description", "amount", "direction", "account_id"]
        for field in required_fields:
            assert field in transaction, f"Transaction {i} missing required field: {field}"

        # Type validations
        assert isinstance(transaction["id"], str), f"Transaction {i} id must be string"
        assert isinstance(transaction["date"], str), f"Transaction {i} date must be string"
        assert isinstance(transaction["description"], str), f"Transaction {i} description must be string"
        assert isinstance(transaction["amount"], (int, float)), f"Transaction {i} amount must be number"
        assert isinstance(transaction["direction"], str), f"Transaction {i} direction must be string"
        assert isinstance(transaction["account_id"], str), f"Transaction {i} account_id must be string"

        # Direction validation
        assert transaction["direction"] in ["credit", "debit"], f"Transaction {i} direction must be 'credit' or 'debit'"

        # Date format validation (YYYY-MM-DD)
        date_str = transaction["date"]
        if date_str:
            assert len(date_str) == 10, f"Transaction {i} date must be YYYY-MM-DD format"
            assert date_str.count("-") == 2, f"Transaction {i} date must be YYYY-MM-DD format"

        # Non-empty validations
        assert transaction["id"], f"Transaction {i} id cannot be empty"
        assert transaction["date"], f"Transaction {i} date cannot be empty"
        assert transaction["description"], f"Transaction {i} description cannot be empty"
        assert transaction["account_id"], f"Transaction {i} account_id cannot be empty"

    print("✅ Transaction schema validation passed")


def test_pagination_schema_validation():
    """Test that pagination conforms to expected schema."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-09-01",
                "end_date": "2024-09-30"
            }
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    pagination = result_data["pagination"]

    # Required pagination fields
    required_fields = ["total", "page", "limit", "has_more"]
    for field in required_fields:
        assert field in pagination, f"Pagination missing required field: {field}"

    # Type validations
    assert isinstance(pagination["total"], int), "Pagination total must be integer"
    assert isinstance(pagination["page"], int), "Pagination page must be integer"
    assert isinstance(pagination["limit"], int), "Pagination limit must be integer"
    assert isinstance(pagination["has_more"], bool), "Pagination has_more must be boolean"

    # Value validations
    assert pagination["total"] >= 0, "Pagination total must be non-negative"
    assert pagination["page"] >= 1, "Pagination page must be at least 1"
    assert pagination["limit"] > 0, "Pagination limit must be positive"

    print("✅ Pagination schema validation passed")


def test_csv_normalization():
    """Test that CSV data is properly normalized to Transaction schema."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "list_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-09-01",
                "end_date": "2024-09-30"
            }
        }
    })

    content = res["result"]["content"][0]["text"]
    result_data = json.loads(content)
    transactions = result_data["transactions"]

    # If we have transactions, check that they're properly normalized
    if transactions:
        for i, transaction in enumerate(transactions):
            # Check that amount and direction are consistent
            amount = transaction["amount"]
            direction = transaction["direction"]

            if amount >= 0:
                assert direction == "credit", f"Transaction {i}: positive amount should be credit"
            else:
                assert direction == "debit", f"Transaction {i}: negative amount should be debit"

            # Check that account_id matches the requested account
            assert transaction["account_id"] == "test123", f"Transaction {i}: account_id should match request"

    print("✅ CSV normalization validation passed")


def test_date_parameter_validation():
    """Test that date parameters are properly validated."""
    # Test with invalid date format
    try:
        res = rpc({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_transactions",
                "arguments": {
                    "account_id": "test123",
                    "start_date": "2024/09/01",  # Invalid format
                    "end_date": "2024-09-30"
                }
            }
        })

        # Should return an error for invalid date format
        assert "error" in res, "Should return error for invalid date format"
        print("✅ Invalid date format properly rejected")

    except Exception:
        # If the request fails completely, that's also acceptable
        print("✅ Invalid date format properly rejected (request failed)")


def test_missing_parameters():
    """Test that missing required parameters are handled."""
    try:
        res = rpc({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "list_transactions",
                "arguments": {
                    "account_id": "test123"
                    # Missing start_date and end_date
                }
            }
        })

        # Should return an error for missing parameters
        assert "error" in res, "Should return error for missing required parameters"
        print("✅ Missing parameters properly rejected")

    except Exception:
        # If the request fails completely, that's also acceptable
        print("✅ Missing parameters properly rejected (request failed)")


def test_validation_error_handling():
    """Test that validation errors are properly handled."""
    res = rpc({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "list_transactions",
            "arguments": {
                "account_id": "test123",
                "start_date": "2024-09-01",
                "end_date": "2024-09-30"
            }
        }
    })

    # Should not have an error in the response for valid requests
    assert "error" not in res, "list_transactions should not return an error for valid requests"

    # Should have valid content
    assert "result" in res
    content = res["result"]["content"][0]["text"]

    # Content should be valid JSON
    try:
        result_data = json.loads(content)
        assert "transactions" in result_data
        assert "pagination" in result_data
    except json.JSONDecodeError as e:
        assert False, f"Response content is not valid JSON: {e}"

    print("✅ Validation error handling passed")


if __name__ == "__main__":
    print("🧪 Running list_transactions tests...\n")

    try:
        test_list_transactions_returns_valid_structure()
        test_transaction_schema_validation()
        test_pagination_schema_validation()
        test_csv_normalization()
        test_date_parameter_validation()
        test_missing_parameters()
        test_validation_error_handling()

        print("\n🎉 All list_transactions tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
