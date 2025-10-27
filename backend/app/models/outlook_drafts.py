"""Database models for Outlook draft tracking."""

import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class OutlookDraft(SQLModel, table=True):
    """Track Outlook drafts for idempotency.

    This model stores a reference to created Outlook drafts to prevent duplicates
    when the same source message generates multiple draft attempts.

    The combination of (user_id, conversation_id, message_id) should be unique
    to ensure we don't create duplicate drafts for the same reply context.
    """

    __tablename__ = "outlook_drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # User who created the draft
    user_id: str = Field(index=True)
    user_email: str

    # Outlook conversation and message references
    conversation_id: str = Field(index=True)
    message_id: str = Field(index=True)

    # Outlook draft ID returned from Graph API
    draft_id: str

    # Subject and content hash for duplicate detection
    subject: str
    content_hash: str = Field(
        description="SHA256 hash of the HTML body for duplicate detection"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """SQLModel configuration."""
        indexes = [
            # Composite index for finding existing drafts
            ("user_id", "conversation_id", "message_id"),
        ]
