"""
MCP server for Open Banking (TrueLayer).

Implements the Model Context Protocol (MCP) for Cursor integration.
Provides tools for accessing bank account data via TrueLayer API.

Runs with mocked data by default. If you set TRUELAYER_CLIENT_ID and
TRUELAYER_CLIENT_SECRET as environment variables, it will try to call
TrueLayer Sandbox instead.
"""

import json
import os
import sys
import re
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from validate import validate_tools
from pkce import pkce_manager, consent_ledger, generate_random_state


def _is_debug_payload_logging_enabled() -> bool:
    """Return True if verbose TrueLayer payload logging is enabled."""
    flag = os.getenv("TRUELAYER_DEBUG_PAYLOADS", "")
    return flag.strip().lower() in {"1", "true", "yes", "on"}


DEBUG_TRUELAYER_PAYLOADS = _is_debug_payload_logging_enabled()


def build_tools_list():
    """Describe available MCP tools with JSON schema metadata."""
    return [
        {
            "name": "create_data_auth_link",
            "description": "Create a TrueLayer OAuth authorization URL for data access.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "exchange_code",
            "description": "Exchange OAuth authorization code for access and refresh tokens.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The authorization code from OAuth callback"
                    }
                },
                "required": ["code"],
                "additionalProperties": False,
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "get_accounts",
            "description": "List all user bank accounts.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "get_transactions",
            "description": "Get transactions for a specific account within a date range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to fetch transactions for"
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return (default: 50)",
                        "minimum": 1,
                        "maximum": 500
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "minimum": 1
                    },
                    "include_raw": {
                        "type": "boolean",
                        "description": "Include full transaction payloads instead of redacted data (default: false)"
                    }
                },
                "required": ["account_id", "start_date", "end_date"],
                "additionalProperties": False,
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["content"]
            }
        }
    ]


class MCPServer:
    """Implements the Model Context Protocol (MCP) for Cursor integration."""

    def __init__(self):
        self.tools = validate_tools(build_tools_list())
        # In-memory token storage (in production, use proper storage)
        self.user_tokens = {}

        # Log startup info
        print(f"🚀 server_start python={sys.version.split()[0]} cwd={os.getcwd()}", file=sys.stderr)

    def send_response(self, response: Dict[str, Any]):
        """Send a JSON response to stdout."""
        # Log outgoing response (redacted)
        self._log_request("rpc_out", response)
        print(json.dumps(response), flush=True)

    def send_error(self, request_id: Any, code: int, message: str):
        """Send a JSON-RPC error response."""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self.send_response(error_response)

    def _log_request(self, direction: str, data: Dict[str, Any]):
        """Log MCP requests/responses with PII redaction."""
        # Create a copy for logging
        log_data = data.copy()

        # Redact sensitive fields
        if "params" in log_data and "arguments" in log_data["params"]:
            args = log_data["params"]["arguments"]
            if "code" in args:
                args["code"] = "[REDACTED]"

        # Redact result content if it contains tokens
        if "result" in log_data and "content" in log_data["result"]:
            content = log_data["result"]["content"]
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")
                if "access_token" in text_content or "refresh_token" in text_content:
                    content[0]["text"] = "[REDACTED_TOKEN_DATA]"

        print(f"📝 {direction}: {json.dumps(log_data, indent=2)}", file=sys.stderr)

    def handle_request(self, request: Dict[str, Any]):
        """Handle incoming MCP requests."""
        # Log incoming request (redacted)
        self._log_request("rpc_in", request)

        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            self.handle_initialize(request)
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            pass
        elif method == "tools/list":
            self.handle_tools_list(request)
        elif method == "tools/call":
            self.handle_tools_call(request)
        else:
            self.send_error(request.get("id"), -32601, f"Method not found: {method}")

    def handle_initialize(self, request: Dict[str, Any]):
        """Handle MCP initialization request."""
        self.send_response({
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "openbanking-mcp",
                    "version": "1.0.0"
                }
            }
        })

    def handle_tools_list(self, request: Dict[str, Any]):
        """Handle tools/list request."""
        print(f"📋 Tools list requested, returning {len(self.tools)} tools", file=sys.stderr)
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": self.tools
            }
        }
        self.send_response(response)

    def handle_tools_call(self, request: Dict[str, Any]):
        """Handle tools/call request."""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "create_data_auth_link":
                result = self._create_data_auth_link()
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            elif tool_name == "exchange_code":
                code = arguments.get("code")
                if not code:
                    self.send_error(request.get("id"), -32602, "Missing required parameter: code")
                    return

                result = self._exchange_code(code)
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            elif tool_name == "get_accounts":
                result = self._get_accounts_data()
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            elif tool_name == "get_transactions":
                account_id = arguments.get("account_id")
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")
                limit = arguments.get("limit", 50)
                page = arguments.get("page", 1)
                include_raw = arguments.get("include_raw", False)

                if not all([account_id, start_date, end_date]):
                    self.send_error(request.get("id"), -32602, "Missing required parameters: account_id, start_date, end_date")
                    return

                # Validate date format
                if not self._validate_date_format(start_date) or not self._validate_date_format(end_date):
                    self.send_error(request.get("id"), -32602, "Invalid date format. Use YYYY-MM-DD")
                    return

                result = self._get_transactions_data(account_id, start_date, end_date, limit, page, include_raw)
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            else:
                self.send_error(request.get("id"), -32601, f"Unknown tool: {tool_name}")
        except Exception as e:
            print(f"❌ Error in tool {tool_name}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            self.send_error(request.get("id"), -32000, f"Tool execution error: {str(e)}")

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate that date string is in YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _create_data_auth_link(self) -> Dict[str, Any]:
        """Create a TrueLayer OAuth authorization URL for data access."""
        client_id = os.getenv("TRUELAYER_CLIENT_ID")
        redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")

        if not client_id:
            return {
                "error": "TRUELAYER_CLIENT_ID environment variable not set",
                "mock_url": "https://auth.truelayer-sandbox.com/connect/authorize?response_type=code&client_id=YOUR_CLIENT_ID&scope=info%20accounts%20balance%20transactions&redirect_uri=http://localhost:8080/callback&providers=mock"
            }

        params = {
            "response_type": "code",
            "client_id": client_id,
            "scope": "info accounts balance transactions",
            "redirect_uri": redirect_uri,
            "providers": "mock"
        }

        auth_url = f"https://auth.truelayer-sandbox.com/connect/authorize?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "instructions": "Visit the auth_url to authorize access, then use the returned code with exchange_code tool"
        }

    def _exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for access and refresh tokens."""
        client_id = os.getenv("TRUELAYER_CLIENT_ID")
        client_secret = os.getenv("TRUELAYER_CLIENT_SECRET")
        redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")

        if not all([client_id, client_secret]):
            return {
                "error": "Missing TrueLayer credentials. Set TRUELAYER_CLIENT_ID and TRUELAYER_CLIENT_SECRET environment variables."
            }

        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }

            response = requests.post(
                "https://auth.truelayer-sandbox.com/connect/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")

            if access_token:
                # Store tokens in memory (in production, use proper storage)
                self.user_tokens["current"] = {
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }

                return {
                    "success": True,
                    "access_token": access_token[:20] + "...",  # Redacted for security
                    "refresh_token": refresh_token[:20] + "..." if refresh_token else None,
                    "message": "Tokens stored successfully"
                }
            else:
                return {
                    "error": "No access token in response",
                    "response": token_data
                }

        except requests.exceptions.RequestException as e:
            return {
                "error": f"Token exchange failed: {str(e)}"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}"
            }

    def _get_user_token(self) -> Optional[str]:
        """Get the current user's access token."""
        user_token = self.user_tokens.get("current")
        if user_token and user_token.get("access_token"):
            return user_token["access_token"]
        return None

    def _get_truelayer_token(self):
        """Get TrueLayer token (legacy method for backward compatibility)."""
        return self._get_user_token()

    def _fetch_truelayer_accounts(self, token):
        """Fetch accounts from TrueLayer API."""
        try:
            response = requests.get(
                "https://api.truelayer-sandbox.com/data/v1/accounts",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()

            if DEBUG_TRUELAYER_PAYLOADS:
                print(f"🪵 Accounts payload preview (debug enabled): {response.text[:200]}...")

            data = response.json()
            results = data.get("results", [])
            print(f"📊 Parsed {len(results)} accounts from TrueLayer response")
            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ TrueLayer accounts API error: {e}")
            raise

    def _fetch_truelayer_transactions(self, token, account_id, start_date, end_date, limit=50, page=1):
        """Fetch transactions from TrueLayer API for a specific account and date range."""
        try:
            params = {
                "from": start_date,
                "to": end_date,
                "limit": limit,
                "page": page
            }

            response = requests.get(
                f"https://api.truelayer-sandbox.com/data/v1/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )
            response.raise_for_status()

            if DEBUG_TRUELAYER_PAYLOADS:
                print(f"🪵 Transactions payload preview (debug enabled): {response.text[:200]}...")

            data = response.json()
            results = data.get("results", [])
            print(f"📊 Parsed {len(results)} transactions from TrueLayer response")
            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ TrueLayer transactions API error: {e}")
            raise

    def _redact_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive transaction data for security."""
        redacted = {
            "id": transaction.get("id", ""),
            "date": transaction.get("date", ""),
            "amount": transaction.get("amount", 0),
            "currency": transaction.get("currency", ""),
            "category": transaction.get("category", ""),
            "classification": transaction.get("classification", "")
        }
        return redacted

    def _get_accounts_data(self):
        """Get accounts data, trying TrueLayer first, then falling back to mock data."""
        token = self._get_truelayer_token()
        if token:
            try:
                print("🔑 User token found, fetching accounts...")
                accounts = self._fetch_truelayer_accounts(token)
                print(f"✅ TrueLayer returned {len(accounts)} accounts")
                return accounts
            except Exception as e:
                print(f"❌ TrueLayer API error: {e}")
                print("🔄 Falling back to mock data...")
        else:
            print("⚠️ No user token found, using mock data")

        # Fallback mock
        return [
            {
                "id": "acc123",
                "name": "Main Checking Account",
                "currency": "GBP",
                "balance": 1250.50,
                "account_type": "checking",
            },
            {
                "id": "acc456",
                "name": "Savings Account",
                "currency": "GBP",
                "balance": 5000.00,
                "account_type": "savings",
            },
        ]

    def _get_transactions_data(self, account_id, start_date, end_date, limit=50, page=1, include_raw=False):
        """Get transactions data, trying TrueLayer first, then falling back to mock data."""
        token = self._get_truelayer_token()
        if token:
            try:
                print(f"🔑 User token found, fetching transactions for {account_id} ({start_date} to {end_date})...")
                transactions = self._fetch_truelayer_transactions(token, account_id, start_date, end_date, limit, page)
                print(f"✅ TrueLayer returned {len(transactions)} transactions")

                if not include_raw:
                    # Redact sensitive data by default
                    transactions = [self._redact_transaction(txn) for txn in transactions]

                return transactions
            except Exception as e:
                print(f"❌ TrueLayer transactions API error: {e}")
                print("🔄 Falling back to mock data...")
        else:
            print("⚠️ No user token found, using mock data")

        # Fallback mock data
        mock_transactions = [
            {
                "id": "txn001",
                "account_id": account_id,
                "amount": -45.50,
                "currency": "GBP",
                "description": "TESCO STORES 1234 LONDON",
                "transaction_type": "debit",
                "merchant_name": "Tesco",
                "category": "groceries",
                "date": "2024-09-15",
                "timestamp": "2024-09-15T14:30:00Z",
            },
            {
                "id": "txn002",
                "account_id": account_id,
                "amount": -12.99,
                "currency": "GBP",
                "description": "AMAZON UK SERVICES",
                "transaction_type": "debit",
                "merchant_name": "Amazon",
                "category": "shopping",
                "date": "2024-09-14",
                "timestamp": "2024-09-14T09:15:00Z",
            },
            {
                "id": "txn003",
                "account_id": account_id,
                "amount": 2500.00,
                "currency": "GBP",
                "description": "SALARY PAYMENT",
                "transaction_type": "credit",
                "merchant_name": "Employer Ltd",
                "category": "salary",
                "date": "2024-09-01",
                "timestamp": "2024-09-01T00:00:00Z",
            },
            {
                "id": "txn004",
                "account_id": account_id,
                "amount": -89.99,
                "currency": "GBP",
                "description": "BRITISH GAS ENERGY",
                "transaction_type": "debit",
                "merchant_name": "British Gas",
                "category": "utilities",
                "date": "2024-08-28",
                "timestamp": "2024-08-28T06:00:00Z",
            },
            {
                "id": "txn005",
                "account_id": account_id,
                "amount": -25.00,
                "currency": "GBP",
                "description": "CASH WITHDRAWAL ATM",
                "transaction_type": "debit",
                "merchant_name": "ATM",
                "category": "cash",
                "date": "2024-08-25",
                "timestamp": "2024-08-25T16:45:00Z",
            }
        ]

        if not include_raw:
            # Redact sensitive data by default
            mock_transactions = [self._redact_transaction(txn) for txn in mock_transactions]

        return mock_transactions


def run_mcp_server():
    """Run the MCP server using stdio communication."""
    print("🚀 OpenBanking MCP server starting...", file=sys.stderr)
    print("🔧 Server initialized, waiting for requests...", file=sys.stderr)

    server = MCPServer()

    # Read from stdin line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            server.handle_request(request)
        except json.JSONDecodeError as e:
            server.send_error(None, -32700, f"Parse error: {e}")
        except Exception as e:
            server.send_error(None, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    run_mcp_server()