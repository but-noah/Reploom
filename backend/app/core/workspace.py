"""Workspace configuration utilities."""

import logging
from typing import Literal
from sqlmodel import Session, select
from app.models.workspace_settings import WorkspaceSettings, DEFAULT_WORKSPACE_SETTINGS
from app.core.db import engine

logger = logging.getLogger(__name__)


class WorkspaceConfig:
    """Workspace configuration container."""

    def __init__(
        self,
        workspace_id: str,
        tone_level: int,
        style_json: dict,
        blocklist: list[str],
        approval_threshold: float | None = None,
    ):
        self.workspace_id = workspace_id
        self.tone_level = tone_level
        self.style_json = style_json
        self.blocklist = blocklist
        self.approval_threshold = approval_threshold


def get_workspace_settings(workspace_id: str | None) -> WorkspaceConfig:
    """
    Fetch workspace settings from database or return stub defaults.

    Args:
        workspace_id: Workspace identifier, or None for default settings

    Returns:
        WorkspaceConfig with tone_level, blocklist, and other settings

    Note:
        - Falls back to "default" workspace if workspace_id not found
        - Uses hardcoded stub data if database query fails
        - Logs warnings for fallback cases
    """
    # Use default workspace if none specified
    if not workspace_id:
        workspace_id = "default"
        logger.info("No workspace_id provided, using 'default'")

    try:
        with Session(engine) as session:
            # Query workspace settings
            statement = select(WorkspaceSettings).where(
                WorkspaceSettings.workspace_id == workspace_id
            )
            result = session.exec(statement).first()

            if result:
                logger.info(f"Loaded settings for workspace: {workspace_id}")
                return WorkspaceConfig(
                    workspace_id=result.workspace_id,
                    tone_level=result.tone_level,
                    style_json=result.style_json,
                    blocklist=result.blocklist_json,
                    approval_threshold=result.approval_threshold,
                )

            # Try default workspace if specific workspace not found
            if workspace_id != "default":
                logger.warning(
                    f"Workspace {workspace_id} not found, falling back to default"
                )
                statement = select(WorkspaceSettings).where(
                    WorkspaceSettings.workspace_id == "default"
                )
                result = session.exec(statement).first()

                if result:
                    return WorkspaceConfig(
                        workspace_id="default",
                        tone_level=result.tone_level,
                        style_json=result.style_json,
                        blocklist=result.blocklist_json,
                        approval_threshold=result.approval_threshold,
                    )

    except Exception as e:
        logger.warning(f"Failed to load workspace settings from DB: {e}")

    # Final fallback: use stub data
    logger.warning("Using stub workspace settings")
    stub = next(
        (ws for ws in DEFAULT_WORKSPACE_SETTINGS if ws["workspace_id"] == workspace_id),
        DEFAULT_WORKSPACE_SETTINGS[0],  # default workspace
    )

    return WorkspaceConfig(
        workspace_id=stub["workspace_id"],
        tone_level=stub["tone_level"],
        style_json=stub.get("style_json", {}),
        blocklist=stub["blocklist_json"],
        approval_threshold=stub.get("approval_threshold"),
    )


def seed_workspace_settings():
    """
    Seed database with default workspace settings.

    This should be called during application initialization or via migration.
    """
    try:
        with Session(engine) as session:
            for stub in DEFAULT_WORKSPACE_SETTINGS:
                # Check if workspace already exists
                statement = select(WorkspaceSettings).where(
                    WorkspaceSettings.workspace_id == stub["workspace_id"]
                )
                existing = session.exec(statement).first()

                if not existing:
                    settings = WorkspaceSettings(**stub)
                    session.add(settings)
                    logger.info(f"Seeded workspace settings: {stub['workspace_id']}")

            session.commit()
            logger.info("Workspace settings seeded successfully")

    except Exception as e:
        logger.error(f"Failed to seed workspace settings: {e}")
        raise
