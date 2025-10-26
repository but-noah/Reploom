"""Database models for draft review and approval workflow."""

import uuid
from datetime import datetime, timezone
from typing import Literal
from sqlmodel import Field, SQLModel, Column, JSON, String


class DraftReview(SQLModel, table=True):
    """Track review state and actions for generated drafts.

    This model stores the review workflow state for drafts generated
    by the Reploom agent, allowing users to approve, reject, or request
    edits before sending.
    """

    __tablename__ = "draft_reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # User who is reviewing
    user_id: str = Field(index=True)
    user_email: str

    # Link to Gmail thread and draft
    thread_id: str = Field(index=True)
    draft_id: str | None = None  # Gmail draft ID (if created)

    # LangGraph run information
    run_id: str | None = Field(default=None, index=True)
    workspace_id: str | None = None

    # Original message context
    original_message_summary: str
    original_message_excerpt: str | None = None

    # Classification results
    intent: str | None = None
    confidence: float | None = None

    # Draft content
    draft_html: str
    draft_version: int = Field(default=1)  # Track edit iterations

    # Policy violations
    violations: list[str] = Field(default=[], sa_column=Column(JSON))

    # Review state
    status: str = Field(
        default="pending", sa_column=Column(String, index=True)
    )

    # User feedback
    feedback: str | None = None
    edit_notes: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None

    class Config:
        """SQLModel configuration."""
        indexes = [
            ("user_id", "status"),
            ("thread_id", "user_id"),
        ]
