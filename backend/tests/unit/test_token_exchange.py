"""Unit tests for Auth0 Token Vault token exchange functionality.

These tests verify the token exchange logic with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException

from app.auth.token_exchange import (
    get_google_access_token,
    TokenExchangeError,
    InsufficientScopeError,
    InvalidGrantError,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_success():
    """Test successful token exchange returns access token."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    expected_token = "ya29.mock-google-access-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": expected_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await get_google_access_token(user_sub, scopes)

        assert result == expected_token
        assert mock_client.post.called
        call_args = mock_client.post.call_args

        # Verify the request parameters
        assert "oauth/token" in call_args.args[0]
        assert call_args.kwargs["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
        assert call_args.kwargs["data"]["scope"] == " ".join(scopes)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_insufficient_scope():
    """Test 403 error raises InsufficientScopeError."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.content = b'{"error": "access_denied", "error_description": "Insufficient scope"}'
    mock_response.json.return_value = {
        "error": "access_denied",
        "error_description": "Insufficient scope for requested operation",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(InsufficientScopeError) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.message.lower() or "scope" in exc_info.value.message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_invalid_grant():
    """Test 401 error raises InvalidGrantError."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.content = b'{"error": "invalid_grant", "error_description": "Grant is invalid"}'
    mock_response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "Grant is invalid or expired",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(InvalidGrantError) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_missing_config():
    """Test missing configuration raises HTTPException."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    with patch("app.auth.token_exchange.settings") as mock_settings:
        mock_settings.AUTH0_DOMAIN = ""
        mock_settings.AUTH0_CUSTOM_API_CLIENT_ID = ""
        mock_settings.AUTH0_CUSTOM_API_CLIENT_SECRET = ""
        mock_settings.AUTH0_AUDIENCE = ""

        with pytest.raises(HTTPException) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_timeout():
    """Test timeout raises HTTPException with 504."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert exc_info.value.status_code == 504
        assert "timeout" in exc_info.value.detail.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_network_error():
    """Test network error raises HTTPException with 503."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Network error"))
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert exc_info.value.status_code == 503
        assert "connect" in exc_info.value.detail.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_missing_access_token_in_response():
    """Test response without access_token field raises error."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token_type": "Bearer",
        "expires_in": 3600,
        # Missing access_token field
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(TokenExchangeError) as exc_info:
            await get_google_access_token(user_sub, scopes)

        assert "invalid_token_response" in exc_info.value.error_code
        assert exc_info.value.status_code == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_google_access_token_logs_without_tokens():
    """Test that access tokens are never logged (security check)."""
    user_sub = "auth0|123456"
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    secret_token = "ya29.secret-should-never-appear-in-logs"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": secret_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("app.auth.token_exchange.logger") as mock_logger:
            result = await get_google_access_token(user_sub, scopes)

            assert result == secret_token

            # Check that no log call contains the actual token
            for call in mock_logger.info.call_args_list:
                args_str = str(call)
                assert secret_token not in args_str, "Secret token found in logs!"

            for call in mock_logger.error.call_args_list:
                args_str = str(call)
                assert secret_token not in args_str, "Secret token found in error logs!"
