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
        if not cid or not secret:
            return None

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
            return json.loads(resp.read().decode()).get("access_token")

    def _fetch_truelayer_accounts(self, token):
        url = "https://api.truelayer-sandbox.com/data/v1/accounts"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            raw = json.loads(resp.read().decode())
            return raw.get("results", [])

    def _get_accounts_data(self):
        token = self._get_truelayer_token()
        if token:
            try:
                return self._fetch_truelayer_accounts(token)
            except Exception as e:
                print(f"TrueLayer API error: {e}")
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
