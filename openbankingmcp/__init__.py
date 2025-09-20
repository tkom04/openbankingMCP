"""
OpenBanking MCP Package

A Model Context Protocol (MCP) server for Open Banking integration with TrueLayer API.
Provides tools for accessing bank account data and generating HMRC-ready CSV exports.
"""

__version__ = "0.1.0"
__author__ = "OpenBanking MCP Team"

# Import main components for easy access
from .server import MCPServer, create_fastapi_app, run_mcp_server, run_rest_api_server
from .validate import validate_tools, validate_tool_output
from .schemas import (
    ACCOUNT_SCHEMA, TRANSACTION_SCHEMA, EXPORT_SCHEMA,
    LIST_ACCOUNTS_OUTPUT_SCHEMA, LIST_TRANSACTIONS_OUTPUT_SCHEMA, EXPORT_HMRC_CSV_OUTPUT_SCHEMA,
    validate_account, validate_transaction, validate_export
)
from .hmrc import normalize_category, CATEGORY_MAP, get_valid_hmrc_categories

__all__ = [
    "MCPServer",
    "create_fastapi_app",
    "run_mcp_server",
    "run_rest_api_server",
    "validate_tools",
    "validate_tool_output",
    "ACCOUNT_SCHEMA",
    "TRANSACTION_SCHEMA",
    "EXPORT_SCHEMA",
    "LIST_ACCOUNTS_OUTPUT_SCHEMA",
    "LIST_TRANSACTIONS_OUTPUT_SCHEMA",
    "EXPORT_HMRC_CSV_OUTPUT_SCHEMA",
    "validate_account",
    "validate_transaction",
    "validate_export",
    "normalize_category",
    "CATEGORY_MAP",
    "get_valid_hmrc_categories",
]
