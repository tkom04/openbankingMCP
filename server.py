"""
Minimal MCP-like server for Open Banking (TrueLayer).

Exposes:
  - GET /tools/list        → lists available tools
  - POST /call/get_accounts → returns account info

Runs with mocked data by default. If you set TRUELAYER_CLIENT_ID and
TRUELAYER_CLIENT_SECRET as environment variables, it will try to call
TrueLayer Sandbox instead.
"""

import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


def build_tools_list():
    """Describe available MCP tools with JSON schema metadata."""
    return [
        {
            "name": "get_accounts",
            "description": "List all user bank accounts.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "currency": {"type": "string"},
                        "balance": {"type": "number"},
                        "account_type": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "name",
                        "currency",
                        "balance",
                        "account_type",
                    ],
                },
            },
        },
        {
            "name": "get_transactions",
            "description": "Get transactions for a specific account within a date range.",
            "input_schema": {
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
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "account_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "description": {"type": "string"},
                        "transaction_type": {"type": "string"},
                        "merchant_name": {"type": "string"},
                        "category": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "id",
                        "account_id", 
                        "amount",
                        "currency",
                        "description",
                        "transaction_type",
                        "date",
                    ],
                },
            },
        }
    ]


class MCPRequestHandler(BaseHTTPRequestHandler):
    """Implements a tiny HTTP API for MCP."""

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- TrueLayer helpers ----------

    def _get_truelayer_token(self):
        """Exchange client credentials for access token."""
        cid = os.getenv("TRUELAYER_CLIENT_ID")
        secret = os.getenv("TRUELAYER_CLIENT_SECRET")
        
        print(f"🔍 Checking TrueLayer credentials...")
        print(f"   Client ID: {cid[:10]}..." if cid else "   Client ID: None")
        print(f"   Secret: {'***' if secret else 'None'}")
        
        if not cid or not secret:
            print("❌ Missing TrueLayer credentials")
            return None

        try:
            print("🚀 Attempting TrueLayer token exchange...")
            data = urllib.parse.urlencode(
                {
                    "grant_type": "client_credentials",
                    "client_id": cid,
                    "client_secret": secret,
                    "scope": "accounts",
                }
            ).encode()
            req = urllib.request.Request(
                "https://auth.truelayer-sandbox.com/connect/token", data=data
            )
            req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urllib.request.urlopen(req) as resp:
                response_data = json.loads(resp.read().decode())
                token = response_data.get("access_token")
                print(f"✅ TrueLayer token obtained: {token[:20]}..." if token else "❌ No token in response")
                return token
        except Exception as e:
            print(f"❌ TrueLayer token exchange failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _fetch_truelayer_accounts(self, token):
        url = "https://api.truelayer-sandbox.com/data/v1/accounts"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            raw = json.loads(resp.read().decode())
            return raw.get("results", [])

    def _fetch_truelayer_transactions(self, token, account_id, start_date, end_date):
        """Fetch transactions from TrueLayer API for a specific account and date range."""
        url = f"https://api.truelayer-sandbox.com/data/v1/accounts/{account_id}/transactions"
        params = {
            "from": start_date,
            "to": end_date
        }
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        req = urllib.request.Request(full_url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            raw = json.loads(resp.read().decode())
            return raw.get("results", [])

    def _get_accounts_data(self):
        token = self._get_truelayer_token()
        if token:
            try:
                print("🔑 TrueLayer token obtained, fetching accounts...")
                accounts = self._fetch_truelayer_accounts(token)
                print(f"✅ TrueLayer returned {len(accounts)} accounts")
                return accounts
            except Exception as e:
                import traceback
                print("❌ TrueLayer API error:", e)
                print("📋 Full traceback:")
                traceback.print_exc()
                print("🔄 Falling back to mock data...")
        else:
            print("⚠️ No TrueLayer credentials found, using mock data")
        
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

    def _get_transactions_data(self, account_id, start_date, end_date):
        """Get transactions data, trying TrueLayer first, then falling back to mock data."""
        token = self._get_truelayer_token()
        if token:
            try:
                print(f"🔑 TrueLayer token obtained, fetching transactions for {account_id} ({start_date} to {end_date})...")
                transactions = self._fetch_truelayer_transactions(token, account_id, start_date, end_date)
                print(f"✅ TrueLayer returned {len(transactions)} transactions")
                return transactions
            except Exception as e:
                import traceback
                print("❌ TrueLayer transactions API error:", e)
                print("📋 Full traceback:")
                traceback.print_exc()
                print("🔄 Falling back to mock data...")
        else:
            print("⚠️ No TrueLayer credentials found, using mock data")
        
        # Fallback mock data
        return [
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

    # ---------- HTTP Handlers ----------

    def do_GET(self):
        if self.path == "/tools/list":
            self._send_json({"tools": build_tools_list()})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/call/get_accounts":
            accounts = self._get_accounts_data()
            self._send_json(accounts)
        elif self.path == "/call/get_transactions":
            # Parse JSON body to get parameters
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    params = json.loads(post_data.decode('utf-8'))
                    account_id = params.get('account_id')
                    start_date = params.get('start_date')
                    end_date = params.get('end_date')
                    
                    if not all([account_id, start_date, end_date]):
                        self._send_json({"error": "Missing required parameters: account_id, start_date, end_date"}, 400)
                        return
                    
                    transactions = self._get_transactions_data(account_id, start_date, end_date)
                    self._send_json(transactions)
                except json.JSONDecodeError:
                    self._send_json({"error": "Invalid JSON in request body"}, 400)
            else:
                self._send_json({"error": "No request body provided"}, 400)
        else:
            self._send_json({"error": "Not found"}, 404)


def run_server():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    server = HTTPServer((host, port), MCPRequestHandler)
    print(f"MCP server running on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
