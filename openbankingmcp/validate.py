"""
MCP schema validation utilities.
"""

from typing import Dict, List, Any, Optional
import json
import sys


def assert_tool_schema(tool: Dict[str, Any]) -> None:
    """Validate that a tool conforms to MCP spec requirements."""
    required_keys = ("name", "description", "inputSchema", "outputSchema")

    for key in required_keys:
        if key not in tool:
            raise ValueError(f"Tool missing required key: {key}")

    # Validate outputSchema structure
    oschema = tool["outputSchema"]
    if not isinstance(oschema, dict):
        raise ValueError("outputSchema must be an object")

    if "properties" not in oschema:
        raise ValueError("outputSchema must have 'properties'")

    if "content" not in oschema["properties"]:
        raise ValueError("outputSchema.properties must include 'content'")

    content_schema = oschema["properties"]["content"]
    if not isinstance(content_schema, dict):
        raise ValueError("outputSchema.properties.content must be an object")

    if content_schema.get("type") != "array":
        raise ValueError("outputSchema.properties.content must be an array")


def validate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate all tools in a list."""
    for i, tool in enumerate(tools):
        try:
            assert_tool_schema(tool)
        except ValueError as e:
            raise ValueError(f"Tool {i} ({tool.get('name', 'unnamed')}): {e}")

    return tools


def validate_tool_output(tool_name: str, output: Any) -> Any:
    """Validate tool output against expected schema."""
    try:
        if tool_name == "list_accounts":
            return _validate_list_accounts_output(output)
        elif tool_name == "list_transactions":
            return _validate_list_transactions_output(output)
        elif tool_name == "export_hmrc_csv":
            return _validate_export_hmrc_csv_output(output)
        else:
            # For other tools, just return the output as-is
            return output
    except Exception as e:
        print(f"❌ Validation error for tool {tool_name}: {e}", file=sys.stderr)
        return {
            "error": f"Output validation failed: {str(e)}",
            "original_output": output
        }


def _validate_list_accounts_output(output: Any) -> Dict[str, Any]:
    """Validate list_accounts tool output."""
    if not isinstance(output, dict):
        raise ValueError("Output must be a dictionary")

    if "accounts" not in output:
        raise ValueError("Output must contain 'accounts' field")

    accounts = output["accounts"]
    if not isinstance(accounts, list):
        raise ValueError("Accounts must be a list")

    # Validate each account
    for i, account in enumerate(accounts):
        _validate_account_structure(account, f"accounts[{i}]")

    return output


def _validate_list_transactions_output(output: Any) -> Dict[str, Any]:
    """Validate list_transactions tool output."""
    if not isinstance(output, dict):
        raise ValueError("Output must be a dictionary")

    required_fields = ["transactions", "pagination"]
    for field in required_fields:
        if field not in output:
            raise ValueError(f"Output must contain '{field}' field")

    # Validate transactions
    transactions = output["transactions"]
    if not isinstance(transactions, list):
        raise ValueError("Transactions must be a list")

    for i, transaction in enumerate(transactions):
        _validate_transaction_structure(transaction, f"transactions[{i}]")

    # Validate pagination
    pagination = output["pagination"]
    _validate_pagination_structure(pagination)

    return output


def _validate_export_hmrc_csv_output(output: Any) -> Dict[str, Any]:
    """Validate export_hmrc_csv tool output."""
    if not isinstance(output, dict):
        raise ValueError("Output must be a dictionary")

    if "error" in output:
        # Error case - just return as-is
        return output

    required_fields = ["export", "summary"]
    for field in required_fields:
        if field not in output:
            raise ValueError(f"Output must contain '{field}' field")

    # Validate export structure
    export = output["export"]
    _validate_export_structure(export)

    # Validate summary
    summary = output["summary"]
    if not isinstance(summary, str):
        raise ValueError("Summary must be a string")

    return output


def _validate_account_structure(account: Any, path: str = "") -> None:
    """Validate account structure."""
    if not isinstance(account, dict):
        raise ValueError(f"{path}: Account must be a dictionary")

    required_fields = ["id", "name", "type", "currency", "balance"]
    for field in required_fields:
        if field not in account:
            raise ValueError(f"{path}: Account missing required field '{field}'")

    # Validate balance is numeric
    balance = account["balance"]
    if not isinstance(balance, (int, float)):
        raise ValueError(f"{path}: Account balance must be a number")


def _validate_transaction_structure(transaction: Any, path: str = "") -> None:
    """Validate transaction structure."""
    if not isinstance(transaction, dict):
        raise ValueError(f"{path}: Transaction must be a dictionary")

    required_fields = ["id", "date", "description", "amount", "direction", "account_id"]
    for field in required_fields:
        if field not in transaction:
            raise ValueError(f"{path}: Transaction missing required field '{field}'")

    # Validate amount is numeric
    amount = transaction["amount"]
    if not isinstance(amount, (int, float)):
        raise ValueError(f"{path}: Transaction amount must be a number")

    # Validate direction
    direction = transaction["direction"]
    if direction not in ["credit", "debit"]:
        raise ValueError(f"{path}: Transaction direction must be 'credit' or 'debit'")


def _validate_pagination_structure(pagination: Any) -> None:
    """Validate pagination structure."""
    if not isinstance(pagination, dict):
        raise ValueError("Pagination must be a dictionary")

    required_fields = ["total", "page", "limit", "has_more"]
    for field in required_fields:
        if field not in pagination:
            raise ValueError(f"Pagination missing required field '{field}'")

    # Validate numeric fields
    for field in ["total", "page", "limit"]:
        value = pagination[field]
        if not isinstance(value, int):
            raise ValueError(f"Pagination '{field}' must be an integer")

    # Validate boolean field
    has_more = pagination["has_more"]
    if not isinstance(has_more, bool):
        raise ValueError("Pagination 'has_more' must be a boolean")


def _validate_export_structure(export: Any) -> None:
    """Validate export structure."""
    if not isinstance(export, dict):
        raise ValueError("Export must be a dictionary")

    required_fields = ["csv_path", "metadata"]
    for field in required_fields:
        if field not in export:
            raise ValueError(f"Export missing required field '{field}'")

    # Validate metadata
    metadata = export["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("Export metadata must be a dictionary")

    required_metadata = ["account_id", "start_date", "end_date", "transaction_count", "created_at"]
    for field in required_metadata:
        if field not in metadata:
            raise ValueError(f"Export metadata missing required field '{field}'")

    # Validate transaction_count is integer
    transaction_count = metadata["transaction_count"]
    if not isinstance(transaction_count, int):
        raise ValueError("Export metadata transaction_count must be an integer")
