"""Database models for workspace configuration."""

import uuid
from datetime import datetime, timezone
from typing import Literal, Annotated
from sqlmodel import Field, SQLModel, Column, JSON, String, Integer


class WorkspaceSettings(SQLModel, table=True):
    """Store workspace-level configuration for draft generation.

    Each workspace can configure:
    - Tone level (1-5 scale: 1=very formal, 5=very casual)
    - Style JSON (additional brand voice guidelines)
    - Blocklist phrases (list of disallowed strings)
    - Additional policy settings

    This model enables workspace-specific policy enforcement in the
    draft generation workflow.
    """

    __tablename__ = "workspace_settings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Workspace identifier (links to FGA workspace)
    workspace_id: str = Field(index=True, unique=True)

    # Tone configuration (1=very formal, 3=neutral, 5=very casual)
    tone_level: int = Field(
        default=3,
        sa_column=Column(Integer),
        description="Tone level for draft generation (1-5 scale)"
    )

    # Additional style configuration
    style_json: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional brand voice guidelines and style preferences"
    )

    # Policy configuration
    blocklist_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of disallowed phrases (case-insensitive)"
    )

    # Confidence threshold for auto-approval (future use)
    approval_threshold: float | None = Field(
        default=None,
        description="Minimum confidence score for auto-send (if implemented)"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """SQLModel configuration."""
        json_schema_extra = {
            "example": {
                "workspace_id": "ws-acme-corp",
                "tone_level": 3,
                "style_json": {"brand_voice": "professional yet approachable"},
                "blocklist_json": ["free trial", "money back guarantee", "limited time offer"],
                "approval_threshold": 0.85
            }
        }


# Stub data for testing (can be loaded via migration or seed script)
DEFAULT_WORKSPACE_SETTINGS = [
    {
        "workspace_id": "default",
        "tone_level": 3,
        "style_json": {},
        "blocklist_json": ["free trial", "money back guarantee", "limited time offer"],
        "approval_threshold": 0.85,
    },
    {
        "workspace_id": "ws-test",
        "tone_level": 2,
        "style_json": {"brand_voice": "formal and professional"},
        "blocklist_json": ["click here", "act now", "special offer"],
        "approval_threshold": 0.90,
    },
]
