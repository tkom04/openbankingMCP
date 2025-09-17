# Open Banking MCP Server

A Model Context Protocol (MCP) server for Open Banking integration with TrueLayer API.

## 🚀 Quick Start

### 1. Setup Credentials

Copy your real credentials to `mcp.local.json`:

```json
{
  "mcpServers": {
    "openbanking-mcp": {
      "command": "py",
      "args": ["server.py"],
      "cwd": "C:\\1 Projects\\Cursor Projects\\GPT Experimentation\\OPEN BANKING MCP BUISNESS\\openbankingMCP",
      "env": {
        "TRUELAYER_CLIENT_ID": "your-real-client-id",
        "TRUELAYER_CLIENT_SECRET": "your-real-client-secret"
      }
    }
  }
}
```

### 2. Install Dependencies

```bash
# No additional dependencies required - uses Python standard library
```

### 3. Test the Server

```bash
# Test minimal server
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | py minimal_mcp.py

# Test full server
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | py server.py
```

### 4. Configure Cursor

Use `mcp.local.json` for your local Cursor configuration (contains real credentials).

## 🛠️ Available Tools

- **`get_accounts`**: List all bank accounts
- **`get_transactions`**: Get transaction history for a specific account and date range

## 🔒 Security

- Real credentials are stored in `mcp.local.json` (gitignored)
- Placeholder credentials in `mcp.json` for version control
- Never commit real API keys or secrets

## 🐞 Debugging

If MCP tools don't appear in Cursor:

1. Check Cursor Developer Console (`Ctrl+Shift+I`)
2. Look for startup messages: `🚀 OpenBanking MCP server starting...`
3. Verify Python path and working directory in MCP config
4. Test server manually outside Cursor first