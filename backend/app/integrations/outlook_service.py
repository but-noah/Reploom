"""Outlook / Microsoft Graph API service layer.

This module provides functions for interacting with the Microsoft Graph API
for Outlook mail operations, including message management and draft creation.
"""

import logging
from typing import Any
import httpx
from fastapi import HTTPException

from app.core.tracing import get_tracer, safe_span_attributes
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class OutlookServiceError(Exception):
    """Base exception for Outlook service errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "outlook_service_error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class MessageNotFoundError(OutlookServiceError):
    """Raised when a message or conversation is not found."""

    def __init__(self, message: str = "Message or conversation not found"):
        super().__init__(
            message=message,
            status_code=404,
            error_code="message_not_found"
        )


class InvalidMessageError(OutlookServiceError):
    """Raised when message data is invalid or missing required fields."""

    def __init__(self, message: str = "Invalid message data"):
        super().__init__(
            message=message,
            status_code=400,
            error_code="invalid_message"
        )


async def list_messages(
    user_token: str,
    folder: str = "inbox",
    top: int = 50,
    skip: int = 0
) -> dict[str, Any]:
    """List Outlook messages from a specific folder.

    Args:
        user_token: Valid Microsoft access token
        folder: Folder to list messages from (default: "inbox")
        top: Maximum number of messages to return (default: 50, max: 100)
        skip: Number of messages to skip for pagination (default: 0)

    Returns:
        dict containing messages list and metadata

    Raises:
        OutlookServiceError: For API errors
        HTTPException: For network errors

    Example response:
        {
            "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('user')/messages",
            "value": [
                {
                    "id": "AAMkAGI...",
                    "conversationId": "AAQkAGI...",
                    "subject": "Meeting tomorrow",
                    "from": {
                        "emailAddress": {
                            "name": "John Doe",
                            "address": "john@example.com"
                        }
                    },
                    "bodyPreview": "Let's meet at...",
                    "receivedDateTime": "2024-01-15T10:00:00Z"
                }
            ]
        }
    """
    with tracer.start_as_current_span("outlook.list_messages") as span:
        span.set_attributes(safe_span_attributes(
            folder=folder,
            top=top,
            skip=skip,
            operation="list_messages"
        ))

        # Microsoft Graph API endpoint for listing messages
        graph_api_url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"

        # Add query parameters
        params = {
            "$top": min(top, 100),  # Graph API max is 100
            "$skip": skip,
            "$orderby": "receivedDateTime DESC",
            "$select": "id,conversationId,subject,from,bodyPreview,receivedDateTime,isRead,hasAttachments"
        }

        logger.info(
            "Listing Outlook messages",
            extra={"folder": folder, "top": top, "skip": skip}
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    graph_api_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    params=params,
                    timeout=15.0
                )

                # Handle specific error cases
                if response.status_code == 401:
                    logger.warning("Microsoft Graph API returned 401 for list messages")
                    span.set_status(Status(StatusCode.ERROR, "Unauthorized"))
                    raise HTTPException(
                        status_code=401,
                        detail="Outlook authorization expired. Please reconnect your Outlook account."
                    )

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "")
                    logger.warning(
                        "Microsoft Graph API returned 403 for list messages",
                        extra={"error_message": error_message}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Forbidden"))
                    raise HTTPException(
                        status_code=403,
                        detail=f"Outlook access denied: {error_message or 'Permission denied'}"
                    )

                elif response.status_code == 404:
                    logger.warning(
                        "Folder not found",
                        extra={"folder": folder}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Folder not found"))
                    raise OutlookServiceError(
                        message=f"Folder '{folder}' not found",
                        status_code=404,
                        error_code="folder_not_found"
                    )

                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Microsoft Graph API error listing messages",
                        extra={
                            "folder": folder,
                            "status_code": response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    raise OutlookServiceError(
                        message=f"Failed to list messages: {error_message}",
                        status_code=response.status_code,
                        error_code="list_messages_error"
                    )

                response.raise_for_status()
                messages_data = response.json()

                logger.info(
                    "Outlook messages listed successfully",
                    extra={
                        "folder": folder,
                        "message_count": len(messages_data.get("value", []))
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("message_count", len(messages_data.get("value", [])))

                return messages_data

        except httpx.TimeoutException:
            logger.error("Microsoft Graph API timeout listing messages", extra={"folder": folder})
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Outlook API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Microsoft Graph API network error listing messages",
                extra={"folder": folder, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Outlook API. Please try again later."
            )

        except (OutlookServiceError, HTTPException):
            # Re-raise our custom exceptions (span status already set)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error listing Outlook messages",
                extra={"folder": folder, "error_type": type(e).__name__}
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )


async def get_message(user_token: str, message_id: str) -> dict[str, Any]:
    """Get a specific Outlook message by ID.

    Args:
        user_token: Valid Microsoft access token
        message_id: Microsoft Graph message ID

    Returns:
        dict containing full message data

    Raises:
        MessageNotFoundError: If message doesn't exist
        OutlookServiceError: For other API errors
        HTTPException: For network errors

    Example response:
        {
            "id": "AAMkAGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Meeting tomorrow",
            "from": {
                "emailAddress": {
                    "name": "John Doe",
                    "address": "john@example.com"
                }
            },
            "toRecipients": [...],
            "body": {
                "contentType": "html",
                "content": "<html>...</html>"
            },
            "receivedDateTime": "2024-01-15T10:00:00Z",
            "internetMessageId": "<abc@example.com>"
        }
    """
    with tracer.start_as_current_span("outlook.get_message") as span:
        span.set_attributes(safe_span_attributes(
            message_id=message_id,
            operation="get_message"
        ))

        graph_api_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"

        logger.info(
            "Fetching Outlook message",
            extra={"message_id": message_id}
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    graph_api_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )

                # Handle specific error cases
                if response.status_code == 404:
                    logger.warning(
                        "Outlook message not found",
                        extra={"message_id": message_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Message not found"))
                    raise MessageNotFoundError(f"Message {message_id} not found")

                elif response.status_code == 401:
                    logger.warning(
                        "Microsoft Graph API returned 401 for message fetch",
                        extra={"message_id": message_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Unauthorized"))
                    raise HTTPException(
                        status_code=401,
                        detail="Outlook authorization expired. Please reconnect your Outlook account."
                    )

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "")
                    logger.warning(
                        "Microsoft Graph API returned 403 for message fetch",
                        extra={"message_id": message_id, "error_message": error_message}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Forbidden"))
                    raise HTTPException(
                        status_code=403,
                        detail=f"Outlook access denied: {error_message or 'Permission denied'}"
                    )

                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Microsoft Graph API error fetching message",
                        extra={
                            "message_id": message_id,
                            "status_code": response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    raise OutlookServiceError(
                        message=f"Failed to fetch message: {error_message}",
                        status_code=response.status_code,
                        error_code="message_fetch_error"
                    )

                response.raise_for_status()
                message_data = response.json()

                logger.info(
                    "Outlook message fetched successfully",
                    extra={"message_id": message_id}
                )

                span.set_status(Status(StatusCode.OK))

                return message_data

        except httpx.TimeoutException:
            logger.error("Microsoft Graph API timeout fetching message", extra={"message_id": message_id})
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Outlook API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Microsoft Graph API network error fetching message",
                extra={"message_id": message_id, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Outlook API. Please try again later."
            )

        except (MessageNotFoundError, OutlookServiceError, HTTPException):
            # Re-raise our custom exceptions (span status already set)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error fetching Outlook message",
                extra={"message_id": message_id, "error_type": type(e).__name__}
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )


async def create_reply_draft(
    user_token: str,
    message_id: str,
    html_body: str,
    comment: str | None = None
) -> dict[str, Any]:
    """Create a reply draft for an Outlook message.

    This function creates a draft reply using the Microsoft Graph API's
    createReply action. The Graph API automatically handles:
    - Subject line with "Re:" prefix
    - In-Reply-To and References headers for threading
    - Recipient (replies to sender)
    - Conversation threading

    Args:
        user_token: Valid Microsoft access token
        message_id: ID of the message to reply to
        html_body: HTML content of the reply
        comment: Optional comment to prepend to the reply

    Returns:
        dict containing created draft message data from Graph API

    Raises:
        MessageNotFoundError: If message doesn't exist
        InvalidMessageError: If message data is invalid
        OutlookServiceError: For other API errors
        HTTPException: For network errors

    Example:
        >>> draft = await create_reply_draft(
        ...     user_token="eyJ0eXAi...",
        ...     message_id="AAMkAGI2NGI...",
        ...     html_body="<p>Thanks for your message!</p>"
        ... )
        >>> print(draft["id"])
        "AAMkAGI2NGI2..."

    Note:
        After creating the draft, you can update its body using the Graph API
        PATCH endpoint if you need to modify the HTML content.
    """
    with tracer.start_as_current_span("outlook.create_reply_draft") as span:
        span.set_attributes(safe_span_attributes(
            message_id=message_id,
            operation="create_draft",
            body_html=html_body  # Will be sanitized by safe_span_attributes
        ))

        logger.info(
            "Creating reply draft",
            extra={"message_id": message_id}
        )

        try:
            # Step 1: Create a reply draft using the createReply action
            # This automatically sets up threading, subject, and recipient
            create_reply_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/createReply"

            async with httpx.AsyncClient() as client:
                # Create the draft with optional comment
                payload = {}
                if comment:
                    payload["comment"] = comment

                create_response = await client.post(
                    create_reply_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json=payload,
                    timeout=15.0
                )

                if create_response.status_code == 404:
                    logger.warning(
                        "Message not found for reply",
                        extra={"message_id": message_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Message not found"))
                    raise MessageNotFoundError(f"Message {message_id} not found")

                elif create_response.status_code == 400:
                    error_data = create_response.json() if create_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Invalid request")
                    logger.error(
                        "Invalid draft creation request",
                        extra={"message_id": message_id, "error": error_message}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Invalid request"))
                    raise InvalidMessageError(f"Invalid draft request: {error_message}")

                elif create_response.status_code == 429:
                    logger.warning(
                        "Microsoft Graph API rate limit exceeded for draft creation",
                        extra={"message_id": message_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Rate limited"))
                    raise HTTPException(
                        status_code=429,
                        detail="Outlook API rate limit exceeded. Please try again later."
                    )

                elif create_response.status_code >= 400:
                    error_data = create_response.json() if create_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Failed to create reply draft",
                        extra={
                            "message_id": message_id,
                            "status_code": create_response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {create_response.status_code}"))
                    raise OutlookServiceError(
                        message=f"Failed to create draft: {error_message}",
                        status_code=create_response.status_code,
                        error_code="draft_creation_error"
                    )

                create_response.raise_for_status()
                draft_data = create_response.json()
                draft_id = draft_data.get("id")

                if not draft_id:
                    logger.error(
                        "Draft created but no ID returned",
                        extra={"message_id": message_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Missing draft ID"))
                    raise InvalidMessageError("Draft created but no ID returned from API")

                # Step 2: Update the draft body with our HTML content
                update_url = f"https://graph.microsoft.com/v1.0/me/messages/{draft_id}"
                update_payload = {
                    "body": {
                        "contentType": "html",
                        "content": html_body
                    }
                }

                update_response = await client.patch(
                    update_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json=update_payload,
                    timeout=15.0
                )

                if update_response.status_code >= 400:
                    error_data = update_response.json() if update_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Failed to update draft body",
                        extra={
                            "draft_id": draft_id,
                            "status_code": update_response.status_code,
                            "error": error_message
                        }
                    )
                    # Still return the draft data even if update fails
                    # The user can manually edit it
                    logger.warning("Draft created but body update failed, returning draft anyway")

                update_response.raise_for_status()
                updated_draft = update_response.json()

                logger.info(
                    "Outlook reply draft created successfully",
                    extra={
                        "message_id": message_id,
                        "draft_id": draft_id
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("draft_id", draft_id)

                return updated_draft

        except httpx.TimeoutException:
            logger.error(
                "Microsoft Graph API timeout creating draft",
                extra={"message_id": message_id}
            )
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Outlook API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Microsoft Graph API network error creating draft",
                extra={"message_id": message_id, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Outlook API. Please try again later."
            )

        except (MessageNotFoundError, InvalidMessageError, OutlookServiceError, HTTPException):
            # Re-raise our custom exceptions (span status should be set inline)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error creating Outlook draft",
                extra={
                    "message_id": message_id,
                    "error_type": type(e).__name__
                }
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )
