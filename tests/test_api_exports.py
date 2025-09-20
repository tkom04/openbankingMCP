"""
Integration tests for /api/exports/hmrc endpoint.
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from openbankingmcp.server import create_fastapi_app


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_fastapi_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_export_hmrc_csv_success(client):
    """Test successful HMRC CSV export."""
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200

    data = response.json()
    assert "path" in data
    assert "total_transactions" in data
    assert "total_amount" in data
    assert "summary" in data

    # Validate data types
    assert isinstance(data["path"], str)
    assert isinstance(data["total_transactions"], int)
    assert isinstance(data["total_amount"], (int, float))
    assert isinstance(data["summary"], str)

    # Check that CSV file was created
    assert os.path.exists(data["path"])
    assert data["path"].endswith(".csv")


def test_export_hmrc_csv_with_filename(client):
    """Test HMRC CSV export with custom filename."""
    custom_filename = "test_export.csv"
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "filename": custom_filename
    })

    assert response.status_code == 200

    data = response.json()
    assert "path" in data

    # Check that filename was used (may be sanitized)
    assert "test_export" in data["path"]
    assert data["path"].endswith(".csv")


def test_export_hmrc_csv_response_format(client):
    """Test that export response matches expected format."""
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200
    data = response.json()

    # Required fields
    required_fields = ["path", "total_transactions", "total_amount", "summary"]
    for field in required_fields:
        assert field in data

    # Validate values
    assert data["path"] != ""
    assert data["total_transactions"] >= 0
    assert isinstance(data["total_amount"], (int, float))
    assert data["summary"] != ""

    # Summary should contain key information
    summary = data["summary"]
    assert "HMRC CSV Export Summary" in summary
    assert "business" in summary
    assert "2025-09-01" in summary
    assert "2025-09-30" in summary


def test_export_hmrc_csv_invalid_date_format(client):
    """Test export endpoint with invalid date format."""
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "01/09/2025",  # Wrong format
        "end_date": "30/09/2025"     # Wrong format
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid date format" in data["detail"]


def test_export_hmrc_csv_missing_params(client):
    """Test export endpoint with missing required parameters."""
    # Missing account_id
    response = client.get("/api/exports/hmrc", params={
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })
    assert response.status_code == 422  # FastAPI validation error

    # Missing start_date
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "end_date": "2025-09-30"
    })
    assert response.status_code == 422  # FastAPI validation error

    # Missing end_date
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "2025-09-01"
    })
    assert response.status_code == 422  # FastAPI validation error


def test_download_hmrc_csv_success(client):
    """Test successful HMRC CSV download."""
    response = client.get("/api/exports/hmrc/download", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    # Check that response contains CSV data
    content = response.text
    assert "Date" in content
    assert "Description" in content
    assert "Amount" in content
    assert "Currency" in content
    assert "HMRC Category" in content


def test_download_hmrc_csv_with_filename(client):
    """Test HMRC CSV download with custom filename."""
    custom_filename = "custom_export.csv"
    response = client.get("/api/exports/hmrc/download", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "filename": custom_filename
    })

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    # Check filename in content-disposition header
    content_disposition = response.headers.get("content-disposition", "")
    assert "custom_export" in content_disposition


def test_csv_file_content_structure(client):
    """Test that generated CSV file has correct structure."""
    response = client.get("/api/exports/hmrc/download", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200

    # Parse CSV content
    lines = response.text.strip().split('\n')
    assert len(lines) > 1  # Header + at least one data row

    # Check header
    header = lines[0]
    expected_columns = ["Date", "Description", "Amount", "Currency", "HMRC Category"]
    for column in expected_columns:
        assert column in header

    # Check data rows
    for line in lines[1:]:
        if line.strip():  # Skip empty lines
            columns = line.split(',')
            assert len(columns) >= 5  # Should have at least 5 columns

            # Check that Amount is numeric
            amount_str = columns[2].strip().replace('"', '')
            try:
                float(amount_str)
            except ValueError:
                pytest.fail(f"Amount column is not numeric: {amount_str}")


def test_export_creates_valid_csv_file(client):
    """Test that export creates a valid CSV file on disk."""
    response = client.get("/api/exports/hmrc", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200
    data = response.json()

    csv_path = data["path"]
    assert os.path.exists(csv_path)

    # Read and validate CSV file
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.strip().split('\n')
    assert len(lines) > 1  # Header + data

    # Check header
    header = lines[0]
    assert "Date" in header
    assert "Description" in header
    assert "Amount" in header
    assert "Currency" in header
    assert "HMRC Category" in header

    # Clean up
    if os.path.exists(csv_path):
        os.remove(csv_path)
