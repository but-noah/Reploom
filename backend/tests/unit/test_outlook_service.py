"""Unit tests for Outlook service layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.integrations.outlook_service import (
    list_messages,
    get_message,
    create_reply_draft,
    MessageNotFoundError,
    InvalidMessageError,
    OutlookServiceError,
)


@pytest.mark.asyncio
class TestListMessages:
    """Test list_messages function."""

    async def test_list_messages_success(self):
        """Test successful message list retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('user')/messages",
            "value": [
                {
                    "id": "AAMkAGI2NGI...",
                    "conversationId": "AAQkAGI...",
                    "subject": "Meeting tomorrow",
                    "from": {
                        "emailAddress": {
                            "name": "John Doe",
                            "address": "john@example.com"
                        }
                    },
                    "bodyPreview": "Let's meet at...",
                    "receivedDateTime": "2024-01-15T10:00:00Z",
                    "isRead": False,
                    "hasAttachments": False
                },
                {
                    "id": "AAMkAGI2NGI2...",
                    "conversationId": "AAQkAGI2...",
                    "subject": "Project update",
                    "from": {
                        "emailAddress": {
                            "name": "Jane Smith",
                            "address": "jane@example.com"
                        }
                    },
                    "bodyPreview": "Here is the latest...",
                    "receivedDateTime": "2024-01-14T15:30:00Z",
                    "isRead": True,
                    "hasAttachments": True
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await list_messages("fake_token", folder="inbox", top=50, skip=0)

            assert "@odata.context" in result
            assert "value" in result
            assert len(result["value"]) == 2
            assert result["value"][0]["subject"] == "Meeting tomorrow"
            assert result["value"][1]["subject"] == "Project update"

            # Verify API call was made with correct parameters
            mock_async_client.get.assert_called_once()
            call_kwargs = mock_async_client.get.call_args[1]
            assert "params" in call_kwargs
            assert call_kwargs["params"]["$top"] == 50
            assert call_kwargs["params"]["$skip"] == 0

    async def test_list_messages_unauthorized(self):
        """Test 401 error for expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": {"message": "Unauthorized"}}'

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await list_messages("fake_token", folder="inbox")

            assert exc_info.value.status_code == 401
            assert "Outlook authorization expired" in str(exc_info.value.detail)

    async def test_list_messages_folder_not_found(self):
        """Test 404 error when folder doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": {"message": "Folder not found"}}'
        mock_response.json.return_value = {
            "error": {"message": "Folder not found"}
        }

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(OutlookServiceError) as exc_info:
                await list_messages("fake_token", folder="nonexistent")

            assert exc_info.value.status_code == 404
            assert "Folder 'nonexistent' not found" in exc_info.value.message

    async def test_list_messages_forbidden(self):
        """Test 403 error for insufficient permissions."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.content = b'{"error": {"message": "Access denied"}}'
        mock_response.json.return_value = {
            "error": {"message": "Access denied"}
        }

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await list_messages("fake_token", folder="inbox")

            assert exc_info.value.status_code == 403
            assert "Outlook access denied" in str(exc_info.value.detail)

    async def test_list_messages_pagination(self):
        """Test message listing with pagination parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            await list_messages("fake_token", folder="inbox", top=25, skip=50)

            # Verify pagination parameters were passed correctly
            call_kwargs = mock_async_client.get.call_args[1]
            assert call_kwargs["params"]["$top"] == 25
            assert call_kwargs["params"]["$skip"] == 50


@pytest.mark.asyncio
class TestGetMessage:
    """Test get_message function."""

    async def test_get_message_success(self):
        """Test successful message retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "AAMkAGI2NGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Meeting tomorrow",
            "from": {
                "emailAddress": {
                    "name": "John Doe",
                    "address": "john@example.com"
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "name": "Recipient",
                        "address": "recipient@example.com"
                    }
                }
            ],
            "body": {
                "contentType": "html",
                "content": "<html><body><p>Meeting details...</p></body></html>"
            },
            "receivedDateTime": "2024-01-15T10:00:00Z",
            "internetMessageId": "<abc@example.com>"
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await get_message("fake_token", "AAMkAGI2NGI...")

            assert result["id"] == "AAMkAGI2NGI..."
            assert result["subject"] == "Meeting tomorrow"
            assert result["from"]["emailAddress"]["address"] == "john@example.com"
            assert result["body"]["contentType"] == "html"

    async def test_get_message_not_found(self):
        """Test 404 error when message doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": {"message": "Not found"}}'

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(MessageNotFoundError) as exc_info:
                await get_message("fake_token", "nonexistent_message")

            assert exc_info.value.status_code == 404
            assert "Message nonexistent_message not found" in exc_info.value.message

    async def test_get_message_unauthorized(self):
        """Test 401 error for expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"error": {"message": "Unauthorized"}}'

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await get_message("fake_token", "AAMkAGI2NGI...")

            assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestCreateReplyDraft:
    """Test create_reply_draft function."""

    async def test_create_reply_draft_success(self):
        """Test successful draft creation."""
        # Mock createReply response
        mock_create_response = MagicMock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "id": "AAMkAGI2NGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Re: Original Subject",
            "isDraft": True
        }
        mock_create_response.raise_for_status = MagicMock()

        # Mock PATCH update response
        mock_update_response = MagicMock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {
            "id": "AAMkAGI2NGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Re: Original Subject",
            "body": {
                "contentType": "html",
                "content": "<p>Thanks for your email!</p>"
            },
            "isDraft": True
        }
        mock_update_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            # First call creates draft, second updates body
            mock_async_client.post = AsyncMock(return_value=mock_create_response)
            mock_async_client.patch = AsyncMock(return_value=mock_update_response)
            mock_client.return_value = mock_async_client

            result = await create_reply_draft(
                user_token="fake_token",
                message_id="AAMkAGI...",
                html_body="<p>Thanks for your email!</p>"
            )

            assert result["id"] == "AAMkAGI2NGI..."
            assert result["conversationId"] == "AAQkAGI..."
            assert result["subject"] == "Re: Original Subject"

            # Verify createReply was called
            mock_async_client.post.assert_called_once()
            post_call_args = mock_async_client.post.call_args[0]
            assert "createReply" in post_call_args[0]

            # Verify PATCH was called to update body
            mock_async_client.patch.assert_called_once()
            patch_call_kwargs = mock_async_client.patch.call_args[1]
            assert "json" in patch_call_kwargs
            assert "body" in patch_call_kwargs["json"]
            assert patch_call_kwargs["json"]["body"]["contentType"] == "html"
            assert patch_call_kwargs["json"]["body"]["content"] == "<p>Thanks for your email!</p>"

    async def test_create_reply_draft_with_comment(self):
        """Test draft creation with optional comment."""
        mock_create_response = MagicMock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "id": "AAMkAGI2NGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Re: Original Subject"
        }
        mock_create_response.raise_for_status = MagicMock()

        mock_update_response = MagicMock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {
            "id": "AAMkAGI2NGI...",
            "conversationId": "AAQkAGI...",
            "subject": "Re: Original Subject"
        }
        mock_update_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_create_response)
            mock_async_client.patch = AsyncMock(return_value=mock_update_response)
            mock_client.return_value = mock_async_client

            await create_reply_draft(
                user_token="fake_token",
                message_id="AAMkAGI...",
                html_body="<p>Reply</p>",
                comment="This is a quick reply"
            )

            # Verify comment was included in createReply call
            post_call_kwargs = mock_async_client.post.call_args[1]
            assert "json" in post_call_kwargs
            assert "comment" in post_call_kwargs["json"]
            assert post_call_kwargs["json"]["comment"] == "This is a quick reply"

    async def test_create_reply_draft_message_not_found(self):
        """Test error when message doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"error": {"message": "Not found"}}'

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(MessageNotFoundError) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    message_id="nonexistent_msg",
                    html_body="<p>Reply</p>"
                )

            assert exc_info.value.status_code == 404

    async def test_create_reply_draft_invalid_request(self):
        """Test 400 error for invalid request."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Invalid request"}}'
        mock_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(InvalidMessageError) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    message_id="AAMkAGI...",
                    html_body="<p>Reply</p>"
                )

            assert exc_info.value.status_code == 400
            assert "Invalid draft request" in exc_info.value.message

    async def test_create_reply_draft_rate_limit(self):
        """Test 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.content = b'{"error": {"message": "Rate limit exceeded"}}'
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    message_id="AAMkAGI...",
                    html_body="<p>Reply</p>"
                )

            assert exc_info.value.status_code == 429

    async def test_create_reply_draft_no_draft_id_returned(self):
        """Test error when Graph API doesn't return draft ID."""
        mock_create_response = MagicMock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            # Missing "id" field
            "conversationId": "AAQkAGI...",
            "subject": "Re: Original Subject"
        }
        mock_create_response.raise_for_status = MagicMock()

        with patch("app.integrations.outlook_service.httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_create_response)
            mock_client.return_value = mock_async_client

            with pytest.raises(InvalidMessageError) as exc_info:
                await create_reply_draft(
                    user_token="fake_token",
                    message_id="AAMkAGI...",
                    html_body="<p>Reply</p>"
                )

            assert "no ID returned" in exc_info.value.message
