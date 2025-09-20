# OpenBanking MCP Web Integration

This document describes the integration between the OpenBanking MCP server and the Next.js web client.

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/REST    ┌─────────────────┐
│   Next.js Web   │ ──────────────► │   FastAPI REST  │
│   Client        │                 │   API Server    │
│   (Port 3000)   │                 │   (Port 8000)   │
└─────────────────┘                 └─────────────────┘
                                           │
                                           ▼
                                    ┌─────────────────┐
                                    │   MCP Server    │
                                    │   (Core Logic)  │
                                    └─────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
cd web
npm install
```

### 2. Start the REST API Server

```bash
# Start the FastAPI REST API server
python server.py api
```

The server will start on `http://localhost:8000` with the following endpoints:
- `GET /api/accounts` - List accounts
- `GET /api/transactions` - Get transactions
- `GET /api/exports/hmrc` - Export HMRC CSV (metadata)
- `GET /api/exports/hmrc/download` - Download HMRC CSV file
- `GET /health` - Health check

### 3. Start the Web Client

```bash
# In a new terminal, start the Next.js development server
cd web
npm run dev
```

The web client will start on `http://localhost:3000`.

### 4. Test Integration

```bash
# Run integration tests
python test_integration.py
```

## 📋 API Endpoints

### GET /api/accounts

Returns a list of available accounts.

**Response:**
```json
{
  "accounts": [
    {
      "id": "acc001",
      "name": "Primary Current Account",
      "type": "checking",
      "currency": "GBP",
      "balance": 2847.32
    }
  ]
}
```

### GET /api/transactions

Get transactions for a specific account within a date range.

**Parameters:**
- `account_id` (required): Account ID
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `limit` (optional): Maximum transactions to return (default: 50)
- `page` (optional): Page number (default: 1)

**Response:**
```json
{
  "transactions": [
    {
      "id": "txn_001",
      "date": "2025-09-15",
      "description": "TESCO STORES 1234 LONDON",
      "amount": -45.50,
      "direction": "debit",
      "account_id": "business",
      "category": "groceries"
    }
  ],
  "pagination": {
    "total": 25,
    "page": 1,
    "limit": 50,
    "has_more": false
  }
}
```

### GET /api/exports/hmrc

Export transactions as HMRC-ready CSV and return metadata.

**Parameters:**
- `account_id` (required): Account ID
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `filename` (optional): Custom filename for CSV

**Response:**
```json
{
  "path": "hmrc_export_business_2025-09-01_2025-09-30.csv",
  "total_transactions": 25,
  "total_amount": 1250.75,
  "summary": "HMRC CSV Export Summary\n..."
}
```

### GET /api/exports/hmrc/download

Download HMRC CSV file directly.

**Parameters:** Same as `/api/exports/hmrc`

**Response:** CSV file download

## 🧪 Testing

### Run API Tests

```bash
# Run all API integration tests
pytest tests/test_api_*.py -v

# Run specific test file
pytest tests/test_api_accounts.py -v
```

### Run Integration Test

```bash
# Test end-to-end integration
python test_integration.py
```

## 🔧 Development

### Adding New Endpoints

1. Add the endpoint to `create_fastapi_app()` in `server.py`
2. Create corresponding tests in `tests/test_api_*.py`
3. Update the web client API client in `web/lib/api.ts`
4. Update the web UI to use the new endpoint

### Error Handling

The API uses standard HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `422` - Validation Error (missing required parameters)
- `500` - Internal Server Error

All errors return JSON with a `detail` field containing the error message.

### CORS Configuration

The API is configured to allow requests from:
- `http://localhost:3000` (Next.js dev server)
- `http://127.0.0.1:3000` (Alternative localhost)

## 📁 File Structure

```
├── server.py                 # Main MCP server + FastAPI REST API
├── requirements.txt          # Python dependencies
├── test_integration.py      # Integration test script
├── tests/
│   ├── test_api_accounts.py     # Accounts API tests
│   ├── test_api_transactions.py # Transactions API tests
│   └── test_api_exports.py      # Export API tests
└── web/
    ├── lib/
    │   └── api.ts               # API client
    ├── app/
    │   └── page.tsx            # Main web interface
    └── package.json            # Node.js dependencies
```

## 🐛 Troubleshooting

### Common Issues

1. **"Cannot connect to API server"**
   - Make sure the REST API server is running: `python server.py api`
   - Check that port 8000 is not in use by another process

2. **"CORS error"**
   - The API server includes CORS middleware for localhost:3000
   - If using a different port, update the CORS configuration in `server.py`

3. **"No transactions found"**
   - The system uses mock data by default
   - Check that the date range is valid (YYYY-MM-DD format)
   - Verify the account ID exists

4. **"CSV export failed"**
   - Check file permissions in the current directory
   - Ensure the server has write access to create CSV files

### Debug Mode

Enable debug logging by setting environment variables:

```bash
export TRUELAYER_DEBUG_PAYLOADS=1
python server.py api
```

## 🔄 Data Flow

1. **Web Client** → **REST API** → **MCP Server** → **Data Source**
2. **Data Source** → **MCP Server** → **Schema Validation** → **REST API** → **Web Client**

The MCP server handles:
- Data fetching (TrueLayer API or mock data)
- Schema validation
- Data normalization
- CSV generation

The REST API provides:
- HTTP endpoints
- Request validation
- Error handling
- CORS support

The Web Client provides:
- User interface
- API integration
- File downloads
- Data visualization

## 📝 Notes

- The system uses mock data by default for development
- Real TrueLayer integration requires API credentials
- All data is validated against schemas before returning
- CSV exports are generated server-side and downloaded client-side
- The integration maintains the same data flow as the original MCP tools
