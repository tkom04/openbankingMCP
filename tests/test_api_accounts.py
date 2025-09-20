"""
Integration tests for /api/accounts endpoint.
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


def test_get_accounts_success(client):
    """Test successful accounts retrieval."""
    response = client.get("/api/accounts")

    assert response.status_code == 200

    data = response.json()
    assert "accounts" in data
    assert isinstance(data["accounts"], list)
    assert len(data["accounts"]) > 0

    # Validate account structure
    account = data["accounts"][0]
    required_fields = ["id", "name", "type", "currency", "balance"]
    for field in required_fields:
        assert field in account

    # Validate data types
    assert isinstance(account["id"], str)
    assert isinstance(account["name"], str)
    assert isinstance(account["type"], str)
    assert isinstance(account["currency"], str)
    assert isinstance(account["balance"], (int, float))


def test_get_accounts_response_format(client):
    """Test that accounts response matches expected schema."""
    response = client.get("/api/accounts")

    assert response.status_code == 200
    data = response.json()

    # Check that response structure matches LIST_ACCOUNTS_OUTPUT_SCHEMA
    assert "accounts" in data

    # Validate each account
    for account in data["accounts"]:
        # Required fields
        assert "id" in account
        assert "name" in account
        assert "type" in account
        assert "currency" in account
        assert "balance" in account

        # Validate field values
        assert account["id"] != ""
        assert account["name"] != ""
        assert account["type"] in ["checking", "savings", "credit", "investment"]
        assert account["currency"] == "GBP"
        assert isinstance(account["balance"], (int, float))
        assert account["balance"] >= 0


def test_get_accounts_returns_dummy_data(client):
    """Test that accounts endpoint returns expected dummy data."""
    response = client.get("/api/accounts")

    assert response.status_code == 200
    data = response.json()

    # Should have at least 2 dummy accounts
    assert len(data["accounts"]) >= 2

    # Check for expected dummy accounts
    account_ids = [acc["id"] for acc in data["accounts"]]
    assert "acc001" in account_ids
    assert "acc002" in account_ids

    # Find specific accounts
    acc001 = next(acc for acc in data["accounts"] if acc["id"] == "acc001")
    acc002 = next(acc for acc in data["accounts"] if acc["id"] == "acc002")

    assert acc001["name"] == "Primary Current Account"
    assert acc001["type"] == "checking"
    assert acc001["balance"] == 2847.32

    assert acc002["name"] == "Business Savings"
    assert acc002["type"] == "savings"
    assert acc002["balance"] == 15750.00
