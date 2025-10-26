"""API endpoints for workspace settings management."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.auth import auth_client
from app.core.db import engine
from app.models.workspace_settings import WorkspaceSettings

logger = logging.getLogger(__name__)

workspace_settings_router = APIRouter(
    prefix="/workspace-settings",
    tags=["workspace-settings"]
)


class WorkspaceSettingsResponse(BaseModel):
    """Response model for workspace settings."""
    workspace_id: str
    tone_level: int = Field(ge=1, le=5, description="Tone level (1=very formal, 5=very casual)")
    style_json: dict = Field(default_factory=dict, description="Additional brand voice guidelines")
    blocklist_json: list[str] = Field(default_factory=list, description="Disallowed phrases")
    approval_threshold: float | None = None


class WorkspaceSettingsUpdate(BaseModel):
    """Request model for updating workspace settings."""
    tone_level: int | None = Field(None, ge=1, le=5, description="Tone level (1=very formal, 5=very casual)")
    style_json: dict | None = Field(None, description="Additional brand voice guidelines")
    blocklist_json: list[str] | None = Field(None, description="Disallowed phrases")
    approval_threshold: float | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "tone_level": 3,
                "style_json": {"brand_voice": "professional yet approachable"},
                "blocklist_json": ["free trial", "money back guarantee"],
                "approval_threshold": 0.85
            }
        }


@workspace_settings_router.get("/{workspace_id}", response_model=WorkspaceSettingsResponse)
async def get_workspace_settings(
    workspace_id: str,
    auth_session=Depends(auth_client.require_session)
) -> WorkspaceSettingsResponse:
    """
    Get workspace settings by workspace ID.

    Returns workspace configuration including tone level, style preferences,
    and blocklist settings.
    """
    logger.info(f"Fetching workspace settings for: {workspace_id}")

    with Session(engine) as session:
        statement = select(WorkspaceSettings).where(
            WorkspaceSettings.workspace_id == workspace_id
        )
        result = session.exec(statement).first()

        if not result:
            # Try default workspace
            statement = select(WorkspaceSettings).where(
                WorkspaceSettings.workspace_id == "default"
            )
            result = session.exec(statement).first()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workspace settings not found for {workspace_id}"
                )

        return WorkspaceSettingsResponse(
            workspace_id=result.workspace_id,
            tone_level=result.tone_level,
            style_json=result.style_json,
            blocklist_json=result.blocklist_json,
            approval_threshold=result.approval_threshold
        )


@workspace_settings_router.put("/{workspace_id}", response_model=WorkspaceSettingsResponse)
async def update_workspace_settings(
    workspace_id: str,
    settings_update: WorkspaceSettingsUpdate,
    auth_session=Depends(auth_client.require_session)
) -> WorkspaceSettingsResponse:
    """
    Update workspace settings.

    Validates inputs and updates workspace configuration:
    - tone_level: Must be between 1-5
    - style_json: Must be a valid JSON object
    - blocklist_json: Limited to 100 items, each max 200 chars
    """
    logger.info(f"Updating workspace settings for: {workspace_id}")

    # Validate blocklist
    if settings_update.blocklist_json is not None:
        if len(settings_update.blocklist_json) > 100:
            raise HTTPException(
                status_code=400,
                detail="Blocklist cannot exceed 100 items"
            )

        for phrase in settings_update.blocklist_json:
            if len(phrase) > 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Blocklist phrase too long (max 200 chars): {phrase[:50]}..."
                )

    with Session(engine) as session:
        statement = select(WorkspaceSettings).where(
            WorkspaceSettings.workspace_id == workspace_id
        )
        result = session.exec(statement).first()

        if not result:
            # Create new workspace settings
            result = WorkspaceSettings(
                workspace_id=workspace_id,
                tone_level=settings_update.tone_level or 3,
                style_json=settings_update.style_json or {},
                blocklist_json=settings_update.blocklist_json or [],
                approval_threshold=settings_update.approval_threshold
            )
            session.add(result)
        else:
            # Update existing settings
            if settings_update.tone_level is not None:
                result.tone_level = settings_update.tone_level
            if settings_update.style_json is not None:
                result.style_json = settings_update.style_json
            if settings_update.blocklist_json is not None:
                result.blocklist_json = settings_update.blocklist_json
            if settings_update.approval_threshold is not None:
                result.approval_threshold = settings_update.approval_threshold

            result.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(result)

        logger.info(f"Workspace settings updated: {workspace_id}")

        return WorkspaceSettingsResponse(
            workspace_id=result.workspace_id,
            tone_level=result.tone_level,
            style_json=result.style_json,
            blocklist_json=result.blocklist_json,
            approval_threshold=result.approval_threshold
        )
