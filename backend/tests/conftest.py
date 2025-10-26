"""Pytest configuration and shared fixtures."""

import os
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.update({
    "APP_BASE_URL": "http://localhost:8000",
    "AUTH0_DOMAIN": "test.auth0.com",
    "AUTH0_CLIENT_ID": "test-client-id",
    "AUTH0_CLIENT_SECRET": "test-client-secret",
    "AUTH0_SECRET": "test-secret-key-32-bytes-long-here",
    "AUTH0_CUSTOM_API_CLIENT_ID": "test-m2m-client-id",
    "AUTH0_CUSTOM_API_CLIENT_SECRET": "test-m2m-client-secret",
    "AUTH0_AUDIENCE": "https://test.auth0.com/api/v2/",
    "OPENAI_API_KEY": "sk-test-key",
    "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test_db",
    "REDIS_URL": "redis://localhost:6379/1",
    "FGA_STORE_ID": "test-store-id",
    "FGA_CLIENT_ID": "test-fga-client-id",
    "FGA_CLIENT_SECRET": "test-fga-client-secret",
    "GMAIL_SCOPES": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify",
})


@pytest.fixture
def mock_auth_session() -> dict[str, Any]:
    """Mock Auth0 session for testing authenticated endpoints."""
    return {
        "user": {
            "sub": "auth0|test-user-123456",
            "email": "testuser@example.com",
            "name": "Test User",
            "email_verified": True,
        },
        "token_sets": [
            {
                "access_token": "mock-auth0-access-token",
                "id_token": "mock-id-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        ],
    }


@pytest.fixture
def mock_auth_client(mock_auth_session: dict[str, Any]) -> Generator[MagicMock, None, None]:
    """Mock Auth0 client dependency for testing."""
    from app.core import auth

    original_client = auth.auth_client
    mock_client = MagicMock()

    # Create a dependency that returns the mock session
    def mock_require_session():
        return mock_auth_session

    mock_client.require_session = mock_require_session

    # Replace the auth_client
    auth.auth_client = mock_client

    yield mock_client

    # Restore original client
    auth.auth_client = original_client


@pytest.fixture
def client(mock_auth_client: MagicMock) -> TestClient:
    """Create FastAPI test client with mocked authentication."""
    from app.main import app

    return TestClient(app)
