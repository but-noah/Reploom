"""Database models for Gmail draft tracking."""

import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class GmailDraft(SQLModel, table=True):
    """Track Gmail drafts for idempotency.

    This model stores a reference to created drafts to prevent duplicates
    when the same source message generates multiple draft attempts.

    The combination of (user_id, thread_id, reply_to_msg_id) should be unique
    to ensure we don't create duplicate drafts for the same reply context.
    """

    __tablename__ = "gmail_drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # User who created the draft
    user_id: str = Field(index=True)
    user_email: str

    # Gmail thread and message references
    thread_id: str = Field(index=True)
    reply_to_msg_id: str = Field(index=True)

    # Gmail draft ID returned from API
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
            ("user_id", "thread_id", "reply_to_msg_id"),
        ]
