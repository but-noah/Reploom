"""Auth0 Token Vault integration for third-party API access.

This module provides secure token exchange functionality using Auth0's Token Vault,
allowing the application to obtain access tokens for external APIs (e.g., Gmail)
on behalf of authenticated users without storing provider refresh tokens.
"""

import logging
from typing import Any
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.tracing import get_tracer, safe_span_attributes
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class TokenExchangeError(Exception):
    """Base exception for token exchange errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "token_exchange_error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class InsufficientScopeError(TokenExchangeError):
    """Raised when user has not granted required scopes."""

    def __init__(self, message: str = "User has not granted required Gmail permissions"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="insufficient_scope"
        )


class InvalidGrantError(TokenExchangeError):
    """Raised when the grant is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired authorization grant"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="invalid_grant"
        )


async def get_google_access_token(user_sub: str, scopes: list[str]) -> str:
    """Exchange Auth0 session for Google access token via Token Vault.

    This function uses Auth0's Token Vault to securely obtain a Google access token
    for the authenticated user. The Token Vault manages the OAuth2 flow with Google
    and handles refresh token rotation, so we never store provider credentials.

    Args:
        user_sub: The Auth0 user identifier (sub claim from JWT)
        scopes: List of Google API scopes required (e.g., ["https://www.googleapis.com/auth/gmail.readonly"])

    Returns:
        str: A valid Google access token

    Raises:
        TokenExchangeError: If token exchange fails
        InsufficientScopeError: If user hasn't granted required scopes (403)
        InvalidGrantError: If the authorization grant is invalid/expired (401)
        HTTPException: For other errors (network, configuration, etc.)

    Example:
        >>> token = await get_google_access_token(
        ...     user_sub="auth0|123456",
        ...     scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        ... )
        >>> # Use token to call Gmail API
    """
    with tracer.start_as_current_span("token_exchange.get_google_access_token") as span:
        # Set span attributes (user_sub will be masked by safe_span_attributes)
        span.set_attributes(safe_span_attributes(
            user_sub=user_sub,
            scopes_count=len(scopes),
            provider="google"
        ))

        # Validate configuration
        if not all([
            settings.AUTH0_DOMAIN,
            settings.AUTH0_CUSTOM_API_CLIENT_ID,
            settings.AUTH0_CUSTOM_API_CLIENT_SECRET,
            settings.AUTH0_AUDIENCE
        ]):
            logger.error("Missing Auth0 Token Vault configuration")
            span.set_status(Status(StatusCode.ERROR, "Missing configuration"))
            raise HTTPException(
                status_code=500,
                detail="Token exchange service is not configured. Please contact support."
            )

        # Prepare token exchange request
        token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
        scope_string = " ".join(scopes)

        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": settings.AUTH0_CUSTOM_API_CLIENT_ID,
            "client_secret": settings.AUTH0_CUSTOM_API_CLIENT_SECRET,
            "audience": settings.AUTH0_AUDIENCE,
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "subject_token": user_sub,  # Use user_sub to identify the user
            "scope": scope_string,
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token"
        }

        # Log the request (redact sensitive data)
        logger.info(
            "Initiating token exchange",
            extra={
                "user_sub": user_sub[:8] + "..." if len(user_sub) > 8 else "[redacted]",
                "scopes": scopes,
                "domain": settings.AUTH0_DOMAIN
            }
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )

                # Handle specific error cases
                if response.status_code == 401:
                    error_data = response.json() if response.content else {}
                    error_description = error_data.get("error_description", "")

                    logger.warning(
                        "Token exchange failed: Unauthorized",
                        extra={
                            "user_sub": user_sub[:8] + "...",
                            "error": error_data.get("error"),
                            "error_description": error_description
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, "Unauthorized"))
                    span.set_attribute("error.type", "invalid_grant")

                    raise InvalidGrantError(
                        message=f"Authorization failed: {error_description or 'Invalid credentials'}"
                    )

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_description = error_data.get("error_description", "")

                    logger.warning(
                        "Token exchange failed: Insufficient scope",
                        extra={
                            "user_sub": user_sub[:8] + "...",
                            "requested_scopes": scopes,
                            "error_description": error_description
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, "Insufficient scope"))
                    span.set_attribute("error.type", "insufficient_scope")

                    # Check for specific scope-related errors
                    if "scope" in error_description.lower() or "permission" in error_description.lower():
                        raise InsufficientScopeError(
                            message="Please reconnect your Gmail account and grant the required permissions"
                        )

                    raise TokenExchangeError(
                        message=f"Access denied: {error_description}",
                        status_code=403,
                        error_code="access_denied"
                    )

                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error_description", "Unknown error")

                    logger.error(
                        "Token exchange failed",
                        extra={
                            "status_code": response.status_code,
                            "error": error_data.get("error"),
                            "error_description": error_msg
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    span.set_attribute("http.status_code", response.status_code)

                    raise TokenExchangeError(
                        message=f"Token exchange failed: {error_msg}",
                        status_code=response.status_code,
                        error_code=error_data.get("error", "token_exchange_error")
                    )

                # Success case
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    logger.error("Token exchange response missing access_token field")
                    span.set_status(Status(StatusCode.ERROR, "Missing access token"))
                    raise TokenExchangeError(
                        message="Invalid token response from authorization server",
                        status_code=500,
                        error_code="invalid_token_response"
                    )

                # Log success (never log the actual token)
                logger.info(
                    "Token exchange successful",
                    extra={
                        "user_sub": user_sub[:8] + "...",
                        "token_type": token_data.get("token_type", "Bearer"),
                        "expires_in": token_data.get("expires_in")
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("token_type", token_data.get("token_type", "Bearer"))
                if token_data.get("expires_in"):
                    span.set_attribute("expires_in_seconds", token_data.get("expires_in"))

                return access_token

        except httpx.TimeoutException:
            logger.error("Token exchange timeout", extra={"user_sub": user_sub[:8] + "..."})
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            span.set_attribute("error.type", "timeout")
            raise HTTPException(
                status_code=504,
                detail="Token exchange service timeout. Please try again."
            )
        except httpx.RequestError as e:
            logger.error(
                "Token exchange network error",
                extra={"user_sub": user_sub[:8] + "...", "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            span.set_attribute("error.type", "network_error")
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to authorization service. Please try again later."
            )
        except (InsufficientScopeError, InvalidGrantError, TokenExchangeError):
            # Re-raise our custom exceptions (span status already set)
            raise
        except Exception as e:
            logger.exception(
                "Unexpected error during token exchange",
                extra={"user_sub": user_sub[:8] + "...", "error_type": type(e).__name__}
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            span.set_attribute("error.type", type(e).__name__)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )
