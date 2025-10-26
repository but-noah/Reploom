"""Gmail API service layer.

This module provides functions for interacting with the Gmail API,
including thread management and draft creation with proper MIME formatting.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
import httpx
from fastapi import HTTPException

from app.core.tracing import get_tracer, safe_span_attributes
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class GmailServiceError(Exception):
    """Base exception for Gmail service errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "gmail_service_error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ThreadNotFoundError(GmailServiceError):
    """Raised when a thread or message is not found."""

    def __init__(self, message: str = "Thread or message not found"):
        super().__init__(
            message=message,
            status_code=404,
            error_code="thread_not_found"
        )


class InvalidMessageError(GmailServiceError):
    """Raised when message data is invalid or missing required fields."""

    def __init__(self, message: str = "Invalid message data"):
        super().__init__(
            message=message,
            status_code=400,
            error_code="invalid_message"
        )


async def get_thread(user_token: str, thread_id: str) -> dict[str, Any]:
    """Get Gmail thread details.

    Args:
        user_token: Valid Google access token
        thread_id: Gmail thread ID

    Returns:
        dict containing thread data with messages

    Raises:
        ThreadNotFoundError: If thread doesn't exist
        GmailServiceError: For other API errors
        HTTPException: For network errors

    Example response:
        {
            "id": "thread_123",
            "messages": [
                {
                    "id": "msg_456",
                    "threadId": "thread_123",
                    "payload": {
                        "headers": [...],
                        "mimeType": "text/html"
                    }
                }
            ]
        }
    """
    with tracer.start_as_current_span("gmail.get_thread") as span:
        span.set_attributes(safe_span_attributes(
            thread_id=thread_id,
            operation="get_thread"
        ))

        gmail_api_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"

        logger.info(
            "Fetching Gmail thread",
            extra={"thread_id": thread_id}
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    gmail_api_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )

                # Handle specific error cases
                if response.status_code == 404:
                    logger.warning(
                        "Gmail thread not found",
                        extra={"thread_id": thread_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Thread not found"))
                    raise ThreadNotFoundError(f"Thread {thread_id} not found")

                elif response.status_code == 401:
                    logger.warning(
                        "Gmail API returned 401 for thread fetch",
                        extra={"thread_id": thread_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Unauthorized"))
                    raise HTTPException(
                        status_code=401,
                        detail="Gmail authorization expired. Please reconnect your Gmail account."
                    )

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "")
                    logger.warning(
                        "Gmail API returned 403 for thread fetch",
                        extra={"thread_id": thread_id, "error_message": error_message}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Forbidden"))
                    raise HTTPException(
                        status_code=403,
                        detail=f"Gmail access denied: {error_message or 'Permission denied'}"
                    )

                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Gmail API error fetching thread",
                        extra={
                            "thread_id": thread_id,
                            "status_code": response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    raise GmailServiceError(
                        message=f"Failed to fetch thread: {error_message}",
                        status_code=response.status_code,
                        error_code="thread_fetch_error"
                    )

                response.raise_for_status()
                thread_data = response.json()

                logger.info(
                    "Gmail thread fetched successfully",
                    extra={
                        "thread_id": thread_id,
                        "message_count": len(thread_data.get("messages", []))
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("message_count", len(thread_data.get("messages", [])))

                return thread_data

        except httpx.TimeoutException:
            logger.error("Gmail API timeout fetching thread", extra={"thread_id": thread_id})
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Gmail API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Gmail API network error fetching thread",
                extra={"thread_id": thread_id, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Gmail API. Please try again later."
            )

        except (ThreadNotFoundError, GmailServiceError, HTTPException):
            # Re-raise our custom exceptions (span status already set)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error fetching Gmail thread",
                extra={"thread_id": thread_id, "error_type": type(e).__name__}
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )


def _get_header_value(headers: list[dict], name: str) -> str | None:
    """Extract header value from Gmail message headers.

    Args:
        headers: List of header dicts from Gmail API
        name: Header name to find (case-insensitive)

    Returns:
        Header value or None if not found
    """
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _build_reply_mime(
    to_address: str,
    subject: str,
    html_body: str,
    in_reply_to: str | None = None,
    references: str | None = None,
    from_address: str = "me"
) -> str:
    """Build RFC-compliant MIME message for Gmail draft reply.

    Creates a properly formatted MIME message with:
    - HTML content type
    - In-Reply-To header (for threading)
    - References header (for threading)
    - Proper UTF-8 encoding

    Args:
        to_address: Recipient email address
        subject: Email subject (should include "Re:" for replies)
        html_body: HTML email body content
        in_reply_to: Message-ID of the message being replied to
        references: Space-separated list of Message-IDs in the thread
        from_address: Sender address (default "me" for Gmail API)

    Returns:
        Base64url-encoded MIME message string ready for Gmail API

    Example:
        >>> mime = _build_reply_mime(
        ...     to_address="sender@example.com",
        ...     subject="Re: Original Subject",
        ...     html_body="<p>Reply content</p>",
        ...     in_reply_to="<original-msg-id@gmail.com>",
        ...     references="<msg1@gmail.com> <msg2@gmail.com>"
        ... )
    """
    # Create MIME message
    message = MIMEMultipart("alternative")
    message["To"] = to_address
    message["From"] = from_address
    message["Subject"] = subject

    # Add threading headers if provided
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references

    # Add HTML body with proper encoding
    html_part = MIMEText(html_body, "html", "utf-8")
    message.attach(html_part)

    # Encode as base64url for Gmail API
    raw_message = message.as_string()
    encoded_message = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")

    return encoded_message


async def create_reply_draft(
    user_token: str,
    thread_id: str,
    reply_to_msg_id: str,
    subject: str | None,
    html_body: str
) -> dict[str, Any]:
    """Create a Gmail draft that replies within an existing thread.

    This function creates a draft with proper MIME formatting including:
    - In-Reply-To header set to the original message's Message-ID
    - References header containing the thread's message IDs
    - Subject with "Re:" prefix if not present
    - HTML content type with UTF-8 encoding
    - threadId to ensure proper Gmail threading

    Args:
        user_token: Valid Google access token
        thread_id: Gmail thread ID to reply within
        reply_to_msg_id: ID of the specific message being replied to
        subject: Email subject (auto-prefixed with "Re:" if None or missing prefix)
        html_body: HTML content of the reply

    Returns:
        dict containing created draft data from Gmail API

    Raises:
        ThreadNotFoundError: If thread or message doesn't exist
        InvalidMessageError: If message data is invalid or missing headers
        GmailServiceError: For other API errors
        HTTPException: For network errors

    Example:
        >>> draft = await create_reply_draft(
        ...     user_token="ya29.xxx",
        ...     thread_id="thread_123",
        ...     reply_to_msg_id="msg_456",
        ...     subject=None,  # Will auto-add "Re:"
        ...     html_body="<p>Thanks for your message!</p>"
        ... )
        >>> print(draft["id"])
        "r-1234567890"
    """
    with tracer.start_as_current_span("gmail.create_reply_draft") as span:
        span.set_attributes(safe_span_attributes(
            thread_id=thread_id,
            reply_to_msg_id=reply_to_msg_id,
            operation="create_draft",
            body_html=html_body  # Will be sanitized by safe_span_attributes
        ))

        logger.info(
            "Creating reply draft",
            extra={
                "thread_id": thread_id,
                "reply_to_msg_id": reply_to_msg_id
            }
        )

        try:
            # Step 1: Fetch the original message to get headers
            msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{reply_to_msg_id}"
            async with httpx.AsyncClient() as client:
                msg_response = await client.get(
                    msg_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )

                if msg_response.status_code == 404:
                    logger.warning(
                        "Message not found for reply",
                        extra={"reply_to_msg_id": reply_to_msg_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Message not found"))
                    raise ThreadNotFoundError(f"Message {reply_to_msg_id} not found")

                elif msg_response.status_code >= 400:
                    error_data = msg_response.json() if msg_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Failed to fetch message for reply",
                        extra={
                            "reply_to_msg_id": reply_to_msg_id,
                            "status_code": msg_response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {msg_response.status_code}"))
                    raise GmailServiceError(
                        message=f"Failed to fetch message: {error_message}",
                        status_code=msg_response.status_code
                    )

                msg_response.raise_for_status()
                original_message = msg_response.json()

            # Step 2: Extract headers from original message
            headers = original_message.get("payload", {}).get("headers", [])
            if not headers:
                logger.error(
                    "Original message missing headers",
                    extra={"reply_to_msg_id": reply_to_msg_id}
                )
                span.set_status(Status(StatusCode.ERROR, "Missing headers"))
                raise InvalidMessageError("Original message is missing required headers")

            # Get essential headers for threading
            original_message_id = _get_header_value(headers, "Message-ID")
            original_subject = _get_header_value(headers, "Subject")
            original_from = _get_header_value(headers, "From")
            existing_references = _get_header_value(headers, "References")

            if not original_message_id:
                logger.error(
                    "Original message missing Message-ID header",
                    extra={"reply_to_msg_id": reply_to_msg_id}
                )
                span.set_status(Status(StatusCode.ERROR, "Missing Message-ID"))
                raise InvalidMessageError("Original message is missing Message-ID header")

            # Step 3: Build reply subject
            if not subject:
                # Auto-generate subject from original
                if original_subject:
                    # Add "Re:" prefix if not present
                    if not original_subject.lower().startswith("re:"):
                        subject = f"Re: {original_subject}"
                    else:
                        subject = original_subject
                else:
                    subject = "Re: (no subject)"
            else:
                # Ensure "Re:" prefix for user-provided subject
                if not subject.lower().startswith("re:"):
                    subject = f"Re: {subject}"

            # Step 4: Build References header for proper threading
            # References should contain all previous message IDs plus the one we're replying to
            references_list = []
            if existing_references:
                # Add existing references
                references_list = [ref.strip() for ref in existing_references.split() if ref.strip()]
            # Add the message we're replying to if not already in references
            if original_message_id and original_message_id not in references_list:
                references_list.append(original_message_id)
            references = " ".join(references_list) if references_list else original_message_id

            # Step 5: Determine recipient (reply to sender)
            to_address = original_from if original_from else "unknown@example.com"

            # Step 6: Build MIME message
            encoded_message = _build_reply_mime(
                to_address=to_address,
                subject=subject,
                html_body=html_body,
                in_reply_to=original_message_id,
                references=references
            )

            # Step 7: Create draft via Gmail API
            draft_url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
            draft_payload = {
                "message": {
                    "raw": encoded_message,
                    "threadId": thread_id  # Critical for proper threading
                }
            }

            async with httpx.AsyncClient() as client:
                draft_response = await client.post(
                    draft_url,
                    headers={
                        "Authorization": f"Bearer {user_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json=draft_payload,
                    timeout=20.0
                )

                # Handle draft creation errors
                if draft_response.status_code == 400:
                    error_data = draft_response.json() if draft_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Invalid request")
                    logger.error(
                        "Invalid draft creation request",
                        extra={
                            "thread_id": thread_id,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, "Invalid request"))
                    raise InvalidMessageError(f"Invalid draft request: {error_message}")

                elif draft_response.status_code == 429:
                    logger.warning(
                        "Gmail API rate limit exceeded for draft creation",
                        extra={"thread_id": thread_id}
                    )
                    span.set_status(Status(StatusCode.ERROR, "Rate limited"))
                    raise HTTPException(
                        status_code=429,
                        detail="Gmail API rate limit exceeded. Please try again later."
                    )

                elif draft_response.status_code >= 400:
                    error_data = draft_response.json() if draft_response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(
                        "Failed to create draft",
                        extra={
                            "thread_id": thread_id,
                            "status_code": draft_response.status_code,
                            "error": error_message
                        }
                    )
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {draft_response.status_code}"))
                    raise GmailServiceError(
                        message=f"Failed to create draft: {error_message}",
                        status_code=draft_response.status_code,
                        error_code="draft_creation_error"
                    )

                draft_response.raise_for_status()
                draft_data = draft_response.json()

                logger.info(
                    "Gmail reply draft created successfully",
                    extra={
                        "thread_id": thread_id,
                        "draft_id": draft_data.get("id"),
                        "message_id": draft_data.get("message", {}).get("id")
                    }
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("draft_id", draft_data.get("id", ""))

                return draft_data

        except httpx.TimeoutException:
            logger.error(
                "Gmail API timeout creating draft",
                extra={"thread_id": thread_id}
            )
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            raise HTTPException(
                status_code=504,
                detail="Gmail API request timeout. Please try again."
            )

        except httpx.RequestError as e:
            logger.error(
                "Gmail API network error creating draft",
                extra={"thread_id": thread_id, "error": str(e)}
            )
            span.set_status(Status(StatusCode.ERROR, "Network error"))
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Gmail API. Please try again later."
            )

        except (ThreadNotFoundError, InvalidMessageError, GmailServiceError, HTTPException):
            # Re-raise our custom exceptions (span status should be set inline)
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error creating Gmail draft",
                extra={
                    "thread_id": thread_id,
                    "error_type": type(e).__name__
                }
            )
            span.set_status(Status(StatusCode.ERROR, f"Unexpected: {type(e).__name__}"))
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again or contact support."
            )
