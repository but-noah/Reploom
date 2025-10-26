"""Integration tests for Gmail API routes.

These tests verify the end-to-end flow of the Gmail endpoints with mocked external services.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx


@pytest.mark.integration
def test_list_gmail_labels_success(client: TestClient):
    """Test successful retrieval of Gmail labels."""
    # Mock the token exchange
    mock_token = "ya29.mock-google-access-token"

    # Mock token exchange response
    mock_exchange_resp = MagicMock(spec=httpx.Response)
    mock_exchange_resp.status_code = 200
    mock_exchange_resp.content = b'{"access_token": "test"}'
    mock_exchange_resp.json.return_value = {
        "access_token": mock_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_exchange_resp.raise_for_status = MagicMock()

    # Mock Gmail API response
    mock_gmail_response = MagicMock()
    mock_gmail_response.status_code = 200
    mock_gmail_response.json.return_value = {
        "labels": [
            {
                "id": "INBOX",
                "name": "INBOX",
                "type": "system",
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
            },
            {
                "id": "SENT",
                "name": "SENT",
                "type": "system",
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
            },
            {
                "id": "Label_123",
                "name": "Work",
                "type": "user",
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
            },
        ]
    }
    mock_gmail_response.raise_for_status = MagicMock()

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        with patch("app.api.routes.gmail.httpx.AsyncClient") as mock_gmail_client:
            mock_gmail = AsyncMock()
            mock_gmail.__aenter__.return_value = mock_gmail
            mock_gmail.__aexit__.return_value = None
            mock_gmail.get = AsyncMock(return_value=mock_gmail_response)
            mock_gmail_client.return_value = mock_gmail

            response = client.get("/api/me/gmail/labels")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "labels" in data
            assert "scope" in data
            assert "user" in data

            # Verify labels
            assert len(data["labels"]) == 3
            assert data["labels"][0]["id"] == "INBOX"
            assert data["labels"][0]["name"] == "INBOX"
            assert data["labels"][0]["type"] == "system"
            assert data["labels"][2]["name"] == "Work"

            # Verify user info
            assert data["user"]["sub"] == "auth0|test-user-123456"
            assert data["user"]["email"] == "testuser@example.com"


@pytest.mark.integration
def test_list_gmail_labels_insufficient_scope(client: TestClient):
    """Test 403 error when user hasn't granted required scopes."""
    # Mock token exchange with 403 error
    mock_exchange_resp = MagicMock()
    mock_exchange_resp.status_code = 403
    mock_exchange_resp.content = b'{"error": "access_denied"}'
    mock_exchange_resp.json.return_value = {
        "error": "access_denied",
        "error_description": "Insufficient scope for the requested operation",
    }

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        response = client.get("/api/me/gmail/labels")

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"].lower() or "scope" in data["detail"].lower()


@pytest.mark.integration
def test_list_gmail_labels_invalid_grant(client: TestClient):
    """Test 401 error when authorization grant is invalid."""
    # Mock token exchange with 401 error
    mock_exchange_resp = MagicMock()
    mock_exchange_resp.status_code = 401
    mock_exchange_resp.content = b'{"error": "invalid_grant"}'
    mock_exchange_resp.json.return_value = {
        "error": "invalid_grant",
        "error_description": "Grant is invalid or expired",
    }

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        response = client.get("/api/me/gmail/labels")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
def test_list_gmail_labels_gmail_api_error(client: TestClient):
    """Test error handling when Gmail API returns an error."""
    mock_token = "ya29.mock-google-access-token"

    # Mock successful token exchange
    mock_exchange_resp = MagicMock()
    mock_exchange_resp.status_code = 200
    mock_exchange_resp.json.return_value = {
        "access_token": mock_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_exchange_resp.raise_for_status = MagicMock()

    # Mock Gmail API error
    mock_gmail_response = MagicMock()
    mock_gmail_response.status_code = 429
    mock_gmail_response.content = b'{"error": {"message": "Rate limit exceeded"}}'
    mock_gmail_response.json.return_value = {
        "error": {
            "code": 429,
            "message": "Rate limit exceeded",
        }
    }

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        with patch("app.api.routes.gmail.httpx.AsyncClient") as mock_gmail_client:
            mock_gmail = AsyncMock()
            mock_gmail.__aenter__.return_value = mock_gmail
            mock_gmail.__aexit__.return_value = None
            mock_gmail.get = AsyncMock(return_value=mock_gmail_response)
            mock_gmail_client.return_value = mock_gmail

            response = client.get("/api/me/gmail/labels")

            assert response.status_code == 429
            data = response.json()
            assert "detail" in data
            assert "rate limit" in data["detail"].lower()


@pytest.mark.integration
def test_list_gmail_labels_gmail_permission_error(client: TestClient):
    """Test Gmail API 403 insufficient permissions error."""
    mock_token = "ya29.mock-google-access-token"

    # Mock successful token exchange
    mock_exchange_resp = MagicMock()
    mock_exchange_resp.status_code = 200
    mock_exchange_resp.json.return_value = {
        "access_token": mock_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_exchange_resp.raise_for_status = MagicMock()

    # Mock Gmail API 403 error
    mock_gmail_response = MagicMock()
    mock_gmail_response.status_code = 403
    mock_gmail_response.content = b'{"error": {"message": "Insufficient permissions"}}'
    mock_gmail_response.json.return_value = {
        "error": {
            "code": 403,
            "message": "Insufficient permissions for the requested operation",
        }
    }

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        with patch("app.api.routes.gmail.httpx.AsyncClient") as mock_gmail_client:
            mock_gmail = AsyncMock()
            mock_gmail.__aenter__.return_value = mock_gmail
            mock_gmail.__aexit__.return_value = None
            mock_gmail.get = AsyncMock(return_value=mock_gmail_response)
            mock_gmail_client.return_value = mock_gmail

            response = client.get("/api/me/gmail/labels")

            assert response.status_code == 403
            data = response.json()
            assert "detail" in data
            assert "permission" in data["detail"].lower()


@pytest.mark.integration
def test_list_gmail_labels_returns_array_structure(client: TestClient):
    """Test that labels endpoint returns proper array structure."""
    mock_token = "ya29.mock-google-access-token"

    # Mock token exchange
    mock_exchange_resp = MagicMock()
    mock_exchange_resp.status_code = 200
    mock_exchange_resp.json.return_value = {
        "access_token": mock_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_exchange_resp.raise_for_status = MagicMock()

    # Mock Gmail API response with empty labels
    mock_gmail_response = MagicMock()
    mock_gmail_response.status_code = 200
    mock_gmail_response.json.return_value = {"labels": []}
    mock_gmail_response.raise_for_status = MagicMock()

    with patch("app.auth.token_exchange.httpx.AsyncClient") as mock_exchange_client:
        mock_ex_client = AsyncMock()
        mock_ex_client.__aenter__.return_value = mock_ex_client
        mock_ex_client.__aexit__.return_value = None
        mock_ex_client.post = AsyncMock(return_value=mock_exchange_resp)
        mock_exchange_client.return_value = mock_ex_client

        with patch("app.api.routes.gmail.httpx.AsyncClient") as mock_gmail_client:
            mock_gmail = AsyncMock()
            mock_gmail.__aenter__.return_value = mock_gmail
            mock_gmail.__aexit__.return_value = None
            mock_gmail.get = AsyncMock(return_value=mock_gmail_response)
            mock_gmail_client.return_value = mock_gmail

            response = client.get("/api/me/gmail/labels")

            assert response.status_code == 200
            data = response.json()

            # Verify it returns an array
            assert isinstance(data["labels"], list)
            assert len(data["labels"]) == 0
            assert isinstance(data["scope"], list)
            assert isinstance(data["user"], dict)
