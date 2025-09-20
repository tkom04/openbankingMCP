"""
Integration tests for /api/transactions endpoint.
"""
import pytest
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


def test_get_transactions_success(client):
    """Test successful transactions retrieval."""
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200

    data = response.json()
    assert "transactions" in data
    assert "pagination" in data
    assert isinstance(data["transactions"], list)

    # Validate pagination structure
    pagination = data["pagination"]
    assert "total" in pagination
    assert "page" in pagination
    assert "limit" in pagination
    assert "has_more" in pagination

    assert isinstance(pagination["total"], int)
    assert isinstance(pagination["page"], int)
    assert isinstance(pagination["limit"], int)
    assert isinstance(pagination["has_more"], bool)


def test_get_transactions_response_format(client):
    """Test that transactions response matches expected schema."""
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "transactions" in data
    assert "pagination" in data

    # Validate each transaction
    for transaction in data["transactions"]:
        # Required fields
        assert "id" in transaction
        assert "date" in transaction
        assert "description" in transaction
        assert "amount" in transaction
        assert "direction" in transaction
        assert "account_id" in transaction
        assert "category" in transaction

        # Validate field values
        assert transaction["id"] != ""
        assert transaction["date"] != ""
        assert transaction["description"] != ""
        assert isinstance(transaction["amount"], (int, float))
        assert transaction["direction"] in ["credit", "debit"]
        assert transaction["account_id"] == "business"
        assert isinstance(transaction["category"], str)


def test_get_transactions_with_optional_params(client):
    """Test transactions endpoint with optional parameters."""
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "limit": 10,
        "page": 1
    })

    assert response.status_code == 200
    data = response.json()

    # Should respect limit parameter
    assert len(data["transactions"]) <= 10
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["page"] == 1


def test_get_transactions_invalid_date_format(client):
    """Test transactions endpoint with invalid date format."""
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "01/09/2025",  # Wrong format
        "end_date": "30/09/2025"     # Wrong format
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid date format" in data["detail"]


def test_get_transactions_missing_params(client):
    """Test transactions endpoint with missing required parameters."""
    # Missing account_id
    response = client.get("/api/transactions", params={
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })
    assert response.status_code == 422  # FastAPI validation error

    # Missing start_date
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "end_date": "2025-09-30"
    })
    assert response.status_code == 422  # FastAPI validation error

    # Missing end_date
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "2025-09-01"
    })
    assert response.status_code == 422  # FastAPI validation error


def test_get_transactions_returns_normalized_data(client):
    """Test that transactions endpoint returns normalized data from CSV or mock."""
    response = client.get("/api/transactions", params={
        "account_id": "business",
        "start_date": "2025-09-01",
        "end_date": "2025-09-30"
    })

    assert response.status_code == 200
    data = response.json()

    # Should have some transactions
    assert len(data["transactions"]) > 0

    # All transactions should have consistent structure
    for transaction in data["transactions"]:
        # Date should be in YYYY-MM-DD format
        assert len(transaction["date"]) == 10
        assert transaction["date"].count("-") == 2

        # Amount should be numeric
        assert isinstance(transaction["amount"], (int, float))

        # Direction should be valid
        assert transaction["direction"] in ["credit", "debit"]

        # Account ID should match request
        assert transaction["account_id"] == "business"
