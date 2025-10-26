"""Gmail API integration routes.

This module provides endpoints for interacting with Gmail via Auth0 Token Vault.
Access tokens are obtained securely without storing provider refresh tokens.
"""

import hashlib
import logging
from typing import Any
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import auth_client
from app.core.config import settings
from app.core.db import engine
from app.auth.token_exchange import (
    get_google_access_token,
    TokenExchangeError,
    InsufficientScopeError,
    InvalidGrantError,
)
from app.integrations.gmail_service import (
    create_reply_draft,
    get_thread,
    ThreadNotFoundError,
    InvalidMessageError,
    GmailServiceError,
)
from app.models.gmail_drafts import GmailDraft

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


class CreateDraftRequest(BaseModel):
    """Request model for creating a reply draft."""
    reply_to_msg_id: str
    subject: str | None = None
    body_html: str


class DraftResponse(BaseModel):
    """Response model for draft creation."""
    draft_id: str
    message_id: str
    thread_id: str
    subject: str
    created_at: str
    is_duplicate: bool = False


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


@gmail_router.post("/threads/{thread_id}/draft", response_model=DraftResponse)
async def create_thread_reply_draft(
    thread_id: str,
    request: CreateDraftRequest,
    auth_session=Depends(auth_client.require_session),
) -> DraftResponse:
    """Create a Gmail draft reply within an existing thread.

    This endpoint creates a properly threaded draft reply with:
    - Correct MIME formatting with In-Reply-To and References headers
    - Subject continuity (auto-adds "Re:" if missing)
    - HTML content with UTF-8 encoding
    - Idempotent behavior to prevent duplicate drafts

    The draft will appear in the same Gmail thread as the original message
    and will be ready for the user to review and send from Gmail.

    Args:
        thread_id: Gmail thread ID to reply within
        request: Draft creation request containing:
            - reply_to_msg_id: ID of the message being replied to
            - subject: Optional subject (auto-generated if None)
            - body_html: HTML content of the reply
        auth_session: Authenticated user session

    Returns:
        DraftResponse with draft details including:
            - draft_id: Gmail draft ID
            - message_id: Gmail message ID
            - thread_id: Thread ID
            - subject: Final subject used
            - created_at: Creation timestamp
            - is_duplicate: True if this was a duplicate request

    Raises:
        HTTPException 400: Invalid thread_id or message_id
        HTTPException 401: Invalid or expired authorization
        HTTPException 403: Insufficient Gmail permissions
        HTTPException 404: Thread or message not found
        HTTPException 429: Gmail API rate limit exceeded
        HTTPException 500: Configuration or unexpected errors
        HTTPException 503: Gmail API unavailable
        HTTPException 504: Request timeout

    Example request:
        POST /api/me/gmail/threads/thread_123/draft
        {
            "reply_to_msg_id": "msg_456",
            "subject": null,
            "body_html": "<p>Thanks for your email!</p>"
        }

    Example response:
        {
            "draft_id": "r-1234567890",
            "message_id": "msg_789",
            "thread_id": "thread_123",
            "subject": "Re: Original Subject",
            "created_at": "2025-01-15T10:30:00Z",
            "is_duplicate": false
        }
    """
    user = auth_session.get("user")
    user_sub = user.get("sub")
    user_email = user.get("email", "unknown")

    logger.info(
        "Draft reply creation request initiated",
        extra={
            "user_sub": user_sub[:8] + "..." if user_sub and len(user_sub) > 8 else "[redacted]",
            "user_email": user_email if user_email != "unknown" else "[redacted]",
            "thread_id": thread_id,
            "reply_to_msg_id": request.reply_to_msg_id
        }
    )

    # Validate inputs
    if not thread_id or not request.reply_to_msg_id:
        logger.warning(
            "Invalid draft request: missing thread_id or reply_to_msg_id",
            extra={"thread_id": thread_id, "reply_to_msg_id": request.reply_to_msg_id}
        )
        raise HTTPException(
            status_code=400,
            detail="Both thread_id and reply_to_msg_id are required"
        )

    if not request.body_html or not request.body_html.strip():
        logger.warning(
            "Invalid draft request: missing body_html",
            extra={"thread_id": thread_id}
        )
        raise HTTPException(
            status_code=400,
            detail="body_html is required and cannot be empty"
        )

    try:
        # Exchange Auth0 session for Google access token
        access_token = await get_google_access_token(
            user_sub=user_sub,
            scopes=settings.GMAIL_SCOPES_LIST
        )

        # Check for existing draft (idempotency)
        content_hash = hashlib.sha256(request.body_html.encode('utf-8')).hexdigest()

        with Session(engine) as db_session:
            # Query for existing draft with same context
            statement = select(GmailDraft).where(
                GmailDraft.user_id == user_sub,
                GmailDraft.thread_id == thread_id,
                GmailDraft.reply_to_msg_id == request.reply_to_msg_id,
                GmailDraft.content_hash == content_hash
            )
            existing_draft = db_session.exec(statement).first()

            if existing_draft:
                logger.info(
                    "Returning existing draft (idempotent request)",
                    extra={
                        "user_sub": user_sub[:8] + "...",
                        "thread_id": thread_id,
                        "draft_id": existing_draft.draft_id
                    }
                )
                return DraftResponse(
                    draft_id=existing_draft.draft_id,
                    message_id=existing_draft.draft_id,  # Draft ID can serve as message ID
                    thread_id=existing_draft.thread_id,
                    subject=existing_draft.subject,
                    created_at=existing_draft.created_at.isoformat(),
                    is_duplicate=True
                )

            # Create new draft via Gmail service
            draft_data = await create_reply_draft(
                user_token=access_token,
                thread_id=thread_id,
                reply_to_msg_id=request.reply_to_msg_id,
                subject=request.subject,
                html_body=request.body_html
            )

            # Extract draft details
            draft_id = draft_data.get("id")
            message_data = draft_data.get("message", {})
            message_id = message_data.get("id")

            # Get the subject from the message headers
            headers = message_data.get("payload", {}).get("headers", [])
            subject = request.subject or "Re: (no subject)"
            for header in headers:
                if header.get("name", "").lower() == "subject":
                    subject = header.get("value", subject)
                    break

            # Store draft reference in database for idempotency
            draft_record = GmailDraft(
                user_id=user_sub,
                user_email=user_email,
                thread_id=thread_id,
                reply_to_msg_id=request.reply_to_msg_id,
                draft_id=draft_id,
                subject=subject,
                content_hash=content_hash,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db_session.add(draft_record)
            db_session.commit()

            logger.info(
                "Draft reply created and stored successfully",
                extra={
                    "user_sub": user_sub[:8] + "...",
                    "thread_id": thread_id,
                    "draft_id": draft_id,
                    "message_id": message_id
                }
            )

            return DraftResponse(
                draft_id=draft_id,
                message_id=message_id or draft_id,
                thread_id=thread_id,
                subject=subject,
                created_at=draft_record.created_at.isoformat(),
                is_duplicate=False
            )

    except ThreadNotFoundError as e:
        logger.warning(
            "Thread or message not found",
            extra={
                "user_sub": user_sub[:8] + "...",
                "thread_id": thread_id,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except InvalidMessageError as e:
        logger.warning(
            "Invalid message data",
            extra={
                "user_sub": user_sub[:8] + "...",
                "thread_id": thread_id,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except GmailServiceError as e:
        logger.error(
            "Gmail service error",
            extra={
                "user_sub": user_sub[:8] + "...",
                "thread_id": thread_id,
                "error_code": e.error_code,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except InsufficientScopeError as e:
        logger.warning(
            "Insufficient Gmail scope for draft creation",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except InvalidGrantError as e:
        logger.warning(
            "Invalid Gmail grant for draft creation",
            extra={"user_sub": user_sub[:8] + "...", "error": e.message}
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except TokenExchangeError as e:
        logger.error(
            "Token exchange error for draft creation",
            extra={
                "user_sub": user_sub[:8] + "...",
                "error_code": e.error_code,
                "error": e.message
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error creating draft reply",
            extra={
                "user_sub": user_sub[:8] + "...",
                "thread_id": thread_id,
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again or contact support."
        )
