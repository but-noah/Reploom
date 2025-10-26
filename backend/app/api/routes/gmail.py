"""Gmail API integration routes.

This module provides endpoints for interacting with Gmail via Auth0 Token Vault.
Access tokens are obtained securely without storing provider refresh tokens.
"""

import logging
from typing import Any
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import auth_client
from app.core.config import settings
from app.auth.token_exchange import (
    get_google_access_token,
    TokenExchangeError,
    InsufficientScopeError,
    InvalidGrantError,
)

logger = logging.getLogger(__name__)

gmail_router = APIRouter(prefix="/me/gmail", tags=["gmail"])


class GmailLabel(BaseModel):
    """Gmail label model."""
    id: str
    name: str
    type: str
    messageListVisibility: str | None = None
    labelListVisibility: str | None = None


class GmailLabelsResponse(BaseModel):
    """Response model for Gmail labels endpoint."""
    labels: list[GmailLabel]
    scope: list[str]
    user: dict[str, Any]


@gmail_router.get("/labels", response_model=GmailLabelsResponse)
async def list_gmail_labels(
    auth_session=Depends(auth_client.require_session),
) -> GmailLabelsResponse:
    """List Gmail labels for the authenticated user.

    This endpoint demonstrates secure integration with Gmail API via Auth0 Token Vault.
    It exchanges the user's Auth0 session for a Google access token and retrieves
    the user's Gmail labels.

    Security features:
    - No provider refresh tokens stored in our application
    - Access tokens obtained on-demand via Auth0 Token Vault
    - Tokens never logged or exposed in responses
    - Comprehensive error handling with user-friendly messages

    Required setup:
    - User must have connected Gmail via Auth0 Social Connection
    - Required scopes: gmail.readonly, gmail.modify, gmail.compose
    - Auth0 Token Vault must be configured

    Returns:
        GmailLabelsResponse: Contains labels, granted scopes, and user info

    Raises:
        HTTPException 401: Invalid or expired authorization
        HTTPException 403: Insufficient Gmail permissions
        HTTPException 429: Gmail API rate limit exceeded
        HTTPException 500: Configuration or unexpected errors
        HTTPException 503: Gmail API unavailable
        HTTPException 504: Request timeout

    Example response:
        {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "Label_123", "name": "Work", "type": "user"}
            ],
            "scope": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"
            ],
            "user": {
                "sub": "auth0|123456",
                "email": "user@example.com"
            }
        }
    """
    user = auth_session.get("user")
    user_sub = user.get("sub")
    user_email = user.get("email", "unknown")

    logger.info(
        "Gmail labels request initiated",
        extra={
            "user_sub": user_sub[:8] + "..." if user_sub and len(user_sub) > 8 else "[redacted]",
            "user_email": user_email if user_email != "unknown" else "[redacted]"
        }
    )

    try:
        # Exchange Auth0 session for Google access token
        access_token = await get_google_access_token(
            user_sub=user_sub,
            scopes=settings.GMAIL_SCOPES_LIST
        )

        # Call Gmail API to list labels
        gmail_api_url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                gmail_api_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                },
                timeout=15.0
            )

            # Handle Gmail API errors
            if response.status_code == 401:
                logger.warning(
                    "Gmail API returned 401",
                    extra={"user_sub": user_sub[:8] + "..."}
                )
                raise HTTPException(
                    status_code=401,
                    detail="Gmail authorization expired. Please reconnect your Gmail account."
                )

            elif response.status_code == 403:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "")

                logger.warning(
                    "Gmail API returned 403",
                    extra={
                        "user_sub": user_sub[:8] + "...",
                        "error_message": error_message
                    }
                )

                # Check for specific permission errors
                if "insufficient" in error_message.lower() or "permission" in error_message.lower():
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient Gmail permissions. Please grant the required scopes and reconnect."
                    )

                raise HTTPException(
                    status_code=403,
                    detail=f"Gmail access denied: {error_message or 'Permission denied'}"
                )

            elif response.status_code == 429:
                logger.warning(
                    "Gmail API rate limit exceeded",
                    extra={"user_sub": user_sub[:8] + "..."}
                )
                raise HTTPException(
                    status_code=429,
                    detail="Gmail API rate limit exceeded. Please try again later."
                )

            elif response.status_code >= 500:
                logger.error(
                    "Gmail API server error",
                    extra={
                        "user_sub": user_sub[:8] + "...",
                        "status_code": response.status_code
                    }
                )
                raise HTTPException(
                    status_code=503,
                    detail="Gmail service is temporarily unavailable. Please try again later."
                )

            elif response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")

                logger.error(
                    "Gmail API error",
                    extra={
                        "user_sub": user_sub[:8] + "...",
                        "status_code": response.status_code,
                        "error": error_message
                    }
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Gmail API error: {error_message}"
                )

            response.raise_for_status()
            gmail_data = response.json()

            # Extract labels from response
            labels_raw = gmail_data.get("labels", [])
            labels = [
                GmailLabel(
                    id=label.get("id", ""),
                    name=label.get("name", ""),
                    type=label.get("type", ""),
                    messageListVisibility=label.get("messageListVisibility"),
                    labelListVisibility=label.get("labelListVisibility")
                )
                for label in labels_raw
            ]

            logger.info(
                "Gmail labels retrieved successfully",
                extra={
                    "user_sub": user_sub[:8] + "...",
                    "label_count": len(labels)
                }
            )

            # Return structured response
            return GmailLabelsResponse(
                labels=labels,
                scope=settings.GMAIL_SCOPES_LIST,
                user={
                    "sub": user_sub,
                    "email": user_email,
                    "name": user.get("name")
                }
            )

    except InsufficientScopeError as e:
        logger.warning(
            "Insufficient Gmail scope",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except InvalidGrantError as e:
        logger.warning(
            "Invalid Gmail grant",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except TokenExchangeError as e:
        logger.error(
            "Token exchange error",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_code": e.error_code,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except httpx.TimeoutException:
        logger.error(
            "Gmail API timeout",
            extra={"user_sub": user_sub[:8] + "..."}
        )
        raise HTTPException(
            status_code=504,
            detail="Gmail API request timeout. Please try again."
        )

    except httpx.RequestError as e:
        logger.error(
            "Gmail API network error",
            extra={"user_sub": user_sub[:8] + "...", "error": str(e)}
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to Gmail API. Please try again later."
        )

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error in Gmail labels endpoint",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again or contact support."
        )
