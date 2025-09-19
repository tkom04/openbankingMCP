# Open Banking MCP Server Setup

## Quick Start

1. **Set Python Path (Windows)**:
   ```powershell
   # If you get "Python was not found" errors, set this:
   set PY_CMD=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
   ```

2. **Set Environment Variables**:
   ```powershell
   # Optional: Set TrueLayer credentials
   set TRUELAYER_CLIENT_ID=your_client_id_here
   set TRUELAYER_CLIENT_SECRET=your_client_secret_here
   set REDIRECT_URI=http://localhost:8080/callback
   ```

3. **Test the Server**:
   ```powershell
   # Run schema tests
   py test_schema.py
   
   # Test MCP server directly
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | py server.py
   ```

4. **Open Cursor** - The MCP server should now appear in Cursor's tools!

## Available Tools

- `create_data_auth_link` - Create OAuth authorization URL
- `exchange_code` - Exchange OAuth code for tokens  
- `get_accounts` - List bank accounts
- `get_transactions` - Get transactions for an account

## Troubleshooting

- **"0 tools" in Cursor**: Check server logs in Cursor's output panel
- **Python not found**: Set `PY_CMD` environment variable to full Python path
- **Schema errors**: Run `py test_schema.py` to validate

## Files

- `server.py` - Main MCP server
- `validate.py` - Schema validation utilities  
- `test_schema.py` - Compliance tests
- `.cursor/mcp.json` - Cursor configuration
