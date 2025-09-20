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
import copy
import requests
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from .validate import validate_tools, validate_tool_output
from .pkce import pkce_manager, consent_ledger, generate_random_state
from .schemas import (
    ACCOUNT_SCHEMA, TRANSACTION_SCHEMA, EXPORT_SCHEMA,
    LIST_ACCOUNTS_OUTPUT_SCHEMA, LIST_TRANSACTIONS_OUTPUT_SCHEMA, EXPORT_HMRC_CSV_OUTPUT_SCHEMA,
    validate_account, validate_transaction, validate_export
)
from .hmrc import normalize_category

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "exchange_code",
            "description": "Exchange OAuth authorization code for access and refresh tokens (legacy alias).",
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "complete_code_exchange",
            "description": "Complete PKCE OAuth authorization code exchange with state validation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The authorization code from OAuth callback"
                    },
                    "state": {
                        "type": "string",
                        "description": "The state parameter from OAuth callback"
                    }
                },
                "required": ["code", "state"],
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_accounts",
            "description": "Return 1-2 dummy accounts with proper schema validation.",
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_transactions",
            "description": "Read sample CSV, normalize rows → Transaction[] with schema validation.",
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "export_hmrc_csv",
            "description": "Export transactions as HMRC-ready CSV with categorization and summary.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to export transactions for"
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
                    "filename": {
                        "type": "string",
                        "description": "Optional filename for the CSV export (defaults to hmrc_export_<account>_<from>_<to>.csv)"
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_consents",
            "description": "List all active user consents with their purposes and expiration dates.",
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
                                "type": {"type": "string", "enum": ["text"]},
                                "text": {"type": "string"}
                            },
                            "required": ["type", "text"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["content"],
                "additionalProperties": False
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
        # Deep copy so redaction never mutates the original payload
        log_data = copy.deepcopy(data)

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
            elif tool_name == "complete_code_exchange":
                code = arguments.get("code")
                state = arguments.get("state")
                if not code or not state:
                    self.send_error(request.get("id"), -32602, "Missing required parameters: code, state")
                    return

                result = self._complete_code_exchange(code, state)
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
            elif tool_name == "list_accounts":
                result = self._list_accounts()
                validated_result = validate_tool_output("list_accounts", result)
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(validated_result, indent=2)
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
            elif tool_name == "list_transactions":
                account_id = arguments.get("account_id")
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")
                limit = arguments.get("limit", 10)  # ✅ Default limit
                offset = arguments.get("offset", 0)  # ✅ Default offset

                if not all([account_id, start_date, end_date]):
                    self.send_error(request.get("id"), -32602, "Missing required parameters: account_id, start_date, end_date")
                    return

                # Validate date format
                if not self._validate_date_format(start_date) or not self._validate_date_format(end_date):
                    self.send_error(request.get("id"), -32602, "Invalid date format. Use YYYY-MM-DD")
                    return

                result = self._list_transactions({
                    "account_id": account_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "offset": offset
                })
                validated_result = validate_tool_output("list_transactions", result)
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(validated_result, indent=2)
                            }
                        ]
                    }
                })
            elif tool_name == "export_hmrc_csv":
                account_id = arguments.get("account_id")
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")
                filename = arguments.get("filename")

                if not all([account_id, start_date, end_date]):
                    self.send_error(request.get("id"), -32602, "Missing required parameters: account_id, start_date, end_date")
                    return

                # Validate date format
                if not self._validate_date_format(start_date) or not self._validate_date_format(end_date):
                    self.send_error(request.get("id"), -32602, "Invalid date format. Use YYYY-MM-DD")
                    return

                result = self._export_hmrc_csv(account_id, start_date, end_date, filename)
                validated_result = validate_tool_output("export_hmrc_csv", result)
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(validated_result, indent=2)
                            }
                        ]
                    }
                })
            elif tool_name == "list_consents":
                result = self._list_consents()
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result
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
        """Create a TrueLayer OAuth authorization URL for data access with PKCE."""
        client_id = os.getenv("TRUELAYER_CLIENT_ID")
        redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")

        if not client_id:
            return {
                "error": "TRUELAYER_CLIENT_ID environment variable not set",
                "mock_url": "https://auth.truelayer-sandbox.com/connect/authorize?response_type=code&client_id=YOUR_CLIENT_ID&scope=info%20accounts%20balance%20transactions&redirect_uri=http://localhost:8080/callback&providers=mock"
            }

        # Generate PKCE parameters
        from pkce import generate_code_verifier
        state = generate_random_state()
        code_verifier = generate_code_verifier()
        state, code_challenge, _ = pkce_manager.create_flow(state, code_verifier)

        params = {
            "response_type": "code",
            "client_id": client_id,
            "scope": "info accounts balance transactions",
            "redirect_uri": redirect_uri,
            "providers": "mock",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = f"https://auth.truelayer-sandbox.com/connect/authorize?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "state": state,
            "instructions": "Visit the auth_url to authorize access, then use the returned code and state with complete_code_exchange tool"
        }

    def _exchange_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
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

            # Add PKCE parameters if available
            if code_verifier:
                data["code_verifier"] = code_verifier

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
                print(f"🪵 Accounts payload preview (debug enabled): {response.text[:200]}...", file=sys.stderr)

            data = response.json()
            results = data.get("results", [])
            print(f"📊 Parsed {len(results)} accounts from TrueLayer response", file=sys.stderr)
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
                print(f"🪵 Transactions payload preview (debug enabled): {response.text[:200]}...", file=sys.stderr)

            data = response.json()
            results = data.get("results", [])
            print(f"📊 Parsed {len(results)} transactions from TrueLayer response", file=sys.stderr)
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
                print("🔑 User token found, fetching accounts...", file=sys.stderr)
                accounts = self._fetch_truelayer_accounts(token)
                print(f"✅ TrueLayer returned {len(accounts)} accounts", file=sys.stderr)
                return accounts
            except Exception as e:
                print(f"❌ TrueLayer API error: {e}", file=sys.stderr)
                print("🔄 Falling back to mock data...", file=sys.stderr)
        else:
            print("⚠️ No user token found, using mock data", file=sys.stderr)

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

    def _list_accounts(self):
        """Return 1-2 dummy accounts with proper schema validation."""
        # Create dummy accounts that match the Account schema
        dummy_accounts = [
            {
                "id": "acc001",
                "name": "Primary Current Account",
                "type": "checking",
                "currency": "GBP",
                "balance": 2847.32
            },
            {
                "id": "acc002",
                "name": "Business Savings",
                "type": "savings",
                "currency": "GBP",
                "balance": 15750.00
            }
        ]

        # Validate each account
        validated_accounts = []
        for account in dummy_accounts:
            try:
                validated_account = validate_account(account)
                validated_accounts.append(validated_account)
            except ValueError as e:
                print(f"❌ Account validation error: {e}", file=sys.stderr)
                continue

        return {
            "accounts": validated_accounts
        }

    def _get_transactions_data(self, account_id, start_date, end_date, limit=50, page=1, include_raw=False):
        """Get transactions data, trying TrueLayer first, then falling back to mock data."""
        token = self._get_truelayer_token()
        if token:
            try:
                print(f"🔑 User token found, fetching transactions for {account_id} ({start_date} to {end_date})...", file=sys.stderr)
                transactions = self._fetch_truelayer_transactions(token, account_id, start_date, end_date, limit, page)
                print(f"✅ TrueLayer returned {len(transactions)} transactions", file=sys.stderr)

                if not include_raw:
                    # Redact sensitive data by default
                    transactions = [self._redact_transaction(txn) for txn in transactions]

                return transactions
            except Exception as e:
                print(f"❌ TrueLayer transactions API error: {e}", file=sys.stderr)
                print("🔄 Falling back to mock data...", file=sys.stderr)
        else:
            print("⚠️ No user token found, using mock data", file=sys.stderr)

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

    def _list_transactions(self, args: dict) -> dict:
        """Read sample CSV, normalize rows → Transaction[] with schema validation."""
        account_id = args.get("account_id")
        start_date = args.get("start_date")
        end_date = args.get("end_date")

        # ✅ Fix: ensure defaults
        limit = int(args.get("limit", 10))
        offset = int(args.get("offset", 0))

        transactions = []

        # Try to read from test.csv file
        csv_file = "test.csv"
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row_num, row in enumerate(reader, 1):
                        try:
                            # Normalize CSV row to Transaction schema
                            transaction = self._normalize_csv_row_to_transaction(row, account_id, row_num)
                            validated_transaction = validate_transaction(transaction)
                            transactions.append(validated_transaction)
                        except ValueError as e:
                            print(f"❌ Transaction validation error on row {row_num}: {e}", file=sys.stderr)
                            continue

                print(f"✅ Loaded {len(transactions)} transactions from {csv_file}", file=sys.stderr)
            except Exception as e:
                print(f"❌ Error reading CSV file: {e}", file=sys.stderr)
        else:
            print(f"⚠️ CSV file {csv_file} not found, using mock transactions", file=sys.stderr)
            # Fallback to mock data
            mock_transactions = self._get_transactions_data(account_id, start_date, end_date, include_raw=True)
            for txn in mock_transactions:
                try:
                    # Normalize mock transaction to schema
                    normalized_txn = self._normalize_mock_transaction_to_schema(txn)
                    validated_transaction = validate_transaction(normalized_txn)
                    transactions.append(validated_transaction)
                except ValueError as e:
                    print(f"❌ Mock transaction validation error: {e}", file=sys.stderr)
                    continue

        # Apply offset and limit to transactions
        paginated_transactions = transactions[offset:offset + limit]

        return {
            "transactions": paginated_transactions,
            "pagination": {
                "total": len(transactions),
                "page": (offset // limit) + 1,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < len(transactions)
            }
        }

    def _normalize_csv_row_to_transaction(self, row: Dict[str, str], account_id: str, row_num: int) -> Dict[str, Any]:
        """Normalize a CSV row to Transaction schema format."""
        # Convert date from DD/MM/YYYY to YYYY-MM-DD
        date_str = row.get("Date", "")
        if date_str and "/" in date_str:
            try:
                # Parse DD/MM/YYYY format
                day, month, year = date_str.split("/")
                normalized_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}")
        else:
            normalized_date = date_str

        # Parse amount
        amount_str = row.get("Amount", "0")
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount_str}")

        # Determine direction based on amount
        direction = "credit" if amount >= 0 else "debit"

        return {
            "id": f"txn_{row_num:03d}",
            "date": normalized_date,
            "description": row.get("Description", ""),
            "amount": amount,
            "direction": direction,
            "account_id": account_id,
            "category": row.get("HMRC Category", "")
        }

    def _normalize_mock_transaction_to_schema(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a mock transaction to Transaction schema format."""
        amount = txn.get("amount", 0)
        direction = "credit" if amount >= 0 else "debit"

        return {
            "id": txn.get("id", ""),
            "date": txn.get("date", ""),
            "description": txn.get("description", ""),
            "amount": amount,
            "direction": direction,
            "account_id": txn.get("account_id", ""),
            "category": txn.get("category", "")
        }

    def _complete_code_exchange(self, code: str, state: str) -> Dict[str, Any]:
        """Complete PKCE OAuth authorization code exchange with state validation."""
        # Validate state
        code_verifier = pkce_manager.get_verifier(state)
        if not code_verifier:
            return {
                "error": "Invalid or expired state parameter",
                "code": -32602
            }

        # Use the existing exchange logic but with PKCE
        result = self._exchange_code(code, code_verifier)

        # Add consent to ledger if successful
        if "success" in result and result["success"]:
            consent_id = consent_ledger.add_consent(
                consent_id=state,
                purpose="Bank account data access for HMRC reporting",
                scopes=["info", "accounts", "balance", "transactions"],
                provider="TrueLayer"
            )
            result["consent_id"] = consent_id

        return result

    def _list_consents(self) -> str:
        """List all active user consents."""
        consents = consent_ledger.list_consents()

        if not consents:
            return "No active consents found."

        result = "Active User Consents:\n"
        result += "=" * 50 + "\n\n"

        for consent in consents:
            result += f"Consent ID: {consent['id']}\n"
            result += f"Purpose: {consent['purpose']}\n"
            result += f"Provider: {consent['provider']}\n"
            result += f"Scopes: {', '.join(consent['scopes'])}\n"
            result += f"Granted: {consent['granted_at']}\n"
            result += f"Expires: {consent['expires_at']}\n"
            result += "-" * 30 + "\n\n"

        return result

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """Categorize transaction for HMRC reporting."""
        # If transaction already has a category, normalize it
        existing_category = transaction.get("category", "")
        if existing_category:
            return normalize_category(existing_category)

        # Get description for pattern matching
        description = (transaction.get("description", "") + " " +
                      transaction.get("merchant_name", "")).lower()

        # HMRC categorization buckets
        if any(keyword in description for keyword in ["salary", "invoice", "stripe", "income"]):
            return normalize_category("Income")
        elif any(keyword in description for keyword in ["interest"]):
            return normalize_category("Bank Interest")
        elif any(keyword in description for keyword in ["uber", "train", "rail", "tfl", "taxi"]):
            return normalize_category("Travel")
        elif any(keyword in description for keyword in ["coffee", "cafe", "restaurant"]):
            return normalize_category("Office Costs")
        elif any(keyword in description for keyword in ["gas", "electric", "water", "broadband"]):
            return normalize_category("Utilities")
        elif any(keyword in description for keyword in ["wise", "transferwise", "fee", "charge"]):
            return normalize_category("Bank charges")
        else:
            return normalize_category("General expenses")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for filesystem."""
        # Remove or replace unsafe characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Ensure it has .csv extension
        if not safe_filename.endswith('.csv'):
            safe_filename += '.csv'
        return safe_filename

    def _export_hmrc_csv(self, account_id: str, start_date: str, end_date: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Export transactions as HMRC-ready CSV with categorization and summary."""
        # Get transactions data
        transactions = self._get_transactions_data(account_id, start_date, end_date, include_raw=True)

        # Generate filename if not provided
        if not filename:
            filename = f"hmrc_export_{account_id}_{start_date}_{end_date}.csv"

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Prepare CSV data
        csv_rows = []
        income_total = 0
        expense_total = 0
        category_totals = {}

        for transaction in transactions:
            # Convert date from YYYY-MM-DD to DD/MM/YYYY
            date_str = transaction.get("date", "")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except ValueError:
                    formatted_date = date_str
            else:
                formatted_date = ""

            # Get amount and currency
            amount = transaction.get("amount", 0)
            currency = transaction.get("currency", "GBP")

            # Categorize transaction
            category = self._categorize_transaction(transaction)

            # Get description
            description = transaction.get("description", "") or transaction.get("merchant_name", "")

            # Add to CSV
            csv_rows.append({
                "Date": formatted_date,
                "Description": description,
                "Amount": abs(amount),  # HMRC wants positive amounts
                "Currency": currency,
                "HMRC Category": category
            })

            # Calculate totals
            if amount > 0:
                income_total += amount
            else:
                expense_total += abs(amount)

            # Track category totals
            category_totals[category] = category_totals.get(category, 0) + abs(amount)

        # Write CSV file
        try:
            with open(safe_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["Date", "Description", "Amount", "Currency", "HMRC Category"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                writer.writerows(csv_rows)

            print(f"✅ CSV exported to {safe_filename} with {len(csv_rows)} transactions", file=sys.stderr)
        except Exception as e:
            print(f"❌ Error writing CSV file: {e}", file=sys.stderr)
            return {
                "error": f"Failed to write CSV file: {str(e)}",
                "export": None,
                "summary": ""
            }

        # Calculate summary
        net_total = income_total - expense_total

        # Get top 3 expense categories
        expense_categories = {k: v for k, v in category_totals.items() if k != "Income" and k != "Bank Interest"}
        top_expenses = sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:3]

        # Create export metadata
        export_data = {
            "csv_path": safe_filename,
            "metadata": {
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
                "transaction_count": len(csv_rows),
                "total_income": income_total,
                "total_expenses": expense_total,
                "net_total": net_total,
                "created_at": datetime.now().isoformat()
            }
        }

        # Validate export data
        try:
            validated_export = validate_export(export_data)
        except ValueError as e:
            print(f"❌ Export validation error: {e}", file=sys.stderr)
            return {
                "error": f"Export validation failed: {str(e)}",
                "export": None,
                "summary": ""
            }

        # Create summary
        summary = f"""HMRC CSV Export Summary
=====================
File: {safe_filename}
Period: {start_date} to {end_date}
Account: {account_id}
Transactions: {len(csv_rows)}

Totals:
- Income: £{income_total:.2f}
- Expenses: £{expense_total:.2f}
- Net: £{net_total:.2f}

Top 3 Expense Categories:
"""

        for i, (category, amount) in enumerate(top_expenses, 1):
            summary += f"{i}. {category}: £{amount:.2f}\n"

        return {
            "export": validated_export,
            "summary": summary
        }


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


def create_fastapi_app():
    """Create FastAPI application with REST API endpoints."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI dependencies not installed. Run: pip install fastapi uvicorn")

    app = FastAPI(
        title="OpenBanking MCP REST API",
        description="REST API layer for OpenBanking MCP server",
        version="1.0.0"
    )

    # Add CORS middleware for web client
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create MCP server instance for API calls
    mcp_server = MCPServer()

    @app.get("/api/accounts")
    async def get_accounts():
        """Get list of accounts."""
        try:
            result = mcp_server._list_accounts()
            validated_result = validate_tool_output("list_accounts", result)
            return JSONResponse(content=validated_result)
        except Exception as e:
            print(f"❌ API Error in get_accounts: {e}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/api/transactions")
    async def get_transactions(
        account_id: str = Query(..., description="Account ID"),
        start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
        end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
        limit: int = Query(50, ge=1, le=500, description="Maximum number of transactions"),
        page: int = Query(1, ge=1, description="Page number")
    ):
        """Get transactions for a specific account within a date range."""
        try:
            # Validate date format
            if not mcp_server._validate_date_format(start_date) or not mcp_server._validate_date_format(end_date):
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

            result = mcp_server._list_transactions({
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "offset": 0
            })
            validated_result = validate_tool_output("list_transactions", result)
            return JSONResponse(content=validated_result)
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ API Error in get_transactions: {e}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/api/exports/hmrc")
    async def export_hmrc_csv(
        account_id: str = Query(..., description="Account ID"),
        start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
        end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
        filename: Optional[str] = Query(None, description="Optional filename for CSV export")
    ):
        """Export transactions as HMRC-ready CSV."""
        try:
            # Validate date format
            if not mcp_server._validate_date_format(start_date) or not mcp_server._validate_date_format(end_date):
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

            result = mcp_server._export_hmrc_csv(account_id, start_date, end_date, filename)
            validated_result = validate_tool_output("export_hmrc_csv", result)

            # Check if export was successful
            if "error" in validated_result:
                raise HTTPException(status_code=500, detail=validated_result["error"])

            # Return metadata about the export
            export_data = validated_result.get("export", {})
            if export_data and "csv_path" in export_data:
                csv_path = export_data["csv_path"]
                return JSONResponse(content={
                    "path": csv_path,
                    "total_transactions": export_data.get("metadata", {}).get("transaction_count", 0),
                    "total_amount": export_data.get("metadata", {}).get("net_total", 0),
                    "summary": validated_result.get("summary", "")
                })
            else:
                raise HTTPException(status_code=500, detail="Export failed - no CSV file generated")

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ API Error in export_hmrc_csv: {e}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/api/exports/hmrc/download")
    async def download_hmrc_csv(
        account_id: str = Query(..., description="Account ID"),
        start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
        end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
        filename: Optional[str] = Query(None, description="Optional filename for CSV export")
    ):
        """Download HMRC CSV file directly."""
        try:
            # Validate date format
            if not mcp_server._validate_date_format(start_date) or not mcp_server._validate_date_format(end_date):
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

            result = mcp_server._export_hmrc_csv(account_id, start_date, end_date, filename)
            validated_result = validate_tool_output("export_hmrc_csv", result)

            # Check if export was successful
            if "error" in validated_result:
                raise HTTPException(status_code=500, detail=validated_result["error"])

            # Return the CSV file
            export_data = validated_result.get("export", {})
            if export_data and "csv_path" in export_data:
                csv_path = export_data["csv_path"]
                if os.path.exists(csv_path):
                    return FileResponse(
                        path=csv_path,
                        filename=os.path.basename(csv_path),
                        media_type="text/csv"
                    )
                else:
                    raise HTTPException(status_code=404, detail="CSV file not found")
            else:
                raise HTTPException(status_code=500, detail="Export failed - no CSV file generated")

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ API Error in download_hmrc_csv: {e}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    return app


def run_rest_api_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI REST API server."""
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI not available. Install with: pip install fastapi uvicorn", file=sys.stderr)
        return

    app = create_fastapi_app()
    print(f"🚀 Starting REST API server on http://{host}:{port}", file=sys.stderr)
    print(f"📋 Available endpoints:", file=sys.stderr)
    print(f"   GET  /api/accounts", file=sys.stderr)
    print(f"   GET  /api/transactions", file=sys.stderr)
    print(f"   GET  /api/exports/hmrc", file=sys.stderr)
    print(f"   GET  /api/exports/hmrc/download", file=sys.stderr)
    print(f"   GET  /health", file=sys.stderr)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Check if we should run REST API or MCP server
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        run_rest_api_server()
    else:
        run_mcp_server()