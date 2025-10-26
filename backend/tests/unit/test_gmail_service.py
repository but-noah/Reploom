"""Unit tests for Gmail service layer."""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.integrations.gmail_service import (
    get_thread,
    create_reply_draft,
    _build_reply_mime,
    _get_header_value,
    ThreadNotFoundError,
    InvalidMessageError,
    GmailServiceError,
)


class TestGetHeaderValue:
    """Test _get_header_value helper function."""

    def test_get_header_value_found(self):
        """Test extracting an existing header."""
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {"name": "Subject", "value": "Test Subject"},
            {"name": "Message-ID", "value": "<msg123@gmail.com>"},
        ]
        result = _get_header_value(headers, "Subject")
        assert result == "Test Subject"

    def test_get_header_value_case_insensitive(self):
        """Test header name matching is case-insensitive."""
        headers = [
            {"name": "Content-Type", "value": "text/html"},
        ]
        result = _get_header_value(headers, "content-type")
        assert result == "text/html"

    def test_get_header_value_not_found(self):
        """Test returns None when header doesn't exist."""
        headers = [
            {"name": "From", "value": "sender@example.com"},
        ]
        result = _get_header_value(headers, "Subject")
        assert result is None

    def test_get_header_value_empty_list(self):
        """Test returns None for empty header list."""
        result = _get_header_value([], "Subject")
        assert result is None


class TestBuildReplyMime:
    """Test MIME message builder for draft replies."""

    def test_build_reply_mime_basic(self):
        """Test basic MIME message creation."""
        mime = _build_reply_mime(
            to_address="recipient@example.com",
            subject="Re: Test",
            html_body="<p>Reply content</p>"
        )

        # Decode the base64url encoded message
        decoded = base64.urlsafe_b64decode(mime).decode('utf-8')

        # Verify essential components
        assert "To: recipient@example.com" in decoded
        assert "Subject: Re: Test" in decoded
        # Content might be base64 encoded, so check for the MIME type instead
        assert "Content-Type: text/html; charset=\"utf-8\"" in decoded
        # Verify the message structure is valid
        assert "multipart/alternative" in decoded

    def test_build_reply_mime_with_threading_headers(self):
        """Test MIME with In-Reply-To and References headers."""
        mime = _build_reply_mime(
            to_address="recipient@example.com",
            subject="Re: Test",
            html_body="<p>Reply</p>",
            in_reply_to="<original@gmail.com>",
            references="<msg1@gmail.com> <msg2@gmail.com>"
        )

        decoded = base64.urlsafe_b64decode(mime).decode('utf-8')

        assert "In-Reply-To: <original@gmail.com>" in decoded
        assert "References: <msg1@gmail.com> <msg2@gmail.com>" in decoded

    def test_build_reply_mime_utf8_content(self):
        """Test MIME with UTF-8 special characters."""
        mime = _build_reply_mime(
            to_address="recipient@example.com",
            subject="Re: Test with émojis 🎉",
            html_body="<p>Hello 世界</p>"
        )

        decoded = base64.urlsafe_b64decode(mime).decode('utf-8')

        # Verify UTF-8 encoding is preserved
        assert "charset=\"utf-8\"" in decoded

    def test_build_reply_mime_no_threading_headers(self):
        """Test MIME without optional threading headers."""
        mime = _build_reply_mime(
            to_address="recipient@example.com",
            subject="Re: Test",
            html_body="<p>Reply</p>"
        )

        decoded = base64.urlsafe_b64decode(mime).decode('utf-8')

        # Verify threading headers are not present
        assert "In-Reply-To:" not in decoded
        assert "References:" not in decoded


@pytest.mark.asyncio
class TestGetThread:
    """Test get_thread function."""

    async def test_get_thread_success(self):
        """Test successful thread retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "thread_123",
            "messages": [
                {"id": "msg_456", "threadId": "thread_123"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await get_thread("fake_token", "thread_123")

            assert result["id"] == "thread_123"
            assert len(result["messages"]) == 1
            assert result["messages"][0]["id"] == "msg_456"

    async def test_get_thread_not_found(self):
        """Test 404 error when thread doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": {"message": "Not found"}}'

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(ThreadNotFoundError) as exc_info:
                await get_thread("fake_token", "nonexistent_thread")

            assert exc_info.value.status_code == 404

    async def test_get_thread_unauthorized(self):
        """Test 401 error for expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": {"message": "Unauthorized"}}'

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await get_thread("fake_token", "thread_123")

            assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestCreateReplyDraft:
    """Test create_reply_draft function."""

    async def test_create_reply_draft_success(self):
        """Test successful draft creation with proper MIME."""
        # Mock message fetch response
        mock_msg_response = MagicMock()
        mock_msg_response.status_code = 200
        mock_msg_response.json.return_value = {
            "id": "msg_456",
            "threadId": "thread_123",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<original@gmail.com>"},
                    {"name": "Subject", "value": "Original Subject"},
                    {"name": "From", "value": "sender@example.com"},
                ]
            }
        }
        mock_msg_response.raise_for_status = MagicMock()

        # Mock draft creation response
        mock_draft_response = MagicMock()
        mock_draft_response.status_code = 200
        mock_draft_response.json.return_value = {
            "id": "r-1234567890",
            "message": {
                "id": "msg_789",
                "threadId": "thread_123",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Re: Original Subject"}
                    ]
                }
            }
        }
        mock_draft_response.raise_for_status = MagicMock()

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            # First call fetches message, second creates draft
            mock_async_client.get = AsyncMock(return_value=mock_msg_response)
            mock_async_client.post = AsyncMock(return_value=mock_draft_response)
            mock_client.return_value = mock_async_client

            result = await create_reply_draft(
                user_token="fake_token",
                thread_id="thread_123",
                reply_to_msg_id="msg_456",
                subject=None,  # Should auto-generate "Re: Original Subject"
                html_body="<p>Thanks for your email!</p>"
            )

            assert result["id"] == "r-1234567890"
            assert result["message"]["threadId"] == "thread_123"

            # Verify draft creation was called with proper structure
            mock_async_client.post.assert_called_once()
            call_kwargs = mock_async_client.post.call_args[1]
            assert "json" in call_kwargs
            assert "message" in call_kwargs["json"]
            assert "raw" in call_kwargs["json"]["message"]
            assert "threadId" in call_kwargs["json"]["message"]
            assert call_kwargs["json"]["message"]["threadId"] == "thread_123"

    async def test_create_reply_draft_custom_subject(self):
        """Test draft with custom subject adds Re: prefix."""
        mock_msg_response = MagicMock()
        mock_msg_response.status_code = 200
        mock_msg_response.json.return_value = {
            "id": "msg_456",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<original@gmail.com>"},
                    {"name": "From", "value": "sender@example.com"},
                ]
            }
        }
        mock_msg_response.raise_for_status = MagicMock()

        mock_draft_response = MagicMock()
        mock_draft_response.status_code = 200
        mock_draft_response.json.return_value = {
            "id": "r-1234567890",
            "message": {"id": "msg_789", "payload": {"headers": []}}
        }
        mock_draft_response.raise_for_status = MagicMock()

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_msg_response)
            mock_async_client.post = AsyncMock(return_value=mock_draft_response)
            mock_client.return_value = mock_async_client

            await create_reply_draft(
                user_token="fake_token",
                thread_id="thread_123",
                reply_to_msg_id="msg_456",
                subject="Custom Subject",  # Should become "Re: Custom Subject"
                html_body="<p>Reply</p>"
            )

            # Verify the MIME message was built with Re: prefix
            call_kwargs = mock_async_client.post.call_args[1]
            raw_message = call_kwargs["json"]["message"]["raw"]
            decoded = base64.urlsafe_b64decode(raw_message).decode('utf-8')
            assert "Subject: Re: Custom Subject" in decoded

    async def test_create_reply_draft_missing_message_id(self):
        """Test error when original message lacks Message-ID header."""
        mock_msg_response = MagicMock()
        mock_msg_response.status_code = 200
        mock_msg_response.json.return_value = {
            "id": "msg_456",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    # Missing Message-ID header
                ]
            }
        }
        mock_msg_response.raise_for_status = MagicMock()

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_msg_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(InvalidMessageError) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    thread_id="thread_123",
                    reply_to_msg_id="msg_456",
                    subject=None,
                    html_body="<p>Reply</p>"
                )

            assert "Message-ID" in exc_info.value.message

    async def test_create_reply_draft_message_not_found(self):
        """Test error when reply_to_msg_id doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(ThreadNotFoundError) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    thread_id="thread_123",
                    reply_to_msg_id="nonexistent_msg",
                    subject=None,
                    html_body="<p>Reply</p>"
                )

            assert exc_info.value.status_code == 404

    async def test_create_reply_draft_builds_references_chain(self):
        """Test that References header includes all previous message IDs."""
        mock_msg_response = MagicMock()
        mock_msg_response.status_code = 200
        mock_msg_response.json.return_value = {
            "id": "msg_456",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<msg3@gmail.com>"},
                    {"name": "References", "value": "<msg1@gmail.com> <msg2@gmail.com>"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Re: Thread"},
                ]
            }
        }
        mock_msg_response.raise_for_status = MagicMock()

        mock_draft_response = MagicMock()
        mock_draft_response.status_code = 200
        mock_draft_response.json.return_value = {
            "id": "r-1234567890",
            "message": {"id": "msg_789", "payload": {"headers": []}}
        }
        mock_draft_response.raise_for_status = MagicMock()

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_msg_response)
            mock_async_client.post = AsyncMock(return_value=mock_draft_response)
            mock_client.return_value = mock_async_client

            await create_reply_draft(
                user_token="fake_token",
                thread_id="thread_123",
                reply_to_msg_id="msg_456",
                subject=None,
                html_body="<p>Reply</p>"
            )

            # Verify References header includes all message IDs
            call_kwargs = mock_async_client.post.call_args[1]
            raw_message = call_kwargs["json"]["message"]["raw"]
            decoded = base64.urlsafe_b64decode(raw_message).decode('utf-8')

            # Should contain all three message IDs
            assert "<msg1@gmail.com>" in decoded
            assert "<msg2@gmail.com>" in decoded
            assert "<msg3@gmail.com>" in decoded
            assert "References: <msg1@gmail.com> <msg2@gmail.com> <msg3@gmail.com>" in decoded

    async def test_create_reply_draft_rate_limit(self):
        """Test 429 rate limit error."""
        mock_msg_response = MagicMock()
        mock_msg_response.status_code = 200
        mock_msg_response.json.return_value = {
            "id": "msg_456",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<original@gmail.com>"},
                    {"name": "From", "value": "sender@example.com"},
                ]
            }
        }
        mock_msg_response.raise_for_status = MagicMock()

        mock_draft_response = MagicMock()
        mock_draft_response.status_code = 429
        mock_draft_response.content = b'{"error": {"message": "Rate limit exceeded"}}'
        mock_draft_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }

        with patch("app.integrations.gmail_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_msg_response)
            mock_async_client.post = AsyncMock(return_value=mock_draft_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    thread_id="thread_123",
                    reply_to_msg_id="msg_456",
                    subject=None,
                    html_body="<p>Reply</p>"
                )

            assert exc_info.value.status_code == 429
