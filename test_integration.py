#!/usr/bin/env python3
"""
Integration test script to verify REST API endpoints work correctly.
Run this after starting the REST API server with: python server.py api
"""
import requests
import json
import sys
from datetime import datetime, timedelta


def test_api_endpoints():
    """Test all REST API endpoints."""
    base_url = "http://localhost:8000"

    print("🧪 Testing OpenBanking MCP REST API Integration")
    print("=" * 50)

    # Test health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running with: python server.py api")
        return False

    # Test accounts endpoint
    print("\n2. Testing accounts endpoint...")
    try:
        response = requests.get(f"{base_url}/api/accounts")
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", [])
            print(f"✅ Accounts endpoint returned {len(accounts)} accounts")
            for account in accounts:
                print(f"   - {account['name']} ({account['id']}): £{account['balance']}")
        else:
            print(f"❌ Accounts endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Accounts endpoint error: {e}")
        return False

    # Test transactions endpoint
    print("\n3. Testing transactions endpoint...")
    try:
        # Use a recent date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        response = requests.get(f"{base_url}/api/transactions", params={
            "account_id": "business",
            "start_date": start_date,
            "end_date": end_date,
            "limit": 10
        })

        if response.status_code == 200:
            data = response.json()
            transactions = data.get("transactions", [])
            pagination = data.get("pagination", {})
            print(f"✅ Transactions endpoint returned {len(transactions)} transactions")
            print(f"   Total: {pagination.get('total', 0)}, Page: {pagination.get('page', 1)}")

            if transactions:
                print("   Sample transaction:")
                tx = transactions[0]
                print(f"   - {tx['date']}: {tx['description']} (£{tx['amount']})")
        else:
            print(f"❌ Transactions endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Transactions endpoint error: {e}")
        return False

    # Test HMRC export endpoint
    print("\n4. Testing HMRC export endpoint...")
    try:
        response = requests.get(f"{base_url}/api/exports/hmrc", params={
            "account_id": "business",
            "start_date": start_date,
            "end_date": end_date
        })

        if response.status_code == 200:
            data = response.json()
            print(f"✅ HMRC export endpoint successful")
            print(f"   CSV path: {data.get('path', 'N/A')}")
            print(f"   Total transactions: {data.get('total_transactions', 0)}")
            print(f"   Total amount: £{data.get('total_amount', 0):.2f}")

            # Check if CSV file exists
            csv_path = data.get('path')
            if csv_path:
                import os
                if os.path.exists(csv_path):
                    print(f"   ✅ CSV file created successfully")
                else:
                    print(f"   ⚠️ CSV file not found at {csv_path}")
        else:
            print(f"❌ HMRC export endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ HMRC export endpoint error: {e}")
        return False

    # Test CSV download endpoint
    print("\n5. Testing CSV download endpoint...")
    try:
        response = requests.get(f"{base_url}/api/exports/hmrc/download", params={
            "account_id": "business",
            "start_date": start_date,
            "end_date": end_date
        })

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'text/csv' in content_type:
                print(f"✅ CSV download endpoint successful")
                print(f"   Content-Type: {content_type}")
                print(f"   Content length: {len(response.content)} bytes")

                # Check CSV content
                csv_content = response.text
                lines = csv_content.strip().split('\n')
                print(f"   CSV rows: {len(lines)}")

                if len(lines) > 1:
                    header = lines[0]
                    print(f"   CSV header: {header}")
            else:
                print(f"❌ CSV download returned wrong content type: {content_type}")
                return False
        else:
            print(f"❌ CSV download endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ CSV download endpoint error: {e}")
        return False

    print("\n" + "=" * 50)
    print("🎉 All integration tests passed!")
    print("\nNext steps:")
    print("1. Start the web client: cd web && npm run dev")
    print("2. Open http://localhost:3000 in your browser")
    print("3. Select an account and date range to view transactions")
    print("4. Click 'Export HMRC CSV' to download the CSV file")

    return True


if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)
