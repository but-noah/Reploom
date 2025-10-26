"""Database models for workspace configuration."""

import uuid
from datetime import datetime
from typing import Literal
from sqlmodel import Field, SQLModel, Column, JSON


class WorkspaceSettings(SQLModel, table=True):
    """Store workspace-level configuration for draft generation.

    Each workspace can configure:
    - Tone level (formal, friendly, casual)
    - Blocklist phrases (list of disallowed strings)
    - Additional policy settings

    This model enables workspace-specific policy enforcement in the
    draft generation workflow.
    """

    __tablename__ = "workspace_settings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Workspace identifier (links to FGA workspace)
    workspace_id: str = Field(index=True, unique=True)

    # Tone configuration
    tone_level: Literal["formal", "friendly", "casual"] = Field(
        default="friendly",
        description="Default tone for draft generation"
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """SQLModel configuration."""
        json_schema_extra = {
            "example": {
                "workspace_id": "ws-acme-corp",
                "tone_level": "friendly",
                "blocklist_json": ["free trial", "money back guarantee", "limited time offer"],
                "approval_threshold": 0.85
            }
        }


# Stub data for testing (can be loaded via migration or seed script)
DEFAULT_WORKSPACE_SETTINGS = [
    {
        "workspace_id": "default",
        "tone_level": "friendly",
        "blocklist_json": ["free trial", "money back guarantee", "limited time offer"],
        "approval_threshold": 0.85,
    },
    {
        "workspace_id": "ws-test",
        "tone_level": "formal",
        "blocklist_json": ["click here", "act now", "special offer"],
        "approval_threshold": 0.90,
    },
]
