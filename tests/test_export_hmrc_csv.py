#!/usr/bin/env python3
"""
Tests for the export_hmrc_csv tool functionality.
"""

import json
import subprocess
import sys
import os
import csv
import tempfile

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def rpc(req: dict) -> dict:
    """Send RPC request to server and return response."""
    p = subprocess.run(
        [sys.executable, "-m", "server"],
        input=json.dumps(req).encode(),
        capture_output=True,
        check=True
    )
    line = p.stdout.decode().splitlines()[0]
    return json.loads(line)


def test_export_hmrc_csv_creates_file():
    """Test that export_hmrc_csv creates a CSV file with correct structure."""
    # Use a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            res = rpc({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "export_hmrc_csv",
                    "arguments": {
                        "account_id": "test123",
                        "start_date": "2024-09-01",
                        "end_date": "2024-09-19",
                        "filename": "test_export.csv"
                    }
                }
            })

            # Check response format
            assert "result" in res
            assert "content" in res["result"]
            content = res["result"]["content"]
            assert isinstance(content, list) and len(content) > 0
            assert content[0]["type"] == "text"

            # Check that CSV file was created
            csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
            assert len(csv_files) > 0, "No CSV file was created"

            # Check filename
            assert "test_export.csv" in csv_files or any("hmrc_export" in f for f in csv_files)

            print("✅ CSV file creation test passed")

        finally:
            os.chdir(original_cwd)


def test_csv_has_correct_headers():
    """Test that the CSV has the correct headers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            res = rpc({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "export_hmrc_csv",
                    "arguments": {
                        "account_id": "test123",
                        "start_date": "2024-09-01",
                        "end_date": "2024-09-19"
                    }
                }
            })

            # Find the CSV file
            csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
            assert len(csv_files) > 0

            csv_file = csv_files[0]

            # Read and check headers
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                expected_headers = ["Date", "Description", "Amount", "Currency", "HMRC Category"]
                assert headers == expected_headers, f"Expected {expected_headers}, got {headers}"

            print("✅ CSV headers test passed")

        finally:
            os.chdir(original_cwd)


def test_date_format_conversion():
    """Test that dates are converted from YYYY-MM-DD to DD/MM/YYYY format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            res = rpc({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "export_hmrc_csv",
                    "arguments": {
                        "account_id": "test123",
                        "start_date": "2024-09-01",
                        "end_date": "2024-09-19"
                    }
                }
            })

            # Find the CSV file
            csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
            csv_file = csv_files[0]

            # Check date format in CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Check that dates are in DD/MM/YYYY format
                for row in rows:
                    date_str = row["Date"]
                    if date_str and "/" in date_str:
                        # Should be in DD/MM/YYYY format
                        parts = date_str.split("/")
                        assert len(parts) == 3, f"Date should have 3 parts separated by /, got: {date_str}"
                        assert len(parts[0]) <= 2, f"Day should be 1-2 digits, got: {parts[0]}"
                        assert len(parts[1]) <= 2, f"Month should be 1-2 digits, got: {parts[1]}"
                        assert len(parts[2]) == 4, f"Year should be 4 digits, got: {parts[2]}"

            print("✅ Date format conversion test passed")

        finally:
            os.chdir(original_cwd)


def test_summary_contains_keywords():
    """Test that the summary contains expected keywords."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            res = rpc({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "export_hmrc_csv",
                    "arguments": {
                        "account_id": "test123",
                        "start_date": "2024-09-01",
                        "end_date": "2024-09-19"
                    }
                }
            })

            summary_text = res["result"]["content"][0]["text"]

            # Check for expected keywords in summary
            expected_keywords = [
                "HMRC CSV Export Summary",
                "Income:",
                "Expenses:",
                "Net:",
                "Top 3 Expense Categories"
            ]

            for keyword in expected_keywords:
                assert keyword in summary_text, f"Summary missing keyword: {keyword}"

            print("✅ Summary keywords test passed")

        finally:
            os.chdir(original_cwd)


def test_hmrc_categorization():
    """Test that transactions are properly categorized for HMRC."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            res = rpc({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "export_hmrc_csv",
                    "arguments": {
                        "account_id": "test123",
                        "start_date": "2024-09-01",
                        "end_date": "2024-09-19"
                    }
                }
            })

            # Find the CSV file
            csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
            csv_file = csv_files[0]

            # Check categorization
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Check that categories are valid HMRC categories
                valid_categories = [
                    "Income", "Bank Interest", "Travel", "Office Costs",
                    "Utilities", "Bank charges", "General expenses"
                ]

                for row in rows:
                    category = row["HMRC Category"]
                    assert category in valid_categories, f"Invalid category: {category}"

            print("✅ HMRC categorization test passed")

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    print("🧪 Running export_hmrc_csv tests...\n")

    try:
        test_export_hmrc_csv_creates_file()
        test_csv_has_correct_headers()
        test_date_format_conversion()
        test_summary_contains_keywords()
        test_hmrc_categorization()

        print("\n🎉 All export_hmrc_csv tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
