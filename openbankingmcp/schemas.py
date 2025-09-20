"""
JSON Schema definitions for Open Banking MCP tools.

Defines schemas for Account, Transaction, and Export data structures.
"""

from typing import Dict, Any, Optional
from datetime import datetime


# JSON Schema definitions
ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Unique account identifier"},
        "name": {"type": "string", "description": "Account display name"},
        "type": {"type": "string", "description": "Account type (e.g., checking, savings)"},
        "currency": {"type": "string", "description": "Account currency code (e.g., GBP, USD)"},
        "balance": {"type": "number", "description": "Current account balance"}
    },
    "required": ["id", "name", "type", "currency", "balance"],
    "additionalProperties": False
}

TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Unique transaction identifier"},
        "date": {"type": "string", "format": "date", "description": "Transaction date in YYYY-MM-DD format"},
        "description": {"type": "string", "description": "Transaction description"},
        "amount": {"type": "number", "description": "Transaction amount (positive for credits, negative for debits)"},
        "direction": {"type": "string", "enum": ["credit", "debit"], "description": "Transaction direction"},
        "account_id": {"type": "string", "description": "Associated account ID"},
        "category": {"type": "string", "description": "Transaction category (optional)"}
    },
    "required": ["id", "date", "description", "amount", "direction", "account_id"],
    "additionalProperties": False
}

EXPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "csv_path": {"type": "string", "description": "Path to the exported CSV file"},
        "metadata": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID that was exported"},
                "start_date": {"type": "string", "format": "date", "description": "Export start date"},
                "end_date": {"type": "string", "format": "date", "description": "Export end date"},
                "transaction_count": {"type": "integer", "description": "Number of transactions exported"},
                "total_income": {"type": "number", "description": "Total income amount"},
                "total_expenses": {"type": "number", "description": "Total expenses amount"},
                "net_total": {"type": "number", "description": "Net total (income - expenses)"},
                "created_at": {"type": "string", "format": "date-time", "description": "Export creation timestamp"}
            },
            "required": ["account_id", "start_date", "end_date", "transaction_count", "created_at"],
            "additionalProperties": False
        }
    },
    "required": ["csv_path", "metadata"],
    "additionalProperties": False
}

# Tool output schemas
LIST_ACCOUNTS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "accounts": {
            "type": "array",
            "items": ACCOUNT_SCHEMA,
            "description": "List of user accounts"
        }
    },
    "required": ["accounts"],
    "additionalProperties": False
}

LIST_TRANSACTIONS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "items": TRANSACTION_SCHEMA,
            "description": "List of transactions"
        },
        "pagination": {
            "type": "object",
            "properties": {
                "total": {"type": "integer", "description": "Total number of transactions"},
                "page": {"type": "integer", "description": "Current page number"},
                "limit": {"type": "integer", "description": "Number of transactions per page"},
                "has_more": {"type": "boolean", "description": "Whether there are more pages"}
            },
            "required": ["total", "page", "limit", "has_more"],
            "additionalProperties": False
        }
    },
    "required": ["transactions", "pagination"],
    "additionalProperties": False
}

EXPORT_HMRC_CSV_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "export": EXPORT_SCHEMA,
        "summary": {"type": "string", "description": "Human-readable export summary"}
    },
    "required": ["export", "summary"],
    "additionalProperties": False
}


def validate_account(account: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize an account object."""
    # Basic validation - in a real implementation, you'd use jsonschema library
    required_fields = ["id", "name", "type", "currency", "balance"]
    for field in required_fields:
        if field not in account:
            raise ValueError(f"Account missing required field: {field}")

    if not isinstance(account["balance"], (int, float)):
        raise ValueError("Account balance must be a number")

    if account["currency"] not in ["GBP", "USD", "EUR"]:
        print(f"Warning: Unknown currency {account['currency']}")

    return account


def validate_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a transaction object."""
    required_fields = ["id", "date", "description", "amount", "direction", "account_id"]
    for field in required_fields:
        if field not in transaction:
            raise ValueError(f"Transaction missing required field: {field}")

    if not isinstance(transaction["amount"], (int, float)):
        raise ValueError("Transaction amount must be a number")

    if transaction["direction"] not in ["credit", "debit"]:
        raise ValueError("Transaction direction must be 'credit' or 'debit'")

    # Validate date format
    try:
        datetime.strptime(transaction["date"], "%Y-%m-%d")
    except ValueError:
        raise ValueError("Transaction date must be in YYYY-MM-DD format")

    return transaction


def validate_export(export: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize an export object."""
    required_fields = ["csv_path", "metadata"]
    for field in required_fields:
        if field not in export:
            raise ValueError(f"Export missing required field: {field}")

    metadata = export["metadata"]
    required_metadata = ["account_id", "start_date", "end_date", "transaction_count", "created_at"]
    for field in required_metadata:
        if field not in metadata:
            raise ValueError(f"Export metadata missing required field: {field}")

    if not isinstance(metadata["transaction_count"], int):
        raise ValueError("Transaction count must be an integer")

    return export
